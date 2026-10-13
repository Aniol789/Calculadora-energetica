"""
Funcions d'analisi agregada a partir de la serie horaria de la simulacio:
resums diaris i mensuals, perfil horari per estacio, i diagnostic de
dimensionament de la bateria (capacitat en kWh vs potencia en kW).
"""
import numpy as np
import pandas as pd
from battery import simulate_battery_series
from thermal import evaluate_electric_alternatives

SEASON_MONTHS = {
    "Hivern": [12, 1, 2],
    "Primavera": [3, 4, 5],
    "Estiu": [6, 7, 8],
    "Tardor": [9, 10, 11],
}
MONTH_TO_SEASON = {m: s for s, months in SEASON_MONTHS.items() for m in months}


def add_time_columns(df, start_year):
    idx = pd.date_range(f"{start_year}-01-01", periods=len(df), freq="h")
    df = df.copy()
    df["timestamp"] = idx
    df["hour"] = idx.hour
    df["day"] = idx.date
    df["month"] = idx.month
    df["weekday"] = idx.day_name()
    df["season"] = df["month"].map(MONTH_TO_SEASON)
    return df


def daily_summary(df):
    agg = {"pv_kwh": "sum", "load_kwh": "sum", "grid_export_kwh": "sum", "grid_import_kwh": "sum"}
    daily = df.groupby("day").agg(agg)
    daily["month"] = pd.to_datetime(pd.Series(daily.index)).dt.month.values

    if "battery_soc_pct" in df.columns:
        daily["soc_min_pct"] = df.groupby("day")["battery_soc_pct"].min()
        daily["soc_max_pct"] = df.groupby("day")["battery_soc_pct"].max()
        daily["soc_avg_pct"] = df.groupby("day")["battery_soc_pct"].mean()
    if "battery_full" in df.columns:
        daily["battery_saturated"] = df.groupby("day")["battery_full"].any()
        daily["battery_empty_day"] = df.groupby("day")["battery_empty"].any()
        daily["power_limited_charge"] = df.groupby("day")["limited_by_power_charge"].any()
        daily["power_limited_discharge"] = df.groupby("day")["limited_by_power_discharge"].any()

    daily["self_consumed_kwh"] = daily["pv_kwh"] - daily["grid_export_kwh"]
    daily["load_served_locally_kwh"] = (daily["load_kwh"] - daily["grid_import_kwh"]).clip(lower=0)
    daily["self_sufficiency_pct"] = np.where(
        daily["load_kwh"] > 0, daily["load_served_locally_kwh"] / daily["load_kwh"] * 100, 0.0
    )
    return daily


def monthly_summary(df):
    agg = {"pv_kwh": "sum", "load_kwh": "sum", "grid_export_kwh": "sum", "grid_import_kwh": "sum"}
    monthly = df.groupby("month").agg(agg)
    monthly["self_consumed_kwh"] = monthly["pv_kwh"] - monthly["grid_export_kwh"]
    monthly["load_served_locally_kwh"] = (monthly["load_kwh"] - monthly["grid_import_kwh"]).clip(lower=0)
    monthly["self_sufficiency_pct"] = np.where(
        monthly["load_kwh"] > 0, monthly["load_served_locally_kwh"] / monthly["load_kwh"] * 100, 0.0
    )
    monthly["self_consumption_pct"] = np.where(
        monthly["pv_kwh"] > 0, monthly["self_consumed_kwh"] / monthly["pv_kwh"] * 100, 0.0
    )
    return monthly


def hourly_profile_by_season(df):
    return df.groupby(["season", "hour"])[["pv_kwh", "load_kwh"]].mean().reset_index()


def compute_summary(df):
    total_pv = float(df["pv_kwh"].sum())
    total_load = float(df["load_kwh"].sum())
    total_export = float(df["grid_export_kwh"].sum())
    total_import = float(df["grid_import_kwh"].sum())
    self_consumed = total_pv - total_export
    load_served_locally = max(total_load - total_import, 0.0)
    return {
        "total_pv": total_pv,
        "total_load": total_load,
        "total_export": total_export,
        "total_import": total_import,
        "self_consumed": self_consumed,
        "load_served_locally": load_served_locally,
        "self_consumption_rate": (self_consumed / total_pv * 100) if total_pv else 0.0,
        "self_sufficiency_rate": (load_served_locally / total_load * 100) if total_load else 0.0,
    }


def compute_economic_summary(summary, pv_peak_kwp, battery_config, economic_config, lifecycle_config=None):
    pv_capex = float(pv_peak_kwp) * float(economic_config.get("pv_cost_per_kw", 0.0))
    battery_capex = 0.0
    battery_power_kw = 0.0
    if battery_config and battery_config.get("enabled", False):
        battery_capex += float(battery_config.get("capacity_kwh", 0.0)) * float(economic_config.get("battery_cost_per_kwh", 0.0))
        battery_power_kw = float(battery_config.get("max_discharge_kw", 0.0))
        battery_capex += battery_power_kw * float(economic_config.get("battery_cost_per_kw", 0.0))

    installation_extra = pv_capex * float(economic_config.get("installation_extra_pct", 0.0))
    capex_total = pv_capex + battery_capex + installation_extra

    buy_price = float(economic_config.get("electricity_buy_price_eur_kwh", 0.0))
    sell_price = float(economic_config.get("electricity_sell_price_eur_kwh", 0.0))

    annual_energy_saving = max(float(summary["total_load"]) - float(summary["total_import"]), 0.0) * buy_price
    annual_export_revenue = summary["total_export"] * sell_price
    annual_grid_cost = summary["total_import"] * buy_price
    # Estalvi respecte a comprar tota la càrrega de xarxa: energia local útil
    # més ingressos d'exportació. No es torna a restar la factura real.
    annual_bill_saving = annual_energy_saving + annual_export_revenue
    annual_om = capex_total * float(economic_config.get("annual_om_pct", 0.0))
    annual_cashflow = annual_bill_saving - annual_om

    degradation = 0.0
    battery_replacement_cost = 0.0
    inverter_replacement_cost = 0.0
    panel_life = 25
    battery_life = 10
    inverter_life = 12

    if lifecycle_config:
        degradation = float(lifecycle_config.get("panel_degradation_pct_per_year", 0.0))
        panel_life = int(lifecycle_config.get("panel_life_years", 25))
        battery_life = int(lifecycle_config.get("battery_life_years", 10))
        inverter_life = int(lifecycle_config.get("inverter_life_years", 12))
        if panel_life <= 0 or not 0 <= degradation < 1:
            raise ValueError("La vida útil dels panells ha de ser positiva i la degradació ha d'estar entre 0% i 100%")

        inverter_kw = max(float(pv_peak_kwp), 1.0)
        inverter_replacement_cost = inverter_kw * float(lifecycle_config.get("inverter_cost_per_kw", 0.0))

        if battery_config and battery_config.get("enabled", False):
            battery_replacement_cost = float(battery_config.get("capacity_kwh", 0.0)) * float(economic_config.get("battery_cost_per_kwh", 0.0))
            battery_replacement_cost += battery_power_kw * float(economic_config.get("battery_cost_per_kw", 0.0))

    payback_years = None
    if annual_cashflow > 0:
        payback_years = capex_total / annual_cashflow

    discount_rate = float(economic_config.get("discount_rate_pct", 0.0))
    project_life = int(economic_config.get("project_life_years", 25))
    inflation = float(economic_config.get("annual_inflation_pct", 0.0))
    if project_life <= 0:
        raise ValueError("La vida del projecte ha de ser d'almenys un any")
    if discount_rate <= -1 or inflation <= -1:
        raise ValueError("La taxa de descompte i la inflació han de ser superiors a -100%")

    lifecycle_replacements = []
    if lifecycle_config:
        if battery_life <= 0 or inverter_life <= 0:
            raise ValueError("La vida útil de la bateria i de l'inversor ha de ser positiva")
        for replacement_year in range(1, project_life + 1):
            if replacement_year % battery_life == 0 and battery_config and battery_config.get("enabled", False):
                lifecycle_replacements.append({"year": replacement_year, "type": "Bateria", "cost": battery_replacement_cost})
            if replacement_year % inverter_life == 0:
                lifecycle_replacements.append({"year": replacement_year, "type": "Inversor", "cost": inverter_replacement_cost})

    replacement_costs_by_year = {}
    for replacement in lifecycle_replacements:
        year = replacement["year"]
        replacement_costs_by_year[year] = replacement_costs_by_year.get(year, 0.0) + replacement["cost"]
    npv_25y = -capex_total
    for year in range(1, project_life + 1):
        annual_cashflow_year = annual_cashflow * ((1.0 + inflation) ** (year - 1))
        replacement_cost = replacement_costs_by_year.get(year, 0.0) * ((1.0 + inflation) ** (year - 1))
        npv_25y += (annual_cashflow_year - replacement_cost) / ((1.0 + discount_rate) ** year)

    lifecycle_impact = {
        "panel_degradation_pct_per_year": degradation,
        "panel_life_years": panel_life,
        "battery_life_years": battery_life,
        "inverter_life_years": inverter_life,
        "battery_replacement_cost": battery_replacement_cost,
        "inverter_replacement_cost": inverter_replacement_cost,
        "replacements": lifecycle_replacements,
    }

    annual_production_at_project_end = summary["total_pv"] * ((1.0 - degradation) ** (project_life - 1))

    return {
        "pv_capex": pv_capex,
        "pv_cost_per_kw": float(economic_config.get("pv_cost_per_kw", 0.0)),
        "battery_capex": battery_capex,
        "battery_cost_per_kwh": float(economic_config.get("battery_cost_per_kwh", 0.0)),
        "battery_cost_per_kw": float(economic_config.get("battery_cost_per_kw", 0.0)),
        "installation_extra": installation_extra,
        "capex_total": capex_total,
        "battery_power_kw": battery_power_kw,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "annual_energy_saving": annual_energy_saving,
        "annual_export_revenue": annual_export_revenue,
        "annual_grid_cost": annual_grid_cost,
        "annual_bill_saving": annual_bill_saving,
        "annual_om": annual_om,
        "annual_cashflow": annual_cashflow,
        "payback_years": payback_years,
        "npv": npv_25y,
        "npv_25y": npv_25y,
        "project_life_years": project_life,
        "panel_degradation_pct_per_year": degradation,
        "annual_production_end_of_project": annual_production_at_project_end,
        "annual_production_year_25": annual_production_at_project_end,
        "lifecycle_impact": lifecycle_impact,
    }


def compute_combined_economic_summary(thermal_summary, economic_summary, economic_config):
    """Compara el paquet FV + bateria + calefaccio electrica amb la referencia."""
    if not thermal_summary or not thermal_summary.get("sources"):
        return None

    reference_key = thermal_summary.get("payback_reference")
    reference = next(
        (item for item in thermal_summary["sources"] if item["source_key"] == reference_key),
        None,
    )
    alternatives = thermal_summary.get("electric_alternatives_with_pv", [])
    if not reference or not alternatives:
        return None

    project_life = int(economic_config.get("project_life_years", 25))
    discount_rate = float(economic_config.get("discount_rate_pct", 0.0))
    inflation = float(economic_config.get("annual_inflation_pct", 0.0))
    pv_battery_capex = float(economic_summary.get("capex_total", 0.0))
    annual_pv_om = float(economic_summary.get("annual_om", 0.0))
    reference_household_electricity_cost = float(
        alternatives[0].get("reference_household_electricity_cost_eur", 0.0)
    )
    replacements = economic_summary.get("lifecycle_impact", {}).get("replacements", [])
    replacement_costs_by_year = {}
    for replacement in replacements:
        replacement_year = int(replacement.get("year", 0))
        if 1 <= replacement_year <= project_life:
            replacement_costs_by_year[replacement_year] = (
                replacement_costs_by_year.get(replacement_year, 0.0)
                + float(replacement.get("cost", 0.0))
            )

    comparisons = []
    for alternative in alternatives:
        package_capex = pv_battery_capex + float(alternative.get("capex_eur", 0.0))
        reference_capex = float(reference.get("capex_eur", 0.0))
        incremental_capex = package_capex - reference_capex
        reference_annual_cost = (
            float(reference.get("annual_total_cost_eur", 0.0))
            + reference_household_electricity_cost
        )
        alternative_annual_cost = float(alternative.get("system_energy_cost_eur", 0.0)) + annual_pv_om
        annual_saving = reference_annual_cost - alternative_annual_cost
        payback = max(incremental_capex, 0.0) / annual_saving if annual_saving > 0 else None
        payback_within_horizon = payback is not None and payback <= project_life

        cumulative_saving = 0.0
        npv = -incremental_capex
        total_replacement_cost = 0.0
        for year in range(1, project_life + 1):
            inflation_factor = (1.0 + inflation) ** (year - 1)
            reference_cost_year = reference_annual_cost * inflation_factor
            lifecycle_costs = alternative.get("lifecycle_system_costs_eur")
            system_cost_year = (
                float(lifecycle_costs[year - 1])
                if lifecycle_costs and year <= len(lifecycle_costs)
                else float(alternative.get("system_energy_cost_eur", 0.0)) * inflation_factor
            )
            saving_year = reference_cost_year - system_cost_year - annual_pv_om * inflation_factor
            replacement_cost = replacement_costs_by_year.get(year, 0.0) * ((1.0 + inflation) ** (year - 1))
            cumulative_saving += saving_year
            total_replacement_cost += replacement_cost
            npv += (saving_year - replacement_cost) / ((1.0 + discount_rate) ** year)

        comparisons.append({
            "source_key": alternative["source_key"],
            "source_name": alternative["source_name"],
            "package_capex": package_capex,
            "reference_capex": reference_capex,
            "incremental_capex": incremental_capex,
            "reference_annual_cost": reference_annual_cost,
            "package_annual_cost": alternative_annual_cost,
            "annual_operating_cost_eur": alternative_annual_cost,
            "annual_saving": annual_saving,
            "cumulative_saving": cumulative_saving,
            "net_saving_over_life": cumulative_saving - incremental_capex - total_replacement_cost,
            "replacement_cost_over_life": total_replacement_cost,
            "pv_battery_capex": pv_battery_capex,
            "heating_capex": float(alternative.get("capex_eur", 0.0)),
            "geothermal_drilling_capex": float(
                (alternative.get("geothermal_design") or {}).get("estimated_drilling_capex_eur", 0.0)
            ),
            "geothermal_heat_pump_capex": float(
                (alternative.get("geothermal_design") or {}).get("estimated_heat_pump_capex_eur", 0.0)
            ),
            "npv": npv,
            "payback_years": payback,
            "payback_within_horizon": payback_within_horizon,
            "project_life_years": project_life,
            "grid_import_kwh": alternative.get("grid_import_kwh", 0.0),
            "grid_export_kwh": alternative.get("grid_export_kwh", 0.0),
            "self_consumption_rate_pct": alternative.get("self_consumption_rate_pct", 0.0),
            "self_sufficiency_rate_pct": alternative.get("self_sufficiency_rate_pct", 0.0),
            "input_energy_kwh": alternative.get("input_energy_kwh", 0.0),
            "emissions_kg_co2e": alternative.get("emissions_kg_co2e", 0.0),
            "primary_energy_nonrenewable_kwh": alternative.get("primary_energy_nonrenewable_kwh", 0.0),
        })

    return {
        "reference_name": reference["source_name"],
        "reference_key": reference["source_key"],
        "reference_household_electricity_cost_eur": reference_household_electricity_cost,
        "pv_battery_capex": pv_battery_capex,
        "pv_capex": float(economic_summary.get("pv_capex", 0.0)),
        "battery_capex": float(economic_summary.get("battery_capex", 0.0)),
        "installation_extra": float(economic_summary.get("installation_extra", 0.0)),
        "annual_pv_om": annual_pv_om,
        "project_life_years": project_life,
        "source_details": [
            {
                "source_key": item["source_key"],
                "input_energy_kwh": item.get("input_energy_kwh", 0.0),
            }
            for item in thermal_summary["sources"]
        ],
        "comparisons": comparisons,
    }


def evaluate_configuration_scenarios(
    pv_series,
    base_load_series,
    active_thermal_electricity_series,
    thermal_config,
    thermal_summary,
    battery_config,
    economic_config,
    lifecycle_config,
    current_pv_kwp,
    outdoor_temp_series=None,
):
    """Compara combinacions candidates de potència FV i capacitat de bateria."""
    if not thermal_summary or not thermal_summary.get("sources"):
        return []
    if float(current_pv_kwp) <= 0:
        raise ValueError("La potència FV de referència ha de ser positiva")

    pv_values = sorted({round(float(current_pv_kwp) * factor, 2) for factor in (0.6, 1.0, 1.6)})
    reference_battery_capacity = float(battery_config.get("capacity_kwh", 0.0))
    battery_step = reference_battery_capacity if reference_battery_capacity > 0 else 3.0
    battery_values = sorted({0.0, round(battery_step, 2), round(battery_step * 2, 2)})
    base_load = base_load_series.reset_index(drop=True).astype(float)
    active_thermal_load = active_thermal_electricity_series.reset_index(drop=True).astype(float)
    if len(pv_series) != len(base_load) or len(base_load) != len(active_thermal_load):
        raise ValueError("Els perfils FV, domèstic i tèrmic han de tenir la mateixa durada")

    results = []
    for pv_kwp in pv_values:
        scenario_pv = pv_series.astype(float) * (pv_kwp / float(current_pv_kwp))
        for capacity_kwh in battery_values:
            scenario_battery = dict(battery_config)
            scenario_battery["enabled"] = capacity_kwh > 0
            scenario_battery["capacity_kwh"] = capacity_kwh
            if reference_battery_capacity > 0:
                power_factor = capacity_kwh / reference_battery_capacity
                scenario_battery["max_charge_kw"] = float(battery_config.get("max_charge_kw", 0.0)) * power_factor
                scenario_battery["max_discharge_kw"] = float(battery_config.get("max_discharge_kw", 0.0)) * power_factor
            else:
                scenario_battery["max_charge_kw"] = capacity_kwh
                scenario_battery["max_discharge_kw"] = capacity_kwh

            scenario_load = base_load + active_thermal_load
            surplus = scenario_pv.reset_index(drop=True) - scenario_load
            if scenario_battery["enabled"]:
                battery_result = simulate_battery_series(surplus, scenario_battery)
                grid_import = battery_result["grid_import_kwh"]
                grid_export = battery_result["grid_export_kwh"]
            else:
                grid_import = (-surplus).clip(lower=0)
                grid_export = surplus.clip(lower=0)
            scenario_summary = compute_summary(pd.DataFrame({
                "pv_kwh": scenario_pv.reset_index(drop=True),
                "load_kwh": scenario_load,
                "grid_import_kwh": grid_import,
                "grid_export_kwh": grid_export,
            }))
            system_economics = compute_economic_summary(
                scenario_summary,
                pv_kwp,
                scenario_battery,
                economic_config,
                lifecycle_config,
            )
            alternatives = evaluate_electric_alternatives(
                scenario_pv,
                base_load_series,
                thermal_config,
                scenario_battery,
                economic_config,
                lifecycle_config,
                outdoor_temp_series,
            )
            scenario_thermal_summary = {
                **thermal_summary,
                "electric_alternatives_with_pv": alternatives,
            }
            combined = compute_combined_economic_summary(
                scenario_thermal_summary,
                system_economics,
                economic_config,
            )
            if combined:
                for comparison in combined["comparisons"]:
                    comparison["pv_peak_power_kwp"] = pv_kwp
                    comparison["battery_capacity_kwh"] = capacity_kwh
                    comparison["is_current_configuration"] = bool(
                        np.isclose(pv_kwp, current_pv_kwp)
                        and np.isclose(
                            capacity_kwh,
                            reference_battery_capacity if battery_config.get("enabled", False) else 0.0,
                        )
                    )
                results.extend(combined["comparisons"])

    return sorted(results, key=lambda item: item["npv"], reverse=True)


def compute_lifecycle_environmental_summary(
    summary, pv_peak_kwp, battery_config, lifecycle_config, hourly_df=None, lifecycle_projection=None
):
    if not lifecycle_config:
        return {
            "embodied_co2_kg": 0.0,
            "co2_saved_kg_over_life": 0.0,
            "avoided_co2_per_year_kg": 0.0,
            "net_co2_kg": 0.0,
            "panel_life_years": 0,
        }

    pv_embodied = float(pv_peak_kwp) * float(lifecycle_config.get("pv_embodied_co2_kg_per_kwp", 0.0))
    battery_embodied = 0.0
    if battery_config and battery_config.get("enabled", False):
        battery_embodied = float(battery_config.get("capacity_kwh", 0.0)) * float(lifecycle_config.get("battery_embodied_co2_kg_per_kwh", 0.0))
    inverter_kw = max(float(pv_peak_kwp), 1.0)
    inverter_embodied = inverter_kw * float(lifecycle_config.get("inverter_embodied_co2_kg_per_kw", 0.0))

    embodied_co2 = pv_embodied + battery_embodied + inverter_embodied
    annual_displaced_grid_kwh = (
        float(summary.get("load_served_locally", 0.0)) + float(summary.get("total_export", 0.0))
    )
    grid_factor = float(lifecycle_config.get("grid_emission_factor_kg_co2_per_kwh", 0.0))
    avoided_co2_per_year = annual_displaced_grid_kwh * grid_factor
    life_years = int(lifecycle_config.get("panel_life_years", 25))
    degradation = float(lifecycle_config.get("panel_degradation_pct_per_year", 0.0))
    if life_years <= 0 or not 0 <= degradation < 1:
        raise ValueError("La vida útil dels panells ha de ser positiva i la degradació ha d'estar entre 0% i 100%")
    co2_saved_over_life = 0.0
    projected_co2 = (lifecycle_projection or {}).get("avoided_co2_kg", [])
    for year in range(1, life_years + 1):
        if year <= len(projected_co2):
            co2_saved_over_life += projected_co2[year - 1]
        else:
            energy_flows = _year_energy_flows(
                summary, (1.0 - degradation) ** (year - 1), hourly_df, battery_config
            )
            displaced_grid_kwh = energy_flows["load_served_locally"] + energy_flows["grid_export"]
            co2_saved_over_life += displaced_grid_kwh * grid_factor

    net_co2 = embodied_co2 - co2_saved_over_life
    return {
        "embodied_co2_kg": embodied_co2,
        "co2_saved_kg_over_life": co2_saved_over_life,
        "avoided_co2_per_year_kg": avoided_co2_per_year,
        "net_co2_kg": net_co2,
        "panel_life_years": life_years,
    }


def compute_lifecycle_projection(summary, pv_peak_kwp, battery_config, economic_config, lifecycle_config, hourly_df=None):
    if not lifecycle_config:
        return {
            "years": [],
            "annual_production_kwh": [],
            "annual_self_consumed_kwh": [],
            "annual_export_kwh": [],
            "annual_import_kwh": [],
            "annual_bill_saving_eur": [],
            "annual_cashflow_eur": [],
            "cumulative_cashflow_eur": [],
            "avoided_co2_kg": [],
        }

    project_life = int(economic_config.get("project_life_years", 25))
    degradation = float(lifecycle_config.get("panel_degradation_pct_per_year", 0.0))
    buy_price = float(economic_config.get("electricity_buy_price_eur_kwh", 0.0))
    sell_price = float(economic_config.get("electricity_sell_price_eur_kwh", 0.0))
    annual_om_pct = float(economic_config.get("annual_om_pct", 0.0))
    grid_factor = float(lifecycle_config.get("grid_emission_factor_kg_co2_per_kwh", 0.0))
    inflation = float(economic_config.get("annual_inflation_pct", 0.0))
    if project_life <= 0:
        raise ValueError("La vida del projecte ha de ser d'almenys un any")
    if not 0 <= degradation < 1:
        raise ValueError("La degradació anual dels panells ha d'estar entre 0% i 100%")
    discount_rate = float(economic_config.get("discount_rate_pct", 0.0))
    if discount_rate <= -1 or inflation <= -1:
        raise ValueError("La taxa de descompte i la inflació han de ser superiors a -100%")

    pv_capex = float(pv_peak_kwp) * float(economic_config.get("pv_cost_per_kw", 0.0))
    battery_capex = 0.0
    battery_power_kw = 0.0
    if battery_config and battery_config.get("enabled", False):
        battery_capex += float(battery_config.get("capacity_kwh", 0.0)) * float(economic_config.get("battery_cost_per_kwh", 0.0))
        battery_power_kw = float(battery_config.get("max_discharge_kw", 0.0))
        battery_capex += battery_power_kw * float(economic_config.get("battery_cost_per_kw", 0.0))
    installation_extra = pv_capex * float(economic_config.get("installation_extra_pct", 0.0))
    capex_total = pv_capex + battery_capex + installation_extra

    battery_life = int(lifecycle_config.get("battery_life_years", 10))
    inverter_life = int(lifecycle_config.get("inverter_life_years", 12))
    if battery_life <= 0 or inverter_life <= 0:
        raise ValueError("La vida útil de la bateria i de l'inversor ha de ser positiva")
    inverter_cost = max(float(pv_peak_kwp), 1.0) * float(lifecycle_config.get("inverter_cost_per_kw", 0.0))
    battery_replacement_cost = 0.0
    if battery_config and battery_config.get("enabled", False):
        battery_replacement_cost = float(battery_config.get("capacity_kwh", 0.0)) * float(economic_config.get("battery_cost_per_kwh", 0.0))
        battery_replacement_cost += battery_power_kw * float(economic_config.get("battery_cost_per_kw", 0.0))

    years = list(range(1, project_life + 1))
    annual_production = []
    annual_self_consumed = []
    annual_export = []
    annual_import = []
    annual_bill_saving = []
    annual_cashflow = []
    cumulative_cashflow = [-capex_total]
    avoided_co2 = []

    running_cash = -capex_total
    for year in years:
        energy_flows = _year_energy_flows(
            summary, (1.0 - degradation) ** (year - 1), hourly_df, battery_config
        )
        production = energy_flows["production"]
        self_consumed = energy_flows["self_consumed"]
        export = energy_flows["grid_export"]
        import_kwh = energy_flows["grid_import"]
        inflation_factor = (1.0 + inflation) ** (year - 1)
        annual_saving = (
            energy_flows["load_served_locally"] * buy_price + export * sell_price
        ) * inflation_factor
        annual_om = capex_total * annual_om_pct * inflation_factor
        replacement = 0.0
        if battery_config and battery_config.get("enabled", False) and year % battery_life == 0:
            replacement += battery_replacement_cost * inflation_factor
        if year % inverter_life == 0:
            replacement += inverter_cost * inflation_factor

        bill_saving = annual_saving
        cashflow_year = bill_saving - annual_om - replacement
        running_cash += cashflow_year

        annual_production.append(production)
        annual_self_consumed.append(self_consumed)
        annual_export.append(export)
        annual_import.append(import_kwh)
        annual_bill_saving.append(bill_saving)
        annual_cashflow.append(cashflow_year)
        cumulative_cashflow.append(running_cash)
        avoided_co2.append((energy_flows["load_served_locally"] + export) * grid_factor)

    return {
        "years": years,
        "annual_production_kwh": annual_production,
        "annual_self_consumed_kwh": annual_self_consumed,
        "annual_export_kwh": annual_export,
        "annual_import_kwh": annual_import,
        "annual_bill_saving_eur": annual_bill_saving,
        "annual_cashflow_eur": annual_cashflow,
        "cumulative_cashflow_eur": cumulative_cashflow,
        "avoided_co2_kg": avoided_co2,
        "capex_total": capex_total,
        "project_life_years": project_life,
        "cashflow_years": [0] + years,
        "npv": -capex_total + sum(
            cashflow / ((1.0 + discount_rate) ** year)
            for year, cashflow in zip(years, annual_cashflow)
        ),
    }


def _year_energy_flows(summary, production_factor, hourly_df=None, battery_config=None):
    """Recalcula l'any amb la sèrie horària; usa una aproximació només si no es disposa de la sèrie."""
    if hourly_df is None:
        return _project_energy_flows(summary, production_factor)

    pv = hourly_df["pv_kwh"].astype(float) * production_factor
    load = hourly_df["load_kwh"].astype(float)
    surplus = pv - load
    if battery_config and battery_config.get("enabled", False):
        battery = simulate_battery_series(surplus, battery_config)
        grid_import = battery["grid_import_kwh"]
        grid_export = battery["grid_export_kwh"]
    else:
        grid_import = (-surplus).clip(lower=0)
        grid_export = surplus.clip(lower=0)

    total_load = float(load.sum())
    total_import = float(grid_import.sum())
    total_pv = float(pv.sum())
    total_export = float(grid_export.sum())
    return {
        "production": total_pv,
        "self_consumed": total_pv - total_export,
        "grid_export": total_export,
        "grid_import": total_import,
        "load_served_locally": max(total_load - total_import, 0.0),
    }


def _project_energy_flows(summary, production_factor):
    """Aproxima els fluxos futurs reduint primer l'excedent exportat i després l'energia útil local."""
    base_production = max(float(summary.get("total_pv", 0.0)), 0.0)
    total_load = max(float(summary.get("total_load", 0.0)), 0.0)
    base_export = max(float(summary.get("total_export", 0.0)), 0.0)
    base_import = max(float(summary.get("total_import", 0.0)), 0.0)
    base_self_consumed = max(float(summary.get("self_consumed", base_production - base_export)), 0.0)
    factor = max(float(production_factor), 0.0)
    production = base_production * factor
    production_loss = max(base_production - production, 0.0)
    lost_export = min(production_loss, base_export)
    grid_export = max(base_export - lost_export, 0.0)
    self_consumed = max(base_self_consumed - max(production_loss - base_export, 0.0), 0.0)
    import_increase = max(production_loss - base_export, 0.0)
    grid_import = min(total_load, base_import + import_increase)
    load_served_locally = max(total_load - grid_import, 0.0)
    return {
        "production": production,
        "self_consumed": self_consumed,
        "grid_export": grid_export,
        "grid_import": grid_import,
        "load_served_locally": load_served_locally,
    }


def battery_sizing_diagnostics(df, daily, battery_config):
    """
    Analitza si la bateria esta ben dimensionada, distingint entre
    problemes de CAPACITAT (kWh, es satura o es buida) i problemes de
    POTENCIA (kW, no dona prou rapid a l'hora de carregar/descarregar
    encara que li quedi marge de capacitat).
    """
    if "battery_full" not in df.columns:
        return None

    n_days = daily.shape[0]
    n_saturated_days = int(daily["battery_saturated"].sum())
    n_empty_days = int(daily["battery_empty_day"].sum())
    n_power_charge_days = int(daily["power_limited_charge"].sum())
    n_power_discharge_days = int(daily["power_limited_discharge"].sum())

    charge_kwh = np.where(df["surplus_kwh"] >= 0, df["surplus_kwh"] - df["grid_export_kwh"], 0.0)
    discharge_kwh = np.where(df["surplus_kwh"] < 0, -df["surplus_kwh"] - df["grid_import_kwh"], 0.0)
    total_charged = float(np.sum(charge_kwh))
    total_discharged = float(np.sum(discharge_kwh))
    capacity = battery_config["capacity_kwh"]
    equivalent_cycles = (total_discharged / capacity) if capacity else 0.0

    energy_lost_full = float(df.loc[df["battery_full"], "grid_export_kwh"].sum())
    energy_lost_power_charge = float(df.loc[df["limited_by_power_charge"], "grid_export_kwh"].sum())
    energy_unmet_empty = float(df.loc[df["battery_empty"], "grid_import_kwh"].sum())
    energy_unmet_power_discharge = float(df.loc[df["limited_by_power_discharge"], "grid_import_kwh"].sum())

    pct_saturated = (n_saturated_days / n_days * 100) if n_days else 0.0
    pct_empty = (n_empty_days / n_days * 100) if n_days else 0.0

    recs = []
    if pct_saturated > 15 and energy_lost_full > max(0.02 * total_charged, 1):
        recs.append(
            f"La bateria arriba al 100% en el {pct_saturated:.0f}% dels dies de l'any, "
            f"perdent uns {energy_lost_full:.0f} kWh d'excedent que no es poden emmagatzemar. "
            f"Valora augmentar la CAPACITAT (kWh) de la bateria."
        )
    if n_power_charge_days > 0.1 * n_days:
        recs.append(
            f"En {n_power_charge_days} dies hi ha excedent disponible pero la potencia de "
            f"carrega actual ({battery_config['max_charge_kw']} kW) limita quant se n'aprofita "
            f"(uns {energy_lost_power_charge:.0f} kWh anuals). Valora mes POTENCIA de carrega (kW), "
            f"no nomes mes capacitat."
        )
    if pct_empty > 15:
        recs.append(
            f"La bateria es buida en el {pct_empty:.0f}% dels dies, deixant uns "
            f"{energy_unmet_empty:.0f} kWh sense cobrir que s'acaben important de la xarxa. "
            f"Valora augmentar la CAPACITAT, o revisar si la potencia FV instal.lada es suficient."
        )
    if n_power_discharge_days > 0.1 * n_days:
        recs.append(
            f"En {n_power_discharge_days} dies la potencia de descarrega actual "
            f"({battery_config['max_discharge_kw']} kW) es insuficient per cobrir puntes de "
            f"consum encara que quedi energia emmagatzemada (uns {energy_unmet_power_discharge:.0f} kWh "
            f"anuals). Valora mes POTENCIA de descarrega (kW)."
        )
    if not recs:
        recs.append(
            "La bateria sembla raonablement ben dimensionada per aquest cas: no es satura ni "
            "es buida de manera sistematica al llarg de l'any."
        )

    return {
        "n_days": n_days,
        "max_soc_pct": float(battery_config.get("max_soc_pct", 100.0)),
        "n_saturated_days": n_saturated_days,
        "n_empty_days": n_empty_days,
        "n_power_charge_days": n_power_charge_days,
        "n_power_discharge_days": n_power_discharge_days,
        "equivalent_cycles": equivalent_cycles,
        "energy_lost_full": energy_lost_full,
        "energy_lost_power_charge": energy_lost_power_charge,
        "energy_unmet_empty": energy_unmet_empty,
        "energy_unmet_power_discharge": energy_unmet_power_discharge,
        "recommendation": " ".join(recs),
    }
