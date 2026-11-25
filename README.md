# easyVerein für Home Assistant

Integration für die Vereinssoftware [easyVerein](https://easyverein.com). Zeigt Kennzahlen als Sensoren und die Termine als Kalender in Home Assistant an.

[![Repository in HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=SD-Software-Design-GmbH&repository=easyverein-homeassistant&category=integration) [![Integration einrichten](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=easyverein) [![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

Die Werte werden über die API (v3.0) abgefragt, standardmäßig alle 30 Minuten. Echtzeit ist nicht gedacht.

## Entitäten

Sensoren:

- Mitglieder (ohne Ausgetretene und ohne Anträge)
- Offene Mitgliedsanträge
- Kündigungen (Kündigung liegt vor, Mitglied ist noch nicht ausgetreten)
- Neue Mitglieder der letzten 30 Tage
- Nächster Termin (Zeitstempel, mit Name und Ort als Attribute)
- Ein Sensor pro gespeichertem Filter aus easyVerein (Custom Filter) mit der Trefferzahl. Unterstützt sind Filter auf Mitglieder, Kontakte, Buchungen, Rechnungen, Termine, Inventar und Aufgaben. Neue Filter erscheinen beim nächsten Abruf, gelöschte verschwinden.

Kalender:

- "Termine" mit allen Terminen
- Je ein Kalender pro easyVerein-Kalender

Der Zustand eines Kalenders ist der laufende oder nächste Termin (Stand des letzten Abrufs). Damit lassen sich Automationen auf Terminbeginn bauen.

## Installation

Über HACS als benutzerdefiniertes Repository (Typ Integration) hinzufügen, danach unter Geräte & Dienste die Integration easyVerein anlegen und einen API-Schlüssel eintragen.

Unter Optionen der Integration lassen sich das Abfrageintervall ändern und einzelne Filter ausblenden.

## API-Schlüssel und Berechtigungen

Den Schlüssel erzeugst du in easyVerein unter [Einstellungen, API](https://easyverein.com/app/settings/easyVereinApi/). Er hat genau die Rechte des Benutzers, als der du beim Erzeugen angemeldet bist. Am besten legst du dafür einen eigenen Benutzer an, der nur lesen darf.

Der Benutzer braucht Vorstandsrechte, weil die gespeicherten Filter nur für Vorstände abrufbar sind. Dazu kommen Leserechte (Schreiben wird nie benötigt) auf die Bereiche, die du anzeigen willst:

- Mitglieder: die Zähler und Filter auf Mitglieder
- Adressen: Filter auf Kontakte
- Termine: Kalender, Nächster Termin und Filter auf Termine
- Mitgliederbereich: die einzelnen easyVerein-Kalender
- Buchungen: Filter auf Buchungen und Rechnungen
- Aufgaben und Inventar: Filter auf Aufgaben bzw. Inventar

Fehlt das Recht für einen Bereich, fehlen nur die zugehörigen Sensoren. Die Integration läuft normal weiter.

Der Schlüssel ist 30 Tage gültig. Die Integration erneuert ihn selbst und speichert den neuen Wert.

## Entwicklung

```bash
pip install -r requirements_test.txt
pytest
```

Die Tests laufen gegen eine simulierte API.

---

[easyVerein](https://easyverein.com) ist ein Produkt der [SD Software-Design GmbH](https://software-design.de) · [Apache-2.0-Lizenz](LICENSE)
