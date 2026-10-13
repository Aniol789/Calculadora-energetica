import unittest

import pandas as pd

from analysis import compute_combined_economic_summary, evaluate_configuration_scenarios
from thermal import calculate_thermal_source, compare_thermal_sources, evaluate_electric_alternatives


class ThermalEconomicConsistencyTests(unittest.TestCase):
    def test_active_gasoil_source_overrides_natural_gas_payback_default(self):
        result = compare_thermal_sources(
            10000.0,
            {
                "sources": ["gas_natural", "gasoil"],
                "active_source": "gasoil",
                "payback_reference": "gas_natural",
                "peak_power_kw": 8.0,
                "analysis_years": 20,
            },
        )

        active_source = next(item for item in result["sources"] if item["source_key"] == "gasoil")
        self.assertEqual(result["payback_reference"], "gasoil")
        self.assertEqual(active_source["annual_operating_saving_vs_reference_eur"], 0.0)
        self.assertEqual(active_source["payback_years"], 0.0)

    def test_thermal_payback_beyond_analysis_horizon_is_flagged(self):
        result = compare_thermal_sources(
            10000.0,
            {
                "sources": ["gas_natural", "gasoil"],
                "active_source": "gas_natural",
                "peak_power_kw": 8.0,
                "analysis_years": 20,
                "source_overrides": {
                    "gasoil": {
                        "capex_eur_per_kw": 100000.0,
                        "resource_price_eur_per_kwh": 0.01,
                    }
                },
            },
        )

        gasoil = next(item for item in result["sources"] if item["source_key"] == "gasoil")
        self.assertGreater(gasoil["payback_years"], 20.0)
        self.assertFalse(gasoil["payback_within_horizon"])
        self.assertEqual(gasoil["payback_horizon_years"], 20.0)

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

    def test_electric_alternatives_expose_both_energy_rates(self):
        index = pd.date_range("2026-01-01", periods=2, freq="h")
        pv = pd.Series([2.0, 0.0], index=index)
        household_load = pd.Series([1.0, 1.0], index=index)

        alternatives = evaluate_electric_alternatives(
            pv,
            household_load,
            {"sources": ["aerotermia"], "annual_heat_demand_kwh": 0.0},
            {"enabled": False},
            {"electricity_buy_price_eur_kwh": 0.2, "electricity_sell_price_eur_kwh": 0.1},
        )

        self.assertEqual(alternatives[0]["self_consumption_rate_pct"], 50.0)
        self.assertEqual(alternatives[0]["self_sufficiency_rate_pct"], 50.0)

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

    def test_simple_payback_is_zero_when_saving_has_no_incremental_capex(self):
        thermal_summary = {
            "payback_reference": "gas_natural",
            "sources": [{
                "source_key": "gas_natural",
                "source_name": "Gas natural",
                "annual_total_cost_eur": 500.0,
                "capex_eur": 2000.0,
            }],
            "electric_alternatives_with_pv": [{
                "source_key": "aerotermia",
                "source_name": "Aerotèrmia",
                "capex_eur": 1000.0,
                "system_energy_cost_eur": 300.0,
                "reference_household_electricity_cost_eur": 400.0,
            }],
        }

        result = compute_combined_economic_summary(
            thermal_summary,
            {"capex_total": 0.0, "annual_om": 0.0},
            {"project_life_years": 1, "discount_rate_pct": 0.0, "annual_inflation_pct": 0.0},
        )

        self.assertEqual(result["comparisons"][0]["payback_years"], 0.0)

    def test_configuration_sweep_evaluates_all_heating_and_size_combinations(self):
        index = pd.date_range("2026-01-01", periods=24, freq="h")
        pv = pd.Series([1.0] * 24, index=index)
        household_load = pd.Series([0.2] * 24, index=index)
        thermal_config = {
            "sources": ["aerotermia", "geotermia", "electricitat_resistencia"],
            "annual_heat_demand_kwh": 500.0,
            "peak_power_kw": 2.0,
            "analysis_years": 20,
        }
        reference = calculate_thermal_source(500.0, "gas_natural", thermal_config)
        thermal_summary = {"payback_reference": "gas_natural", "sources": [reference]}
        battery = {
            "enabled": True,
            "capacity_kwh": 1.0,
            "max_charge_kw": 1.0,
            "max_discharge_kw": 1.0,
            "round_trip_efficiency": 0.9,
            "min_soc_pct": 10,
            "max_soc_pct": 100,
            "initial_soc_pct": 50,
        }
        economy = {
            "electricity_buy_price_eur_kwh": 0.25,
            "electricity_sell_price_eur_kwh": 0.08,
            "pv_cost_per_kw": 1000.0,
            "battery_cost_per_kwh": 500.0,
            "battery_cost_per_kw": 100.0,
            "installation_extra_pct": 0.1,
            "annual_om_pct": 0.01,
            "project_life_years": 3,
            "annual_inflation_pct": 0.0,
            "discount_rate_pct": 0.04,
        }
        lifecycle = {
            "panel_degradation_pct_per_year": 0.0,
            "panel_life_years": 25,
            "battery_life_years": 2,
            "inverter_life_years": 2,
            "inverter_cost_per_kw": 100.0,
        }

        results = evaluate_configuration_scenarios(
            pv,
            household_load,
            pd.Series([0.0] * 24),
            thermal_config,
            thermal_summary,
            battery,
            economy,
            lifecycle,
            current_pv_kwp=5.0,
        )

        self.assertEqual(len(results), 27)
        self.assertEqual({item["pv_peak_power_kwp"] for item in results}, {3.0, 5.0, 8.0})
        self.assertEqual({item["battery_capacity_kwh"] for item in results}, {0.0, 1.0, 2.0})
        self.assertEqual(
            {item["source_key"] for item in results},
            {"aerotermia", "geotermia", "electricitat_resistencia"},
        )
        self.assertTrue(all(0 <= item["self_consumption_rate_pct"] <= 100 for item in results))
        self.assertTrue(all(0 <= item["self_sufficiency_rate_pct"] <= 100 for item in results))
        self.assertTrue(all(results[index]["npv"] >= results[index + 1]["npv"] for index in range(len(results) - 1)))


if __name__ == "__main__":
    unittest.main()