import hashlib
import json
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

import streamlit as st

from case_manager import (
    CASES_DIR,
    default_case,
    get_default_case_file,
    list_case_files,
    load_case,
    prepare_ephemeral_run_case,
    save_case,
    slugify_case_name,
)

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="Basic Case Editor", page_icon="⚡", layout="wide")


def get_case_from_state():
    if "case" not in st.session_state:
        default_path = get_default_case_file()
        st.session_state.case = load_case(default_path)
    return st.session_state.case


case = get_case_from_state()


st.title("Calculadora energètica residencial")
st.caption("Configura el sistema i genera un informe tècnic, econòmic i ambiental. Els casos es mantenen a la sessió del navegador; exporta el JSON si el vols conservar.")

case_files = list_case_files()
if not case_files:
    case_files = ["default_case.json"]

with st.sidebar:
    st.subheader("Casos")
    selected_case = st.selectbox("Casos guardats", options=case_files, index=0)
    st.caption("Els casos predefinits són compartits; les modificacions només afecten la teva sessió.")

    if st.button("Carregar el cas seleccionat"):
        try:
            loaded = load_case(Path(CASES_DIR) / selected_case)
            st.session_state.case = loaded
            case.clear()
            case.update(loaded)
            st.session_state.pop("generated_outputs", None)
            st.success(f"Cas carregat a la sessió: {selected_case}")
        except Exception as exc:
            st.error(f"No s'ha pogut carregar: {exc}")

    uploaded_case = st.file_uploader("Carregar un cas JSON", type=["json"], key="case_json_upload")
    if uploaded_case is not None:
        upload_content = uploaded_case.getvalue()
        upload_fingerprint = hashlib.sha256(upload_content).hexdigest()
        if upload_fingerprint != st.session_state.get("loaded_case_fingerprint"):
            try:
                loaded = json.loads(upload_content.decode("utf-8"))
                required_sections = {
                    "LOCATION", "PV_SYSTEM", "CONSUMPTION", "THERMAL",
                    "BATTERY", "ECONOMY", "LIFECYCLE", "OUTPUT",
                }
                if not isinstance(loaded, dict) or not required_sections.issubset(loaded):
                    raise ValueError("El JSON no conté tots els blocs de configuració requerits.")
                case.clear()
                case.update(loaded)
                st.session_state.case = case
                st.session_state["loaded_case_fingerprint"] = upload_fingerprint
                st.session_state.pop("generated_outputs", None)
                st.success("Cas JSON carregat a la sessió.")
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                st.error(f"No s'ha pogut carregar el cas JSON: {exc}")

    if case["CONSUMPTION"].get("profile") == "custom_csv":
        uploaded_consumption = st.file_uploader(
            "Consum horari CSV",
            type=["csv"],
            help="Sèrie completa d'un any amb data/hora i kWh. Es tracta només a la sessió actual.",
            key="custom_consumption_upload",
        )
        if uploaded_consumption is not None:
            st.session_state["custom_consumption_csv"] = {
                "name": uploaded_consumption.name,
                "content": uploaded_consumption.getvalue(),
            }
        if st.session_state.get("custom_consumption_csv"):
            st.caption(f"CSV preparat: {st.session_state['custom_consumption_csv']['name']}")

    if st.button("Crear un cas en blanc"):
        fresh_case = default_case()
        fresh_case["LOCATION"]["name"] = "Cas nou"
        st.session_state.case = fresh_case
        case.clear()
        case.update(fresh_case)
        st.session_state.pop("generated_outputs", None)
        st.success("Cas en blanc creat a la sessió.")

    case_filename = f"{slugify_case_name(case['LOCATION']['name'])}.json"
    st.download_button(
        "Descarregar cas JSON",
        data=json.dumps(case, indent=2, ensure_ascii=False),
        file_name=case_filename,
        mime="application/json",
        use_container_width=True,
    )
    st.caption("Aquest cas només es desa al navegador durant la sessió. Descarrega el JSON per conservar-lo o tornar-lo a carregar més tard.")

st.subheader("Dades del cas actual")
case_name = st.text_input("Nom del cas", value=case["LOCATION"]["name"].replace(" ", "_").lower())


def save_current_case():
    st.session_state.case = deepcopy(case)
    st.session_state.pop("generated_outputs", None)
    st.session_state["case_saved_in_session"] = True


if st.session_state.pop("case_saved_in_session", False):
    st.success("Canvis desats a la sessió del navegador.")


def generate_report_html():
    try:
        safe_name = slugify_case_name(case_name.strip() or "cas")
        with tempfile.TemporaryDirectory(prefix="energia_case_") as output_dir:
            run_case = prepare_ephemeral_run_case(case, output_dir)
            if run_case["CONSUMPTION"].get("profile") == "custom_csv":
                uploaded_consumption = st.session_state.get("custom_consumption_csv")
                if not uploaded_consumption:
                    st.error("Carrega el CSV horari de consum a la barra lateral abans de generar l'informe.")
                    return
                consumption_path = Path(output_dir) / "consum_horari.csv"
                consumption_path.write_bytes(uploaded_consumption["content"])
                run_case["CONSUMPTION"]["custom_csv_path"] = str(consumption_path)
            case_path = Path(output_dir) / "case.json"
            save_case(run_case, case_path)

            with st.spinner("Consultant PVGIS i generant l'informe..."):
                result = subprocess.run(
                    [sys.executable, "simulate_case.py", str(case_path)],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    timeout=600,
                )

            if result.returncode != 0:
                st.error("La simulació ha fallat.")
                st.code(result.stdout)
                st.code(result.stderr)
                return

            outputs = run_case["OUTPUT"]
            generated = {
                "report_name": f"{safe_name}_informe.html",
                "report": Path(outputs["report_html_path"]).read_bytes(),
                "hourly_name": f"{safe_name}_horari.csv",
                "daily_name": f"{safe_name}_diari.csv",
            }
            generated["hourly"] = (
                Path(outputs["hourly_csv_path"]).read_bytes()
                if outputs.get("save_hourly_csv") else None
            )
            generated["daily"] = (
                Path(outputs["daily_csv_path"]).read_bytes()
                if outputs.get("save_daily_csv") else None
            )
            st.session_state["generated_outputs"] = generated
            st.session_state["generated_case_fingerprint"] = hashlib.sha256(
                json.dumps(case, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest()
        st.success("Informe generat. Descarrega'l al dispositiu.")
    except subprocess.TimeoutExpired:
        st.error("La simulació ha superat el temps màxim de 10 minuts. Revisa el cas o torna-ho a provar més tard.")
    except Exception as exc:
        st.error(f"Error: {exc}")


tabs = st.tabs(["Ubicació", "PV", "Consum", "Tèrmic", "Bateria", "Econòmic", "Sortida"])

with tabs[0]:
    with st.form("form_ubicacio"):
        st.subheader("Ubicació")
        case["LOCATION"]["name"] = st.text_input("Nom", value=case["LOCATION"]["name"])
        case["LOCATION"]["lat"] = st.number_input("Latitud", value=float(case["LOCATION"]["lat"]), step=0.0001)
        case["LOCATION"]["lon"] = st.number_input("Longitud", value=float(case["LOCATION"]["lon"]), step=0.0001)
        case["LOCATION"]["altitude_m"] = st.number_input("Altitud (m)", value=int(case["LOCATION"]["altitude_m"]))
        st.markdown("#### Propietats tèrmiques del terreny")
        ground = case["LOCATION"].setdefault("ground", {})
        ground["mean_ground_temp_c"] = st.number_input("Temperatura mitjana del sòl (°C)", value=float(ground.get("mean_ground_temp_c", 14.5)), step=0.5)
        ground["thermal_conductivity_w_mk"] = st.number_input("Conductivitat tèrmica del sòl (W/m·K)", value=float(ground.get("thermal_conductivity_w_mk", 2.2)), min_value=0.1, step=0.1)
        ground["thermal_diffusivity_m2_s"] = st.number_input("Difusivitat tèrmica del sòl (m²/s)", value=float(ground.get("thermal_diffusivity_m2_s", 1.1e-6)), min_value=1e-9, step=1e-7, format="%.8f")
        ground["groundwater_level_m"] = st.number_input("Profunditat nivell freàtic (m)", value=float(ground.get("groundwater_level_m", 5.0)), min_value=0.0, step=0.5)
        ground["borehole_spacing_m"] = st.number_input("Separació entre sondes (m)", value=float(ground.get("borehole_spacing_m", 6.0)), min_value=1.0, step=0.5)
        st.form_submit_button("Guardar ubicació", on_click=save_current_case)

with tabs[1]:
    with st.form("form_pv"):
        st.subheader("Sistema fotovoltaic")
        case["PV_SYSTEM"]["peak_power_kwp"] = st.number_input("Potència pic (kWp)", value=float(case["PV_SYSTEM"]["peak_power_kwp"]), step=0.1)
        case["PV_SYSTEM"]["tilt_deg"] = st.number_input("Inclinació (º)", value=float(case["PV_SYSTEM"]["tilt_deg"]), step=1.0)
        case["PV_SYSTEM"]["azimuth_deg"] = st.number_input("Azimut (º)", value=float(case["PV_SYSTEM"]["azimuth_deg"]), step=1.0)
        case["PV_SYSTEM"]["system_loss_pct"] = st.number_input("Pèrdues del sistema (%)", value=float(case["PV_SYSTEM"]["system_loss_pct"]), step=1.0)
        case["PV_SYSTEM"]["technology"] = st.selectbox("Tecnologia", ["crystSi", "CIS", "CdTe", "monoSi"], index=["crystSi", "CIS", "CdTe", "monoSi"].index(case["PV_SYSTEM"]["technology"]))
        case["PV_SYSTEM"]["mounting"] = st.selectbox("Muntatge", ["building", "free"], index=["building", "free"].index(case["PV_SYSTEM"]["mounting"]))
        case["PV_SYSTEM"]["use_horizon"] = st.checkbox("Tenir en compte horitzó", value=bool(case["PV_SYSTEM"]["use_horizon"]))
        case["PVGIS_DATABASE"] = st.selectbox("Base meteorològica", ["PVGIS-SARAH3", "PVGIS-ERA5"], index=["PVGIS-SARAH3", "PVGIS-ERA5"].index(case["PVGIS_DATABASE"]))
        st.form_submit_button("Guardar sistema FV", on_click=save_current_case)

with tabs[2]:
    with st.form("form_consum"):
        st.subheader("Consum")
        case["CONSUMPTION"]["annual_kwh"] = st.number_input("Consum anual (kWh)", value=float(case["CONSUMPTION"]["annual_kwh"]), step=100.0)
        case["CONSUMPTION"]["profile"] = st.selectbox("Perfil", ["residential_default", "custom_csv"], index=["residential_default", "custom_csv"].index(case["CONSUMPTION"]["profile"]))
        case["CONSUMPTION"]["custom_csv_path"] = None
        if case["CONSUMPTION"]["profile"] == "custom_csv":
            st.info("Desa el consum i puja el CSV des de la barra lateral. El fitxer no es desa al servidor.")
        st.form_submit_button("Guardar consum", on_click=save_current_case)

with tabs[3]:
    with st.form("form_termic"):
        st.subheader("Tèrmic")
        case["THERMAL"]["enabled"] = st.checkbox("Activat", value=bool(case["THERMAL"]["enabled"]))
        case["THERMAL"]["annual_heat_demand_kwh"] = st.number_input("Demanda tèrmica anual (kWh)", value=float(case["THERMAL"]["annual_heat_demand_kwh"]), step=100.0)
        case["THERMAL"]["heat_demand_mode"] = st.selectbox(
            "Mètode de demanda", ["annual_kwh", "heat_loss_coefficient"],
            format_func=lambda mode: "Consum anual conegut" if mode == "annual_kwh" else "Coeficient de pèrdua × graus-hora",
            index=["annual_kwh", "heat_loss_coefficient"].index(case["THERMAL"].get("heat_demand_mode", "annual_kwh")),
        )
        if case["THERMAL"]["heat_demand_mode"] == "heat_loss_coefficient":
            case["THERMAL"]["building_heat_loss_kw_per_k"] = st.number_input(
                "Pèrdua tèrmica de l'edifici (kW/K)",
                value=float(case["THERMAL"].get("building_heat_loss_kw_per_k", 0.25)),
                min_value=0.001, step=0.01,
                help="Demanda estimada = kW/K × suma horària de max(consigna − temperatura exterior, 0). Cal calibrar amb dades de l'edifici.",
            )
        st.caption("Amb consum anual conegut, el temps redistribueix la demanda i modifica el COP; no canvia artificialment la calor anual. El mode kW/K estima també la demanda segons el fred de l'any meteorològic.")
        case["THERMAL"]["active_source"] = st.selectbox("Font activa", case["THERMAL"]["sources"], index=case["THERMAL"]["sources"].index(case["THERMAL"]["active_source"]))
        case["THERMAL"]["peak_power_kw"] = st.number_input("Potència tèrmica (kW)", value=float(case["THERMAL"]["peak_power_kw"]), step=1.0)
        case["THERMAL"]["analysis_years"] = st.number_input("Anys d'anàlisi", value=int(case["THERMAL"]["analysis_years"]), step=1)
        case["THERMAL"]["heating_setpoint_c"] = st.number_input("Consigna calefacció (ºC)", value=float(case["THERMAL"]["heating_setpoint_c"]), step=0.5)
        case["THERMAL"]["ground_loop_target_temp_c"] = st.number_input("Temperatura objectiu del circuit geotèrmic (°C)", value=float(case["THERMAL"].get("ground_loop_target_temp_c", 8.0)), step=0.5)
        case["THERMAL"]["borehole_diameter_m"] = st.number_input("Diàmetre de perforació (m)", value=float(case["THERMAL"].get("borehole_diameter_m", 0.12)), min_value=0.05, step=0.01)
        case["THERMAL"]["groundwater_level_m"] = st.number_input("Profunditat del nivell freàtic (m)", value=float(case["THERMAL"].get("groundwater_level_m", 5.0)), min_value=0.0, step=0.5)
        overrides = case["THERMAL"].setdefault("source_overrides", {})
        st.markdown("#### Hipòtesis editables per font")
        st.caption("Els valors inicials del catàleg són orientatius. Ajusta'ls amb pressupostos, factures o fitxes tècniques del sistema concret.")
        st.caption("El model meteorològic estima el COP horari amb una corba termodinàmica simplificada; introdueix les dades del fabricant per representar amb més precisió una màquina concreta. Aquest COP no és un SCOP certificat.")
        fields = [
                ("resource_price_eur_per_kwh", "Preu del recurs (€/kWh)"),
                ("direct_emission_factor_kg_co2_per_kwh", "Emissions directes (kg CO₂e/kWh recurs)"),
                ("maintenance_annual_eur", "Manteniment anual (€)"),
                ("fixed_annual_cost_eur", "Cost fix anual (€)"),
                ("capex_eur_per_kw", "Inversió equip (€/kW)"),
        ]
        from thermal import THERMAL_SOURCES
        for source_key in case["THERMAL"]["sources"]:
            with st.expander(source_key.replace("_", " ").title()):
                values = overrides.setdefault(source_key, {})
                source_defaults = THERMAL_SOURCES[source_key]
                performance_field = "cop" if "cop" in source_defaults else "efficiency"
                performance_label = "COP al punt de referència" if performance_field == "cop" else "Rendiment sobre el poder calorífic (factor)"
                for field, label in [*fields, (performance_field, performance_label)]:
                    if source_key == "geotermia" and field == "capex_eur_per_kw":
                        continue
                    default = float(values[field]) if field in values else float(source_defaults.get(field, 0.0))
                    values[field] = st.number_input(
                        label, value=default, min_value=0.0,
                        max_value=2.0 if field == "efficiency" else 1000000000.0,
                        step=0.01 if "price" in field or "emission" in field or field == "efficiency" else 0.1 if field == "cop" else 1.0,
                        key=f"thermal_{source_key}_{field}",
                    )
                if source_key == "aerotermia":
                    values["flow_temp_c"] = st.number_input("Temperatura d'impulsió (°C)", value=float(values.get("flow_temp_c", 35.0)), min_value=20.0, max_value=80.0, step=1.0, key="hp_flow_temp")
                    values["weather_compensation_c_per_c"] = st.number_input("Compensació climàtica (°C d'impulsió / °C exterior)", value=float(values.get("weather_compensation_c_per_c", 0.0)), min_value=0.0, max_value=2.0, step=0.05, key="hp_weather_comp")
                if source_key == "geotermia":
                    for field, label, default, step in [
                        ("heat_pump_capex_eur_per_kw", "Bomba geotèrmica (€/kW)", 1500.0, 50.0),
                        ("drilling_labor_cost_per_m_eur", "Perforació i mà d'obra (€/m)", 39.0, 1.0),
                        ("probe_material_cost_per_m_eur", "Sonda i canonada (€/m)", 16.0, 1.0),
                        ("grout_material_cost_per_m_eur", "Reblert tèrmic (€/m)", 8.0, 1.0),
                        ("drilling_mobilization_eur", "Mobilització perforadora (€)", 435.5, 25.0),
                    ]:
                        values[field] = st.number_input(label, value=float(values.get(field, default)), min_value=0.0, step=step, key=f"geo_{field}")
        st.form_submit_button("Guardar tèrmic", on_click=save_current_case)

with tabs[4]:
    with st.form("form_bateria"):
        st.subheader("Bateria")
        case["BATTERY"]["enabled"] = st.checkbox("Bateria activada", value=bool(case["BATTERY"]["enabled"]))
        case["BATTERY"]["capacity_kwh"] = st.number_input("Capacitat (kWh)", value=float(case["BATTERY"]["capacity_kwh"]), step=0.5)
        case["BATTERY"]["max_charge_kw"] = st.number_input("Càrrega màxima (kW)", value=float(case["BATTERY"]["max_charge_kw"]), step=0.5)
        case["BATTERY"]["max_discharge_kw"] = st.number_input("Descàrrega màxima (kW)", value=float(case["BATTERY"]["max_discharge_kw"]), step=0.5)
        case["BATTERY"]["round_trip_efficiency"] = st.number_input("Eficiència round trip", value=float(case["BATTERY"]["round_trip_efficiency"]), min_value=0.0, max_value=1.0, step=0.01)
        case["BATTERY"]["min_soc_pct"] = st.number_input("SOC mínim (%)", value=float(case["BATTERY"]["min_soc_pct"]), step=1.0)
        case["BATTERY"]["max_soc_pct"] = st.number_input("SOC màxim (%)", value=float(case["BATTERY"].get("max_soc_pct", 100)), min_value=float(case["BATTERY"]["min_soc_pct"]), max_value=100.0, step=1.0)
        case["BATTERY"]["initial_soc_pct"] = st.number_input("SOC inicial (%)", value=float(case["BATTERY"].get("initial_soc_pct", 50)), min_value=float(case["BATTERY"]["min_soc_pct"]), max_value=float(case["BATTERY"]["max_soc_pct"]), step=1.0)
        st.form_submit_button("Guardar bateria", on_click=save_current_case)

with tabs[5]:
    with st.form("form_economic"):
        st.subheader("Econòmic")
        case["ECONOMY"]["pv_cost_per_kw"] = st.number_input("Cost FV (€/kWp)", value=float(case["ECONOMY"]["pv_cost_per_kw"]), step=10.0)
        case["ECONOMY"]["battery_cost_per_kwh"] = st.number_input("Cost bateria (€/kWh)", value=float(case["ECONOMY"]["battery_cost_per_kwh"]), step=10.0)
        case["ECONOMY"]["battery_cost_per_kw"] = st.number_input("Cost potència bateria (€/kW)", value=float(case["ECONOMY"].get("battery_cost_per_kw", 0.0)), step=10.0)
        case["ECONOMY"]["installation_extra_pct"] = st.number_input("Cost addicional instal·lació (%)", value=float(case["ECONOMY"].get("installation_extra_pct", 0.0)) * 100, step=1.0) / 100
        case["ECONOMY"]["annual_om_pct"] = st.number_input("Manteniment FV/bateria (% CAPEX/any)", value=float(case["ECONOMY"].get("annual_om_pct", 0.0)) * 100, step=0.1) / 100
        case["ECONOMY"]["electricity_buy_price_eur_kwh"] = st.number_input("Preu compra llum (€/kWh)", value=float(case["ECONOMY"]["electricity_buy_price_eur_kwh"]), step=0.01)
        case["ECONOMY"]["electricity_sell_price_eur_kwh"] = st.number_input("Preu venda excedent (€/kWh)", value=float(case["ECONOMY"]["electricity_sell_price_eur_kwh"]), step=0.01)
        case["ECONOMY"]["annual_inflation_pct"] = st.number_input("Indexació anual nominal (%)", value=float(case["ECONOMY"].get("annual_inflation_pct", 0.02)) * 100, step=0.25) / 100
        case["ECONOMY"]["discount_rate_pct"] = st.number_input("Taxa de descompte (%)", value=float(case["ECONOMY"].get("discount_rate_pct", 0.04)) * 100, step=0.25) / 100
        case["ECONOMY"]["project_life_years"] = st.number_input("Vida útil project (anys)", value=int(case["ECONOMY"]["project_life_years"]), step=1)
        st.subheader("Vida útil i emissions incorporades")
        lifecycle = case["LIFECYCLE"]
        lifecycle["panel_degradation_pct_per_year"] = st.number_input("Degradació FV anual (%)", value=float(lifecycle.get("panel_degradation_pct_per_year", 0.004)) * 100, step=0.05) / 100
        lifecycle["panel_life_years"] = st.number_input("Vida útil panells (anys)", value=int(lifecycle.get("panel_life_years", 25)), min_value=1, step=1)
        lifecycle["battery_life_years"] = st.number_input("Vida útil bateria (anys)", value=int(lifecycle.get("battery_life_years", 10)), min_value=1, step=1)
        lifecycle["inverter_life_years"] = st.number_input("Vida útil inversor (anys)", value=int(lifecycle.get("inverter_life_years", 12)), min_value=1, step=1)
        lifecycle["inverter_cost_per_kw"] = st.number_input("Cost inversor de substitució (€/kW)", value=float(lifecycle.get("inverter_cost_per_kw", 0)), step=10.0)
        lifecycle["grid_emission_factor_kg_co2_per_kwh"] = st.number_input("Factor d'emissió xarxa (kg CO₂e/kWh)", value=float(lifecycle.get("grid_emission_factor_kg_co2_per_kwh", 0.18)), min_value=0.0, step=0.01)
        lifecycle["pv_embodied_co2_kg_per_kwp"] = st.number_input("Emissions incorporades FV (kg CO₂e/kWp)", value=float(lifecycle.get("pv_embodied_co2_kg_per_kwp", 340)), step=10.0)
        lifecycle["battery_embodied_co2_kg_per_kwh"] = st.number_input("Emissions incorporades bateria (kg CO₂e/kWh)", value=float(lifecycle.get("battery_embodied_co2_kg_per_kwh", 80)), step=10.0)
        lifecycle["inverter_embodied_co2_kg_per_kw"] = st.number_input("Emissions incorporades inversor (kg CO₂e/kW)", value=float(lifecycle.get("inverter_embodied_co2_kg_per_kw", 40)), step=10.0)
        st.form_submit_button("Guardar econòmic", on_click=save_current_case)

with tabs[6]:
    with st.form("form_sortida"):
        st.subheader("Sortida")
        case["OUTPUT"]["save_hourly_csv"] = st.checkbox("Guardar CSV horari", value=bool(case["OUTPUT"]["save_hourly_csv"]))
        case["OUTPUT"]["save_daily_csv"] = st.checkbox("Guardar resum diari CSV", value=bool(case["OUTPUT"].get("save_daily_csv", True)))
        st.caption("Els fitxers es generen temporalment i es descarreguen des d'aquesta pàgina.")
        st.form_submit_button("Guardar sortida", on_click=save_current_case)

st.markdown("---")
if st.button("Generar informe HTML final", type="primary"):
    generate_report_html()

generated = st.session_state.get("generated_outputs")
if generated:
    st.download_button(
        "Descarregar informe HTML",
        data=generated["report"],
        file_name=generated["report_name"],
        mime="text/html",
        type="primary",
        use_container_width=True,
    )
    if generated["hourly"] is not None:
        st.download_button(
            "Descarregar resultats horaris CSV",
            data=generated["hourly"],
            file_name=generated["hourly_name"],
            mime="text/csv",
            use_container_width=True,
        )
    if generated["daily"] is not None:
        st.download_button(
            "Descarregar resum diari CSV",
            data=generated["daily"],
            file_name=generated["daily_name"],
            mime="text/csv",
            use_container_width=True,
        )
