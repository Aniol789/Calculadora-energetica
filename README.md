# Simulador anual d'instal·lacions fotovoltaiques

Simula la producció, el consum i (opcionalment) una bateria domèstica
d'una instal·lació fotovoltaica al llarg d'un any, per a qualsevol
ubicació i configuració que triïs.

## Com funciona (resum)

| Peça | Font de dades |
|---|---|
| Irradiació solar i producció FV horària | **PVGIS** (Comissió Europea, JRC) — API pública, gratuïta, sense clau |
| Consum de la llar | Perfil sintètic per defecte (editable) o CSV propi |
| Bateria | Model físic simplificat (càrrega/descàrrega hora a hora) |

PVGIS és la mateixa base de dades que fan servir instal·ladors i estudis
oficials: li dónes latitud/longitud + característiques del sistema
(potència pic, inclinació, orientació, pèrdues) i et retorna la producció
horària estimada durant un any, tenint en compte la irradiació real de la
zona, temperatura, etc. És fiable i gratuïta, però necessites connexió a
internet quan executis l'script.

El consum **no** té cap font pública equivalent amb el teu perfil real, així
que es genera una corba sintètica raonable (punta matí/vespre, més consum a
l'hivern) escalada al kWh anual que li indiquis. Si tens el teu consum
horari real (moltes distribuïdores el faciliten en CSV des de l'àrea de
client), el pots connectar directament — veure més avall.

## Estructura del projecte

```
pv_simulator/
├── config.py          <- AQUÍ canvies ubicació, sistema FV, consum i bateria
├── pvgis_client.py     <- connexió amb l'API de PVGIS
├── consumption.py      <- perfil de consum per defecte / carregador de CSV propi
├── battery.py           <- simulació de la bateria (distingeix límits de potència vs capacitat)
├── analysis.py            <- resums diaris/mensuals i diagnòstic de dimensionament de bateria
├── thermal.py             <- fonts de calor/fred, energia primària, emissions i costos
├── report.py               <- genera l'informe HTML interactiu (Plotly)
├── simulate.py               <- script principal, executa tot i genera les sortides
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
   - Una recomanació automàtica en text segons aquests indicadors.
2. **`resultats_horaris.csv`** — les 8760 hores de l'any amb producció,
   consum, excedent/dèficit, import/export i estat de la bateria.
3. **`resultats_diaris.csv`** — un resum per a cada dia de l'any (producció,
   consum, autosuficiència %, i si aquell dia la bateria es va saturar o buidar).

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
font indicada a `payback_reference`. Els factors i preus són valors orientatius
inicials i es poden modificar amb `source_overrides`.

La font indicada a `active_source` s'integra en la simulació FV: la seva
demanda elèctrica horària se suma al consum domèstic i és coberta per la FV,
la bateria o la xarxa. El CSV horari conserva `base_load_kwh`,
`thermal_electricity_kwh` i `load_kwh` per auditar el balanç.
Si la font activa és gas, gasoil o biomassa, no s'afegeix consum elèctric
tèrmic a l'escenari actual. Les alternatives elèctriques es calculen després
sota una FV i una bateria iguals a les existents.

## Posar-ho en marxa a VS Code

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
5. Obre `config.py`, canvia ubicació/potència/consum/bateria com vulguis.
6. Executa:
   ```bash
   python simulate.py
   ```
   Et sortirà el resum anual per terminal, un CSV amb el detall horari
   (`resultats_horaris.csv`) i un gràfic mensual (`produccio_vs_consum.png`).

## Com avaluar diferents casos

Per comparar instal·lacions/ubicacions diferents, la manera més simple és
duplicar `config.py` (p.ex. `config_barcelona.py`, `config_girona.py`) i
canviar la primera línia de `simulate.py` (`import config`) pel fitxer que
vulguis, o bé anar canviant els valors i executant de nou — cada execució
sobreescriu `resultats_horaris.csv`, així que si vols conservar resultats
canvia el nom de sortida a `config.py` (`OUTPUT["hourly_csv_path"]`) abans
de cada prova.

### Afegir el teu propi consum real
A `config.py`:
```python
CONSUMPTION = {
    "profile": "custom_csv",
    "custom_csv_path": "el_meu_consum.csv",
}
```
El CSV ha de tenir dues columnes (data/hora i kWh) amb 8760 files (una per
hora de l'any).

### Activar bateria
```python
BATTERY = {
    "enabled": True,
    "capacity_kwh": 10.0,
    ...
}
```

## Sobre GitHub (breu introducció)

GitHub és un servei on pots desar el teu codi "al núvol", portar un
historial de canvis (Git) i compartir-lo o versionar-lo. No és
imprescindible per fer córrer aquest projecte — funciona igual només amb
els fitxers al teu ordinador — però és útil si vols:
- Tenir còpia de seguretat / historial de versions.
- Compartir el projecte o treballar-hi des de diferents ordinadors.
- Que quedi "públic" com a portfoli.

Passos bàsics (des del terminal de VS Code, dins la carpeta del projecte):
```bash
git init
git add .
git commit -m "Primera versio del simulador FV"
```
Després, crea un repositori buit a https://github.com (botó "New repository"),
i connecta'l:
```bash
git remote add origin https://github.com/EL_TEU_USUARI/pv_simulator.git
git branch -M main
git push -u origin main
```
A partir d'aquí, cada cop que facis canvis:
```bash
git add .
git commit -m "Descripcio del canvi"
git push
```
VS Code també té una pestanya de "Source Control" (icona de branca al
lateral) des d'on pots fer tot això amb clics, sense escriure les ordres.

## Limitacions actuals / possibles ampliacions

- El perfil de consum per defecte és una aproximació, no dades mesurades.
- No inclou encara anàlisi econòmica (preu kWh, compensació d'excedents,
  amortització de la instal·lació) — es podria afegir fàcilment a partir
  del CSV horari generat.
- PVGIS dona un any "representatiu"; per anàlisi de risc interanual caldria
  creuar-ho amb diverses sèries d'anys reals.
- La simulació de bateria és energètica (balanç kWh), no modela degradació
  ni límits tèrmics del fabricant.
