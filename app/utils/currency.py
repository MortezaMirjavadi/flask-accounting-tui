"""Currency conversion utilities."""

from decimal import Decimal

SUPPORTED_CURRENCIES = ['IRR', 'USD', 'EUR', 'GBP', 'AED']

CURRENCY_SYMBOLS = {
    'IRR': 'تومان',
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'AED': 'د.إ',
}

CURRENCY_NAMES = {
    'IRR': 'ریال ایران',
    'USD': 'دلار آمریکا',
    'EUR': 'یورو',
    'GBP': 'پوند انگلیس',
    'AED': 'درهم امارات',
}


def get_exchange_rate(cursor, user_id, from_currency, to_currency):
    """Look up user's manual exchange rate. Returns 1.0 if same currency."""
    if from_currency == to_currency:
        return Decimal('1.0')

    # Look up direct rate
    cursor.execute(
        """
        SELECT rate FROM exchange_rates
        WHERE user_id = %s AND from_currency = %s AND to_currency = %s
        ORDER BY effective_date DESC LIMIT 1
        """,
        (user_id, from_currency, to_currency)
    )
    row = cursor.fetchone()
    if row:
        return Decimal(str(row['rate']))

    # Try reverse rate
    cursor.execute(
        """
        SELECT rate FROM exchange_rates
        WHERE user_id = %s AND from_currency = %s AND to_currency = %s
        ORDER BY effective_date DESC LIMIT 1
        """,
        (user_id, to_currency, from_currency)
    )
    row = cursor.fetchone()
    if row:
        return Decimal('1.0') / Decimal(str(row['rate']))

    return None


def convert_amount(amount, from_currency, to_currency, rate):
    """Convert amount using provided exchange rate."""
    if from_currency == to_currency:
        return Decimal(str(amount))
    if rate is None:
        return Decimal(str(amount))
    return Decimal(str(amount)) * Decimal(str(rate))


def get_user_preferred_currency(cursor, user_id):
    """Get user's preferred display currency, default IRR."""
    cursor.execute(
        "SELECT preferred_currency FROM user_preferences WHERE user_id = %s",
        (user_id,)
    )
    row = cursor.fetchone()
    if row:
        return row['preferred_currency']
    return 'IRR'


def validate_currency(currency):
    """Validate that a currency code is supported."""
    return currency in SUPPORTED_CURRENCIES
