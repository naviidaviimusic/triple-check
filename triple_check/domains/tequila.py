"""Tequila domain: a curated agronomy + business fact base, a deterministic
agave→bottle supply-chain calculator, and two expert personas (agronomist and
industry analyst).

Figures are curated estimates from public industry knowledge (CRT, Diageo /
Bacardi / Becle disclosures, trade press). They are honest ballparks with
confidence and as-of flags, not live data. Update them here, never in prompts.
"""

from __future__ import annotations

import re

from ..cell import Cell, Expert
from ..facts import FactBase

FACTS = {

    # ════════════════════ AGRONOMY / FARMING ════════════════════
    "agave_species": {
        "value": "Agave tequilana Weber, Blue variety (Weber Azul)",
        "unit": "species", "confidence": "HIGH", "as_of": 2024,
        "note": "The ONLY agave legally permitted for tequila under NOM-006-SCFI.",
    },
    "maturity_years": {
        "value": 7, "unit": "years", "lo": 6, "hi": 8,
        "confidence": "HIGH", "as_of": 2024,
        "note": "Time from planting to harvest (jima). Highlands often 7-8y.",
    },
    "plants_per_hectare": {
        "value": 3000, "unit": "plants/ha", "lo": 2000, "hi": 4000,
        "confidence": "MEDIUM", "as_of": 2024,
        "note": "Traditional ~2,500-3,000; high-density up to ~4,000.",
    },
    "plants_per_acre": {
        "value": 1200, "unit": "plants/acre", "lo": 1000, "hi": 2000,
        "confidence": "MEDIUM", "as_of": 2024,
        "note": "1 ha = 2.47 acres. Density depends on row spacing for machinery.",
    },
    "pina_weight_kg": {
        "value": 40, "unit": "kg", "lo": 25, "hi": 90,
        "confidence": "MEDIUM", "as_of": 2024,
        "note": "Harvested piña (cored heart). Highlands agave runs larger.",
    },
    "agave_kg_per_liter": {
        "value": 7, "unit": "kg agave / L", "lo": 6, "hi": 8,
        "confidence": "HIGH", "as_of": 2024,
        "note": "~7 kg agave per liter of 100% agave tequila (industry rule of thumb).",
    },
    "liters_per_plant": {
        "value": 6, "unit": "L / plant", "lo": 4, "hi": 9,
        "confidence": "MEDIUM", "as_of": 2024,
        "note": "Derived: piña weight ÷ ~7 kg/L. ~5-7 L common → ~7-10 bottles.",
    },
    "bottles_per_plant": {
        "value": 8, "unit": "750ml bottles / plant", "lo": 7, "hi": 10,
        "confidence": "MEDIUM", "as_of": 2024,
        "note": "liters_per_plant ÷ 0.75. Varies widely with piña size + method.",
    },
    "harvest_brix": {
        "value": 25, "unit": "% sugar (Brix)", "lo": 24, "hi": 28,
        "confidence": "MEDIUM", "as_of": 2024,
        "note": "Target sugar concentration at harvest; jimador trims with a coa.",
    },
    "propagation": {
        "value": "Clonal via hijuelos (offshoots/pups)",
        "unit": "method", "confidence": "HIGH", "as_of": 2024,
        "note": "Largely clonal monoculture → low genetic diversity, disease risk.",
    },
    "key_pests": {
        "value": "Agave weevil (Scyphophorus acupunctatus); Fusarium/Erwinia rots; "
                 "TMA complex (tristeza y muerte del agave)",
        "unit": "pests/disease", "confidence": "HIGH", "as_of": 2024,
        "note": "Weevil larvae bore the piña; fungal/bacterial wilt spread by monoculture.",
    },
    "do_region": {
        "value": "Jalisco (entire state) + designated municipalities of Guanajuato, "
                 "Michoacán, Nayarit, and Tamaulipas",
        "unit": "Denomination of Origin", "confidence": "HIGH", "as_of": 2024,
        "note": "Tequila DO is geographically protected; ~181 municipalities total.",
    },
    "terroir": {
        "value": "Los Altos (highlands) red iron-rich volcanic soil → larger, sweeter, "
                 "fruitier agave; Valles (lowlands, near Tequila town) → earthier/herbal",
        "unit": "terroir", "confidence": "MEDIUM", "as_of": 2024,
        "note": "Two principal growing zones with distinct flavor profiles.",
    },

    # ════════════════════ BUSINESS / MARKET ════════════════════
    "regulator": {
        "value": "CRT — Consejo Regulador del Tequila",
        "unit": "body", "confidence": "HIGH", "as_of": 2024,
        "note": "Certifies producers, enforces NOM-006-SCFI, audits agave-to-bottle.",
    },
    "nom_standard": {
        "value": "NOM-006-SCFI-2012",
        "unit": "standard", "confidence": "HIGH", "as_of": 2024,
        "note": "Each producer carries a NOM ID (distillery registration number).",
    },
    "categories": {
        "value": "Blanco/Silver (0-2 mo); Reposado (2-12 mo oak); Añejo (1-3 yr); "
                 "Extra Añejo (3+ yr); Joven/Gold (blended/colored)",
        "unit": "classes", "confidence": "HIGH", "as_of": 2024,
        "note": "Aging classes per NOM. Also 100% agave vs mixto (≥51% agave).",
    },
    "industry_production_liters": {
        "value": 600_000_000, "unit": "L/year", "lo": 500_000_000, "hi": 650_000_000,
        "confidence": "MEDIUM", "as_of": 2023,
        "note": "Total tequila output near record highs (~599M L in 2022 per CRT).",
    },
    "agave_consumed_tonnes": {
        "value": 1_500_000, "unit": "tonnes/year", "lo": 1_300_000, "hi": 2_000_000,
        "confidence": "MEDIUM", "as_of": 2023,
        "note": "Agave milled industry-wide; tracks production volume.",
    },
    "export_share": {
        "value": 80, "unit": "% exported", "lo": 70, "hi": 85,
        "confidence": "MEDIUM", "as_of": 2023,
        "note": "Majority of tequila is exported; US is ~80% of exports.",
    },
    "top_market": {
        "value": "United States",
        "unit": "market", "confidence": "HIGH", "as_of": 2024,
        "note": "Largest consumer; tequila/mezcal rivaling American whiskey in US.",
    },

    # ── Brand volumes (9-L cases/year) ──
    "brand_jose_cuervo_cases": {
        "value": 9_000_000, "unit": "9L cases/yr", "lo": 8_000_000, "hi": 10_000_000,
        "confidence": "MEDIUM", "as_of": 2023,
        "note": "#1 tequila by volume worldwide (Becle). ~108M bottles/yr.",
    },
    "brand_casamigos_cases": {
        "value": 4_000_000, "unit": "9L cases/yr", "lo": 3_000_000, "hi": 5_000_000,
        "confidence": "MEDIUM", "as_of": 2023,
        "note": "Diageo; fastest-growing super-premium. ~48M bottles/yr.",
    },
    "brand_don_julio_cases": {
        "value": 3_300_000, "unit": "9L cases/yr", "lo": 2_800_000, "hi": 4_000_000,
        "confidence": "MEDIUM", "as_of": 2023,
        "note": "Diageo; momentum leader. ~40M bottles/yr.",
    },
    "brand_patron_cases": {
        "value": 3_000_000, "unit": "9L cases/yr", "lo": 2_500_000, "hi": 3_500_000,
        "confidence": "MEDIUM", "as_of": 2023,
        "note": "Bacardi; original super-premium volume king. ~36M bottles/yr.",
    },
    "bottles_per_case": {
        "value": 12, "unit": "bottles (750ml) / 9L case", "lo": 12, "hi": 12,
        "confidence": "HIGH", "as_of": 2024,
        "note": "Standard 9-L case = 12 × 750ml. Conversion constant.",
    },

    # ── M&A / valuation ──
    "ma_casamigos": {
        "value": "Diageo acquired Casamigos (2017) for ~$1.0B upfront (+ up to $0.5B earnout)",
        "unit": "deal", "confidence": "HIGH", "as_of": 2017,
        "note": "Founded by Clooney, Gerber, Meldman. Landmark celebrity-spirits exit.",
    },
    "ma_patron": {
        "value": "Bacardi acquired Patrón (2018) at ~$5.1B enterprise value",
        "unit": "deal", "confidence": "HIGH", "as_of": 2018,
        "note": "Bacardi bought remaining stake; valued the brand ~$5.1B total.",
    },

    # ── Agave price cycle (the 'hog cycle') ──
    "agave_price_peso_per_kg": {
        "value": 25, "unit": "MXN/kg (cycle peak)", "lo": 2, "hi": 30,
        "confidence": "MEDIUM", "as_of": 2022,
        "note": "Classic boom/bust from the ~7y planting lag: ~2-3 MXN/kg (2016) → "
                "~25-30 MXN/kg peak (2021-22) → crashed toward ~5 MXN/kg (2023-24).",
    },
    "agave_cycle_years": {
        "value": 7, "unit": "years (supply lag)", "lo": 6, "hi": 8,
        "confidence": "HIGH", "as_of": 2024,
        "note": "The maturation lag IS the cause of price cycles — plant today, "
                "harvest in 7y, so supply chronically over/undershoots demand.",
    },
}

# Words in free text that point a nearby number at a fact.
# Association is by nearest keyword; order only breaks ties.
HINTS = [
    (r"per\s+acre|/\s*acre|an?\s+acre", "plants_per_acre"),
    (r"per\s+hectare|/\s*ha\b|hectare", "plants_per_hectare"),
    (r"matures?\s+in|years?\s+to\s+(?:harvest|matur)|\d\s*-?\s*years?\b|"
     r"year\s+cycle|year\s+lifecycle", "maturity_years"),
    (r"bottles?\s+(?:per|/|from|a|each)\s+(?:a\s+)?plant|per\s+plant", "bottles_per_plant"),
    (r"lit\w+\s+(?:per|/)\s+plant|l\s*/\s*plant", "liters_per_plant"),
    (r"kg\s+per\s+lit|kg\s*/\s*l|agave\s+per\s+lit", "agave_kg_per_liter"),
    (r"pi[ñn]a|heart\s+weigh", "pina_weight_kg"),
    (r"brix|sugar\s+at\s+harvest", "harvest_brix"),
    (r"cuervo", "brand_jose_cuervo_cases"),
    (r"casamigos", "brand_casamigos_cases"),
    (r"don\s*julio", "brand_don_julio_cases"),
    (r"patr[oó]n", "brand_patron_cases"),
    (r"export", "export_share"),
    (r"agave\s+price|peso.*kg|mxn.*kg", "agave_price_peso_per_kg"),
    (r"price\s+cycle|hog\s+cycle|supply\s+lag", "agave_cycle_years"),
    (r"industry\s+produc\w+|total\s+produc\w+", "industry_production_liters"),
]

FARMING_KEYS = {
    "agave_species", "maturity_years", "plants_per_hectare", "plants_per_acre",
    "pina_weight_kg", "agave_kg_per_liter", "liters_per_plant", "bottles_per_plant",
    "harvest_brix", "propagation", "key_pests", "do_region", "terroir",
    "agave_cycle_years",
}
BUSINESS_EXCLUDE = FARMING_KEYS - {"agave_cycle_years", "maturity_years", "do_region"}


# ── DETERMINISTIC CALCULATOR ─────────────────────────────────────────────────────
# LLMs botch arithmetic. All supply-chain math is computed here, in Python, from
# the verified constants — never left to the model. The agents EXPLAIN these
# numbers; they do not calculate them.
LITERS_PER_CASE   = 9.0     # a 9-litre case is 9 L (12 × 750ml)
LITERS_PER_BOTTLE = 0.75


def supply_chain(cases_per_year: float,
                 density_per_acre: float | None = None,
                 liters_per_plant: float | None = None,
                 maturity_years: int | None = None) -> dict:
    """
    Full, deterministic agave→bottle supply chain for an annual case volume.
    Returns every intermediate with the assumptions used, so it is auditable.

    standing_acres = annual harvest acres × maturity years, because a plant
    occupies land for its whole ~7-year life but is harvested only once.
    """
    density = density_per_acre if density_per_acre is not None else float(FACTS["plants_per_acre"]["value"])
    lpp     = liters_per_plant if liters_per_plant is not None else float(FACTS["liters_per_plant"]["value"])
    mat     = maturity_years if maturity_years is not None else int(FACTS["maturity_years"]["value"])
    kg_per_l = float(FACTS["agave_kg_per_liter"]["value"])

    liters   = cases_per_year * LITERS_PER_CASE
    bottles  = liters / LITERS_PER_BOTTLE
    agave_kg = liters * kg_per_l
    plants_harvested = liters / lpp                  # plants cut per year
    acres_harvested  = plants_harvested / density    # land harvested per year
    standing_acres   = acres_harvested * mat         # total land in production

    return {
        "inputs": {
            "cases_per_year": cases_per_year,
            "density_per_acre": density,
            "liters_per_plant": lpp,
            "maturity_years": mat,
            "agave_kg_per_liter": kg_per_l,
        },
        "liters_per_year": round(liters),
        "bottles_per_year": round(bottles),
        "agave_tonnes_per_year": round(agave_kg / 1000),
        "plants_harvested_per_year": round(plants_harvested),
        "acres_harvested_per_year": round(acres_harvested),
        "standing_acres_in_production": round(standing_acres),
    }


def format_supply_chain(sc: dict) -> str:
    i = sc["inputs"]
    return (
        "VERIFIED CALCULATION (computed in Python from the fact base — not estimated):\n"
        f"  • {i['cases_per_year']:,.0f} cases/yr × 9 L = {sc['liters_per_year']:,} L/yr "
        f"= {sc['bottles_per_year']:,} bottles/yr\n"
        f"  • Agave milled: {sc['agave_tonnes_per_year']:,} tonnes/yr "
        f"(at {i['agave_kg_per_liter']} kg/L)\n"
        f"  • Plants harvested: {sc['plants_harvested_per_year']:,}/yr "
        f"(at {i['liters_per_plant']} L/plant)\n"
        f"  • Land harvested: {sc['acres_harvested_per_year']:,} acres/yr "
        f"(at {i['density_per_acre']:,.0f} plants/acre)\n"
        f"  • STANDING ACREAGE in production: {sc['standing_acres_in_production']:,} acres "
        f"(× {i['maturity_years']}-yr maturity)"
    )


BRAND_ANCHORS = {
    "cuervo": "brand_jose_cuervo_cases",
    "casamigos": "brand_casamigos_cases",
    "don julio": "brand_don_julio_cases",
    "patron": "brand_patron_cases",
    "patrón": "brand_patron_cases",
}
SUPPLY_WORDS = ("acre", "hectare", "plant", "supply", "grow", "land", "agave needed",
                "how many liters", "how much agave", "tonnes", "volume", "produce")


def supply_calculator(question: str) -> str:
    """CHECK 0: supply/acreage questions about a known brand (or "<n> million
    cases") get a VERIFIED CALCULATION block computed in Python."""
    q = question.lower()
    if not any(w in q for w in SUPPLY_WORDS):
        return ""
    cases = label = None
    for brand, key in BRAND_ANCHORS.items():
        if brand in q:
            cases, label = float(FACTS[key]["value"]), brand.title()
            break
    if cases is None:
        m = re.search(r"(\d[\d,\.]*)\s*(million|m)\s*(9.?l(?:itre|iter)?\s*)?cases", q)
        if m:
            cases, label = float(m.group(1).replace(",", "")) * 1_000_000, "specified"
    if cases is None:
        return ""
    sc = supply_chain(cases)
    sc2k = supply_chain(cases, density_per_acre=2000)
    return (f"[{label}: {cases:,.0f} 9L cases/yr]\n" + format_supply_chain(sc) +
            f"\n  • (at higher 2,000 plants/acre density → "
            f"{sc2k['standing_acres_in_production']:,} standing acres)")


FARMING_WORDS = ("agave", "plant", "soil", "harvest", "yield", "acre", "hectare",
                 "pest", "weevil", "grow", "cultivat", "jima", "brix", "piña", "pina",
                 "irrigat", "field", "crop", "maturity")
BUSINESS_WORDS = ("brand", "case", "bottle", "sell", "sales", "market", "price",
                  "margin", "export", "revenue", "valuation", "m&a", "cuervo",
                  "casamigos", "patron", "patrón", "don julio", "cost", "profit",
                  "consumer", "demand")

FARMING_PERSONA = (
    "You are a master agave agronomist with 30 years cultivating Agave tequilana "
    "Weber Azul in Jalisco's highlands and valleys. You speak precisely about the "
    "6-8 year lifecycle, planting density, red volcanic soil, hijuelo propagation, "
    "the agave weevil and Fusarium wilt, Brix at harvest, the jima, and yield. "
    "You ALWAYS ground numbers in the verified reference ranges below. If you state "
    "a figure, keep it inside those ranges; if you must deviate, say so explicitly. "
    "Be concrete and quantitative. No filler."
)

BUSINESS_PERSONA = (
    "You are a tequila industry analyst who knows every number in the category: "
    "brand case volumes, the 9-litre case math, super-premium pricing, CRT/NOM "
    "regulation, US export dependence, landmark M&A (Diageo-Casamigos, Bacardi-"
    "Patron), and the agave price cycle driven by the 7-year planting lag. You ALWAYS "
    "cite figures with a range and an as-of year, and you keep numbers inside the "
    "verified reference ranges below. If you must deviate, say so explicitly and "
    "label it an estimate. Be precise, quantitative, and concise."
)


def make_cell(expert_model: str = "qwen2.5:3b", verifier_model: str = "llama3.2",
              ask=None) -> Cell:
    facts = FactBase(FACTS, HINTS)
    experts = [
        Expert("farming", FARMING_PERSONA, expert_model, FARMING_WORDS,
               fact_filter=lambda k: k in FARMING_KEYS),
        Expert("business", BUSINESS_PERSONA, expert_model, BUSINESS_WORDS,
               fact_filter=lambda k: k not in BUSINESS_EXCLUDE),
    ]
    kw = {"ask": ask} if ask else {}
    return Cell(facts, experts, verifier_model, [supply_calculator], **kw)
