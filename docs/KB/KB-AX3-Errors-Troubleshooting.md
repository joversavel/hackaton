# KB-AX3-002 — Axapta 3: Foutafhandeling & Technische Troubleshooting

**Systeem:** Axapta 3  
**Categorie:** Technisch / Infrastructuur  
**Taal:** NL  
**Doelgroep:** IT Support, Infrastructuur

---

## 1. Axapta start niet op

### Stap 1: Bepaal de scope van het probleem

Is het probleem aanwezig op **alle 4 live AOS-servers** (AOS01, AOS02, AOS03, AOS04)?

- **Ja** → Axapta-breed probleem, escaleer naar senior support
- **Nee (slechts 1 server)** → Ga naar stap 2

### AOS-serveroverzicht

| Server | Functie |
|---|---|
| AOS01 (BEDCMAOS01) | Pool webshops – PIMS01 |
| AOS02 (BEDCMAOS02) | Water Webshops – WEBL02 |
| AOS03 (BEDCMAOS03) | Portugal gebruikers |
| AOS04 (BEDCMAOS04) | WMS – WEBL01 |
| AOS05 (BEDCMAOS05) | DEV webshops – SQL03 |

---

## 2. AOS Reboot

### 2.1 Via PowerShell (voorkeur)

Gebruik het volgende script:  
[restart AOS services with menu.ps1](https://polletgroupintranet.sharepoint.com/:u:/r/sites/PG_CORP_IT/Internal/PowerShell/Restarting%20all%20AOS/restart%20AOS%20services%20with%20menu.ps1)

Daarna direct verder naar **sectie 3 (Axapta check na reboot)**.

---

### 2.2 Manuele procedure

1. Stuur een mail naar de Axapta key users dat Axapta voor een kwartier down gaat.
2. Log in op een AOS-server met je admin user via Remote Connection Manager.  
   Servers: `BEDCMAOS01` t/m `BEDCMAOS04` (live), `BEDCMAOS05` (DEV)
3. Start **AxCtrl** met "Run as administrator".
4. Klik op de onderste **Stop**-knop.
5. Controleer of de Axapta-services niet automatisch herstarten.
6. Wacht tot ze volledig gestopt zijn.
7. Klik op **Start**.
8. Herhaal eventueel voor andere servers door de computernaam bovenaan aan te passen.
9. Controleer de status.

> ⚠️ Als services terugkomen op "Stopped", moet je de **volledige server** herstarten.

---

## 3. Axapta check na reboot

Voer onderstaande checks uit op elk van de AOS-servers na het herstarten.

---

### Check 1: Tabelbrowser

1. Ga naar een **andere firma** (bv. AQD)
2. Klik op "Toepassingsobjectstructuur (AOT)"
3. Navigeer naar: `AOT > Data Dictionary > Tables`
4. Zoek tabel **"Gateway Organisation"**
5. Rechtermuisklik → Add-Ins → Tabelbrowser

**Resultaat:**
- **Fout** → Herstart de AOS
- **Leeg** → Controleer of je in de juiste firma zit

---

### Check 2: Batch gebruikers

> Wordt normaal opgevangen door PRTG. Geen tussenkomst nodig tenzij afwijking.

1. Ga naar `Administratie (Administration) > Online gebruikers`
2. Er horen **2 batch-users per AOS** te zijn. Bij 1 AOS herstart blijven er 6 staan.

**Als er te veel of te weinig batch-users zijn:**

1. Klik op **Refresh**
2. Maak de tabel **PWGBatchClientsOnline** leeg:
   - Klik op eerste tabel en typ `pwgbatch...`
   - Open via rechtermuisklik → Add-ins → Tablebrowser
   - Controleer of er een batchjob lopende is:
     - **Idle** → Niets aan de hand
     - **Naam van een batchjob** → Die job is in uitvoering, wachten

---

## 4. Veelvoorkomende foutmeldingen

### 4.1 "The date of voucher 'xxx' is outside the date range of the voucher series"

**Oorzaak:** Boekan heeft de datum in het EVSI-journal nog niet ingesteld op het huidige jaar.

**Oplossing:** Boekan contacteren om de datum in het EVSI-journal bij te werken.

**Op DEV:** Datum aanpassen in `Boekhouding > Setup > Journals > Posting journals`.

---

### 4.2 "Document nr 1 already exists" (bv. SOxxxxxx1_XXX already exists)

**Oorzaak:** Conflict in de nummerreeks.

**Oplossing:**
1. Ga naar de Number Sequences van het documenttype
2. Zet "Manual" aan, dan "Continuous" terug aan
3. Test met een nieuwe SO
4. Alternatief: `Cleanup > Current` en test opnieuw

---

### 4.3 "Eenheidsomrekening van 'M' naar 'PCS' bestaat niet"

**Oorzaak:** Geen unit conversion gedefinieerd.

**Oplossing:**
1. Ga naar het artikel → `Setup > Unit conversion`
2. Voeg de omrekening toe
3. Controleer via "Example" of de conversie correct is

---

### 4.4 "Een of meer voorraadtransacties gevonden" (bij aanpassen stock unit)

**Oorzaak:** Er zijn open transacties/orders op dit artikel.

**Oplossing:** Annuleer eerst de openstaande orderregels (deliver remainder op 0), pas daarna de unit aan.

---

### 4.5 "Asciilog object niet geïnitialiseerd" (bij item import)

**Referentie:** T2002396

**Oplossing:** Zie Ticket T2002396 voor de specifieke context.

---

### 4.6 "U hebt onvoldoende rechten om Menu Item Aankooporder uit te voeren"

**Oorzaak:** Gebruiker mist security group **PWG-F-VPO** voor het automatisch aanmaken van PO's vanuit een zusterfirma in PWG.

**Oplossing:** Security group `PWG-F-VPO` toevoegen aan de gebruiker.

---

### 4.7 "Geen toegang" bij klikken op Transactions (leveranciersfiche)

**Oorzaak:** Veld "Supplier type" is niet ingevuld op de leveranciersfiche.

**Oplossing:** Vul het veld "Supplier type" in op de leveranciersfiche.

---

### 4.8 Pickinglist staat "grayed out" en kan niet afgedrukt worden

**Oorzaak:** Niet al het werk kan gegenereerd worden. Mogelijke redenen:
- Een component is gereserveerd op een locatie die geen picking toelaat

**Oplossing:**
- Controleer de locatie van de componenten in de BOM
- Verplaats de stock van de blokkerende locatie naar een geldige picklocatie

---

### 4.9 "Leveringsadres kan niet worden gewijzigd" op SO

**Foutmelding:** *"The selected address on the line is no longer effective."*

**Oorzaak:** Het leveringsadres kan niet gewijzigd worden als de lijn al op een lading (load) staat.

**Oplossing A (niets geleverd):**
1. Verwijder de lijn van de lading
2. Wijzig het leveringsadres
3. Voeg de lijn terug toe aan de lading

**Oplossing B (deel geleverd):**
1. Verwijder de lijn van de lading
2. Zet "deliver remainder" op 0 op de SO-lijn
3. Maak een nieuwe lijn met de resterende items en het nieuwe adres
4. Voeg terug toe aan de lading

---

### 4.10 "Picking list kan niet worden afgedrukt" (grayed out)

**Oorzaak:** Picking lists blijven grayed out zolang niet al het werk gegenereerd kan worden.

**Mogelijke oorzaken voor productieorders:**
- Component(en) zijn gereserveerd op een locatie die geen picking toelaat

---

## 5. SII / COSMO (Spanje – INSOL) problemen

### Probleem: Mail van SII komt niet toe

**Oorzaak:** Batch job is gecrasht terwijl een lock-file aanwezig was.

**Oplossing:**
1. Ga naar firma **SOL**: `Basic > Inquiries > Batch list`
2. Zoek in "ended jobs" naar: `"Sol: Inmediatement: X (SOL)"`
3. Klik op `Functions > Change status > Waiting`
4. Ga naar firma **MDC**: `Basic > Inquiries > Batch list`
5. Zoek naar: `"SOL: Immediately: X (SOL)"` → zet op Waiting
6. Verwijder de Lock-file in: `\\boekan.be\dfs\AxArchive\Insol\Cosmo\XMLHacienda\log`

---

### Probleem: Oud order blijft op "Sent" staan

**Oorzaak:** Batch job kon zijn mail niet uitsturen (bv. batchserver was herstart).

**Oplossing:**
1. Open "Statements sent"
2. Klik op "Lines" → selecteer de eerste 3 facturen → "Reject line"
3. In het rejected statement: verwijder de te verzenden lijnen
4. Maak een nieuw statement met die facturen en volg de normale procedure

---

## 6. Batch jobs

### 6.1 Batch job herplannen

1. Ga naar `Basic > Inquiries > Batchlijst`
2. Pas de begindatum aan op de grid om de job opnieuw te starten
3. Voor definitieve aanpassing: klik op knop **Terugkeerpatroon**

### 6.2 Batch van "Fout" naar "In afwachting" zetten

1. Ga naar `Basic > Inquiries > Batchlijst`
2. Selecteer de batch in fout
3. `Functies > Status wijzigen > In afwachting`

> ⚠️ Een batch in "Fout" kan niet direct herstart worden — eerst naar "In afwachting" zetten.

### 6.3 Job laten lopen op DEV

1. Voer job `PWGSanaTest_DisableAllBatches` uit (zet alle batchdatums in de toekomst)
2. Zet de status van gewenste batch op "In afwachting"
3. Pas de startdatum aan naar het verleden

---

## 7. WMS / Dynaman problemen

### 7.1 Pickinglist in Dynaman afgehandeld maar feedback naar Axapta gaat in error

**Oorzaak:** Verdwenen PL in Axapta, of aanpassingen van hoeveelheden.

**Oplossing:**
1. Open `SalesPickingListJournalTable` → veld `PWGCnwDateExported` → uitblanken
2. Verwijder de pickinglist
3. Verhoog "Deliver remainder" naar het aantal op de PL
4. WMS-vinkje tijdelijk afzetten op artikel
5. PL boeken
6. WMS-vinkje terug aanzetten
7. PL boeken en zendnota maken

---

### 7.2 "Location ... is blocked for input"

**Oorzaak:** Locatie op ontvangstjournaal werd aangepast naar een productielocatie die geblokkeerd is voor input.

**Oplossing:**
1. Open `WMSJournalTable` → veld `PWGCNWexported date` verwijderen
2. Pas de locatie op het ontvangstjournaal aan
3. Reprocess
4. `PWGCNWDateExported` terug op niet-editeerbaar zetten

---

### 7.3 Pickinglist zonder leveringsmethode (onbekende transporteur)

**Oorzaak:** Nieuwe leveringsmethode in Dynaman aangemaakt zonder melding aan IT.

**Oplossing:** Conversietabel voor `transport_company_code` aanvullen in Axapta.

---

## 8. Referenties

| Document | Locatie |
|---|---|
| Restart AX service or Server | SharePoint → Internal → AX3 |
| PowerShell restart script | SharePoint → Internal → PowerShell → Restarting all AOS |
| Batchverwerking handleiding | SharePoint → Internal → AX3 → Manuals → Batch job |
| How to cancel a work order | SharePoint → Axapta Procedures → Work Orders |
| C&W SCO Portal Errors | SharePoint → Internal → WMS |
