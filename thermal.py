"""
Model simplificat de fonts per cobrir una demanda anual de calor i/o fred.

Els factors del cataleg son valors inicials orientatius i configurables. La
referencia del calcul es sempre l'energia util que necessita l'habitatge.
"""
from copy import deepcopy

import numpy as np
import pandas as pd

from battery import simulate_battery_series


THERMAL_SOURCES = {
    "gas_natural": {
        "name": "Gas natural",
        "category": "combustible",
        "efficiency": 0.92,
        "primary_energy_factor": 1.05,
        "nonrenewable_primary_share": 1.00,
        "direct_emission_factor_kg_co2_per_kwh": 0.202,
        "resource_price_eur_per_kwh": 0.085,
        "auxiliary_electricity_kwh_per_heat_kwh": 0.015,
        "fixed_annual_cost_eur": 120.0,
        "maintenance_annual_eur": 140.0,
        "capex_eur_per_kw": 450.0,
    },
    "gasoil": {
        "name": "Gasoil",
        "category": "combustible",
        "efficiency": 0.88,
        "primary_energy_factor": 1.08,
        "nonrenewable_primary_share": 1.00,
        "direct_emission_factor_kg_co2_per_kwh": 0.267,
        "resource_price_eur_per_kwh": 0.105,
        "auxiliary_electricity_kwh_per_heat_kwh": 0.012,
        "fixed_annual_cost_eur": 180.0,
        "maintenance_annual_eur": 220.0,
        "capex_eur_per_kw": 500.0,
    },
    "aerotermia": {
        "name": "Aerotermia",
        "category": "electricitat",
        "cop": 3.50,
        "primary_energy_factor": 1.95,
        "nonrenewable_primary_share": 0.55,
        "direct_emission_factor_kg_co2_per_kwh": 0.18,
        "resource_price_eur_per_kwh": 0.22,
        "auxiliary_electricity_kwh_per_heat_kwh": 0.0,
        "fixed_annual_cost_eur": 0.0,
        "maintenance_annual_eur": 180.0,
        "capex_eur_per_kw": 900.0,
    },
    "geotermia": {
        "name": "Geotermia",
        "category": "electricitat",
        "cop": 4.50,
        "primary_energy_factor": 1.95,
        "nonrenewable_primary_share": 0.55,
        "direct_emission_factor_kg_co2_per_kwh": 0.18,
        "resource_price_eur_per_kwh": 0.22,
        "auxiliary_electricity_kwh_per_heat_kwh": 0.0,
        "fixed_annual_cost_eur": 0.0,
        "maintenance_annual_eur": 220.0,
        "capex_eur_per_kw": 1500.0,
    },
    "biomassa": {
        "name": "Biomassa (pellet)",
        "category": "combustible",
        "efficiency": 1.07,
        "primary_energy_factor": 1.10,
        "nonrenewable_primary_share": 0.05,
        "direct_emission_factor_kg_co2_per_kwh": 0.041,
        "resource_price_eur_per_kwh": 0.070,
        "auxiliary_electricity_kwh_per_heat_kwh": 0.025,
        "fixed_annual_cost_eur": 100.0,
        "maintenance_annual_eur": 240.0,
        "capex_eur_per_kw": 700.0,
    },
    "electricitat_resistencia": {
        "name": "Electricitat (resistencia)",
        "category": "electricitat",
        "cop": 1.00,
        "primary_energy_factor": 1.95,
        "nonrenewable_primary_share": 0.55,
        "direct_emission_factor_kg_co2_per_kwh": 0.18,
        "resource_price_eur_per_kwh": 0.22,
        "auxiliary_electricity_kwh_per_heat_kwh": 0.0,
        "fixed_annual_cost_eur": 0.0,
        "maintenance_annual_eur": 40.0,
        "capex_eur_per_kw": 120.0,
    },
}


def available_sources():
    """Retorna una copia del cataleg per poder-lo modificar sense efectes globals."""
    return deepcopy(THERMAL_SOURCES)


def estimate_thermal_site_factors(location_config=None):
    """Calcula factors de rendiment i dimensionament segons clima i sòl."""
    location = location_config or {}
    climate = location.get("climate", {}) if isinstance(location, dict) else {}
    ground = location.get("ground", {}) if isinstance(location, dict) else {}

    mean_air_temp_c = float(climate.get("mean_annual_air_temp_c", 15.0))
    winter_design_temp_c = float(climate.get("winter_design_temp_c", 3.0))
    mean_ground_temp_c = float(ground.get("mean_ground_temp_c", mean_air_temp_c))
    thermal_conductivity = float(ground.get("thermal_conductivity_w_mk", 2.2))
    thermal_diffusivity = float(ground.get("thermal_diffusivity_m2_s", 1.0e-6))
    if thermal_diffusivity <= 0:
        thermal_diffusivity = 1.0e-6

    mildness_bonus = max(0.0, (mean_air_temp_c - 15.0) / 12.0)
    winter_penalty = max(0.0, (5.0 - winter_design_temp_c) / 9.0)
    air_source_cop_factor = 1.0 + 0.18 * mildness_bonus - 0.25 * winter_penalty
    air_source_cop_factor = float(np.clip(air_source_cop_factor, 0.82, 1.28))

    ground_source_cop_factor = 0.95 + 0.12 * max(0.0, (mean_ground_temp_c - 10.0) / 10.0)
    ground_source_cop_factor += 0.10 * max(0.0, (thermal_conductivity - 1.8) / 1.2)
    ground_source_cop_factor = float(np.clip(ground_source_cop_factor, 0.90, 1.25))

    borehole_depth_m = 150.0 - 35.0 * thermal_conductivity + (15.0 - mean_ground_temp_c) * 0.8
    borehole_depth_m = float(np.clip(borehole_depth_m, 55.0, 220.0))

    borehole_capex_factor = 1.25 - 0.22 * max(0.0, thermal_conductivity - 1.4)
    borehole_capex_factor = float(np.clip(borehole_capex_factor, 0.72, 1.20))

    return {
        "air_source_cop_factor": air_source_cop_factor,
        "ground_source_cop_factor": ground_source_cop_factor,
        "borehole_depth_m": borehole_depth_m,
        "borehole_capex_factor": borehole_capex_factor,
        "mean_air_temp_c": mean_air_temp_c,
        "mean_ground_temp_c": mean_ground_temp_c,
        "thermal_conductivity_w_mk": thermal_conductivity,
        "thermal_diffusivity_m2_s": thermal_diffusivity,
    }


def estimate_geothermal_design(heat_demand_kwh, peak_power_kw=None, location_config=None, thermal_config=None):
    """Calcula un dimensionament geotèrmic físic per al cas actual.

    Les dades geològiques del sòl poden obtenir-se del ICGC o d'un estudi geotècnic local.
    La demanda tèrmica pot venir d'un consum anual de calefacció/refrigeració o d'un
    model d'edifici; la càrrega tèrmica de pic s'ha d'estimar a partir de la demanda de
    disseny i de la temperatura de consigna. Aquesta funció és un model orientatiu però
    configurable perquè els valors es puguin ajustar cas per cas.
    """
    location = location_config or {}
    climate = location.get("climate", {}) if isinstance(location, dict) else {}
    ground = location.get("ground", {}) if isinstance(location, dict) else {}
    settings = thermal_config or {}

    indoor_setpoint_c = float(settings.get("heating_setpoint_c", settings.get("indoor_setpoint_c", 22.0)))
    ground_loop_target_c = float(settings.get("ground_loop_target_temp_c", settings.get("ground_loop_temp_c", 8.0)))
    borehole_diameter_m = float(settings.get("borehole_diameter_m", ground.get("borehole_diameter_m", 0.12)))
    groundwater_level_m = float(settings.get("groundwater_level_m", ground.get("groundwater_level_m", 5.0)))
    mean_ground_temp_c = float(ground.get("mean_ground_temp_c", climate.get("mean_annual_air_temp_c", 15.0)))
    thermal_conductivity = float(ground.get("thermal_conductivity_w_mk", 2.2))
    thermal_diffusivity = float(ground.get("thermal_diffusivity_m2_s", 1.1e-6))
    if thermal_diffusivity <= 0:
        thermal_diffusivity = 1.1e-6

    demand_kwh = float(heat_demand_kwh)
    design_peak_kw = float(peak_power_kw) if peak_power_kw is not None else max(demand_kwh / 2000.0, 3.0)
    delta_t_c = max(4.0, mean_ground_temp_c - ground_loop_target_c)
    # Estimació conservadora de flux tèrmic per metre de pou mostrant la relació
    # física entre conductivitat del terreny i capacitat de disipar calor.
    heat_flux_w_per_m = 20.0 + 18.0 * thermal_conductivity + 6.0 * max(0.0, delta_t_c - 5.0)
    required_length_m = design_peak_kw * 1000.0 / max(heat_flux_w_per_m, 15.0)
    required_length_m *= 1.25  # factor de seguretat per a càrregues puntuals i no idealitat del terreny

    borehole_depth_m = max(55.0, min(required_length_m / 1.5, 180.0))
    boreholes_count = max(1, int(np.ceil(required_length_m / max(borehole_depth_m, 80.0))))
    total_loop_length_m = boreholes_count * borehole_depth_m

    # Cost orientatiu per profunditat i terreny; s'ajusta amb la conductivitat i el nivell freàtic.
    drilling_cost_per_m = 58.0 + 18.0 / max(thermal_conductivity, 0.8) + max(0.0, (5.0 - groundwater_level_m)) * 3.0
    drilling_capex_eur = total_loop_length_m * drilling_cost_per_m * 1.18
    heat_pump_capex_per_kw = float(settings.get("capex_eur_per_kw", 1500.0))
    heat_pump_capex_eur = design_peak_kw * heat_pump_capex_per_kw
    capex_eur = drilling_capex_eur + heat_pump_capex_eur
    annualized_capex_eur = capex_eur / max(float(settings.get("analysis_years", 20.0)), 1.0)

    return {
        "source_key": "geotermia",
        "design_type": "Buit geotèrmic vertical",
        "case_name": location.get("name", "Ubicació no definida"),
        "indoor_setpoint_c": indoor_setpoint_c,
        "mean_ground_temp_c": mean_ground_temp_c,
        "ground_loop_target_temp_c": ground_loop_target_c,
        "delta_t_c": delta_t_c,
        "thermal_conductivity_w_mk": thermal_conductivity,
        "thermal_diffusivity_m2_s": thermal_diffusivity,
        "groundwater_level_m": groundwater_level_m,
        "borehole_diameter_m": borehole_diameter_m,
        "heat_flux_w_per_m": heat_flux_w_per_m,
        "required_length_m": required_length_m,
        "borehole_depth_m": borehole_depth_m,
        "boreholes_count": boreholes_count,
        "total_loop_length_m": total_loop_length_m,
        "design_peak_kw": design_peak_kw,
        "estimated_capex_eur": capex_eur,
        "estimated_drilling_capex_eur": drilling_capex_eur,
        "estimated_heat_pump_capex_eur": heat_pump_capex_eur,
        "annualized_capex_eur": annualized_capex_eur,
        "drilling_cost_per_m_eur": drilling_cost_per_m,
        "note": "Els paràmetres geològics (conductivitat, difusivitat, temperatura del sòl, nivell freàtic) poden extreure's del ICGC o d'un estudi geotècnic local i s'han d'ajustar cas per cas.",
    }


def _source_runtime_config(source_key, thermal_config=None):
    settings = thermal_config or {}
    if source_key not in THERMAL_SOURCES:
        raise KeyError(f"Font termica desconeguda: {source_key}")
    common_settings = {
        "peak_power_kw": settings.get("peak_power_kw", 8.0),
        "analysis_years": settings.get("analysis_years", 20),
        "location_config": settings.get("location_config") or settings.get("location") or settings.get("site"),
    }
    return {
        **common_settings,
        **settings.get("source_overrides", {}).get(source_key, {}),
    }


def hourly_thermal_electricity_profile(index, thermal_config):
    """Genera la demanda termica i electrica horaria de la font activa."""
    source_key = thermal_config.get("active_source")
    if not source_key:
        return pd.DataFrame(
            {"thermal_heat_demand_kwh": 0.0, "thermal_electricity_kwh": 0.0},
            index=index,
        )

    annual_demand = float(thermal_config.get("annual_heat_demand_kwh", 0.0))
    source_result = calculate_thermal_source(
        annual_demand,
        source_key,
        _source_runtime_config(source_key, thermal_config),
    )
    monthly_shape = {
        1: 1.70, 2: 1.50, 3: 1.20, 4: 0.80, 5: 0.40, 6: 0.20,
        7: 0.12, 8: 0.12, 9: 0.20, 10: 0.65, 11: 1.15, 12: 1.60,
    }
    hourly_shape = np.array([
        0.70, 0.65, 0.60, 0.58, 0.60, 0.70, 0.90, 1.05,
        0.95, 0.75, 0.60, 0.55, 0.55, 0.60, 0.65, 0.75,
        0.90, 1.10, 1.30, 1.40, 1.35, 1.15, 0.95, 0.80,
    ])
    weights = np.array([
        monthly_shape[timestamp.month] * hourly_shape[timestamp.hour]
        for timestamp in index
    ], dtype=float)
    heat_demand = weights / weights.sum() * annual_demand if weights.any() else weights
    electricity_ratio = (
        source_result["electricity_total_kwh"] / annual_demand
        if annual_demand and THERMAL_SOURCES[source_key].get("category") == "electricitat"
        else 0.0
    )
    return pd.DataFrame(
        {
            "thermal_heat_demand_kwh": heat_demand,
            "thermal_electricity_kwh": heat_demand * electricity_ratio,
        },
        index=index,
    )


def evaluate_electric_alternatives(pv_series, base_load_series, thermal_config, battery_config, economy_config):
    """Avalua fonts tèrmiques elèctriques aprofitant la FV i bateria existents."""
    results = []
    buy_price = float(economy_config.get("electricity_buy_price_eur_kwh", 0.0))
    sell_price = float(economy_config.get("electricity_sell_price_eur_kwh", 0.0))
    reference_household_electricity_cost = float(base_load_series.sum()) * buy_price
    sources = thermal_config.get("sources", list(THERMAL_SOURCES))
    for source_key in sources:
        if THERMAL_SOURCES[source_key].get("category") != "electricitat":
            continue
        source_settings = {**thermal_config, "active_source": source_key}
        thermal_profile = hourly_thermal_electricity_profile(pv_series.index, source_settings)
        load = base_load_series.reset_index(drop=True) + thermal_profile["thermal_electricity_kwh"].reset_index(drop=True)
        pv = pv_series.reset_index(drop=True)
        surplus = pv - load
        if battery_config.get("enabled", False):
            battery_result = simulate_battery_series(surplus, battery_config)
            grid_import = battery_result["grid_import_kwh"]
            grid_export = battery_result["grid_export_kwh"]
        else:
            grid_import = (-surplus).clip(lower=0)
            grid_export = surplus.clip(lower=0)

        source_result = calculate_thermal_source(
            thermal_config.get("annual_heat_demand_kwh", 0.0),
            source_key,
            _source_runtime_config(source_key, thermal_config),
        )
        grid_cost = float(grid_import.sum()) * buy_price
        export_revenue = float(grid_export.sum()) * sell_price
        fixed_and_maintenance = source_result["annual_total_cost_eur"] - source_result["resource_cost_eur"] - source_result["auxiliary_energy_cost_eur"]
        results.append({
            **source_result,
            "pv_load_kwh": float(load.sum()),
            "grid_import_kwh": float(grid_import.sum()),
            "grid_export_kwh": float(grid_export.sum()),
            "pv_self_consumed_kwh": float(pv.sum() - grid_export.sum()),
            "grid_energy_cost_eur": grid_cost,
            "pv_export_revenue_eur": export_revenue,
            "reference_household_electricity_cost_eur": reference_household_electricity_cost,
            "thermal_fixed_and_maintenance_eur": fixed_and_maintenance,
            "system_energy_cost_eur": grid_cost - export_revenue + fixed_and_maintenance,
        })
    return results


def _input_energy_kwh(heat_demand_kwh, source):
    performance = source.get("cop", source.get("efficiency"))
    if performance is None or performance <= 0:
        raise ValueError("La font ha de tenir un COP o un rendiment positiu")
    return heat_demand_kwh / performance


def calculate_thermal_source(heat_demand_kwh, source_key, source_config=None):
    """Calcula els indicadors anuals d'una font per una demanda termica util."""
    demand = float(heat_demand_kwh)
    if demand < 0:
        raise ValueError("La demanda termica no pot ser negativa")

    if source_key not in THERMAL_SOURCES and not source_config:
        raise KeyError(f"Font termica desconeguda: {source_key}")
    source = deepcopy(THERMAL_SOURCES.get(source_key, {}))
    source.update(source_config or {})

    site_factors = estimate_thermal_site_factors(
        source.get("location_config") or source.get("location") or source.get("site")
    )
    geothermal_design = None
    if source_key == "geotermia":
        geothermal_design = estimate_geothermal_design(
            demand,
            source.get("peak_power_kw", 0.0),
            source.get("location_config") or source.get("location") or source.get("site"),
            source,
        )

    base_performance = float(source.get("cop", source.get("efficiency", 1.0)))
    effective_performance = base_performance
    if source_key == "aerotermia":
        effective_performance *= float(site_factors.get("air_source_cop_factor", 1.0))
    elif source_key == "geotermia":
        effective_performance *= float(site_factors.get("ground_source_cop_factor", 1.0))

    capex_per_kw = float(source.get("capex_eur_per_kw", 0.0))

    input_energy = _input_energy_kwh(demand, {**source, "cop": effective_performance, "efficiency": effective_performance})
    auxiliary_electricity = demand * float(source.get("auxiliary_electricity_kwh_per_heat_kwh", 0.0))
    total_electricity = input_energy + auxiliary_electricity if source.get("category") == "electricitat" else auxiliary_electricity
    primary_total = (input_energy * float(source.get("primary_energy_factor", 1.0))) + auxiliary_electricity * float(source.get("auxiliary_primary_energy_factor", 1.95))
    nonrenewable_primary = (
        input_energy * float(source.get("primary_energy_factor", 1.0)) * float(source.get("nonrenewable_primary_share", 1.0))
        + auxiliary_electricity * float(source.get("auxiliary_primary_energy_factor", 1.95)) * float(source.get("auxiliary_nonrenewable_share", 0.55))
    )
    emissions = (
        input_energy * float(source.get("direct_emission_factor_kg_co2_per_kwh", 0.0))
        + auxiliary_electricity * float(source.get("auxiliary_emission_factor_kg_co2_per_kwh", 0.18))
    )
    resource_cost = input_energy * float(source.get("resource_price_eur_per_kwh", 0.0))
    auxiliary_cost = auxiliary_electricity * float(source.get("electricity_price_eur_per_kwh", source.get("resource_price_eur_per_kwh", 0.22)))
    annual_operating_cost = resource_cost + auxiliary_cost + float(source.get("fixed_annual_cost_eur", 0.0))
    maintenance = float(source.get("maintenance_annual_eur", 0.0))
    annual_total_cost = annual_operating_cost + maintenance

    peak_power = float(source.get("peak_power_kw", 0.0))
    if source_key == "geotermia" and geothermal_design:
        capex = geothermal_design["estimated_capex_eur"]
    else:
        capex = peak_power * capex_per_kw if peak_power else 0.0
    analysis_years = max(float(source.get("analysis_years", 20.0)), 1.0)
    annualized_capex = capex / analysis_years
    return {
        "source_key": source_key,
        "source_name": source.get("name", source_key),
        "category": source.get("category", "altres"),
        "heat_demand_kwh": demand,
        "performance": float(effective_performance),
        "input_energy_kwh": input_energy,
        "electricity_auxiliary_kwh": auxiliary_electricity,
        "electricity_total_kwh": total_electricity,
        "primary_energy_total_kwh": primary_total,
        "primary_energy_nonrenewable_kwh": nonrenewable_primary,
        "renewable_primary_kwh": max(primary_total - nonrenewable_primary, 0.0),
        "emissions_kg_co2e": emissions,
        "resource_cost_eur": resource_cost,
        "auxiliary_energy_cost_eur": auxiliary_cost,
        "operating_cost_eur": annual_operating_cost,
        "maintenance_cost_eur": maintenance,
        "annual_total_cost_eur": annual_total_cost,
        "capex_eur": capex,
        "annualized_capex_eur": annualized_capex,
        "annualized_total_cost_eur": annual_total_cost + annualized_capex,
        "total_first_year_cost_eur": annual_total_cost + capex,
        "cost_per_heat_kwh_eur": annual_total_cost / demand if demand else 0.0,
        "emissions_per_heat_kwh": emissions / demand if demand else 0.0,
        "nonrenewable_primary_per_heat_kwh": nonrenewable_primary / demand if demand else 0.0,
        "site_factors": site_factors,
        "borehole_depth_m": site_factors.get("borehole_depth_m"),
        "geothermal_design": geothermal_design,
    }


def compare_thermal_sources(heat_demand_kwh, thermal_config=None):
    """Compara fonts i genera rànquings de cost, emissions i energia primària."""
    settings = thermal_config or {}
    source_keys = settings.get("sources", list(THERMAL_SOURCES))
    source_overrides = settings.get("source_overrides", {})
    location_config = settings.get("location_config") or settings.get("location") or settings.get("site")
    common_settings = {
        "peak_power_kw": settings.get("peak_power_kw", 8.0),
        "analysis_years": settings.get("analysis_years", 20),
        "location_config": location_config,
    }
    effective_overrides = {}
    for key in source_keys:
        effective_overrides[key] = {**common_settings, **source_overrides.get(key, {})}
    results = [
        calculate_thermal_source(heat_demand_kwh, key, effective_overrides[key])
        for key in source_keys
    ]
    weights = settings.get("weights", {"cost": 0.34, "environment": 0.33, "energy": 0.33})
    reference_key = settings.get("payback_reference", source_keys[0] if source_keys else None)
    reference = next((item for item in results if item["source_key"] == reference_key), None)
    if reference:
        for result in results:
            annual_saving = reference["annual_total_cost_eur"] - result["annual_total_cost_eur"]
            additional_capex = result["capex_eur"] - reference["capex_eur"]
            if result["source_key"] == reference_key:
                payback = 0.0
            elif annual_saving > 0 and additional_capex > 0:
                payback = additional_capex / annual_saving
            elif annual_saving > 0 and additional_capex <= 0:
                payback = 0.0
            else:
                payback = None
            result["payback_years"] = payback
            result["annual_operating_saving_vs_reference_eur"] = annual_saving
            result["additional_capex_vs_reference_eur"] = additional_capex

    def rank(metric):
        return sorted(results, key=lambda item: item[metric])

    for index, result in enumerate(rank("annualized_total_cost_eur"), start=1):
        result["cost_rank"] = index
    for index, result in enumerate(rank("emissions_kg_co2e"), start=1):
        result["environment_rank"] = index
    for index, result in enumerate(rank("primary_energy_nonrenewable_kwh"), start=1):
        result["energy_rank"] = index

    max_cost = max((item["annualized_total_cost_eur"] for item in results), default=1.0)
    max_emissions = max((item["emissions_kg_co2e"] for item in results), default=1.0)
    max_energy = max((item["primary_energy_nonrenewable_kwh"] for item in results), default=1.0)
    for result in results:
        result["combined_score"] = (
            float(weights.get("cost", 0.0)) * result["annualized_total_cost_eur"] / max_cost
            + float(weights.get("environment", 0.0)) * result["emissions_kg_co2e"] / max_emissions
            + float(weights.get("energy", 0.0)) * result["primary_energy_nonrenewable_kwh"] / max_energy
        )
    results.sort(key=lambda item: item["combined_score"])
    preferred_results = [
        item for item in results if item["source_key"] != "electricitat_resistencia"
    ] or results
    geothermal_design = next(
        (item.get("geothermal_design") for item in results if item.get("source_key") == "geotermia" and item.get("geothermal_design")),
        None,
    )
    return {
        "heat_demand_kwh": float(heat_demand_kwh),
        "sources": results,
        "best_cost": min(preferred_results, key=lambda item: item["annualized_total_cost_eur"]) if preferred_results else None,
        "best_environment": min(results, key=lambda item: item["emissions_kg_co2e"]) if results else None,
        "best_energy": min(results, key=lambda item: item["primary_energy_nonrenewable_kwh"]) if results else None,
        "recommended": min(preferred_results, key=lambda item: item["combined_score"]) if preferred_results else None,
        "weights": weights,
        "payback_reference": reference_key,
        "analysis_years": common_settings["analysis_years"],
        "geothermal_design": geothermal_design,
    }
