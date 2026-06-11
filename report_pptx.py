"""
report_pptx.py — Professional PPTX Report Generator
BTM PV+BESS Financial Modelling System
GreenWatt Consulting · greenwattconsulting.co.za

7 slides:
  1. Cover
  2. Executive Summary  (5 metric cards)
  3. System Configuration (PV + BESS specs)
  4. Financial Analysis   (20-year cash flow chart)
  5. Energy Analysis      (monthly generation chart + table)
  6. Tariff & Savings
  7. Assumptions & Disclaimer
"""
from __future__ import annotations

import io
from datetime import date
from typing import Any

# ── Colour palette ────────────────────────────────────────────────────────────
_NAV  = "0D1B2A"   # dark navy  (cover / sidebar background)
_MNV  = "1A3A5C"   # mid-navy   (card header strips)
_DNV  = "112233"   # deep navy  (system-size callout)
_SEP  = "2A3F55"   # separator lines / subtle dividers
_GRN  = "00E5A0"   # brand green accent
_WHT  = "FFFFFF"   # white
_LGY  = "F4F6F9"   # light grey slide background
_DGY  = "6E7681"   # dim grey label text
_TXT  = "1A1A2E"   # near-black body text
_RED  = "E74C3C"   # negative values

# ── python-pptx low-level helpers ─────────────────────────────────────────────

def _rgb(hex6: str):
    from pptx.dml.color import RGBColor
    h = hex6.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _in(v: float):
    from pptx.util import Inches
    return Inches(v)


def _pt(v: float):
    from pptx.util import Pt
    return Pt(v)


def _fill(shape, hex6: str):
    shape.fill.solid()
    shape.fill.fore_color.rgb = _rgb(hex6)


def _no_line(shape):
    shape.line.fill.background()


def _add_rect(slide, x: float, y: float, w: float, h: float,
              fill: str, line: str | None = None):
    """Add a filled rectangle; coords/sizes in inches."""
    shp = slide.shapes.add_shape(1, _in(x), _in(y), _in(w), _in(h))
    _fill(shp, fill)
    if line:
        from pptx.util import Pt
        shp.line.color.rgb = _rgb(line)
        shp.line.width = Pt(0.75)
    else:
        _no_line(shp)
    return shp


def _add_tb(slide, x: float, y: float, w: float, h: float,
            text: str, size: float,
            bold: bool = False,
            color: str = _TXT,
            align: str = "left",
            wrap: bool = True) -> Any:
    """Add a text-box with a single paragraph."""
    from pptx.enum.text import PP_ALIGN
    _align_map = {
        "left":   PP_ALIGN.LEFT,
        "center": PP_ALIGN.CENTER,
        "right":  PP_ALIGN.RIGHT,
    }
    tb = slide.shapes.add_textbox(_in(x), _in(y), _in(w), _in(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = _pt(0)
    para = tf.paragraphs[0]
    para.alignment = _align_map.get(align, PP_ALIGN.LEFT)
    run = para.add_run()
    run.text = text
    run.font.size = _pt(size)
    run.font.bold = bold
    run.font.color.rgb = _rgb(color)
    return tb


def _metric_card(slide, x: float, y: float,
                 label: str, value: str, unit: str = "",
                 accent: str = _GRN) -> None:
    """Dark metric card: accent bar | label / big-number / unit."""
    W, H = 2.7, 1.55
    _add_rect(slide, x,       y,     W,    H,    _NAV)
    _add_rect(slide, x,       y,     0.07, H,    accent)   # left accent strip
    _add_tb(slide, x + 0.15, y + 0.12, W - 0.2, 0.35, label, 9,  color=_DGY)
    _add_tb(slide, x + 0.15, y + 0.48, W - 0.2, 0.65, value, 27, bold=True, color=accent)
    if unit:
        _add_tb(slide, x + 0.15, y + 1.17, W - 0.2, 0.3, unit, 8, color=_DGY)


def _footer(slide) -> None:
    _add_tb(slide, 0.4, 7.05, 12.5, 0.32,
            "GreenWatt Consulting  ·  BTM PV+BESS Analysis  ·  CONFIDENTIAL",
            8, color=_DGY, align="center")


# ── Chart generators (matplotlib, graceful fallback) ─────────────────────────

def _cashflow_png(fin_df) -> bytes | None:
    """20-year bar + cumulative line chart → PNG bytes."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        years = fin_df["Year"].tolist()
        ncf   = fin_df["Net Cash Flow NCF (ZAR)"].values / 1e6
        cum   = fin_df["Cumulative CF (ZAR)"].values / 1e6

        fig, ax1 = plt.subplots(figsize=(9, 3.3), facecolor="white")
        ax1.set_facecolor("white")
        colors = ["#00E5A0" if v >= 0 else "#E74C3C" for v in ncf]
        ax1.bar(years, ncf, color=colors, alpha=0.85, width=0.65, zorder=3)
        ax1.axhline(0, color="#cccccc", linewidth=0.8)
        ax1.set_xlabel("Year", fontsize=9, color="#555")
        ax1.set_ylabel("Annual NCF  (R million)", fontsize=9, color="#555")
        ax1.tick_params(labelsize=8, colors="#555")
        ax1.spines[["top", "right"]].set_visible(False)
        ax1.spines[["left", "bottom"]].set_color("#ddd")
        ax1.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

        ax2 = ax1.twinx()
        ax2.plot(years, cum, color="#0D1B2A", linewidth=2,
                 marker="o", markersize=3, zorder=5, label="Cumulative")
        ax2.set_ylabel("Cumulative  (R million)", fontsize=9, color="#0D1B2A")
        ax2.tick_params(labelsize=8, colors="#0D1B2A")
        ax2.spines[["top"]].set_visible(False)

        plt.tight_layout(pad=0.4)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception:
        return None


def _monthly_gen_png(pvgis_data: dict) -> bytes | None:
    """Monthly PV generation bar chart → PNG bytes."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        months  = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        monthly = pvgis_data.get("monthly_kwh", [0] * 12)

        fig, ax = plt.subplots(figsize=(9, 2.9), facecolor="white")
        ax.set_facecolor("white")
        # colour winter months differently
        bar_colors = ["#1A6B5C" if i in (5, 6, 7) else "#00E5A0" for i in range(12)]
        ax.bar(months, monthly, color=bar_colors, alpha=0.9, width=0.65, zorder=3)
        ax.set_ylabel("kWh / month", fontsize=9, color="#555")
        ax.tick_params(labelsize=8, colors="#555")
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color("#ddd")
        ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

        # Annotate winter
        ax.axvspan(4.5, 7.5, color="#1A3A5C", alpha=0.08, zorder=0)
        ax.text(6.0, max(monthly) * 0.94, "Winter\n(High tariff)",
                ha="center", va="top", fontsize=7, color="#558")

        plt.tight_layout(pad=0.4)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception:
        return None


# ── Slide builders ────────────────────────────────────────────────────────────

def _slide_cover(prs, project_name: str, client_name: str,
                 pv_kwp: float, bess_kwh: float, tariff_mode: str) -> None:
    """Slide 1 – dark cover."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Background
    _add_rect(slide, 0, 0, 13.33, 7.5, _NAV)
    # Left accent strip
    _add_rect(slide, 0, 0, 0.12, 7.5, _GRN)

    # Brand
    _add_tb(slide, 0.45, 0.38, 7, 0.55,
            "GreenWatt Consulting", 18, bold=True, color=_GRN)
    _add_tb(slide, 0.45, 0.93, 7, 0.38,
            "BTM PV+BESS Financial Analysis Report", 11, color="8899AA")
    # Separator
    _add_rect(slide, 0.45, 1.42, 12.33, 0.025, _SEP)

    # Title
    title = project_name or f"{pv_kwp:.0f} kWp PV + {bess_kwh:.0f} kWh BESS"
    _add_tb(slide, 0.45, 1.65, 12, 1.2,
            title, 38, bold=True, color=_WHT)

    # Client + date
    if client_name:
        _add_tb(slide, 0.45, 2.95, 9, 0.45,
                f"Client:  {client_name}", 13, color="8899AA")
    _add_tb(slide, 0.45, 3.42, 9, 0.40,
            f"Report Date:  {date.today().strftime('%B %Y')}", 12, color="8899AA")

    # Tariff badge
    if tariff_mode:
        _add_rect(slide, 0.45, 4.05, 4.2, 0.45, _MNV)
        _add_tb(slide, 0.60, 4.12, 4.0, 0.32,
                f"⚡  {tariff_mode}", 10, color=_GRN)

    # System size callout (right)
    _add_rect(slide, 9.6, 1.75, 3.2, 2.1, _DNV)
    _add_tb(slide, 9.75, 1.87, 2.9, 0.35,
            "SYSTEM SIZE", 9, bold=True, color=_GRN, align="center")
    _add_tb(slide, 9.75, 2.22, 2.9, 0.75,
            f"{pv_kwp:,.0f} kWp", 34, bold=True, color=_WHT, align="center")
    _add_rect(slide, 9.75, 2.97, 2.9, 0.025, _SEP)
    _add_tb(slide, 9.75, 3.02, 2.9, 0.55,
            f"+ {bess_kwh:,.0f} kWh\nBESS", 14, color="8899AA", align="center")

    # Footer
    _add_tb(slide, 0.45, 7.05, 12.33, 0.32,
            "CONFIDENTIAL  ·  For client use only  ·  greenwattconsulting.co.za",
            8, color="445566", align="center")


def _slide_exec_summary(prs, results: dict) -> None:
    """Slide 2 – Executive Summary."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_rect(slide, 0, 0, 13.33, 7.5, _LGY)
    _add_rect(slide, 0, 0, 13.33, 0.88, _NAV)
    _add_tb(slide, 0.45, 0.20, 10, 0.52,
            "Executive Summary", 22, bold=True, color=_WHT)

    npv     = results.get("npv", 0) or 0
    irr     = results.get("irr", 0) or 0
    payback = results.get("payback") or 0
    capex   = results.get("total_capex", 0) or 0
    lcoe_d  = results.get("lcoe") or {}
    lcoe    = lcoe_d.get("lcoe_zar_kwh", 0) or 0
    avoided = lcoe_d.get("total_avoided_mwh", 0) or 0
    d1      = results.get("dispatch_yr1") or {}
    ann_sav = d1.get("annual_savings_zar", 0) or 0

    def _m(v):
        return f"R {abs(v)/1e6:.2f}M" if abs(v) >= 1e6 else f"R {abs(v)/1e3:.0f}k"

    # Row 1 – 4 cards
    for i, (lbl, val, unit) in enumerate([
        ("TOTAL CAPEX",     _m(capex),          "Capital expenditure"),
        ("20-yr NPV",       _m(npv),             "Net present value (after tax)"),
        ("Project IRR",     f"{irr:.1f}%",       "Internal rate of return"),
        ("Simple Payback",  f"{payback:.1f} yr", "Years to positive cash flow"),
    ]):
        _metric_card(slide, 0.45 + i * 2.9, 1.05, lbl, val, unit)

    # Row 2 – LCOE + summary text block
    _metric_card(slide, 0.45, 2.78, "1ST YR LCOE",
                 f"R {lcoe:.2f}/kWh", f"{avoided:,.0f} MWh lifetime avoided")
    if ann_sav:
        _metric_card(slide, 3.35, 2.78, "YR-1 GRID SAVINGS",
                     _m(ann_sav), "Avoided grid purchase cost")

    # Right summary panel
    _add_rect(slide, 6.75, 2.78, 6.1, 3.6, _NAV)
    _add_tb(slide, 6.95, 2.95, 5.7, 0.40,
            "At a Glance", 13, bold=True, color=_GRN)

    lines = [
        ("CAPEX",           _m(capex)),
        ("20-year NPV",     _m(npv) + (" ✓" if npv > 0 else " ✗")),
        ("IRR",             f"{irr:.1f}%"),
        ("Break-even",      f"Year {payback:.1f}"),
        ("1st yr LCOE",     f"R {lcoe:.2f}/kWh"),
        ("Lifetime avoided",f"{avoided:,.0f} MWh"),
    ]
    from pptx.util import Pt
    from pptx.enum.text import PP_ALIGN
    txb = slide.shapes.add_textbox(_in(6.95), _in(3.45), _in(5.7), _in(2.7))
    tf  = txb.text_frame
    tf.word_wrap = True
    for j, (k, v) in enumerate(lines):
        para = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
        for chunk, clr, is_bold in [(f"{k}:  ", _DGY, False), (v, _WHT, True)]:
            run = para.add_run()
            run.text = chunk
            run.font.size = Pt(10.5)
            run.font.bold = is_bold
            run.font.color.rgb = _rgb(clr)
        para.space_after = Pt(4)

    _footer(slide)


def _slide_system_config(prs, params: dict, pvgis_data: dict) -> None:
    """Slide 3 – System Configuration."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_rect(slide, 0, 0, 13.33, 7.5, _LGY)
    _add_rect(slide, 0, 0, 13.33, 0.88, _NAV)
    _add_tb(slide, 0.45, 0.20, 10, 0.52,
            "System Configuration", 22, bold=True, color=_WHT)

    def _spec_card(title: str, icon: str, rows: list[tuple[str, str]],
                   x: float) -> None:
        W = 5.9
        _add_rect(slide, x, 1.0, W, 5.65, _NAV)
        _add_rect(slide, x, 1.0, W, 0.52, _MNV)
        _add_tb(slide, x + 0.18, 1.07, W - 0.3, 0.37,
                f"{icon}  {title}", 13, bold=True, color=_GRN)
        for i, (lbl, val) in enumerate(rows):
            yy = 1.65 + i * 0.58
            _add_tb(slide, x + 0.18, yy, 2.8, 0.42, lbl, 10, color=_DGY)
            _add_tb(slide, x + 3.0,  yy, W - 3.2, 0.42,
                    val, 11, bold=True, color=_WHT, align="right")
            if i < len(rows) - 1:
                _add_rect(slide, x + 0.18, yy + 0.46, W - 0.36, 0.01, _SEP)

    pv_rows = [
        ("Peak Power",        f"{params.get('pv_kwp', 0):,.0f} kWp"),
        ("System Loss",       f"{params.get('pv_loss', 14):.0f}%"),
        ("Tilt",              f"{params.get('tilt', 20):.0f}°"),
        ("Azimuth",           f"{params.get('azimuth', 180):.0f}°  (N=0°)"),
        ("Annual Generation", f"{pvgis_data.get('annual_kwh', 0):,.0f} kWh/yr"),
        ("Summer Daily",      f"{pvgis_data.get('summer_daily_kwh', 0):.1f} kWh/day"),
        ("Winter Daily",      f"{pvgis_data.get('winter_daily_kwh', 0):.1f} kWh/day"),
        ("Degradation",       f"{params.get('pv_degradation', 0.5):.1f}%/yr"),
    ]
    _spec_card("PV ARRAY", "☀", pv_rows, 0.45)

    c_rate = params.get("c_rate", 0.25)
    bess_kw = params.get("bess_kwh", 0) * c_rate
    bess_rows = [
        ("Capacity",      f"{params.get('bess_kwh', 0):,.0f} kWh"),
        ("Max Power",     f"{bess_kw:,.0f} kW  ({params.get('c_rate_label','0.25C')})"),
        ("Depth of Discharge", f"{params.get('dod', 90):.0f}%"),
        ("Round-trip η",  f"{params.get('rte', 90):.0f}%"),
        ("Cycle Life",    f"{params.get('bess_cycles', 365):.0f} cycles/yr"),
        ("Tariff Mode",   (params.get("tariff_mode", "—")[:26] + "…")
                          if len(params.get("tariff_mode", "")) > 26
                          else params.get("tariff_mode", "—")),
        ("Site Lat / Lon", f"{params.get('lat', 0):.3f}°, {params.get('lon', 0):.3f}°"),
        ("Analysis Period","20 years"),
    ]
    _spec_card("BATTERY STORAGE", "🔋", bess_rows, 7.0)

    _footer(slide)


def _slide_financial(prs, results: dict, fin_df) -> None:
    """Slide 4 – Financial Analysis with cash flow chart."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_rect(slide, 0, 0, 13.33, 7.5, _LGY)
    _add_rect(slide, 0, 0, 13.33, 0.88, _NAV)
    _add_tb(slide, 0.45, 0.20, 10, 0.52,
            "Financial Analysis  —  20-Year Projection", 22, bold=True, color=_WHT)

    # Cash flow chart (left 9")
    chart_png = _cashflow_png(fin_df) if fin_df is not None else None
    if chart_png:
        slide.shapes.add_picture(
            io.BytesIO(chart_png), _in(0.45), _in(1.0), _in(8.7), _in(3.85))
    else:
        _add_rect(slide, 0.45, 1.0, 8.7, 3.85, _NAV)
        _add_tb(slide, 0.65, 2.6, 8.3, 0.5,
                "Run simulation to generate cash flow chart", 11, color=_DGY, align="center")

    # Caption
    _add_tb(slide, 0.45, 4.95, 8.7, 0.32,
            "Green = positive NCF · Red = negative NCF · Line = cumulative cash flow",
            8, color=_DGY, align="center")

    # Right sidebar
    _add_rect(slide, 9.55, 1.0, 3.35, 5.6, _NAV)
    _add_tb(slide, 9.72, 1.1, 3.0, 0.38,
            "KEY METRICS", 11, bold=True, color=_GRN)

    capex   = results.get("total_capex", 0) or 0
    npv     = results.get("npv", 0) or 0
    irr     = results.get("irr", 0) or 0
    payback = results.get("payback") or 0
    lcoe    = (results.get("lcoe") or {}).get("lcoe_zar_kwh", 0) or 0
    disc    = results.get("discount_rate", 12)

    def _m(v): return f"R{abs(v)/1e6:.2f}M"

    sidebar_rows = [
        ("CAPEX",           _m(capex)),
        ("NPV (20yr)",      _m(npv)),
        ("IRR",             f"{irr:.1f}%"),
        ("Payback",         f"{payback:.1f} yr"),
        ("1st yr LCOE",     f"R{lcoe:.2f}/kWh"),
        ("Discount Rate",   f"{disc:.1f}%"),
        ("Section 12B",     "150% (Yr 1)"),
        ("Tax (CIT)",       f"{results.get('tax_rate', 27):.0f}%"),
    ]
    for i, (k, v) in enumerate(sidebar_rows):
        yy = 1.6 + i * 0.57
        _add_tb(slide, 9.72, yy,      2.0,  0.42, k, 9,  color=_DGY)
        _add_tb(slide, 11.65, yy, 1.1, 0.42, v, 10, bold=True, color=_WHT, align="right")
        if i < len(sidebar_rows) - 1:
            _add_rect(slide, 9.72, yy + 0.44, 3.0, 0.01, _SEP)

    _footer(slide)


def _slide_energy(prs, pvgis_data: dict, results: dict) -> None:
    """Slide 5 – Energy Analysis."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_rect(slide, 0, 0, 13.33, 7.5, _LGY)
    _add_rect(slide, 0, 0, 13.33, 0.88, _NAV)
    _add_tb(slide, 0.45, 0.20, 10, 0.52,
            "Energy Analysis", 22, bold=True, color=_WHT)

    # Monthly generation chart
    chart_png = _monthly_gen_png(pvgis_data)
    if chart_png:
        slide.shapes.add_picture(
            io.BytesIO(chart_png), _in(0.45), _in(1.0), _in(8.7), _in(3.5))
        _add_tb(slide, 0.45, 4.58, 8.7, 0.3,
                "Shaded = winter (Jun-Aug) high-demand season", 8, color=_DGY, align="center")
    else:
        _add_rect(slide, 0.45, 1.0, 8.7, 3.5, _NAV)
        _add_tb(slide, 0.65, 2.5, 8.3, 0.5,
                "Monthly generation chart unavailable", 11, color=_DGY, align="center")

    # Energy stats sidebar
    d1 = results.get("dispatch_yr1") or {}
    _add_rect(slide, 9.55, 1.0, 3.35, 3.5, _NAV)
    _add_tb(slide, 9.72, 1.1, 3.0, 0.38,
            "ANNUAL ENERGY (Yr 1)", 10, bold=True, color=_GRN)
    e_rows = [
        ("PV Generation",   f"{pvgis_data.get('annual_kwh', 0):,.0f} kWh"),
        ("Site Load",       f"{d1.get('annual_load_kWh', 0):,.0f} kWh"),
        ("Grid Purchase",   f"{d1.get('annual_grid_buy_kWh', 0):,.0f} kWh"),
        ("BESS Discharge",  f"{d1.get('annual_discharge_kWh', 0):,.0f} kWh"),
    ]
    annual_load = d1.get("annual_load_kWh", 0)
    annual_grid = d1.get("annual_grid_buy_kWh", 0)
    if annual_load > 0:
        self_suf = (1 - annual_grid / annual_load) * 100
        e_rows.append(("Self-sufficiency", f"{self_suf:.0f}%"))
    for i, (k, v) in enumerate(e_rows):
        yy = 1.6 + i * 0.54
        _add_tb(slide, 9.72, yy,      2.0, 0.40, k, 9, color=_DGY)
        _add_tb(slide, 11.65, yy, 1.1, 0.40, v, 9, bold=True, color=_WHT, align="right")
        if i < len(e_rows) - 1:
            _add_rect(slide, 9.72, yy + 0.42, 3.0, 0.01, _SEP)

    # Monthly table
    _add_rect(slide, 0.45, 4.95, 12.45, 1.62, _NAV)
    _add_tb(slide, 0.62, 5.03, 4, 0.32,
            "PVGIS MONTHLY GENERATION (kWh)", 9, bold=True, color=_GRN)
    months  = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly = pvgis_data.get("monthly_kwh", [0] * 12)
    col_w   = 12.25 / 12
    for j, (m, v) in enumerate(zip(months, monthly)):
        xx = 0.5 + j * col_w
        winter = j in (5, 6, 7)
        clr = _GRN if winter else "8899AA"
        _add_tb(slide, xx, 5.42, col_w, 0.30, m,       8, color=clr, align="center")
        _add_tb(slide, xx, 5.76, col_w, 0.35, f"{v:,.0f}", 9,
                bold=True, color=_WHT, align="center")

    _footer(slide)


def _slide_tariff(prs, params: dict, results: dict) -> None:
    """Slide 6 – Tariff Structure & Savings."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_rect(slide, 0, 0, 13.33, 7.5, _LGY)
    _add_rect(slide, 0, 0, 13.33, 0.88, _NAV)
    _add_tb(slide, 0.45, 0.20, 10, 0.52,
            "Tariff Structure & Annual Savings", 22, bold=True, color=_WHT)

    tariff_mode = params.get("tariff_mode", "Custom")
    _add_rect(slide, 0.45, 1.02, 5.75, 0.50, _NAV)
    _add_tb(slide, 0.60, 1.10, 5.5, 0.35,
            f"⚡  Tariff:  {tariff_mode}", 12, bold=True, color=_GRN)

    # TOU rates table
    _add_rect(slide, 0.45, 1.62, 5.75, 4.65, _NAV)
    header_rows = [
        ("Period",         "Winter  Jun–Aug",                          "Summer  Sep–May"),
        ("Morning Peak",   f"R {params.get('w_morning_peak',0):.4f}",  f"R {params.get('s_morning_peak',0):.4f}"),
        ("Evening Peak",   f"R {params.get('w_evening_peak',0):.4f}",  f"R {params.get('s_evening_peak',0):.4f}"),
        ("Standard",       f"R {params.get('w_standard',0):.4f}",      f"R {params.get('s_standard',0):.4f}"),
        ("Off-Peak",       f"R {params.get('w_off_peak',0):.4f}",      f"R {params.get('s_off_peak',0):.4f}"),
    ]
    row_heights = 0.68
    for i, (a, b, c) in enumerate(header_rows):
        yy   = 1.70 + i * row_heights
        hdr  = (i == 0)
        bg   = _MNV if hdr else _NAV
        _add_rect(slide, 0.45, yy, 5.75, row_heights, bg)
        clr  = _GRN if hdr else (_DGY if True else _WHT)
        _add_tb(slide, 0.60, yy + 0.17, 1.55, 0.38, a, 9,  bold=hdr, color=_GRN if hdr else _DGY)
        _add_tb(slide, 2.18, yy + 0.17, 1.95, 0.38, b, 10, bold=hdr, color=_GRN if hdr else _WHT, align="center")
        _add_tb(slide, 4.18, yy + 0.17, 1.95, 0.38, c, 10, bold=hdr, color=_GRN if hdr else _WHT, align="center")

    # Savings metric cards (right)
    d1        = results.get("dispatch_yr1") or {}
    ann_sav   = d1.get("annual_savings_zar", 0) or 0
    tariff_esc = params.get("tariff_escalation", 8.0)
    disc_rate  = params.get("discount_rate", 12.0)
    forex      = params.get("forex_usd_zar", 18.5)

    def _m(v): return f"R {abs(v)/1e3:.0f}k/yr" if abs(v) < 1e6 else f"R {abs(v)/1e6:.2f}M/yr"

    for i, (lbl, val, unit) in enumerate([
        ("YR-1 SAVINGS",      _m(ann_sav) if ann_sav else "Run simulation", "Avoided grid cost"),
        ("TARIFF ESCALATION", f"{tariff_esc:.1f}% p.a.",                    "Annual increase assumed"),
        ("DISCOUNT RATE",     f"{disc_rate:.1f}%",                          "WACC / hurdle rate"),
        ("USD / ZAR",         f"{forex:.2f}",                               "Exchange rate used"),
    ]):
        row, col = divmod(i, 2)
        _metric_card(slide, 6.6 + col * 3.1, 1.62 + row * 1.85, lbl, val, unit)

    _footer(slide)


def _slide_assumptions(prs, params: dict) -> None:
    """Slide 7 – Assumptions & Disclaimer (dark closing slide)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_rect(slide, 0, 0, 13.33, 7.5, _NAV)
    _add_rect(slide, 0, 0, 0.12, 7.5, _GRN)

    _add_tb(slide, 0.45, 0.28, 9, 0.65,
            "Key Assumptions", 28, bold=True, color=_WHT)
    _add_rect(slide, 0.45, 0.98, 12.33, 0.025, _SEP)

    assumptions = [
        ("PV Degradation",     f"{params.get('pv_degradation', 0.5):.1f}% per year"),
        ("Round-trip η",       f"{params.get('rte', 90):.0f}%"),
        ("Analysis Period",    "20 years"),
        ("Tariff Escalation",  f"{params.get('tariff_escalation', 8.0):.1f}% per annum"),
        ("Discount Rate",      f"{params.get('discount_rate', 12.0):.1f}%  (WACC)"),
        ("Tax Rate (CIT)",     f"{params.get('tax_rate', 27):.0f}%"),
        ("Section 12B",        "150% accelerated depreciation – Year 1"),
        ("BESS DoD",           f"{params.get('dod', 90):.0f}%"),
        ("USD / ZAR",          f"{params.get('forex_usd_zar', 18.5):.2f}"),
        ("Irradiance source",  "EU PVGIS API  (crystSi, free-mounting)"),
    ]
    mid = len(assumptions) // 2
    for col_i, chunk in enumerate([assumptions[:mid], assumptions[mid:]]):
        x = 0.45 + col_i * 6.45
        for i, (k, v) in enumerate(chunk):
            yy = 1.15 + i * 0.68
            _add_tb(slide, x,       yy, 2.9, 0.42, k, 10, color="8899AA")
            _add_tb(slide, x + 3.0, yy, 3.3, 0.42, v, 10, bold=True, color=_WHT)
            _add_rect(slide, x, yy + 0.44, 6.1, 0.01, _SEP)

    # Disclaimer
    _add_rect(slide, 0.45, 5.42, 12.33, 0.025, _SEP)
    disc = (
        "This report has been prepared by GreenWatt Consulting for informational purposes only. "
        "Results are based on modelled data and stated assumptions; actual performance may vary. "
        "This document does not constitute investment advice. "
        "All tariff values are inclusive of VAT at 15%.  "
        "© GreenWatt Consulting."
    )
    _add_tb(slide, 0.45, 5.56, 12.33, 1.0, disc, 9, color="557799", wrap=True)

    # Closing brand
    _add_tb(slide, 0.45, 6.65, 12.33, 0.55,
            "greenwattconsulting.co.za", 20, bold=True, color=_GRN, align="center")


# ── Public API ────────────────────────────────────────────────────────────────

def generate_pptx(
    params:       dict,
    results:      dict | None,
    fin_df,
    pvgis_data:   dict,
    project_name: str = "",
    client_name:  str = "",
) -> bytes:
    """
    Build a 7-slide PPTX report and return the raw bytes.

    Parameters
    ----------
    params       : dict of session_state params (tariff rates, capex inputs, etc.)
    results      : st.session_state.results dict (npv, irr, dispatch_yr1, lcoe, …)
    fin_df       : 20-year financial model DataFrame (or None)
    pvgis_data   : PVGIS dict (annual_kwh, monthly_kwh, winter/summer daily)
    project_name : display name for the project (slide title)
    client_name  : client/company name shown on cover

    Returns
    -------
    bytes  — write directly to st.download_button(data=...)
    """
    from pptx import Presentation

    results    = results    or {}
    pvgis_data = pvgis_data or {}

    prs = Presentation()
    prs.slide_width  = _in(13.33)
    prs.slide_height = _in(7.5)

    _slide_cover(
        prs, project_name, client_name,
        params.get("pv_kwp", 0), params.get("bess_kwh", 0),
        params.get("tariff_mode", ""),
    )
    _slide_exec_summary(prs, results)
    _slide_system_config(prs, params, pvgis_data)
    _slide_financial(prs, results, fin_df)
    _slide_energy(prs, pvgis_data, results)
    _slide_tariff(prs, params, results)
    _slide_assumptions(prs, params)

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.read()
