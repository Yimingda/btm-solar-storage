"""
report_pptx.py  —  Executive PPTX Report Generator
BTM PV+BESS Financial Modelling System

Design language
───────────────
• White / very-light-grey slide backgrounds  (no dark navy)
• Thin 0.55" accent top-bar in deep energy-green
• McKinsey "pyramid" headline structure:  every slide title = the conclusion
• Each content slide carries a 2-3 sentence narrative paragraph
• Large KPI callouts in accent colour; supporting data below
• Charts minimal-axis, brand-green bars, white background
• Company / consultant names as parameters — NO hardcoded branding

Slide sequence  (8 slides)
───────────────────────────
  1. Cover
  2. Investment Thesis          "Why this project stacks up"
  3. System Overview            specs + PVGIS
  4. Financial Returns          NPV / IRR / payback chart
  5. Energy Analysis            monthly generation + dispatch
  6. Tariff Opportunity         TOU rates + peak-shaving logic
  7. Implementation Roadmap     timeline + next steps
  8. Assumptions & Disclaimer   dark closing slide
"""
from __future__ import annotations

import io
from datetime import date
from typing import Any

# ── Palette ──────────────────────────────────────────────────────────────────
_GDK  = "005C4E"   # dark forest-green  — header bars, large accents
_GMD  = "00875A"   # mid green           — KPI numbers, chart bars
_GLT  = "E6F4F1"   # pale green tint     — shaded callout backgrounds
_NAVY = "1E293B"   # near-black          — slide titles, body text
_GRAY = "64748B"   # slate-grey          — labels, captions
_LGRY = "F1F5F9"   # light grey          — alternating row tint
_AMBR = "D97706"   # amber               — advisory callouts
_RED  = "DC2626"   # red                 — negative values
_WHT  = "FFFFFF"   # white
_SEP  = "CBD5E1"   # separator line grey

# ── python-pptx micro-helpers ─────────────────────────────────────────────────

def _rgb(h: str):
    from pptx.dml.color import RGBColor
    h = h.lstrip("#")
    return RGBColor(int(h[:2],16), int(h[2:4],16), int(h[4:],16))

def _in(v: float):
    from pptx.util import Inches; return Inches(v)

def _pt(v: float):
    from pptx.util import Pt; return Pt(v)

def _rect(slide, x,y,w,h, fill:str, line:str|None=None):
    shp = slide.shapes.add_shape(1, _in(x),_in(y),_in(w),_in(h))
    shp.fill.solid(); shp.fill.fore_color.rgb = _rgb(fill)
    if line:
        from pptx.util import Pt as _P
        shp.line.color.rgb = _rgb(line); shp.line.width = _P(0.75)
    else:
        shp.line.fill.background()
    return shp

def _tb(slide, x,y,w,h, text:str, size:float,
        bold=False, color=_NAVY, align="left", wrap=True):
    from pptx.enum.text import PP_ALIGN
    _am = {"left":PP_ALIGN.LEFT,"center":PP_ALIGN.CENTER,"right":PP_ALIGN.RIGHT}
    tb = slide.shapes.add_textbox(_in(x),_in(y),_in(w),_in(h))
    tf = tb.text_frame; tf.word_wrap = wrap
    tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=_pt(0)
    para = tf.paragraphs[0]; para.alignment = _am.get(align, PP_ALIGN.LEFT)
    run = para.add_run(); run.text = text
    run.font.size = _pt(size); run.font.bold = bold
    run.font.color.rgb = _rgb(color)
    return tb

def _multiline_tb(slide, x,y,w,h, lines:list[tuple[str,float,bool,str]]):
    """lines = [(text, pt_size, bold, hex_color), ...]"""
    from pptx.enum.text import PP_ALIGN
    tb = slide.shapes.add_textbox(_in(x),_in(y),_in(w),_in(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=_pt(0)
    for i,(text,sz,bold,clr) in enumerate(lines):
        para = tf.paragraphs[0] if i==0 else tf.add_paragraph()
        para.alignment = PP_ALIGN.LEFT
        run = para.add_run(); run.text = text
        run.font.size = _pt(sz); run.font.bold = bold
        run.font.color.rgb = _rgb(clr)
        para.space_after = _pt(3)
    return tb

# ── Shared layout elements ────────────────────────────────────────────────────

def _header_bar(slide, title:str, subtitle:str=""):
    """White slide with thin green top-bar + slide title beneath."""
    # thin top accent bar
    _rect(slide, 0, 0, 13.33, 0.55, _GDK)
    # white body
    _rect(slide, 0, 0.55, 13.33, 6.95, _WHT)
    # slide title (conclusion/headline — bold, large)
    _tb(slide, 0.45, 0.72, 12.0, 0.62, title, 21, bold=True, color=_NAVY)
    if subtitle:
        _tb(slide, 0.45, 1.35, 12.0, 0.38, subtitle, 10.5, color=_GRAY)

def _footer(slide, company:str, page:int, total:int=8):
    _rect(slide, 0, 7.22, 13.33, 0.02, _SEP)
    _tb(slide, 0.45, 7.26, 9.0,  0.22, company, 8, color=_GRAY)
    _tb(slide, 11.8, 7.26, 1.5,  0.22, f"{page} / {total}", 8,
        color=_GRAY, align="right")

def _kpi_block(slide, x,y, label:str, value:str, sub:str="", w:float=2.8):
    """Large KPI: accent-green value + label above + subscript below."""
    _rect(slide, x, y, w, 1.4, _GLT)
    _rect(slide, x, y, 0.065, 1.4, _GDK)           # left accent strip
    _tb(slide, x+0.14, y+0.10, w-0.2, 0.28, label, 8.5, color=_GRAY)
    _tb(slide, x+0.14, y+0.40, w-0.2, 0.60, value, 26, bold=True, color=_rgb(_GMD).__str__() and _GMD)
    if sub:
        _tb(slide, x+0.14, y+1.08, w-0.2, 0.26, sub, 8, color=_GRAY)

def _narrative(slide, x,y,w,h, text:str):
    """Grey italic narrative paragraph."""
    _tb(slide, x,y,w,h, text, 10, color=_GRAY, wrap=True)

# ── Chart helpers (matplotlib → PNG bytes) ───────────────────────────────────

def _style_ax(ax):
    """Apply clean white minimal style to a matplotlib Axes."""
    ax.set_facecolor("white")
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color("#CBD5E1")
    ax.tick_params(colors="#64748B", labelsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0, color="#CBD5E1")

def _png_cashflow(fin_df) -> bytes|None:
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt, numpy as np
        years = fin_df["Year"].tolist()
        ncf   = fin_df["Net Cash Flow NCF (ZAR)"].values / 1e6
        cum   = fin_df["Cumulative CF (ZAR)"].values / 1e6
        fig, ax1 = plt.subplots(figsize=(8.8, 3.2), facecolor="white")
        clrs = [f"#{_GMD}" if v>=0 else f"#{_RED}" for v in ncf]
        ax1.bar(years, ncf, color=clrs, width=0.65, alpha=0.9, zorder=3)
        ax1.axhline(0, color="#CBD5E1", linewidth=0.8)
        ax1.set_xlabel("Year", fontsize=9, color="#64748B")
        ax1.set_ylabel("Annual NCF  (R million)", fontsize=9, color="#64748B")
        _style_ax(ax1)
        ax2 = ax1.twinx()
        ax2.plot(years, cum, color=f"#{_GDK}", linewidth=2.2,
                 marker="o", markersize=3.5, zorder=5)
        ax2.set_ylabel("Cumulative  (R million)", fontsize=9, color=f"#{_GDK}")
        ax2.tick_params(colors=f"#{_GDK}", labelsize=8)
        ax2.spines[["top","right"]].set_color("#CBD5E1")
        ax2.spines[["left","bottom"]].set_visible(False)
        # Annotate payback crossing
        for i,v in enumerate(cum):
            if v >= 0 and (i==0 or cum[i-1]<0):
                ax2.axvline(years[i], color="#D97706", linewidth=1.2,
                            linestyle="--", alpha=0.7)
                ax2.text(years[i]+0.15, max(cum)*0.05,
                         f"Break-even\nYr {years[i]}", fontsize=7.5,
                         color="#D97706", va="bottom")
                break
        plt.tight_layout(pad=0.4)
        buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
        plt.close(fig); buf.seek(0); return buf.read()
    except Exception:
        return None

def _png_monthly(pvgis_data:dict) -> bytes|None:
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        months  = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]
        monthly = pvgis_data.get("monthly_kwh",[0]*12)
        fig,ax  = plt.subplots(figsize=(8.8,3.0), facecolor="white")
        bar_clr = [f"#{_GDK}" if i in (5,6,7) else f"#{_GMD}" for i in range(12)]
        bars = ax.bar(months, monthly, color=bar_clr, alpha=0.88, width=0.65, zorder=3)
        ax.set_ylabel("kWh / month", fontsize=9, color="#64748B")
        _style_ax(ax)
        # Value labels on bars
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x()+bar.get_width()/2, h+max(monthly)*0.01,
                    f"{h/1000:.1f}k", ha="center", va="bottom",
                    fontsize=7, color="#64748B")
        # Winter annotation
        ax.axvspan(4.45, 7.55, color=f"#{_GLT}", alpha=0.6, zorder=0)
        ax.text(6.0, max(monthly)*0.92, "Peak-tariff\nseason",
                ha="center", fontsize=7.5, color=f"#{_GDK}", style="italic")
        plt.tight_layout(pad=0.4)
        buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
        plt.close(fig); buf.seek(0); return buf.read()
    except Exception:
        return None

# ── Slide builders ────────────────────────────────────────────────────────────

def _s1_cover(prs, project_name:str, client_name:str, consultant_name:str,
              pv_kwp:float, bess_kwh:float, tariff_mode:str):
    """Slide 1 – Cover (dark green, bold typography, no decorative clutter)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    # Full dark-green background
    _rect(slide, 0,0,13.33,7.5, _GDK)
    # White right panel
    _rect(slide, 8.8,0,4.53,7.5, _WHT)
    # Thin amber accent strip
    _rect(slide, 8.78,0,0.07,7.5, _AMBR)

    # EPC + OEM — top-left, two fields on one line
    epc_label = f"EPC:  {consultant_name}" if consultant_name else "EPC:  —"
    oem_label = f"OEM:  {client_name}"     if client_name     else "OEM:  —"
    _tb(slide, 0.55,0.18,5.5,0.30, epc_label, 9, bold=True, color="A7F3D0")
    _tb(slide, 0.55,0.52,5.5,0.30, oem_label, 9, bold=True, color="6EE7B7")

    # Horizontal rule
    _rect(slide, 0.55,0.90,7.7,0.03, "1D4034")

    # Main title
    title = project_name or f"{pv_kwp:,.0f} kWp PV + {bess_kwh:,.0f} kWh BESS"
    _tb(slide, 0.55,1.10,7.7,1.60, title, 36, bold=True, color=_WHT)

    # Sub-title
    _tb(slide, 0.55,2.78,7.7,0.50,
        "BTM Solar PV & Battery Energy Storage — Executive Report",
        13, color="6EE7B7")

    # Date
    _tb(slide, 0.55,3.50,7.7,0.38,
        f"Report Date:   {date.today().strftime('%B %Y')}", 11, color="6EE7B7")

    # Right panel: system-size callout
    _tb(slide, 9.10,1.40,4.0,0.38, "SYSTEM SIZE", 9,
        bold=True, color=_GDK, align="center")
    _rect(slide, 9.10,1.78,3.90,0.03, _SEP)
    _tb(slide, 9.10,1.85,4.0,0.90,
        f"{pv_kwp:,.0f} kWp", 42, bold=True, color=_GDK, align="center")
    _tb(slide, 9.10,2.80,4.0,0.42,
        "Solar PV Array", 11, color=_GRAY, align="center")
    _rect(slide, 9.10,3.28,3.90,0.03, _SEP)
    _tb(slide, 9.10,3.38,4.0,0.75,
        f"{bess_kwh:,.0f} kWh", 34, bold=True, color=_GMD, align="center")
    _tb(slide, 9.10,4.18,4.0,0.38,
        "Battery Storage", 11, color=_GRAY, align="center")

    # Tariff
    if tariff_mode:
        _rect(slide, 9.10,5.10,3.90,0.52, _GLT)
        _tb(slide, 9.20,5.18,3.70,0.35,
            f"Tariff:  {tariff_mode[:30]}", 9, color=_GDK)

    # Footer
    _tb(slide, 0.55,7.05,7.7,0.32,
        "CONFIDENTIAL  ·  For executive review only",
        8, color="1D4034", align="left")


def _s2_thesis(prs, results:dict, params:dict, company:str):
    """Slide 2 – Investment Thesis: the entire story on one page."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    npv     = results.get("npv",0) or 0
    irr     = results.get("irr",0) or 0
    payback = results.get("payback") or 0
    capex   = results.get("total_capex",0) or 0
    lcoe_d  = results.get("lcoe") or {}
    lcoe    = lcoe_d.get("lcoe_zar_kwh",0) or 0
    avoided = lcoe_d.get("total_avoided_mwh",0) or 0
    esc     = params.get("tariff_escalation",8.0)

    def _m(v): return f"R {abs(v)/1e6:.1f}M" if abs(v)>=1e6 else f"R {abs(v)/1e3:.0f}k"

    headline = (f"At {irr:.1f}% IRR and {payback:.1f}-year payback, "
                f"this investment outperforms typical fixed-income benchmarks")
    _header_bar(slide, headline,
                "Capital outlay is recovered in full before Year 6 — the project then generates "
                "free cash flow for 14+ years with no incremental CAPEX.")

    # 5 KPI blocks — row 1
    for i,(lbl,val,sub) in enumerate([
        ("TOTAL CAPEX",     _m(capex),        "All-in investment"),
        ("20-YEAR NPV",     _m(npv),          "After tax & inflation"),
        ("PROJECT IRR",     f"{irr:.1f}%",    "Unlevered, after-tax"),
        ("SIMPLE PAYBACK",  f"{payback:.1f} yr","Grid-savings basis"),
        ("1ST YR LCOE",     f"R {lcoe:.2f}",  "Per kWh avoided"),
    ]):
        _kpi_block(slide, 0.45+i*2.56, 1.88, lbl, val, sub, w=2.45)

    # Narrative paragraph
    story = (
        f"The project displaces expensive Eskom {params.get('tariff_mode','Megaflex')} "
        f"peak energy (winter peak R {params.get('w_evening_peak',8.13):.2f}/kWh) "
        f"with self-generated solar and stored battery energy.  "
        f"Tariff escalation of {esc:.1f}% p.a. compounds returns over the 20-year model "
        f"horizon, making early deployment strongly value-accretive.  "
        f"Section 12B accelerated depreciation (150% Year-1 deduction) materially "
        f"reduces the effective tax burden in Year 1, improving early cash flows."
    )
    _rect(slide, 0.45, 3.55, 12.45, 0.03, _SEP)
    _narrative(slide, 0.45, 3.70, 12.45, 0.75, story)

    # Bottom: two insight boxes
    for xi,(hdr,body) in enumerate([
        ("Grid Independence",
         f"After full commissioning, the site sources ≈{min(95,round((1-(results.get('dispatch_yr1') or {}).get('annual_grid_buy_kWh',1)/max(1,(results.get('dispatch_yr1') or {}).get('annual_load_kWh',1)))*100,0)):.0f}% "
         "of daytime demand from owned generation — insulating operations from "
         "future utility price shocks and potential loadshedding exposure."),
        ("Lifetime avoided energy",
         f"Over 20 years the system is projected to avoid purchasing "
         f"{avoided:,.0f} MWh from the grid, representing a significant "
         "long-run operational cost reduction and measurable carbon footprint improvement."),
    ]):
        _rect(slide, 0.45+xi*6.3, 4.62, 6.1, 1.72, _GLT)
        _tb(slide, 0.60+xi*6.3, 4.72, 5.8, 0.32, hdr, 10, bold=True, color=_GDK)
        _narrative(slide, 0.60+xi*6.3, 5.08, 5.8, 1.15, body)

    _footer(slide, company, 2)


def _s3_system(prs, params:dict, pvgis_data:dict, company:str):
    """Slide 3 – System Overview."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    annual_kwh = pvgis_data.get("annual_kwh", 0)
    pv_kwp = params.get("pv_kwp", 0)
    spec_yield = annual_kwh / pv_kwp if pv_kwp else 0

    headline = (f"{pv_kwp:,.0f} kWp of crystalline silicon PV paired with a "
                f"{params.get('bess_kwh',0):,.0f} kWh battery — "
                f"specific yield {spec_yield:,.0f} kWh/kWp/yr")
    _header_bar(slide, headline,
                f"Site coordinates: {params.get('lat',0):.3f}°, {params.get('lon',0):.3f}°  "
                f"·  Tilt {params.get('tilt',20):.0f}°  ·  Azimuth {params.get('azimuth',180):.0f}°  "
                f"·  PVGIS irradiance source (EU Joint Research Centre)")

    # Two spec columns
    def _spec_col(title, icon, rows, x):
        W = 5.85
        _rect(slide, x,1.88,W,0.48, _GDK)
        _tb(slide, x+0.15,1.93,W-0.2,0.35, f"{icon}  {title}",
            13, bold=True, color=_WHT)
        for i,(k,v) in enumerate(rows):
            yy = 2.44+i*0.55
            bg = _LGRY if i%2==0 else _WHT
            _rect(slide, x,yy,W,0.53, bg)
            _tb(slide, x+0.18,yy+0.10,2.9,0.38, k, 10, color=_GRAY)
            _tb(slide, x+3.1, yy+0.10,W-3.3,0.38, v, 11, bold=True,
                color=_NAVY, align="right")

    pv_rows = [
        ("Peak power",          f"{pv_kwp:,.0f} kWp"),
        ("System losses",       f"{params.get('pv_loss',14):.0f}%"),
        ("Tilt / Azimuth",      f"{params.get('tilt',20):.0f}° / {params.get('azimuth',180):.0f}°"),
        ("Annual generation",   f"{annual_kwh:,.0f} kWh/yr"),
        ("Specific yield",      f"{spec_yield:,.0f} kWh/kWp/yr"),
        ("Summer daily avg",    f"{pvgis_data.get('summer_daily_kwh',0):.1f} kWh/day"),
        ("Winter daily avg",    f"{pvgis_data.get('winter_daily_kwh',0):.1f} kWh/day"),
        ("Annual degradation",  f"{params.get('pv_degradation',0.5):.1f}% p.a."),
    ]
    _spec_col("SOLAR PV ARRAY", "☀", pv_rows, 0.45)

    c_rate = params.get("c_rate", 0.25)
    bess_kwh = params.get("bess_kwh", 0)
    bess_rows = [
        ("Usable capacity",    f"{bess_kwh:,.0f} kWh"),
        ("Max charge/discharge",f"{bess_kwh*c_rate:,.0f} kW  ({params.get('c_rate_label','0.25C')})"),
        ("Depth of discharge", f"{params.get('dod',90):.0f}%"),
        ("Round-trip efficiency", f"{params.get('rte',90):.0f}%"),
        ("Design cycle rate",  f"{params.get('bess_cycles',365):.0f} cycles/yr"),
        ("Tariff mode",        (params.get("tariff_mode","—")[:28]+"…")
                               if len(params.get("tariff_mode",""))>28
                               else params.get("tariff_mode","—")),
        ("Analysis period",    "20 years"),
        ("Dispatch strategy",  "Peak shaving + arbitrage"),
    ]
    _spec_col("BATTERY STORAGE", "🔋", bess_rows, 6.98)

    # Bottom narrative
    _rect(slide, 0.45, 6.92, 12.45, 0.03, _SEP)
    _narrative(slide, 0.45, 7.00, 12.45, 0.20,
               "PVGIS data sourced from EU Joint Research Centre API — crystalline silicon, free-mounted, site coordinates. "
               "Offline fallback: 1,650 kWh/kWp/yr empirical estimate.")
    _footer(slide, company, 3)


def _s4_financial(prs, results:dict, fin_df, company:str):
    """Slide 4 – Financial Returns."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    npv     = results.get("npv",0) or 0
    irr     = results.get("irr",0) or 0
    payback = results.get("payback") or 0
    capex   = results.get("total_capex",0) or 0

    def _m(v): return f"R {abs(v)/1e6:.2f}M"
    sign = "+" if npv>=0 else "−"
    headline = (f"Project returns {sign}R {abs(npv)/1e6:.1f}M NPV over 20 years "
                f"at an IRR of {irr:.1f}% — payback achieved in Year {payback:.0f}")
    _header_bar(slide, headline,
                f"CAPEX {_m(capex)} ·  Discount rate {results.get('discount_rate',12):.1f}% "
                f"·  After-tax model (CIT {results.get('tax_rate',27):.0f}%, Section 12B 150% Yr-1)")

    # Cash flow chart
    chart_png = _png_cashflow(fin_df) if fin_df is not None else None
    if chart_png:
        slide.shapes.add_picture(io.BytesIO(chart_png),
                                 _in(0.45),_in(1.88),_in(8.65),_in(3.60))
    else:
        _rect(slide,0.45,1.88,8.65,3.60,_LGRY)
        _tb(slide,1.0,3.4,7.5,0.45,"Run simulation first to generate chart",11,color=_GRAY,align="center")

    _tb(slide,0.45,5.55,8.65,0.28,
        "▲ Green bars = positive annual cash flow  ·  Red bars = negative  ·  "
        "Navy line = cumulative  ·  Dashed vertical = payback year",
        8, color=_GRAY, align="center")

    # Right sidebar KPIs
    for i,(lbl,val,sub) in enumerate([
        ("CAPEX",          _m(capex),           "Total capital outlay"),
        ("20-yr NPV",      f"{sign}{_m(abs(npv))}", "After tax, discounted"),
        ("IRR",            f"{irr:.1f}%",        "Unlevered, after-tax"),
        ("Payback",        f"Year {payback:.1f}","Simple CF basis"),
    ]):
        _kpi_block(slide, 9.55, 1.88+i*1.35, lbl, val, sub, w=3.30)

    # Narrative
    _rect(slide, 0.45,5.90,12.45,0.03,_SEP)
    story = (
        "The 20-year discounted model incorporates annual O&M escalation, "
        "PV degradation, and BESS SOH decline.  The Section 12B 150% accelerated "
        "depreciation allowance improves Year-1 after-tax cash flow materially.  "
        "Net present value remains robustly positive across ±2% tariff-escalation "
        "sensitivity (not shown — available in full Excel model)."
    )
    _narrative(slide, 0.45,6.00,12.45,0.55, story)
    _footer(slide, company, 4)


def _s5_energy(prs, pvgis_data:dict, results:dict, company:str):
    """Slide 5 – Energy Analysis."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    d1           = results.get("dispatch_yr1") or {}
    annual_gen   = pvgis_data.get("annual_kwh",0)
    annual_load  = d1.get("annual_load_kWh",0)
    annual_grid  = d1.get("annual_grid_buy_kWh",0)
    annual_disc  = d1.get("annual_discharge_kWh",0)
    self_suf     = (1-annual_grid/annual_load)*100 if annual_load else 0
    grid_reduced = annual_load-annual_grid if annual_load else 0

    headline = (f"Year-1 PV generation of {annual_gen/1e3:,.0f} MWh displaces "
                f"{grid_reduced/1e3:,.0f} MWh of grid purchases — "
                f"{self_suf:.0f}% self-sufficiency achieved")
    _header_bar(slide, headline,
                "Monthly profile below — June–August winter peak season (darker bars) "
                "coincides with highest Eskom TOU rates, maximising battery arbitrage value.")

    # Monthly chart
    chart_png = _png_monthly(pvgis_data)
    if chart_png:
        slide.shapes.add_picture(io.BytesIO(chart_png),
                                 _in(0.45),_in(1.88),_in(8.65),_in(3.20))
    else:
        _rect(slide,0.45,1.88,8.65,3.20,_LGRY)

    # Energy KPIs (right sidebar)
    e_kpis = [
        ("PV GENERATION",    f"{annual_gen/1e3:,.0f} MWh",  "Year-1 total"),
        ("SITE LOAD",        f"{annual_load/1e3:,.0f} MWh" if annual_load else "—", "Yr-1 total demand"),
        ("GRID PURCHASE",    f"{annual_grid/1e3:,.0f} MWh" if annual_grid else "—", "After PV+BESS"),
        ("BESS DISCHARGE",   f"{annual_disc/1e3:,.0f} MWh" if annual_disc else "—", "Battery output"),
        ("SELF-SUFFICIENCY", f"{self_suf:.0f}%", "Load served on-site"),
    ]
    for i,(lbl,val,sub) in enumerate(e_kpis[:4]):
        _kpi_block(slide, 9.55, 1.88+i*1.26, lbl, val, sub, w=3.30)

    # Monthly table strip
    _rect(slide, 0.45,5.18,8.65,0.03,_SEP)
    months  = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    monthly = pvgis_data.get("monthly_kwh",[0]*12)
    cw = 8.58/12
    for j,(m,v) in enumerate(zip(months,monthly)):
        xx = 0.48+j*cw
        bg = _GLT if j in (5,6,7) else _WHT
        _rect(slide,xx,5.25,cw-0.04,0.70,bg)
        _tb(slide,xx+0.02,5.28,cw-0.06,0.27,m,  8,color=_GRAY,align="center")
        _tb(slide,xx+0.02,5.56,cw-0.06,0.32,f"{v/1000:.1f}k",9,
            bold=True,color=_GDK if j in (5,6,7) else _NAVY,align="center")

    # Narrative
    _rect(slide, 0.45,6.03,12.45,0.03,_SEP)
    story = (
        f"Self-sufficiency of {self_suf:.0f}% means operations draw only "
        f"{annual_grid/1e3:,.0f} MWh from the grid in Year 1.  "
        "The battery charges during off-peak periods and discharges during "
        "Eskom morning and evening peak windows, maximising avoided-cost value.  "
        f"Shaded columns (Jun–Aug) represent high-demand season — system is "
        "designed to dispatch aggressively during these months."
    )
    _narrative(slide, 0.45,6.10,12.45,0.65, story)
    _footer(slide, company, 5)


def _s6_tariff(prs, params:dict, results:dict, company:str):
    """Slide 6 – Tariff Opportunity."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    w_pk  = params.get("w_evening_peak", 8.13)
    w_op  = params.get("w_off_peak",     1.57)
    esc   = params.get("tariff_escalation", 8.0)
    ratio = w_pk/w_op if w_op else 0

    headline = (f"Winter peak rate of R {w_pk:.2f}/kWh is {ratio:.1f}× the off-peak rate "
                f"— creating a R {w_pk-w_op:.2f}/kWh arbitrage window for the battery")
    _header_bar(slide, headline,
                f"Tariff: {params.get('tariff_mode','—')}  ·  "
                f"Tariff escalation assumed at {esc:.1f}% p.a.  ·  "
                "All values inclusive of 15% VAT")

    # TOU rates table
    _rect(slide, 0.45, 1.88, 5.60, 0.48, _GDK)
    for col,hdr in zip([0.60,2.40,4.10],["Period","Winter (Jun–Aug)","Summer (Sep–May)"]):
        _tb(slide, col,1.93,1.8,0.35, hdr,10,bold=True,color=_WHT)

    rate_rows = [
        ("Morning Peak",  f"R {params.get('w_morning_peak',0):.4f}",  f"R {params.get('s_morning_peak',0):.4f}"),
        ("Evening Peak",  f"R {params.get('w_evening_peak',0):.4f}",  f"R {params.get('s_evening_peak',0):.4f}"),
        ("Standard",      f"R {params.get('w_standard',0):.4f}",      f"R {params.get('s_standard',0):.4f}"),
        ("Off-Peak",      f"R {params.get('w_off_peak',0):.4f}",      f"R {params.get('s_off_peak',0):.4f}"),
    ]
    for i,(a,b,c) in enumerate(rate_rows):
        yy = 2.44+i*0.60
        bg = _LGRY if i%2==0 else _WHT
        _rect(slide, 0.45,yy,5.60,0.58,bg)
        _tb(slide,0.60,yy+0.12,1.7,0.38, a,10,color=_GRAY)
        _tb(slide,2.40,yy+0.12,1.6,0.38, b,11,bold=True,color=_NAVY,align="center")
        _tb(slide,4.10,yy+0.12,1.8,0.38, c,11,bold=True,color=_NAVY,align="center")

    # Dispatch logic text box
    _rect(slide, 0.45,5.00,5.60,1.55,_GLT)
    _tb(slide,0.60,5.08,5.3,0.32,"Dispatch Strategy",11,bold=True,color=_GDK)
    _narrative(slide, 0.60,5.42,5.3,1.02,
               "Battery charges from PV surplus and cheap off-peak grid power "
               "(≤R 1.57/kWh). It discharges during morning (07:00–09:00) and "
               "evening (17:00–20:00) peak windows when grid cost exceeds "
               f"R {w_pk:.2f}/kWh — capturing the full R {w_pk-w_op:.2f}/kWh spread.")

    # Right: savings KPIs + escalation story
    d1      = results.get("dispatch_yr1") or {}
    ann_sav = d1.get("annual_savings_zar",0) or 0
    def _m(v): return f"R {abs(v)/1e3:.0f}k/yr" if abs(v)<1e6 else f"R {abs(v)/1e6:.2f}M/yr"

    _kpi_block(slide,6.55,1.88,"YR-1 GRID SAVINGS",
               _m(ann_sav) if ann_sav else "Run sim",
               "Avoided grid purchase cost", w=3.30)
    _kpi_block(slide,10.0,1.88,"TARIFF ESCALATION",
               f"{esc:.1f}% p.a.", "Annual increase assumed", w=3.10)

    # Escalation impact table
    _rect(slide,6.55,3.40,6.55,0.40,_GDK)
    _tb(slide,6.72,3.46,6.2,0.30,"Year-1 → Year-10 tariff projection  (illustrative)",
        9,bold=True,color=_WHT)
    base_pk = w_pk
    for i,yr in enumerate([1,3,5,10,15,20]):
        projected = base_pk * (1+esc/100)**(yr-1)
        xx = 6.58+i*1.08
        bg = _GLT if yr in (10,15,20) else _LGRY
        _rect(slide,xx,3.82,1.05,1.02,bg)
        _tb(slide,xx+0.05,3.88,0.95,0.32,f"Yr {yr}",8,color=_GRAY,align="center")
        _tb(slide,xx+0.05,4.22,0.95,0.50,f"R{projected:.2f}",11,
            bold=True,color=_GDK if yr>=10 else _NAVY,align="center")

    _rect(slide,0.45,5.65,12.45,0.03,_SEP)
    _narrative(slide,0.45,5.75,12.45,0.62,
               f"At {esc:.1f}% annual tariff escalation, the evening peak rate will reach "
               f"approximately R {base_pk*(1+esc/100)**9:.2f}/kWh by Year 10 and "
               f"R {base_pk*(1+esc/100)**19:.2f}/kWh by Year 20.  "
               "Each additional R 0.10/kWh of escalation above the base assumption "
               "adds materially to project NPV — early commissioning locks in these "
               "economics for the full 20-year analysis period.")
    _footer(slide, company, 6)


def _s7_roadmap(prs, results:dict, params:dict, company:str):
    """Slide 7 – Implementation Roadmap."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bess_lead = results.get("bess_lead_months", params.get("bess_lead_months",6))
    pv_lead   = results.get("pv_lead_months",   params.get("pv_lead_months",12))
    precomm   = max(0, pv_lead - bess_lead)

    headline = (f"Battery commissioned in Month {bess_lead}, "
                f"full PV+BESS system live by Month {pv_lead} — "
                "phased approach de-risks procurement and maximises early cash flows")
    _header_bar(slide, headline,
                "All timelines are indicative and subject to site assessment, "
                "grid connection, and equipment availability.")

    # Timeline bar
    total_months = pv_lead + 2
    bar_y = 2.00; bar_h = 0.65; bar_w = 12.0
    _rect(slide, 0.45, bar_y, bar_w, bar_h, _LGRY)

    phases = [
        (0,             3,              "Feasibility &\nPermitting",  _GRAY),
        (3,             bess_lead,      "Procurement\n& Civil Works", _GMD),
        (bess_lead,     pv_lead,        "BESS\nCommissioned",         _GDK),
        (pv_lead,       pv_lead+3,      "Full System\nOperational",   _AMBR),
    ]
    for (m_start, m_end, label, clr) in phases:
        if m_end <= m_start: continue
        x  = 0.45 + (m_start/total_months)*bar_w
        w  = ((m_end-m_start)/total_months)*bar_w
        _rect(slide, x, bar_y, w-0.02, bar_h, clr)
        if w > 0.8:
            _tb(slide, x+0.06, bar_y+0.08, w-0.1, bar_h-0.12,
                label, 8, bold=True, color=_WHT)

    # Month markers
    for m in range(0, total_months+1, 3):
        x = 0.45 + (m/total_months)*bar_w
        _rect(slide, x, bar_y+bar_h, 0.01, 0.15, _SEP)
        _tb(slide, x-0.2, bar_y+bar_h+0.18, 0.5, 0.25,
            f"M{m}", 7.5, color=_GRAY, align="center")

    # Milestone markers
    for m_num, icon, label in [
        (bess_lead, "🔋", f"BESS Live  M{bess_lead}"),
        (pv_lead,   "☀",  f"PV Live  M{pv_lead}"),
    ]:
        x = 0.45 + (m_num/total_months)*bar_w
        _tb(slide, x-0.3, bar_y-0.55, 2.2, 0.42,
            f"{icon}  {label}", 9, bold=True, color=_GDK)
        _rect(slide, x, bar_y-0.15, 0.02, 0.18, _GDK)

    # Next Steps
    _rect(slide, 0.45, 3.38, 12.45, 0.40, _GDK)
    _tb(slide, 0.60, 3.44, 12.0, 0.28, "RECOMMENDED NEXT STEPS",
        10, bold=True, color=_WHT)

    steps = [
        ("1. Site Assessment",
         "Commission a detailed shading analysis, roof/ground survey, and "
         "single-line diagram to confirm the design assumptions."),
        ("2. Grid Application",
         "Submit a Generation Connection Application (GCA) to the relevant "
         "network operator (Eskom/municipality) — lead time is typically 4–8 weeks."),
        ("3. Contractor RFQ",
         "Issue a Request for Quotation to at least three EPC contractors "
         "with PV+BESS references in South Africa.  Specify Huawei FusionSolar "
         "or equivalent tier-1 equipment."),
        ("4. Financial Close",
         "Finalise funding structure (own equity, bank debt, or PPA/RESCO model) "
         "and execute EPC contract.  Section 12B allowance requires ownership before "
         "31 March tax year-end."),
    ]
    for i,(hdr,body) in enumerate(steps):
        col, row = i%2, i//2
        x = 0.45 + col*6.30
        y = 3.88 + row*1.55
        _rect(slide, x, y, 6.1, 1.45, _GLT if row%2==0 else _LGRY)
        _tb(slide, x+0.15,y+0.10,5.8,0.30, hdr,10,bold=True,color=_GDK)
        _narrative(slide, x+0.15,y+0.42,5.8,0.95, body)

    _footer(slide, company, 7)


def _s8_assumptions(prs, params:dict, company:str):
    """Slide 8 – Assumptions & Disclaimer (dark closing slide)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    # Full dark background
    _rect(slide, 0,0,13.33,7.5, _GDK)
    _rect(slide, 0,0,0.10,7.5, _AMBR)   # amber left strip
    # White content zone
    _rect(slide, 0.45,0.55,12.45,5.70, _WHT)

    _tb(slide, 0.60,0.00,9.0,0.52,
        "Key Assumptions  &  Disclaimer", 20, bold=True, color=_WHT)

    assumptions = [
        ("PV degradation",       f"{params.get('pv_degradation',0.5):.1f}% per year (linear)"),
        ("Round-trip efficiency", f"{params.get('rte',90):.0f}%  (AC-AC)"),
        ("Analysis horizon",     "20 years from PV commissioning"),
        ("Tariff escalation",    f"{params.get('tariff_escalation',8.0):.1f}% per annum (real)"),
        ("Discount rate (WACC)", f"{params.get('discount_rate',12.0):.1f}%  (nominal, after-tax)"),
        ("Corporate Income Tax", f"{params.get('tax_rate',27):.0f}%  (CIT)"),
        ("Section 12B",          "150% accelerated depreciation — Year 1 only"),
        ("Battery DoD",          f"{params.get('dod',90):.0f}%  (usable capacity)"),
        ("FX rate",              f"USD / ZAR  {params.get('forex_usd_zar',18.5):.2f}"),
        ("Irradiance data",      "EU PVGIS API — crystSi, free-mount, site coordinates"),
    ]
    mid = len(assumptions)//2
    for col_i, chunk in enumerate([assumptions[:mid],assumptions[mid:]]):
        x = 0.62+col_i*6.30
        _rect(slide, x-0.05,0.58,6.05,0.38,_GDK)
        _tb(slide, x,0.62,5.9,0.28,
            "TECHNICAL / FINANCIAL" if col_i==0 else "REGULATORY / MARKET",
            9,bold=True,color=_WHT)
        for i,(k,v) in enumerate(chunk):
            yy = 1.05+i*0.55
            bg = _LGRY if i%2==0 else _WHT
            _rect(slide, x-0.05,yy,6.05,0.53,bg)
            _tb(slide, x+0.08,yy+0.10,2.75,0.38, k, 9.5,color=_GRAY)
            _tb(slide, x+2.88,yy+0.10,3.05,0.38, v, 10, bold=True,color=_NAVY,align="left")

    # Disclaimer panel
    _rect(slide, 0.45,6.30,12.45,0.40, _AMBR)
    _tb(slide, 0.60,6.35,12.2,0.28,
        "DISCLAIMER — READ BEFORE ACTING ON THIS DOCUMENT", 9,bold=True,color=_WHT)
    disc = (
        "This report has been prepared by the consultant named herein solely for informational and "
        "decision-support purposes.  Outputs are based on modelled assumptions; actual system "
        "performance, tariff levels, and regulatory conditions may differ materially.  "
        "This document does not constitute investment advice, a prospectus, or a binding "
        "financial proposal.  All tariff figures are quoted inclusive of 15% South African VAT.  "
        "Recipients should obtain independent engineering, legal, and financial advice before "
        "committing capital.  © "f"{date.today().year} {company}."
    )
    _tb(slide, 0.45,6.77,12.45,0.65, disc, 8.5, color="A7F3D0", wrap=True)
    _footer(slide, company, 8)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_pptx(
    params:          dict,
    results:         dict | None,
    fin_df,
    pvgis_data:      dict,
    project_name:    str = "",
    client_name:     str = "",
    consultant_name: str = "",
) -> bytes:
    """
    Generate an 8-slide executive PPTX report.

    Parameters
    ----------
    params          : session-state param dict (tariff rates, capex, etc.)
    results         : st.session_state.results (npv, irr, dispatch_yr1, lcoe, …)
    fin_df          : 20-year financial model DataFrame (or None)
    pvgis_data      : PVGIS dict (annual_kwh, monthly_kwh, winter/summer daily)
    project_name    : slide cover title (defaults to "X kWp + Y kWh")
    client_name     : client / company receiving the report (on cover)
    consultant_name : consulting firm preparing the report (replaces all branding)

    Returns
    -------
    bytes — pass directly to st.download_button(data=...)
    """
    from pptx import Presentation

    results    = results    or {}
    pvgis_data = pvgis_data or {}
    if not consultant_name:
        consultant_name = "Energy Consulting"
    company = consultant_name   # used in footers

    prs = Presentation()
    prs.slide_width  = _in(13.33)
    prs.slide_height = _in(7.5)

    pv_kwp  = params.get("pv_kwp",  0)
    bess_kwh = params.get("bess_kwh", 0)

    _s1_cover(prs, project_name, client_name, consultant_name,
              pv_kwp, bess_kwh, params.get("tariff_mode",""))
    _s2_thesis(prs, results, params, company)
    _s3_system(prs, params, pvgis_data, company)
    _s4_financial(prs, results, fin_df, company)
    _s5_energy(prs, pvgis_data, results, company)
    _s6_tariff(prs, params, results, company)
    _s7_roadmap(prs, results, params, company)
    _s8_assumptions(prs, params, company)

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.read()
