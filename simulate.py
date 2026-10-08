"""
Script principal: simula la produccio, el consum i (opcionalment) la
bateria d'una instal.lacio fotovoltaica durant un any complet, genera
resums diaris/mensuals, un diagnostic de dimensionament de la bateria,
i un informe HTML interactiu.

Us:
    python simulate.py
"""
import os
import re
import shutil
import unicodedata
from datetime import datetime
import webbrowser

import numpy as np
import pandas as pd

import config
from pvgis_client import get_hourly_pv_production
from consumption import default_hourly_consumption, load_custom_consumption
from battery import simulate_battery_series
from analysis import (
    add_time_columns, daily_summary, monthly_summary,
    hourly_profile_by_season, compute_summary, compute_economic_summary,
    compute_lifecycle_environmental_summary, compute_lifecycle_projection,
    battery_sizing_diagnostics, compute_combined_economic_summary,
)
from report import build_report
from thermal import (
    compare_thermal_sources,
    evaluate_electric_alternatives,
    hourly_thermal_electricity_profile,
)


def run():
    thermal_runtime_config = {**config.THERMAL, "location_config": config.LOCATION}
    thermal_summary = None

    print("Generant/carregant perfil de consum...")
    custom_load = None
    target_hours = None
    if config.CONSUMPTION["profile"] == "custom_csv" and config.CONSUMPTION["custom_csv_path"]:
        custom_load = load_custom_consumption(config.CONSUMPTION["custom_csv_path"])
        target_hours = len(custom_load)

    print(f"Obtenint dades de produccio PV de PVGIS per '{config.LOCATION['name']}'...")
    pv = get_hourly_pv_production(
        config.LOCATION,
        config.PV_SYSTEM,
        database=config.PVGIS_DATABASE,
        target_hours=target_hours,
        heating_setpoint_c=config.THERMAL.get("heating_setpoint_c", 18.0),
    )
    if custom_load is not None:
        load = custom_load
    else:
        load = default_hourly_consumption(config.CONSUMPTION["annual_kwh"], year=pv.index[0].year)
    print(
        f"Any PVGIS representatiu: {pv.attrs['pvgis_reference_year']} "
        f"(selecció conjunta FV/calefacció entre {pv.attrs['pvgis_complete_years']} anys complets)"
    )

    _validate_hourly_profiles(pv, load)
    outdoor_temp = pv["outdoor_temp_c"] if "outdoor_temp_c" in pv else None
    if config.THERMAL.get("enabled", False):
        thermal_summary = compare_thermal_sources(
            config.THERMAL["annual_heat_demand_kwh"],
            thermal_runtime_config,
            outdoor_temp_series=outdoor_temp,
        )
        active_source = config.THERMAL.get("active_source")
        thermal_summary["active_source"] = next(
            (item for item in thermal_summary["sources"] if item["source_key"] == active_source),
            None,
        )
        print_thermal_summary(thermal_summary)

    pv_vals = pv["pv_kwh"].reset_index(drop=True)
    base_load_vals = load["load_kwh"].reset_index(drop=True)
    if thermal_summary is not None:
        thermal_summary["electric_alternatives_with_pv"] = evaluate_electric_alternatives(
            pv["pv_kwh"],
            load["load_kwh"],
            thermal_runtime_config,
            config.BATTERY,
            config.ECONOMY,
            config.LIFECYCLE,
            outdoor_temp,
        )
        print_electric_alternatives_summary(thermal_summary["electric_alternatives_with_pv"])
    if config.THERMAL.get("enabled", False):
        thermal_profile = hourly_thermal_electricity_profile(pv.index, thermal_runtime_config, outdoor_temp)
    else:
        thermal_profile = pd.DataFrame(
            {"thermal_heat_demand_kwh": 0.0, "thermal_electricity_kwh": 0.0, "thermal_cop": 0.0},
            index=pv.index,
        )
    if thermal_summary and thermal_summary.get("active_source"):
        thermal_summary["active_source"]["pv_thermal_electricity_kwh"] = float(
            thermal_profile["thermal_electricity_kwh"].sum()
        )
    thermal_heat_vals = thermal_profile["thermal_heat_demand_kwh"].reset_index(drop=True)
    thermal_electricity_vals = thermal_profile["thermal_electricity_kwh"].reset_index(drop=True)
    thermal_cop_vals = thermal_profile["thermal_cop"].reset_index(drop=True)
    if len(thermal_electricity_vals) != len(pv_vals):
        raise ValueError("El perfil tèrmic no coincideix amb el nombre d'hores de PVGIS")
    n = len(pv_vals)

    df = pd.DataFrame({
        "pv_kwh": pv_vals.iloc[:n].values,
        "base_load_kwh": base_load_vals.iloc[:n].values,
        "thermal_heat_demand_kwh": thermal_heat_vals.iloc[:n].values,
        "thermal_electricity_kwh": thermal_electricity_vals.iloc[:n].values,
        "thermal_cop": thermal_cop_vals.iloc[:n].values,
    })
    df["load_kwh"] = df["base_load_kwh"] + df["thermal_electricity_kwh"]
    df["surplus_kwh"] = df["pv_kwh"] - df["load_kwh"]

    if config.BATTERY["enabled"]:
        print("Simulant bateria...")
        bat_result = simulate_battery_series(df["surplus_kwh"], config.BATTERY)
        df = pd.concat([df, bat_result.reset_index(drop=True)], axis=1)
    else:
        df["grid_export_kwh"] = df["surplus_kwh"].clip(lower=0)
        df["grid_import_kwh"] = (-df["surplus_kwh"]).clip(lower=0)
        df["battery_soc_kwh"] = 0.0
        df["battery_soc_pct"] = 0.0

    df = add_time_columns(df, start_year=pv.index[0].year)

    print("Calculant resums diaris i mensuals...")
    daily = daily_summary(df)
    monthly = monthly_summary(df)
    hourly_profile = hourly_profile_by_season(df)
    summary = compute_summary(df)
    summary["pvgis_reference_year"] = pv.attrs.get("pvgis_reference_year", pv.index[0].year)
    summary["pvgis_complete_years"] = pv.attrs.get("pvgis_complete_years", 1)

    battery_diag = None
    if config.BATTERY["enabled"]:
        battery_diag = battery_sizing_diagnostics(df, daily, config.BATTERY)

    economic_summary = compute_economic_summary(
        summary,
        config.PV_SYSTEM["peak_power_kwp"],
        config.BATTERY,
        config.ECONOMY,
        config.LIFECYCLE,
    )
    lifecycle_projection = compute_lifecycle_projection(
        summary,
        config.PV_SYSTEM["peak_power_kwp"],
        config.BATTERY,
        config.ECONOMY,
        config.LIFECYCLE,
        df,
    )
    environmental_summary = compute_lifecycle_environmental_summary(
        summary,
        config.PV_SYSTEM["peak_power_kwp"],
        config.BATTERY,
        config.LIFECYCLE,
        df,
        lifecycle_projection,
    )
    economic_summary["npv"] = lifecycle_projection.get("npv", economic_summary["npv"])
    economic_summary["npv_25y"] = economic_summary["npv"]
    combined_economic_summary = compute_combined_economic_summary(
        thermal_summary, economic_summary, config.ECONOMY
    )

    print_summary(summary)
    print_economic_summary(economic_summary)
    print_environmental_summary(environmental_summary)
    if battery_diag:
        print_battery_diag(battery_diag)

    if config.OUTPUT.get("save_hourly_csv", True):
        df.drop(columns=["day"]).to_csv(config.OUTPUT["hourly_csv_path"], index=False)
        print(f"\nDades horaries desades a {config.OUTPUT['hourly_csv_path']}")

    if config.OUTPUT.get("save_daily_csv", True):
        daily.to_csv(config.OUTPUT.get("daily_csv_path", "resultats_diaris.csv"))
        print(f"Resum diari desat a {config.OUTPUT.get('daily_csv_path', 'resultats_diaris.csv')}")

    if config.OUTPUT.get("make_report", True):
        path = build_report(df, daily, monthly, hourly_profile, summary, battery_diag,
                            economic_summary, environmental_summary, lifecycle_projection,
                            config.OUTPUT.get("report_html_path", "informe.html"), thermal_summary, config,
                            combined_economic_summary)
        print(f"Informe HTML generat a {path}")
        archive_path = archive_report(path, config.OUTPUT.get("report_archive_dir", "informes_historic"),
                                      config.LOCATION.get("name", "ubicacio"))
        print(f"Copia historica desada a {archive_path}")
        if config.OUTPUT.get("open_report_in_browser", True):
            webbrowser.open("file://" + os.path.abspath(path))

    return df


def _validate_hourly_profiles(pv, load):
    """Comprova que producció i consum cobreixen el mateix any hora a hora."""
    for label, frame, column in (("PVGIS", pv, "pv_kwh"), ("consum", load, "load_kwh")):
        if column not in frame.columns:
            raise ValueError(f"La sèrie de {label} no conté la columna '{column}'")
        if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.hasnans:
            raise ValueError(f"La sèrie de {label} no té un índex de dates vàlid")
        if frame.index.tz is not None:
            raise ValueError(f"La sèrie de {label} ha d'utilitzar hores locals sense zona horària")
        if not len(frame.index) or not frame.index.is_monotonic_increasing or frame.index.has_duplicates:
            raise ValueError(f"La sèrie de {label} és buida, desordenada o té hores duplicades")
        expected = pd.date_range(
            f"{frame.index[0].year}-01-01 00:00",
            f"{frame.index[0].year}-12-31 23:00",
            freq="h",
        )
        if not frame.index.equals(expected):
            raise ValueError(f"La sèrie de {label} no cobreix un any complet d'hores sense salts")
        values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(f"La sèrie de {label} conté valors negatius, buits o no finits")

    if len(pv) != len(load):
        raise ValueError(
            f"Les sèries no cobreixen el mateix nombre d'hores: PVGIS={len(pv)}, consum={len(load)}. "
            "Cal proporcionar un any complet amb el mateix nombre d'hores (inclòs el tractament dels anys de traspàs)."
        )


def archive_report(report_path, archive_dir, location_name):
    """Desa una còpia de l'informe amb la ubicació i l'instant de la simulació."""
    os.makedirs(archive_dir, exist_ok=True)
    normalized_name = unicodedata.normalize("NFKD", str(location_name))
    ascii_name = normalized_name.encode("ascii", "ignore").decode("ascii")
    safe_location = re.sub(r"[^A-Za-z0-9]+", "_", ascii_name).strip("_") or "ubicacio"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = os.path.join(archive_dir, f"{safe_location}_{timestamp}.html")
    shutil.copy2(report_path, archive_path)
    return archive_path


def print_thermal_summary(thermal_summary):
    print("\n" + "=" * 52)
    print(" ANALISI DE FONTS TERMiques")
    print("=" * 52)
    print(f" Demanda termica:                 {thermal_summary['heat_demand_kwh']:10.0f} kWh")
    for label, key in (("Recomanada", "recommended"), ("Millor cost", "best_cost"),
                       ("Millor ambiental", "best_environment"), ("Millor energia", "best_energy")):
        result = thermal_summary.get(key)
        if result:
            print(f" {label}: {result['source_name']} ({result['annualized_total_cost_eur']:.0f} €/any anualitzats, "
                  f"{result['emissions_kg_co2e']:.0f} kg CO2e, "
                  f"{result['primary_energy_nonrenewable_kwh']:.0f} kWh prim. no renovable)")
    print("-" * 52)
    print(" Comparativa:")
    for result in thermal_summary["sources"]:
        print(f"  {result['source_name']:<28} {result['annual_total_cost_eur']:>7.0f} €/any  "
              f"{result['emissions_kg_co2e']:>7.0f} kg CO2e  "
              f"{result['primary_energy_nonrenewable_kwh']:>7.0f} kWh")
    print("=" * 52)


def print_electric_alternatives_summary(results):
    if not results:
        return
    print("\n" + "-" * 52)
    print(" ALTERNATIVES ELECTRIQUES AMB FV EXISTENT")
    print("-" * 52)
    for result in results:
        print(f" {result['source_name']:<28} import xarxa: {result['grid_import_kwh']:>7.0f} kWh  "
              f"cost energia + manteniment: {result['system_energy_cost_eur']:>7.0f} €")
    print("-" * 52)


def print_summary(summary):
    print("\n" + "=" * 52)
    print(" RESUM ANUAL")
    print("=" * 52)
    print(f" Produccio FV total:          {summary['total_pv']:10.1f} kWh")
    print(f" Consum total:                {summary['total_load']:10.1f} kWh")
    print(f" Autoconsumit:                {summary['self_consumed']:10.1f} kWh")
    print(f" Excedent exportat a xarxa:   {summary['total_export']:10.1f} kWh")
    print(f" Energia importada de xarxa:  {summary['total_import']:10.1f} kWh")
    print(f" Taxa d'autoconsum:           {summary['self_consumption_rate']:10.1f} %")
    print(f" Taxa d'autosuficiencia:      {summary['self_sufficiency_rate']:10.1f} %")
    print("=" * 52)


def print_economic_summary(economic_summary):
    print("\n" + "=" * 52)
    print(" ANALISI ECONOMICA")
    print("=" * 52)
    print(f" Cost total instal.lacio:        {economic_summary['capex_total']:10.0f} €")
    print(f" Cost plaques FV:                {economic_summary['pv_capex']:10.0f} €")
    print(f" Cost bateria:                   {economic_summary['battery_capex']:10.0f} €")
    print(f" Estalvi anual estimat:          {economic_summary['annual_bill_saving']:10.0f} €/any")
    print(f" Flux net anual:                {economic_summary['annual_cashflow']:10.0f} €/any")
    if economic_summary['payback_years'] is None:
        print(" Temps de recuperacio:           no viable econòmicament")
    else:
        print(f" Temps de recuperacio:           {economic_summary['payback_years']:10.1f} anys")
    print(f" VAN estimat ({economic_summary['project_life_years']} anys):      {economic_summary['npv']:10.0f} €")
    print(f" Preu compra electricitat:      {economic_summary['buy_price']:10.2f} €/kWh")
    print(f" Preu venda excedents:          {economic_summary['sell_price']:10.2f} €/kWh")
    print(f" Pèrdua anual de producció:     {economic_summary['panel_degradation_pct_per_year'] * 100:5.2f} %/any")
    print("=" * 52)


def print_environmental_summary(environmental_summary):
    print("\n" + "=" * 52)
    print(" IMPACTE AMBIENTAL")
    print("=" * 52)
    print(f" Emissions incorporades:        {environmental_summary['embodied_co2_kg']:10.0f} kg CO2e")
    print(f" CO2 evitat / any:             {environmental_summary['avoided_co2_per_year_kg']:10.0f} kg CO2e")
    life_years = environmental_summary.get("panel_life_years", 25)
    print(f" CO2 evitat en {life_years} anys:        {environmental_summary['co2_saved_kg_over_life']:10.0f} kg CO2e")
    print(f" Balanç net {life_years} anys:           {environmental_summary['net_co2_kg']:10.0f} kg CO2e")
    print("=" * 52)


def print_battery_diag(diag):
    print("\n" + "-" * 52)
    print(" DIAGNOSTIC DE LA BATERIA")
    print("-" * 52)
    print(f" Dies bateria saturada ({diag['max_soc_pct']:.0f}%):       {diag['n_saturated_days']} / {diag['n_days']}")
    print(f" Dies bateria buida:                   {diag['n_empty_days']} / {diag['n_days']}")
    print(f" Dies limitats per potencia carrega:   {diag['n_power_charge_days']} / {diag['n_days']}")
    print(f" Dies limitats per potencia descarrega:{diag['n_power_discharge_days']} / {diag['n_days']}")
    print(f" Cicles complets equivalents/any:      {diag['equivalent_cycles']:.0f}")
    print(f" Energia perduda (bateria plena):      {diag['energy_lost_full']:.0f} kWh")
    print(f" Energia no coberta (bateria buida):   {diag['energy_unmet_empty']:.0f} kWh")
    print("-" * 52)
    print(" Recomanacio:")
    print(f" {diag['recommendation']}")
    print("-" * 52)


if __name__ == "__main__":
    run()
