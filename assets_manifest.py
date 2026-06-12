"""
assets_manifest.py  —  Huawei Digital Power asset catalogue
============================================================
Central registry of all static media assets bundled with the btm_system
report generator.  Each asset is tagged with one or more scenario labels
so that `report_pptx.py` can select context-appropriate imagery.

Scenario tags
-------------
  "pv"    — Solar PV specific
  "bess"  — Battery / ESS specific
  "both"  — Suitable for any scenario

Asset types
-----------
  "hero"     — full-width background / banner photograph
  "product"  — white-background equipment render
  "brand"    — brand / marketing image
  "cert"     — certification / compliance showcase
  "video"    — reserved for future video assets

Directory layout (relative to this file)
-----------------------------------------
  assets/pv/      ← PV-only equipment renders + hero
  assets/bess/    ← BESS-only equipment renders + hero
  assets/common/  ← brand / cert / cover assets for any scenario
  assets/         ← legacy root-level site photos and logos
"""
from __future__ import annotations
import os

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")


# ── Asset registry ─────────────────────────────────────────────────────────────
ASSETS: dict[str, dict] = {

    # ── Cover ─────────────────────────────────────────────────────────────────
    # Used as cover background for ALL scenario modes (PV-only, BESS-only, PV+BESS)
    "huge_bess_deployed": {
        "file": "common/Huge_BESS_Project_Deployed.png",
        "tags": ["pv", "bess"],
        "type": "hero",
        "desc": "Aerial view of a large-scale BESS deployment — cover background (all scenarios)",
    },

    # ── PV — product renders ──────────────────────────────────────────────────
    "sun2000_controller": {
        "file": "pv/prod_sun2000_controller.png",
        "tags": ["pv"],
        "type": "product",
        "desc": "SUN2000 String Inverter Controller — utility / C&I",
    },
    "sun2000_150k": {
        "file": "pv/prod_sun2000_150k.png",
        "tags": ["pv"],
        "type": "product",
        "desc": "SUN2000 150KTL Utility-Scale String Inverter",
    },
    "sun2000_506ktl": {
        "file": "pv/prod_sun2000_506ktl.png",
        "tags": ["pv"],
        "type": "product",
        "desc": "SUN2000 506KTL-H Utility Central Inverter",
    },
    "module_controller": {
        "file": "pv/prod_module_controller.png",
        "tags": ["pv"],
        "type": "product",
        "desc": "Smart Module Controller (MLPE optimiser)",
    },
    "merc_module_controller": {
        "file": "pv/prod_merc_module_controller.png",
        "tags": ["pv"],
        "type": "product",
        "desc": "Mercury Smart Module Controller",
    },
    "jupt_transformer": {
        "file": "pv/prod_jupt_transformer.png",
        "tags": ["pv"],
        "type": "product",
        "desc": "Jupiter Step-Up Transformer (utility PV)",
    },
    "smartguard": {
        "file": "pv/prod_smartguard.png",
        "tags": ["pv"],
        "type": "product",
        "desc": "SmartGuard Arc-Fault / Protection Device",
    },
    "pv_plant_mgmt": {
        "file": "pv/prod_pv_plant_mgmt.png",
        "tags": ["pv"],
        "type": "brand",
        "desc": "FusionSolar Plant Management Dashboard (UI screenshot 1)",
    },
    "pv_plant_mgmt2": {
        "file": "pv/prod_pv_plant_mgmt2.png",
        "tags": ["pv"],
        "type": "brand",
        "desc": "FusionSolar Plant Management Dashboard (UI screenshot 2)",
    },
    "hero_pv": {
        "file": "pv/hero_fusionsolar9_utility.jpg",
        "tags": ["pv"],
        "type": "hero",
        "desc": "FusionSolar 9 Utility PV — dark-background hero photograph (PV slides)",
    },

    # ── BESS — product renders ────────────────────────────────────────────────
    "luna2000_gridforming": {
        "file": "bess/prod_luna2000_4472_gridforming.png",
        "tags": ["bess"],
        "type": "product",
        "desc": "LUNA2000 4472 Grid-Forming Container ESS — utility / large C&I",
    },
    "luna2000_pcs": {
        "file": "bess/prod_luna2000_213ktl_pcs.png",
        "tags": ["bess"],
        "type": "product",
        "desc": "LUNA2000 213KTL Power Conversion System (PCS)",
    },
    "cert_safety": {
        "file": "bess/cert_safety.png",
        "tags": ["bess"],
        "type": "cert",
        "desc": "System safety certification showcase: ESS container + PCS + TUV Rheinland certificate",
    },
    "hero_bess": {
        "file": "bess/hero_ess_grid_forming.jpg",
        "tags": ["bess"],
        "type": "hero",
        "desc": "Grid-Forming ESS Stack — dark-background hero photograph",
    },

    # ── Common — brand ────────────────────────────────────────────────────────
    "fusionsolar_logo": {
        "file": "common/brand_fusionsolar_logo.png",
        "tags": ["pv", "bess"],
        "type": "brand",
        "desc": "FusionSolar Brand Logo (transparent background)",
    },
    "professional_services": {
        "file": "common/brand_professional_services.png",
        "tags": ["pv", "bess"],
        "type": "brand",
        "desc": "Huawei Professional Services — marketing brand image",
    },
}


# ── Helper functions ───────────────────────────────────────────────────────────

def asset_path(key: str) -> str | None:
    """
    Return the absolute filesystem path for an asset key.
    Returns None if the key is unknown or the file does not exist on disk.
    """
    entry = ASSETS.get(key)
    if not entry:
        return None
    p = os.path.join(_ASSETS_DIR, entry["file"])
    return p if os.path.exists(p) else None


def list_assets(tag: str | None = None,
                asset_type: str | None = None) -> list[dict]:
    """Return a list of all asset entries, optionally filtered by tag / type."""
    result = []
    for key, entry in ASSETS.items():
        if tag is not None and tag not in entry["tags"]:
            continue
        if asset_type is not None and entry["type"] != asset_type:
            continue
        result.append({"key": key, **entry, "path": asset_path(key)})
    return result


# ── Scenario-based selectors (used directly by report_pptx.py) ────────────────

def cover_hero(has_pv: bool = True, has_bess: bool = True) -> str | None:
    """
    Cover background image — hw_kv_dark.jpg (Huawei KV dark) for clarity and
    overall slide quality.  Falls back to the aerial BESS deployment if missing.
    """
    # Primary: high-quality Huawei KV dark photo
    primary = os.path.join(_ASSETS_DIR, "hw_kv_dark.jpg")
    if os.path.exists(primary):
        return primary
    # Fallback: large-scale BESS deployment aerial
    p = asset_path("huge_bess_deployed")
    if p:
        return p
    return None


def system_product_image(has_pv: bool, has_bess: bool) -> tuple[str | None, str]:
    """
    Primary product image + caption for the System Overview slide right panel.
    Only called for single-component (PV-only or BESS-only) mode.
    """
    if has_pv and not has_bess:
        return (
            asset_path("sun2000_controller"),
            "Huawei SUN2000 String Inverter  ·  Huawei Digital Power",
        )
    # BESS-only: LUNA2000 213KTL PCS — near-square product render, ideal for panel
    return (
        asset_path("luna2000_pcs"),
        "Huawei LUNA2000 213KTL PCS  ·  Huawei Digital Power",
    )


def tariff_product_image() -> str | None:
    """
    BESS product / cert image for the Tariff Opportunity slide dispatch block.
    cert_safety (landscape ESS + certificate) fits well in the dispatch inset.
    """
    return asset_path("cert_safety")


def energy_pv_hero() -> str | None:
    """
    Hero photograph for the PV Energy Analysis slide — FusionSolar 9 utility lineup.
    Displayed as a full-width cinematic strip below the slide header.
    """
    return asset_path("hero_pv")
