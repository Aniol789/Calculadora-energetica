"""
Genera un informe HTML interactiu i modern amb els resultats de la
simulacio: targetes KPI, grafics interactius (Plotly) i diagnostic de
dimensionament de la bateria. Es un fitxer HTML autonom que s'obre amb
qualsevol navegador (no cal servidor).
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime
from html import escape

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
    margin: 0; padding: 0;
  }
  .report-container { width: min(1240px, 100%); margin: 0 auto; padding: 24px clamp(20px, 5vw, 72px) 72px; }
  .front-page {
    min-height: 100vh; position: relative; overflow: hidden; display: flex; flex-direction: column;
    justify-content: space-between; padding: clamp(36px, 8vw, 100px) clamp(28px, 10vw, 140px);
    background: radial-gradient(ellipse at 88% 18%, rgba(56,189,248,.24), transparent 35%),
                radial-gradient(ellipse at 12% 92%, rgba(52,211,153,.16), transparent 36%), #0b1221;
    border-bottom: 1px solid rgba(148,163,184,.24); break-after: page; page-break-after: always;
  }
  .front-page::after { content: ""; position: absolute; width: 52vw; height: 52vw; min-width: 420px; min-height: 420px; right: -14vw; bottom: -28vw; border: 1px solid rgba(56,189,248,.19); border-radius: 50%; box-shadow: 0 0 0 44px rgba(56,189,248,.025), 0 0 0 90px rgba(56,189,248,.025), 0 0 0 138px rgba(52,211,153,.025); pointer-events: none; }
  .cover-brand { display: flex; align-items: center; gap: 13px; position: relative; z-index: 1; }
  .cover-mark { width: 42px; height: 42px; border-radius: 14px; display: grid; place-items: center; color: #07111f; font-size: 23px; font-weight: 900; background: linear-gradient(135deg,#7dd3fc,#6ee7b7); box-shadow: 0 8px 28px rgba(56,189,248,.22); }
  .cover-brand-name { font-size: .95rem; font-weight: 750; letter-spacing: .08em; text-transform: uppercase; }
  .cover-brand-sub { color: var(--muted); font-size: .75rem; margin-top: 3px; }
  .cover-main { position: relative; z-index: 1; max-width: 820px; padding: 64px 0; }
  .cover-eyebrow, .section-kicker { color: var(--accent2); text-transform: uppercase; letter-spacing: .15em; font-size: .74rem; font-weight: 800; }
  .cover-main h1 { font-size: clamp(3.2rem, 9vw, 7rem); line-height: .98; margin: 18px 0; letter-spacing: -.065em; max-width: 780px; }
  .cover-description { color: #b7c7d9; font-size: clamp(1.05rem, 2vw, 1.35rem); line-height: 1.6; max-width: 630px; }
  .cover-case { margin-top: 48px; border-left: 3px solid var(--accent2); padding: 4px 0 4px 18px; }
  .cover-case-label { color: var(--muted); font-size: .72rem; text-transform: uppercase; letter-spacing: .1em; }
  .cover-case-name { font-size: clamp(1.35rem, 3vw, 2rem); margin-top: 7px; font-weight: 700; }
  .cover-meta { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 18px; max-width: 850px; position: relative; z-index: 1; }
  .cover-meta-item { border-top: 1px solid rgba(148,163,184,.35); padding-top: 12px; }
  .cover-meta-label { color: var(--muted); font-size: .7rem; text-transform: uppercase; letter-spacing: .09em; }
  .cover-meta-value { font-weight: 650; margin-top: 5px; }
  .index-page { min-height: 100vh; padding: clamp(38px, 7vw, 82px) clamp(24px, 10vw, 140px); max-width: 1240px; margin: 0 auto; break-after: page; page-break-after: always; }
  .index-page h1 { font-size: clamp(2rem,5vw,3.3rem); margin: 10px 0 10px; letter-spacing: -.04em; }
  .index-lead { color: var(--muted); max-width: 660px; line-height: 1.65; margin: 0 0 30px; }
  .toc-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
  .toc-link { display: grid; grid-template-columns: 54px 1fr 24px; gap: 15px; align-items: center; text-decoration: none; color: var(--text); padding: 16px 18px; border: 1px solid rgba(148,163,184,.19); border-radius: 13px; background: rgba(30,41,59,.62); transition: transform .18s ease, border-color .18s ease, background .18s ease; }
  .toc-link:hover { transform: translateX(4px); border-color: rgba(56,189,248,.5); background: rgba(30,41,59,.95); }
  .toc-number { color: var(--accent2); font-size: .82rem; font-weight: 800; letter-spacing: .05em; }
  .toc-title { font-weight: 700; }
  .toc-description { margin-top: 4px; color: var(--muted); font-size: .86rem; line-height: 1.4; }
  .toc-arrow { color: var(--accent); font-size: 1.2rem; text-align: right; }
  .report-toolbar { position: sticky; top: 0; z-index: 10; display: flex; justify-content: space-between; align-items: center; padding: 10px max(20px, calc((100vw - 1096px)/2)); background: rgba(11,18,33,.9); border-bottom: 1px solid rgba(148,163,184,.18); backdrop-filter: blur(14px); }
  .toolbar-brand { color: var(--text); font-weight: 750; text-decoration: none; }
  .toolbar-actions { display: flex; gap: 10px; align-items: center; }
  .toolbar-link, .print-button { color: #cbd5e1; background: transparent; text-decoration: none; border: 1px solid #475569; padding: 8px 12px; border-radius: 9px; font: inherit; font-size: .85rem; cursor: pointer; }
  .print-button { background: rgba(56,189,248,.13); border-color: rgba(56,189,248,.45); color: #bae6fd; }
  .report-section { padding: 38px 0 24px; border-bottom: 1px solid rgba(148,163,184,.18); scroll-margin-top: 66px; break-before: page; page-break-before: always; }
  .section-intro { margin: 0 0 20px; max-width: 850px; }
  .section-intro h2 { font-size: clamp(1.8rem,4vw,2.7rem); color: var(--text); letter-spacing: -.04em; margin: 8px 0; }
  .section-intro p { color: var(--muted); line-height: 1.6; margin: 0; }
  .report-section > h2:first-child { border-bottom: 1px solid rgba(148,163,184,.2); padding-bottom: 12px; }
  .method-card { background: linear-gradient(135deg,rgba(56,189,248,.1),rgba(52,211,153,.06)); border: 1px solid rgba(56,189,248,.25); border-radius: 14px; padding: 20px; margin: 18px 0; line-height: 1.65; }
  .method-card h3 { margin-top: 0; color: var(--accent); }
    .glossary-group { margin: 26px 0; }
    .glossary-group h3 { color: var(--accent); margin-bottom: 10px; }
    .glossary-list { display: grid; grid-template-columns: minmax(190px, .75fr) 2fr; margin: 0; }
    .glossary-list dt, .glossary-list dd { margin: 0; padding: 12px 14px; border-top: 1px solid rgba(148,163,184,.18); line-height: 1.6; }
    .glossary-list dt { color: var(--text); font-weight: 700; }
    .glossary-list dd { color: #cbd5e1; }
    @media (max-width: 640px) { .glossary-list { grid-template-columns: 1fr; } .glossary-list dt { padding-bottom: 2px; border-top: 1px solid rgba(148,163,184,.18); } .glossary-list dd { padding-top: 2px; border-top: 0; } }
  .source-list { display: grid; grid-template-columns: repeat(auto-fit,minmax(230px,1fr)); gap: 10px; margin-top: 14px; }
  .source-list a { color: #bae6fd; text-decoration-color: rgba(125,211,252,.45); text-underline-offset: 3px; }
  .report-footer { color: var(--muted); font-size: .78rem; border-top: 1px solid rgba(148,163,184,.2); margin-top: 36px; padding-top: 14px; }
  @media (max-width: 640px) { .cover-meta { grid-template-columns: 1fr; gap: 12px; } .cover-main { padding: 40px 0; } .toc-link { grid-template-columns: 38px 1fr 18px; gap: 10px; padding: 13px; } .report-toolbar { padding: 9px 14px; } .toolbar-link { display: none; } }
  @media print {
    @page { size: A4; margin: 15mm 14mm; }
    body { background: #fff !important; color: #182230 !important; print-color-adjust: exact; -webkit-print-color-adjust: exact; }
    .front-page { min-height: 267mm; margin: -15mm -14mm 0; padding: 25mm 22mm; }
    .index-page { min-height: 267mm; padding: 20mm 8mm; }
    .report-toolbar { display: none; }
    .report-container { width: 100%; padding: 0; }
    .report-section { padding-top: 12mm; }
    .chart-block, .summary-section, .kpi-card, .exec-card, .savings-card { break-inside: avoid; }
    a { color: inherit; }
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


def _chapter_intro(number, category, title, description):
    return f"""
    <header class="section-intro">
      <div class="section-kicker">{number} · {escape(category)}</div>
      <h2>{escape(title)}</h2>
      <p>{escape(description)}</p>
    </header>
    """


def _report_identity(config, summary, thermal_summary):
    location = getattr(config, "LOCATION", {}) if config is not None else {}
    thermal = getattr(config, "THERMAL", {}) if config is not None else {}
    if not isinstance(thermal, dict):
        thermal = {}
    location_name = location.get("name", "Cas energètic") if isinstance(location, dict) else "Cas energètic"
    source_names = {
        "gas_natural": "Gas natural", "gasoil": "Gasoil", "aerotermia": "Aerotèrmia",
        "geotermia": "Geotèrmia", "biomassa": "Biomassa (pèl·let)",
        "electricitat_resistencia": "Resistència elèctrica",
    }
    active_source = thermal.get("active_source") if isinstance(thermal, dict) else None
    system_name = source_names.get(active_source, "Sistema fotovoltaic")
    case_name = f"{location_name} · {system_name}" if thermal.get("enabled", False) else location_name
    year = summary.get("pvgis_reference_year", "No indicat")
    complete_years = summary.get("pvgis_complete_years", 1)
    return {
        "case_name": escape(str(case_name)),
        "location": escape(str(location_name)),
        "system": escape(str(system_name)),
        "year": escape(str(year)),
        "complete_years": escape(str(complete_years)),
        "date": datetime.now().astimezone().strftime("%d/%m/%Y"),
    }


def _methodology_section(config, identity):
    pvgis_database = getattr(config, "PVGIS_DATABASE", "PVGIS") if config is not None else "PVGIS"
    consumption = getattr(config, "CONSUMPTION", {}) if config is not None else {}
    thermal = getattr(config, "THERMAL", {}) if config is not None else {}
    if not isinstance(thermal, dict):
        thermal = {}
    economy = getattr(config, "ECONOMY", {}) if config is not None else {}
    load_profile = consumption.get("profile", "no indicat") if isinstance(consumption, dict) else "no indicat"
    demand_mode = thermal.get("heat_demand_mode", "annual_kwh") if isinstance(thermal, dict) else "annual_kwh"
    demand_description = (
        "La demanda s'estima hora a hora amb el coeficient de pèrdua de l'edifici i la diferència entre consigna i temperatura exterior."
        if demand_mode == "heat_loss_coefficient"
        else "La calor anual configurada es conserva; les temperatures en determinen la distribució horària i afecten el COP estimat."
    )
    annual_index = float(economy.get("annual_inflation_pct", 0.0)) * 100 if isinstance(economy, dict) else 0.0
    return f"""
    <div class="method-card">
      <h3>Com llegir aquests resultats</h3>
      <p><strong>Clima i producció:</strong> s'ha utilitzat {escape(str(pvgis_database))} i l'any representatiu {identity['year']}, escollit entre {identity['complete_years']} anys complets disponibles per la producció FV i els graus-hora de calefacció. És una comparació amb un any representatiu, no una estimació de l'extrem meteorològic ni del risc interanual.</p>
      <p><strong>Perfil de consum:</strong> {escape(str(load_profile))}. Si és un perfil sintètic, els consums horaris són una aproximació escalada al total anual configurat.</p>
      <p><strong>Demanda tèrmica:</strong> {escape(demand_description)}</p>
      <p><strong>Bomba de calor:</strong> el COP horari s'estima a partir d'un punt de referència i d'una corba termodinàmica simplificada. No és un SCOP certificat; la fitxa de rendiment del fabricant és necessària per una previsió d'equip específic.</p>
      <p><strong>Costos i projecció:</strong> els preus de combustible, electricitat, manteniment i equipament són valors de referència editables. El model aplica una indexació general del {annual_index:.2f}% anual; no és una predicció de mercat diferenciada per recurs.</p>
      <p><strong>Emissions:</strong> les emissions operatives depenen dels factors configurats i de l'energia consumida. L'anàlisi de cicle de vida de la instal·lació fotovoltaica presenta separadament les emissions incorporades estimades.</p>
    </div>
    <div class="method-card">
      <h3>Fonts de referència</h3>
      <div class="source-list">
        <a href="https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/api-non-interactive-service_en">PVGIS · Comissió Europea / JRC</a>
        <a href="https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_204/default/table">Eurostat · preus d'electricitat</a>
        <a href="https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_202/default/table">Eurostat · preus de gas</a>
        <a href="https://www.miteco.gob.es/es/cambio-climatico/temas/registro-huella/huella-de-carbonoinscripcion.html">MITECO · factors d'emissió</a>
        <a href="https://avebiom.org/actividades/indice-de-precios-biocombustibles-solidos/">AVEBIOM · índex de preus del pèl·let</a>
        <a href="https://www.iea-pvps.org/wp-content/uploads/2024/12/IEA-PVPS-2023-National-Survey-Report-Spain.pdf">IEA-PVPS · mercat FV a Espanya</a>
      </div>
    </div>
    """


def _glossary_section():
    groups = [
        ("Economia i inversió", [
            ("CAPEX (inversió inicial)", "Desemborsament per adquirir i instal·lar els equips. En el model FV inclou kWp × €/kWp, bateria (kWh × €/kWh i potència de descàrrega kW × €/kW) i l'extra d'instal·lació/BOS configurat. En el paquet combinat s'hi suma el CAPEX tèrmic. No és una factura ni necessàriament un pressupost d'obra."),
            ("BOS (balance of system)", "Components i treballs auxiliars necessaris perquè la instal·lació FV funcioni, a més dels panells. En aquest model es representa amb un percentatge configurable del cost FV; no és un desglossament d'obra detallat."),
            ("OPEX (costos recurrents)", "Despeses d'ús al llarg del temps: energia comprada o combustible, costos fixos i manteniment. No inclou la inversió inicial CAPEX. En els resultats tèrmics, 'operació + manteniment' suma consum energètic, costos fixos i manteniment."),
            ("Cost anualitzat tèrmic", "Cost anual d'operació i manteniment més CAPEX tèrmic dividit pels anys d'anàlisi: (OPEX anual) + (CAPEX / anys). És una amortització lineal orientativa: no aplica taxa de descompte, inflació ni reposicions de l'equip tèrmic."),
            ("Cost anual amb FV existent", "A la comparativa d'alternatives elèctriques és el cost de les importacions de xarxa menys els ingressos per excedents, més costos fixos i manteniment tèrmic. Reutilitza la FV i la bateria configurades i no hi afegeix el CAPEX d'aquests equips."),
            ("Estalvi anual de factura FV", "Factura de referència sense generació pròpia menys factura estimada amb FV. El càlcul valora l'energia de la càrrega coberta localment al preu de compra i hi suma els ingressos per excedents al preu de venda. La referència és comprar tota la càrrega elèctrica de l'escenari a la xarxa; encara no s'han restat O&M ni CAPEX."),
            ("Flux net anual FV", "Estalvi anual de factura FV menys manteniment anual FV (O&M). És un flux operatiu estimat de l'any base abans de restar el CAPEX inicial i les reposicions futures. Positiu vol dir flux favorable aquell any, no benefici final garantit."),
            ("Estalvi operatiu tèrmic", "Cost anual d'operació i manteniment de la font activa menys el de l'alternativa. Positiu vol dir que l'alternativa costa menys cada any; negatiu vol dir que costa més. No inclou la diferència d'inversió CAPEX."),
            ("CAPEX incremental del paquet", "CAPEX del paquet nou (FV + bateria + calefacció alternativa) menys CAPEX de la calefacció de referència. El model inclou el cost configurat de FV/bateria al paquet; no tracta aquests equips com a inversió ja pagada ni resta un valor residual."),
            ("Retorn simple FV/bateria", "CAPEX FV+bateria dividit pel flux net operatiu anual de l'any base, sempre que aquest sigui positiu. No descompta fluxos ni inclou les reposicions futures; és una aproximació ràpida i no substitueix el VAN."),
            ("Retorn simple tèrmic", "CAPEX tèrmic addicional respecte de la font activa dividit per l'estalvi anual d'operació i manteniment. Només es calcula si tots dos valors són positius; no aplica descompte, inflació ni reposicions."),
            ("Retorn simple del paquet", "Màxim entre zero i el CAPEX incremental FV+bateria+calefacció respecte del sistema de referència, dividit per l'estalvi anual del paquet. Si l'estalvi anual no és positiu no hi ha retorn simple calculable; si no cal CAPEX addicional, el retorn és zero anys. No descompta fluxos ni incorpora reposicions en el quocient."),
            ("VAN FV/bateria", "Valor actual net de la instal·lació: −CAPEX inicial + suma dels fluxos nets futurs descomptats. Els fluxos incorporen estalvi de factura, O&M i reposicions modelades de bateria/inversor; la producció es degrada i els costos s'indexen segons les hipòtesis. VAN > 0 vol dir valor net positiu respecte dels supòsits i la taxa de descompte; no és un estalvi anual."),
            ("VAN del paquet combinat", "Valor actual dels estalvis del paquet FV+bateria+bomba de calor respecte del sistema de referència actiu, menys CAPEX incremental i reposicions modelades de bateria/inversor. La referència inclou el cost tèrmic actiu i assumeix la compra de tota l'electricitat domèstica a la xarxa; el paquet inclou la factura elèctrica neta amb FV/bateria i manteniment. No modela la reposició futura de la bomba de calor ni del sistema de referència."),
            ("Benefici nominal net", "Estalvis anuals acumulats durant la vida del projecte menys CAPEX incremental i reposicions estimades. Els costos s'indexen amb la inflació configurada, però no es descompten; per això no equival al VAN."),
            ("ROI (retorn de la inversió)", "A la comparativa tèrmica es calcula com (estalvi operatiu anual × anys − CAPEX incremental) / CAPEX incremental × 100. No descompta fluxos ni incorpora inflació o reposicions; si el CAPEX incremental no és positiu, no es calcula."),
            ("O&M (operació i manteniment)", "Despesa anual de manteniment FV aproximada com un percentatge configurable del CAPEX. En fonts tèrmiques, operació i manteniment inclouen també energia consumida, costos fixos i manteniment de l'equip."),
            ("Flux de caixa acumulat", "Suma del CAPEX inicial negatiu i dels fluxos nets anuals acumulats. El gràfic de caixa no descompta els fluxos futurs; per això pot diferir del VAN."),
            ("Cost per kWh tèrmic", "Cost anual d'operació i manteniment de la font dividit pels kWh de calor útil que cobreix. No inclou el CAPEX; no és el preu per kWh d'electricitat o combustible."),
            ("Taxa de descompte", "Percentatge anual que converteix fluxos futurs en valor d'avui en el càlcul del VAN. Com més alta és, menys pes tenen els estalvis llunyans."),
            ("Inflació / indexació", "Increment anual general aplicat als costos i fluxos projectats. El model no prediu per separat com evolucionarà cada tarifa de llum, combustible o manteniment."),
            ("Reposicions", "Costos previstos de substituir bateria i inversor en els anys configurats. El model no inclou la substitució de la bomba de calor ni del sistema tèrmic de referència en el VAN combinat."),
            ("Preu de compra / venda", "Preu per kWh importat de la xarxa i compensació per kWh exportat, respectivament. La diferència entre tots dos influeix en el valor econòmic de consumir FV localment o vendre'n l'excedent."),
        ]),
        ("Energia, calefacció i bateria", [
            ("kW, kWh i kWp", "kW és potència (ritme instantani d'ús o producció); kWh és energia acumulada al llarg del temps; kWp és la potència pic nominal dels panells FV en condicions de prova. No són unitats intercanviables."),
            ("kWh tèrmic", "Energia de calor útil lliurada o requerida per l'edifici. No s'ha de confondre amb els kWh elèctrics/combustible d'entrada: una bomba de calor pot lliurar diversos kWh tèrmics per cada kWh elèctric."),
            ("Producció FV", "Energia elèctrica generada pels panells durant el període simulat, expressada en kWh. No és necessàriament igual a l'energia autoconsumida: una part pot exportar-se i una altra pot perdre's en conversió/emmagatzematge segons el model."),
            ("Consum / càrrega", "Electricitat requerida per l'habitatge en el model. Pot incloure la demanda elèctrica de la calefacció activa si aquesta és elèctrica."),
            ("Importació de xarxa", "Electricitat comprada a la xarxa quan FV i bateria no cobreixen la càrrega horària. Es valora al preu de compra configurat."),
            ("Excedent / exportació", "Producció FV que no s'utilitza localment ni es desa a la bateria i s'envia a la xarxa. Els kWh exportats es valoren al preu de venda/compensació, habitualment inferior al de compra."),
            ("Autoconsum", "Percentatge de tota la producció FV que s'utilitza al mateix habitatge (directament o després de passar per la bateria segons el balanç del model). Mesura l'aprofitament de la producció."),
            ("Autosuficiència", "Percentatge de tota la càrrega elèctrica cobert amb energia local; equival a (càrrega total − importació de xarxa) / càrrega total. Mesura quanta dependència de xarxa s'evita."),
            ("Capacitat i potència de bateria", "Capacitat (kWh) és l'energia que pot guardar; potència de càrrega/descàrrega (kW) és la rapidesa màxima d'entrada/sortida. Augmentar kWh no resol necessàriament un límit de kW."),
            ("SOC (estat de càrrega)", "Energia que queda dins la bateria, mostrada en kWh o com a percentatge de la capacitat. Els límits mínim i màxim del cas redueixen la fracció utilitzable."),
            ("Eficiència round-trip", "Fracció de l'energia de càrrega recuperable després d'un cicle de càrrega i descàrrega. La resta representa pèrdues del model de bateria."),
            ("Cicles equivalents", "Energia total descarregada dividida per la capacitat nominal. És una mesura d'ús equivalent a cicles complets, no necessàriament el nombre de cicles físics observats."),
            ("Demanda tèrmica", "Calor útil anual necessària per a l'edifici. No és el consum elèctric o de combustible de l'equip: aquest depèn del rendiment/COP i dels auxiliars."),
            ("COP / η / SCOP", "COP és la calor lliurada dividida per l'electricitat consumida per una bomba de calor en unes condicions concretes. η és el rendiment utilitzat per altres fonts. SCOP és el rendiment estacional; la corba simplificada d'aquest model no és un SCOP certificat."),
            ("Energia d'entrada", "Electricitat o combustible que necessita la font per cobrir la demanda tèrmica. Per a una bomba de calor, aproximadament calor útil / COP; per a una caldera, calor útil / rendiment, més els auxiliars quan pertoqui."),
            ("Energia primària total", "Energia d'entrada multiplicada pel factor d'energia primària de la font, més els auxiliars modelats. Representa recursos energètics abans de convertir-los en energia final al lloc d'ús."),
            ("Energia primària no renovable", "Part de l'energia primària total atribuïda a recursos no renovables segons els factors i percentatges configurats per a cada font. No és igual al consum final del comptador."),
            ("Energia primària renovable", "Diferència entre energia primària total i la part classificada com a no renovable en el catàleg del model."),
            ("Factor d'energia primària", "Coeficient que converteix l'energia final consumida (electricitat o combustible) en energia primària estimada. Els valors són hipòtesis configurables, no mesures del comptador."),
        ]),
        ("Emissions, vida útil i rànquings", [
            ("CO₂e", "Diòxid de carboni equivalent: unitat que expressa l'efecte climàtic de diferents gasos d'efecte hivernacle en una mateixa escala."),
            ("Emissions operatives", "Emissions anuals estimades de l'energia consumida per la font tèrmica, aplicant els factors d'emissió del catàleg. A la taula tèrmica no es descompten les emissions evitades perquè part de l'electricitat provingui de FV."),
            ("Emissions incorporades", "Emissions estimades de fabricació dels panells, bateria i inversor, calculades amb factors kg CO₂e per kWp/kWh/kW. No són una anàlisi ambiental completa de tots els materials i obres."),
            ("CO₂ evitat i balanç net", "CO₂ evitat estima les emissions de xarxa associades a l'electricitat local i exportada que desplaça el sistema FV. Per a FV, bateria i inversor, el balanç net mostrat és emissions incorporades menys CO₂ evitat; signe negatiu indica emissions evitades superiors a les incorporades. No inclou les emissions incorporades dels equips tèrmics."),
            ("Degradació", "Pèrdua anual de producció FV aplicada de manera composta en la projecció (la producció baixa una fracció cada any)."),
            ("Any meteorològic representatiu", "Any complet PVGIS seleccionat per apropar-se a la mediana de producció solar i, quan hi ha dades, de graus-hora de calefacció. No cobreix tota la variabilitat climàtica interanual."),
            ("PVGIS / JRC", "PVGIS és el sistema d'informació geogràfica fotovoltaica de la Comissió Europea; JRC és el seu Centre Comú de Recerca. El model n'utilitza la sèrie horària de producció i meteorologia."),
            ("UA i graus-hora", "UA és el coeficient global de pèrdua de calor de l'edifici, en kW/K. El mode UA·ΔT estima la demanda sumant hora a hora UA × diferència positiva entre consigna interior i temperatura exterior; els graus-hora resumeixen aquesta diferència al llarg del temps."),
            ("Conductivitat i difusivitat del sòl", "La conductivitat (W/m·K) descriu com de bé el sòl transmet calor; la difusivitat (m²/s) descriu la rapidesa amb què s'hi propaga un canvi de temperatura. Són entrades estimades del dimensionament geotèrmic, que cal validar amb dades geotècniques."),
            ("Càrrega de disseny i ΔT útil", "La càrrega de disseny és la potència tèrmica punta estimada (kW) que el sistema ha de cobrir en condicions de disseny. ΔT útil és la diferència de temperatura emprada pel model entre el sòl i el circuit geotèrmic; no és una lectura mesurada del pou."),
            ("Flux tèrmic i pou geotèrmic", "El flux tèrmic per metre (W/m) és una capacitat estimada d'intercanvi amb el terreny. La longitud requerida es tradueix en un o més pous verticals amb sondes; el càlcul orienta costos i mides, però no substitueix un estudi geològic ni el projecte d'un instal·lador."),
            ("Inversor", "Equip que converteix el corrent continu dels panells en corrent altern utilitzable per la instal·lació/xarxa. Al cicle de vida se n'estima una reposició segons els anys i costos configurats."),
            ("Recomanació ponderada", "Rànquing tèrmic que combina cost anualitzat, emissions i energia no renovable amb els pesos configurats. No és sinònim de l'opció més barata: aquesta s'identifica separadament com a 'Menys cost'."),
            ("Millor combinació provada", "Combinació amb VAN més alt dins les mides FV/bateria que s'han simulat per a aquest cas. No demostra un òptim global: la graella no comprova espai de teulada, ombres noves, límits d'inversor ni pressupostos reals."),
            ("Any d'anàlisi tèrmica / vida del projecte", "L'horitzó tèrmic s'utilitza per repartir linealment el CAPEX en el cost anualitzat. La vida del projecte s'utilitza per projectar fluxos, inflació, descompte i reposicions. Poden ser horitzons diferents."),
        ]),
    ]
    sections = []
    for heading, entries in groups:
        definitions = "".join(
            f"<dt>{term}</dt><dd>{definition}</dd>"
            for term, definition in entries
        )
        sections.append(f'<div class="glossary-group"><h3>{heading}</h3><dl class="glossary-list">{definitions}</dl></div>')
    return '<div class="metric-note">Els imports amb €/any són valors anuals estimats. Els indicadors només són comparables quan comparteixen la mateixa demanda, període i supòsits. Les definicions següents expliquen també la base de comparació i les exclusions rellevants.</div>' + "".join(sections)


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
    <div class="exec-card"><div class="label">Retorn simple FV</div><div class="value">{payback_text}</div></div>
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
    <h3>Fonts de calor i fred</h3>
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
    <h3>Dimensionament geotèrmic</h3>
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
    <h3>Anàlisi d'estalvi: canvi de tecnologia de calefacció</h3>
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




def _personalized_analysis(thermal_summary, summary, economic_summary, config, combined_economic_summary=None):
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
    
    thermal_payback = (
        capex_diff / annual_cost_diff
        if capex_diff > 0 and annual_cost_diff > 0
        else None
    )

    # Determinar si hi ha un motiu econòmic o ambiental per estudiar el canvi.
    should_change = annual_cost_diff > 0 or emissions_diff > 100  # estalvi > 100€/any o > 100 kg CO2
    
    analysis_text = f"""
    <h3>Anàlisi personalitzada i recomanacions</h3>
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
            <strong style="color: var(--accent2);">Comparativa de fonts tèrmiques:</strong><br>
            <strong>{rec_name}</strong> (COP/η = {rec_performance:.2f}) és l'opció millor puntuada amb els pesos configurats; això, per si sol, no confirma que la inversió sigui rendible.
        </p>
        <ul style="line-height: 1.8;">
            <li><strong>Cost operatiu tèrmic:</strong> {'estalvi estimat de' if annual_cost_diff >= 0 else 'increment estimat de'} <strong>{abs(annual_cost_diff):.0f} €/any</strong> respecte del sistema actual.</li>
            <li><strong>Emissions operatives:</strong> {'reducció estimada de' if emissions_diff >= 0 else 'increment estimat de'} <strong>{abs(emissions_diff):.0f} kg CO2e/any</strong>.</li>
            <li><strong>Energia primària no renovable:</strong> {'reducció estimada de' if energy_diff >= 0 else 'increment estimat de'} <strong>{abs(energy_diff):.0f} kWh/any</strong>.</li>
        """
        
        if capex_diff > 0:
            if thermal_payback is not None:
                analysis_text += f"""
                <li><strong>CAPEX tèrmic addicional:</strong> {capex_diff:.0f} €; retorn simple orientatiu de {thermal_payback:.1f} anys, abans de reposicions i sense l'efecte conjunt FV+bateria.</li>
                """
            else:
                analysis_text += f"""
                <li><strong>CAPEX tèrmic addicional:</strong> {capex_diff:.0f} €. Amb l'estalvi operatiu calculat no es recupera aquesta inversió.</li>
                """
        elif capex_diff < 0:
            analysis_text += f"""
            <li><strong>CAPEX tèrmic:</strong> {abs(capex_diff):.0f} € inferior al del sistema actual.</li>
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
        final_is_viable = False
        combined_comparisons = (combined_economic_summary or {}).get("comparisons", [])
        tested_comparisons = (combined_economic_summary or {}).get("configuration_scenarios", [])
        combined_heat_pumps = [
            item for item in (tested_comparisons or combined_comparisons)
            if item.get("source_key") in {"aerotermia", "geotermia"}
        ]
        best_package = max(combined_heat_pumps, key=lambda item: item.get("npv", float("-inf")), default=None)
        if combined_comparisons and best_package and best_package.get("npv", 0) > 0:
            final_is_viable = True
            configuration_note = (
                f" amb FV {best_package['pv_peak_power_kwp']:.1f} kWp i bateria de {best_package['battery_capacity_kwh']:.1f} kWh"
                if "pv_peak_power_kwp" in best_package else ""
            )
            final_recommendation = (
                f"Per criteris econòmics, {best_package['source_name']}{configuration_note} és l'opció amb VAN positiu més alt "
                f"({best_package['npv']:.0f} €) respecte de {combined_economic_summary.get('reference_name', 'la referència')}, "
                "dins les combinacions provades i sota els preus, costos i horitzó configurats. És una estimació condicionada a aquests supòsits, no una garantia de rendibilitat."
            )
        elif combined_comparisons:
            final_recommendation = (
                f"Amb els supòsits actuals no s'aconsella invertir en cap combinació FV+bateria+bomba de calor provada respecte de "
                f"{combined_economic_summary.get('reference_name', 'la referència')}: cap alternativa té VAN positiu. "
                "Cal mantenir la comparació amb el sistema de referència o revisar pressupostos i tarifes abans de decidir."
            )
        elif thermal_payback is not None:
            final_is_viable = True
            final_recommendation = (
                f"Es pot estudiar {rec_name}: el retorn simple tèrmic és {thermal_payback:.1f} anys, "
                "abans de reposicions i sense l'efecte conjunt FV+bateria."
            )
        else:
            final_recommendation = (
                f"No hi ha retorn simple calculable per substituir {active_name} per {rec_name} amb l'estalvi operatiu actual; "
                "no s'ha d'interpretar com una inversió rendible."
            )
        analysis_text += f"""
        <p style="margin-top: 18px; padding: 12px; background: {'rgba(52, 211, 153, 0.1)' if final_is_viable else 'rgba(251, 191, 36, 0.1)'}; border-left: 4px solid {'var(--accent2)' if final_is_viable else 'var(--warn)'}; border-radius: 4px;">
            <strong style="color: {'var(--accent2)' if final_is_viable else 'var(--warn)'};">Conclusió de la comparativa tèrmica:</strong><br>
            {final_recommendation}
            {' La bateria existent forma part de l’escenari combinat, però no garanteix per si sola l’estalvi.' if battery_enabled else ''}
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
    <h3>Comparativa de fonts de calefacció: alternatives vs sistema actual</h3>
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
        configuration_scenarios = combined_summary.get("configuration_scenarios", [])
        heat_pump_options = [
            item for item in comparisons
            if item["source_key"] in {"aerotermia", "geotermia"}
        ]
        best_heat_pump = max(heat_pump_options, key=lambda item: item["npv"]) if heat_pump_options else None
        recommended = best_heat_pump if best_heat_pump and best_heat_pump["npv"] > 0 else None
        recommended_payback = (
            "No viable"
            if recommended is None or recommended["payback_years"] is None
            else f"{recommended['payback_years']:.1f} anys"
        )
        most_efficient = min(
            heat_pump_options,
            key=lambda item: next(
                source["input_energy_kwh"]
                for source in combined_summary.get("source_details", [])
                if source["source_key"] == item["source_key"]
            ),
        ) if combined_summary.get("source_details") and heat_pump_options else (best_heat_pump or comparisons[0])
        tested_heat_pumps = [
            item for item in configuration_scenarios
            if item.get("source_key") in {"aerotermia", "geotermia"}
        ]
        best_tested = max(tested_heat_pumps, key=lambda item: item.get("npv", float("-inf")), default=None)
        viable_tested = best_tested if best_tested and best_tested.get("npv", 0) > 0 else None
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
                is_recommended = recommended is not None and item["source_key"] == recommended["source_key"]
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

        tested_rows = []
        for item in sorted(tested_heat_pumps, key=lambda entry: entry.get("npv", float("-inf")), reverse=True)[:5]:
                payback = "No viable" if item.get("payback_years") is None else f"{item['payback_years']:.1f} anys"
                current_badge = '<span class="decision-badge reference">FV/bateria actuals</span>' if item.get("is_current_configuration") else ""
                tested_rows.append(f"""
                <tr>
                    <td><strong>{item['source_name']}</strong><br>{current_badge}</td>
                    <td class="numeric">{item['pv_peak_power_kwp']:.1f} kWp</td>
                    <td class="numeric">{item['battery_capacity_kwh']:.1f} kWh</td>
                    <td class="numeric">{item.get('input_energy_kwh', 0.0):.0f} kWh/any</td>
                    <td class="numeric">{item.get('grid_import_kwh', 0.0):.0f} kWh/any</td>
                    <td class="numeric">{item['annual_saving']:.0f} €/any</td>
                    <td class="numeric">{payback}</td>
                    <td class="numeric">{item['emissions_kg_co2e']:.0f} kg CO2e/any</td>
                    <td class="numeric">{item['npv']:.0f} €</td>
                </tr>
                """)

        scenario_section = ""
        if configuration_scenarios:
                best_tested_text = (
                    f"{viable_tested['source_name']}, FV {viable_tested['pv_peak_power_kwp']:.1f} kWp, "
                    f"bateria {viable_tested['battery_capacity_kwh']:.1f} kWh; VAN {viable_tested['npv']:.0f} €."
                    if viable_tested else
                    "Cap combinació provada amb bomba de calor té VAN positiu amb els supòsits actuals."
                )
                scenario_section = f"""
                <h4>Combinació de sistema amb millor resultat econòmic provat</h4>
                <div class="metric-note">
                    Millor resultat: <strong>{best_tested_text}</strong>
                    S'han provat FV al 60%, 100% i 160% de la potència actual, i bateries de 0, 1× i 2× la capacitat de referència.
                    Es mantenen el perfil horari, orientació FV, ubicació, demanda i tarifes del cas. És un cribratge de mides candidates:
                    no verifica superfície de teulada, ombres noves, límits d'inversor, subvencions ni pressupostos d'instal·lador.
                    Les emissions són operatives de la font tèrmica segons els factors del catàleg; no representen la petjada neta de cicle de vida del paquet FV/bateria.
                </div>
                <div class="combined-table-wrap">
                    <table class="combined-table">
                        <thead><tr>
                            <th>Calefacció</th><th>FV</th><th>Bateria</th><th>Energia d'entrada tèrmica</th>
                            <th>Importació de xarxa</th><th>Estalvi any 1</th><th>Retorn simple</th>
                            <th>Emissions operatives tèrmiques</th><th>VAN</th>
                        </tr></thead>
                        <tbody>{''.join(tested_rows)}</tbody>
                    </table>
                </div>
                """

        return f"""
        <h3>Anàlisi econòmica combinada: FV + bateria + calefacció elèctrica</h3>
        <div class="metric-note">
            Aquesta anàlisi compara dos escenaris per al mateix habitatge: referència amb
            <strong>{combined_summary['reference_name']}</strong> i tota l'electricitat domèstica comprada a la xarxa,
            davant del paquet nou FV + bateria + calefacció elèctrica. El CAPEX del paquet inclou FV, bateria,
            costos d'instal·lació i calefacció; el CAPEX de referència inclou el sistema tèrmic actual.
            El cost anual del paquet inclou la factura elèctrica neta (importacions menys excedents), manteniment tèrmic
            i manteniment FV. El cas de referència inclou el cost anual de {combined_summary['reference_name']} i la factura elèctrica domèstica sense FV.
            El component FV+bateria es desglossa en {combined_summary.get('pv_capex', 0.0):.0f} € de sistema FV,
            {combined_summary.get('battery_capex', 0.0):.0f} € de bateria i {combined_summary.get('installation_extra', 0.0):.0f} € d'instal·lació/BOS (inclou l'allowance inicial d'inversor).
        </div>
                <div class="combined-summary">
                    <div class="combined-highlight primary">
                        <div class="highlight-label">{'Millor bomba de calor amb FV/bateria actuals' if recommended else 'Viabilitat de la configuració actual'}</div>
                        <div class="highlight-value">{recommended['source_name'] if recommended else 'Cap opció viable'}</div>
                        <div class="highlight-detail">{'VAN: ' + f"{recommended['npv']:.0f} € · Payback: {recommended_payback}" if recommended else 'Cap bomba de calor té VAN positiu amb els supòsits actuals.'}</div>
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
        {scenario_section}
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
    if battery_diag is not None and "battery_soc_pct" in df.columns:
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
        <h3>Dimensionament de la bateria</h3>
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
    <h3>Anàlisi econòmica de la instal·lació</h3>
    <div class="kpi-grid">
      {_kpi("Cost total instal·lacio", f"{economic_summary['capex_total']:.0f} €")}
      {_kpi("Cost plaques FV", f"{economic_summary['pv_capex']:.0f} €")}
      {_kpi("Cost bateria", f"{economic_summary['battery_capex']:.0f} €", "accent2")}
      {_kpi("Estalvi anual", f"{economic_summary['annual_bill_saving']:.0f} €/any", "accent2")}
      {_kpi("Flux net anual", f"{economic_summary['annual_cashflow']:.0f} €/any", "warn")}
    {_kpi("Retorn simple FV", payback_text, "warn")}
    {_kpi(f"VAN FV/bateria {economic_summary.get('project_life_years', 25)} anys", f"{economic_summary.get('npv', economic_summary['npv_25y']):.0f} €", "accent2")}
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
    <h3>Vida útil i degradació del sistema</h3>
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
    personalized_analysis_html = _personalized_analysis(
        thermal_summary, summary, economic_summary, config, combined_economic_summary
    )
    combined_economic_html = _combined_economic_section(combined_economic_summary)

    first_year_kpis = f"""
    <h3>Indicadors del primer any</h3>
    <div class="kpi-grid">
      {_kpi("Producció any 1", f"{summary['total_pv']:.0f} kWh")}
      {_kpi("Autoconsum any 1", f"{summary['self_consumed']:.0f} kWh", "accent2")}
    {_kpi("Estalvi de factura FV any 1", f"{economic_summary['annual_bill_saving']:.0f} €")}
      {_kpi("Flux net anual", f"{economic_summary['annual_cashflow']:.0f} €", "warn")}
      {_kpi("CO2 evitat any 1", f"{environmental_summary.get('avoided_co2_per_year_kg', 0):.0f} kg CO2e")}
      {_kpi("Taxa d'autoconsum", f"{summary['self_consumption_rate']:.1f} %", "accent2")}
    </div>
    """

    lifecycle_kpis = f"""
    <h3>Indicadors del projecte ({project_life_years} anys)</h3>
    <div class="kpi-grid">
      {_kpi("Producció total estimada", f"{sum(lifecycle_projection.get('annual_production_kwh', [])):.0f} kWh")}
      {_kpi(f"CO2 evitat en {environmental_summary.get('panel_life_years', panel_life_years)} anys", f"{environmental_summary.get('co2_saved_kg_over_life', 0):.0f} kg CO2e")}
      {_kpi(f"VAN {economic_summary.get('project_life_years', 25)} anys", f"{economic_summary.get('npv', economic_summary['npv_25y']):.0f} €", "accent2")}
      {_kpi("Flux caixa acumulat final", f"{lifecycle_projection.get('cumulative_cashflow_eur', [])[-1]:.0f} €", "warn")}
      {_kpi(f"Producció any {project_life_years}", f"{lifecycle_projection.get('annual_production_kwh', [0])[-1]:.0f} kWh")}
      {_kpi(f"CO2 evitat any {project_life_years}", f"{lifecycle_projection.get('avoided_co2_kg', [0])[-1]:.0f} kg CO2e")}
    </div>
    """

    identity = _report_identity(config, summary, thermal_summary)
    chapters = [
        ("results", "Resultats", "Les xifres clau del primer any i la lectura inicial del projecte."),
        ("system", "Sistema i autoconsum", "Configuració del cas, energia produïda, consum i encaix entre tots dos."),
    ]
    if thermal_summary:
        chapters.append(("thermal", "Calefacció i alternatives", "Comparativa tècnica, econòmica i ambiental de les fonts tèrmiques."))
    chapters.append(("economics", "Viabilitat i cicle de vida", "Inversió, estalvis, flux de caixa, degradació i emissions incorporades."))
    if battery_diag is not None:
        chapters.append(("battery", "Dimensionament de la bateria", "Saturacions, buidatges, límits de potència i ús anual estimat."))
    chapters.append(("glossary", "Glossari de termes", "Definicions, fórmules, bases de comparació i límits dels indicadors de l'informe."))
    chapters.append(("methodology", "Metodologia i fonts", "Dades emprades, abast dels càlculs i referències per interpretar-los."))
    chapter_numbers = {chapter_id: f"{index:02d}" for index, (chapter_id, _, _) in enumerate(chapters, start=1)}
    toc_html = "\n".join(
        f'<li><a class="toc-link" href="#{chapter_id}"><span class="toc-number">{chapter_numbers[chapter_id]}</span>'
        f'<span><span class="toc-title">{escape(title)}</span><div class="toc-description">{escape(description)}</div></span>'
        f'<span class="toc-arrow" aria-hidden="true">→</span></a></li>'
        for chapter_id, title, description in chapters
    )
    methodology_html = _methodology_section(config, identity)
    glossary_html = _glossary_section()

    html = f"""<!DOCTYPE html>
<html lang="ca">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Energia Clara · {identity['case_name']}</title>{CARD_CSS}</head>
<body>
  <section class="front-page" aria-label="Portada de l'informe">
    <div class="cover-brand"><div class="cover-mark" aria-hidden="true">E</div><div><div class="cover-brand-name">Energia Clara</div><div class="cover-brand-sub">Simulador d'energia i sistemes tèrmics</div></div></div>
    <div class="cover-main">
      <div class="cover-eyebrow">Informe tècnic · anàlisi energètica</div>
      <h1>Energia que<br>encaixa.</h1>
      <p class="cover-description">Producció fotovoltaica, autoconsum i alternatives de climatització en una lectura clara del sistema i del seu horitzó econòmic i ambiental.</p>
      <div class="cover-case"><div class="cover-case-label">Cas d'estudi</div><div class="cover-case-name">{identity['case_name']}</div></div>
    </div>
    <div class="cover-meta">
      <div class="cover-meta-item"><div class="cover-meta-label">Elaborat per</div><div class="cover-meta-value">Aniol Calafell</div></div>
      <div class="cover-meta-item"><div class="cover-meta-label">Any meteorològic PVGIS</div><div class="cover-meta-value">{identity['year']} · {identity['complete_years']} anys revisats</div></div>
      <div class="cover-meta-item"><div class="cover-meta-label">Data de l'informe</div><div class="cover-meta-value">{identity['date']}</div></div>
    </div>
  </section>

  <section class="index-page" id="index" aria-labelledby="index-title">
    <div class="section-kicker">Guia de lectura</div>
    <h1 id="index-title">Índex de l'informe</h1>
    <p class="index-lead">Els blocs segueixen l'ordre de decisió: primer els resultats, després el sistema que els genera, les alternatives i els supòsits que permeten interpretar-los.</p>
    <ol class="toc-list">{toc_html}</ol>
  </section>

  <nav class="report-toolbar" aria-label="Eines de l'informe">
    <a class="toolbar-brand" href="#index">Energia Clara</a>
    <div class="toolbar-actions"><a class="toolbar-link" href="#index">Ves a l'índex ↑</a><button class="print-button" onclick="window.print()">Imprimeix / desa en PDF</button></div>
  </nav>

  <main class="report-container">
    <section class="report-section" id="results">
      {_chapter_intro(chapter_numbers['results'], "Lectura ràpida", "Resultats executius", "Els indicadors principals de l'escenari analitzat.")}
      {_executive_summary(summary, economic_summary)}
      {first_year_kpis}
    </section>

    <section class="report-section" id="system">
      {_chapter_intro(chapter_numbers['system'], "Configuració i energia", "El cas i el balanç energètic", "Dades de partida, producció i relació horària entre l'energia solar i la demanda.")}
      {_system_summary_section(config)}
      {kpis}
      <h3>Autoconsum i autosuficiència</h3>
      {_autoconsumption_narrative(summary)}
      <h3>Producció i consum al llarg de l'any</h3>
      <div class="chart-block">{pio.to_html(fig_monthly, include_plotlyjs='cdn', full_html=False)}</div>
      <div class="chart-block">{pio.to_html(fig_rates, include_plotlyjs=False, full_html=False)}</div>
      <div class="chart-block">{pio.to_html(fig_daily, include_plotlyjs=False, full_html=False)}</div>
      <h3>Perfil horari per estació</h3>
      <div class="chart-block">{pio.to_html(fig_profile, include_plotlyjs=False, full_html=False)}</div>
    </section>

    {f'''<section class="report-section" id="thermal">
      {_chapter_intro(chapter_numbers['thermal'], "Alternatives", "Calefacció i sistemes tèrmics", "Comparació de costos, emissions i energia per cobrir la demanda tèrmica del cas.")}
      {thermal_comparison_html}
      {combined_economic_html}
      {personalized_analysis_html}
      {_thermal_section(thermal_summary)}
      {geothermal_design_html}
      {_thermal_savings_section(thermal_summary)}
      {thermal_charts_html}
    </section>''' if thermal_summary else ''}

    <section class="report-section" id="economics">
      {_chapter_intro(chapter_numbers['economics'], "Horitzó del projecte", "Viabilitat econòmica i cicle de vida", "Inversió inicial, estalvi, reposicions i trajectòria de l'impacte ambiental.")}
      {economic_html}
      {lifecycle_kpis}
      {lifecycle_html}
      <h3>Flux de caixa i evolució de la instal·lació</h3>
      <div class="chart-block">{pio.to_html(fig_cashflow, include_plotlyjs=False, full_html=False)}</div>
      <div class="chart-block">{pio.to_html(fig_production_lifecycle, include_plotlyjs=False, full_html=False)}</div>
      <div class="chart-block">{pio.to_html(fig_emissions_lifecycle, include_plotlyjs=False, full_html=False)}</div>
    </section>

    {f'''<section class="report-section" id="battery">
      {_chapter_intro(chapter_numbers['battery'], "Dimensionament", "Diagnòstic de la bateria", "Indicadors de saturació, buidatge i aprofitament del sistema d'emmagatzematge.")}
      {battery_html}
      {battery_figs_html}
    </section>''' if battery_diag is not None else ''}

        <section class="report-section" id="glossary">
            {_chapter_intro(chapter_numbers['glossary'], "Referència", "Glossari de termes", "Què mesura cada indicador, respecte de quina base i quins costos o efectes no inclou.")}
            {glossary_html}
        </section>

    <section class="report-section" id="methodology">
      {_chapter_intro(chapter_numbers['methodology'], "Transparència", "Metodologia, abast i fonts", "Els supòsits i les dades que cal tenir presents abans d'interpretar o comparar els resultats.")}
      {methodology_html}
      <div class="report-footer">Energia Clara · Informe del cas {identity['case_name']} · Elaborat per Aniol Calafell · {identity['date']}</div>
    </section>
  </main>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
