"""
Unit tests for the Algerian License Plate Parsing and Normalization Engine.
Compliant with Algerian vehicle registration standards (Decree on vehicle identification).
"""

import unittest
import sys
import os

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.alpr.algerian_plate_parser import AlgerianPlateParser, PlateType


class TestAlgerianPlateParser(unittest.TestCase):
    def setUp(self):
        self.parser = AlgerianPlateParser()

    def test_standard_civilian_5_digit(self):
        result = self.parser.parse("08412 119 16")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.plate_type, PlateType.CIVILIAN_STANDARD)
        self.assertEqual(result.sequential_number, "08412")
        self.assertEqual(result.vehicle_category, 1)
        self.assertEqual(result.registration_year, 2019)
        self.assertEqual(result.wilaya_code, "16")
        self.assertEqual(result.wilaya_name, "Alger")
        self.assertEqual(result.formatted, "08412 119 16")

    def test_high_density_wilaya_6_digit_serial(self):
        # High density wilayas like Algiers (16) and Oran (31) issue 6-digit serials
        result = self.parser.parse("104822 121 16")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.plate_type, PlateType.CIVILIAN_STANDARD)
        self.assertEqual(result.sequential_number, "104822")
        self.assertEqual(result.vehicle_category, 1)
        self.assertEqual(result.registration_year, 2021)
        self.assertEqual(result.wilaya_code, "16")
        self.assertEqual(result.formatted, "104822 121 16")

    def test_temporary_00_plate(self):
        # Brand new vehicles circulate with '00' before receiving permanent carte grise
        result = self.parser.parse("04182 00 16")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.plate_type, PlateType.TEMPORARY_00)
        self.assertEqual(result.sequential_number, "04182")
        self.assertEqual(result.wilaya_code, "16")
        self.assertEqual(result.formatted, "04182 00 16")

    def test_temporary_00_plate_6_digit(self):
        result = self.parser.parse("120482 00 31")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.plate_type, PlateType.TEMPORARY_00)
        self.assertEqual(result.sequential_number, "120482")
        self.assertEqual(result.wilaya_code, "31")
        self.assertEqual(result.wilaya_name, "Oran")
        self.assertEqual(result.formatted, "120482 00 31")

    def test_commercial_van_category(self):
        # Category 3 = Camionnette / Light Commercial Van
        result = self.parser.parse("01412 322 09")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.vehicle_category, 3)
        self.assertEqual(result.registration_year, 2022)
        self.assertEqual(result.wilaya_code, "09")
        self.assertEqual(result.wilaya_name, "Blida")

    def test_heavy_truck_category(self):
        # Category 2 = Camion / Heavy Commercial Truck
        result = self.parser.parse("00912 218 25")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.vehicle_category, 2)
        self.assertEqual(result.registration_year, 2018)
        self.assertEqual(result.wilaya_code, "25")
        self.assertEqual(result.wilaya_name, "Constantine")

    def test_optical_ocr_character_normalization(self):
        # OCR common letter confusions: O->0, I->1, B->8, S->5
        result = self.parser.parse("O84I2 119 16")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.sequential_number, "08412")
        self.assertEqual(result.formatted, "08412 119 16")

    def test_diplomatic_series(self):
        result = self.parser.parse("CD 0412 16")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.plate_type, PlateType.DIPLOMATIC)
        self.assertEqual(result.wilaya_code, "16")

    def test_invalid_wilaya_code(self):
        # Wilaya 99 does not exist in Algeria (valid wilayas are 01 to 58)
        result = self.parser.parse("08412 119 99")
        self.assertFalse(result.is_valid)
        self.assertIn("wilaya", result.error_message.lower())

    def test_arabic_wilaya_and_category_metadata(self):
        result = self.parser.parse("104822 121 16")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.wilaya_name, "Alger")
        self.assertEqual(result.wilaya_name_ar, "الجزائر")
        self.assertEqual(result.category_name_fr, "Véhicule de tourisme / Particulier")
        self.assertEqual(result.category_name_ar, "سيارة سياحية خاصة")
        self.assertEqual(result.confidence, 1.0)
        self.assertFalse(result.is_ambiguous)
        self.assertEqual(result.substitutions_applied, [])

    def test_ambiguity_tracking_and_confidence_scoring(self):
        # Two optical substitutions: O->0 and I->1
        result = self.parser.parse("O84I2 119 16")
        self.assertTrue(result.is_valid)
        self.assertTrue(result.is_ambiguous)
        self.assertEqual(len(result.substitutions_applied), 2)
        self.assertIn("O->0", result.substitutions_applied)
        self.assertIn("I->1", result.substitutions_applied)
        self.assertEqual(result.confidence, 0.90)  # 1.0 - 2 * 0.05

    def test_temporary_plate_arabic_metadata(self):
        result = self.parser.parse("04182 00 31")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.wilaya_name, "Oran")
        self.assertEqual(result.wilaya_name_ar, "وهران")
        self.assertEqual(result.category_name_fr, "Carte grise provisoire")
        self.assertEqual(result.category_name_ar, "بطاقة رمادية مؤقتة")

    def test_to_dict_serialization(self):
        result = self.parser.parse("01412 322 09")
        self.assertTrue(result.is_valid)
        d = result.to_dict()
        self.assertEqual(d["formatted"], "01412 322 09")
        self.assertEqual(d["wilaya_code"], "09")
        self.assertEqual(d["wilaya_name"], "Blida")
        self.assertEqual(d["wilaya_name_ar"], "البليدة")
        self.assertEqual(d["vehicle_category"], 3)
        self.assertEqual(d["category_name_fr"], "Camionnette / Utilitaire léger")
        self.assertEqual(d["category_name_ar"], "مركبة نفعية خفيفة")
        self.assertIn("confidence", d)
        self.assertIn("is_ambiguous", d)


if __name__ == "__main__":
    unittest.main()

