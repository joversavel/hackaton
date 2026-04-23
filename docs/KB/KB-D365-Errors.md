# KB-D365-001 — Dynamics 365: Foutafhandeling & Troubleshooting

**Systeem:** Microsoft Dynamics 365 Finance & Operations  
**Categorie:** Technisch / Functioneel  
**Taal:** NL/EN  
**Doelgroep:** IT Support, Functioneel beheer

---

## 1. Vendors / Customers – Synchronisatieproblemen

### 1.1 Verkeerde relatie aangemaakt in AX3 en doorgestuurd naar D365

**Voorwaarde:** Geen transacties in D365 op de klant/leverancier.

**Oplossing:**
1. Verwijder de vendor/customer in D365 die verwijderd moet worden
2. Zet vendor/customer op "Stopped for All" in AX3
3. Voor het verwijderen van de relatie in AX3 is een **developer** nodig

---

### 1.2 ITS-3961 — Klant komt niet door in D365: "party does not exist…" of "Party not found…"

**Oorzaak:** Party-record bestaat nog niet of is niet correct gesynchroniseerd.

**Oplossing:**
1. Verwerk de lijn opnieuw via de servicebus: [https://platform.boekan.be/ReportingDashboard/](https://platform.boekan.be/ReportingDashboard/)
2. Als de fout aanhoudt voor een nieuwe klant:
   - Servicebus check in D365: controleer of de sync in error staat → Reprocess
   - Controleer in AX3 of de klant op "Active" staat
   - In AX3: klik op "Save" om de klant opnieuw te activeren

---

### 1.3 "The value 'BNK' in field 'Bank account' is not found in the related table 'customer bank accounts'"

**Oorzaak:** Bank account staat op de klantenfiche maar niet in master data. Bij de meeste bedrijven wordt dit niet gebruikt.

**Oplossing:**
1. Controleer op de klantenfiche of de dropdown opties geeft
2. Indien niet → veld leegmaken
3. Ga terug naar Master Data en sla opnieuw op om de lagen opnieuw te synchroniseren
4. Bij klanten zonder rekeningnummer mag dit veld worden uitgeblankt (referentie T17632)

---

### 1.4 "The Document ID xxxx already been used before" (Error sequence number of the packing slips)

**Oorzaak:** Tegelijkertijd uitgevoerde acties schrijven hetzelfde nummer weg in de nummerreekstabel.

> ⚠️ **Opgelet:** Dev team onderzoekt een standaard of custom oplossing. Eerst polsen bij het dev team voordat je manueel ingrijpt.

**Tijdelijke oplossing (als dev team akkoord gaat):**
1. Ga naar de achterliggende PWG-tabel via:  
   `https://pwg-prod.operations.eu.dynamics.com/?cmp=2000&mi=pwgSysTableBrowser&TableName=numbe…`
2. Zoek in kolom `numbersequenceid` naar `2000-gr25`
3. Verwijder de betreffende record

---

## 2. Sales Orders

### 2.1 ITS-2525 — Productie picking lukt niet voor PC01001591

**Oorzaak:** Component in BOM staat op locatie RETSTOCK, wat geen picklocatie is.

**Oplossing:** Verplaats de component van RETSTOCK naar een geldige picklocatie.

---

### 2.2 ITS-2719 — Kan niet factureren

**Situatie:** Item A besteld, maar item B geleverd (aan prijs van item A).

**Oplossing:**
1. Lever item A gratis (corrective levering)
2. Factureer item B aan de prijs van item A, maar zonder warehouseproces

---

### 2.3 ITS-2694 — Leveringsadres kan niet worden gewijzigd

**Foutmelding:** *"The selected address on the line is no longer effective."*

**Oorzaak:** Leveringsadres kan niet gewijzigd worden zodra de lijn op een lading staat.

**Oplossing A — Niets geleverd:**
1. Verwijder de lijn van de lading
2. Wijzig het leveringsadres
3. Voeg de items opnieuw toe aan de lading

**Oplossing B — Deel al geleverd:**
1. Verwijder de lijn van de lading
2. Zet "deliver remainder" op de SO op 0
3. Maak een nieuwe SO-lijn met de resterende items + nieuw adres
4. Voeg de lijnen toe aan de lading

---

### 2.4 ITS-2835 — Picking list kan niet worden afgedrukt (grayed out)

**Oorzaak:** Picking lists blijven grayed out zolang niet al het werk gegenereerd kan worden.

**Mogelijke redenen voor productieorders:**
- Component(en) zijn gereserveerd op een locatie die geen picking toelaat

**Oplossing:** Controleer welke componenten op een niet-pickbare locatie staan en verplaats de stock.

---

## 3. Referenties

| Ticket | Omschrijving |
|---|---|
| ITS-3961 | Klant komt niet door in D365 – party not found |
| ITS-2525 | Productie picking lukt niet – RETSTOCK locatie |
| ITS-2719 | Kan niet factureren – verkeerd item geleverd |
| ITS-2694 | Leveringsadres kan niet gewijzigd worden op lading |
| ITS-2835 | Picking list grayed out – component op niet-picklocatie |
| T17632 | Klanten zonder rekeningnummer – BNK veld leegmaken |

| Tool | Link |
|---|---|
| Servicebus ReportingDashboard | [https://platform.boekan.be/ReportingDashboard/](https://platform.boekan.be/ReportingDashboard/) |
| D365 Table Browser | `https://pwg-prod.operations.eu.dynamics.com/?cmp=2000&mi=pwgSysTableBrowser` |
