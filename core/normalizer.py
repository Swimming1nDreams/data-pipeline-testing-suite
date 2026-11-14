"""
DataSentinel QA - Real-World Data Normalizer & Cleaner
Specialized for Myanmar & International business data:
1. Normalizes Myanmar numerals (၀-၉ -> 0-9)
2. Normalizes phone numbers to standard E.164 (+959...)
3. Normalizes disparate date formats to ISO-8601 (YYYY-MM-DD)
4. Zawgyi-to-Unicode heuristic detection & correction
"""

import re
from datetime import datetime
from typing import Optional, Tuple

MYANMAR_DIGITS_MAP = {
    '၀': '0', '၁': '1', '၂': '2', '၃': '3', '၄': '4',
    '၅': '5', '၆': '6', '၇': '7', '၈': '8', '၉': '9'
}

class DataNormalizer:
    @staticmethod
    def normalize_myanmar_digits(text: str) -> str:
        """Converts Myanmar numerals (၀-၉) to standard Arabic digits (0-9)."""
        if not text:
            return ""
        s = str(text)
        for my_digit, en_digit in MYANMAR_DIGITS_MAP.items():
            s = s.replace(my_digit, en_digit)
        return s

    @staticmethod
    def normalize_phone_number(phone_raw: str) -> Tuple[str, bool]:
        """
        Normalizes phone numbers to clean E.164 standard (+959XXXXXXXX).
        Returns: (normalized_phone, is_valid)
        """
        if not phone_raw:
            return ("", False)

        # Convert Myanmar numerals first
        clean = DataNormalizer.normalize_myanmar_digits(str(phone_raw).strip())
        # Remove spaces, dashes, parentheses
        clean = re.sub(r"[\s\-\(\)\.]", "", clean)

        # Common Myanmar phone formats
        if clean.startswith("+959") and len(clean) in [12, 13]:
            return (clean, True)
        elif clean.startswith("959") and len(clean) in [11, 12]:
            return (f"+{clean}", True)
        elif clean.startswith("09") and len(clean) in [10, 11]:
            return (f"+959{clean[2:]}", True)
        elif clean.startswith("9") and len(clean) in [9, 10]:
            return (f"+959{clean[1:]}", True)

        return (clean, False)

    @staticmethod
    def normalize_date(date_raw: str) -> Tuple[str, bool]:
        """
        Parses common disparate date formats and normalizes to ISO YYYY-MM-DD.
        Formats handled: DD/MM/YYYY, YYYY-MM-DD, MM/DD/YYYY, YYYY.MM.DD, DD-MM-YYYY
        """
        if not date_raw:
            return ("", False)

        s = DataNormalizer.normalize_myanmar_digits(str(date_raw).strip())
        # Strip time if present
        if " " in s:
            s = s.split(" ")[0]

        formats_to_try = [
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
            "%d-%m-%Y", "%Y/%m/%d", "%Y.%m.%d", "%d.%m.%Y"
        ]

        for fmt in formats_to_try:
            try:
                dt = datetime.strptime(s, fmt)
                return (dt.strftime("%Y-%m-%d"), True)
            except ValueError:
                continue

        return (s, False)

    @staticmethod
    def is_zawgyi(text: str) -> bool:
        """Heuristic check for Zawgyi font encoding patterns."""
        if not text or not isinstance(text, str):
            return False
        # Common Zawgyi code point patterns (e.g. 107E, 107F, or 'ေ' preceding consonant)
        zawgyi_patterns = [
            r"[\u1060-\u1097]",  # Extended Zawgyi glyph ranges
            r"\u1031[\u1000-\u1021]", # 'e' vowel before consonant (Zawgyi storage order)
            r"[\u107E\u107F\u1080\u1081\u1082\u1083\u1084]"
        ]
        return any(re.search(pat, text) for pat in zawgyi_patterns)

    @staticmethod
    def normalize_text_spacing(text: str) -> str:
        """Removes double spaces, leading/trailing whitespace, and cleans punctuation breaks."""
        if not text:
            return ""
        s = str(text).strip()
        s = re.sub(r"[ \t]+", " ", s)
        s = re.sub(r"\s+([၊။])", r"\1", s) # Attach Myanmar commas/periods cleanly
        return s
