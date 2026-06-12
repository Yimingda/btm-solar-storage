"""
ppa_wheeling.py — Scenario 2: PPA / Wheeling financial model
BTM PV+BESS Financial Modelling System

Reuses the BTM engine (PVGIS generation, tariff & escalation logic,
20-year cash-flow framework) injected from app.py via an `eng` dict:

    eng = {
        "get_pvgis_data":      PVGIS fetcher        (lat, lon, kwp, loss, tilt, az),
        "get_tariff_for_hour": Megaflex TOU lookup  (hour, month, day_type),
        "get_capex_zar":       USD→ZAR unit costs,
        "SECTION_12B":         {1:.5, 2:.3, 3:.2} SA accelerated depreciation,
        "ANALYSIS_YEARS":      20,
        "fmw":                 kW→MW auto-scale formatter,
    }

Two linked perspectives sharing one PPA / Wheeling term sheet:
  • Developer / IPP   — revenue = PPA price × billed energy;
                        costs = CAPEX, OPEX, insurance, (wheeling if borne);
                        outputs: 20-yr cash flow, IRR, NPV, payback.
  • End-user / Offtaker — savings = avoided grid cost − (PPA cost +
                        wheeling-if-borne + loss share); 20-yr cumulative model.

Both Excel (openpyxl) and PPTX (report_pptx.generate_ppa_pptx) reports are
generated per perspective.
"""
from __future__ import annotations

import io
import re
import datetime as _dt

import numpy as np
import pandas as pd
import streamlit as st

DEV = "Developer / IPP"
USR = "End-user / Offtaker"

# ─────────────────────────────────────────────────────────────
# Session-state defaults (whl_* namespace, seeded from BTM params)
# ─────────────────────────────────────────────────────────────

def _init_state(eng: dict) -> None:
    if st.session_state.get("_whl_initialized"):
        return
    ss = st.session_state
    pv_capex_zar, _ = eng["get_capex_zar"]()
    _defaults = {
        # PV plant
        "whl_pv_kwp":          float(ss.get("pv_kwp", 4000.0) or 4000.0),
        "whl_spec_yield":      1800.0,            # kWh/kWp/yr (PVGIS can refresh)
        "whl_pv_degradation":  float(ss.get("pv_degradation", 0.5)),
        "whl_capex_per_kwp":   round(pv_capex_zar, 0),
        "whl_opex_per_kwp":    float(ss.get("pv_opex_per_kwp", 125.0)),
        "whl_insurance_pct":   0.5,               # % of CAPEX / yr
        # PPA terms (shared)
        "whl_ppa_price":       1.20,              # ZAR/kWh
        "whl_ppa_escalation":  6.0,               # %/yr
        "whl_contract_years":  20,
        # Wheeling terms (shared)
        "whl_fee_mode":        "Per kWh (ZAR/kWh)",
        "whl_fee_kwh":         0.25,              # ZAR/kWh use-of-system
        "whl_fee_month":       50000.0,           # ZAR/month fixed
        "whl_loss_pct":        3.0,               # network loss %
        "whl_fee_borne_by":    "Developer",
        "whl_loss_borne_by":   "End-user",
        # Finance
        "whl_discount_rate":   float(ss.get("discount_rate", 10.0)),
        "whl_tax_rate":        float(ss.get("tax_rate", 27.0)),
        "whl_cost_escalation": 6.0,               # OPEX / insurance / wheeling CPI
        "whl_grid_escalation": float(ss.get("tariff_escalation", 8.76)),
        "whl_grid_tariff":     0.0,               # 0 → auto-fill from tariff table
    }
    for k, v in _defaults.items():
        ss.setdefault(k, v)
    # Auto-fill blended grid tariff from the BTM Megaflex tariff engine
    if not ss["whl_grid_tariff"]:
        ss["whl_grid_tariff"] = _blended_grid_tariff(eng)
    ss["_whl_initialized"] = True


def _blended_grid_tariff(eng: dict) -> float:
    """Blended daylight (07-17h) weekday grid rate from the BTM TOU tariff
    engine — the rate PPA energy displaces. Same tariff logic as BTM."""
    try:
        days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        tot, wsum = 0.0, 0.0
        for m in range(1, 13):
            for h in range(7, 18):
                rate, _ = eng["get_tariff_for_hour"](h, m, "weekday")
                tot  += rate * days[m - 1]
                wsum += days[m - 1]
        return round(tot / max(wsum, 1), 4)
    except Exception:
        return 2.50


# ─────────────────────────────────────────────────────────────
# Core model — 20-yr PPA/Wheeling cash flows, both perspectives
# (pure function: no streamlit access — unit-testable)
# ─────────────────────────────────────────────────────────────

def _npv_irr(cfs: list[float], disc: float) -> tuple[float, float]:
    """NPV + IRR (bisection) — mirrors BTM compute_npv_irr framework."""
    npv = sum(cf / (1 + disc) ** t for t, cf in enumerate(cfs))
    irr = 0.0
    try:
        lo, hi = -0.5, 5.0
        mid = 0.0
        for _ in range(120):
            mid = (lo + hi) / 2
            pv = sum(cf / (1 + mid) ** t for t, cf in enumerate(cfs))
            if abs(pv) < 0.5:
                break
            if pv > 0:
                lo = mid
            else:
                hi = mid
        irr = mid * 100
    except Exception:
        irr = 0.0
    return round(npv, 0), round(irr, 2)


def run_ppa_models(p: dict) -> dict:
    """
    Run both linked 20-yr models off one shared term sheet.

    p keys: pv_kwp, spec_yield, pv_degradation, capex_per_kwp, opex_per_kwp,
            insurance_pct, ppa_price, ppa_escalation, contract_years,
            fee_mode, fee_kwh, fee_month, loss_pct, fee_borne_by,
            loss_borne_by, discount_rate, tax_rate, cost_escalation,
            grid_escalation, grid_tariff, section_12b, service_fraction
    """
    yrs   = int(p["contract_years"])
    gen1  = p["pv_kwp"] * p["spec_yield"]
    loss  = p["loss_pct"] / 100.0
    deg   = p["pv_degradation"] / 100.0
    p_esc = p["ppa_escalation"] / 100.0
    g_esc = p["grid_escalation"] / 100.0
    c_esc = p["cost_escalation"] / 100.0
    disc  = p["discount_rate"] / 100.0
    tax   = p["tax_rate"] / 100.0

    capex     = p["pv_kwp"] * p["capex_per_kwp"]
    svc_frac  = p.get("service_fraction", 0.40)
    dep_basis = capex * (1.0 - svc_frac)          # equipment portion only (12B)
    sec12b    = p.get("section_12b") or {1: 0.50, 2: 0.30, 3: 0.20}

    dev_rows, usr_rows = [], []
    dev_cfs, usr_cfs   = [-capex], [0.0]
    cum_dev, cum_usr   = -capex, 0.0
    payback = None

    for y in range(1, yrs + 1):
        gen       = gen1 * (1 - deg) ** (y - 1)
        delivered = gen * (1 - loss)
        # Billing point: if end-user bears losses they pay for generated
        # energy (loss share); if developer bears, billing = delivered.
        billed    = gen if p["loss_borne_by"] == "End-user" else delivered
        price     = p["ppa_price"] * (1 + p_esc) ** (y - 1)
        revenue   = price * billed

        if str(p["fee_mode"]).startswith("Per kWh"):
            wheel = delivered * p["fee_kwh"] * (1 + c_esc) ** (y - 1)
        else:
            wheel = p["fee_month"] * 12.0 * (1 + c_esc) ** (y - 1)
        wheel_dev = wheel if p["fee_borne_by"] == "Developer" else 0.0
        wheel_usr = wheel - wheel_dev

        opex = p["pv_kwp"] * p["opex_per_kwp"] * (1 + c_esc) ** (y - 1)
        ins  = capex * p["insurance_pct"] / 100.0 * (1 + c_esc) ** (y - 1)

        # ── Developer / IPP cash flow (BTM 20-yr framework) ─────────────
        ebitda   = revenue - opex - ins - wheel_dev
        dep      = dep_basis * sec12b.get(y, 0.0)
        cash_tax = (ebitda - dep) * tax     # negative in 12B years → tax shield
        ncf      = ebitda - cash_tax
        prev_cum = cum_dev
        cum_dev += ncf
        if payback is None and prev_cum < 0 <= cum_dev:
            payback = round((y - 1) + (-prev_cum) / max(ncf, 1e-9), 2)
        dev_cfs.append(ncf)
        dev_rows.append({
            "Year": y,
            "Generation (kWh)":     round(gen, 0),
            "Delivered (kWh)":      round(delivered, 0),
            "PPA Price (ZAR/kWh)":  round(price, 4),
            "Revenue (ZAR)":        round(revenue, 0),
            "O&M (ZAR)":            round(opex, 0),
            "Insurance (ZAR)":      round(ins, 0),
            "Wheeling (ZAR)":       round(wheel_dev, 0),
            "EBITDA (ZAR)":         round(ebitda, 0),
            "Depreciation (ZAR)":   round(dep, 0),
            "Tax (ZAR)":            round(cash_tax, 0),
            "Net Cash Flow (ZAR)":  round(ncf, 0),
            "Discounted CF (ZAR)":  round(ncf / (1 + disc) ** y, 0),
            "Cumulative CF (ZAR)":  round(cum_dev, 0),
        })

        # ── End-user / Offtaker savings model ───────────────────────────
        grid_rate  = p["grid_tariff"] * (1 + g_esc) ** (y - 1)
        baseline   = delivered * grid_rate          # grid bill avoided (BTM logic)
        loss_share = price * (billed - delivered)   # paid-but-not-received energy
        ppa_energy = revenue - loss_share           # price × delivered
        saving     = baseline - revenue - wheel_usr
        cum_usr   += saving
        usr_cfs.append(saving)
        usr_rows.append({
            "Year": y,
            "Delivered (kWh)":        round(delivered, 0),
            "Grid Rate (ZAR/kWh)":    round(grid_rate, 4),
            "Avoided Grid Cost (ZAR)": round(baseline, 0),
            "PPA Price (ZAR/kWh)":    round(price, 4),
            "PPA Energy Cost (ZAR)":  round(ppa_energy, 0),
            "Loss Share (ZAR)":       round(loss_share, 0),
            "Wheeling (ZAR)":         round(wheel_usr, 0),
            "Net Saving (ZAR)":       round(saving, 0),
            "Discounted Saving (ZAR)": round(saving / (1 + disc) ** y, 0),
            "Cumulative Saving (ZAR)": round(cum_usr, 0),
        })

    dev_df = pd.DataFrame(dev_rows)
    usr_df = pd.DataFrame(usr_rows)
    dev_npv, dev_irr = _npv_irr(dev_cfs, disc)
    usr_npv, _       = _npv_irr(usr_cfs, disc)

    y1 = dev_rows[0]
    u1 = usr_rows[0]
    base1 = max(u1["Avoided Grid Cost (ZAR)"], 1e-9)
    return {
        "dev_df": dev_df,
        "usr_df": usr_df,
        "capex": round(capex, 0),
        "dev_npv": dev_npv,
        "dev_irr": dev_irr,
        "dev_payback": payback,
        "dev_rev_yr1": y1["Revenue (ZAR)"],
        "usr_npv": usr_npv,
        "usr_saving_yr1": u1["Net Saving (ZAR)"],
        "usr_cum_saving": round(cum_usr, 0),
        "usr_discount_pct": round(100.0 * u1["Net Saving (ZAR)"] / base1, 1),
        "gen_yr1": y1["Generation (kWh)"],
        "delivered_yr1": y1["Delivered (kWh)"],
    }


# ─────────────────────────────────────────────────────────────
# Excel report — per perspective (pure function, no streamlit)
# ─────────────────────────────────────────────────────────────

def generate_ppa_excel(perspective: str, p: dict, model: dict,
                       project_name: str = "", client_name: str = "",
                       consultant_name: str = "") -> bytes:
    """3-sheet report (Cover · Cash-flow/Savings · Parameters) styled to
    match the BTM professional Excel report."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.chart import LineChart, BarChart, Reference

    is_dev = perspective == DEV
    df     = model["dev_df"] if is_dev else model["usr_df"]

    C_NAVY, C_DARK, C_LTBLUE, C_ALT = "1F3864", "2E4057", "D6E4F0", "F2F6FC"
    C_GREEN, C_RED = "196F3D", "922B21"
    _thin = Side(style="thin", color="BDBDBD")

    def _fill(c): return PatternFill("solid", fgColor=c)
    def _font(bold=False, sz=10, color="1A1A2E", italic=False):
        return Font(name="Calibri", size=sz, bold=bold, color=color, italic=italic)
    def _align(h="left", v="center", wrap=False):
        return Alignment(horizontal=h, vertical=v, wrap_text=wrap)
    def _bdr(): return Border(left=_thin, right=_thin, top=_thin, bottom=_thin)

    wb  = Workbook()

    # ── Sheet 1: Cover ───────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Cover"
    ws1.sheet_view.showGridLines = False
    for ci, w in enumerate([2, 28, 22, 22, 22, 22, 2], 1):
        ws1.column_dimensions[get_column_letter(ci)].width = w

    ws1.merge_cells("B2:G2")
    c = ws1["B2"]
    c.value = (f"PPA / Wheeling Financial Report — "
               f"{'Developer (IPP)' if is_dev else 'End-user (Offtaker)'} Perspective")
    c.font = Font("Calibri", size=15, bold=True, color="FFFFFF")
    c.fill = _fill(C_NAVY); c.alignment = _align("center")
    ws1.row_dimensions[2].height = 40

    ws1.merge_cells("B3:G3")
    c = ws1["B3"]
    c.value = "Powered by Huawei SA Digital Power · FusionSolar · Grid-Wheeled PPA Model"
    c.font = Font("Calibri", size=9, color="D6E4F0")
    c.fill = _fill(C_NAVY); c.alignment = _align("center")

    ws1.merge_cells("B5:G5")
    c = ws1["B5"]
    c.value = " Project Overview"
    c.font = Font("Calibri", size=10, bold=True, color="FFFFFF")
    c.fill = _fill(C_DARK)
    ws1.row_dimensions[5].height = 20

    _fee_str = (f"{p['fee_kwh']:.4f} ZAR/kWh"
                if str(p["fee_mode"]).startswith("Per kWh")
                else f"{p['fee_month']:,.0f} ZAR/month")
    info_rows = [
        ("Project",            project_name or "PPA Wheeling Project"),
        ("Client Name",        client_name or "—"),
        ("EPC / Consultant",   consultant_name or "—"),
        ("PV Capacity",        f"{p['pv_kwp']:,.0f} kWp"),
        ("Yr-1 Generation",    f"{model['gen_yr1']:,.0f} kWh  "
                               f"(delivered {model['delivered_yr1']:,.0f} kWh)"),
        ("PPA Price",          f"{p['ppa_price']:.4f} ZAR/kWh  "
                               f"(+{p['ppa_escalation']:.1f}%/yr)"),
        ("Contract Term",      f"{int(p['contract_years'])} years"),
        ("Wheeling Fee",       f"{_fee_str}  · borne by {p['fee_borne_by']}"),
        ("Wheeling Loss",      f"{p['loss_pct']:.1f}%  · borne by {p['loss_borne_by']}"),
        ("Grid Ref. Tariff",   f"{p['grid_tariff']:.4f} ZAR/kWh  "
                               f"(+{p['grid_escalation']:.2f}%/yr)"),
        ("Discount Rate",      f"{p['discount_rate']:.1f}%"),
        ("Export Time",        _dt.datetime.now().strftime("%Y-%m-%d  %H:%M")),
    ]
    for i, (lbl, val) in enumerate(info_rows):
        r = 6 + i
        ws1.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
        cl = ws1.cell(row=r, column=2, value=lbl)
        cl.font = _font(bold=True); cl.fill = _fill(C_LTBLUE)
        cl.alignment = _align(); cl.border = _bdr()
        ws1.merge_cells(start_row=r, start_column=4, end_row=r, end_column=6)
        cv = ws1.cell(row=r, column=4, value=val)
        cv.font = _font(); cv.fill = _fill("FFFFFF")
        cv.alignment = _align(); cv.border = _bdr()
        ws1.row_dimensions[r].height = 18

    r0 = 6 + len(info_rows) + 1
    ws1.merge_cells(start_row=r0, start_column=2, end_row=r0, end_column=7)
    c = ws1.cell(row=r0, column=2, value=" Key Financial Metrics")
    c.font = Font("Calibri", size=10, bold=True, color="FFFFFF")
    c.fill = _fill(C_DARK)
    ws1.row_dimensions[r0].height = 20

    if is_dev:
        _pb = f"{model['dev_payback']:.2f} yr" if model["dev_payback"] else \
              f"{int(p['contract_years'])}yr+"
        kpis = [
            ("Total CAPEX",     f"R {model['capex']/1e6:.2f} M"),
            ("NPV",             f"R {model['dev_npv']/1e6:.2f} M"),
            ("Project IRR",     f"{model['dev_irr']:.2f}%"),
            ("Simple Payback",  _pb),
            ("Yr-1 Revenue",    f"R {model['dev_rev_yr1']/1e6:.2f} M"),
        ]
        _kpi_good = model["dev_npv"] > 0
    else:
        kpis = [
            ("Yr-1 Net Saving",       f"R {model['usr_saving_yr1']/1e6:.2f} M"),
            (f"{int(p['contract_years'])}-yr Cumulative Saving",
                                      f"R {model['usr_cum_saving']/1e6:.2f} M"),
            ("NPV of Savings",        f"R {model['usr_npv']/1e6:.2f} M"),
            ("Yr-1 Saving vs Grid",   f"{model['usr_discount_pct']:.1f}%"),
        ]
        _kpi_good = model["usr_cum_saving"] > 0
    for i, (lbl, val) in enumerate(kpis):
        r = r0 + 1 + i
        ws1.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
        cl = ws1.cell(row=r, column=2, value=lbl)
        cl.font = _font(bold=True); cl.fill = _fill(C_LTBLUE)
        cl.alignment = _align(); cl.border = _bdr()
        ws1.merge_cells(start_row=r, start_column=4, end_row=r, end_column=6)
        cv = ws1.cell(row=r, column=4, value=val)
        cv.font = Font("Calibri", size=12, bold=True,
                       color=C_GREEN if _kpi_good else C_RED)
        cv.fill = _fill("FFFFFF"); cv.alignment = _align(); cv.border = _bdr()
        ws1.row_dimensions[r].height = 20

    # ── Sheet 2: 20-yr table + charts ────────────────────────
    ws2 = wb.create_sheet("Cash Flow" if is_dev else "Savings Model")
    ws2.freeze_panes = "A2"
    cols = list(df.columns)
    for ci, hdr in enumerate(cols, 1):
        hc = ws2.cell(row=1, column=ci, value=hdr)
        hc.font = Font("Calibri", size=9, bold=True, color="FFFFFF")
        hc.fill = _fill(C_NAVY); hc.alignment = _align("center", wrap=True)
        hc.border = _bdr()
        ws2.column_dimensions[get_column_letter(ci)].width = max(12, len(hdr) + 2)
    ws2.row_dimensions[1].height = 30
    for ri, rec in enumerate(df.itertuples(index=False), 2):
        for ci, v in enumerate(rec, 1):
            cell = ws2.cell(row=ri, column=ci, value=v)
            cell.font = _font(sz=9)
            cell.fill = _fill(C_ALT if ri % 2 == 0 else "FFFFFF")
            cell.border = _bdr()
            cell.number_format = "#,##0" if ci > 1 else "0"
            cell.alignment = _align("right")

    n = len(df)
    cum_col = cols.index("Cumulative CF (ZAR)" if is_dev
                         else "Cumulative Saving (ZAR)") + 1
    ncf_col = cols.index("Net Cash Flow (ZAR)" if is_dev
                         else "Net Saving (ZAR)") + 1
    cat = Reference(ws2, min_col=1, max_col=1, min_row=2, max_row=n + 1)
    ch1 = LineChart()
    ch1.title = ("Cumulative Cash Flow (ZAR)" if is_dev
                 else "Cumulative Savings (ZAR)")
    ch1.style = 10; ch1.width = 16; ch1.height = 9
    ch1.add_data(Reference(ws2, min_col=cum_col, max_col=cum_col,
                           min_row=1, max_row=n + 1), titles_from_data=True)
    ch1.set_categories(cat)
    ws2.add_chart(ch1, f"{get_column_letter(len(cols) + 2)}2")
    ch2 = BarChart()
    ch2.type = "col"
    ch2.title = ("Annual Net Cash Flow (ZAR)" if is_dev
                 else "Annual Net Saving (ZAR)")
    ch2.style = 10; ch2.width = 16; ch2.height = 9
    ch2.add_data(Reference(ws2, min_col=ncf_col, max_col=ncf_col,
                           min_row=1, max_row=n + 1), titles_from_data=True)
    ch2.set_categories(cat)
    ws2.add_chart(ch2, f"{get_column_letter(len(cols) + 2)}22")

    # ── Sheet 3: Parameters ──────────────────────────────────
    ws3 = wb.create_sheet("Parameters")
    ws3.sheet_view.showGridLines = False
    for ci, w in enumerate([3, 34, 18, 16], 1):
        ws3.column_dimensions[get_column_letter(ci)].width = w
    prm = [
        ("PV Capacity",              p["pv_kwp"],          "kWp"),
        ("Specific Yield (Yr-1)",    p["spec_yield"],      "kWh/kWp/yr"),
        ("PV Degradation",           p["pv_degradation"],  "%/yr"),
        ("CAPEX",                    p["capex_per_kwp"],   "ZAR/kWp"),
        ("O&M",                      p["opex_per_kwp"],    "ZAR/kWp/yr"),
        ("Insurance",                p["insurance_pct"],   "% CAPEX/yr"),
        ("PPA Price (Yr-1)",         p["ppa_price"],       "ZAR/kWh"),
        ("PPA Escalation",           p["ppa_escalation"],  "%/yr"),
        ("Contract Term",            p["contract_years"],  "years"),
        ("Wheeling Fee Mode",        p["fee_mode"],        ""),
        ("Wheeling Fee (per kWh)",   p["fee_kwh"],         "ZAR/kWh"),
        ("Wheeling Fee (fixed)",     p["fee_month"],       "ZAR/month"),
        ("Wheeling Loss",            p["loss_pct"],        "%"),
        ("Wheeling Fee Borne By",    p["fee_borne_by"],    ""),
        ("Loss Borne By",            p["loss_borne_by"],   ""),
        ("Grid Reference Tariff",    p["grid_tariff"],     "ZAR/kWh"),
        ("Grid Tariff Escalation",   p["grid_escalation"], "%/yr"),
        ("Cost Escalation (CPI)",    p["cost_escalation"], "%/yr"),
        ("Discount Rate",            p["discount_rate"],   "%"),
        ("Tax Rate",                 p["tax_rate"],        "%"),
    ]
    ws3.merge_cells("B1:D1")
    c = ws3.cell(row=1, column=2, value="PPA / Wheeling — Shared Term Sheet & Assumptions")
    c.font = Font("Calibri", size=12, bold=True, color="FFFFFF")
    c.fill = _fill(C_NAVY); c.alignment = _align("center")
    ws3.row_dimensions[1].height = 28
    for i, (lbl, val, unit) in enumerate(prm):
        r = 3 + i
        lb = ws3.cell(row=r, column=2, value=lbl)
        lb.font = _font(); lb.fill = _fill(C_ALT)
        lb.alignment = _align(); lb.border = _bdr()
        vc = ws3.cell(row=r, column=3, value=val)
        vc.alignment = _align("center"); vc.border = _bdr()
        un = ws3.cell(row=r, column=4, value=unit)
        un.font = _font(sz=9, italic=True, color="666666")
        un.fill = _fill(C_ALT); un.alignment = _align(); un.border = _bdr()
        ws3.row_dimensions[r].height = 17

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────

def _kpi(label: str, value: str, sub: str = "") -> None:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-unit">{sub}</div></div>',
        unsafe_allow_html=True)


def _params_dict() -> dict:
    ss = st.session_state
    return {
        "pv_kwp":          ss.whl_pv_kwp,
        "spec_yield":      ss.whl_spec_yield,
        "pv_degradation":  ss.whl_pv_degradation,
        "capex_per_kwp":   ss.whl_capex_per_kwp,
        "opex_per_kwp":    ss.whl_opex_per_kwp,
        "insurance_pct":   ss.whl_insurance_pct,
        "ppa_price":       ss.whl_ppa_price,
        "ppa_escalation":  ss.whl_ppa_escalation,
        "contract_years":  ss.whl_contract_years,
        "fee_mode":        ss.whl_fee_mode,
        "fee_kwh":         ss.whl_fee_kwh,
        "fee_month":       ss.whl_fee_month,
        "loss_pct":        ss.whl_loss_pct,
        "fee_borne_by":    ss.whl_fee_borne_by,
        "loss_borne_by":   ss.whl_loss_borne_by,
        "discount_rate":   ss.whl_discount_rate,
        "tax_rate":        ss.whl_tax_rate,
        "cost_escalation": ss.whl_cost_escalation,
        "grid_escalation": ss.whl_grid_escalation,
        "grid_tariff":     ss.whl_grid_tariff,
    }


def render_ppa_wheeling(eng: dict) -> None:
    """Scenario-2 main page. `eng` = BTM engine functions injected by app.py."""
    _init_state(eng)
    ss  = st.session_state
    fmw = eng["fmw"]

    # ── Header ───────────────────────────────────────────────
    _b, _h, _x = st.columns([1.8, 6.2, 2], gap="small")
    with _b:
        if st.button("◀ Back to Scenarios", key="whl_back_btn2",
                     use_container_width=True):
            ss.pop("_scenario", None)
            st.rerun()
    with _h:
        st.markdown("""
<div class="main-header">
    <div style="font-size:1.8rem;line-height:1">🔄</div>
    <div>
        <div class="main-title">PPA / Wheeling Financial Model</div>
        <div class="sub-title">GRID-WHEELED PPA &nbsp;·&nbsp; DEVELOPER + OFFTAKER DUAL VIEW &nbsp;·&nbsp; BTM 20-YR ENGINE</div>
    </div>
</div>""", unsafe_allow_html=True)

    col_main, col_prm = st.columns([7, 3], gap="large")

    # ── Right: shared parameter panel ────────────────────────
    with col_prm:
        _scroll = st.container(height=860, border=False)
    with _scroll:
        with st.expander("☀️ PV Plant & Generation", expanded=True):
            st.number_input("PV Capacity (kWp)", 0.0, 1e6,
                            key="whl_pv_kwp", step=100.0)
            st.number_input("Specific Yield Yr-1 (kWh/kWp)", 500.0, 3000.0,
                            key="whl_spec_yield", step=10.0)
            if st.button("↻ Fetch yield from PVGIS", key="whl_pvgis_btn",
                         use_container_width=True,
                         help="Uses BTM site location (lat/lon, tilt, azimuth)"):
                try:
                    pvg = eng["get_pvgis_data"](
                        ss.get("lat", -26.1), ss.get("lon", 28.0),
                        ss.whl_pv_kwp, ss.get("pv_loss", 14.0),
                        ss.get("tilt", 26.0), ss.get("azimuth", 180.0))
                    _akwh = float(pvg.get("annual_kwh", 0) or 0)
                    if _akwh > 0 and ss.whl_pv_kwp > 0:
                        ss.whl_spec_yield = round(_akwh / ss.whl_pv_kwp, 1)
                        st.rerun()
                    else:
                        st.warning("PVGIS returned no data — kept manual yield.")
                except Exception as _e:
                    st.warning(f"PVGIS unavailable: {_e}")
            st.number_input("PV Degradation (%/yr)", 0.0, 3.0,
                            key="whl_pv_degradation", step=0.1)
            st.markdown(
                f'<div class="derived-value">☀️ Yr-1 Gen: '
                f'{fmw(ss.whl_pv_kwp * ss.whl_spec_yield, "kWh/yr")}</div>',
                unsafe_allow_html=True)

        with st.expander("📜 PPA Terms (shared)", expanded=True):
            st.number_input("PPA Price (ZAR/kWh)", 0.0, 20.0,
                            key="whl_ppa_price", step=0.01, format="%.4f")
            st.number_input("PPA Escalation (%/yr)", 0.0, 25.0,
                            key="whl_ppa_escalation", step=0.25)
            st.number_input("Contract Term (years)", 1, 25,
                            key="whl_contract_years", step=1)

        with st.expander("🔌 Wheeling Terms (shared)", expanded=True):
            st.selectbox("Use-of-System Fee Basis",
                         ["Per kWh (ZAR/kWh)", "Fixed (ZAR/month)"],
                         key="whl_fee_mode")
            if str(ss.whl_fee_mode).startswith("Per kWh"):
                st.number_input("Wheeling Fee (ZAR/kWh)", 0.0, 5.0,
                                key="whl_fee_kwh", step=0.01, format="%.4f")
            else:
                st.number_input("Wheeling Fee (ZAR/month)", 0.0, 1e7,
                                key="whl_fee_month", step=1000.0)
            st.number_input("Wheeling Loss (%)", 0.0, 15.0,
                            key="whl_loss_pct", step=0.1)
            st.selectbox("Wheeling Fee Borne By",
                         ["Developer", "End-user"], key="whl_fee_borne_by")
            st.selectbox("Network Loss Borne By",
                         ["End-user", "Developer"], key="whl_loss_borne_by",
                         help="End-user → billed on generated energy (pays loss "
                              "share). Developer → billed on delivered energy.")

        with st.expander("💰 Developer Costs", expanded=False):
            st.number_input("CAPEX (ZAR/kWp)", 0.0, 1e5,
                            key="whl_capex_per_kwp", step=100.0)
            st.number_input("O&M (ZAR/kWp/yr)", 0.0, 2000.0,
                            key="whl_opex_per_kwp", step=5.0)
            st.number_input("Insurance (% CAPEX/yr)", 0.0, 5.0,
                            key="whl_insurance_pct", step=0.1)

        with st.expander("🏦 Finance & Grid Baseline", expanded=False):
            st.number_input("Grid Reference Tariff (ZAR/kWh)", 0.0, 20.0,
                            key="whl_grid_tariff", step=0.05, format="%.4f",
                            help="Blended daylight grid rate the wheeled energy "
                                 "displaces — auto-seeded from the BTM Megaflex "
                                 "tariff table")
            if st.button("↻ Re-blend from tariff table", key="whl_blend_btn",
                         use_container_width=True):
                ss.whl_grid_tariff = _blended_grid_tariff(eng)
                st.rerun()
            st.number_input("Grid Tariff Escalation (%/yr)", 0.0, 25.0,
                            key="whl_grid_escalation", step=0.25)
            st.number_input("Cost Escalation CPI (%/yr)", 0.0, 25.0,
                            key="whl_cost_escalation", step=0.25)
            st.number_input("Discount Rate (%)", 0.0, 30.0,
                            key="whl_discount_rate", step=0.5)
            st.number_input("Tax Rate (%)", 0.0, 50.0,
                            key="whl_tax_rate", step=1.0)

    # ── Model run (cheap — every rerun) ──────────────────────
    p     = _params_dict()
    p["section_12b"] = eng["SECTION_12B"]
    model = run_ppa_models(p)
    ss["_whl_model"] = model

    # ── Left: dual-perspective tabs ──────────────────────────
    with col_main:
        tab_dev, tab_usr, tab_rpt = st.tabs(
            ["🏗 Developer / IPP", "🏭 End-user / Offtaker", "📁 Reports"])

        import plotly.graph_objects as go

        def _chart(df, bar_col, line_col, title):
            fig = go.Figure()
            fig.add_bar(x=df["Year"], y=df[bar_col], name=bar_col,
                        marker_color="#4ECDC4")
            fig.add_scatter(x=df["Year"], y=df[line_col], name=line_col,
                            mode="lines+markers", line=dict(color="#00E5A0"),
                            yaxis="y2")
            _dark = not st.session_state.get("_light_mode", False)
            fig.update_layout(
                title=title, height=380,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E8ECF0" if _dark else "#1A202C",
                          family="IBM Plex Mono"),
                yaxis=dict(title="ZAR/yr"),
                yaxis2=dict(title="Cumulative ZAR", overlaying="y", side="right"),
                legend=dict(orientation="h", y=-0.2),
                margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig, use_container_width=True)

        # ── Developer tab ────────────────────────────────────
        with tab_dev:
            _pb_str = (f"{model['dev_payback']:.2f} yr" if model["dev_payback"]
                       else f"{int(p['contract_years'])}yr+")
            k1, k2, k3, k4, k5 = st.columns(5)
            with k1: _kpi("TOTAL CAPEX",  f"R {model['capex']/1e6:.2f}M", "ZAR")
            with k2: _kpi("NPV",          f"R {model['dev_npv']/1e6:.2f}M",
                          f"@ {p['discount_rate']:.1f}%")
            with k3: _kpi("PROJECT IRR",  f"{model['dev_irr']:.2f}%", "after-tax")
            with k4: _kpi("PAYBACK",      _pb_str, "simple")
            with k5: _kpi("YR-1 REVENUE", f"R {model['dev_rev_yr1']/1e6:.2f}M",
                          "PPA sales")
            _chart(model["dev_df"], "Net Cash Flow (ZAR)",
                   "Cumulative CF (ZAR)",
                   f"Developer — {int(p['contract_years'])}-Year Cash Flow")
            st.dataframe(model["dev_df"], use_container_width=True,
                         hide_index=True, height=420)
            st.caption(
                f"Revenue = PPA price × "
                f"{'generated' if p['loss_borne_by'] == 'End-user' else 'delivered'} "
                f"energy · Costs = CAPEX / O&M / insurance"
                f"{' / wheeling fee' if p['fee_borne_by'] == 'Developer' else ''}"
                f" · Section 12B depreciation (50/30/20, equipment portion) · "
                f"Tax {p['tax_rate']:.0f}%")

        # ── End-user tab ─────────────────────────────────────
        with tab_usr:
            j1, j2, j3, j4 = st.columns(4)
            with j1: _kpi("YR-1 NET SAVING",
                          f"R {model['usr_saving_yr1']/1e6:.2f}M", "vs grid bill")
            with j2: _kpi(f"{int(p['contract_years'])}-YR CUM. SAVING",
                          f"R {model['usr_cum_saving']/1e6:.2f}M", "nominal")
            with j3: _kpi("NPV OF SAVINGS",
                          f"R {model['usr_npv']/1e6:.2f}M",
                          f"@ {p['discount_rate']:.1f}%")
            with j4: _kpi("YR-1 SAVING RATE",
                          f"{model['usr_discount_pct']:.1f}%", "of avoided cost")
            _chart(model["usr_df"], "Net Saving (ZAR)",
                   "Cumulative Saving (ZAR)",
                   f"End-user — {int(p['contract_years'])}-Year Cumulative Savings")
            st.dataframe(model["usr_df"], use_container_width=True,
                         hide_index=True, height=420)
            st.caption(
                "Saving = avoided grid cost (BTM tariff logic, "
                f"+{p['grid_escalation']:.2f}%/yr) − PPA energy cost − "
                f"{'loss share − ' if p['loss_borne_by'] == 'End-user' else ''}"
                f"{'wheeling fee' if p['fee_borne_by'] == 'End-user' else 'wheeling (borne by developer)'}")

        # ── Reports tab ──────────────────────────────────────
        with tab_rpt:
            st.markdown('<div class="section-header">📊 Financial Reports — per perspective</div>',
                        unsafe_allow_html=True)
            rc1, rc2 = st.columns(2)
            with rc1:
                st.text_input("EPC / Consultant",
                              value=ss.get("_pptx_consultant", ""),
                              placeholder="e.g. Lanxi Engineering",
                              key="_pptx_consultant")
            with rc2:
                st.text_input("Client Name",
                              value=ss.get("_pptx_client_name", ""),
                              placeholder="e.g. Lanxi Mining Company",
                              key="_pptx_client_name")
            _proj = ss.get("_active_snap_name") or "PPA_Wheeling_Project"
            _proj_safe = re.sub(r"[^\w\-]", "_", _proj).strip("_")
            _today = _dt.datetime.now().strftime("%Y%m%d")

            for _persp, _tag in ((DEV, "Developer"), (USR, "EndUser")):
                st.markdown(f"##### {'🏗' if _persp == DEV else '🏭'} {_persp}")
                b1, b2 = st.columns(2)
                with b1:
                    try:
                        _xb = generate_ppa_excel(
                            _persp, p, model,
                            project_name=_proj,
                            client_name=ss.get("_pptx_client_name", ""),
                            consultant_name=ss.get("_pptx_consultant", ""))
                        st.download_button(
                            f"⬇ Excel — {_tag} Report", data=_xb,
                            file_name=f"{_proj_safe}_PPA_{_tag}_{_today}.xlsx",
                            mime=("application/vnd.openxmlformats-officedocument"
                                  ".spreadsheetml.sheet"),
                            use_container_width=True,
                            key=f"whl_xl_{_tag}")
                    except Exception as _e:
                        st.error(f"Excel failed: {_e}")
                with b2:
                    if st.button(f"📊 Build PPTX — {_tag} Report",
                                 key=f"whl_pp_btn_{_tag}",
                                 use_container_width=True):
                        with st.spinner("Building PPTX…"):
                            try:
                                from report_pptx import generate_ppa_pptx
                                ss[f"_whl_pptx_{_tag}"] = generate_ppa_pptx(
                                    perspective=_persp, p=p, model=model,
                                    project_name=_proj,
                                    client_name=ss.get("_pptx_client_name", ""),
                                    consultant_name=ss.get("_pptx_consultant", ""))
                            except Exception as _e:
                                st.error(f"PPTX failed: {_e}")
                    if ss.get(f"_whl_pptx_{_tag}"):
                        st.download_button(
                            f"⬇ Download PPTX — {_tag}",
                            data=ss[f"_whl_pptx_{_tag}"],
                            file_name=f"{_proj_safe}_PPA_{_tag}_{_today}.pptx",
                            mime=("application/vnd.openxmlformats-officedocument"
                                  ".presentationml.presentation"),
                            use_container_width=True,
                            key=f"whl_pp_dl_{_tag}")
            st.caption("Both reports share one PPA / Wheeling term sheet — "
                       "developer revenue and end-user PPA cost are two sides "
                       "of the same contracted energy flows.")
