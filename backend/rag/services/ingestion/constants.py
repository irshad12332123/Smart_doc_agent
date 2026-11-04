import re
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

ROMAN_NUMERALS: dict[str, int] = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
    "vi": 6,
    "vii": 7,
    "viii": 8,
    "ix": 9,
    "x": 10,
    "xi": 11,
    "xii": 12,
    "xiii": 13,
    "xiv": 14,
    "xv": 15,
    "xvi": 16,
    "xvii": 17,
    "xviii": 18,
    "xix": 19,
    "xx": 20,
}

WORD_NUMBERS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def parse_unit_value(v: Any) -> Optional[int]:
    """
    Normalizes any unit representation (integer, string digit, Roman numeral,
    alphabet letter a-z, or word numbers) into a standard positive integer.

    Examples:
      - 1, "1", "unit 1" -> 1
      - "a", "A", "Unit A", "unit-b", "Module C" -> 1, 1, 1, 2, 3
      - "i", "I", "Unit II", "Unit iv", "iv", "IV" -> 1, 1, 2, 4, 4, 4
      - "one", "Unit two" -> 1, 2
    """
    if v is None:
        return None
    if isinstance(v, int):
        return v if v > 0 else None

    if not isinstance(v, str):
        try:
            val_int = int(v)
            return val_int if val_int > 0 else None
        except (ValueError, TypeError):
            return None

    clean = v.strip().lower()
    if not clean or clean in {"null", "none", "n/a", "na", ""}:
        return None

    # 1. Direct Arabic digits (e.g., "1", "unit 2", "module 3", "unit-4")
    digit_match = re.search(r"\b\d+\b", clean)
    if digit_match:
        try:
            return int(digit_match.group(0))
        except ValueError:
            pass

    # 2. Labeled unit with Roman numeral, letter, or word
    # e.g. "unit b", "unit-c", "unit ii", "module iv", "chapter a", "unit three"
    labeled_match = re.search(
        r"\b(?:unit|module|chapter|part|section|assignment|paper)\s*[-:]?\s*([a-z0-9]+)\b",
        clean,
    )
    if labeled_match:
        token = labeled_match.group(1)
        if token.isdigit():
            return int(token)
        if token in ROMAN_NUMERALS:
            return ROMAN_NUMERALS[token]
        if token in WORD_NUMBERS:
            return WORD_NUMBERS[token]
        if len(token) == 1 and "a" <= token <= "z":
            return ord(token) - ord("a") + 1

    # 3. Standalone Roman numeral tokens (e.g., "ii", "IV", "III")
    tokens = re.findall(r"\b[a-z]+\b", clean)
    for token in tokens:
        if token in ROMAN_NUMERALS:
            return ROMAN_NUMERALS[token]

    # 4. Standalone word number tokens (e.g. "two", "three")
    for token in tokens:
        if token in WORD_NUMBERS:
            return WORD_NUMBERS[token]

    # 5. Standalone single letter (e.g. "a", "B", "c")
    if len(clean) == 1 and "a" <= clean <= "z":
        return ord(clean) - ord("a") + 1

    # 6. Bracketed single letter (e.g. "(b)", "[c]", "a)")
    bracketed_letter = re.search(r"(?:^|[\s\(\[\{])([a-z])(?:[\)\]\}]|$)", clean)
    if bracketed_letter:
        letter = bracketed_letter.group(1)
        if letter in ROMAN_NUMERALS:
            return ROMAN_NUMERALS[letter]
        return ord(letter) - ord("a") + 1

    return None


class DocumentMetaData(BaseModel):
    model_config = ConfigDict(extra="allow")

    description: str = Field(..., description="Summary of the document content")
    deadline: Optional[str] = Field(None, description="Deadline if mentioned, YYYY-MM-DD or ISO")
    document_type: Literal["notice", "assignment", "syllabus", "notes", "time_table", "others"] = Field(...)
    unit: Optional[int] = Field(
        None,
        description="Academic unit or module number if covered in document, e.g. 1, 2, 3",
    )

    @field_validator("unit", mode="before")
    @classmethod
    def parse_unit(cls, v: Any) -> Optional[int]:
        return parse_unit_value(v)


class DocumentIdMetaData(BaseModel):
    subject_id: str = Field(...)
