# easyVerein für Home Assistant

Integration für [easyVerein](https://easyverein.com), eine Vereinssoftware mit Mitgliederverwaltung und Buchhaltung. Sie zeigt ein paar Kennzahlen aus easyVerein als Sensoren in Home Assistant an, außerdem die Termine des Vereins als Kalender.

Die Werte werden alle 30 Minuten über die API (v3.0) abgefragt, Echtzeit ist nicht gedacht.

## Entitäten

Ein Sensor "Mitglieder" mit der Anzahl der Mitglieder ohne Austrittsdatum.

Pro gespeichertem Filter aus easyVerein (Custom Filter) ein weiterer Sensor mit der Trefferzahl. So lässt sich zum Beispiel "Offene Mitgliedsanträge" anzeigen: Filter in easyVerein anlegen, fertig. Unterstützt sind Filter auf Mitglieder, Kontakte, Buchungen, Rechnungen, Termine, Inventar und Aufgaben. Ein Filter, der erst nach der Einrichtung angelegt wird, taucht nach einem Neuladen der Integration auf.

Ein Kalender "Termine" mit allen Terminen aus easyVerein.

## Installation

Über HACS als benutzerdefiniertes Repository (Typ Integration) hinzufügen, danach unter Geräte & Dienste die Integration easyVerein anlegen und einen API-Schlüssel eintragen.

## API-Schlüssel und Berechtigungen

Den Schlüssel erzeugst du in easyVerein unter [Einstellungen, API](https://easyverein.com/app/settings/easyVereinApi/). Er hat genau die Rechte des Benutzers, als der du beim Erzeugen angemeldet bist. Am besten legst du dafür einen eigenen Benutzer an, der nur lesen darf.

Der Benutzer braucht Vorstandsrechte, weil die gespeicherten Filter nur für Vorstände abrufbar sind. Dazu kommen Leserechte (Schreiben wird nie benötigt) auf die Bereiche, die du anzeigen willst:

- Mitglieder: Sensor "Mitglieder" und Filter auf Mitglieder
- Adressen: Filter auf Kontakte
- Termine: Kalender und Filter auf Termine
- Buchungen: Filter auf Buchungen und Rechnungen
- Aufgaben und Inventar: Filter auf Aufgaben bzw. Inventar

Fehlt das Recht für einen Bereich, fehlen nur die zugehörigen Sensoren. Die Integration läuft normal weiter.

Der Schlüssel ist 30 Tage gültig. Die Integration erneuert ihn selbst und speichert den neuen Wert.

## Stand

Das ist ein Prototyp. Der API-Client hat Tests (`python -m unittest discover -s tests`), Config-Flow und Kalender sind noch nicht in einer laufenden Home-Assistant-Instanz ausprobiert. Der Kalender zeigt außerdem noch keinen "nächsten Termin" als Zustand, und "Mitglieder" kann Anträge mitzählen.
