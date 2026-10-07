"""
Funcions d'analisi agregada a partir de la serie horaria de la simulacio:
resums diaris i mensuals, perfil horari per estacio, i diagnostic de
dimensionament de la bateria (capacitat en kWh vs potencia en kW).
"""
import numpy as np
import pandas as pd

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
    daily["self_sufficiency_pct"] = np.where(
        daily["load_kwh"] > 0, daily["self_consumed_kwh"] / daily["load_kwh"] * 100, 0.0
    )
    return daily


def monthly_summary(df):
    agg = {"pv_kwh": "sum", "load_kwh": "sum", "grid_export_kwh": "sum", "grid_import_kwh": "sum"}
    monthly = df.groupby("month").agg(agg)
    monthly["self_consumed_kwh"] = monthly["pv_kwh"] - monthly["grid_export_kwh"]
    monthly["self_sufficiency_pct"] = np.where(
        monthly["load_kwh"] > 0, monthly["self_consumed_kwh"] / monthly["load_kwh"] * 100, 0.0
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
    return {
        "total_pv": total_pv,
        "total_load": total_load,
        "total_export": total_export,
        "total_import": total_import,
        "self_consumed": self_consumed,
        "self_consumption_rate": (self_consumed / total_pv * 100) if total_pv else 0.0,
        "self_sufficiency_rate": (self_consumed / total_load * 100) if total_load else 0.0,
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

    annual_energy_saving = summary["self_consumed"] * buy_price
    annual_export_revenue = summary["total_export"] * sell_price
    annual_grid_cost = summary["total_import"] * buy_price
    annual_bill_saving = annual_energy_saving + annual_export_revenue - annual_grid_cost
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
    future_cashflow = annual_cashflow
    npv_25y = 0.0
    for year in range(1, project_life + 1):
        future_cashflow = annual_cashflow * ((1.0 + inflation) ** (year - 1))
        npv_25y += future_cashflow / ((1.0 + discount_rate) ** year)
    npv_25y -= capex_total

    lifecycle_replacements = []
    if lifecycle_config:
        for replacement_year in range(1, project_life + 1):
            if replacement_year % battery_life == 0 and battery_config and battery_config.get("enabled", False):
                lifecycle_replacements.append({"year": replacement_year, "type": "Bateria", "cost": battery_replacement_cost})
            if replacement_year % inverter_life == 0:
                lifecycle_replacements.append({"year": replacement_year, "type": "Inversor", "cost": inverter_replacement_cost})

    lifecycle_impact = {
        "panel_degradation_pct_per_year": degradation,
        "panel_life_years": panel_life,
        "battery_life_years": battery_life,
        "inverter_life_years": inverter_life,
        "battery_replacement_cost": battery_replacement_cost,
        "inverter_replacement_cost": inverter_replacement_cost,
        "replacements": lifecycle_replacements,
    }

    annual_production_with_degradation = summary["total_pv"]
    if lifecycle_config:
        annual_production_with_degradation = summary["total_pv"] * ((1.0 - degradation) ** (panel_life - 1))

    return {
        "pv_capex": pv_capex,
        "battery_capex": battery_capex,
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
        "npv_25y": npv_25y,
        "panel_degradation_pct_per_year": degradation,
        "annual_production_year_25": annual_production_with_degradation,
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
        payback = incremental_capex / annual_saving if incremental_capex > 0 and annual_saving > 0 else None

        cumulative_saving = 0.0
        npv = -incremental_capex
        total_replacement_cost = 0.0
        for year in range(1, project_life + 1):
            saving_year = annual_saving * ((1.0 + inflation) ** (year - 1))
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
            "grid_import_kwh": alternative.get("grid_import_kwh", 0.0),
            "grid_export_kwh": alternative.get("grid_export_kwh", 0.0),
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


def compute_lifecycle_environmental_summary(summary, pv_peak_kwp, battery_config, lifecycle_config):
    if not lifecycle_config:
        return {
            "embodied_co2_kg": 0.0,
            "co2_saved_kg_over_life": 0.0,
            "avoided_co2_per_year_kg": 0.0,
            "net_co2_kg": 0.0,
        }

    pv_embodied = float(pv_peak_kwp) * float(lifecycle_config.get("pv_embodied_co2_kg_per_kwp", 0.0))
    battery_embodied = 0.0
    if battery_config and battery_config.get("enabled", False):
        battery_embodied = float(battery_config.get("capacity_kwh", 0.0)) * float(lifecycle_config.get("battery_embodied_co2_kg_per_kwh", 0.0))
    inverter_kw = max(float(pv_peak_kwp), 1.0)
    inverter_embodied = inverter_kw * float(lifecycle_config.get("inverter_embodied_co2_kg_per_kw", 0.0))

    embodied_co2 = pv_embodied + battery_embodied + inverter_embodied
    annual_self_consumed_kwh = float(summary.get("self_consumed", 0.0))
    grid_factor = float(lifecycle_config.get("grid_emission_factor_kg_co2_per_kwh", 0.0))
    avoided_co2_per_year = annual_self_consumed_kwh * grid_factor
    life_years = int(lifecycle_config.get("panel_life_years", 25))
    degradation = float(lifecycle_config.get("panel_degradation_pct_per_year", 0.0))
    co2_saved_over_life = 0.0
    for year in range(1, life_years + 1):
        effective_self_consumed = annual_self_consumed_kwh * ((1.0 - degradation) ** (year - 1))
        co2_saved_over_life += effective_self_consumed * grid_factor

    net_co2 = embodied_co2 - co2_saved_over_life
    return {
        "embodied_co2_kg": embodied_co2,
        "co2_saved_kg_over_life": co2_saved_over_life,
        "avoided_co2_per_year_kg": avoided_co2_per_year,
        "net_co2_kg": net_co2,
    }


def compute_lifecycle_projection(summary, pv_peak_kwp, battery_config, economic_config, lifecycle_config):
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
    inverter_cost = max(float(pv_peak_kwp), 1.0) * float(lifecycle_config.get("inverter_cost_per_kw", 0.0))
    battery_replacement_cost = 0.0
    if battery_config and battery_config.get("enabled", False):
        battery_replacement_cost = float(battery_config.get("capacity_kwh", 0.0)) * float(economic_config.get("battery_cost_per_kwh", 0.0))
        battery_replacement_cost += battery_power_kw * float(economic_config.get("battery_cost_per_kw", 0.0))

    base_production = float(summary.get("total_pv", 0.0))
    base_self_consumed = float(summary.get("self_consumed", 0.0))
    base_export = float(summary.get("total_export", 0.0))
    base_import = float(summary.get("total_import", 0.0))

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
        production = base_production * ((1.0 - degradation) ** (year - 1))
        self_consumed = base_self_consumed * ((1.0 - degradation) ** (year - 1))
        export = base_export * ((1.0 - degradation) ** (year - 1))
        if base_self_consumed > 0:
            import_ratio = max(1.0 - (self_consumed / base_self_consumed), 0.0)
        else:
            import_ratio = 0.0
        import_kwh = max(base_import * (1.0 + import_ratio), 0.0)
        annual_om = capex_total * annual_om_pct
        replacement = 0.0
        if battery_config and battery_config.get("enabled", False) and year % battery_life == 0:
            replacement += battery_replacement_cost
        if year % inverter_life == 0:
            replacement += inverter_cost

        bill_saving = self_consumed * buy_price + export * sell_price - import_kwh * buy_price
        cashflow_year = bill_saving - annual_om - replacement
        running_cash += cashflow_year

        annual_production.append(production)
        annual_self_consumed.append(self_consumed)
        annual_export.append(export)
        annual_import.append(import_kwh)
        annual_bill_saving.append(bill_saving)
        annual_cashflow.append(cashflow_year)
        cumulative_cashflow.append(running_cash)
        avoided_co2.append(production * grid_factor)

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
