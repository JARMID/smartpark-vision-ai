"""
Algerian License Plate Parser and Normalization Engine.
Implements the Algerian vehicle registration scheme under national transport regulations.
"""

from dataclasses import dataclass
from enum import Enum
import re
from typing import Optional, Dict


class PlateType(str, Enum):
    CIVILIAN_STANDARD = "civilian_standard"
    TEMPORARY_00 = "temporary_00"
    DIPLOMATIC = "diplomatic"
    STATE_OFFICIAL = "state_official"
    INVALID = "invalid"


# Official 58 Wilayas of Algeria
ALGERIAN_WILAYAS: Dict[str, str] = {
    "01": "Adrar",
    "02": "Chlef",
    "03": "Laghouat",
    "04": "Oum El Bouaghi",
    "05": "Batna",
    "06": "Béjaïa",
    "07": "Biskra",
    "08": "Béchar",
    "09": "Blida",
    "10": "Bouira",
    "11": "Tamanrasset",
    "12": "Tébessa",
    "13": "Tlemcen",
    "14": "Tiaret",
    "15": "Tizi Ouzou",
    "16": "Alger",
    "17": "Djelfa",
    "18": "Jijel",
    "19": "Sétif",
    "20": "Saïda",
    "21": "Skikda",
    "22": "Sidi Bel Abbès",
    "23": "Annaba",
    "24": "Guelma",
    "25": "Constantine",
    "26": "Médéa",
    "27": "Mostaganem",
    "28": "M'Sila",
    "29": "Mascara",
    "30": "Ouargla",
    "31": "Oran",
    "32": "El Bayadh",
    "33": "Illizi",
    "34": "Bordj Bou Arréridj",
    "35": "Boumerdès",
    "36": "El Tarf",
    "37": "Tindouf",
    "38": "Tissemsilt",
    "39": "El Oued",
    "40": "Khenchela",
    "41": "Souk Ahras",
    "42": "Tipaza",
    "43": "Mila",
    "44": "Aïn Defla",
    "45": "Naâma",
    "46": "Aïn Témouchent",
    "47": "Ghardaïa",
    "48": "Relizane",
    "49": "El M'Ghair",
    "50": "El Meniaa",
    "51": "Ouled Djellal",
    "52": "Bordj Baji Mokhtar",
    "53": "Béni Abbès",
    "54": "Timimoun",
    "55": "Touggourt",
    "56": "Djanet",
    "57": "In Salah",
    "58": "In Guezzam",
}

# OCR character normalization mapping for common optical letter-to-digit errors
OCR_DIGIT_NORMALIZATION = {
    "O": "0",
    "Q": "0",
    "D": "0",
    "I": "1",
    "L": "1",
    "Z": "2",
    "E": "3",
    "A": "4",
    "S": "5",
    "G": "6",
    "B": "8",
}


@dataclass
class PlateParseResult:
    is_valid: bool
    raw_input: str
    plate_type: PlateType
    formatted: str = ""
    sequential_number: str = ""
    middle_code: str = ""
    vehicle_category: Optional[int] = None
    registration_year: Optional[int] = None
    wilaya_code: str = ""
    wilaya_name: str = ""
    error_message: str = ""


class AlgerianPlateParser:
    """
    Parser for Algerian Vehicle Registration Plates.
    Handles civilian plates, temporary 00 plates, and diplomatic vehicles.
    """

    def __init__(self):
        self.wilayas = ALGERIAN_WILAYAS
        self.normalization_map = OCR_DIGIT_NORMALIZATION

    def normalize_ocr_text(self, text: str) -> str:
        """Standardize raw OCR string, upper-case, strip spaces and apply digit fixes."""
        cleaned = text.strip().upper()
        # Remove separators like dashes, dots, slashes
        cleaned = re.sub(r"[\s\-\.\/]", " ", cleaned)
        return cleaned

    def parse(self, raw_text: str) -> PlateParseResult:
        if not raw_text or len(raw_text.strip()) == 0:
            return PlateParseResult(
                is_valid=False,
                raw_input=raw_text,
                plate_type=PlateType.INVALID,
                error_message="Empty plate string",
            )

        normalized = self.normalize_ocr_text(raw_text)

        # 1. Check for Diplomatic / Consular prefixes
        diplo_match = re.match(r"^(CD|CC|CMD)\s*(\d+)\s*(\d{2})$", normalized)
        if diplo_match:
            prefix = diplo_match.group(1)
            seq = diplo_match.group(2)
            wilaya = diplo_match.group(3)
            if wilaya in self.wilayas:
                return PlateParseResult(
                    is_valid=True,
                    raw_input=raw_text,
                    plate_type=PlateType.DIPLOMATIC,
                    formatted=f"{prefix} {seq} {wilaya}",
                    sequential_number=seq,
                    wilaya_code=wilaya,
                    wilaya_name=self.wilayas[wilaya],
                )

        # 2. Extract digits and apply optical OCR normalizations
        tokens = normalized.split()
        normalized_tokens = []
        for token in tokens:
            # Map optical character confusions to digits if the token is mostly numeric
            repaired = "".join(self.normalization_map.get(ch, ch) for ch in token)
            normalized_tokens.append(repaired)

        merged_digits = "".join(re.findall(r"\d+", "".join(normalized_tokens)))

        # Algerian civilian plates must have between 5 and 11 total digits:
        # e.g., '104822 119 16' (11 digits), '08412 00 16' (9 digits), '482 124 31' (8 digits)
        if len(merged_digits) < 5 or len(merged_digits) > 11:
            return PlateParseResult(
                is_valid=False,
                raw_input=raw_text,
                plate_type=PlateType.INVALID,
                error_message=f"Invalid total digit count ({len(merged_digits)}) for Algerian plate",
            )

        # 3. Extract Wilaya code (last 2 digits)
        wilaya_code = merged_digits[-2:]
        if wilaya_code not in self.wilayas:
            return PlateParseResult(
                is_valid=False,
                raw_input=raw_text,
                plate_type=PlateType.INVALID,
                error_message=f"Wilaya code '{wilaya_code}' is invalid (valid range is 01 to 58)",
            )

        wilaya_name = self.wilayas[wilaya_code]

        # 4. Check for Temporary '00' registration (Carte grise provisoire)
        # In temporary plates, the 2 digits preceding the wilaya code are '00'
        # e.g., '04182 00 16' or '120482 00 31'
        if merged_digits[-4:-2] == "00":
            sequential = merged_digits[:-4]
            if 1 <= len(sequential) <= 6:
                return PlateParseResult(
                    is_valid=True,
                    raw_input=raw_text,
                    plate_type=PlateType.TEMPORARY_00,
                    formatted=f"{sequential} 00 {wilaya_code}",
                    sequential_number=sequential,
                    middle_code="00",
                    wilaya_code=wilaya_code,
                    wilaya_name=wilaya_name,
                )

        # 5. Standard Civilian Plate: 3-digit category & year code
        # e.g. '119' -> Category 1 (Passenger Car), Year 2019
        if len(merged_digits) < 6:
            return PlateParseResult(
                is_valid=False,
                raw_input=raw_text,
                plate_type=PlateType.INVALID,
                error_message="Plate string too short for standard civilian format",
            )

        category_year = merged_digits[-5:-2]
        sequential = merged_digits[:-5]

        if not (1 <= len(sequential) <= 6):
            return PlateParseResult(
                is_valid=False,
                raw_input=raw_text,
                plate_type=PlateType.INVALID,
                error_message=f"Sequential registration number length ({len(sequential)}) out of range",
            )

        category_digit = int(category_year[0])
        year_digits = int(category_year[1:])

        # Category digit must be 1 to 9
        if category_digit < 1 or category_digit > 9:
            return PlateParseResult(
                is_valid=False,
                raw_input=raw_text,
                plate_type=PlateType.INVALID,
                error_message=f"Vehicle category digit '{category_digit}' is invalid (must be 1-9)",
            )

        # Calculate 4-digit registration year
        # Years 00-40 are treated as 2000-2040; years 70-99 as 1970-1999
        if year_digits <= 40:
            reg_year = 2000 + year_digits
        else:
            reg_year = 1900 + year_digits

        formatted_plate = f"{sequential} {category_year} {wilaya_code}"

        return PlateParseResult(
            is_valid=True,
            raw_input=raw_text,
            plate_type=PlateType.CIVILIAN_STANDARD,
            formatted=formatted_plate,
            sequential_number=sequential,
            middle_code=category_year,
            vehicle_category=category_digit,
            registration_year=reg_year,
            wilaya_code=wilaya_code,
            wilaya_name=wilaya_name,
        )
