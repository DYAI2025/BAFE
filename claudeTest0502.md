# claudeTest0502 – Vollständige Funktions- und Formatdokumentation BAFE

**Projekt:** BAFE (BaZi-Astrology Fusion Engine)
**Version:** 0.2.0 / API 1.0.0-rc0
**Datum:** 2026-02-06
**Autor:** Claude Opus 4 – automatisierte Codebase-Analyse

---

## Inhaltsverzeichnis

- [1. Projektüberblick & Architektur](#1-projektüberblick--architektur)
- [2. Modulabhängigkeiten](#2-modulabhängigkeiten)
- [3. Datenstrukturen (types.py, constants.py)](#3-datenstrukturen)
- [4. Core-Berechnungsfunktionen](#4-core-berechnungsfunktionen)
  - [4.1 bazi.py – Hauptberechnungs-Engine](#41-bazipy)
  - [4.2 ephemeris.py – Swiss Ephemeris Backend](#42-ephemerispy)
  - [4.3 jieqi.py – Sonnenterm-Berechnungen](#43-jieqipy)
  - [4.4 time_utils.py – Zeitkonvertierung](#44-time_utilspy)
- [5. API-Endpoints & Request/Response-Formate](#5-api-endpoints) *(Iteration 2)*
- [6. Fusion-Modul & Western-Modul](#6-fusion-modul) *(Iteration 2)*
- [7. BAFE-Subpackage (Contract-First Validator)](#7-bafe-subpackage) *(Iteration 3)*
- [8. Verifikation: BaZi-Chart, Ephemeriden, Fusion-Mathematik](#8-verifikation) *(Iteration 3)*
- [9. Testabdeckung & Golden Vectors](#9-testabdeckung) *(Iteration 3)*

---

## 1. Projektüberblick & Architektur

### 1.1 Was ist BAFE?

BAFE ist eine **deterministische astronomische Berechnungs-Engine** für chinesische Astrologie (Vier Säulen des Schicksals / BaZi) kombiniert mit westlicher Astrologie und einem **Fusion-Layer**, der beide Systeme über Wu-Xing-Vektormathematik verbindet.

### 1.2 Kernmerkmale

| Eigenschaft | Beschreibung |
|---|---|
| **Deterministisch** | Keine Zufallselemente, rein astronomische Berechnungen |
| **Immutabel** | Alle Dataclasses mit `frozen=True` |
| **Typsicher** | Vollständige Type-Hint-Abdeckung (Python 3.10+) |
| **Funktional** | Pure Functions ohne Seiteneffekte |
| **Contract-First** | JSON-Schema-Validierung (Draft-07) für `/validate` |
| **Dual-System** | BaZi (östlich) + Western Astrology + Fusion-Layer |

### 1.3 Verzeichnisstruktur

```
BAFE/
├── bazi_engine/                # Hauptpaket
│   ├── __init__.py             # Package-Exporte (Pillar, FourPillars, BaziInput, BaziResult, compute_bazi)
│   ├── types.py                # Datenstrukturen (76 LOC)
│   ├── constants.py            # STEMS, BRANCHES, ANIMALS, DAY_OFFSET (21 LOC)
│   ├── bazi.py                 # Kern-Berechnungs-Pipeline (150 LOC)
│   ├── ephemeris.py            # Swiss Ephemeris Backend + Protocol (110 LOC)
│   ├── jieqi.py                # Sonnenterm-/Jieqi-Berechnungen (99 LOC)
│   ├── time_utils.py           # Zeitparsing/-konvertierung (42 LOC)
│   ├── western.py              # Westliche Astrologie (121 LOC)
│   ├── fusion.py               # Wu-Xing Fusion-Analyse (596 LOC)
│   ├── app.py                  # FastAPI REST API (617 LOC)
│   ├── cli.py                  # Command-Line Interface (67 LOC)
│   └── bafe/                   # Contract-First Validator Subpackage
│       ├── __init__.py          # Exportiert validate_request
│       ├── service.py           # Haupt-Validierungslogik (322 LOC)
│       ├── mapping.py           # Branch-Mapping-Konventionen (131 LOC)
│       ├── kernel.py            # Von-Mises Soft-Kernel (51 LOC)
│       ├── harmonics.py         # Phasor-Harmonik-Features (44 LOC)
│       ├── canonical_json.py    # Deterministische JSON-Serialisierung (75 LOC)
│       ├── refdata.py           # RefData-Evaluierung (278 LOC)
│       ├── time_model.py        # Zeitmodell-Evaluierung (200 LOC)
│       ├── ruleset_loader.py    # Ruleset-Loader (59 LOC)
│       └── errors.py           # Fehlerkatalog (53 LOC)
├── tests/                      # Testsuite
│   ├── conftest.py             # Pfadkonfiguration
│   ├── test_golden.py          # 4 Golden-Vector-Tests
│   ├── test_golden_vectors.py  # 5 erweiterte Vektor-Tests
│   ├── test_invariants.py      # 2 strukturelle Invarianz-Tests
│   ├── test_api.py             # 11 API/Contract-Tests
│   └── test_properties.py      # 4 mathematische Eigenschafts-Tests
├── spec/                       # BaZodiac Spezifikation
│   ├── schemas/                # JSON-Schemas (ValidateRequest, ValidateResponse)
│   ├── rulesets/               # standard_bazi_2026.json
│   ├── refdata/                # RefPack Manifest Template
│   ├── tests/                  # tv_matrix.json (Test-Vektoren)
│   └── addenda/                # Interpretation/Scientific Compliance
├── scripts/                    # GitHub Actions Script
│   └── action_compute.py       # BaZi + Western Berechnung für CI
└── metrics/                    # System-Metriken
    └── system-metrics.json
```

---

## 2. Modulabhängigkeiten

```
Ebene 0:  constants.py                          (keine Abhängigkeiten)
Ebene 1:  types.py                              (← constants.py)
Ebene 2:  ephemeris.py, time_utils.py           (← types.py, swisseph)
Ebene 3:  jieqi.py                              (← ephemeris.py)
Ebene 4:  bazi.py                               (← types, time_utils, ephemeris, jieqi, constants)
Ebene 5:  western.py                            (← ephemeris.py, swisseph)
Ebene 6:  fusion.py                             (← eigenständig, math)
Ebene 7:  app.py                                (← bazi, western, fusion, time_utils, bafe)
          cli.py                                (← types, bazi)
          bafe/service.py                       (← bafe/*, fusion.true_solar_time)
```

**Kritische Regel:** Niedrigere Ebenen dürfen NIEMALS höhere Ebenen importieren (Zirkuläre-Import-Prävention).

---

## 3. Datenstrukturen

### 3.1 Konstanten (`constants.py:1-21`)

| Konstante | Typ | Wert | Beschreibung |
|---|---|---|---|
| `STEMS` | `List[str]` | `["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]` | 10 Himmelsstämme (天干) |
| `BRANCHES` | `List[str]` | `["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]` | 12 Erdzweige (地支) |
| `ANIMALS` | `List[str]` | `["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig"]` | 12 Tierkreiszeichen |
| `DAY_OFFSET` | `int` | `49` | JDN-Kalibrierungskonstante: `(JDN + 49) % 60` aligniert 1949-10-01 auf Jia-Zi (Index 0) |

### 3.2 Type-Aliase (`types.py:9-12`)

| Alias | Definition | Erlaubte Werte |
|---|---|---|
| `TimeStandard` | `Literal["CIVIL", "LMT"]` | Bürgerliche Zeit oder Local Mean Time |
| `DayBoundary` | `Literal["midnight", "zi"]` | Tagesgrenze: Mitternacht oder Beginn der Zi-Stunde (23:00) |
| `EphemerisBackendName` | `Literal["swisseph", "skyfield"]` | Backend-Auswahl (nur swisseph implementiert) |
| `Fold` | `Literal[0, 1]` | DST-Fold-Parameter für ambige Zeiten |

### 3.3 Pillar (`types.py:14-19`) – frozen dataclass

```python
@dataclass(frozen=True)
class Pillar:
    stem_index: int     # 0-9 → Index in STEMS
    branch_index: int   # 0-11 → Index in BRANCHES
```

| Feld | Typ | Bereich | Beschreibung |
|---|---|---|---|
| `stem_index` | `int` | 0–9 | Jia=0, Yi=1, Bing=2, Ding=3, Wu=4, Ji=5, Geng=6, Xin=7, Ren=8, Gui=9 |
| `branch_index` | `int` | 0–11 | Zi=0, Chou=1, Yin=2, ... Hai=11 |

**`__str__`** gibt `"{Stem}{Branch}"` zurück, z.B. `"JiaChen"`.

### 3.4 FourPillars (`types.py:21-26`) – frozen dataclass

```python
@dataclass(frozen=True)
class FourPillars:
    year: Pillar
    month: Pillar
    day: Pillar
    hour: Pillar
```

### 3.5 SolarTerm (`types.py:28-33`) – frozen dataclass

```python
@dataclass(frozen=True)
class SolarTerm:
    index: int              # 0-23, Sonnenterm-Index
    target_lon_deg: float   # Ziel-Sonnenlänge in Grad (0°, 15°, 30°, ... 345°)
    utc_dt: datetime        # UTC-Zeitpunkt des Eintritts
    local_dt: datetime      # Lokaler Zeitpunkt des Eintritts
```

### 3.6 BaziInput (`types.py:35-56`) – frozen dataclass

**Haupteingabe-Datenstruktur für `compute_bazi()`.**

| Feld | Typ | Default | Pflicht | Beschreibung |
|---|---|---|---|---|
| `birth_local` | `str` | — | Ja | ISO 8601 Lokaldatum, z.B. `"2024-02-10T14:30:00"` |
| `timezone` | `str` | — | Ja | IANA Zeitzone, z.B. `"Europe/Berlin"` |
| `longitude_deg` | `float` | — | Ja | Geographische Länge (−180 bis +180) |
| `latitude_deg` | `float` | — | Ja | Geographische Breite (−90 bis +90) |
| `time_standard` | `TimeStandard` | `"CIVIL"` | Nein | `"CIVIL"` oder `"LMT"` |
| `day_boundary` | `DayBoundary` | `"midnight"` | Nein | `"midnight"` oder `"zi"` |
| `ephemeris_backend` | `EphemerisBackendName` | `"swisseph"` | Nein | `"swisseph"` (einziges implementiertes) |
| `accuracy_seconds` | `float` | `1.0` | Nein | Iterationsgenauigkeit in Sekunden |
| `strict_local_time` | `bool` | `True` | Nein | DST-Validierung ein/aus |
| `fold` | `Fold` | `0` | Nein | DST-Fold für ambige Zeiten |
| `ephe_path` | `Optional[str]` | `None` | Nein | Pfad zu Swiss-Ephemeris-Dateien |
| `day_anchor_date_iso` | `Optional[str]` | `None` | Nein | v0.4: Anker-Datum für Tagessäule |
| `day_anchor_pillar_idx` | `Optional[int]` | `None` | Nein | v0.4: Anker-Pillar-Index (0-59) |
| `month_boundary_scheme` | `Literal["jie_only","all_24"]` | `"jie_only"` | Nein | v0.4: Monatsgrenzenmodus |

### 3.7 BaziResult (`types.py:58-75`) – frozen dataclass

**Vollständiges Berechnungsergebnis.**

| Feld | Typ | Beschreibung |
|---|---|---|
| `input` | `BaziInput` | Original-Eingabedaten |
| `pillars` | `FourPillars` | Die vier berechneten Säulen |
| `birth_local_dt` | `datetime` | Geparster lokaler Geburtszeitpunkt (timezone-aware) |
| `birth_utc_dt` | `datetime` | Geburtszeitpunkt in UTC |
| `chart_local_dt` | `datetime` | Chart-lokaler Zeitpunkt (CIVIL oder LMT) |
| `jd_ut` | `float` | Julian Day (Universal Time) |
| `jd_tt` | `float` | Julian Day (Terrestrial Time) |
| `delta_t_seconds` | `float` | ΔT-Korrektur in Sekunden (TT − UT) |
| `lichun_local_dt` | `datetime` | LiChun-Zeitpunkt (Start des Frühlings, 315° Sonnenlänge) |
| `month_boundaries_local_dt` | `Sequence[datetime]` | 13 Monatsgrenzen (Jie-Übergänge) |
| `month_index` | `int` | 0–11, aktueller Monatsindex |
| `solar_terms_local_dt` | `Optional[Sequence[SolarTerm]]` | 24 Sonnenterme (Diagnostik, kann `None` sein) |

---

## 4. Core-Berechnungsfunktionen

### 4.1 bazi.py – Hauptberechnungs-Engine

**Datei:** `bazi_engine/bazi.py` (150 LOC)

#### 4.1.1 `jdn_gregorian(y, m, d)` → `int` (Zeile 14-18)

Berechnet den **Julian Day Number** (JDN) aus einem gregorianischen Datum.

| Parameter | Typ | Beschreibung |
|---|---|---|
| `y` | `int` | Jahr |
| `m` | `int` | Monat (1-12) |
| `d` | `int` | Tag (1-31) |

**Algorithmus:**
```
a = (14 - m) // 12
y2 = y + 4800 - a
m2 = m + 12*a - 3
JDN = d + (153*m2 + 2)//5 + 365*y2 + y2//4 - y2//100 + y2//400 - 32045
```

**Rückgabe:** Integer JDN-Wert.

---

#### 4.1.2 `sexagenary_day_index_from_date(y, m, d, offset=DAY_OFFSET)` → `int` (Zeile 20-21)

Berechnet den **60er-Zyklus-Index des Tages** (sexagenary cycle).

| Parameter | Typ | Default | Beschreibung |
|---|---|---|---|
| `y` | `int` | — | Jahr |
| `m` | `int` | — | Monat |
| `d` | `int` | — | Tag |
| `offset` | `int` | `49` | Kalibrierungs-Offset |

**Formel:** `(jdn_gregorian(y, m, d) + offset) % 60`

**Rückgabe:** Integer 0–59 (Sexagenary-Index).

**Kalibrierung:**
- `1949-10-01` → Index 0 (Jia-Zi, 甲子)
- `1912-02-18` → Index 0 (Jia-Zi)

---

#### 4.1.3 `pillar_from_index60(idx60)` → `Pillar` (Zeile 23-24)

Wandelt einen 60er-Zyklus-Index in ein `Pillar`-Objekt um.

| Parameter | Typ | Beschreibung |
|---|---|---|
| `idx60` | `int` | 0–59, Sexagenary-Index |

**Formel:**
- `stem_index = idx60 % 10`
- `branch_index = idx60 % 12`

---

#### 4.1.4 `year_pillar_from_solar_year(solar_year)` → `Pillar` (Zeile 26-28)

Berechnet die **Jahressäule** aus dem Solarjahr.

| Parameter | Typ | Beschreibung |
|---|---|---|
| `solar_year` | `int` | Solarjahr (nach LiChun-Grenze) |

**Formel:** `idx60 = (solar_year - 1984) % 60`

**Referenzpunkt:** 1984 = Jia-Zi Jahr (甲子年), Index 0.

---

#### 4.1.5 `month_pillar_from_year_stem(year_stem_index, month_index)` → `Pillar` (Zeile 30-33)

Berechnet die **Monatssäule** aus dem Jahresstamm und dem Monatsindex.

| Parameter | Typ | Beschreibung |
|---|---|---|
| `year_stem_index` | `int` | 0–9, Stamm der Jahressäule |
| `month_index` | `int` | 0–11, Monatsindex (0=Yin-Monat nach LiChun) |

**Formeln:**
- `branch_index = (2 + month_index) % 12` → Yin(2) als erster Monat
- `stem_index = (year_stem_index * 2 + 2 + month_index) % 10`

---

#### 4.1.6 `hour_branch_index(dt_local)` → `int` (Zeile 35-36)

Berechnet den **Erdzweig-Index der Stunde** aus einem lokalen Zeitpunkt.

| Parameter | Typ | Beschreibung |
|---|---|---|
| `dt_local` | `datetime` | Lokaler Zeitpunkt |

**Formel:** `((dt_local.hour + 1) // 2) % 12`

**Zuordnung:** Zi(23-01)=0, Chou(01-03)=1, Yin(03-05)=2, ... Hai(21-23)=11

---

#### 4.1.7 `hour_pillar_from_day_stem(day_stem_index, hour_branch)` → `Pillar` (Zeile 38-40)

Berechnet die **Stundensäule** aus dem Tagesstamm und dem Stundenzweig.

| Parameter | Typ | Beschreibung |
|---|---|---|
| `day_stem_index` | `int` | 0–9, Stamm der Tagessäule |
| `hour_branch` | `int` | 0–11, Zweig der Stunde |

**Formel:** `stem_index = (day_stem_index * 2 + hour_branch) % 10`

---

#### 4.1.8 `_lichun_jd_ut_for_year(year, backend)` → `float` (Zeile 42-44)

Berechnet den **Julian Day (UT) von LiChun** (Start des Frühlings, 315° Sonnenlänge) für ein gegebenes Jahr.

| Parameter | Typ | Beschreibung |
|---|---|---|
| `year` | `int` | Kalenderjahr |
| `backend` | `SwissEphBackend` | Ephemeris-Backend |

**Methode:** Ruft `backend.solcross_ut(315.0, jd_start)` auf, wobei `jd_start` der 1. Januar des Jahres ist.

---

#### 4.1.9 `compute_bazi(inp)` → `BaziResult` (Zeile 46-149)

**Hauptfunktion – 9-Schritt-Berechnungspipeline.**

| Parameter | Typ | Beschreibung |
|---|---|---|
| `inp` | `BaziInput` | Vollständige Eingabedaten |

**Pipeline:**

| Schritt | Zeilen | Beschreibung |
|---|---|---|
| 1 | 47-48 | Backend-Prüfung: nur `"swisseph"` implementiert |
| 2 | 50 | `SwissEphBackend` initialisieren |
| 3 | 52-57 | ISO-String parsen → timezone-aware `datetime` (DST-Prüfung) |
| 4 | 58 | Konvertierung zu Chart-Local (CIVIL oder LMT) + UTC |
| 5 | 60-62 | Julian Day (UT), ΔT, Julian Day (TT) berechnen |
| 6 | 64-76 | **Jahressäule**: LiChun-Grenze bestimmen, Solarjahr ableiten |
| 7 | 78-91 | **Monatssäule**: 13 Monatsgrenzen berechnen, Monatsindex finden |
| 8 | 93-107 | **Tagessäule**: JDN + Offset (oder Custom Anchor), Sexagenary-Index |
| 9 | 109-113 | **Stundensäule**: Stundenzweig + Tagesstamm-Ableitung |

**LiChun-Logik (Schritt 6, Zeile 64-76):**
```python
if chart_local_dt < lichun_this_local:
    solar_year = y - 1          # Geburt VOR LiChun → Vorjahr
else:
    solar_year = y              # Geburt NACH LiChun → aktuelles Jahr
```

**Custom Day Anchor (Schritt 8, Zeile 94-103):**
```python
if inp.day_anchor_date_iso and inp.day_anchor_pillar_idx is not None:
    calculated_offset = (inp.day_anchor_pillar_idx - anchor_jdn) % 60
else:
    calculated_offset = DAY_OFFSET  # Standard: 49
```

**Diagnostik (Zeile 116-134):** Berechnung der 24 Sonnenterme im try-catch – Fehler blockiert nicht die Hauptberechnung.

**Rückgabe:** Vollständiges `BaziResult`-Objekt.

---

### 4.2 ephemeris.py – Swiss Ephemeris Backend

**Datei:** `bazi_engine/ephemeris.py` (110 LOC)

#### 4.2.1 Hilfsfunktionen

| Funktion | Zeile | Signatur | Beschreibung |
|---|---|---|---|
| `norm360(deg)` | 12-16 | `float → float` | Normalisiert Grad auf [0, 360) |
| `wrap180(deg)` | 18-19 | `float → float` | Normalisiert Grad auf (-180, +180] |

#### 4.2.2 `EphemerisBackend` Protocol (Zeile 21-25)

Interface für austauschbare Ephemeris-Backends.

| Methode | Signatur | Beschreibung |
|---|---|---|
| `delta_t_seconds(jd_ut)` | `float → float` | ΔT in Sekunden |
| `jd_tt_from_jd_ut(jd_ut)` | `float → float` | JD(TT) aus JD(UT) |
| `sun_lon_deg_ut(jd_ut)` | `float → float` | Sonnenlänge in Grad |
| `solcross_ut(target, jd_start)` | `(float, float) → Optional[float]` | Sonnenlängen-Überquerung |

#### 4.2.3 `SwissEphBackend` (Zeile 27-47) – frozen dataclass

Implementiert `EphemerisBackend` mit der Swiss Ephemeris Bibliothek (pyswisseph).

| Feld | Typ | Default | Beschreibung |
|---|---|---|---|
| `flags` | `int` | `swe.FLG_SWIEPH` | Swiss Ephemeris Flags |
| `ephe_path` | `Optional[str]` | `None` | Pfad zu Ephemeris-Dateien |

**Methoden:**

| Methode | Zeile | Implementierung |
|---|---|---|
| `delta_t_seconds(jd_ut)` | 36-37 | `swe.deltat(jd_ut) * 86400.0` |
| `jd_tt_from_jd_ut(jd_ut)` | 39-40 | `jd_ut + swe.deltat(jd_ut)` |
| `sun_lon_deg_ut(jd_ut)` | 42-44 | `swe.calc_ut(jd_ut, swe.SUN, flags)` → normalisiert auf [0,360) |
| `solcross_ut(target, jd_start)` | 46-47 | `swe.solcross_ut(target, jd_start, flags)` |

**`__post_init__`** (Zeile 32-34): Löst Ephemeris-Pfad auf und ruft `swe.set_ephe_path()` auf.

#### 4.2.4 `datetime_utc_to_jd_ut(dt_utc)` → `float` (Zeile 49-53)

Konvertiert ein UTC-`datetime` in einen Julian Day (UT).

| Parameter | Typ | Bedingung |
|---|---|---|
| `dt_utc` | `datetime` | Muss timezone-aware UTC sein |

**Fehler:** `ValueError` wenn nicht UTC.

#### 4.2.5 `jd_ut_to_datetime_utc(jd_ut)` → `datetime` (Zeile 55-73)

Konvertiert einen Julian Day (UT) zurück in ein UTC-`datetime`.

**Behandelt Überläufe** bei Sekunden/Minuten/Stunden korrekt (Zeile 63-71).

#### 4.2.6 `ensure_ephemeris_files(ephe_path)` → `str` (Zeile 92-109)

Stellt sicher, dass Swiss Ephemeris Dateien vorhanden sind.

**Erforderliche Dateien:**
- `sepl_18.se1` (Planeten-Ephemeris 1800-2400 AD)
- `semo_18.se1` (Mond-Ephemeris)
- `seas_18.se1` (Asteroiden-Ephemeris)
- `seplm06.se1` (Ergänzende Ephemeris)

**Pfadauflösung:**
1. Expliziter `ephe_path` Parameter
2. Umgebungsvariable `SE_EPHE_PATH`
3. Fallback: `~/.cache/bazi_engine/swisseph`

**Sicherheit:** Lädt NIEMALS Dateien aus dem Netz herunter. Wirft `FileNotFoundError` bei fehlenden Dateien.

---

### 4.3 jieqi.py – Sonnenterm-Berechnungen

**Datei:** `bazi_engine/jieqi.py` (99 LOC)

#### 4.3.1 Konstante

```python
SOLAR_TERM_TARGETS_DEG = [0.0, 15.0, 30.0, ... 345.0]  # 24 Sonnentermen in Grad
```

#### 4.3.2 `_bisection_crossing(backend, target_lon_deg, jd_lo, jd_hi, accuracy_seconds, max_iter=80)` → `float` (Zeile 9-40)

**Interner Bisektions-Algorithmus** zum Finden eines Sonnenlängen-Übergangs.

| Parameter | Typ | Beschreibung |
|---|---|---|
| `backend` | `EphemerisBackend` | Ephemeris-Backend |
| `target_lon_deg` | `float` | Ziellänge in Grad |
| `jd_lo` | `float` | Untere JD-Grenze |
| `jd_hi` | `float` | Obere JD-Grenze |
| `accuracy_seconds` | `float` | Zielgenauigkeit in Sekunden |
| `max_iter` | `int` | Maximale Iterationen (Default: 80) |

**Algorithmus:**
1. Berechne `f(jd) = wrap180(sun_lon(jd) - target)` an beiden Grenzen
2. Prüfe Vorzeichenwechsel (Interval-Bracketing)
3. Bisektiere bis `|hi - lo| ≤ accuracy_seconds / 86400`
4. Toleranz: `tol_days = accuracy_seconds / 86400.0`

**Fehler:** `ValueError` wenn kein Root im Interval.

#### 4.3.3 `find_crossing(backend, target_lon_deg, jd_start_ut, *, accuracy_seconds, max_span_days=40.0)` → `float` (Zeile 42-68)

**Universelle Sonnenlängen-Überquerungsfunktion.**

| Parameter | Typ | Default | Beschreibung |
|---|---|---|---|
| `backend` | `EphemerisBackend` | — | Ephemeris-Backend |
| `target_lon_deg` | `float` | — | Ziel-Sonnenlänge |
| `jd_start_ut` | `float` | — | Startpunkt (JD UT) |
| `accuracy_seconds` | `float` | — | Genauigkeit |
| `max_span_days` | `float` | `40.0` | Max. Suchfenster in Tagen |

**Strategie:**
1. **Primär:** `backend.solcross_ut()` → direkte Swiss-Ephemeris-Lösung
2. **Fallback:** Stepping (1 Tag) + Bisection bei Vorzeichenwechsel

#### 4.3.4 `compute_month_boundaries_from_lichun(backend, jd_lichun_ut, *, accuracy_seconds)` → `List[float]` (Zeile 70-83)

Berechnet **13 Monatsgrenzen** (Jie-Übergänge) ab LiChun.

| Index | Sonnenlänge | Jie-Name |
|---|---|---|
| 0 | 315° | LiChun (Frühlingsbeginn) |
| 1 | 345° | JingZhe (Erwachen der Insekten) |
| 2 | 15° | QingMing (Klares und Helles) |
| 3 | 45° | LiXia (Sommerbeginn) |
| ... | +30° je Schritt | ... |
| 12 | 315° + 360° | Nächster LiChun |

**Rückgabe:** Liste von 13 JD(UT)-Werten, streng aufsteigend.

#### 4.3.5 `compute_24_solar_terms_for_window(backend, jd_start_ut, jd_end_ut, *, accuracy_seconds)` → `List[Tuple[int, float]]` (Zeile 85-98)

Berechnet alle **24 Sonnenterme** innerhalb eines Zeitfensters.

**Rückgabe:** Liste von `(index, jd_ut)` Tupeln, sortiert nach JD.

---

### 4.4 time_utils.py – Zeitkonvertierung

**Datei:** `bazi_engine/time_utils.py` (42 LOC)

#### 4.4.1 `LocalTimeError` (Zeile 7-8)

Exception für ungültige lokale Zeiten (DST-Lücken, ambige Zeiten).

#### 4.4.2 `parse_local_iso(birth_local_iso, tz_name, *, strict, fold)` → `datetime` (Zeile 10-27)

Parst einen ISO-8601-String und macht ihn timezone-aware.

| Parameter | Typ | Beschreibung |
|---|---|---|
| `birth_local_iso` | `str` | ISO-8601-Zeitstring |
| `tz_name` | `str` | IANA Zeitzone |
| `strict` | `bool` | Strikte DST-Validierung |
| `fold` | `int` | 0 oder 1 für ambige Zeiten |

**Strikter Modus:** Führt einen Round-Trip-Check durch (lokal → UTC → lokal). Wirft `LocalTimeError` wenn das Ergebnis abweicht (z.B. bei Spring-Forward-Lücken).

#### 4.4.3 `lmt_tzinfo(longitude_deg)` → `timezone` (Zeile 29-30)

Erzeugt ein `timezone`-Objekt für **Local Mean Time** basierend auf Längengrad.

**Formel:** `offset_seconds = longitude_deg × 240.0` (4 Minuten pro Grad)

#### 4.4.4 `to_chart_local(birth_local, longitude_deg, time_standard)` → `Tuple[datetime, datetime]` (Zeile 32-36)

Konvertiert den lokalen Geburtszeitpunkt in Chart-Local-Time.

| `time_standard` | Verhalten |
|---|---|
| `"CIVIL"` | Gibt `birth_local` und `birth_utc` zurück |
| `"LMT"` | Konvertiert UTC → LMT-Zeitzone basierend auf Längengrad |

**Rückgabe:** `(chart_local_dt, birth_utc_dt)`

#### 4.4.5 `apply_day_boundary(dt_local, day_boundary)` → `datetime` (Zeile 38-41)

Verschiebt den Zeitpunkt bei Zi-Tagesgrenze.

| `day_boundary` | Verhalten |
|---|---|
| `"midnight"` | Keine Änderung |
| `"zi"` | Addiert +1 Stunde (verschiebt 23:00-00:00 zum nächsten Tag) |

---

*Fortsetzung in Iteration 2: API-Endpoints, Fusion-Modul, Western-Modul*
*Fortsetzung in Iteration 3: BAFE-Subpackage, Verifikation, Tests*
