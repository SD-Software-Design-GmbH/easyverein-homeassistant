# easyVerein für Home Assistant

Custom Integration (HACS), die ein paar Kennzahlen aus [easyVerein](https://easyverein.com) als Entitäten bereitstellt.
Läuft gegen die API `v3.0`, Polling alle 30 Minuten.

## Entitäten

| Entität | Quelle |
|---|---|
| `sensor` **Mitglieder** | Anzahl Einträge im `member`-Endpunkt ohne Austrittsdatum (kann Anträge enthalten) |
| `sensor` pro **Custom Filter** | Anzahl Treffer des in easyVerein gespeicherten Filters, z. B. „Offene Mitgliedsanträge“ |
| `calendar` **Termine** | Alle Termine aus easyVerein (Datumsbereich wird bei Bedarf abgefragt) |

Unterstützte Filter-Modelle: Mitglieder, Kontakte, Buchungen, Rechnungen, Termine, Inventar, Aufgaben.
Neue Filter in easyVerein erscheinen nach einem Neuladen der Integration.

## Installation

1. HACS → Benutzerdefinierte Repositories → dieses Repo als *Integration* hinzufügen.
2. Integration „easyVerein“ hinzufügen und den API-Token eintragen.

Der Token läuft nach 30 Tagen ab und wird von der Integration täglich geprüft und bei Bedarf automatisch erneuert.
Empfehlung: einen eigenen API-Benutzer mit Leserechten verwenden.

## Entwicklung

```bash
python -m unittest discover -s tests   # API-Client, ohne Home Assistant
```

## Bekannte Lücken (Prototyp)

- Kalender-Mapping und Config-Flow sind nicht gegen eine echte Home-Assistant-Instanz getestet.
- Kalender-Entität zeigt keinen „nächsten Termin“ als Zustand.
- Der Sensor „Mitglieder“ filtert nur nach Austrittsdatum.
