# agents/budget_validator.py
"""
Budget Validator — checks budget feasibility only.
Does NOT validate destination names — any place in India is valid.
Uses broad category estimates. No hardcoded prices.
"""

DESTINATION_CATEGORIES = {
    "ultra_remote": ["ladakh", "leh", "andaman", "lakshadweep", "spiti", "zanskar",
                     "arunachal", "tawang", "mechuka", "dzukou", "gurudongmar"],
    "hill_station": ["manali", "shimla", "mussoorie", "darjeeling", "ooty", "kodaikanal",
                     "coorg", "munnar", "shillong", "gangtok", "nainital", "mcleod",
                     "dalhousie", "khajjiar", "chikmagalur", "yercaud", "pachmarhi",
                     "mahabaleshwar", "lonavala", "matheran", "lansdowne", "mukteshwar",
                     "ranikhet", "almora", "binsar", "chopta", "tungnath", "deoria tal",
                     "parashar lake", "jalori pass", "kheerganga", "barot", "jibhi"],
    "beach":        ["goa", "pondicherry", "varkala", "kovalam", "alleppey", "alappuzha",
                     "marari", "palolem", "havelock", "neil island", "gokarna", "murudeshwar",
                     "tarkarli", "alibaug", "diveagar", "kashid", "mandrem", "agonda",
                     "puri", "digha", "mandarmani", "chilika", "rameswaram", "dhanushkodi"],
    "heritage":     ["jaipur", "jodhpur", "jaisalmer", "udaipur", "agra", "varanasi",
                     "hampi", "khajuraho", "mysore", "madurai", "mahabalipuram", "thanjavur",
                     "orchha", "mandu", "chittorgarh", "kumbhalgarh", "bundi", "pushkar",
                     "ajmer", "fatehpur sikri", "lucknow", "hyderabad", "bijapur", "badami",
                     "pattadakal", "aihole", "belur", "halebidu", "sravanabelagola"],
    "spiritual":    ["rishikesh", "haridwar", "tirupati", "shirdi", "amritsar",
                     "vrindavan", "mathura", "bodh gaya", "varanasi", "ujjain",
                     "dwarka", "nashik", "pandharpur", "somnath", "sabrimala",
                     "guruvayur", "rameshwaram", "madurai", "kashi", "prayagraj"],
    "wildlife":     ["ranthambore", "corbett", "bandipur", "kaziranga", "sundarbans",
                     "kanha", "tadoba", "pench", "nagarhole", "kabini", "wayanad",
                     "mudumalai", "anamalai", "satpura", "panna", "sariska",
                     "gir", "rann of kutch", "chilika", "bharatpur", "periyar"],
    "northeast":    ["meghalaya", "assam", "arunachal", "manipur", "nagaland",
                     "mizoram", "tripura", "sikkim", "dawki", "cherrapunji",
                     "mawlynnong", "kaziranga", "majuli", "ziro", "dzukou"],
    "city":         ["delhi", "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai",
                     "kolkata", "pune", "ahmedabad", "surat", "jaipur", "lucknow",
                     "kochi", "indore", "bhopal", "nagpur", "visakhapatnam", "coimbatore"],
}

CATEGORY_DAILY_MIN = {
    "ultra_remote": 3500,
    "hill_station": 1800,
    "beach":        2000,
    "heritage":     1600,
    "spiritual":    1200,
    "wildlife":     2500,
    "northeast":    2000,
    "city":         1500,
    "unknown":      800,    # default for any unrecognized place
}

FLIGHT_ESTIMATE_MIN = {
    "ultra_remote": 5000,
    "hill_station": 2500,
    "beach":        2500,
    "heritage":     2000,
    "spiritual":    2000,
    "wildlife":     2500,
    "northeast":    3500,
    "city":         1800,
    "unknown":      500,    # unknown/local places — assume bus/road transport
}

def get_category(destination: str) -> str:
    dest_lower = destination.lower()
    for cat, places in DESTINATION_CATEGORIES.items():
        for place in places:
            if place in dest_lower or dest_lower in place:
                return cat
    # Unknown destination — could be a small village, local spot, etc.
    # Do NOT reject it — treat as budget-friendly unknown category
    return "unknown"

def estimate_minimum_budget(destination: str, duration_days: int, travelers: int) -> dict:
    category  = get_category(destination)
    daily_min = CATEGORY_DAILY_MIN[category]

    # For unknown/small places, assume road transport is possible (no flight needed)
    # so use a lower flight estimate
    flight_min = FLIGHT_ESTIMATE_MIN[category]

    flight_total = flight_min * 2 * travelers      # round trip
    daily_total  = daily_min * duration_days * travelers
    subtotal     = flight_total + daily_total
    buffer       = int(subtotal * 0.10)
    minimum      = subtotal + buffer

    category_label = category if category != "unknown" else "general/local destination"

    return {
        "minimum":  minimum,
        "category": category_label,
        "breakdown": {
            f"Transport to/from {destination} (est. round trip × {travelers})":
                f"₹{flight_total:,}  (approx ₹{flight_min:,}/person one-way — could be less for road trips)",
            f"Daily expenses × {duration_days} days × {travelers} person(s)":
                f"₹{daily_total:,}  (approx ₹{daily_min:,}/person/day)",
            "10% emergency buffer":
                f"₹{buffer:,}",
        },
        "note": (
            "These are rough minimum estimates based on destination type. "
            "For local/small destinations, actual costs may be much lower. "
            "Prices vary by season, booking time, and travel style."
        ),
    }

def validate_budget(destination: str, budget_inr: int,
                    duration_days: int, travelers: int) -> dict:
    """
    Only validates budget feasibility.
    Accepts ALL destination names — small villages, local spots, anything.
    """
    data    = estimate_minimum_budget(destination, duration_days, travelers)
    minimum = data["minimum"]

    if budget_inr >= minimum:
        return {"valid": True}

    shortfall  = minimum - budget_inr
    breakdown_str = "\n".join([f"  • {k}: {v}" for k, v in data["breakdown"].items()])
    alt_days   = max(1, budget_inr // max(minimum // max(duration_days, 1), 1))

    message = f"""⚠️ Budget May Be Low for {destination}

Your budget      : ₹{budget_inr:,}
Estimated minimum: ₹{minimum:,}  ({travelers} traveler(s), {duration_days} days)
Destination type : {data['category']}

Rough cost breakdown:
{breakdown_str}

Note: {data['note']}

💡 Options:
  1. Increase budget to at least ₹{minimum:,} for a comfortable trip
  2. Reduce duration to ~{alt_days} day(s) within ₹{budget_inr:,}
  3. Travel by road/bus if destination is drivable — saves significantly on transport

Please adjust and try again."""

    return {
        "valid":     False,
        "message":   message,
        "minimum":   minimum,
        "breakdown": data["breakdown"],
        "note":      data["note"],
    }

def calculate_minimum_budget(destination: str, duration_days: int, travelers: int) -> dict:
    return estimate_minimum_budget(destination, duration_days, travelers)