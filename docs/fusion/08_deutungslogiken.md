# 08 — Zwei Deutungslogiken: Narrativ und Diagnostisch

Dieses Dokument definiert zwei vollständige, in sich konsistente Logiken,
wie die Fusion-Mathematik in astrologische Sprache übersetzt werden kann.
Beide Logiken sind **schematisch plausibel** — jede Aussage ist aus den
Zahlen ableitbar, keine ist erfunden.

---

## Vorbedingung: Was "schematisch plausibel" bedeutet

Schematische Plausibilität hat zwei Bedingungen:

1. **Mathematische Bindung:** Jede Aussage muss eindeutig aus Zahlenwerten
   folgen. Gleiche Zahlen → gleiche Aussage, immer.

2. **Traditionskongruenz:** Die Aussage muss innerhalb des Bedeutungsraums
   beider astrologischen Traditionen liegen. Es wird nichts erfunden —
   nur übersetzt und verbunden.

---

## Logik A: Die astrologische Geschichte (narrativ-symbolisch)

### Grundprinzip

Die Mathematik liefert den **Plot** — der Archetyp liefert die **Sprache**.
Das Ergebnis ist eine Geschichte, die der Nutzer wiedererkennen kann.

### Schritt 1: Archetyp bestimmen

Aus H-Wert und Resonanzachse (dominantes `rᵢ`):

```python
def get_archetype(H, resonance_axis):
    if H >= 0.8:
        return ARCHETYPES_HIGH[resonance_axis]
    elif H >= 0.6:
        return ARCHETYPES_MEDIUM_HIGH[resonance_axis]
    elif H >= 0.4:
        return ARCHETYPES_MEDIUM[resonance_axis]
    elif H >= 0.2:
        return ARCHETYPES_MEDIUM_LOW[resonance_axis]
    else:
        return ARCHETYPES_LOW[resonance_axis]
```

**Archetypen-Matrix (Auswahl):**

| | Holz | Feuer | Erde | Metall | Wasser |
|---|---|---|---|---|---|
| **H ≥ 0.8** | Der Visionär | Der Leuchtturm | Der Anker | Der Meister | Der Tiefenschwimmer |
| **H 0.6–0.8** | Der Wachstumstreiber | Der Kommunikator | Der Strukturgeber | Der Differenzierer | Der Intuitive |
| **H 0.4–0.6** | Der Alchemist des Aufbruchs | Der Alchemist des Ausdrucks | Der Alchemist der Form | Der Alchemist der Klarheit | Der Alchemist der Tiefe |
| **H 0.2–0.4** | Der Wanderer | Der Flackernde | Der Sucher | Der Zweifler | Der Rückgezogene |
| **H < 0.2** | Der Brückenbauer (Holz) | Der Brückenbauer (Feuer) | Der Brückenbauer (Erde) | Der Brückenbauer (Metall) | Der Brückenbauer (Wasser) |

### Schritt 2: Narrative aufbauen

Jeder Archetyp hat eine **Dreisatz-Erzählung**:

1. **Wer du bist** (aus dem BaZi — innere Struktur)
2. **Was der Moment bringt** (aus Western — kosmischer Kontext)
3. **Wie sich beides verhält** (aus H und Differenzfeld)

**Beispiel: H = 0.84, Resonanzachse = Feuer, d_Holz = −0.4**

```
Archetypus: "Der Leuchtturm"

[Wer du bist]
Dein BaZi zeigt eine ausgeprägte Feuer- und Holzstruktur —
Vitalität, Ausdruck und Wachstumsdrang sind in deiner Zeitstruktur tief verankert.
Das Holzelement (Stämme Jia oder Yi) trägt das Feuer: du wächst, um zu leuchten.

[Was der Moment bringt]
Der Himmel deiner Geburt spricht dieselbe Sprache: Sonne und Mars in Feuerachsen,
Jupiter (Holz) prominent. Die kosmische Konfiguration spiegelt, was du innerlich bist.

[Wie sich beides verhält]
Hier arbeiten Ost und West synoptisch — mit einem H von 0.84 ist die
systemische Kongruenz außergewöhnlich hoch. Die Differenz zeigt: deine innere
Holzstruktur übersteigt das Himmelsangebot leicht (d_Holz = −0.4). Das bedeutet:
Wachstumsantrieb kommt primär von innen, nicht vom kosmischen Rückenwind.
Du trägst dein Feuer selbst.
```

### Schritt 3: Entwicklungsfeld einbinden

Das Differenzfeld wird als **offene Frage** formuliert, nicht als Defizit:

```
Das Feld, das die stärkste Spannung trägt, ist {max(|dᵢ|) Achse}.
Wenn d < 0: "Was brauchst du, um das, was du innerlich bist, 
             in der Welt sichtbar zu machen?"
Wenn d > 0: "Was bietet dir das Leben an, das du noch nicht 
             vollständig angenommen hast?"
```

### Textgenerierungsprinzip

Die Geschichte wird **modular** aufgebaut — jeder Block stammt aus
einem Template, befüllt mit konkreten Zahlenwerten:

```
[ARCHETYP]     = f(H, resonance_axis)
[BAZI_PROFIL]  = f(dominant_bazi_element, top_branch_hidden)
[WEST_PROFIL]  = f(dominant_western_planet, dominant_sign)
[KONGRUENZ]    = f(H, threshold_label)
[ENTWICKLUNG]  = f(max_diff_element, sign(diff))
[FRAGE]        = f(max_diff_element, sign(diff), archetype)
```

**Jede Aussage ist aus den Zahlen ableitbar. Keine Aussage ist erfunden.**

---

## Logik B: Die diagnostische Karte (analytisch-funktional)

### Grundprinzip

Keine Erzählung, kein Archetyp — nur **Topografie**. Die Karte zeigt,
wo Stärken liegen, wo Spannung besteht, und wo Entwicklungsraum ist.
Das Ergebnis ist ein strukturierter Report, den der Nutzer selbst interpretiert.

### Die drei Zonen

**Zone 1: Stärkefelder** — Elemente, die in beiden Systemen stark vertreten sind

```python
strength_fields = [
    elem for elem in WUXING_ORDER
    if western_norm[elem] > 0.25 AND bazi_norm[elem] > 0.25
]
```

Diese Elemente sind doppelt bestätigt — sowohl der Himmel als auch
die Zeitstruktur tragen sie. Das ist der Bereich, wo der Mensch
konsistent und ohne innere Reibung operiert.

**Zone 2: Spannungsfelder** — Elemente mit hoher Differenz (|dᵢ| > 0.15)

```python
tension_fields = {
    elem: {
        "direction": "West überwiegt" if d > 0 else "BaZi überwiegt",
        "magnitude": abs(d),
        "interpretation": ...
    }
    for elem, d in differences.items()
    if abs(d) > 0.15
}
```

Spannungsfelder sind keine Schwächen — sie sind **Entwicklungsbewegungen**.
Sie zeigen, wo Innen und Außen auseinanderdriften.

**Zone 3: Entwicklungsfelder** — Elemente, die in beiden Systemen schwach sind

```python
development_fields = [
    elem for elem in WUXING_ORDER
    if western_norm[elem] < 0.10 AND bazi_norm[elem] < 0.10
]
```

Was in beiden Systemen kaum vertreten ist, ist kein Manko —
es ist ein **unentwickelter Raum**. In der BaZi-Tradition würde
man sagen: das Element fehlt (缺). Das ist gleichzeitig ein
Risiko (fehlendes Element schwächt bestimmte Lebensbereiche)
und eine Ressource (das Hinzufügen dieses Elements durch Umgebung,
Praxis oder Zeiträume hat starke Wirkung).

### Ausgabeformat

```
═══════════════════════════════════════════
FUSION ANALYSE — DIAGNOSTISCHE KARTE
═══════════════════════════════════════════

HARMONY INDEX: 68,47% (Gute Harmonie)
Die relative Elementstruktur beider Systeme stimmt zu 68,47% überein.

──────────────────────────────────────────
STÄRKEFELDER (in beiden Systemen aktiv)
──────────────────────────────────────────
● Feuer     West: 61,2%  BaZi: 34,0%  → Geteilte Kraft, unterschiedliche Intensität
● Erde      West: 41,8%  BaZi: 56,0%  → Geteilter Anker, BaZi-lastig

──────────────────────────────────────────
SPANNUNGSFELDER (Differenz > 15%)
──────────────────────────────────────────
▲ Metall    West: 52,1%  BaZi: 17,0%  Δ+35,1% → Welt bietet mehr als innere Struktur
▼ Holz      West: 23,1%  BaZi: 73,0%  Δ-49,9% → Innere Stärke sucht äußeren Spiegel

──────────────────────────────────────────
ENTWICKLUNGSFELDER (in beiden Systemen schwach)
──────────────────────────────────────────
○ Wasser    West: 33,7%  BaZi: 10,2%  → Potenzialfeld: Intuition, Tiefe, Rückzug

═══════════════════════════════════════════
LEITFRAGEN
▲ Metall: Welche Anforderungen nach Schärfe und Distinktion nimmst du noch nicht an?
▼ Holz:   Wo wartet dein Wachstum auf Bestätigung von außen?
○ Wasser:  Was würde sich verändern, wenn du mehr Raum für Stille und Tiefe schaffst?
═══════════════════════════════════════════
```

### Unterschied zu Logik A

| | Logik A (Narrativ) | Logik B (Diagnostisch) |
|---|---|---|
| **Zielgruppe** | Mystisch-symbolisch orientierte Nutzer | Analytisch-strukturierte Nutzer |
| **Sprache** | Metapher, Archetypus, Geschichte | Zone, Feld, Prozentsatz |
| **Offenheit** | Geschichte ist offen für Selbstdeutung | Karte ist offen für eigene Schlüsse |
| **Tiefe** | Verlangt astrologisches Vorwissen für volle Wirkung | Funktioniert ohne Vorkenntnisse |
| **Wiedererkennen** | "Das bin ich" (identifikatorisch) | "Das ist meine Situation" (situativ) |
| **Fehlerrisiko** | Archetyp kann falsch greifen | Karte kann korrekt aber bedeutungslos wirken |

---

## Kombinierte Anwendung: Beide Logiken als Paar

Die stärkste Anwendung nutzt **beide Logiken komplementär**:

```
1. Diagnostische Karte → Überblick der Topografie (2 Minuten lesen)
2. Narrative Deutung  → Geschichte, die die Topografie belebt (5 Minuten)
3. Leitfragen        → Übergang in persönliche Reflektion (offen)
```

Das entspricht der klassischen astrologischen Konsultationsstruktur:
Erst die objektive Kartendarstellung (Horoskop zeigen), dann die
narrative Deutung (Gespräch), dann die persönliche Frage.

---

## Anschlussfähigkeit zu den Traditionen

### Logik A: Narrative — westlicher Deutungskanon

Die narrative Deutung folgt der **psychologischen Astrologie** (Liz Greene,
Howard Sasportas, Robert Hand): das Horoskop als Spiegel des Charakters,
der Archetyp als Einladung, nicht als Schicksal. Die verwendeten Archetypen
(Leuchtturm, Anker, Alchemist) sind Jungsche Amplifikationen, die in der
modernen westlichen Astrologie kanonisch sind.

### Logik A: Narrative — BaZi-Deutungskanon

Die BaZi-Tradition hat ebenfalls eine narrative Schicht: Die zehn Götter
(十神, Shí Shén) sind archetypal — "Direkter Reichtum", "Essbarer Gott",
"Offizieller Gott" usw. Das Fusion-Narrativ kann diese Sprache spiegeln,
indem der dominante BaZi-Archetyp mit dem nächstverwandten der zehn Götter
assoziiert wird.

### Logik B: Diagnostisch — Klassische BaZi-Stärkeanalyse

Die Zone-Logik der diagnostischen Karte ist strukturell identisch mit der
klassischen BaZi-Analyse des **Kräftegleichgewichts (五行平衡)**:
- Welches Element ist überrepräsentiert? (→ Spannungsfeld)
- Welches Element fehlt? (→ Entwicklungsfeld)
- Welches ist im Gleichgewicht? (→ Stärkefeld)

Die diagnostische Karte ist damit eine mathematisch formalisierte Version
dessen, was ein erfahrener BaZi-Leser intuitiv tut.

### Logik B: Diagnostisch — Westliches Pendant

Die Kategorisierung in Stärke/Spannung/Entwicklung entspricht dem
**Stellarium-Ansatz** (Marc Edmund Jones) der Planetenmuster-Klassifikation
und dem **Quadrant-Dominanz-Konzept** der modernen Horoskop-Analyse.
Beide fragen: Wo ist die Energie konzentriert, und was fehlt?
