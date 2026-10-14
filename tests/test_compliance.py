"""
Unit tests for Algerian Law 18-07 and Law 25-11 compliance engine.
"""

import unittest
from datetime import datetime, timedelta
from src.compliance.law_25_11_audit import Law2511ComplianceEngine


class TestLaw2511ComplianceEngine(unittest.TestCase):

    def setUp(self):
        self.engine = Law2511ComplianceEngine(facility_code="DZ-ALG-01", facility_name="Parking Municipal Alger-Centre")

    def test_dpia_generation_contains_statutory_references(self):
        dpia = self.engine.generate_dpia(dpo_name="Mohamed Cherif", dpo_phone="+213 550 11 22 33")
        self.assertEqual(dpia["dossier_type"], "DPIA_ANPDP_ALGERIA")
        self.assertIn("Loi n° 25-11", dpia["statutory_reference"])
        self.assertEqual(len(dpia["data_categories_processed"]), 3)
        self.assertIn("100% de l'inférence", dpia["risk_mitigation_measures"][0]["mitigation"])

    def test_processing_register_has_mandatory_activities(self):
        reg = self.engine.get_processing_register()
        self.assertGreaterEqual(len(reg), 4)
        activity_names = [r["activity_name"] for r in reg]
        self.assertTrue(any("ALPR" in name for name in activity_names))
        self.assertTrue(any("Biométrique" in name for name in activity_names))

    def test_breach_triage_deadline_exact_5_days(self):
        dossier = self.engine.create_breach_triage_dossier(
            incident_type="TENTATIVE_EXTRACTION_NON_AUTORISEE",
            severity="HIGH",
            description="Tentative de dump de la table registered_vehicles",
            impacted_records=250,
        )
        self.assertEqual(dossier["severity"], "HIGH")
        self.assertEqual(dossier["status"], "TRIAGE_OPEN")
        # Statutory window must be exactly ~120 hours (5 days)
        self.assertGreaterEqual(dossier["hours_remaining_until_statutory_breach"], 119)
        self.assertLessEqual(dossier["hours_remaining_until_statutory_breach"], 120)
        self.assertEqual(len(dossier["containment_checklist"]), 4)

    def test_rolling_purge_plan(self):
        now = datetime.now()
        events = [
            {"id": "ev-new", "timestamp_full": now.strftime("%Y-%m-%d %H:%M:%S"), "is_flagged_incident": False},
            {"id": "ev-old", "timestamp_full": (now - timedelta(days=35)).strftime("%Y-%m-%d %H:%M:%S"), "is_flagged_incident": False},
            {"id": "ev-old-flagged", "timestamp_full": (now - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S"), "is_flagged_incident": True},
        ]
        result = self.engine.execute_rolling_purge_plan(events)
        self.assertEqual(result["records_purged"], 1)  # Only ev-old is purged
        self.assertEqual(result["records_retained"], 2)  # ev-new and ev-old-flagged are retained


if __name__ == "__main__":
    unittest.main()
