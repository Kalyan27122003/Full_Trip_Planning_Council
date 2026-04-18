# agents/currency_helper.py
# ─────────────────────────────────────────────────────────────────────────────
# CURRENCY HELPER — Destination → Country + Currency Detection
#
# Problem this solves:
#   The user types a destination like "Tokyo" or "Bali" — a city name.
#   But we need to know: which country is it in? What currency do they use?
#   What's the exchange rate vs INR? How expensive is it per day?
#
# Solution:
#   A hardcoded lookup table (DESTINATION_CURRENCY_MAP) that maps keywords
#   (city/country names) → (country, currency code, symbol, INR rate).
#
# Why hardcoded instead of an API?
#   - Faster (no extra API call)
#   - Works offline
#   - Covers all major travel destinations
#   - Rates are approximate — just for budget estimation, not forex trading
#
# Used by: destination_agent, budget_agent, budget_validator, itinerary_agent
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOKUP TABLE
# Format: ([list of keywords], country_name, currency_code, currency_symbol, inr_rate)
# inr_rate = how many INR = 1 unit of local currency
#   e.g. USD: 1 USD = 84 INR → inr_rate = 84
#   e.g. JPY: 1 JPY = 0.56 INR → inr_rate = 0.56 (JPY is a smaller unit)
# ─────────────────────────────────────────────────────────────────────────────
DESTINATION_CURRENCY_MAP = [
    # India — inr_rate = 1.0 because we store everything in INR internally
    (["india", "delhi", "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai",
      "kolkata", "goa", "jaipur", "ladakh", "leh", "manali", "shimla", "kerala",
      "rajasthan", "varanasi", "agra", "udaipur", "rishikesh", "darjeeling",
      "ooty", "coorg", "munnar", "kochi", "vizag", "visakhapatnam", "kakinada",
      "guntur", "vijayawada", "tirupati", "pondicherry", "hampi", "mysore",
      "amritsar", "chandigarh", "dehradun", "nainital", "mussoorie", "shirdi",
      "pune", "aurangabad", "nashik", "indore", "bhopal", "nagpur", "lucknow",
      "allahabad", "prayagraj", "patna", "bhubaneswar", "puri", "raipur",
      "srinagar", "jammu", "spiti", "andaman", "lakshadweep"],
     "India", "INR", "₹", 1.0),

    # USA
    (["new york", "los angeles", "san francisco", "chicago", "miami", "las vegas",
      "boston", "seattle", "washington", "hawaii", "orlando", "dallas", "houston",
      "new orleans", "nashville", "denver", "portland", "austin", "usa", "united states"],
     "USA", "USD", "$", 84.0),

    # UK
    (["london", "edinburgh", "manchester", "liverpool", "bristol", "oxford",
      "cambridge", "bath", "york", "glasgow", "uk", "england", "scotland", "wales"],
     "UK", "GBP", "£", 106.0),

    # Europe (Euro zone — covers most of continental Europe)
    (["paris", "rome", "barcelona", "madrid", "amsterdam", "berlin", "prague",
      "vienna", "budapest", "lisbon", "athens", "dublin", "brussels", "milan",
      "florence", "venice", "munich", "frankfurt", "nice", "marseille",
      "seville", "porto", "dubrovnik", "split", "santorini", "mykonos",
      "france", "italy", "spain", "germany", "netherlands", "portugal",
      "greece", "austria", "belgium", "ireland", "croatia", "czech republic",
      "hungary", "poland", "switzerland partial", "luxembourg"],
     "Europe", "EUR", "€", 91.0),

    # Switzerland (separate from Europe because it uses CHF, not EUR)
    (["zurich", "geneva", "bern", "lausanne", "interlaken", "lucerne",
      "zermatt", "switzerland"],
     "Switzerland", "CHF", "CHF", 95.0),

    # Japan
    (["tokyo", "kyoto", "osaka", "hiroshima", "nara", "sapporo", "fukuoka",
      "hakone", "nikko", "okinawa", "japan"],
     "Japan", "JPY", "¥", 0.56),

    # Thailand
    (["bangkok", "phuket", "chiang mai", "pattaya", "koh samui", "krabi",
      "koh phi phi", "chiang rai", "ayutthaya", "thailand"],
     "Thailand", "THB", "฿", 2.4),

    # Singapore
    (["singapore"], "Singapore", "SGD", "S$", 63.0),

    # Malaysia
    (["kuala lumpur", "penang", "langkawi", "kota kinabalu", "malacca",
      "malaysia", "kl"],
     "Malaysia", "MYR", "RM", 19.0),

    # Indonesia (Bali, Jakarta, etc.)
    # Note: IDR rate is very small (0.0053) because 1 IDR = 0.0053 INR
    (["bali", "jakarta", "yogyakarta", "lombok", "komodo", "surabaya",
      "ubud", "seminyak", "indonesia"],
     "Indonesia", "IDR", "Rp", 0.0053),

    # Vietnam
    (["hanoi", "ho chi minh", "saigon", "hoi an", "da nang", "halong",
      "nha trang", "hue", "vietnam"],
     "Vietnam", "VND", "₫", 0.0033),

    # Nepal
    (["kathmandu", "pokhara", "everest", "annapurna", "chitwan",
      "bhaktapur", "lumbini", "nepal"],
     "Nepal", "NPR", "NPR", 0.63),

    # Sri Lanka
    (["colombo", "kandy", "galle", "sigiriya", "ella", "trincomalee",
      "sri lanka", "ceylon"],
     "Sri Lanka", "LKR", "LKR", 0.28),

    # UAE / Dubai
    (["dubai", "abu dhabi", "sharjah", "ajman", "uae", "united arab emirates"],
     "UAE", "AED", "AED", 23.0),

    # Australia
    (["sydney", "melbourne", "brisbane", "perth", "adelaide", "cairns",
      "gold coast", "uluru", "great barrier reef", "australia"],
     "Australia", "AUD", "A$", 55.0),

    # Canada
    (["toronto", "vancouver", "montreal", "calgary", "ottawa", "banff",
      "niagara", "quebec", "canada"],
     "Canada", "CAD", "C$", 62.0),

    # Turkey
    (["istanbul", "ankara", "cappadocia", "antalya", "bodrum", "izmir",
      "ephesus", "pamukkale", "turkey", "turkiye"],
     "Turkey", "TRY", "₺", 2.5),

    # Egypt
    (["cairo", "luxor", "aswan", "hurghada", "sharm el sheikh",
      "alexandria", "egypt"],
     "Egypt", "EGP", "EGP", 1.7),

    # South Africa
    (["cape town", "johannesburg", "durban", "kruger", "garden route",
      "south africa"],
     "South Africa", "ZAR", "R", 4.6),

    # Kenya / East Africa (also includes Tanzania — same emergency context)
    (["nairobi", "maasai mara", "serengeti", "kilimanjaro", "zanzibar",
      "mombasa", "kenya", "tanzania"],
     "Kenya", "KES", "KSh", 0.65),

    # China
    (["beijing", "shanghai", "hong kong", "guangzhou", "chengdu", "xian",
      "guilin", "zhangjiajie", "tibet", "china"],
     "China", "CNY", "¥", 11.6),

    # South Korea
    (["seoul", "busan", "jeju", "incheon", "gyeongju", "south korea", "korea"],
     "South Korea", "KRW", "₩", 0.061),

    # Maldives
    (["maldives", "male", "maafushi"], "Maldives", "MVR", "MVR", 5.5),

    # Mexico
    (["mexico city", "cancun", "tulum", "playa del carmen", "oaxaca",
      "guadalajara", "mexico"],
     "Mexico", "MXN", "MX$", 4.2),

    # Brazil
    (["rio de janeiro", "sao paulo", "salvador", "iguazu", "florianopolis",
      "brazil", "brasil"],
     "Brazil", "BRL", "R$", 15.0),

    # Argentina
    (["buenos aires", "patagonia", "mendoza", "bariloche", "iguazu falls",
      "argentina"],
     "Argentina", "ARS", "ARS", 0.10),

    # Peru
    (["lima", "cusco", "machu picchu", "arequipa", "lake titicaca", "peru"],
     "Peru", "PEN", "S/", 22.0),

    # Morocco
    (["marrakech", "casablanca", "fes", "chefchaouen", "essaouira",
      "rabat", "agadir", "sahara", "morocco"],
     "Morocco", "MAD", "MAD", 8.4),

    # Jordan
    (["petra", "amman", "wadi rum", "aqaba", "dead sea", "jordan"],
     "Jordan", "JOD", "JD", 119.0),

    # New Zealand
    (["auckland", "queenstown", "christchurch", "rotorua", "wellington",
      "milford sound", "new zealand"],
     "New Zealand", "NZD", "NZ$", 51.0),

    # Philippines
    (["manila", "palawan", "boracay", "cebu", "siargao", "el nido",
      "davao", "philippines"],
     "Philippines", "PHP", "₱", 1.5),
]


# ─────────────────────────────────────────────────────────────────────────────
# REGIONAL DAILY MINIMUM COSTS (per person per day, in INR)
# Used by budget_validator to check if the user's total budget is enough.
# Includes: accommodation + food + local transport (NOT flights).
# ─────────────────────────────────────────────────────────────────────────────
REGIONAL_DAILY_MIN_INR = {
    "India":        800,    # Budget backpacker level
    "Nepal":        1200,
    "Sri Lanka":    1500,
    "Thailand":     2500,   # Thailand is budget-friendly for Indians
    "Indonesia":    2000,
    "Vietnam":      1800,
    "Malaysia":     3000,
    "Philippines":  2500,
    "China":        4000,
    "South Korea":  6000,
    "Japan":        7000,   # Japan is expensive — even budget stays cost a lot
    "Singapore":    9000,
    "UAE":          8000,
    "Maldives":     12000,  # Very expensive — mostly resort-only island
    "Turkey":       3500,
    "Egypt":        2500,
    "Morocco":      3000,
    "Jordan":       5000,
    "Kenya":        5000,
    "South Africa": 4500,
    "UK":           10000,
    "Europe":       9000,
    "Switzerland":  14000,  # Most expensive destination in Europe
    "Australia":    9000,
    "New Zealand":  9000,
    "Canada":       8000,
    "USA":          10000,
    "Mexico":       3000,
    "Brazil":       4000,
    "Peru":         3500,
    "Argentina":    2000,
}


# ─────────────────────────────────────────────────────────────────────────────
# INTERNATIONAL FLIGHT COSTS FROM INDIA (round trip per person, in INR)
# Used by budget_validator and budget_agent to include flight cost in estimates.
# ─────────────────────────────────────────────────────────────────────────────
INTL_FLIGHT_FROM_INDIA_INR = {
    "Nepal":        8000,    # Very short flight — affordable
    "Sri Lanka":    12000,
    "Thailand":     18000,
    "Indonesia":    22000,
    "Vietnam":      20000,
    "Malaysia":     16000,
    "Philippines":  22000,
    "Singapore":    15000,
    "China":        25000,
    "South Korea":  28000,
    "Japan":        35000,
    "UAE":          15000,
    "Maldives":     20000,
    "Turkey":       30000,
    "Egypt":        28000,
    "Morocco":      35000,
    "Jordan":       28000,
    "Kenya":        35000,
    "South Africa": 45000,
    "UK":           55000,
    "Europe":       50000,
    "Switzerland":  55000,
    "Australia":    60000,
    "New Zealand":  65000,
    "Canada":       65000,
    "USA":          65000,
    "Mexico":       70000,
    "Brazil":       75000,
    "Peru":         75000,
    "Argentina":    80000,
}


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def detect_country_and_currency(destination: str) -> dict:
    """
    Given a destination name (like "Tokyo" or "Bali"), detect:
      - country name
      - currency code (e.g. "JPY")
      - currency symbol (e.g. "¥")
      - INR exchange rate (1 local unit = X INR)

    How it works:
      - Converts destination to lowercase.
      - Loops through DESTINATION_CURRENCY_MAP keyword lists.
      - Returns the first match found (keyword is substring of destination or vice versa).
      - Falls back to India/INR if nothing matches.
    """
    dest_lower = destination.lower()
    for keywords, country, code, symbol, rate in DESTINATION_CURRENCY_MAP:
        for kw in keywords:
            if kw in dest_lower or dest_lower in kw:
                return {
                    "country": country,
                    "currency_code": code,
                    "currency_symbol": symbol,
                    "inr_rate": rate,
                }
    # Default fallback — destination not in our map → assume India/INR
    return {
        "country": "Unknown",
        "currency_code": "INR",
        "currency_symbol": "₹",
        "inr_rate": 1.0,
    }


def get_daily_min_inr(country: str) -> int:
    """
    Return the minimum daily cost (per person, in INR) for a given country.
    Used by budget_validator to calculate the minimum viable budget.
    Returns 1500 for unknown countries as a safe default.
    """
    return REGIONAL_DAILY_MIN_INR.get(country, 1500)


def get_intl_flight_inr(country: str) -> int:
    """
    Return the approximate round-trip international flight cost from India (in INR).
    Used by budget_validator and budget_agent for international trips.
    Returns 30000 for unknown countries as a safe default.
    """
    return INTL_FLIGHT_FROM_INDIA_INR.get(country, 30000)


def format_amount(amount_inr: float, currency_symbol: str, inr_rate: float) -> str:
    """
    Convert an INR amount to local currency and return a formatted string.

    Examples:
      - India (rate=1.0):     ₹5000 → "₹5,000"
      - Japan (rate=0.56):    ₹5000 → "¥8,928"  (5000 / 0.56)
      - Indonesia (rate=0.005): ₹5000 → "Rp1,000,000"

    The rate is "1 local unit = X INR", so to go INR → local: divide by rate.
    """
    if inr_rate == 1.0:
        return f"₹{int(amount_inr):,}"
    local = amount_inr * inr_rate
    if local >= 1000:
        return f"{currency_symbol}{int(local):,}"
    elif local >= 1:
        return f"{currency_symbol}{local:.1f}"
    else:
        # Very small unit currencies like IDR — show as integer
        return f"{currency_symbol}{int(local):,}"


def get_booking_platforms(country: str) -> str:
    """
    Return relevant travel booking platforms for the destination country.
    Used in prompts so the LLM recommends the right booking apps.

    Examples:
      - India → IRCTC, redBus, MakeMyTrip
      - Southeast Asia → Agoda, Klook, 12Go Asia
      - Europe → Eurail, FlixBus, Booking.com
    """
    if country == "India":
        return "IRCTC, AbhiBus, redBus, MakeMyTrip, OYO, Goibibo"
    elif country in ["Thailand", "Vietnam", "Indonesia", "Malaysia", "Philippines"]:
        return "Booking.com, Agoda, Klook, 12Go Asia, Hostelworld"
    elif country in ["Japan", "South Korea", "China"]:
        return "Booking.com, Agoda, Klook, Japan Rail Pass (JR Pass)"
    elif country in ["UK", "Europe", "Switzerland"]:
        return "Booking.com, Hostelworld, Eurail, FlixBus, Skyscanner"
    elif country in ["USA", "Canada"]:
        return "Booking.com, Expedia, Greyhound, Amtrak, Airbnb"
    elif country in ["Australia", "New Zealand"]:
        return "Booking.com, Wotif, Airbnb, Greyhound Australia"
    elif country in ["UAE", "Maldives", "Jordan", "Egypt", "Morocco", "Turkey"]:
        return "Booking.com, Airbnb, Expedia, local travel agencies"
    else:
        return "Booking.com, Hostelworld, Airbnb, Expedia, Skyscanner"


def get_emergency_number(country: str) -> str:
    """
    Return the emergency contact numbers for the given country.
    Used by safety_agent and itinerary_agent so the plan includes emergency info.
    Returns international SOS (112) for unknown countries.
    """
    EMERGENCY_NUMBERS = {
        "India":        "112 (universal) | Police: 100 | Ambulance: 108",
        "USA":          "911",
        "UK":           "999 | EU: 112",
        "Europe":       "112 (EU universal)",
        "Switzerland":  "112",
        "Japan":        "110 (Police) | 119 (Ambulance/Fire)",
        "Thailand":     "191 (Police) | 1669 (Ambulance)",
        "Singapore":    "999 (Police) | 995 (Ambulance)",
        "Malaysia":     "999",
        "Indonesia":    "110 (Police) | 118 (Ambulance)",
        "Vietnam":      "113 (Police) | 115 (Ambulance)",
        "UAE":          "999",
        "Australia":    "000",
        "New Zealand":  "111",
        "Canada":       "911",
        "South Africa": "10111 (Police) | 10177 (Ambulance)",
        "Kenya":        "999",
        "Egypt":        "122 (Police) | 123 (Ambulance)",
        "Morocco":      "190 (Police) | 150 (Ambulance)",
        "Turkey":       "155 (Police) | 112 (Ambulance)",
        "Jordan":       "911",
        "Nepal":        "100 (Police) | 102 (Ambulance)",
        "Sri Lanka":    "119 (Police) | 110 (Ambulance)",
        "Maldives":     "119",
        "Philippines":  "911",
        "South Korea":  "112 (Police) | 119 (Ambulance)",
        "China":        "110 (Police) | 120 (Ambulance)",
        "Mexico":       "911",
        "Brazil":       "190 (Police) | 192 (Ambulance)",
        "Peru":         "105 (Police) | 117 (Ambulance)",
        "Argentina":    "911",
    }
    return EMERGENCY_NUMBERS.get(country, "112 (international SOS)")