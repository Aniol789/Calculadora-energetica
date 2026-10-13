import unittest

from report import GLOSSARY_TABS_SCRIPT, _glossary_section


class ReportGlossaryTests(unittest.TestCase):
    def test_glossary_defines_core_economic_and_energy_terms(self):
        glossary = _glossary_section()

        for term in (
            "Flux net anual FV",
            "CAPEX (inversió inicial)",
            "BOS (balance of system)",
            "OPEX (costos recurrents)",
            "Cost anualitzat tèrmic",
            "VAN FV/bateria",
            "VAN del paquet combinat",
            "Retorn simple FV/bateria",
            "Retorn simple tèrmic",
            "Retorn simple del paquet",
            "Energia primària no renovable",
            "Autoconsum",
            "Autosuficiència",
            "CO₂e",
            "UA i graus-hora",
            "Conductivitat i difusivitat del sòl",
        ):
            with self.subTest(term=term):
                self.assertIn(term, glossary)

        self.assertIn("abans de restar el CAPEX inicial", glossary)
        self.assertIn("respecte del sistema de referència actiu", glossary)
        self.assertIn("no aplica taxa de descompte", glossary)
        self.assertIn('role="tablist"', glossary)
        self.assertIn('aria-selected="true"', glossary)
        self.assertIn("Llenguatge planer", glossary)
        self.assertIn("Són els diners que cal posar al principi", glossary)
        self.assertEqual(glossary.count("<dt>"), glossary.count("<dd>"))
        self.assertEqual(glossary.count("<dt>CAPEX (inversió inicial)</dt>"), 2)
        self.assertIn("ArrowRight", GLOSSARY_TABS_SCRIPT)
        self.assertIn("ArrowLeft", GLOSSARY_TABS_SCRIPT)
        self.assertIn("aria-selected", GLOSSARY_TABS_SCRIPT)


if __name__ == "__main__":
    unittest.main()