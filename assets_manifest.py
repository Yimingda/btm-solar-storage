"""
assets_manifest.py  —  Huawei Digital Power asset catalogue
============================================================
Central registry of all static media assets bundled with the btm_system
report generator.  Each asset is tagged with one or more scenario labels
so that `report_pptx.py` can select context-appropriate imagery without
hard-coded paths.

Scenario tags
-------------
  "pv"    — Solar PV specific (inverters, module controllers, plant mgmt)
  "bess"  — Battery / ESS specific (LUNA2000, ACU, PCS, safety cert)
  "both"  — Brand / common assets suitable for any slide

Asset types
-----------
  "hero"     — full-width background / banner photograph
  "product"  — white-background equipment render (portrait or square)
  "brand"    — brand / marketing image (may contain people or installations)
  "cert"     — certification or compliance showcase
  "video"    — reserved for future video assets

Directory layout (relative to this file)
-----------------------------------------
  assets/pv/      ← PV-only equipment renders
  assets/bess/    ← BESS-only equipment renders
  assets/common/  ← brand / cert assets for both scenarios
  assets/         ← legacy root-level assets (existing site photos, logos)
"""
from __future__ import annotations
import os

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")


# ── Asset registry ─────────────────────────────────────────────────────────────
# Key        : short logical name used by report_pptx.py
# file        : path relative to _ASSETS_DIR
# tags        : list of scenario labels ("pv", "bess", "both")
# type        : "hero" | "product" | "brand" | "cert" | "video"
# desc        : human-readable description for tooltips / logs
# ──────────────────────────────────────────────────────────────────────────────
ASSETS: dict[str, dict] = {

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
        "desc": "FusionSolar 9 Utility PV Solution — dark-background hero photograph",
    },

    # ── BESS — product renders ────────────────────────────────────────────────
    "luna2000_string_ess": {
        "file": "bess/prod_luna2000_string_ess.png",
        "tags": ["bess"],
        "type": "product",
        "desc": "LUNA2000 String ESS Cabinet — residential / C&I BTM",
    },
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
    "luna2000_ci": {
        "file": "bess/prod_luna2000_241_ci.png",
        "tags": ["bess"],
        "type": "product",
        "desc": "LUNA2000 241 C&I BESS Cabinet",
    },
    "smartacu2000f": {
        "file": "bess/prod_smartacu2000f.png",
        "tags": ["bess"],
        "type": "product",
        "desc": "Smart ACU 2000F — active cooling unit for large-scale ESS",
    },
    "cert_safety": {
        "file": "bess/cert_safety.png",
        "tags": ["bess"],
        "type": "cert",
        "desc": "Safety certification showcase: container ESS + PCS + TUV Rheinland certificate",
    },
    "hero_bess": {
        "file": "bess/hero_ess_grid_forming.jpg",
        "tags": ["bess"],
        "type": "hero",
        "desc": "Grid-Forming ESS Stack — dark-background hero photograph",
    },

    # ── Common — brand / certification ────────────────────────────────────────
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
    "security_stability": {
        "file": "common/brand_security_stability.png",
        "tags": ["pv", "bess"],
        "type": "brand",
        "desc": "Security & Stability brand graphic (suitable for partner/trust slides)",
    },
    "cert_recognition": {
        "file": "common/cert_recognition.png",
        "tags": ["pv", "bess"],
        "type": "cert",
        "desc": "Certification recognition badge / award",
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
    """
    Return a list of all asset entries, optionally filtered.

    Parameters
    ----------
    tag         : "pv", "bess", or None (all tags)
    asset_type  : "hero", "product", "brand", "cert", "video", or None (all)

    Each entry in the returned list is the original dict with two extra keys:
      "key"  : the logical name
      "path" : absolute path (or None if file missing)
    """
    result = []
    for key, entry in ASSETS.items():
        if tag is not None and tag not in entry["tags"]:
            continue
        if asset_type is not None and entry["type"] != asset_type:
            continue
        result.append({"key": key, **entry, "path": asset_path(key)})
    return result


# ── Scenario-based selectors (used directly by report_pptx.py) ────────────────

def cover_hero(has_pv: bool, has_bess: bool) -> str | None:
    """
    Best cover hero image for a given scenario.
    Falls back to the legacy hw_kv_dark.jpg for PV+BESS.
    """
    if has_bess and not has_pv:
        # BESS-only: ESS container hero
        p = asset_path("hero_bess")
        if p:
            return p
    if has_pv and not has_bess:
        # PV-only: FusionSolar utility hero
        p = asset_path("hero_pv")
        if p:
            return p
    # PV+BESS (or fallback): use existing legacy dark hero
    legacy = os.path.join(_ASSETS_DIR, "hw_kv_dark.jpg")
    return legacy if os.path.exists(legacy) else None


def system_product_image(has_pv: bool, has_bess: bool) -> tuple[str | None, str]:
    """
    Primary product image + caption for the System Overview slide.

    Returns
    -------
    (absolute_path_or_None, caption_text)
    """
    if has_pv and not has_bess:
        return (
            asset_path("sun2000_controller"),
            "Huawei SUN2000 String Inverter  ·  Huawei Digital Power",
        )
    if has_bess and not has_pv:
        return (
            asset_path("luna2000_string_ess"),
            "Huawei LUNA2000 String ESS  ·  Huawei Digital Power",
        )
    # PV+BESS: cert_safety is the full-system lifestyle photo
    return (
        asset_path("cert_safety"),
        "Huawei ESS + PCS  ·  TUV Rheinland Certified  ·  Huawei Digital Power",
    )


def energy_product_image() -> str | None:
    """PV product image for the Energy Analysis slide right panel."""
    return asset_path("sun2000_controller")


def tariff_product_image() -> str | None:
    """BESS product image for the Tariff Opportunity slide right panel."""
    return asset_path("luna2000_string_ess")


def huawei_partner_cert() -> str | None:
    """Certification image for Huawei Partner slide."""
    return asset_path("cert_recognition")
