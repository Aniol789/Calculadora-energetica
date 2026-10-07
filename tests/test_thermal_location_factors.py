import unittest

from thermal import calculate_thermal_source, estimate_thermal_site_factors, estimate_geothermal_design


class ThermalLocationFactorsTests(unittest.TestCase):
    def test_site_factors_are_location_sensitive(self):
        mild_site = {
            "climate": {"mean_annual_air_temp_c": 17.0, "winter_design_temp_c": 4.0},
            "ground": {"thermal_conductivity_w_mk": 2.8, "mean_ground_temp_c": 15.0},
        }
        factors = estimate_thermal_site_factors(mild_site)
        self.assertGreater(factors["air_source_cop_factor"], 1.0)
        self.assertLess(factors["borehole_depth_m"], 140.0)
        self.assertLess(factors["borehole_capex_factor"], 1.0)

    def test_aerothermal_performance_changes_with_site(self):
        mild_site = {
            "climate": {"mean_annual_air_temp_c": 17.0, "winter_design_temp_c": 4.0},
            "ground": {"thermal_conductivity_w_mk": 2.8, "mean_ground_temp_c": 15.0},
        }
        mild = calculate_thermal_source(5000.0, "aerotermia", {"peak_power_kw": 8.0, "location_config": mild_site})
        cold = calculate_thermal_source(5000.0, "aerotermia", {"peak_power_kw": 8.0, "location_config": {"climate": {"mean_annual_air_temp_c": 8.0, "winter_design_temp_c": -4.0}, "ground": {"thermal_conductivity_w_mk": 1.4, "mean_ground_temp_c": 9.0}}})
        self.assertGreater(mild["performance"], cold["performance"])

    def test_geothermal_design_uses_case_parameters(self):
        site = {
            "name": "Cas test",
            "climate": {"mean_annual_air_temp_c": 15.0, "winter_design_temp_c": 3.0},
            "ground": {"mean_ground_temp_c": 13.0, "thermal_conductivity_w_mk": 2.8, "thermal_diffusivity_m2_s": 1.1e-6, "groundwater_level_m": 5.0},
        }
        design = estimate_geothermal_design(10000.0, 8.0, site, {"heating_setpoint_c": 22.0, "ground_loop_target_temp_c": 8.0})
        self.assertGreater(design["required_length_m"], 0)
        self.assertGreater(design["boreholes_count"], 0)
        self.assertGreater(design["estimated_capex_eur"], 0)


if __name__ == "__main__":
    unittest.main()
