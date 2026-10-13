import unittest
from types import SimpleNamespace

from report import _combined_economic_section, _personalized_analysis


class ReportRecommendationTests(unittest.TestCase):
    def _comparison(self, source_key, source_name, npv, annual_saving):
        return {
            "source_key": source_key,
            "source_name": source_name,
            "npv": npv,
            "payback_years": None if annual_saving <= 0 else 5.0,
            "package_capex": 12000.0,
            "pv_battery_capex": 8000.0,
            "heating_capex": 4000.0,
            "incremental_capex": 11000.0,
            "annual_saving": annual_saving,
            "replacement_cost_over_life": 1000.0,
            "net_saving_over_life": npv,
        }

    def _combined_summary(self, npv_aerotermia, npv_geotermia):
        return {
            "comparisons": [
                self._comparison("aerotermia", "Aerotèrmia", npv_aerotermia, -100.0),
                self._comparison("geotermia", "Geotèrmia", npv_geotermia, -50.0),
            ],
            "source_details": [
                {"source_key": "aerotermia", "input_energy_kwh": 3000.0},
                {"source_key": "geotermia", "input_energy_kwh": 2500.0},
            ],
            "reference_name": "Gas natural",
            "project_life_years": 25,
            "pv_capex": 6000.0,
            "battery_capex": 2000.0,
            "installation_extra": 500.0,
        }

    def test_negative_npv_does_not_recommend_a_heat_pump_package(self):
        rendered = _combined_economic_section(self._combined_summary(-2000.0, -1000.0))

        self.assertIn("Cap opció viable", rendered)
        self.assertIn("Cap bomba de calor té VAN positiu", rendered)
        self.assertNotIn("Millor opció viable entre bombes de calor", rendered)

    def test_positive_npv_selects_the_highest_npv_heat_pump(self):
        rendered = _combined_economic_section(self._combined_summary(1200.0, 2400.0))

        self.assertIn("Geotèrmia", rendered)
        self.assertIn("VAN: 2400 €", rendered)
        self.assertIn("Millor bomba de calor amb FV/bateria actuals", rendered)

    def test_report_displays_best_tested_system_combination(self):
        summary = self._combined_summary(-2000.0, -1000.0)
        summary["configuration_scenarios"] = [{
            **self._comparison("aerotermia", "Aerotèrmia", 1800.0, 700.0),
            "pv_peak_power_kwp": 8.0,
            "battery_capacity_kwh": 0.0,
            "input_energy_kwh": 2800.0,
            "grid_import_kwh": 5200.0,
            "emissions_kg_co2e": 500.0,
            "is_current_configuration": False,
        }]

        rendered = _combined_economic_section(summary)

        self.assertIn("Millor resultat: <strong>Aerotèrmia, FV 8.0 kWp, bateria 0.0 kWh; VAN 1800 €", rendered)
        self.assertIn("Combinació de sistema amb millor resultat econòmic provat", rendered)
        self.assertIn("FV 8.0 kWp", rendered)

    def test_thermal_comparison_reports_cost_increase_without_false_payback(self):
        thermal_summary = {
            "active_source": {
                "source_name": "Gas natural",
                "annual_total_cost_eur": 1000.0,
                "emissions_kg_co2e": 2000.0,
                "primary_energy_nonrenewable_kwh": 4000.0,
                "capex_eur": 1000.0,
            },
            "recommended": {
                "source_name": "Aerotèrmia",
                "annual_total_cost_eur": 1100.0,
                "emissions_kg_co2e": 1500.0,
                "primary_energy_nonrenewable_kwh": 3500.0,
                "capex_eur": 5000.0,
                "performance": 3.5,
            },
            "heat_demand_kwh": 10000.0,
        }
        config = SimpleNamespace(
            PV_SYSTEM={"peak_power_kwp": 5.0},
            BATTERY={"enabled": False},
        )

        rendered = _personalized_analysis(
            thermal_summary,
            {"self_consumption_rate": 40.0, "self_sufficiency_rate": 30.0, "total_pv": 5000.0},
            {"payback_years": None},
            config,
            {
                "reference_name": "Gas natural",
                "comparisons": [
                    {"source_key": "aerotermia", "source_name": "Aerotèrmia", "npv": -2500.0},
                    {"source_key": "geotermia", "source_name": "Geotèrmia", "npv": -4000.0},
                ],
            },
        )

        self.assertIn("increment estimat de <strong>100 €/any", rendered)
        self.assertIn("Amb l'estalvi operatiu calculat no es recupera", rendered)
        self.assertIn("no s'aconsella invertir en cap combinació FV+bateria+bomba de calor provada", rendered)
        self.assertNotIn("Estalviaria <strong>100 €/any", rendered)
        self.assertNotIn("payback de 0.0 anys", rendered)


if __name__ == "__main__":
    unittest.main()