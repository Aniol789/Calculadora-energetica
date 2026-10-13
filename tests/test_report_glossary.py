import unittest

from report import _glossary_section


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


if __name__ == "__main__":
    unittest.main()