import unittest

import pandas as pd

from analysis import compute_combined_economic_summary
from thermal import calculate_thermal_source, evaluate_electric_alternatives


class ThermalEconomicConsistencyTests(unittest.TestCase):
    def test_combined_savings_include_reference_household_electricity(self):
        thermal_summary = {
            "payback_reference": "gas_natural",
            "sources": [{
                "source_key": "gas_natural",
                "source_name": "Gas natural",
                "annual_total_cost_eur": 500.0,
                "capex_eur": 1000.0,
            }],
            "electric_alternatives_with_pv": [{
                "source_key": "aerotermia",
                "source_name": "Aerotermia",
                "capex_eur": 2000.0,
                "system_energy_cost_eur": 300.0,
                "reference_household_electricity_cost_eur": 400.0,
            }],
        }

        result = compute_combined_economic_summary(
            thermal_summary,
            {"capex_total": 5000.0, "annual_om": 100.0},
            {"project_life_years": 1, "discount_rate_pct": 0.0, "annual_inflation_pct": 0.0},
        )

        comparison = result["comparisons"][0]
        self.assertEqual(comparison["reference_annual_cost"], 900.0)
        self.assertEqual(comparison["package_annual_cost"], 400.0)
        self.assertEqual(comparison["annual_saving"], 500.0)
        self.assertEqual(comparison["incremental_capex"], 6000.0)

    def test_electric_alternatives_expose_grid_only_household_cost(self):
        index = pd.date_range("2026-01-01", periods=2, freq="h")
        pv = pd.Series([0.0, 0.0], index=index)
        household_load = pd.Series([1.0, 2.0], index=index)

        alternatives = evaluate_electric_alternatives(
            pv,
            household_load,
            {"sources": ["aerotermia"], "annual_heat_demand_kwh": 0.0},
            {"enabled": False},
            {"electricity_buy_price_eur_kwh": 0.2, "electricity_sell_price_eur_kwh": 0.1},
        )

        self.assertAlmostEqual(alternatives[0]["reference_household_electricity_cost_eur"], 0.6)

    def test_geothermal_capex_includes_drilling_and_heat_pump(self):
        location = {
            "ground": {
                "mean_ground_temp_c": 14.5,
                "thermal_conductivity_w_mk": 2.2,
                "groundwater_level_m": 5.0,
            }
        }

        result = calculate_thermal_source(
            10000.0,
            "geotermia",
            {"peak_power_kw": 8.0, "location_config": location},
        )
        design = result["geothermal_design"]

        self.assertEqual(design["estimated_heat_pump_capex_eur"], 12000.0)
        self.assertEqual(
            result["capex_eur"],
            design["estimated_drilling_capex_eur"] + design["estimated_heat_pump_capex_eur"],
        )

    def test_combined_benefit_subtracts_scheduled_replacements(self):
        thermal_summary = {
            "payback_reference": "gas_natural",
            "sources": [{
                "source_key": "gas_natural",
                "source_name": "Gas natural",
                "annual_total_cost_eur": 500.0,
                "capex_eur": 1000.0,
            }],
            "electric_alternatives_with_pv": [{
                "source_key": "aerotermia",
                "source_name": "Aerotermia",
                "capex_eur": 2000.0,
                "system_energy_cost_eur": 300.0,
                "reference_household_electricity_cost_eur": 400.0,
            }],
        }

        result = compute_combined_economic_summary(
            thermal_summary,
            {
                "capex_total": 5000.0,
                "annual_om": 100.0,
                "lifecycle_impact": {"replacements": [{"year": 1, "type": "Inversor", "cost": 250.0}]},
            },
            {"project_life_years": 1, "discount_rate_pct": 0.0, "annual_inflation_pct": 0.0},
        )

        comparison = result["comparisons"][0]
        self.assertEqual(comparison["net_saving_over_life"], -5750.0)
        self.assertEqual(comparison["npv"], -5750.0)
        self.assertEqual(comparison["replacement_cost_over_life"], 250.0)


if __name__ == "__main__":
    unittest.main()