import unittest
from types import SimpleNamespace

from report import (
    _combined_economic_section,
    _economically_viable,
    _payback_label,
    _personalized_analysis,
    _thermal_savings_section,
    _thermal_section,
)


class ReportRecommendationTests(unittest.TestCase):
    def test_payback_beyond_horizon_is_marked_as_economically_discarded(self):
        rendered = _payback_label(325.0, 20.0)

        self.assertIn("Descartada econòmicament", rendered)
        self.assertIn("no es recupera en 20 anys", rendered)
        self.assertIn("325.0 anys", rendered)

    def test_thermal_tables_and_narrative_flag_payback_beyond_horizon(self):
        active = {
            "source_key": "aerotermia",
            "source_name": "Aerotèrmia",
            "performance": 3.5,
            "input_energy_kwh": 3000.0,
            "primary_energy_total_kwh": 6000.0,
            "primary_energy_nonrenewable_kwh": 3000.0,
            "renewable_primary_kwh": 3000.0,
            "emissions_kg_co2e": 700.0,
            "annual_total_cost_eur": 1000.0,
            "annualized_total_cost_eur": 1200.0,
            "capex_eur": 1000.0,
        }
        geothermal = {
            **active,
            "source_key": "geotermia",
            "source_name": "Geotèrmia",
            "performance": 4.5,
            "annual_total_cost_eur": 900.0,
            "annualized_total_cost_eur": 2825.0,
            "capex_eur": 33500.0,
            "emissions_kg_co2e": 500.0,
            "payback_years": 325.0,
            "payback_within_horizon": False,
            "payback_horizon_years": 20.0,
            "annual_operating_saving_vs_reference_eur": 100.0,
            "additional_capex_vs_reference_eur": 32500.0,
        }
        thermal_summary = {
            "sources": [active, geothermal],
            "active_source": active,
            "recommended": geothermal,
            "best_cost": geothermal,
            "best_environment": geothermal,
            "best_energy": geothermal,
            "heat_demand_kwh": 10000.0,
            "analysis_years": 20,
            "payback_reference": "aerotermia",
        }

        table_html = _thermal_section(thermal_summary)
        narrative_html = _thermal_savings_section(thermal_summary)

        self.assertIn("Descartada econòmicament", table_html)
        self.assertIn("no recupera dins l’horitzó", table_html)
        self.assertNotIn('class="badge best">✓ Recomanat</span>', table_html)
        self.assertIn("325.0 anys", table_html)
        self.assertIn("No es recomana econòmicament", narrative_html)
        self.assertIn("supera l'horitzó de 20 anys", narrative_html)

    def test_package_requires_positive_npv_and_payback_within_horizon(self):
        self.assertTrue(_economically_viable({"npv": 100.0, "payback_years": 10.0}, 25.0))
        self.assertFalse(_economically_viable({"npv": 100.0, "payback_years": 30.0}, 25.0))
        self.assertFalse(_economically_viable({"npv": -1.0, "payback_years": 10.0}, 25.0))

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
            "annual_operating_cost_eur": 1500.0,
            "package_annual_cost": 1500.0,
            "self_consumption_rate_pct": 60.0,
            "self_sufficiency_rate_pct": 50.0,
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
        self.assertIn("Cap bomba de calor combina VAN positiu i retorn dins els 25 anys", rendered)
        self.assertNotIn("Millor opció viable entre bombes de calor", rendered)

    def test_positive_npv_selects_the_highest_npv_heat_pump(self):
        summary = self._combined_summary(1200.0, 2400.0)
        for comparison in summary["comparisons"]:
            comparison["annual_saving"] = 500.0
            comparison["payback_years"] = 5.0
        rendered = _combined_economic_section(summary)

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
        self.assertIn("Combinacions de sistema provades, ordenades per VAN", rendered)
        self.assertIn("FV 8.0 kWp", rendered)
        self.assertIn("CAPEX total paquet", rendered)
        self.assertIn("Autoconsum", rendered)
        self.assertIn("Autosuficiència", rendered)

    def test_report_renders_every_size_and_heating_candidate(self):
        summary = self._combined_summary(-2000.0, -1000.0)
        summary["comparisons"].append(
            self._comparison("electricitat_resistencia", "Resistència", -3000.0, -200.0)
        )
        summary["configuration_scenarios"] = []
        for pv_kwp in (3.0, 5.0, 8.0):
            for battery_kwh in (0.0, 3.0, 6.0):
                for source_key, source_name in (
                    ("aerotermia", "Aerotèrmia"),
                    ("geotermia", "Geotèrmia"),
                    ("electricitat_resistencia", "Resistència"),
                ):
                    summary["configuration_scenarios"].append({
                        **self._comparison(source_key, source_name, 1000.0 - pv_kwp, 500.0),
                        "pv_peak_power_kwp": pv_kwp,
                        "battery_capacity_kwh": battery_kwh,
                        "input_energy_kwh": 2500.0,
                        "grid_import_kwh": 1200.0,
                        "emissions_kg_co2e": 450.0,
                        "is_current_configuration": pv_kwp == 5.0 and battery_kwh == 3.0,
                    })

        rendered = _combined_economic_section(summary)

        self.assertEqual(rendered.count('<tr class="scenario-row">'), 27)
        self.assertIn("Referència COP 1", rendered)
        self.assertIn("60.0%", rendered)
        self.assertIn("50.0%", rendered)

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