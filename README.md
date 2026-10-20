# Calculadora energètica residencial

Eina digital per estudiar sistemes residencials amb fotovoltaica, bateria i
calefacció elèctrica o de combustible. El projecte continua un treball final
de màster: trasllada càlculs que abans es feien manualment amb fulls de càlcul
a una simulació horària reproduïble, una comparativa tècnicoeconòmica i un
informe HTML interactiu.

El desenvolupament s'ha fet amb suport d'eines d'IA, però els resultats els
calcula codi Python determinista a partir de dades i hipòtesis configurables.
No és un sistema d'IA que decideixi pel client: les fórmules, comparadors i
limitacions del model es poden revisar.

## Com funciona (resum)

| Peça | Font de dades |
|---|---|
| Irradiació solar i producció FV horària | **PVGIS** (Comissió Europea, JRC) — API pública, gratuïta, sense clau |
| Consum de la llar | Perfil sintètic per defecte (editable) o CSV propi |
| Bateria | Model físic simplificat (càrrega/descàrrega hora a hora) |
| Sistemes tèrmics | Catàleg editable de rendiments, costos i factors ambientals |
| Economia | Fluxos anuals, reposicions modelades, inflació, descompte i VAN |

PVGIS proporciona una sèrie horària estimada segons ubicació i configuració
FV. A cada hora, el simulador calcula el balanç entre generació, consum,
importació de xarxa, excedents i emmagatzematge. PVGIS és una font de dades de
referència, però un any representatiu no substitueix mesures locals ni una
anàlisi de variabilitat interanual.

El consum **no** té cap font pública equivalent amb el teu perfil real, així
que es genera una corba sintètica raonable (punta matí/vespre, més consum a
l'hivern) escalada al kWh anual que li indiquis. Si tens el teu consum
horari real (moltes distribuïdores el faciliten en CSV des de l'àrea de
client), el pots connectar directament — veure més avall.

## Què calcula

- Balanç energètic horari i resums mensuals, diaris i estacionals.
- Autoconsum, autosuficiència, electricitat importada i excedents exportats.
- Bateria amb límits separats de capacitat (kWh) i potència (kW), i diagnòstics d'ús.
- Comparació de sis fonts tèrmiques per cost, rendiment, energia primària i emissions.
- CAPEX/OPEX, cost anualitzat, retorn simple, fluxos de caixa i VAN.
- Graella de nou combinacions FV/bateria i alternatives de calefacció elèctrica.
- Informe HTML interactiu amb gràfics Plotly, conclusions i glossari.

## Estructura del projecte

```
├── streamlit_app.py   <- editor d'escenaris al navegador
├── case_manager.py    <- càrrega i desament de casos JSON
├── simulate.py        <- orquestra la simulació i les sortides
├── pvgis_client.py    <- obtenció i validació de dades PVGIS
├── consumption.py     <- perfils de consum sintètics o CSV propi
├── battery.py         <- simulació horària de bateria
├── thermal.py         <- fonts tèrmiques, rendiments i costos
├── analysis.py        <- resums, projeccions i comparatives econòmiques
├── report.py          <- informe HTML, gràfics i glossari
├── cases/             <- cas demostratiu i casos locals
├── tests/             <- proves de càlcul i coherència
└── requirements.txt
```

## Sortides que genera cada execució

1. **`informe.html`** — s'obre sol al navegador. Conté targetes amb els KPI
   principals, gràfics interactius (producció vs consum mensual, evolució
   diària, perfil horari típic per estació) i, si la bateria està activada,
   un bloc de **diagnòstic de dimensionament**:
   - Dies que la bateria arriba al 100% (indica que li falta **capacitat**, kWh).
   - Dies que la bateria es buida (indica **capacitat** insuficient o poca producció FV).
   - Dies limitats per la **potència** de càrrega/descàrrega (kW) — diferent
     de la capacitat: pot passar que sobri energia però l'inversor/bateria
     no la pugui absorbir prou ràpid.
   - Cicles complets equivalents/any (útil per estimar la vida útil).
   - Recomanacions automàtiques per distingir límits de capacitat i potència.
2. **`resultats_horaris.csv`** — les hores de l'any amb producció, consum,
   excedent/dèficit, importació/exportació i estat de la bateria.
3. **`resultats_diaris.csv`** — resums diaris de producció, consum i
   autosuficiència, incloent si la bateria s'ha saturat o buidat.

## Anàlisi de fonts de calor i fred

El bloc tèrmic compara gas natural, gasoil, aerotèrmia, geotèrmia, biomassa i
resistència elèctrica. A `config.py`, modifica la demanda, la potència de
disseny, els anys d'anàlisi i el pes de cada criteri:

```python
THERMAL = {
   "enabled": True,
   "annual_heat_demand_kwh": 10000,
   "active_source": "aerotermia",
   "peak_power_kw": 8,
   "analysis_years": 20,
   "payback_reference": "gas_natural",
   "weights": {"cost": 0.34, "environment": 0.33, "energy": 0.33},
}
```

L'informe mostra energia primària total i no renovable, emissions operatives,
cost del recurs, electricitat auxiliar, manteniment, inversió i cost
anualitzat. També inclou gràfics de comparació energètica, emissions, costos,
inversió i període de retorn. El període de retorn es calcula respecte de la
font tèrmica activa del cas; `payback_reference` només s'utilitza si no hi ha
cap font activa vàlida. Els factors i preus són valors orientatius inicials i
es poden modificar amb `source_overrides`.

L'informe també compara una graella de potència FV (60%, 100% i 160% de la
configuració actual) i capacitat de bateria (0, 1× i 2× la capacitat de
referència), juntament amb aerotèrmia, geotèrmia i resistència. La classificació
econòmica usa el VAN del paquet i els costos de reposició configurats. És un
cribratge basat en el mateix perfil horari, orientació, ubicació, demanda i
tarifes; no comprova límits de teulada/inversor, ombres, pressupostos d'obra ni
emissions incorporades de cada alternativa. Cal confirmar la combinació amb
dades i ofertes específiques abans d'invertir.

La font indicada a `active_source` s'integra en la simulació FV: la seva
demanda elèctrica horària se suma al consum domèstic i és coberta per la FV,
la bateria o la xarxa. El CSV horari conserva `base_load_kwh`,
`thermal_electricity_kwh` i `load_kwh` per auditar el balanç.
Si la font activa és gas, gasoil o biomassa, no s'afegeix consum elèctric
tèrmic a l'escenari actual. Les alternatives elèctriques es calculen després
sota una FV i una bateria iguals a les existents.

## Instal·lació i ús

1. **Instal·la Python** (3.9 o superior) si no el tens: https://www.python.org/downloads/
2. Obre la carpeta `pv_simulator` a VS Code (`File > Open Folder`).
3. Obre un terminal dins de VS Code (`Terminal > New Terminal`) i crea un
   entorn virtual (recomanat, per no barrejar llibreries amb altres projectes):
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```
4. Instal·la les dependències:
   ```bash
   pip install -r requirements.txt
   ```
5. Inicia l'editor web:
   ```bash
   streamlit run streamlit_app.py
   ```
   Des de l'app pots configurar un cas, desar-lo i generar l'informe HTML.
6. També pots executar la simulació des del terminal:
   ```bash
   python simulate.py
   ```
   Cal connexió a internet perquè el simulador obtingui dades de PVGIS.

## Com avaluar diferents casos

Per comparar ubicacions o sistemes, crea o duplica un cas des de l'editor
Streamlit. Les sortides CSV i HTML es regeneren a cada execució; desa o
exporta només resultats que hagis revisat i anonimitzat.

### Afegir el teu propi consum real
A `config.py`:
```python
CONSUMPTION = {
    "profile": "custom_csv",
    "custom_csv_path": "el_meu_consum.csv",
}
```
El CSV ha de contenir una sèrie horària completa amb data/hora i kWh. Un any
normal té 8760 hores i un any de traspàs 8784.

### Activar bateria
```python
BATTERY = {
    "enabled": True,
    "capacity_kwh": 10.0,
    ...
}
```

### Executar les proves

```bash
python -m unittest discover -s tests -v
```

## Publicació i privacitat

Abans de fer públic el repositori, revisa coordenades, casos JSON, CSV de
consum, informes HTML i captures de pantalla. No hi publiquis factures ni
dades identificables de clients. El `.gitignore` exclou les sortides
generades i els casos locals; `cases/default_case.json` és el cas demostratiu
versionat i també s'ha de revisar abans de publicar-lo.

El codi d'aquest repositori es distribueix sota la llicència
[Apache 2.0](LICENSE). Permet utilitzar, copiar, modificar i redistribuir el
programari, inclòs comercialment, subjecte a les seves condicions, com ara
incloure una còpia de la llicència i conservar els avisos de copyright i
atribució. El fitxer [NOTICE](NOTICE) identifica l'autor original i s'ha de
conservar quan es redistribueixi el projecte o una obra derivada. Apache 2.0
també inclou una concessió de patents. És una llicència permissiva: no impedeix
que altres persones copiïn o reutilitzin el codi si compleixen aquests termes.

## Limitacions actuals / possibles ampliacions

- El perfil de consum per defecte és una aproximació, no dades mesurades.
- Els preus, manteniments, rendiments i emissions del catàleg tèrmic són hipòtesis orientatives i editables, no ofertes ni dades específiques d'una màquina. Cal substituir-los per pressupostos i fitxes del projecte abans de prendre decisions d'inversió.
- La bomba de calor aplica una corba termodinàmica simplificada al COP del punt de referència. No és un SCOP certificat; per representar un equip concret calen els seus punts de rendiment del fabricant.
- En mode `annual_kwh`, la demanda anual coneguda es conserva i la temperatura només en distribueix les hores i ajusta el COP. En mode `heat_loss_coefficient`, la demanda s'estima com `UA × max(consigna − T exterior, 0)` hora a hora. El coeficient UA s'ha de calibrar amb factures o un càlcul de pèrdues de l'edifici.
- PVGIS selecciona un any complet representatiu de producció FV i graus-hora de calefacció. Una sola sèrie anual no quantifica la variació interanual ni els extrems meteorològics.
- La projecció econòmica aplica una indexació general i no prediu els preus reals de cada energia durant 25 anys. S'ha d'interpretar com una hipòtesi d'escenari i completar amb sensibilitat per combustible, electricitat i manteniment.
- La simulació de bateria és energètica (balanç kWh), no modela degradació ni límits tèrmics del fabricant.

## Obrir l'app web al mòbil (mateixa xarxa Wi-Fi)

1. Connecta l'ordinador i el mòbil a la mateixa xarxa Wi-Fi.
2. A VS Code, obre un terminal a la carpeta del projecte i activa l'entorn virtual si en fas servir un. Instal·la les dependències amb `pip install -r requirements.txt`.
3. Inicia l'app amb `streamlit run streamlit_app.py --server.address 0.0.0.0`.
4. A Windows, executa `ipconfig` i apunta l'adreça IPv4 de l'adaptador Wi-Fi (per exemple `192.168.1.42`).
5. Al navegador del mòbil, obre `http://192.168.1.42:8501`, substituint l'adreça d'exemple per la de l'ordinador. Si Windows demana permís pel tallafoc, permet l'accés a la xarxa privada.

L'ordinador ha de continuar encès i executant Streamlit. Aquesta adreça només serveix dins la xarxa local; per accedir-hi des de fora cal desplegar l'app en un servei d'allotjament i configurar-ne l'accés.

## Deploy for access from any network

To keep the app available while your computer is off, deploy it to a cloud service. One straightforward option is [Streamlit Community Cloud](https://share.streamlit.io/):

1. Push the project changes to GitHub and sign in to Streamlit Community Cloud with an account that can access the repository.
2. Choose **Create app**, select the repository, the `main` branch, and `streamlit_app.py`.
3. In **Advanced settings**, choose a Python version compatible with the project dependencies, then deploy. Streamlit installs packages listed in `requirements.txt`.
4. Once deployment finishes, open the `*.streamlit.app` URL on your phone and bookmark it or add it to your home screen.
5. Under **Settings / Sharing**, restrict access to your account if private sharing is available on your plan. If you make the app public, anyone with the link can use it.

The app does not save shared case or report files on the server: each browser uses its own session state. Download a case JSON to keep it between sessions. Uploaded consumption CSV files and generated reports are temporary; download results before closing or refreshing the page. Consumption data is sent to the app server for calculation, and coordinates are sent to PVGIS to retrieve solar and weather data.

Free services may suspend inactive apps, so the first visit after a period of inactivity can take longer while the app starts. Streamlit Cloud menu names and privacy options may vary by plan and account settings.

## Referències de dades

- [PVGIS, servei API i documentació del JRC](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/api-non-interactive-service_en): producció FV i dades meteorològiques horàries.
- [Eurostat, preus d'electricitat domèstica (nrg_pc_204)](https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_204/default/table): mitjanes semestrals per país i banda de consum.
- [Eurostat, preus de gas domèstic (nrg_pc_202)](https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_202/default/table): mitjanes semestrals per país i banda de consum.
- [AVEBIOM, índex de preus de biocombustibles sòlids](https://avebiom.org/actividades/indice-de-precios-biocombustibles-solidos/): seguiment periòdic del preu del pellet.
- [MITECO, factors del registre de petjada de carboni](https://www.miteco.gob.es/es/cambio-climatico/temas/registro-huella/huella-de-carbonoinscripcion.html): consulta els factors oficials disponibles per any i combustible.
- [CYPE, preu de referència d'un sondeig geotèrmic](https://carm.generadordeprecios.info/obra_nueva/Instalaciones/IC_Calefaccion__climatizacion_y_A/Geotermia/Sondeo_geotermico.html) i [estudi TRI-HP](https://www.tri-hp.eu/fileadmin/downloads/Deliverables/D1.4_-_Economic_assessment_of_TRI-HP_solutions.pdf): referències per al cost de perforació; el material de sonda/reblert i la mobilització s'han de pressupostar per projecte.
- [IEA-PVPS, informe nacional d'Espanya 2023](https://www.iea-pvps.org/wp-content/uploads/2024/12/IEA-PVPS-2023-National-Survey-Report-Spain.pdf): preu mitjà reportat de 1,4 €/W per a sistemes residencials FV instal·lats de 5–10 kW. La base del model és menor perquè hi suma el 12% de costos d'instal·lació addicionals.
- [EUPD Research, preus d'emmagatzematge residencial H1 2025](https://www.ess-news.com/2025/07/23/eupd-research-home-storage-grows-across-europe-in-first-half-of-2025/): referència de 711 €/kWh per a bateries residencials a Alemanya; és una referència de mercat, no un pressupost local.
