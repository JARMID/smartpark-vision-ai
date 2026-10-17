"""
Algerian License Plate Parser and Normalization Engine.
Implements the Algerian vehicle registration scheme under national transport regulations.
"""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Optional, Dict, List, Any, Tuple


class PlateType(str, Enum):
    CIVILIAN_STANDARD = "civilian_standard"
    TEMPORARY_00 = "temporary_00"
    DIPLOMATIC = "diplomatic"
    STATE_OFFICIAL = "state_official"
    INVALID = "invalid"


# Official 58 Wilayas of Algeria (French and Arabic administrative designations)
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

ALGERIAN_WILAYAS_AR: Dict[str, str] = {
    "01": "أدرار",
    "02": "الشلف",
    "03": "الأغواط",
    "04": "أم البواقي",
    "05": "باتنة",
    "06": "بجاية",
    "07": "بسكرة",
    "08": "بشار",
    "09": "البليدة",
    "10": "البويرة",
    "11": "تمنراست",
    "12": "تبسة",
    "13": "تلمسان",
    "14": "تيارت",
    "15": "تيزي وزو",
    "16": "الجزائر",
    "17": "الجلفة",
    "18": "جيجل",
    "19": "سطيف",
    "20": "سعيدة",
    "21": "سكيكدة",
    "22": "سيدي بلعباس",
    "23": "عنابة",
    "24": "قالمة",
    "25": "قسنطينة",
    "26": "المدية",
    "27": "مستغانم",
    "28": "المسيلة",
    "29": "معسكر",
    "30": "ورقلة",
    "31": "وهران",
    "32": "البيض",
    "33": "إليزي",
    "34": "برج بوعريريج",
    "35": "بومرداس",
    "36": "الطارف",
    "37": "تندوف",
    "38": "تيسمسيلت",
    "39": "الوادي",
    "40": "خنشلة",
    "41": "سوق أهراس",
    "42": "تيبازة",
    "43": "ميلة",
    "44": "عين الدفلى",
    "45": "النعامة",
    "46": "عين تموشنت",
    "47": "غرداية",
    "48": "غليزان",
    "49": "المغير",
    "50": "المنيعة",
    "51": "أولاد جلال",
    "52": "برج باجي مختار",
    "53": "بني عباس",
    "54": "تيميمون",
    "55": "تقرت",
    "56": "جانت",
    "57": "عين صالح",
    "58": "عين قزام",
}

# Algerian Vehicle Category Classification (National Vehicle Identification Decree)
VEHICLE_CATEGORIES_INFO: Dict[int, Tuple[str, str]] = {
    1: ("Véhicule de tourisme / Particulier", "سيارة سياحية خاصة"),
    2: ("Camion / Poids lourd", "شاحنة نقل بضائع"),
    3: ("Camionnette / Utilitaire léger", "مركبة نفعية خفيفة"),
    4: ("Autocar / Autobus / Transport collectif", "حافلة نقل مسافرين"),
    5: ("Tracteur routier", "جرار طريقي"),
    6: ("Tracteur agricole", "جرار فلاحي"),
    7: ("Véhicule spécial / Travaux publics", "مركبة أشغال خاصة"),
    8: ("Remorque / Semi-remorque", "مقطورة"),
    9: ("Deux-roues / Motocycle", "دراجة نارية"),
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
    category_name_fr: str = ""
    category_name_ar: str = ""
    registration_year: Optional[int] = None
    wilaya_code: str = ""
    wilaya_name: str = ""
    wilaya_name_ar: str = ""
    confidence: float = 1.0
    is_ambiguous: bool = False
    substitutions_applied: List[str] = field(default_factory=list)
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "raw_input": self.raw_input,
            "plate_type": self.plate_type.value if isinstance(self.plate_type, PlateType) else str(self.plate_type),
            "formatted": self.formatted,
            "sequential_number": self.sequential_number,
            "middle_code": self.middle_code,
            "vehicle_category": self.vehicle_category,
            "category_name_fr": self.category_name_fr,
            "category_name_ar": self.category_name_ar,
            "registration_year": self.registration_year,
            "wilaya_code": self.wilaya_code,
            "wilaya_name": self.wilaya_name,
            "wilaya_name_ar": self.wilaya_name_ar,
            "confidence": round(self.confidence, 3),
            "is_ambiguous": self.is_ambiguous,
            "substitutions_applied": self.substitutions_applied,
            "error_message": self.error_message,
        }


class AlgerianPlateParser:
    """
    Parser for Algerian Vehicle Registration Plates.
    Handles civilian plates, temporary 00 plates, and diplomatic vehicles.
    """

    def __init__(self):
        self.wilayas = ALGERIAN_WILAYAS
        self.wilayas_ar = ALGERIAN_WILAYAS_AR
        self.categories = VEHICLE_CATEGORIES_INFO
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
                    category_name_fr="Corps Diplomatique / Consulaire",
                    category_name_ar="سلك دبلوماسي وقنصلي",
                    wilaya_code=wilaya,
                    wilaya_name=self.wilayas[wilaya],
                    wilaya_name_ar=self.wilayas_ar.get(wilaya, ""),
                    confidence=1.0,
                    is_ambiguous=False,
                    substitutions_applied=[],
                )

        # 2. Extract digits and apply optical OCR normalizations with tracking
        tokens = normalized.split()
        normalized_tokens = []
        substitutions: List[str] = []
        for token in tokens:
            repaired_chars = []
            for ch in token:
                if ch in self.normalization_map:
                    mapped = self.normalization_map[ch]
                    substitutions.append(f"{ch}->{mapped}")
                    repaired_chars.append(mapped)
                else:
                    repaired_chars.append(ch)
            normalized_tokens.append("".join(repaired_chars))

        merged_digits = "".join(re.findall(r"\d+", "".join(normalized_tokens)))
        confidence = max(0.50, round(1.0 - (0.05 * len(substitutions)), 3))
        is_ambiguous = len(substitutions) > 0

        # Algerian civilian plates must have between 5 and 11 total digits:
        # e.g., '104822 119 16' (11 digits), '08412 00 16' (9 digits), '482 124 31' (8 digits)
        if len(merged_digits) < 5 or len(merged_digits) > 11:
            return PlateParseResult(
                is_valid=False,
                raw_input=raw_text,
                plate_type=PlateType.INVALID,
                confidence=confidence,
                is_ambiguous=is_ambiguous,
                substitutions_applied=substitutions,
                error_message=f"Invalid total digit count ({len(merged_digits)}) for Algerian plate",
            )

        # 3. Extract Wilaya code (last 2 digits)
        wilaya_code = merged_digits[-2:]
        if wilaya_code not in self.wilayas:
            return PlateParseResult(
                is_valid=False,
                raw_input=raw_text,
                plate_type=PlateType.INVALID,
                confidence=confidence,
                is_ambiguous=is_ambiguous,
                substitutions_applied=substitutions,
                error_message=f"Wilaya code '{wilaya_code}' is invalid (valid range is 01 to 58)",
            )

        wilaya_name = self.wilayas[wilaya_code]
        wilaya_name_ar = self.wilayas_ar.get(wilaya_code, "")

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
                    category_name_fr="Carte grise provisoire",
                    category_name_ar="بطاقة رمادية مؤقتة",
                    wilaya_code=wilaya_code,
                    wilaya_name=wilaya_name,
                    wilaya_name_ar=wilaya_name_ar,
                    confidence=confidence,
                    is_ambiguous=is_ambiguous,
                    substitutions_applied=substitutions,
                )

        # 5. Standard Civilian Plate: 3-digit category & year code
        # e.g. '119' -> Category 1 (Passenger Car), Year 2019
        if len(merged_digits) < 6:
            return PlateParseResult(
                is_valid=False,
                raw_input=raw_text,
                plate_type=PlateType.INVALID,
                confidence=confidence,
                is_ambiguous=is_ambiguous,
                substitutions_applied=substitutions,
                error_message="Plate string too short for standard civilian format",
            )

        category_year = merged_digits[-5:-2]
        sequential = merged_digits[:-5]

        if not (1 <= len(sequential) <= 6):
            return PlateParseResult(
                is_valid=False,
                raw_input=raw_text,
                plate_type=PlateType.INVALID,
                confidence=confidence,
                is_ambiguous=is_ambiguous,
                substitutions_applied=substitutions,
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
                confidence=confidence,
                is_ambiguous=is_ambiguous,
                substitutions_applied=substitutions,
                error_message=f"Vehicle category digit '{category_digit}' is invalid (must be 1-9)",
            )

        # Calculate 4-digit registration year
        # Years 00-40 are treated as 2000-2040; years 70-99 as 1970-1999
        if year_digits <= 40:
            reg_year = 2000 + year_digits
        else:
            reg_year = 1900 + year_digits

        formatted_plate = f"{sequential} {category_year} {wilaya_code}"
        cat_info = self.categories.get(
            category_digit, ("Véhicule de tourisme / Particulier", "سيارة سياحية خاصة")
        )

        return PlateParseResult(
            is_valid=True,
            raw_input=raw_text,
            plate_type=PlateType.CIVILIAN_STANDARD,
            formatted=formatted_plate,
            sequential_number=sequential,
            middle_code=category_year,
            vehicle_category=category_digit,
            category_name_fr=cat_info[0],
            category_name_ar=cat_info[1],
            registration_year=reg_year,
            wilaya_code=wilaya_code,
            wilaya_name=wilaya_name,
            wilaya_name_ar=wilaya_name_ar,
            confidence=confidence,
            is_ambiguous=is_ambiguous,
            substitutions_applied=substitutions,
        )
