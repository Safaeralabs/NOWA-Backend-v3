# city_fallbacks.py
# Static fallback data for City DNA when LLM is unavailable

from typing import Dict, Any


# ========== GENERIC CONTINENTAL FALLBACKS ==========
EUROPEAN_FALLBACK = {
    "food_typicals": [
        {"name": "Local specialties", "note": "Try regional dishes", "when": ["lunch", "dinner"], "how_to_order": "Ask for local recommendations"},
        {"name": "Seasonal produce", "note": "Farm-to-table ingredients", "when": ["lunch", "dinner"], "how_to_order": "Look for daily specials"},
        {"name": "Traditional bakery", "note": "Fresh bread and pastries", "when": ["morning", "afternoon"], "how_to_order": "Point at what looks good"},
    ],
    "drink_typicals": [
        {"name": "Local beer", "note": "Regional brewery", "when": ["evening"], "how_to_order": "Ask what's on tap"},
        {"name": "Coffee", "note": "European coffee culture", "when": ["morning", "afternoon"], "how_to_order": "Cappuccino or espresso"},
        {"name": "Wine", "note": "Regional wines", "when": ["evening"], "how_to_order": "Ask for local recommendations"},
    ],
    "local_keywords": ["local", "traditional", "authentic", "historic"],
    "negative_keywords": ["tourist trap", "chain", "fast food"],
    "etiquette": ["Tip 5-10% if service was good", "Greetings are appreciated", "Dress neatly for nice restaurants"],
    "neighborhood_hints": []
}

ASIAN_FALLBACK = {
    "food_typicals": [
        {"name": "Street food", "note": "Authentic local flavors", "when": ["lunch", "dinner"], "how_to_order": "Point at what locals are eating"},
        {"name": "Noodles", "note": "Various noodle dishes", "when": ["lunch", "dinner"], "how_to_order": "Ask for recommendations"},
        {"name": "Rice dishes", "note": "Local rice specialties", "when": ["lunch", "dinner"], "how_to_order": "Try the house special"},
    ],
    "drink_typicals": [
        {"name": "Tea", "note": "Traditional tea", "when": ["afternoon", "evening"], "how_to_order": "Ask for local tea"},
        {"name": "Fresh juice", "note": "Tropical fruit juice", "when": ["morning", "afternoon"], "how_to_order": "Order by fruit name"},
    ],
    "local_keywords": ["authentic", "local", "traditional", "street"],
    "negative_keywords": ["westernized", "tourist", "overpriced"],
    "etiquette": ["Remove shoes if required", "Tipping varies by country", "Respect local customs"],
    "neighborhood_hints": []
}

LATIN_AMERICAN_FALLBACK = {
    "food_typicals": [
        {"name": "Tacos", "note": "Street tacos", "when": ["lunch", "dinner"], "how_to_order": "Order a variety"},
        {"name": "Empanadas", "note": "Stuffed pastries", "when": ["lunch", "evening"], "how_to_order": "Try different fillings"},
        {"name": "Fresh ceviche", "note": "Seafood specialty", "when": ["lunch"], "how_to_order": "Ask for the catch of the day"},
    ],
    "drink_typicals": [
        {"name": "Fresh juice", "note": "Tropical fruits", "when": ["morning", "afternoon"], "how_to_order": "Try local fruits"},
        {"name": "Beer", "note": "Local cerveza", "when": ["evening"], "how_to_order": "Ask what's popular"},
        {"name": "Coffee", "note": "Quality coffee", "when": ["morning"], "how_to_order": "Order black or with milk"},
    ],
    "local_keywords": ["auténtico", "local", "casero", "típico"],
    "negative_keywords": ["tourist trap", "cadena", "mall"],
    "etiquette": ["Tip 10-15% if service was good", "Greetings are important", "Meal times are social"],
    "neighborhood_hints": []
}

NORTH_AMERICAN_FALLBACK = {
    "food_typicals": [
        {"name": "Local burger", "note": "Regional burger spots", "when": ["lunch", "dinner"], "how_to_order": "Ask for house specialty"},
        {"name": "BBQ", "note": "Regional barbecue", "when": ["lunch", "dinner"], "how_to_order": "Try the combo plate"},
        {"name": "Craft food", "note": "Farm-to-table", "when": ["lunch", "dinner"], "how_to_order": "Ask about local ingredients"},
    ],
    "drink_typicals": [
        {"name": "Craft beer", "note": "Local breweries", "when": ["evening"], "how_to_order": "Try a flight"},
        {"name": "Coffee", "note": "Third-wave coffee", "when": ["morning", "afternoon"], "how_to_order": "Pour-over or cold brew"},
    ],
    "local_keywords": ["local", "craft", "artisan", "farm-to-table"],
    "negative_keywords": ["chain", "corporate", "mass-produced"],
    "etiquette": ["Tip 15-20%", "Friendly service expected", "Casual dress OK"],
    "neighborhood_hints": []
}

# ========== CITY-SPECIFIC OVERRIDES ==========
CITY_FALLBACKS = {
    # Germany
    "munich": {
        "city": "München",
        "language": "en",
        "food_typicals": [
            {"name": "Weißwurst", "note": "Traditional white sausage", "when": ["morning"], "how_to_order": "With sweet mustard and pretzel"},
            {"name": "Schweinshaxe", "note": "Roasted pork knuckle", "when": ["lunch", "dinner"], "how_to_order": "Ask for traditional sides"},
            {"name": "Leberkäse", "note": "Bavarian meatloaf", "when": ["lunch"], "how_to_order": "In a semmel (bread roll)"},
            {"name": "Obatzda", "note": "Cheese spread", "when": ["evening"], "how_to_order": "With pretzels and beer"},
        ],
        "drink_typicals": [
            {"name": "Beer", "note": "Munich's beer culture", "when": ["evening"], "how_to_order": "Helles or Weißbier"},
            {"name": "Radler", "note": "Beer and lemonade", "when": ["afternoon"], "how_to_order": "Perfect for summer"},
        ],
        "local_keywords": ["traditional", "bavarian", "biergarten", "authentic"],
        "negative_keywords": ["tourist trap", "overpriced"],
        "etiquette": ["Greet with 'Grüß Gott'", "Tip 5-10%", "Beer gardens are social"],
        "neighborhood_hints": [
            {"name": "Schwabing", "vibe": ["trendy", "artsy"], "best_for": ["nightlife", "culture"]},
            {"name": "Maxvorstadt", "vibe": ["cultural", "student"], "best_for": ["museums", "cafes"]},
        ]
    },
    "münchen": {  # Alias
        "city": "München",
        "language": "en",
        "food_typicals": [
            {"name": "Weißwurst", "note": "Traditional white sausage", "when": ["morning"], "how_to_order": "With sweet mustard and pretzel"},
            {"name": "Schweinshaxe", "note": "Roasted pork knuckle", "when": ["lunch", "dinner"], "how_to_order": "Ask for traditional sides"},
        ],
        "drink_typicals": [
            {"name": "Beer", "note": "Munich's beer culture", "when": ["evening"], "how_to_order": "Helles or Weißbier"},
        ],
        "local_keywords": ["traditional", "bavarian", "biergarten"],
        "negative_keywords": ["tourist trap"],
        "etiquette": ["Tip 5-10% if service was good"],
        "neighborhood_hints": []
    },
    
    # Spain
    "barcelona": {
        "city": "Barcelona",
        "language": "en",
        "food_typicals": [
            {"name": "Tapas", "note": "Small plates", "when": ["evening"], "how_to_order": "Order a variety to share"},
            {"name": "Pan con tomate", "note": "Bread with tomato", "when": ["lunch", "dinner"], "how_to_order": "Traditional starter"},
            {"name": "Paella", "note": "Rice dish", "when": ["lunch"], "how_to_order": "Order for 2+ people"},
        ],
        "drink_typicals": [
            {"name": "Vermouth", "note": "Aperitif", "when": ["afternoon"], "how_to_order": "With olives"},
            {"name": "Cava", "note": "Sparkling wine", "when": ["evening"], "how_to_order": "Catalan specialty"},
        ],
        "local_keywords": ["authentic", "local", "catalan"],
        "negative_keywords": ["tourist trap", "overpriced"],
        "etiquette": ["Dinner starts late (9 PM)", "Tip 5-10%", "Greet in Catalan if possible"],
        "neighborhood_hints": []
    },
    
    # Add more cities as needed...
}


def get_city_fallback(city: str) -> Dict[str, Any]:
    """
    Get City DNA fallback for a city.
    
    Strategy:
    1. Check for city-specific override
    2. Fall back to continental generic
    3. Fall back to minimal generic
    """
    city_normalized = (city or "").strip().lower()
    
    # Remove common variations
    city_normalized = city_normalized.replace("ü", "u").replace("ö", "o").replace("ä", "a")
    
    # Check city-specific
    if city_normalized in CITY_FALLBACKS:
        data = CITY_FALLBACKS[city_normalized].copy()
        data["city"] = city  # Use original capitalization
        return data
    
    # Continental fallback based on city name patterns
    # Europe
    if any(marker in city_normalized for marker in ["munich", "berlin", "paris", "london", "rome", 
                                                     "barcelona", "madrid", "vienna", "prague"]):
        data = EUROPEAN_FALLBACK.copy()
        data["city"] = city
        data["language"] = "en"
        return data
    
    # Asia
    if any(marker in city_normalized for marker in ["tokyo", "bangkok", "singapore", "hong kong",
                                                     "seoul", "taipei"]):
        data = ASIAN_FALLBACK.copy()
        data["city"] = city
        data["language"] = "en"
        return data
    
    # Latin America
    if any(marker in city_normalized for marker in ["mexico", "buenos aires", "lima", "bogota",
                                                     "santiago", "sao paulo"]):
        data = LATIN_AMERICAN_FALLBACK.copy()
        data["city"] = city
        data["language"] = "en"
        return data
    
    # North America
    if any(marker in city_normalized for marker in ["new york", "los angeles", "chicago", "san francisco",
                                                     "toronto", "vancouver"]):
        data = NORTH_AMERICAN_FALLBACK.copy()
        data["city"] = city
        data["language"] = "en"
        return data
    
    # Generic fallback
    return {
        "city": city,
        "language": "en",
        "food_typicals": [
            {"name": "Local specialties", "note": "Try regional dishes", "when": ["lunch", "dinner"], "how_to_order": "Ask for recommendations"},
            {"name": "Street food", "note": "Authentic local food", "when": ["lunch", "evening"], "how_to_order": "Look for busy stalls"},
        ],
        "drink_typicals": [
            {"name": "Local beverages", "note": "Regional drinks", "when": ["evening"], "how_to_order": "Ask what's popular"},
            {"name": "Coffee", "note": "Local coffee", "when": ["morning"], "how_to_order": "Order as locals do"},
        ],
        "local_keywords": ["local", "authentic", "traditional"],
        "negative_keywords": ["tourist trap", "chain"],
        "etiquette": ["Tip 10-15% if service was good"],
        "neighborhood_hints": []
    }