"""
Currency formatting utilities for contracts.
Formats amounts properly for different currencies in legal documents.
"""

from decimal import Decimal
from typing import Union


class CurrencyFormatter:
    """Format currency amounts for legal contracts"""

    # Currency symbols and formatting rules
    CURRENCY_CONFIG = {
        "USD": {
            "symbol": "$",
            "name": "United States Dollars",
            "code": "USD",
            "decimals": 2,
            "position": "before",  # Symbol before amount
            "separator": ",",
            "decimal": "."
        },
        "EUR": {
            "symbol": "€",
            "name": "Euros",
            "code": "EUR",
            "decimals": 2,
            "position": "before",
            "separator": ",",
            "decimal": "."
        },
        "GBP": {
            "symbol": "£",
            "name": "British Pounds Sterling",
            "code": "GBP",
            "decimals": 2,
            "position": "before",
            "separator": ",",
            "decimal": "."
        },
        "NGN": {
            "symbol": "₦",
            "name": "Nigerian Naira",
            "code": "NGN",
            "decimals": 2,
            "position": "before",
            "separator": ",",
            "decimal": "."
        },
        "AED": {
            "symbol": "د.إ",
            "name": "UAE Dirhams",
            "code": "AED",
            "decimals": 2,
            "position": "before",
            "separator": ",",
            "decimal": "."
        },
        "ZAR": {
            "symbol": "R",
            "name": "South African Rand",
            "code": "ZAR",
            "decimals": 2,
            "position": "before",
            "separator": ",",
            "decimal": "."
        },
        "KES": {
            "symbol": "KSh",
            "name": "Kenyan Shillings",
            "code": "KES",
            "decimals": 2,
            "position": "before",
            "separator": ",",
            "decimal": "."
        },
        "SAR": {
            "symbol": "﷼",
            "name": "Saudi Riyals",
            "code": "SAR",
            "decimals": 2,
            "position": "before",
            "separator": ",",
            "decimal": "."
        },
        "QAR": {
            "symbol": "ر.ق",
            "name": "Qatari Riyals",
            "code": "QAR",
            "decimals": 2,
            "position": "before",
            "separator": ",",
            "decimal": "."
        },
    }

    @classmethod
    def format_amount(cls, amount: Union[float, Decimal, int], currency: str = "USD") -> str:
        """
        Format amount with currency symbol.

        Examples:
            format_amount(1000000, "USD") -> "$1,000,000.00"
            format_amount(700000000, "AED") -> "د.إ 700,000,000.00"
            format_amount(4450000000, "NGN") -> "₦4,450,000,000.00"
        """
        currency = currency.upper() if currency else "USD"
        config = cls.CURRENCY_CONFIG.get(currency, cls.CURRENCY_CONFIG["USD"])

        # Convert to Decimal for precision
        amount = Decimal(str(amount))

        # Format with thousands separator
        amount_str = f"{amount:,.{config['decimals']}f}"

        # Add currency symbol
        if config["position"] == "before":
            return f"{config['symbol']}{amount_str}"
        else:
            return f"{amount_str} {config['symbol']}"

    @classmethod
    def format_legal(cls, amount: Union[float, Decimal, int], currency: str = "USD") -> str:
        """
        Format amount for legal contracts with both numeric and written form.

        Examples:
            format_legal(700000000, "AED") ->
            "د.إ 700,000,000.00 (Seven Hundred Million UAE Dirhams)"

            format_legal(4450000000, "NGN") ->
            "₦4,450,000,000.00 (Four Billion, Four Hundred and Fifty Million Nigerian Naira)"
        """
        currency = currency.upper() if currency else "USD"
        config = cls.CURRENCY_CONFIG.get(currency, cls.CURRENCY_CONFIG["USD"])

        numeric = cls.format_amount(amount, currency)
        words = cls.amount_to_words(amount)

        return f"{numeric} ({words} {config['name']})"

    @classmethod
    def amount_to_words(cls, amount: Union[float, Decimal, int]) -> str:
        """
        Convert numeric amount to words for legal documents.

        Examples:
            700000000 -> "Seven Hundred Million"
            4450000000 -> "Four Billion, Four Hundred and Fifty Million"
            1000000.50 -> "One Million and Fifty Cents"
        """
        amount = Decimal(str(amount))

        # Split into integer and decimal parts
        integer_part = int(amount)
        decimal_part = int((amount - integer_part) * 100)

        # Convert integer part to words
        words = cls._number_to_words(integer_part)

        # Add decimal part if present
        if decimal_part > 0:
            decimal_words = cls._number_to_words(decimal_part)
            words += f" and {decimal_words} Cents"

        return words

    @classmethod
    def _number_to_words(cls, n: int) -> str:
        """Convert a number to words"""
        if n == 0:
            return "Zero"

        # Basic number words
        ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
        teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
                 "Sixteen", "Seventeen", "Eighteen", "Nineteen"]

        def convert_below_thousand(num):
            if num == 0:
                return ""
            elif num < 10:
                return ones[num]
            elif num < 20:
                return teens[num - 10]
            elif num < 100:
                return tens[num // 10] + (" " + ones[num % 10] if num % 10 != 0 else "")
            else:
                return ones[num // 100] + " Hundred" + (
                    " and " + convert_below_thousand(num % 100) if num % 100 != 0 else ""
                )

        # Handle large numbers
        if n >= 1_000_000_000_000:  # Trillions
            trillions = n // 1_000_000_000_000
            remainder = n % 1_000_000_000_000
            result = convert_below_thousand(trillions) + " Trillion"
            if remainder > 0:
                result += ", " + cls._number_to_words(remainder)
            return result

        elif n >= 1_000_000_000:  # Billions
            billions = n // 1_000_000_000
            remainder = n % 1_000_000_000
            result = convert_below_thousand(billions) + " Billion"
            if remainder > 0:
                result += ", " + cls._number_to_words(remainder)
            return result

        elif n >= 1_000_000:  # Millions
            millions = n // 1_000_000
            remainder = n % 1_000_000
            result = convert_below_thousand(millions) + " Million"
            if remainder > 0:
                result += ", " + cls._number_to_words(remainder)
            return result

        elif n >= 1_000:  # Thousands
            thousands = n // 1_000
            remainder = n % 1_000
            result = convert_below_thousand(thousands) + " Thousand"
            if remainder > 0:
                result += ", " + cls._number_to_words(remainder)
            return result

        else:
            return convert_below_thousand(n)

    @classmethod
    def get_currency_name(cls, currency: str = "USD") -> str:
        """Get the full name of a currency"""
        currency = currency.upper() if currency else "USD"
        config = cls.CURRENCY_CONFIG.get(currency, cls.CURRENCY_CONFIG["USD"])
        return config["name"]


# Convenience function
def format_contract_amount(amount: Union[float, Decimal, int], currency: str = "USD") -> str:
    """
    Format amount for use in legal contracts.
    Returns: "د.إ 700,000,000.00 (Seven Hundred Million UAE Dirhams)"
    """
    return CurrencyFormatter.format_legal(amount, currency)
