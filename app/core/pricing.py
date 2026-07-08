"""
Pricing Configuration - Credit-based pricing with Early Adopter support
"""

# Credit costs per deal type
CREDIT_COSTS = {
    "early_adopter": {
        "simple": 2,      # $200 at $100/credit
        "property": 8,    # $800
        "m&a": 30,        # $3,000
    },
    "standard": {
        "simple": 4,      # $400 at $100/credit
        "property": 15,   # $1,500
        "m&a": 60,        # $6,000
    }
}

# Credit pack pricing (in cents)
CREDIT_PACKS = {
    "early_adopter": [
        {
            "id": "starter",
            "name": "Starter Pack",
            "credits": 100,
            "price": 500000,  # $5,000 in cents
            "savings": 500000,  # Save $5,000
        },
        {
            "id": "growth",
            "name": "Growth Pack",
            "credits": 500,
            "price": 2250000,  # $22,500
            "savings": 2250000,  # Save $22,500
        },
        {
            "id": "enterprise",
            "name": "Enterprise Pack",
            "credits": 2000,
            "price": 8000000,  # $80,000
            "savings": 8000000,  # Save $80,000
        },
    ],
    "standard": [
        {
            "id": "starter",
            "name": "Starter Pack",
            "credits": 100,
            "price": 1000000,  # $10,000
            "savings": 0,
        },
        {
            "id": "growth",
            "name": "Growth Pack",
            "credits": 500,
            "price": 4500000,  # $45,000
            "savings": 0,
        },
        {
            "id": "enterprise",
            "name": "Enterprise Pack",
            "credits": 2000,
            "price": 16000000,  # $160,000
            "savings": 0,
        },
    ]
}

# Price per credit (in cents)
PRICE_PER_CREDIT = 10000  # $100 per credit

# Early adopter limit
EARLY_ADOPTER_LIMIT = 100


def get_credit_cost(deal_type: str, is_early_adopter: bool) -> int:
    """
    Get the credit cost for a deal type.

    Args:
        deal_type: "simple", "property", or "m&a"
        is_early_adopter: Whether the organization is an early adopter

    Returns:
        Number of credits required for this deal type
    """
    tier = "early_adopter" if is_early_adopter else "standard"
    return CREDIT_COSTS[tier].get(deal_type.lower(), CREDIT_COSTS[tier]["simple"])


def get_credit_packs(is_early_adopter: bool) -> list:
    """
    Get available credit packs for the organization.

    Args:
        is_early_adopter: Whether the organization is an early adopter

    Returns:
        List of credit pack options
    """
    tier = "early_adopter" if is_early_adopter else "standard"
    return CREDIT_PACKS[tier]


def get_usd_price(deal_type: str, is_early_adopter: bool) -> int:
    """
    Get the USD price (in cents) for a deal type.

    Args:
        deal_type: "simple", "property", or "m&a"
        is_early_adopter: Whether the organization is an early adopter

    Returns:
        Price in cents
    """
    credits = get_credit_cost(deal_type, is_early_adopter)
    return credits * PRICE_PER_CREDIT
