"""
Genera un informe HTML interactiu i modern amb els resultats de la
simulacio: targetes KPI, grafics interactius (Plotly) i diagnostic de
dimensionament de la bateria. Es un fitxer HTML autonom que s'obre amb
qualsevol navegador (no cal servidor).
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

CARD_CSS = """
<style>
  :root {
    --bg: #0f172a; --card-bg: #1e293b; --accent: #38bdf8; --accent2: #34d399;
    --warn: #fbbf24; --danger: #f87171; --text: #e2e8f0; --muted: #94a3b8;
  }
  * { box-sizing: border-box; }
  body {
    background: var(--bg); color: var(--text);
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    margin: 0; padding: 32px 5vw;
  }
  .top-header {
    padding: 12px 0 18px; border-bottom: 1px solid rgba(148, 163, 184, 0.25); margin-bottom: 18px;
  }
  h1 { font-size: 2rem; margin: 0 0 6px; letter-spacing: -0.03em; }
  .subtitle { color: var(--muted); margin-bottom: 26px; }
  .executive-summary {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin: 18px 0 12px;
  }
  .exec-card {
    background: linear-gradient(135deg, rgba(52, 211, 153, 0.08), rgba(15, 23, 42, 0.35));
    border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 12px; padding: 16px 18px;
  }
  .exec-card .label { color: var(--muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: .06em; }
  .exec-card .value { font-size: 1.35rem; font-weight: 700; margin-top: 6px; }
  h2 { font-size: 1.25rem; margin-top: 42px; color: var(--accent); font-weight: 700; }
  h3 { font-size: 1.1rem; margin-top: 28px; color: var(--text); font-weight: 600; }
  .kpi-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 16px; margin-bottom: 12px;
  }
  .kpi-card { background: var(--card-bg); border-radius: 14px; padding: 18px 20px; border: 1px solid #334155; }
  .kpi-card .label { color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: .04em; }
  .kpi-card .value { font-size: 1.6rem; font-weight: 700; margin-top: 4px; }
  .kpi-card .value.accent { color: var(--accent); }
  .kpi-card .value.accent2 { color: var(--accent2); }
  .kpi-card .value.warn { color: var(--warn); }
  .kpi-card .value.danger { color: var(--danger); }
  .chart-block { background: var(--card-bg); border-radius: 14px; padding: 10px; margin-bottom: 24px; border: 1px solid #334155; }
  .reco { background: #1e293b; border-left: 4px solid var(--accent); padding: 12px 18px; border-radius: 8px; margin: 8px 0; line-height: 1.5; }
  .metric-note {
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.10), rgba(15, 23, 42, 0.35));
    border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 12px; padding: 18px 20px; margin: 12px 0 18px; line-height: 1.7;
  }
  .metric-note strong { color: var(--accent); }
  .quality-row { display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0 8px; }
  .quality-tag { display: inline-block; padding: 6px 12px; border-radius: 999px; font-weight: 700; font-size: 0.8rem; letter-spacing: .03em; }
  .quality-good { background: rgba(52, 211, 153, 0.15); border: 1px solid rgba(52, 211, 153, 0.45); color: #a7f3d0; }
  .quality-medium { background: rgba(251, 191, 36, 0.12); border: 1px solid rgba(251, 191, 36, 0.45); color: #fcd34d; }
  .quality-low { background: rgba(248, 113, 113, 0.12); border: 1px solid rgba(248, 113, 113, 0.45); color: #fca5a5; }
  
  /* Taula estètica millorada */
  .thermal-table-container { overflow-x: auto; margin: 12px 0; }
  .thermal-table {
    width: 100%; border-collapse: collapse; text-align: left;
    background: var(--card-bg); border-radius: 10px; overflow: hidden;
  }
  .thermal-table thead { background: rgba(52, 211, 153, 0.15); border-bottom: 2px solid rgba(52, 211, 153, 0.35); }
  .thermal-table th {
    padding: 14px 16px; color: var(--accent2); font-weight: 700; font-size: 0.85rem;
    text-transform: uppercase; letter-spacing: 0.04em;
  }
  .thermal-table tbody tr {
    border-bottom: 1px solid rgba(148, 163, 184, 0.1); transition: background-color 0.2s ease;
  }
  .thermal-table tbody tr:hover { background: rgba(52, 211, 153, 0.05); }
  .thermal-table td {
    padding: 14px 16px; color: var(--text); font-size: 0.95rem;
  }
  .thermal-table td.numeric { text-align: right; font-family: 'Courier New', monospace; }
  .thermal-table .source-name { font-weight: 600; color: var(--accent); }
  .thermal-table .badge {
    display: inline-block; padding: 4px 10px; border-radius: 20px;
    font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.02em;
  }
  .thermal-table .badge.best { background: rgba(52, 211, 153, 0.25); color: #a7f3d0; border: 1px solid rgba(52, 211, 153, 0.45); }
  .thermal-table .badge.active { background: rgba(56, 189, 248, 0.25); color: #bfdbfe; border: 1px solid rgba(56, 189, 248, 0.45); }
    .thermal-table .badge.warning { background: rgba(251, 191, 36, 0.18); color: #fde68a; border: 1px solid rgba(251, 191, 36, 0.45); }
  
  /* Secció d'estalvi */
  .savings-section { background: linear-gradient(135deg, rgba(52, 211, 153, 0.1), rgba(56, 189, 248, 0.05)); 
                     border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 12px; padding: 24px; margin: 24px 0; }
  .savings-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 18px; margin-top: 18px; }
  .savings-card { background: var(--card-bg); border-radius: 10px; padding: 18px; border: 1px solid #334155; text-align: center; }
  .savings-card .label { color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px; }
  .savings-card .value { font-size: 1.8rem; font-weight: 700; margin: 6px 0; }
  .savings-card .unit { color: var(--muted); font-size: 0.85rem; font-weight: 500; }
  .savings-card .value.saving { color: var(--accent2); }
  .savings-card .value.loss { color: var(--danger); }
  .savings-card .value.economic { color: var(--accent); }
  
  /* Taula de comparativa */
  .comparison-table {
    width: 100%; border-collapse: collapse;
    background: var(--card-bg); border-radius: 10px; overflow: hidden;
    margin: 16px 0;
  }
  .comparison-table thead { background: rgba(56, 189, 248, 0.15); border-bottom: 2px solid rgba(56, 189, 248, 0.35); }
  .comparison-table th { padding: 12px; color: var(--accent); font-weight: 700; text-align: left; }
  .comparison-table td { padding: 12px; border-bottom: 1px solid rgba(148, 163, 184, 0.1); }
  .comparison-table .current { background: rgba(248, 113, 113, 0.1); color: var(--text); }
  .comparison-table .alternative { background: rgba(52, 211, 153, 0.1); color: var(--text); }
    .combined-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; margin: 18px 0; }
    .combined-highlight { background: var(--card-bg); border: 1px solid #334155; border-radius: 12px; padding: 16px; }
    .combined-highlight.primary { border-color: rgba(52, 211, 153, 0.65); background: rgba(52, 211, 153, 0.10); }
    .combined-highlight.efficiency { border-color: rgba(56, 189, 248, 0.65); background: rgba(56, 189, 248, 0.10); }
    .combined-highlight.reference { border-color: rgba(251, 191, 36, 0.55); background: rgba(251, 191, 36, 0.08); }
    .combined-highlight .highlight-label { color: var(--muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: .05em; }
    .combined-highlight .highlight-value { color: var(--text); font-size: 1.25rem; font-weight: 700; margin-top: 7px; }
    .combined-highlight .highlight-detail { color: var(--muted); font-size: 0.86rem; margin-top: 5px; }
    .combined-table-wrap { overflow-x: auto; margin: 16px 0; }
    .combined-table { width: 100%; min-width: 900px; border-collapse: collapse; background: var(--card-bg); border-radius: 10px; overflow: hidden; }
    .combined-table thead { background: rgba(56, 189, 248, 0.15); border-bottom: 2px solid rgba(56, 189, 248, 0.35); }
    .combined-table th { padding: 13px 14px; color: var(--accent); font-size: .78rem; text-transform: uppercase; letter-spacing: .04em; text-align: left; }
    .combined-table td { padding: 14px; border-bottom: 1px solid rgba(148, 163, 184, 0.12); color: var(--text); }
    .combined-table td.numeric { text-align: right; font-family: 'Courier New', monospace; white-space: nowrap; }
    .combined-table tr.recommended { background: rgba(52, 211, 153, 0.13); box-shadow: inset 4px 0 0 var(--accent2); }
    .combined-table tr.reference { background: rgba(251, 191, 36, 0.08); }
    .combined-table .positive { color: #86efac; font-weight: 700; }
    .combined-table .negative { color: #fca5a5; font-weight: 700; }
    .decision-badge { display: inline-block; margin-top: 6px; padding: 4px 8px; border-radius: 999px; font-size: .7rem; font-weight: 700; text-transform: uppercase; }
    .decision-badge.recommended { color: #a7f3d0; background: rgba(52, 211, 153, .20); border: 1px solid rgba(52, 211, 153, .45); }
    .decision-badge.reference { color: #fde68a; background: rgba(251, 191, 36, .16); border: 1px solid rgba(251, 191, 36, .42); }
  
  /* Resum del Sistema */
  .system-summary { display: flex; flex-direction: column; gap: 16px; margin: 18px 0; }
  .summary-section {
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.08), rgba(52, 211, 153, 0.05));
    border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 10px; padding: 18px;
  }
  .summary-section h3 { margin: 0 0 14px; font-size: 1rem; color: var(--accent); font-weight: 700; letter-spacing: 0.02em; }
  .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
  .summary-item {
    background: var(--card-bg); border: 1px solid #334155; border-radius: 8px;
    padding: 12px 14px;
  }
  .summary-item .summary-label {
    color: var(--muted); font-size: 0.75rem; text-transform: uppercase;
    letter-spacing: 0.04em; margin-bottom: 6px;
  }
  .summary-item .summary-value {
    color: var(--text); font-size: 1.1rem; font-weight: 700;
  }
</style>
"""


def _kpi(label, value, css_class="accent"):
    return f'<div class="kpi-card"><div class="label">{label}</div><div class="value {css_class}">{value}</div></div>'


def _quality_band(value, low, high):
    if value >= high:
        return "Excel·lent", "quality-good"
    if value >= low:
        return "Acceptable", "quality-medium"
    return "Millorable", "quality-low"


def _executive_summary(summary, economic_summary):
    auto = float(summary.get("self_consumption_rate", 0.0))
    suff = float(summary.get("self_sufficiency_rate", 0.0))
    annual_cashflow = float(economic_summary.get("annual_cashflow", 0.0))
    payback = economic_summary.get("payback_years")

    key_message = "Rendiment general correcte, amb marge de millora en l'optimització del consum a les hores de sol."
    if auto >= 70 and suff >= 80:
        key_message = "Sistema ben ajustat i eficient: l'energia generada es consumeix pràcticament en el moment de producció."
    elif annual_cashflow < 0:
        key_message = "L'escenari és poc atractiu econòmicament i cal revisar cost, dimensionament o perfil de consum."

    payback_text = "no viable" if payback is None else f"{payback:.1f} anys"
    return f"""
    <div class="executive-summary">
      <div class="exec-card"><div class="label">Autoconsum</div><div class="value">{auto:.1f}%</div></div>
      <div class="exec-card"><div class="label">Autosuficiència</div><div class="value">{suff:.1f}%</div></div>
      <div class="exec-card"><div class="label">Flux net anual</div><div class="value">{annual_cashflow:.0f} €</div></div>
      <div class="exec-card"><div class="label">Payback</div><div class="value">{payback_text}</div></div>
    </div>
    <div class="reco">{key_message}</div>
    """


def _autoconsumption_narrative(summary):
    auto = float(summary.get("self_consumption_rate", 0.0))
    suff = float(summary.get("self_sufficiency_rate", 0.0))
    export = float(summary.get("total_export", 0.0))
    import_kwh = float(summary.get("total_import", 0.0))

    def fmt(v):
        return f"{v:.1f}%"

    auto_state, auto_class = _quality_band(auto, 50, 75)
    suff_state, suff_class = _quality_band(suff, 55, 80)

    definition = (
        "L'autoconsum indica quanta de la producció fotovoltaica s'aprofita a la mateixa casa; "
        "l'autosuficiència indica quanta part del consum total queda coberta amb energia pròpia."
    )

    if auto < 70 or suff < 80:
        actions = []
        if export > 0:
            actions.append("desplaçar consum flexible a les hores de sol (bomba de calor, llavatge, rentavaixelles, càrrega del vehicle, climatització)")
        if import_kwh > 0:
            actions.append("reduir la importació nocturna amb un millor encaix entre consum i producció, i valorar bateries o gestió intel·ligent")
        if auto < 70:
            actions.append("revisar el dimensionament FV i l'ús de la producció perquè no s'exporti tant a la xarxa")
        recommendation = "La millora principal és ajustar el consum a les hores de producció solar i, si cal, complementar-ho amb bateries o estratègies de gestió de càrregues per evitar exportacions i importacions innecessàries."
    else:
        actions = ["el sistema ja està molt ben ajustat; mantenir el patró de consum i monitoritzar l'estat de la bateria o de la producció"]
        recommendation = "No hi ha marge de millora molt important; el principal objectiu és mantenir un bon encaix entre producció i consum i evitar pèrdues per sobreproducció o operacions innecessàries."

    return f"""
    <div class="metric-note">
      <strong>Autoconsum:</strong> mesura quina fracció de la producció FV s'utilitza directament al lloc. <strong>Autosuficiència:</strong> mesura quina fracció del consum total es cobreix amb la pròpia energia solar.<br>
      <strong>Valoració:</strong> l'autoconsum és <b>{fmt(auto)}</b> i l'autosuficiència és <b>{fmt(suff)}</b>. Es considera <span class="quality-tag {auto_class}">{auto_state}</span> per a l'autoconsum i <span class="quality-tag {suff_class}">{suff_state}</span> per a l'autosuficiència. {definition}<br>
      <div class="quality-row">
        <span class="quality-tag quality-good">Excel·lent</span>
        <span class="quality-tag quality-medium">Acceptable</span>
        <span class="quality-tag quality-low">Millorable</span>
      </div>
      <strong>Recomanació:</strong> {recommendation} Les accions més efectives són: {', '.join(actions)}.
    </div>
    """


def _thermal_section(thermal_summary):
    if not thermal_summary:
        return ""
    recommendation = thermal_summary.get("recommended")
    best_cost = thermal_summary.get("best_cost")
    best_env = thermal_summary.get("best_environment")
    best_energy = thermal_summary.get("best_energy")
    active_source = thermal_summary.get("active_source")
    pv_alternatives = thermal_summary.get("electric_alternatives_with_pv", [])
    payback_reference_key = thermal_summary.get("payback_reference")
    payback_reference = next(
        (item for item in thermal_summary.get("sources", []) if item["source_key"] == payback_reference_key),
        None,
    )
    payback_reference_name = payback_reference["source_name"] if payback_reference else "referència configurada"
    
    # Generar taula de comparativa principal
    rows = []
    for item in thermal_summary.get("sources", []):
        badges = ""
        low_efficiency = item["source_key"] == "electricitat_resistencia"
        if recommendation and item["source_key"] == recommendation["source_key"]:
            badges += '<span class="badge best">✓ Recomanat</span> '
        if best_cost and item["source_key"] == best_cost["source_key"]:
            badges += '<span class="badge best">💰 Menys cost</span> '
        if best_env and item["source_key"] == best_env["source_key"]:
            badges += '<span class="badge best">🌱 Menys emissions</span> '
        if active_source and item["source_key"] == active_source["source_key"]:
            badges += '<span class="badge active">● Activa</span> '
        if low_efficiency:
            badges += '<span class="badge warning">⚠ Referència, baixa eficiència</span> '
        
        if item["source_key"] == payback_reference_key:
            payback_text = "Referència"
        else:
            payback_text = f"{item.get('payback_years'):.1f} anys" if item.get('payback_years') is not None else "No viable"
        row = f"""<tr>
            <td class="source-name">{item['source_name']}{' <br/>' + badges if badges else ''}</td>
            <td class="numeric">{item['performance']:.2f}</td>
            <td class="numeric">{item['input_energy_kwh']:.0f}</td>
            <td class="numeric">{item['primary_energy_total_kwh']:.0f}</td>
            <td class="numeric">{item['primary_energy_nonrenewable_kwh']:.0f}</td>
            <td class="numeric">{item['emissions_kg_co2e']:.0f}</td>
            <td class="numeric">{item['annual_total_cost_eur']:.0f}</td>
            <td class="numeric">{item['capex_eur']:.0f}</td>
            <td class="numeric">{item['annualized_total_cost_eur']:.0f}</td>
            <td class="numeric">{payback_text}</td>
        </tr>"""
        rows.append(row)
    
    rows_html = "".join(rows)
    recommendation_text = recommendation["source_name"] if recommendation else "-"
    
    active_text = ""
    if active_source:
        active_text = (
            f"<strong>Font activa simulada:</strong> {active_source['source_name']} "
            f"({active_source.get('pv_thermal_electricity_kwh', 0.0):.0f} kWh elèctrics/any integrats al consum)"
        )
    
    pv_alternatives_html = ""
    if pv_alternatives:
        alt_rows = []
        for item in pv_alternatives:
            alt_rows.append(f"""<tr>
                <td class="source-name">{item['source_name']}</td>
                <td class="numeric">{item['electricity_total_kwh']:.0f}</td>
                <td class="numeric">{item['grid_import_kwh']:.0f}</td>
                <td class="numeric">{item['grid_export_kwh']:.0f}</td>
                <td class="numeric">{item['system_energy_cost_eur']:.0f}</td>
            </tr>""")
        pv_alternatives_html = f"""
        <h3>Alternatives elèctriques amb plaques FV existents</h3>
        <div class="metric-note">Cada alternativa reutilitza la FV, el consum domèstic i la bateria configurats. El cost és la factura elèctrica neta estimada (importacions menys ingressos d'excedents) més operació i manteniment tèrmic; no inclou CAPEX de FV, bateria ni calefacció.</div>
        <div class="chart-block">
            <div class="thermal-table-container">
                <table class="thermal-table">
                    <thead>
                        <tr>
                            <th>Alternativa</th>
                            <th>Consum elèctric tèrmic (kWh)</th>
                            <th>Importació xarxa (kWh)</th>
                            <th>Excedent FV (kWh)</th>
                            <th>Cost anual net del sistema (€)</th>
                        </tr>
                    </thead>
                    <tbody>{"".join(alt_rows)}</tbody>
                </table>
            </div>
        </div>"""
    
    return f"""
    <h2>Fonts de calor i fred</h2>
    <div class="metric-note">
      Demanda termica anual: <strong>{thermal_summary['heat_demand_kwh']:.0f} kWh</strong> |
      Recomanacio ponderada: <strong>{recommendation_text}</strong>
      {f'| {active_text}' if active_text else ''}
            <br><strong>Com llegir aquesta comparativa:</strong> la recomanació ponderada combina cost anualitzat, emissions i energia no renovable; <strong>Menys cost</strong> identifica només la millor opció econòmica.
            El CAPEX i els costos d'aquesta taula corresponen només a calefacció (no inclouen FV ni bateria). El cost anualitzat suma operació, manteniment i CAPEX amortitzat durant {thermal_summary.get('analysis_years', 20)} anys.
            El payback compara cada alternativa amb <strong>{payback_reference_name}</strong> i considera l'estalvi operatiu i el CAPEX tèrmic addicional. La resistència elèctrica es mostra com a referència de baixa eficiència (COP 1,00).
    </div>
    
    <h3>Comparativa de fonts tèrmiques</h3>
    <div class="chart-block">
        <div class="thermal-table-container">
            <table class="thermal-table">
                <thead>
                    <tr>
                        <th>Font</th>
                        <th>COP/η</th>
                        <th>Entrada (kWh)</th>
                        <th>Primaria total (kWh)</th>
                        <th>Primaria no renovable (kWh)</th>
                        <th>Emissions (kg CO2e)</th>
                        <th>Operació + manteniment (€/any)</th>
                        <th>CAPEX calefacció (€; sense FV/bateria)</th>
                        <th>Cost anualitzat (€/any)</th>
                        <th>Payback vs {payback_reference_name}</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
    </div>
    {pv_alternatives_html}
    """


def _geothermal_design_section(thermal_summary):
    """Mostra el dimensionament geotèrmic del cas actual, amb dades modificables a config.py."""
    if not thermal_summary:
        return ""

    geothermal_design = thermal_summary.get("geothermal_design")
    if not geothermal_design:
        return ""

    return f"""
    <h2>Dimensionament geotèrmic</h2>
    <div class="metric-note">
      <strong>Cas actual:</strong> {geothermal_design.get('case_name', 'Ubicació no definida')}<br>
      <strong>Font de dades geològiques:</strong> conductivitat, difusivitat, temperatura del sòl i nivell freàtic es poden obtenir del ICGC o d'un estudi geotècnic local. Els valors es poden modificar directament a <strong>config.py</strong>.<br>
      <strong>Hipòtesi de calefacció:</strong> consigna interior de {geothermal_design.get('indoor_setpoint_c', 22.0):.1f} °C i temperatura de circuit de terra de {geothermal_design.get('ground_loop_target_temp_c', 8.0):.1f} °C.
    </div>
    <div class="chart-block">
        <div class="thermal-table-container">
            <table class="thermal-table">
                <thead>
                    <tr>
                        <th>Paràmetre</th>
                        <th>Valor</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>Temperatura mitjana del sòl</td><td class="numeric">{geothermal_design.get('mean_ground_temp_c', 0.0):.1f} °C</td></tr>
                    <tr><td>Conductivitat tèrmica del sòl</td><td class="numeric">{geothermal_design.get('thermal_conductivity_w_mk', 0.0):.2f} W/m·K</td></tr>
                    <tr><td>Difusivitat tèrmica</td><td class="numeric">{geothermal_design.get('thermal_diffusivity_m2_s', 0.0):.3e} m²/s</td></tr>
                    <tr><td>Temperatura de treball del circuit</td><td class="numeric">{geothermal_design.get('ground_loop_target_temp_c', 0.0):.1f} °C</td></tr>
                    <tr><td>ΔT útil</td><td class="numeric">{geothermal_design.get('delta_t_c', 0.0):.1f} °C</td></tr>
                    <tr><td>Càrrega tèrmica de disseny</td><td class="numeric">{geothermal_design.get('design_peak_kw', 0.0):.1f} kW</td></tr>
                    <tr><td>Flux tèrmic per metre</td><td class="numeric">{geothermal_design.get('heat_flux_w_per_m', 0.0):.1f} W/m</td></tr>
                    <tr><td>Longitud requerida</td><td class="numeric">{geothermal_design.get('required_length_m', 0.0):.0f} m</td></tr>
                    <tr><td>Profunditat per pou</td><td class="numeric">{geothermal_design.get('borehole_depth_m', 0.0):.0f} m</td></tr>
                    <tr><td>Nombre de pous</td><td class="numeric">{geothermal_design.get('boreholes_count', 0)}</td></tr>
                    <tr><td>Longitud total de buits</td><td class="numeric">{geothermal_design.get('total_loop_length_m', 0.0):.0f} m</td></tr>
                    <tr><td>Cost estimat de perforació i sondes</td><td class="numeric">{geothermal_design.get('estimated_drilling_capex_eur', 0.0):.0f} €</td></tr>
                    <tr><td>Equip geotèrmic (bomba de calor i sistema)</td><td class="numeric">{geothermal_design.get('estimated_heat_pump_capex_eur', 0.0):.0f} €</td></tr>
                    <tr><td>CAPEX tèrmic geotèrmic estimat (sense FV/bateria)</td><td class="numeric">{geothermal_design.get('estimated_capex_eur', 0.0):.0f} €</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    <div class="reco">{geothermal_design.get('note', '')}</div>
    """


def _thermal_savings_section(thermal_summary):
    """Genera secció de comparativa d'estalvi entre la font actual i la millor alternativa."""
    if not thermal_summary or not thermal_summary.get("sources"):
        return ""
    
    active_source = thermal_summary.get("active_source")
    recommended = thermal_summary.get("recommended")
    
    if not active_source or not recommended or active_source["source_key"] == recommended["source_key"]:
        return ""
    
    current = active_source
    best = recommended
    
    # Calcular estalvis
    annual_cost_saving = current["annual_total_cost_eur"] - best["annual_total_cost_eur"]
    annualized_cost_saving = current["annualized_total_cost_eur"] - best["annualized_total_cost_eur"]
    emissions_saving = current["emissions_kg_co2e"] - best["emissions_kg_co2e"]
    energy_saving = current["primary_energy_nonrenewable_kwh"] - best["primary_energy_nonrenewable_kwh"]
    additional_capex = best["capex_eur"] - current["capex_eur"]
    
    years = int(thermal_summary.get("analysis_years", 20))
    total_cost_saving_20y = annual_cost_saving * years - additional_capex
    total_emissions_saved_20y = emissions_saving * years
    total_energy_saved_20y = energy_saving * years

    roi_pct = total_cost_saving_20y / additional_capex * 100 if additional_capex > 0 else None
    payback_years = additional_capex / annual_cost_saving if annual_cost_saving > 0 and additional_capex > 0 else None
    
    # Determine color and mood based on savings
    cost_class = "saving" if annual_cost_saving > 0 else "loss"
    env_class = "saving" if emissions_saving > 0 else "loss"
    energy_class = "saving" if energy_saving > 0 else "loss"
    
    payback_text = f"{payback_years:.1f} anys" if payback_years is not None else "No hi ha retorn econòmic"
    roi_text = f"{roi_pct:.0f}%" if roi_pct is not None else "N/A"
    
    recommendation_msg = ""
    if annual_cost_saving > 0 and emissions_saving > 0:
        recommendation_msg = f"<strong>✓ Resultat:</strong> {best['source_name']} redueix costos d'operació en {annual_cost_saving:.0f} €/any i emissions en {emissions_saving:.0f} kg CO2e/any. El balanç net a {years} anys, incloent la diferència de CAPEX, és {total_cost_saving_20y:+.0f} €."
    elif annual_cost_saving > 0:
        recommendation_msg = f"<strong>⚠ Resultat:</strong> {best['source_name']} estalvia {annual_cost_saving:.0f} €/any en operació i manteniment, però podria tenir altres implicacions. El balanç net a {years} anys, incloent la diferència de CAPEX, és {total_cost_saving_20y:+.0f} €."
    elif emissions_saving > 0:
        recommendation_msg = f"<strong>🌱 Resultat ambiental:</strong> {best['source_name']} redueix emissions en {emissions_saving:.0f} kg CO2e/any, però augmenta el cost d'operació i manteniment en {abs(annual_cost_saving):.0f} €/any. El balanç net a {years} anys, incloent la diferència de CAPEX, és {total_cost_saving_20y:+.0f} €."
    else:
        recommendation_msg = f"<strong>ℹ Info:</strong> La font actual ja és una bona solució. No hi ha millores significatives disponibles."
    
    return f"""
    <h2>Análisis d'estalvi: Canvi de tecnologia de calefacció</h2>
    <div class="savings-section">
        <div>
            <h3>Comparativa: sistema actiu {current['source_name']} → alternativa amb millor puntuació global {best['source_name']}</h3>
            <div class="metric-note">
                La millor puntuació combina cost anualitzat, emissions i energia no renovable; no vol dir necessàriament que sigui l'alternativa més barata. Els estalvis són sistema actiu menys alternativa. El CAPEX és només de calefacció, sense FV ni bateria.
            </div>
        </div>
        
        <div class="savings-grid">
            <div class="savings-card">
                <div class="label">Estalvi econòmic anual</div>
                <div class="value {cost_class}">{annual_cost_saving:+.0f} €</div>
                <div class="unit">€/any (operació + manteniment)</div>
            </div>
            <div class="savings-card">
                <div class="label">Estalvi energètic anual</div>
                <div class="value {energy_class}">{energy_saving:+.0f} kWh</div>
                <div class="unit">Primaria no renovable/any</div>
            </div>
            <div class="savings-card">
                <div class="label">Reducció d'emissions anual</div>
                <div class="value {env_class}">{emissions_saving:+.0f} kg CO2e</div>
                <div class="unit">Emissions CO2 evitades/any</div>
            </div>
            <div class="savings-card">
                <div class="label">Inversió addicional</div>
                <div class="value economic">{additional_capex:+.0f} €</div>
                <div class="unit">Cost inicial capex</div>
            </div>
            <div class="savings-card">
                <div class="label">Balanç net a {years} anys</div>
                <div class="value saving">{total_cost_saving_20y:+.0f} €</div>
                <div class="unit">Estalvi operatiu acumulat menys CAPEX addicional</div>
            </div>
            <div class="savings-card">
                <div class="label">Retorn del CAPEX addicional</div>
                <div class="value economic">{payback_text}</div>
                <div class="unit">Payback period</div>
            </div>
            <div class="savings-card">
                <div class="label">CO2 evitat ({years} anys)</div>
                <div class="value saving">{total_emissions_saved_20y:+.0f} kg</div>
                <div class="unit">Tons de CO2e evitades</div>
            </div>
            <div class="savings-card">
                <div class="label">ROI a {years} anys</div>
                <div class="value economic">{roi_text}</div>
                <div class="unit">Return on investment</div>
            </div>
        </div>
        
        <div class="reco">
            {recommendation_msg}
        </div>
        
        <h3>Detalls de la comparativa</h3>
        <table class="comparison-table">
            <thead>
                <tr>
                    <th>Paràmetre</th>
                    <th class="current">Tecnologia actual ({current['source_name']})</th>
                    <th class="alternative">Alternativa recomanada ({best['source_name']})</th>
                    <th>Alternativa - actual</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>COP / Rendiment</strong></td>
                    <td class="current numeric">{current['performance']:.2f}</td>
                    <td class="alternative numeric">{best['performance']:.2f}</td>
                    <td class="numeric">{best['performance'] - current['performance']:+.2f}</td>
                </tr>
                <tr>
                    <td><strong>Cost operació anual</strong></td>
                    <td class="current numeric">{current['annual_total_cost_eur']:.0f} €</td>
                    <td class="alternative numeric">{best['annual_total_cost_eur']:.0f} €</td>
                    <td class="numeric">{best['annual_total_cost_eur'] - current['annual_total_cost_eur']:+.0f} €</td>
                </tr>
                <tr>
                    <td><strong>Cost anualitzat (incl. amortització)</strong></td>
                    <td class="current numeric">{current['annualized_total_cost_eur']:.0f} €</td>
                    <td class="alternative numeric">{best['annualized_total_cost_eur']:.0f} €</td>
                    <td class="numeric">{best['annualized_total_cost_eur'] - current['annualized_total_cost_eur']:+.0f} €</td>
                </tr>
                <tr>
                    <td><strong>CAPEX calefacció (sense FV/bateria)</strong></td>
                    <td class="current numeric">{current['capex_eur']:.0f} €</td>
                    <td class="alternative numeric">{best['capex_eur']:.0f} €</td>
                    <td class="numeric">{best['capex_eur'] - current['capex_eur']:+.0f} €</td>
                </tr>
                <tr>
                    <td><strong>Emissions CO2 anuals</strong></td>
                    <td class="current numeric">{current['emissions_kg_co2e']:.0f} kg</td>
                    <td class="alternative numeric">{best['emissions_kg_co2e']:.0f} kg</td>
                    <td class="numeric">{best['emissions_kg_co2e'] - current['emissions_kg_co2e']:+.0f} kg</td>
                </tr>
                <tr>
                    <td><strong>Energia primaria no renovable</strong></td>
                    <td class="current numeric">{current['primary_energy_nonrenewable_kwh']:.0f} kWh</td>
                    <td class="alternative numeric">{best['primary_energy_nonrenewable_kwh']:.0f} kWh</td>
                    <td class="numeric">{best['primary_energy_nonrenewable_kwh'] - current['primary_energy_nonrenewable_kwh']:+.0f} kWh</td>
                </tr>
                <tr>
                    <td><strong>Energia primaria renovable</strong></td>
                    <td class="current numeric">{current['renewable_primary_kwh']:.0f} kWh</td>
                    <td class="alternative numeric">{best['renewable_primary_kwh']:.0f} kWh</td>
                    <td class="numeric">{best['renewable_primary_kwh'] - current['renewable_primary_kwh']:+.0f} kWh</td>
                </tr>
            </tbody>
        </table>
    </div>
    """




def _system_summary_section(config):
    """Genera secció de resum dels paràmetres principals del sistema."""
    if config is None:
        return ""
    
    # Accedir als atributs del mòdul config
    location = getattr(config, "LOCATION", {})
    pv_system = getattr(config, "PV_SYSTEM", {})
    consumption = getattr(config, "CONSUMPTION", {})
    battery = getattr(config, "BATTERY", {})
    thermal = getattr(config, "THERMAL", {})
    economy = getattr(config, "ECONOMY", {})
    
    # Paràmetres principals
    location_name = location.get("name", "No definida") if isinstance(location, dict) else "No definida"
    latitude = location.get("lat", "-") if isinstance(location, dict) else "-"
    longitude = location.get("lon", "-") if isinstance(location, dict) else "-"
    climate = location.get("climate", {}) if isinstance(location, dict) else {}
    ground = location.get("ground", {}) if isinstance(location, dict) else {}
    mean_air_temp = climate.get("mean_annual_air_temp_c", "-") if isinstance(climate, dict) else "-"
    winter_temp = climate.get("winter_design_temp_c", "-") if isinstance(climate, dict) else "-"
    soil_conductivity = ground.get("thermal_conductivity_w_mk", "-") if isinstance(ground, dict) else "-"
    
    pv_power = pv_system.get("peak_power_kwp", 0) if isinstance(pv_system, dict) else 0
    num_panels = round(pv_power / 0.4) if pv_power > 0 else 0  # assumint panells de 400W
    tilt = pv_system.get("tilt_deg", "-") if isinstance(pv_system, dict) else "-"
    azimuth = pv_system.get("azimuth_deg", "-") if isinstance(pv_system, dict) else "-"
    
    annual_consumption = consumption.get("annual_kwh", 0) if isinstance(consumption, dict) else 0
    
    battery_enabled = battery.get("enabled", False) if isinstance(battery, dict) else False
    battery_capacity = battery.get("capacity_kwh", 0) if (isinstance(battery, dict) and battery_enabled) else 0
    battery_power = battery.get("max_charge_kw", 0) if (isinstance(battery, dict) and battery_enabled) else 0
    
    thermal_enabled = thermal.get("enabled", False) if isinstance(thermal, dict) else False
    thermal_demand = thermal.get("annual_heat_demand_kwh", 0) if (isinstance(thermal, dict) and thermal_enabled) else 0
    active_thermal_source = thermal.get("active_source", "No configurada") if (isinstance(thermal, dict) and thermal_enabled) else "No configurada"
    
    # Convertir nom de font termica a readable
    thermal_source_names = {
        "gas_natural": "Gas natural",
        "gasoil": "Gasoil",
        "aerotermia": "Aerotermia",
        "geotermia": "Geotermia",
        "biomassa": "Biomassa (pellet)",
        "electricitat_resistencia": "Electricitat (resistència)",
    }
    thermal_source_display = thermal_source_names.get(active_thermal_source, active_thermal_source)
    
    buy_price = economy.get("electricity_buy_price_eur_kwh", 0) if isinstance(economy, dict) else 0
    sell_price = economy.get("electricity_sell_price_eur_kwh", 0) if isinstance(economy, dict) else 0
    
    # Determinar azimuth descriptiu
    azimuth_desc = ""
    if azimuth == 0:
        azimuth_desc = " (Sud)"
    elif azimuth == -90:
        azimuth_desc = " (Est)"
    elif azimuth == 90:
        azimuth_desc = " (Oest)"
    elif azimuth == 180 or azimuth == -180:
        azimuth_desc = " (Nord)"
    
    return f"""
    <h2>Resum del Sistema</h2>
    <div class="system-summary">
        <div class="summary-section">
            <h3>🏠 Ubicació i Client</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-label">Ubicació</div>
                    <div class="summary-value">{location_name}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Coordenades</div>
                    <div class="summary-value">{latitude:.4f}° N, {longitude:.4f}° E</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Temp. mitjana anual</div>
                    <div class="summary-value">{mean_air_temp} °C</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Temp. disseny hivern</div>
                    <div class="summary-value">{winter_temp} °C</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Conductivitat del sòl</div>
                    <div class="summary-value">{soil_conductivity} W/m·K</div>
                </div>
            </div>
        </div>
        
        <div class="summary-section">
            <h3>☀️ Sistema Fotovoltaic</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-label">Potència instal·lada</div>
                    <div class="summary-value">{pv_power:.1f} kWp</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Nombre de panells (estimat)</div>
                    <div class="summary-value">{num_panels} unitats (~400W/u)</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Inclinació</div>
                    <div class="summary-value">{tilt}°</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Orientació</div>
                    <div class="summary-value">{azimuth}°{azimuth_desc}</div>
                </div>
            </div>
        </div>
        
        <div class="summary-section">
            <h3>⚡ Consum i Bateria</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-label">Consum anual estimat</div>
                    <div class="summary-value">{annual_consumption:,.0f} kWh</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Consum diari mitjà</div>
                    <div class="summary-value">{annual_consumption / 365:.1f} kWh</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Bateria instal·lada</div>
                    <div class="summary-value">{'Sí: ' + f'{battery_capacity:.1f} kWh' if battery_enabled else 'No'}</div>
                </div>
                {f'<div class="summary-item"><div class="summary-label">Potència bateria</div><div class="summary-value">{battery_power:.1f} kW</div></div>' if battery_enabled else ''}
            </div>
        </div>
        
        <div class="summary-section">
            <h3>🔥 Calefacció i Refrigeració</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-label">Demanda tèrmica anual</div>
                    <div class="summary-value">{thermal_demand:,.0f} kWh</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Mètode actiu</div>
                    <div class="summary-value">{thermal_source_display}</div>
                </div>
            </div>
        </div>
        
        <div class="summary-section">
            <h3>💰 Paràmetres Econòmics</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-label">Preu compra electricitat</div>
                    <div class="summary-value">{buy_price:.3f} €/kWh</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Preu venda excedents</div>
                    <div class="summary-value">{sell_price:.3f} €/kWh</div>
                </div>
            </div>
        </div>
    </div>
    """




def _personalized_analysis(thermal_summary, summary, economic_summary, config):
    """Genera un text personalitzat d'anàlisi i recomanacions."""
    if not thermal_summary:
        return ""
    
    active_source = thermal_summary.get("active_source")
    recommended = thermal_summary.get("recommended")
    best_cost = thermal_summary.get("best_cost")
    best_env = thermal_summary.get("best_environment")
    
    if not active_source:
        return ""
    
    active_name = active_source.get("source_name", "desconeguda")
    rec_name = recommended.get("source_name", "desconeguda") if recommended else "desconeguda"
    
    # Calcular estalvis
    annual_cost_diff = active_source.get("annual_total_cost_eur", 0) - recommended.get("annual_total_cost_eur", 0) if recommended else 0
    emissions_diff = active_source.get("emissions_kg_co2e", 0) - recommended.get("emissions_kg_co2e", 0) if recommended else 0
    energy_diff = active_source.get("primary_energy_nonrenewable_kwh", 0) - recommended.get("primary_energy_nonrenewable_kwh", 0) if recommended else 0
    capex_diff = recommended.get("capex_eur", 0) - active_source.get("capex_eur", 0) if recommended else 0
    
    # Dades FV i bateria
    pv_power = getattr(config, "PV_SYSTEM", {}).get("peak_power_kwp", 0) if hasattr(config, "PV_SYSTEM") else 0
    battery_enabled = getattr(config, "BATTERY", {}).get("enabled", False) if hasattr(config, "BATTERY") else False
    battery_capacity = getattr(config, "BATTERY", {}).get("capacity_kwh", 0) if battery_enabled else 0
    
    self_consumption_rate = float(summary.get("self_consumption_rate", 0))
    self_sufficiency_rate = float(summary.get("self_sufficiency_rate", 0))
    payback_years = economic_summary.get("payback_years")
    
    # Determinar si és necessari el canvi
    should_change = annual_cost_diff > 0 or emissions_diff > 100  # estalvi > 100€/any o > 100 kg CO2
    
    analysis_text = f"""
    <h2>Análisis Personalitzat i Recomanacions</h2>
    <div class="metric-note">
        <p>
            <strong>Sistema actual:</strong> Actualment, la instal·lació utilitza <strong>{active_name}</strong> com a font de calefacció per cobrir una demanda anual de {thermal_summary.get('heat_demand_kwh', 0):.0f} kWh. 
            El sistema fotovoltaic instal·lat de <strong>{pv_power} kWp</strong> genera una producció anual de <strong>{summary.get('total_pv', 0):.0f} kWh</strong>, 
            amb una taxa d'autoconsum del <strong>{self_consumption_rate:.1f}%</strong> i autosuficiència del <strong>{self_sufficiency_rate:.1f}%</strong>.
            {'La bateria de ' + f'{battery_capacity} kWh' if battery_enabled else 'No disposa de sistema de bateria'} 
            {'ajuda a emmagatzemar energia i millorar l\'autosuficiència.' if battery_enabled else 'limita la capacitat d\'emmagatzematge i autosuficiència.'}
        </p>
    """
    
    if should_change and recommended:
        rec_cost = recommended.get("annual_total_cost_eur", 0)
        rec_emissions = recommended.get("emissions_kg_co2e", 0)
        rec_performance = recommended.get("performance", 0)
        
        analysis_text += f"""
        <p>
            <strong style="color: var(--accent2);">✓ Anàlisis de Canvi Recomanat:</strong><br>
            La font recomanada és <strong>{rec_name}</strong> (COP/η = {rec_performance:.2f}), que ofereix millors prestacions tant econòmicament com ambientalment.
        </p>
        <ul style="line-height: 1.8;">
            <li><strong>Avantatge econòmic:</strong> Estalviaria <strong>{abs(annual_cost_diff):.0f} €/any</strong> en costos operatius i manteniment.</li>
            <li><strong>Avantatge ambiental:</strong> Reduiria les emissions en <strong>{abs(emissions_diff):.0f} kg CO2e/any</strong> 
                ({abs(emissions_diff) * 20:.0f} kg CO2e en 20 anys).</li>
            <li><strong>Millora energètica:</strong> Disminuiria el consum d'energia primaria no renovable en <strong>{abs(energy_diff):.0f} kWh/any</strong>.</li>
        """
        
        if capex_diff > 0:
            payback = capex_diff / annual_cost_diff if annual_cost_diff > 0 else 0
            analysis_text += f"""
            <li><strong>Inversió adicional:</strong> Requeriria una inversió inicial de <strong>{capex_diff:.0f} €</strong>, 
                que es recuperaria en aproximadament <strong>{payback:.1f} anys</strong>.</li>
            """
        
        analysis_text += """
        </ul>
        """
    
    # Analizar l'impacte de la FV i bateria
    analysis_text += f"""
        <p style="margin-top: 18px;">
            <strong style="color: var(--accent);">Consideracions sobre el Sistema Fotovoltaic i Bateria:</strong><br>
    """
    
    if self_sufficiency_rate < 60:
        analysis_text += f"""
            El sistema FV de {pv_power} kWp proporciona una autosuficiència del {self_sufficiency_rate:.1f}%, 
            el que significa que només cobreix una part del consum total de l'habitatge. 
            {'Per a assolir major independència de la xarxa, caldria augmentar la capacitat FV o la bateria.' if not battery_enabled else 
             f'Tot i disposar de bateria ({battery_capacity} kWh), la capacitat és limitada. Es recomana estudiar augmentar la capacitat de bateria o la potència FV.'}
        """
    else:
        analysis_text += f"""
            El sistema FV de {pv_power} kWp amb autosuficiència del {self_sufficiency_rate:.1f}% 
            {'juntament amb la bateria de ' + f'{battery_capacity} kWh' if battery_enabled else ''} 
            proporciona una bona cobertura del consum. 
            Aquesta capacitat de generació local és especialment valuosa si es complementa amb una font tèrmica eficient.
        """
    
    analysis_text += """
        </p>
    """
    
    # Recomanació final
    if should_change and recommended:
        payback_rec = recommended.get("payback_years", None)
        analysis_text += f"""
        <p style="margin-top: 18px; padding: 12px; background: rgba(52, 211, 153, 0.1); border-left: 4px solid var(--accent2); border-radius: 4px;">
            <strong style="color: var(--accent2);">🎯 Recomanació Final:</strong><br>
            Basant-nos en l'anàlisi integrat del sistema fotovoltaic, bateria i calefacció, es recomana <strong>estudiar la substitució de {active_name} per {rec_name}</strong>. 
            Això no només milloraria la rendibilitat de la inversió (payback de {payback_rec:.1f} anys), 
            sinó que reduiria significativament l'impacte ambiental i optimitzaria la complementarietat amb el sistema de generació renovable instal·lat.
            {'La bateria actual facilitaria aquesta transició emmagatzemant energia addicional que podria provenir de la demanda tèrmica.' if battery_enabled else ''}
        </p>
        """
    else:
        analysis_text += f"""
        <p style="margin-top: 18px; padding: 12px; background: rgba(56, 189, 248, 0.1); border-left: 4px solid var(--accent); border-radius: 4px;">
            <strong style="color: var(--accent);">ℹ️ Observació:</strong><br>
            La font de calefacció actual ({active_name}) ja és una solució adequada o la millor disponible segons els criteris d'anàlisi. 
            El focus hauria d'estar en optimitzar el sistema fotovoltaic i bateria per maximitzar l'autosuficiència.
        </p>
        """
    
    analysis_text += """
    </div>
    """
    
    return analysis_text


def _thermal_comparison_charts(thermal_summary):
    """Genera gràfics de comparativa d'alternatives vs sistema actual."""
    if not thermal_summary or not thermal_summary.get("sources"):
        return ""
    
    active_source = thermal_summary.get("active_source")
    if not active_source:
        return ""
    
    sources = thermal_summary["sources"]
    names = [item["source_name"] for item in sources]
    active_key = active_source.get("source_key")
    
    # Marcar el sistema actual amb color diferent
    colors_env = ["#f87171" if item["source_key"] == active_key else "#38bdf8" for item in sources]
    colors_econ = ["#fbbf24" if item["source_key"] == active_key else "#34d399" for item in sources]
    colors_energy = ["#f87171" if item["source_key"] == active_key else "#38bdf8" for item in sources]
    
    # 1. Gràfic comparativa ambiental (Emissions + Energia primaria no renovable)
    fig_env = go.Figure()
    fig_env.add_bar(x=names, y=[item["emissions_kg_co2e"] for item in sources],
                    name="Emissions CO2e (kg/any)", marker_color=colors_env, marker_line_width=2,
                    marker_line_color=['#ff6b6b' if item["source_key"] == active_key else '#cbd5e1' for item in sources])
    fig_env.add_scatter(x=names, y=[item["primary_energy_nonrenewable_kwh"] for item in sources],
                       name="Primaria no renovable (kWh)", mode="lines+markers",
                       line=dict(color="#fbbf24", width=3), marker=dict(size=10))
    fig_env.update_layout(template="plotly_dark", title="Comparativa Ambiental: Emissions i Energia No Renovable",
                         xaxis_title="Font de Calefacció", yaxis_title="Valor anual",
                         height=450, hovermode="x unified")
    
    # 2. Gràfic comparativa econòmica de les opcions elèctriques
    economic_sources = [
        item for item in sources
        if item["source_key"] in {"aerotermia", "geotermia", "electricitat_resistencia"}
    ]
    economic_names = [item["source_name"] for item in economic_sources]
    economic_colors = [
        "#fbbf24" if item["source_key"] == "electricitat_resistencia" else
        ("#34d399" if item["source_key"] == "geotermia" else "#38bdf8")
        for item in economic_sources
    ]
    fig_econ = go.Figure()
    fig_econ.add_bar(x=economic_names, y=[item["annual_total_cost_eur"] for item in economic_sources],
                     name="Operació + manteniment (€/any)", marker_color=economic_colors,
                     marker_line_width=2, marker_line_color=[
                         "#fbbf24" if item["source_key"] == active_key else "#cbd5e1"
                         for item in economic_sources
                     ])
    fig_econ.add_bar(x=economic_names, y=[item["annualized_capex_eur"] for item in economic_sources],
                     name="Amortització CAPEX tèrmic (€/any)", marker_color="#64748b")
    fig_econ.add_scatter(x=economic_names, y=[item["input_energy_kwh"] for item in economic_sources],
                        name="Electricitat necessària (kWh/any)", mode="lines+markers+text",
                        text=[f"{item['input_energy_kwh']:.0f} kWh" for item in economic_sources],
                        textposition="top center", yaxis="y2",
                        line=dict(color="#f8fafc", width=3), marker=dict(size=10))
    fig_econ.update_layout(template="plotly_dark", barmode="stack",
                          title="Comparativa Econòmica: Bombes de calor vs resistència",
                          xaxis_title="Alternativa elèctrica", yaxis_title="Cost anual (€/any)",
                          yaxis2=dict(title="Electricitat necessària (kWh/any)", overlaying="y", side="right"),
                          height=450, hovermode="x unified",
                          legend=dict(orientation="h", y=1.12), margin=dict(t=100, b=90))
    
    # 3. Gràfic d'energies renovables vs no renovables
    fig_energy_split = go.Figure()
    fig_energy_split.add_bar(x=names, y=[item["primary_energy_nonrenewable_kwh"] for item in sources],
                            name="Primaria no renovable", marker_color=colors_energy,
                            marker_line_width=2, marker_line_color=['#f87171' if item["source_key"] == active_key else '#cbd5e1' for item in sources])
    fig_energy_split.add_bar(x=names, y=[item["renewable_primary_kwh"] for item in sources],
                            name="Primaria renovable", marker_color="#34d399")
    fig_energy_split.update_layout(barmode="stack", template="plotly_dark",
                                  title="Comparativa Energètica: Desglosament d'Energia Primaria",
                                  xaxis_title="Font de Calefacció", yaxis_title="kWh/any",
                                  height=450)
    
    # 4. Gràfic Triple: Ranking de cada font en 3 criteris
    fig_radar = go.Figure()
    
    # Normalitzar valors per al radar (0-100)
    max_cost = max([item["annualized_total_cost_eur"] for item in sources])
    max_emis = max([item["emissions_kg_co2e"] for item in sources])
    max_energy = max([item["primary_energy_nonrenewable_kwh"] for item in sources])
    
    for item in sources:
        cost_score = 100 - (item["annualized_total_cost_eur"] / max_cost * 100)  # invert (lower is better)
        emis_score = 100 - (item["emissions_kg_co2e"] / max_emis * 100)
        energy_score = 100 - (item["primary_energy_nonrenewable_kwh"] / max_energy * 100)
        
        is_active = item["source_key"] == active_key
        
        fig_radar.add_trace(go.Scatterpolar(
            r=[cost_score, emis_score, energy_score],
            theta=["Cost Anualitzat", "Emissions", "Energia No Renovable"],
            name=item["source_name"],
            fill="toself" if is_active else None,
            line_width=3 if is_active else 2,
            opacity=0.8 if is_active else 0.5,
            marker=dict(size=10 if is_active else 6)
        ))
    
    fig_radar.update_layout(
        template="plotly_dark",
        title="Classificació Multi-Criteris (0=pitjor, 100=millor)",
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=500
    )
    
    figures_html = "".join([
        f'<div class="chart-block"><h3>Comparativa Ambiental</h3>{pio.to_html(fig_env, include_plotlyjs="cdn", full_html=False)}</div>',
        f'<div class="chart-block"><h3>Comparativa Econòmica</h3>{pio.to_html(fig_econ, include_plotlyjs=False, full_html=False)}</div>',
        f'<div class="chart-block"><h3>Comparativa Energètica</h3>{pio.to_html(fig_energy_split, include_plotlyjs=False, full_html=False)}</div>',
        f'<div class="chart-block"><h3>Classificació Multi-Criteris</h3>{pio.to_html(fig_radar, include_plotlyjs=False, full_html=False)}</div>',
    ])
    
    return f"""
    <h2>Comparativa de Fonts de Calefacció: Alternatives vs Sistema Actual</h2>
    <div class="metric-note">
        Els gràfics següents mostren una comparativa detallada entre totes les fonts tèrmiques disponibles.
        La font actual s'identifica amb un ressalt visual. Els valors es mostren en termes ambientals (emissions, energia primaria),
        econòmics (costos operatius i anualitzats) i energètics (renovables vs no renovables).
    </div>
    {figures_html}
    """


def _combined_economic_section(combined_summary):
        """Presenta la inversio conjunta FV+bateria+calefaccio electrica."""
        if not combined_summary or not combined_summary.get("comparisons"):
                return ""

        comparisons = combined_summary["comparisons"]
        names = [item["source_name"] for item in comparisons]
        heat_pump_options = [
            item for item in comparisons
            if item["source_key"] in {"aerotermia", "geotermia"}
        ]
        recommended = max(heat_pump_options, key=lambda item: item["npv"]) if heat_pump_options else comparisons[0]
        recommended_payback = (
            "No viable"
            if recommended["payback_years"] is None
            else f"{recommended['payback_years']:.1f} anys"
        )
        most_efficient = min(
            heat_pump_options,
            key=lambda item: next(
                source["input_energy_kwh"]
                for source in combined_summary.get("source_details", [])
                if source["source_key"] == item["source_key"]
            ),
        ) if combined_summary.get("source_details") and heat_pump_options else recommended
        fig = go.Figure()
        fig.add_bar(
                x=names,
                y=[item["package_capex"] for item in comparisons],
                name="CAPEX total del paquet",
                marker_color="#38bdf8",
                text=[f"{item['package_capex']:.0f} €" for item in comparisons],
                textposition="auto",
        )
        fig.add_scatter(
                x=names,
                y=[item["annual_saving"] for item in comparisons],
                name="Estalvi net anual",
                mode="lines+markers+text",
                text=[f"{item['annual_saving']:.0f} €/any" for item in comparisons],
                textposition="top center",
                yaxis="y2",
                line=dict(color="#34d399", width=3),
                marker=dict(size=10),
        )
        fig.update_layout(
                template="plotly_dark",
                title="Inversió total i estalvi anual del paquet FV + calefacció elèctrica",
                xaxis_title="Alternativa de calefacció",
                yaxis=dict(title="CAPEX total (€)"),
                yaxis2=dict(title="Estalvi net anual (€/any)", overlaying="y", side="right"),
                height=460,
                legend=dict(orientation="h", y=1.12),
                margin=dict(t=100, b=100),
        )

        rows = []
        for item in comparisons:
                payback = "No viable" if item["payback_years"] is None else f"{item['payback_years']:.1f} anys"
                saving_class = "positive" if item["annual_saving"] > 0 else "negative"
                is_recommended = item["source_key"] == recommended["source_key"]
                is_reference = item["source_key"] == "electricitat_resistencia"
                row_class = "recommended" if is_recommended else ("reference" if is_reference else "")
                decision_badge = (
                    '<span class="decision-badge recommended">Millor opció de bomba de calor</span>'
                    if is_recommended else
                    '<span class="decision-badge reference">Referència, COP 1,00</span>'
                    if is_reference else ""
                )
                rows.append(f"""
                <tr class="{row_class}">
                    <td><strong>{item['source_name']}</strong><br>{decision_badge}</td>
                    <td class="numeric">{item['pv_battery_capex']:.0f} €</td>
                    <td class="numeric">{item['heating_capex']:.0f} €</td>
                    <td class="numeric">{item['package_capex']:.0f} €</td>
                    <td class="numeric">{item['incremental_capex']:.0f} €</td>
                    <td class="numeric {saving_class}">{item['annual_saving']:.0f} €/any</td>
                    <td class="numeric">{payback}</td>
                                        <td class="numeric">{item['replacement_cost_over_life']:.0f} €</td>
                                        <td class="numeric">{item['net_saving_over_life']:.0f} €</td>
                    <td class="numeric">{item['npv']:.0f} €</td>
                </tr>
                """)

        return f"""
        <h2>Anàlisi econòmica combinada: FV + bateria + calefacció elèctrica</h2>
        <div class="metric-note">
            Aquesta anàlisi compara dos escenaris per al mateix habitatge: referència amb
            <strong>{combined_summary['reference_name']}</strong> i tota l'electricitat domèstica comprada a la xarxa,
            davant del paquet nou FV + bateria + calefacció elèctrica. El CAPEX del paquet inclou FV, bateria,
            costos d'instal·lació i calefacció; el CAPEX de referència inclou només la calefacció de gas.
            El cost anual del paquet inclou la factura elèctrica neta (importacions menys excedents), manteniment tèrmic
            i manteniment FV. El cas de referència inclou el cost de gas i la factura elèctrica domèstica sense FV.
            El component FV+bateria es desglossa en {combined_summary.get('pv_capex', 0.0):.0f} € de sistema FV,
            {combined_summary.get('battery_capex', 0.0):.0f} € de bateria i {combined_summary.get('installation_extra', 0.0):.0f} € d'instal·lació/BOS (inclou l'allowance inicial d'inversor).
        </div>
                <div class="combined-summary">
                    <div class="combined-highlight primary">
                        <div class="highlight-label">Millor opció entre bombes de calor</div>
                        <div class="highlight-value">{recommended['source_name']}</div>
                        <div class="highlight-detail">VAN: {recommended['npv']:.0f} € · Payback: {recommended_payback}</div>
                    </div>
                    <div class="combined-highlight efficiency">
                        <div class="highlight-label">Més eficient energèticament</div>
                        <div class="highlight-value">{most_efficient['source_name']}</div>
                        <div class="highlight-detail">Menor consum elèctric per cobrir la mateixa demanda tèrmica</div>
                    </div>
                    <div class="combined-highlight reference">
                        <div class="highlight-label">Referència de baixa eficiència</div>
                        <div class="highlight-value">Electricitat (resistència)</div>
                        <div class="highlight-detail">Es conserva per comparar, però no es recomana per a obra nova</div>
                    </div>
                </div>
                <div class="chart-block">{pio.to_html(fig, include_plotlyjs=False, full_html=False)}</div>
                <div class="combined-table-wrap">
                        <table class="combined-table">
                <thead><tr>
                    <th>Alternativa</th><th>CAPEX FV+bateria (€)</th><th>CAPEX calefacció (€)</th>
                    <th>CAPEX total paquet (€)</th><th>CAPEX addicional vs referència (€)</th>
                                        <th>Estalvi net anual</th><th>Payback</th>
                                        <th>Reposicions estimades ({combined_summary['project_life_years']} anys)</th>
                                        <th>Benefici nominal net ({combined_summary['project_life_years']} anys)</th><th>VAN</th>
                </tr></thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
        <div class="metric-note">
            La inversió addicional és CAPEX del paquet nou menys el CAPEX de la calefacció de referència.
            El VAN considera la inflació i la taxa de descompte configurades. Aquest CAPEX sí que inclou FV i bateria;
            no s'ha de confondre amb el CAPEX tèrmic de la comparativa de fonts de calefacció. El benefici nominal net acumula els estalvis anuals amb inflació i resta CAPEX addicional i reposicions estimades de bateria/inversor, però no descompta el valor temporal dels diners. El VAN sí que aplica la taxa de descompte.
            Les reposicions mostrades cobreixen només bateria i inversor segons la vida útil configurada; encara no modelen la substitució de la bomba de calor ni del sistema de referència.
            El cost geotèrmic inclou perforació i una estimació configurable de bomba de calor/sistema geotèrmic; no és un pressupost d'obra i encara no inclou una partida separada per interacumulador, adaptació d'emissors, obra interior ni contingències.
        </div>
        """


def _thermal_charts(thermal_summary):
    if not thermal_summary or not thermal_summary.get("sources"):
        return ""
    sources = thermal_summary["sources"]
    names = [item["source_name"] for item in sources]

    # 1. Comparativa energètica anual
    fig_energy = go.Figure()
    fig_energy.add_bar(x=names, y=[item["input_energy_kwh"] for item in sources], name="Consum d'entrada")
    fig_energy.add_bar(x=names, y=[item["primary_energy_total_kwh"] for item in sources], name="Energia primària total")
    fig_energy.add_bar(x=names, y=[item["primary_energy_nonrenewable_kwh"] for item in sources], name="Primària no renovable")
    fig_energy.update_layout(barmode="group", template="plotly_dark", title="Comparativa energètica anual",
                             xaxis_title="Font", yaxis_title="kWh/any", height=430)

    # 2. Emissions operatives de CO2
    fig_emissions = go.Figure()
    fig_emissions.add_bar(x=names, y=[item["emissions_kg_co2e"] for item in sources],
                          marker_color="#f87171", name="Emissions")
    fig_emissions.update_layout(template="plotly_dark", title="Emissions operatives de CO2",
                                xaxis_title="Font", yaxis_title="kg CO2e/any", height=400)

    # 3. Comparativa econòmica de les tres opcions elèctriques
    electrical_sources = [
        item for item in sources
        if item["source_key"] in {"aerotermia", "geotermia", "electricitat_resistencia"}
    ]
    electrical_names = [item["source_name"] for item in electrical_sources]
    electrical_colors = [
        "#fbbf24" if item["source_key"] == "electricitat_resistencia" else
        ("#34d399" if item["source_key"] == "geotermia" else "#38bdf8")
        for item in electrical_sources
    ]
    fig_economy = go.Figure()
    fig_economy.add_bar(
        x=electrical_names,
        y=[item["annual_total_cost_eur"] for item in electrical_sources],
        name="Operació + manteniment",
        marker_color=electrical_colors,
    )
    fig_economy.add_bar(
        x=electrical_names,
        y=[item["annualized_capex_eur"] for item in electrical_sources],
        name="Amortització del CAPEX tèrmic",
        marker_color=["#94a3b8" if item["source_key"] == "electricitat_resistencia" else "#64748b" for item in electrical_sources],
    )
    fig_economy.add_scatter(
        x=electrical_names,
        y=[item["input_energy_kwh"] for item in electrical_sources],
        name="Electricitat necessària (kWh/any)",
        mode="lines+markers+text",
        text=[f"{item['input_energy_kwh']:.0f} kWh" for item in electrical_sources],
        textposition="top center",
        yaxis="y2",
        line=dict(color="#f8fafc", width=3),
        marker=dict(size=10),
    )
    fig_economy.update_layout(
        barmode="stack",
        template="plotly_dark",
        title="Comparativa econòmica de les opcions elèctriques",
        xaxis_title="Alternativa",
        yaxis=dict(title="Cost anual (€ / any)"),
        yaxis2=dict(title="Electricitat necessària (kWh / any)", overlaying="y", side="right"),
        height=460,
        legend=dict(orientation="h", y=1.12),
        margin=dict(t=100, b=90),
    )

    # 4. Gràfic de Payback period
    payback_values = [item.get("payback_years") if item.get("payback_years") is not None else 0 for item in sources]
    payback_colors = ["#34d399" if v is not None and v > 0 else "#f87171" for v in [item.get("payback_years") for item in sources]]
    fig_payback = go.Figure()
    fig_payback.add_bar(x=names, y=payback_values, marker_color=payback_colors, name="Retorn")
    fig_payback.update_layout(template="plotly_dark", 
                             title=f"Període de retorn respecte de {thermal_summary.get('payback_reference', 'la referència')}",
                             xaxis_title="Font", yaxis_title="Anys", height=400)

    # 5. Gràfic de Cost vs Emissions (Scatter)
    fig_scatter = go.Figure()
    hover_texts = [f"{item['source_name']}<br>Cost: {item['annualized_total_cost_eur']:.0f} €<br>Emissions: {item['emissions_kg_co2e']:.0f} kg CO2e" 
                   for item in sources]
    fig_scatter.add_scatter(
        x=[item["annualized_total_cost_eur"] for item in sources],
        y=[item["emissions_kg_co2e"] for item in sources],
        mode="markers+text",
        text=names,
        hovertext=hover_texts,
        hoverinfo="text",
        marker=dict(size=12, color=[item["combined_score"] for item in sources], 
                   colorscale="RdYlGn_r", showscale=True, colorbar=dict(title="Puntuació")),
        textposition="top center",
        name="Fonts"
    )
    fig_scatter.update_layout(template="plotly_dark", 
                             title="Relació Cost Anualitzat vs Emissions",
                             xaxis_title="Cost anualitzat (€/any)",
                             yaxis_title="Emissions anuals (kg CO2e)",
                             height=420)

    # 6. Gràfic de Energia Primaria No Renovable
    fig_nonrenewable = go.Figure()
    fig_nonrenewable.add_bar(x=names, 
                            y=[item["primary_energy_nonrenewable_kwh"] for item in sources],
                            marker_color="#f87171",
                            name="Primaria no renovable")
    fig_nonrenewable.add_bar(x=names,
                            y=[item["renewable_primary_kwh"] for item in sources],
                            marker_color="#34d399",
                            name="Primaria renovable")
    fig_nonrenewable.update_layout(barmode="stack", template="plotly_dark",
                                  title="Desglosament de l'energia primaria (renovable vs no renovable)",
                                  xaxis_title="Font", yaxis_title="kWh/any", height=420)

    # 7. Gràfic de Cost per kWh de calor
    fig_cost_per_kwh = go.Figure()
    fig_cost_per_kwh.add_bar(x=names,
                            y=[item["cost_per_heat_kwh_eur"] for item in sources],
                            marker_color="#38bdf8",
                            name="Cost per kWh")
    fig_cost_per_kwh.update_layout(template="plotly_dark",
                                  title="Cost anualitzat per kWh de calor generat",
                                  xaxis_title="Font", yaxis_title="€/kWh", height=400)

    figures = [fig_energy, fig_emissions, fig_economy, fig_payback, fig_scatter, fig_nonrenewable, fig_cost_per_kwh]
    
    # Afegir gràfic de sinergia amb FV si hi ha alternatives elèctriques
    pv_alternatives = thermal_summary.get("electric_alternatives_with_pv", [])
    if pv_alternatives:
        alternative_names = [item["source_name"] for item in pv_alternatives]
        fig_pv_synergy = go.Figure()
        fig_pv_synergy.add_bar(x=alternative_names, y=[item["grid_import_kwh"] for item in pv_alternatives], name="Importació de xarxa")
        fig_pv_synergy.add_bar(x=alternative_names, y=[item["grid_export_kwh"] for item in pv_alternatives], name="Excedent FV")
        fig_pv_synergy.update_layout(barmode="group", template="plotly_dark", 
                                    title="Sinergia: FV existent i alternatives elèctriques",
                                    xaxis_title="Alternativa", yaxis_title="kWh/any", height=420)
        figures.append(fig_pv_synergy)
    
    return "".join(
        f'<div class="chart-block">{pio.to_html(figure, include_plotlyjs=False, full_html=False)}</div>'
        for figure in figures
    )


def build_report(df, daily, monthly, hourly_profile, summary, battery_diag, economic_summary, environmental_summary, lifecycle_projection, output_path, thermal_summary=None, config=None, combined_economic_summary=None):
    # --- Produccio vs consum mensual ---
    fig_monthly = go.Figure()
    fig_monthly.add_bar(x=monthly.index, y=monthly["pv_kwh"], name="Produccio")
    fig_monthly.add_bar(x=monthly.index, y=monthly["load_kwh"], name="Consum")
    fig_monthly.update_layout(barmode="group", template="plotly_dark",
                               title="Produccio vs consum mensual (kWh)",
                               xaxis_title="Mes", yaxis_title="kWh", height=380)

    # --- Taxes mensuals d'autoconsum / autosuficiencia ---
    fig_rates = go.Figure()
    fig_rates.add_scatter(x=monthly.index, y=monthly["self_consumption_pct"], name="Taxa autoconsum (%)", mode="lines+markers")
    fig_rates.add_scatter(x=monthly.index, y=monthly["self_sufficiency_pct"], name="Taxa autosuficiencia (%)", mode="lines+markers")
    fig_rates.update_layout(template="plotly_dark", title="Evolucio mensual de l'autoconsum i l'autosuficiencia",
                             xaxis_title="Mes", yaxis_title="%", height=360)

    # --- Produccio i consum diaris ---
    first_day = pd.to_datetime(daily.index.min())
    last_day = pd.to_datetime(daily.index.max())
    daily_dates = pd.to_datetime(daily.index)
    fig_daily = go.Figure()
    fig_daily.add_scatter(x=daily_dates, y=daily["pv_kwh"], name="Produccio diaria", mode="lines")
    fig_daily.add_scatter(x=daily_dates, y=daily["load_kwh"], name="Consum diari", mode="lines")

    season_ranges = [
        (pd.Timestamp(first_day.year, 12, 1), pd.Timestamp(first_day.year + 1, 3, 1), "Hivern"),
        (pd.Timestamp(first_day.year, 3, 1), pd.Timestamp(first_day.year, 6, 1), "Primavera"),
        (pd.Timestamp(first_day.year, 6, 1), pd.Timestamp(first_day.year, 9, 1), "Estiu"),
        (pd.Timestamp(first_day.year, 9, 1), pd.Timestamp(first_day.year, 12, 1), "Tardor"),
    ]
    for start, end, season in season_ranges:
        if start <= last_day and end >= first_day:
            fig_daily.add_vrect(x0=start, x1=end, line_width=0, fillcolor="rgba(148, 163, 184, 0.08)", opacity=0.5,
                               annotation_text=season, annotation_position="top left")

    month_starts = pd.date_range(start=first_day, end=last_day, freq="MS")
    month_labels = [m.strftime("%b") for m in month_starts]
    fig_daily.update_layout(template="plotly_dark", title="Produccio i consum diaris al llarg de l'any",
                             xaxis_title="Mes", yaxis_title="kWh", height=380,
                             xaxis=dict(tickvals=month_starts, ticktext=month_labels, tickangle=-30))

    # --- Perfil horari mitja per estacio ---
    season_order = ["Hivern", "Primavera", "Estiu", "Tardor"]
    season_colors = {
        "Hivern": "#60a5fa", 
        "Primavera": "#34d399",
        "Estiu": "#fbbf24",
        "Tardor": "#f87171",
    }
    fig_profile = go.Figure()
    for season in season_order:
        sub = hourly_profile[hourly_profile["season"] == season]
        if sub.empty:
            continue
        fig_profile.add_scatter(
            x=sub["hour"], y=sub["pv_kwh"],
            name=f"PV - {season}",
            mode="lines",
            line=dict(color=season_colors[season], width=2.5),
        )
    for season in season_order:
        sub = hourly_profile[hourly_profile["season"] == season]
        if sub.empty:
            continue
        fig_profile.add_scatter(
            x=sub["hour"], y=sub["load_kwh"],
            name=f"Consum - {season}",
            mode="lines",
            line=dict(color=season_colors[season], width=2.0, dash="dot"),
        )
    fig_profile.update_layout(
        template="plotly_dark",
        title="Perfil horari mitja per estacio (dia tipic)",
        xaxis_title="Hora del dia",
        yaxis_title="kWh mitjos",
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(tickmode="array", tickvals=list(range(0, 24)))
    )

    battery_figs_html = ""
    if "battery_soc_pct" in df.columns:
        fig_soc = go.Figure()
        fig_soc.add_scatter(x=list(range(len(df))), y=df["battery_soc_pct"], mode="lines",
                             name="SOC %", line=dict(color="#34d399", width=1))
        fig_soc.update_layout(template="plotly_dark", title="Estat de carrega de la bateria (%) al llarg de l'any",
                               xaxis_title="Hora de l'any", yaxis_title="SOC (%)", height=380)
        battery_figs_html += f'<div class="chart-block">{pio.to_html(fig_soc, include_plotlyjs=False, full_html=False)}</div>'

        if "soc_avg_pct" in daily.columns:
            monthly_soc = daily.groupby("month")[["soc_min_pct", "soc_avg_pct", "soc_max_pct"]].mean()
            fig_soc_m = go.Figure()
            fig_soc_m.add_scatter(x=monthly_soc.index, y=monthly_soc["soc_max_pct"], name="Maxim", line=dict(color="#f87171"))
            fig_soc_m.add_scatter(x=monthly_soc.index, y=monthly_soc["soc_avg_pct"], name="Mitjana", line=dict(color="#38bdf8"))
            fig_soc_m.add_scatter(x=monthly_soc.index, y=monthly_soc["soc_min_pct"], name="Minim", line=dict(color="#34d399"))
            fig_soc_m.update_layout(template="plotly_dark", title="Variacio mensual de l'estat de carrega (%)",
                                     xaxis_title="Mes", yaxis_title="SOC (%)", height=380)
            battery_figs_html += f'<div class="chart-block">{pio.to_html(fig_soc_m, include_plotlyjs=False, full_html=False)}</div>'

    kpis = f"""<div class="kpi-grid">
      {_kpi("Produccio anual", f"{summary['total_pv']:.0f} kWh")}
      {_kpi("Consum anual", f"{summary['total_load']:.0f} kWh")}
      {_kpi("Autoconsumit", f"{summary['self_consumed']:.0f} kWh", "accent2")}
      {_kpi("Excedent exportat", f"{summary['total_export']:.0f} kWh")}
      {_kpi("Importat de xarxa", f"{summary['total_import']:.0f} kWh", "warn")}
      {_kpi("Taxa d'autoconsum", f"{summary['self_consumption_rate']:.1f} %", "accent2")}
      {_kpi("Taxa d'autosuficiencia", f"{summary['self_sufficiency_rate']:.1f} %", "accent2")}
    </div>"""

    battery_html = ""
    if battery_diag is not None:
        battery_html = f"""
        <h2>Dimensionament de la bateria</h2>
        <div class="kpi-grid">
          {_kpi(f"Dies bateria saturada ({battery_diag.get('max_soc_pct', 100):.0f}%)", battery_diag['n_saturated_days'], "warn")}
          {_kpi("Dies bateria buida", battery_diag['n_empty_days'], "danger")}
          {_kpi("Dies limitats per potencia carrega", battery_diag['n_power_charge_days'], "warn")}
          {_kpi("Dies limitats per potencia descarrega", battery_diag['n_power_discharge_days'], "warn")}
          {_kpi("Cicles complets equivalents/any", f"{battery_diag['equivalent_cycles']:.0f}")}
          {_kpi("Energia perduda (bateria plena)", f"{battery_diag['energy_lost_full']:.0f} kWh", "danger")}
          {_kpi("Energia no coberta (bateria buida)", f"{battery_diag['energy_unmet_empty']:.0f} kWh", "danger")}
        </div>
        <div class="reco">{battery_diag['recommendation']}</div>
        """

    project_life_years = economic_summary.get("project_life_years", 25)
    lifecycle_impact = economic_summary.get("lifecycle_impact", {})
    panel_life_years = lifecycle_impact.get("panel_life_years", 25)
    payback_text = "No viable econòmicament" if economic_summary["payback_years"] is None else f"{economic_summary['payback_years']:.1f} anys"
    economic_html = f"""
    <h2>Analisi econòmica</h2>
    <div class="kpi-grid">
      {_kpi("Cost total instal·lacio", f"{economic_summary['capex_total']:.0f} €")}
      {_kpi("Cost plaques FV", f"{economic_summary['pv_capex']:.0f} €")}
      {_kpi("Cost bateria", f"{economic_summary['battery_capex']:.0f} €", "accent2")}
      {_kpi("Estalvi anual", f"{economic_summary['annual_bill_saving']:.0f} €/any", "accent2")}
      {_kpi("Flux net anual", f"{economic_summary['annual_cashflow']:.0f} €/any", "warn")}
      {_kpi("Payback", payback_text, "warn")}
      {_kpi(f"VAN {economic_summary.get('project_life_years', 25)} anys", f"{economic_summary.get('npv', economic_summary['npv_25y']):.0f} €", "accent2")}
      {_kpi("Compra mitjana llum", f"{economic_summary['buy_price']:.2f} €/kWh")}
      {_kpi("Venda excedents", f"{economic_summary['sell_price']:.2f} €/kWh")}
    </div>
    <div class="reco">
      Supòsits utilitzats: cost fotovoltaic de {economic_summary.get('pv_cost_per_kw', 0):.0f} €/kWp, bateria de {economic_summary.get('battery_cost_per_kwh', 0):.0f} €/kWh i {economic_summary.get('battery_cost_per_kw', 0):.0f} €/kW, preu de compra {economic_summary['buy_price']:.2f} €/kWh, preu de venda {economic_summary['sell_price']:.2f} €/kWh, manteniment anual {economic_summary['annual_om']:.0f} € i horitzó del projecte de {project_life_years} anys.
    </div>
    """

    replacements = lifecycle_impact.get("replacements", [])
    replacement_lines = "Cap substitució prevista en el període analitzat." if not replacements else "; ".join(
        f"{entry['type']} a l'any {entry['year']} ({entry['cost']:.0f} €)" for entry in replacements
    )

    lifecycle_html = f"""
    <h2>Vida útil i degradació del sistema</h2>
    <div class="kpi-grid">
      {_kpi("Pèrdua anual de rendiment", f"{economic_summary.get('panel_degradation_pct_per_year', 0) * 100:.2f} %/any")}
      {_kpi("Vida útil plaques", f"{economic_summary.get('lifecycle_impact', {}).get('panel_life_years', 25)} anys")}
      {_kpi("Vida útil bateria", f"{economic_summary.get('lifecycle_impact', {}).get('battery_life_years', 10)} anys")}
      {_kpi("Vida útil inversor", f"{economic_summary.get('lifecycle_impact', {}).get('inverter_life_years', 12)} anys")}
      {_kpi("Cost substitució bateria", f"{economic_summary.get('lifecycle_impact', {}).get('battery_replacement_cost', 0):.0f} €")}
      {_kpi("Cost substitució inversor", f"{economic_summary.get('lifecycle_impact', {}).get('inverter_replacement_cost', 0):.0f} €")}
      {_kpi(f"Producció estimada any {project_life_years}", f"{economic_summary.get('annual_production_end_of_project', economic_summary.get('annual_production_year_25', 0)):.0f} kWh")}
      {_kpi("Emissions incorporades", f"{environmental_summary.get('embodied_co2_kg', 0):.0f} kg CO2e")}
    </div>
    <div class="reco">
      En l'horitzó del projecte de {project_life_years} anys, les plaques perden eficiència de manera gradual; el càlcul inclou una degradació anual de {economic_summary.get('panel_degradation_pct_per_year', 0) * 100:.2f}% i les substitucions estimades de bateria/inversor. Substitucions previstes: {replacement_lines}. Pel que fa a l'impacte ambiental, s'estima que el sistema evita {environmental_summary.get('co2_saved_kg_over_life', 0):.0f} kg CO2e al llarg dels {environmental_summary.get('panel_life_years', panel_life_years)} anys de vida útil dels panells, amb un balanç net de {environmental_summary.get('net_co2_kg', 0):.0f} kg CO2e després de comptabilitzar les emissions incorporades.
    </div>
    """

    fig_cashflow = go.Figure()
    fig_cashflow.add_scatter(x=lifecycle_projection.get("cashflow_years", [0]), y=lifecycle_projection.get("cumulative_cashflow_eur", [0]),
                            mode="lines+markers", name="Flux de caixa acumulat", line=dict(color="#38bdf8", width=3))
    fig_cashflow.update_layout(template="plotly_dark", title=f"Flux de caixa acumulat de la instal·lació ({project_life_years} anys)",
                               xaxis_title="Any", yaxis_title="€ acumulat", height=360)

    years = lifecycle_projection.get("years", [])
    prod = lifecycle_projection.get("annual_production_kwh", [])
    saved_co2 = lifecycle_projection.get("avoided_co2_kg", [])

    fig_production_lifecycle = go.Figure()
    fig_production_lifecycle.add_scatter(x=years, y=prod, mode="lines+markers", name="Producció anual", line=dict(color="#34d399", width=3))
    fig_production_lifecycle.update_layout(template="plotly_dark", title=f"Producció anual durant el projecte ({project_life_years} anys)",
                                          xaxis_title="Any", yaxis_title="kWh/any", height=360)

    fig_emissions_lifecycle = go.Figure()
    fig_emissions_lifecycle.add_scatter(x=years, y=saved_co2, mode="lines+markers", name="CO2 evitat anual", line=dict(color="#fbbf24", width=3))
    fig_emissions_lifecycle.update_layout(template="plotly_dark", title=f"Emissions evitades anuals durant el projecte ({project_life_years} anys)",
                                         xaxis_title="Any", yaxis_title="kg CO2eq/any", height=360)

    thermal_charts_html = _thermal_charts(thermal_summary)
    geothermal_design_html = _geothermal_design_section(thermal_summary)

    thermal_comparison_html = _thermal_comparison_charts(thermal_summary)
    personalized_analysis_html = _personalized_analysis(thermal_summary, summary, economic_summary, config)
    combined_economic_html = _combined_economic_section(combined_economic_summary)

    first_year_kpis = f"""
    <h2>Indicadors del primer any</h2>
    <div class="kpi-grid">
      {_kpi("Producció any 1", f"{summary['total_pv']:.0f} kWh")}
      {_kpi("Autoconsum any 1", f"{summary['self_consumed']:.0f} kWh", "accent2")}
      {_kpi("Estalvi anual energia", f"{economic_summary['annual_bill_saving']:.0f} €")}
      {_kpi("Flux net anual", f"{economic_summary['annual_cashflow']:.0f} €", "warn")}
      {_kpi("CO2 evitat any 1", f"{environmental_summary.get('avoided_co2_per_year_kg', 0):.0f} kg CO2e")}
      {_kpi("Taxa d'autoconsum", f"{summary['self_consumption_rate']:.1f} %", "accent2")}
    </div>
    """

    lifecycle_kpis = f"""
    <h2>Indicadors del projecte ({project_life_years} anys)</h2>
    <div class="kpi-grid">
      {_kpi("Producció total estimada", f"{sum(lifecycle_projection.get('annual_production_kwh', [])):.0f} kWh")}
      {_kpi(f"CO2 evitat en {environmental_summary.get('panel_life_years', panel_life_years)} anys", f"{environmental_summary.get('co2_saved_kg_over_life', 0):.0f} kg CO2e")}
      {_kpi(f"VAN {economic_summary.get('project_life_years', 25)} anys", f"{economic_summary.get('npv', economic_summary['npv_25y']):.0f} €", "accent2")}
      {_kpi("Flux caixa acumulat final", f"{lifecycle_projection.get('cumulative_cashflow_eur', [])[-1]:.0f} €", "warn")}
      {_kpi(f"Producció any {project_life_years}", f"{lifecycle_projection.get('annual_production_kwh', [0])[-1]:.0f} kWh")}
      {_kpi(f"CO2 evitat any {project_life_years}", f"{lifecycle_projection.get('avoided_co2_kg', [0])[-1]:.0f} kg CO2e")}
    </div>
    """

    html = f"""<!DOCTYPE html>
<html lang="ca">
<head><meta charset="utf-8"><title>Informe integral d'energia, climatització i sostenibilitat</title>{CARD_CSS}</head>
<body>
  <div class="top-header">
    <h1>Informe integral d'energia, climatització i sostenibilitat</h1>
    <div class="subtitle">Generat amb l'any PVGIS {summary.get('pvgis_reference_year', 'no indicat')}, triat perquè la seva producció anual és la més propera a la mediana de {summary.get('pvgis_complete_years', 1)} anys complets disponibles, i amb el perfil de consum configurat.</div>
  </div>

  {_system_summary_section(config)}

  {_executive_summary(summary, economic_summary)}

  {thermal_comparison_html}

    {combined_economic_html}

  {personalized_analysis_html}

  {kpis}

  {first_year_kpis}
  {lifecycle_kpis}

  {_thermal_section(thermal_summary)}
  {geothermal_design_html}
  {_thermal_savings_section(thermal_summary)}
  {thermal_charts_html}

  <h2>Autoconsum i autosuficiencia</h2>
  {_autoconsumption_narrative(summary)}

  <h2>Produccio vs consum</h2>
  <div class="chart-block">{pio.to_html(fig_monthly, include_plotlyjs='cdn', full_html=False)}</div>
  <div class="chart-block">{pio.to_html(fig_rates, include_plotlyjs=False, full_html=False)}</div>
  <div class="chart-block">{pio.to_html(fig_daily, include_plotlyjs=False, full_html=False)}</div>

  <h2>Perfil horari</h2>
  <div class="chart-block">{pio.to_html(fig_profile, include_plotlyjs=False, full_html=False)}</div>

  <h2>Flux de caixa i trajectòria de la instal·lació</h2>
  <div class="chart-block">{pio.to_html(fig_cashflow, include_plotlyjs=False, full_html=False)}</div>
  <div class="chart-block">{pio.to_html(fig_production_lifecycle, include_plotlyjs=False, full_html=False)}</div>
  <div class="chart-block">{pio.to_html(fig_emissions_lifecycle, include_plotlyjs=False, full_html=False)}</div>

  {battery_figs_html}

  {lifecycle_html}

  {economic_html}

  {battery_html}
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
