import json
import types
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES_DIR = ROOT / "cases"


def default_case():
    return {
        "LOCATION": {
            "name": "Santa Maria d'Oló",
            "lat": 41.8745,
            "lon": 2.0347,
            "altitude_m": 542,
            "climate": {
                "mean_annual_air_temp_c": 15.3,
                "winter_design_temp_c": 3.0,
                "summer_design_temp_c": 29.0,
                "heating_degree_days_base_18": 1300,
                "cooling_degree_days_base_26": 120,
            },
            "ground": {
                "mean_ground_temp_c": 14.5,
                "thermal_conductivity_w_mk": 2.2,
                "thermal_diffusivity_m2_s": 1.1e-6,
                "groundwater_level_m": 5.0,
                "borehole_spacing_m": 6.0,
                "rock_type": "granit",
            },
        },
        "PV_SYSTEM": {
            "peak_power_kwp": 5.0,
            "tilt_deg": 30,
            "azimuth_deg": 0,
            "system_loss_pct": 14,
            "technology": "crystSi",
            "mounting": "building",
            "use_horizon": True,
        },
        "PVGIS_DATABASE": "PVGIS-SARAH3",
        "CONSUMPTION": {
            "annual_kwh": 6000,
            "profile": "residential_default",
            "custom_csv_path": None,
        },
        "THERMAL": {
            "enabled": True,
            "annual_heat_demand_kwh": 10000.0,
            "active_source": "aerotermia",
            "peak_power_kw": 8.0,
            "analysis_years": 20,
            "heating_setpoint_c": 22.0,
            "heat_demand_mode": "annual_kwh",
            "building_heat_loss_kw_per_k": 0.25,
            "ground_loop_target_temp_c": 8.0,
            "borehole_diameter_m": 0.12,
            "groundwater_level_m": 5.0,
            "payback_reference": "gas_natural",
            "sources": [
                "gas_natural",
                "gasoil",
                "aerotermia",
                "geotermia",
                "biomassa",
                "electricitat_resistencia",
            ],
            "weights": {"cost": 0.34, "environment": 0.33, "energy": 0.33},
            "source_overrides": {},
        },
        "BATTERY": {
            "enabled": True,
            "capacity_kwh": 3.0,
            "max_charge_kw": 3.0,
            "max_discharge_kw": 3.0,
            "round_trip_efficiency": 0.90,
            "min_soc_pct": 10,
            "max_soc_pct": 100,
            "initial_soc_pct": 50,
        },
        "ECONOMY": {
            "pv_cost_per_kw": 1250.0,
            "battery_cost_per_kwh": 650.0,
            "battery_cost_per_kw": 120.0,
            "installation_extra_pct": 0.12,
            "annual_om_pct": 0.015,
            "electricity_buy_price_eur_kwh": 0.2669,
            "electricity_sell_price_eur_kwh": 0.09,
            "annual_inflation_pct": 0.02,
            "discount_rate_pct": 0.04,
            "project_life_years": 25,
        },
        "LIFECYCLE": {
            "panel_degradation_pct_per_year": 0.004,
            "panel_life_years": 25,
            "battery_life_years": 10,
            "inverter_life_years": 12,
            "inverter_cost_per_kw": 180.0,
            "pv_embodied_co2_kg_per_kwp": 340.0,
            "battery_embodied_co2_kg_per_kwh": 80.0,
            "inverter_embodied_co2_kg_per_kw": 40.0,
            "grid_emission_factor_kg_co2_per_kwh": 0.18,
        },
        "OUTPUT": {
            "save_hourly_csv": True,
            "hourly_csv_path": "resultats_horaris.csv",
            "make_plots": True,
            "make_report": True,
            "report_archive_dir": "informes_historic",
            "open_report_in_browser": True,
        },
    }


def ensure_cases_dir():
    CASES_DIR.mkdir(exist_ok=True)


def load_case(case_path):
    path = Path(case_path)
    if not path.exists():
        raise FileNotFoundError(f"No existeix el cas: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data


def save_case(case_data, case_path):
    path = Path(case_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(case_data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return str(path)


def build_runtime_config(case_data):
    runtime_config = types.ModuleType("runtime_config")
    for key in [
        "LOCATION",
        "PV_SYSTEM",
        "PVGIS_DATABASE",
        "CONSUMPTION",
        "THERMAL",
        "BATTERY",
        "ECONOMY",
        "LIFECYCLE",
        "OUTPUT",
    ]:
        if key in case_data:
            setattr(runtime_config, key, case_data[key])
    return runtime_config


def list_case_files():
    ensure_cases_dir()
    files = sorted(CASES_DIR.glob("*.json"))
    return [file.name for file in files]


def get_default_case_file():
    ensure_cases_dir()
    default_path = CASES_DIR / "default_case.json"
    if not default_path.exists():
        save_case(default_case(), default_path)
    return str(default_path)


def slugify_case_name(name):
    sanitized = name.strip().lower()
    sanitized = sanitized.replace(" ", "_")
    sanitized = sanitized.replace("/", "_")
    sanitized = sanitized.replace("\\", "_")
    sanitized = ''.join(ch if ch.isalnum() or ch in "_-" else "_" for ch in sanitized)
    sanitized = sanitized.strip("_")
    return sanitized or "cas"
