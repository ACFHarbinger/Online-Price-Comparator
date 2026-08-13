"""Price string parsing and normalization utilities."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

# Mapping of currency symbols / codes to standard ISO 4217 currency codes.
CURRENCY_MAP: dict[str, str] = {
    "€": "EUR",
    "EUR": "EUR",
    "EURO": "EUR",
    "EUROS": "EUR",
    "$": "USD",
    "USD": "USD",
    "US$": "USD",
    "DOLLAR": "USD",
    "DOLLARS": "USD",
    "£": "GBP",
    "GBP": "GBP",
    "POUND": "GBP",
    "POUNDS": "GBP",
    "R$": "BRL",
    "BRL": "BRL",
    "zł": "PLN",
    "PLN": "PLN",
    "Kč": "CZK",
    "CZK": "CZK",
    "CHF": "CHF",
    "¥": "JPY",
    "JPY": "JPY",
    "CNY": "CNY",
    "₹": "INR",
    "INR": "INR",
    "CA$": "CAD",
    "CAD": "CAD",
    "AU$": "AUD",
    "AUD": "AUD",
    "NZD": "NZD",
    "SEK": "SEK",
    "NOK": "NOK",
    "DKK": "DKK",
    "kr": "SEK",
}

# Regex to match currency symbols or alphabetic currency codes.
_CURRENCY_REGEX = re.compile(
    r"(?:US\$|CA\$|AU\$|R\$|zł|Kč|"
    r"\bEUR\b|\bEURO\b|\bEUROS\b|\bUSD\b|\bDOLLAR\b|\bDOLLARS\b|"
    r"\bGBP\b|\bPOUND\b|\bPOUNDS\b|\bBRL\b|\bPLN\b|\bCZK\b|\bCHF\b|"
    r"\bJPY\b|\bCNY\b|\bINR\b|\bCAD\b|\bAUD\b|\bNZD\b|\bSEK\b|\bNOK\b|"
    r"\bDKK\b|kr|[€$£¥₹])",
    re.IGNORECASE,
)

# Number candidate regex matching digits with separators.
_NUMBER_CANDIDATE_REGEX = re.compile(r"[-+]?\d+(?:[\s.,'\xa0\u200b]\d+)*")


def _extract_currency(
    price_text: str, currency_hint: str | None
) -> tuple[str, str]:
    """Find ISO 4217 currency code in text, or fallback to hint / default 'EUR'."""
    match = _CURRENCY_REGEX.search(price_text)
    if match:
        matched_str = match.group(0)
        lookup_key = matched_str.upper()
        iso_code = CURRENCY_MAP.get(lookup_key, CURRENCY_MAP.get(matched_str, ""))
        if iso_code:
            return iso_code, matched_str

    if currency_hint and currency_hint.strip():
        return currency_hint.strip().upper(), ""

    return "EUR", ""


def _parse_number_string(num_str: str, currency: str) -> float:
    """Parse a cleaned numerical string into a float."""
    s = num_str.strip()
    s = re.sub(r"[\s\xa0\u200b']", "", s)

    if not s:
        raise ValueError("Empty number string")

    has_dot = "." in s
    has_comma = "," in s

    if has_dot and has_comma:
        last_dot = s.rfind(".")
        last_comma = s.rfind(",")
        if last_dot < last_comma:
            # Spanish/EU format: "1.234,56" -> remove dot, replace comma with dot
            clean_s = s.replace(".", "").replace(",", ".")
        else:
            # US/UK format: "1,234.56" -> remove comma
            clean_s = s.replace(",", "")
    elif has_comma:
        commas = s.count(",")
        if commas > 1:
            clean_s = s.replace(",", "")
        else:
            parts = s.split(",")
            dec_len = len(parts[1]) if len(parts) > 1 else 0
            if dec_len in (1, 2):
                clean_s = s.replace(",", ".")
            elif dec_len == 3:
                if currency in ("USD", "GBP", "CAD", "AUD"):
                    clean_s = s.replace(",", "")
                else:
                    clean_s = s.replace(",", ".")
            else:
                clean_s = s.replace(",", ".")
    elif has_dot:
        dots = s.count(".")
        if dots > 1:
            clean_s = s.replace(".", "")
        else:
            parts = s.split(".")
            dec_len = len(parts[1]) if len(parts) > 1 else 0
            if dec_len in (1, 2):
                clean_s = s
            elif dec_len == 3:
                if currency in ("USD", "GBP", "CAD", "AUD"):
                    clean_s = s
                else:
                    clean_s = s.replace(".", "")
            else:
                clean_s = s
    else:
        clean_s = s

    try:
        val = Decimal(clean_s)
        return float(val)
    except InvalidOperation as err:
        raise ValueError(f"Invalid decimal string: {clean_s!r}") from err


def parse_price(
    price_text: str, currency_hint: str | None = None
) -> tuple[float, str]:
    """Parse a raw scraped price string into (amount, ISO 4217 currency code).

    Must handle, at minimum:
    - Spanish/Portuguese format: '.' as thousands separator, ',' as decimal
      separator, e.g. "1.234,56 €" -> (1234.56, "EUR"), "649,99€" -> (649.99, "EUR")
    - Plain integer prices with no decimal part, e.g. "999 €" -> (999.0, "EUR")
    - US/UK format as a fallback when unambiguous, e.g. "$899.99" -> (899.99,
      "USD"), "£1,299.00" -> (1299.00, "GBP")
    - Currency symbol before or after the number, with or without a space
    - Extra whitespace / non-breaking spaces around the string
    - If no currency symbol is present in the text, fall back to `currency_hint`
      if given, else default to "EUR" (this tool's primary market is Spain/Portugal)
    - Must raise a clear `ValueError` (with the original text in the message) if the
      string genuinely contains no parseable number at all — callers are expected to
      catch this, not silently produce a wrong number.
    """
    if not isinstance(price_text, str) or not price_text.strip():
        raise ValueError(f"Price text is empty or not a string: {price_text!r}")

    clean_text = re.sub(r"[\xa0\u200b]", " ", price_text)
    currency, matched_token = _extract_currency(clean_text, currency_hint)

    candidates = list(_NUMBER_CANDIDATE_REGEX.finditer(clean_text))
    if not candidates:
        raise ValueError(f"No parseable price number found in text: {price_text!r}")

    selected_candidate: str | None = None
    if len(candidates) == 1:
        selected_candidate = candidates[0].group(0)
    else:
        if matched_token:
            for match in candidates:
                match_str = match.group(0)
                start, end = match.span()
                sub_around = clean_text[
                    max(0, start - 5) : min(len(clean_text), end + 5)
                ]
                if matched_token in sub_around:
                    selected_candidate = match_str
                    break

        if selected_candidate is None:
            for match in candidates:
                match_str = match.group(0)
                if "." in match_str or "," in match_str:
                    selected_candidate = match_str
                    break

        if selected_candidate is None:
            selected_candidate = candidates[0].group(0)

    try:
        amount = _parse_number_string(selected_candidate, currency)
    except ValueError as err:
        raise ValueError(
            f"Could not parse price amount from text: {price_text!r}"
        ) from err

    return amount, currency
