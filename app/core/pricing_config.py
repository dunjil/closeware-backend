"""
Simple Subscription Pricing Configuration
Monthly/Yearly plans with hard limits (like Claude AI)
"""

# Pricing tiers
PRICING_TIERS = {
    "free": {
        "name": "Free",
        "monthly": {
            "price": 0,
            "deal_limit": 2,
        },
        "yearly": {
            "price": 0,
            "deal_limit": 24,  # 2 per month * 12
        },
        "features": [
            "2 deals per month",
            "Contract generation",
            "Instant verification",
            "Internal review workflow",
            "Digital signatures",
            "Complete audit trail",
            "Court-admissible export",
        ],
    },
    "pro": {
        "name": "Pro",
        "monthly": {
            "price": 99,
            "deal_limit": 20,
        },
        "yearly": {
            "price": 950,  # Save ~$238/year (~20% off)
            "deal_limit": 240,  # 20 per month * 12
        },
        "features": [
            "20 deals per month",
            "Everything in Free",
            "Priority support",
            "Unlimited revisions per deal",
            "Advanced analytics",
            "Export templates",
        ],
        "recommended": True,
    },
    "team": {
        "name": "Team",
        "monthly": {
            "price": 299,
            "deal_limit": 100,
        },
        "yearly": {
            "price": 2850,  # Save ~$738/year (~20% off)
            "deal_limit": 1200,  # 100 per month * 12
        },
        "features": [
            "100 deals per month",
            "Everything in Pro",
            "Team collaboration (multiple users)",
            "Role-based permissions",
            "Dedicated account manager",
            "Custom contract templates",
            "Monthly strategy calls",
        ],
    },
    "enterprise": {
        "name": "Enterprise",
        "monthly": {
            "price": None,  # Custom pricing
            "deal_limit": None,  # Unlimited
        },
        "yearly": {
            "price": None,  # Custom pricing
            "deal_limit": None,  # Unlimited
        },
        "features": [
            "Unlimited deals",
            "Everything in Team",
            "Custom integrations",
            "API access",
            "SLA guarantee (24hr response)",
            "White-glove onboarding",
            "Custom compliance requirements",
            "Dedicated infrastructure",
        ],
        "contact_sales": True,
    },
}


def get_tier_pricing(tier: str, billing_period: str = "monthly"):
    """
    Get pricing for a specific tier and billing period.

    Args:
        tier: "free", "pro", "team", or "enterprise"
        billing_period: "monthly" or "yearly"

    Returns:
        dict with price and deal_limit
    """
    tier_data = PRICING_TIERS.get(tier.lower())
    if not tier_data:
        raise ValueError(f"Invalid tier: {tier}")

    period_data = tier_data.get(billing_period.lower())
    if not period_data:
        raise ValueError(f"Invalid billing period: {billing_period}")

    return period_data


def get_yearly_savings(tier: str):
    """Calculate yearly savings vs monthly for a tier."""
    tier_data = PRICING_TIERS.get(tier.lower())
    if not tier_data or not tier_data["monthly"]["price"] or not tier_data["yearly"]["price"]:
        return 0

    monthly_annual_cost = tier_data["monthly"]["price"] * 12
    yearly_cost = tier_data["yearly"]["price"]
    savings = monthly_annual_cost - yearly_cost

    return savings
