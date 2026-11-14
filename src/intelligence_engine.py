import re

MISSION_PROFILES = {
    "Lunar Habitat (Moon Base)": {
        "o2_pct": 32.0,
        "pressure_psi": 10.2,
        "gravity": "1/6 g (Partial Gravity)",
        "description": "Exploration Atmosphere: Elevated O2 (≥30%) and reduced pressure (≤10.2 psi) to minimize EVA pre-breathe time.",
        "priority_keywords": ["saffire", "bass", "flammability", "oxygen", "solid", "cfi-g", "cool flames", "acme", "e-field"],
        "risk_factors": {
            "Ignition Likelihood": ("High", "O2 concentration ≥30% (>40% increase over Earth) significantly lowers minimum ignition energy."),
            "Material Flammability": ("Critical", "BASS & Saffire show flame spread accelerates with O2% and low-speed forced ventilation."),
            "Partial-Gravity Uncertainty": ("High Uncertainty", "CRITICAL LIMITATION: PSI currently lacks true 1/6g data (pending LUCI & FM2). E-FIELD Flames only mimics partial-g via electric fields."),
            "Suppression Effectiveness": ("Moderate-High", "FLEX studies show CO2/Helium dilution suppresses flames, but enclosed habitat CO2 toxicity limits apply.")
        }
    },
    "Pressurized Lunar/Mars Rover": {
        "o2_pct": 34.0,
        "pressure_psi": 8.2,
        "gravity": "1/6 g to 3/8 g",
        "description": "Compact high-oxygen cabin (up to 34% O2, 8.2 psi) with tight equipment density and rapid egress constraints.",
        "priority_keywords": ["bass", "bre", "same", "smoke", "detection", "flex", "suppression", "oxygen", "dust", "daft"],
        "risk_factors": {
            "Ignition Likelihood": ("Critical", "Up to 34% O2 in compact volume near avionics and suit interfaces."),
            "Detection & Dust Interference": ("High", "SAME & DAFT show lunar/martian dust aerosols can trigger false alarms or mask early smoke signatures."),
            "Fire Propagation": ("Critical", "Small cabin volume leads to rapid pressure spike and toxic gas accumulation."),
            "Partial-Gravity Uncertainty": ("High Uncertainty", "No true lunar/martian gravity combustion datasets exist in PSI yet.")
        }
    },
    "International Space Station (ISS)": {
        "o2_pct": 21.0,
        "pressure_psi": 14.7,
        "gravity": "Microgravity (~10^-6 g)",
        "description": "Earth-normal atmosphere (21% O2, 14.7 psi) in continuous microgravity with forced rack ventilation.",
        "priority_keywords": ["iss", "msg", "cir", "saffire", "bass", "same", "flex", "acme", "spice", "slice"],
        "risk_factors": {
            "Ignition Likelihood": ("Moderate", "21% O2 standard atmosphere, but absence of buoyancy eliminates convective cooling of electronics."),
            "Smoke Detection": ("Moderate-High", "SAME/SAME-R show microgravity smoke particle size distribution differs from Earth, requiring specialized optical/ionization detectors."),
            "Ventilation-Driven Spread": ("High", "Without buoyancy, HVAC airflow controls flame spread direction and intensity (BASS-II / SPICE)."),
            "Data Confidence": ("High (Direct Evidence)", "Directly supported by decades of ISS CIR, MSG, and Cygnus Saffire flight experiments.")
        }
    },
    "Mars Surface Habitat": {
        "o2_pct": 26.0,
        "pressure_psi": 11.0,
        "gravity": "3/8 g (Partial Gravity)",
        "description": "Long-duration isolated surface habitat with elevated O2, martian dust ingress, and zero rapid-return capability.",
        "priority_keywords": ["saffire", "bass", "daft", "dust", "same", "flex", "acme", "extinction"],
        "risk_factors": {
            "Material Flammability": ("High", "Elevated O2 combined with long-duration material aging increases flammability risk."),
            "Dust & Aerosol Hazard": ("High", "DAFT/DAFT-2 highlight fine particulate interference with optical smoke detection systems."),
            "Partial-Gravity Uncertainty": ("High Uncertainty", "No 3/8g combustion data in PSI; microgravity and 1g data only bound expected behavior."),
            "Suppression & Recovery": ("Critical", "Closed-loop life support must scrub combustion byproducts without resupply.")
        }
    }
}

def check_scope_guardrails(query: str) -> list[str]:
    warnings = []
    q_lower = query.lower()
    if any(w in q_lower for w in ["rocket", "propellant", "thruster", "engine combustion", "booster"]):
        warnings.append("⚠️ **Scientific Scope Notice:** Rocket and propellant fire safety is outside the scope of NASA's PSI database (high-velocity engine combustion is effectively gravity-independent).")
    if any(w in q_lower for w in ["moon", "lunar", "mars", "martian", "partial gravity", "1/6", "3/8"]):
        warnings.append("ℹ️ **Data Limitation Notice:** Partial-gravity combustion data is not yet available in PSI (awaiting future missions like LUCI and FM2). Microgravity and 1g data bound expected behavior, while ACME's E-FIELD Flames mimicked partial gravity using electric fields.")
    return warnings

def rank_studies_for_mission(mission_name: str, studies_list: list, custom_query: str = "", top_k: int = 6):
    profile = MISSION_PROFILES[mission_name]
    mission_kw = profile["priority_keywords"]
    query_tokens = set(re.findall(r'[a-z0-9\-]+', custom_query.lower()))
    exact_ids = set(re.findall(r'psi-\d+', custom_query.lower()))

    ranked = []
    for s in studies_list:
        score = 0
        reasons = []
        s_id = s.get("study_id", "")
        acronym = (s.get("acronym") or "").lower()
        title = (s.get("title") or "").lower()
        pillars = s.get("fire_safety_pillars", [])
        full_text = f"{s_id} {title} {acronym} {' '.join(pillars)} {s.get('objective', '')} {s.get('approach', '')} {' '.join(s.get('keywords', []))}".lower()

        # 1. Exact ID boost
        if s_id.lower() in exact_ids:
            score += 50
            reasons.append(f"Direct match for {s_id}")

        # 2. Mission-specific keyword relevance
        matched_mission_kw = [kw.upper() for kw in mission_kw if kw in full_text]
        if matched_mission_kw:
            score += len(matched_mission_kw) * 4
            reasons.append(f"Matches mission hazards: {', '.join(matched_mission_kw[:4])}")

        # 3. Fire safety pillar alignment
        if any("Prevention" in p for p in pillars):
            score += 3
            reasons.append("Covers Material Flammability & Prevention")
        if any("Suppression" in p or "Detection" in p for p in pillars):
            score += 3
            reasons.append("Covers Active Detection/Suppression")

        # 4. Custom query token match
        matched_q = [w for w in query_tokens if len(w) > 2 and w in full_text]
        if matched_q:
            score += len(matched_q) * 2
            reasons.append(f"Query terms: {', '.join(matched_q[:3])}")

        # 5. Publication richness bonus (higher scientific maturity)
        pubs = s.get("top_publications", [])
        if pubs:
            score += min(len(pubs), 3)
            reasons.append(f"{len(pubs)} peer-reviewed publications")

        ranked.append({
            "study": s,
            "score": score,
            "reasons": reasons if reasons else ["General microgravity combustion baseline"]
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:top_k]