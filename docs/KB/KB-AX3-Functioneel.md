# KB-AX3-001 — Axapta 3: Functionele Supportgids

**Systeem:** Axapta 3  
**Categorie:** Functioneel / ERP  
**Taal:** NL  
**Doelgroep:** Support, Master Data, Key Users

---

## 1. Einde(boek)jaars issues

### 1.1 Documenttellers resetten

Documenttellers worden gereset door **Boekan**. Niet zelf aanpassen.

#### Probleem: Teller staat nog niet goed (bv. SO19xxxx terwijl we al 2020 zijn)

**Oorzaak:** Boekan is bezig met resetten, of heeft een fout gemaakt.

**Oplossing:**
1. Gebruiker informeren dat Boekan ermee bezig is.
2. Teller eventueel controleren via: `Sales Ledger > Setup > Parameters > tab Number Sequences`
3. Zoek het juiste documenttype → rechtermuisklik op kolom "Number sequence code" → "Go to maintable"
4. **Nooit zelf aanpassen.**

---

#### Probleem: "Document nr 1 already exists" (bv. SOxxxxxx1_XXX already exists)

**Oplossing:**
1. Ga naar de Number Sequences van dat documenttype.
2. Zet "Manual" aan, daarna "Continuous" terug aan.
3. Test met een nieuwe SO (klantnr ingeven en controleren of er een nieuw SOxxxxx-nummer met correct nummer aangemaakt werd).
4. Alternatief: doe "Cleanup – Current" en test opnieuw.

---

#### Probleem: "The date of voucher 'xxx' is outside the date range of the voucher series"

**Oorzaak:** Boekan heeft de datum in het EVSI-journal nog niet op het huidige jaar gezet.

**Oplossing:** Wachten tot Boekan de datum in het EVSI-journal heeft bijgewerkt naar het huidige jaar.

---

### 1.2 Stocktelling / Stock Taking

Zie de officiële procedure op SharePoint:  
[Procedure Stock Take (Engels)](https://polletgroupintranet.sharepoint.com/:w:/r/sites/PG_CORP_IT/Shared%20Documents/Axapta/Axapta%20Procedures/English/Stock%20Take/Procedure%20Stock%20Take(E).doc)

---

## 2. Master Data

### 2.1 Algemene velden op klant-/leveranciersfiche

| Veld | Uitleg |
|---|---|
| Registratienummer | Sommige landen hebben naast een BTW-nr ook een registratienr |
| Taal | Taal gebruikt op documenten |
| Valuta | Per firma aanpasbaar op klanten-/leveranciersfiche |

**Tab Klant – Gestopt:**

| Waarde | Betekenis |
|---|---|
| Nee | Actief |
| Alle | Volledig geblokkeerd, geen enkel documenttype bewerkbaar |
| Alles behalve opname lijst | Alles geblokkeerd behalve zendnota's |

> ⚠️ **Bedrijfstak** moet steeds binnen **Master Data** worden aangepast, niet via het menu Klanten.

---

### 2.2 BTW-groepen (ondertab Klant)

| Code | Omschrijving |
|---|---|
| BDOM | België Domestic |
| BIC | België Intracommunitair |
| BX | België Export |
| BJO | België Medecontractant |
| NDOM | NL Domestic |

---

### 2.3 Klantengroepen (PWG-breed)

| Code | Omschrijving |
|---|---|
| 10 | Local |
| 20 | EU |
| 30 | Export |

---

### 2.4 Master Data Relations

- **00001 – 0…**: Zussen
- Zie SharePoint voor aanmaken nieuwe leverancier: [Aanmaken leverancier(A).docx](https://polletgroupintranet.sharepoint.com/:w:/r/sites/PG_CORP_IT/Internal/AX3/Manuals%20Axapta%203/PURCHASE/Aanmaken%20leverancier(A).docx)

**Supplier type:** Als dit veld niet ingevuld is, krijg je een "geen toegang"-melding bij het klikken op Transactions.

**E-mail (Contact Info):** E-mailadres voor orderbevestigingen voor alle firma's. Met vinkje "e-mail adjustable" kan het adres per firma worden gewijzigd.

---

## 3. Artikelen (Items)

### 3.1 Aanmaken nieuwe artikelen

Template: [NEW Item Request Template - 10digit.xltx](https://polletgroupintranet.sharepoint.com/:x:/r/sites/PG_CORP_IT/Shared%20Documents/Axapta/Item%20Requests/NEW%20Item%20Request%20Template%20-%2010digit.xltx)

**Stappen:**
1. Tab "item REQUEST" controleren (hoofdletters, intrastatcode …)
2. Tab "item Sheet" wordt automatisch gevuld op basis van "item REQUEST"
3. Rechtermuisklik op "item Sheet" tabblad → Unprotect (wachtwoord: `atthedoor`)
4. Kopieer de lijn naar een simpel `.txt`-bestand
5. In Axapta (MDC): `Voorraadbeheer > Periodiek > Artikels importeren`
6. Haal het txt-bestand op en klik OK
7. Antwoord de aanvraagmail met een kopie van het i-resultaat (itemcode + naam)

---

### 3.2 Artikelformaat en types

**Format itemnr:** `<artgrp1>(2 cijfers)` + `<artgrp2>(2 cijfers)` + `<artgrp3>(2 cijfers)` …

**Itemtypes:**

| Code | Omschrijving |
|---|---|
| 0 | Item / Artikel |
| 1 | BOM / Stuklijst / LMAT |
| 2 | Service |

**Service items:**
- Werken met negatieve stock (als correct group)
- Geen automatische reservering (geen stock)
- Kunnen niet op de pickinglijst (geen stock)
- Dimensiegroep 40 (niet 10)

---

### 3.3 Dimensiegroepen

| Code | Omschrijving |
|---|---|
| 10 | Zonder configuratie |
| 20 | Met configuratie |
| 30 | Lengte |
| 40 | Service item (zonder configuratie) |

---

### 3.4 Voorraadmodelgroep (Stock model group)

| Code | Omschrijving |
|---|---|
| 10 | Artikels & stuklijsten – geen negatieve voorraad toegestaan |
| 20 | Service artikels – wel negatieve voorraad toegestaan |

---

### 3.5 Itemstatus

| Status | Betekenis |
|---|---|
| ACT | Actief |
| DNU | Do Not Use – wellicht vervangitem aangemaakt |
| DEL | Deleted – niet verkrijgbaar bij lev, maar nog stock bij zus |
| EOL | End-Of-Life – niet meer aankoopbaar |
| OBS | Obsolete – verdwijnt via batchjob (DEL + geen voorraad) |

---

### 3.6 Minimum stock wijzigen

**Voor 1 artikel:**
1. Wijzig de coverage group op het item naar MIN (of STD)
2. Wijzig het minimum (als coverage group = MIN) of voeg een lijn toe

**Voor meerdere artikelen:**
1. Run het Safety journal voor de items
2. Wijzig de Coverage group
3. Post het journal
4. Run opnieuw het Safety journal en vul de minima in voor items met Coverage group = MIN
5. Post het journal

> ⚠️ Als je MIN naar STD wijzigt via safety journal, worden **alle minima verwijderd**.

---

### 3.7 KITO / KITA

**KITO** (Collected item for picking = Kit voor verkoop):
- Enkel op SO gebruiken, nooit op PO
- Nooit voorraad van KITO zelf, enkel van onderdelen
- Op itemfiche: tab Parameters → "Collected item for picking" aanvinken
- Default issue/receipt locatie instellen op warehouse items

**KITA** (Collected item for purchase = Kit voor aankoop):
- Op PO gebruiken
- Componenten komen bij ontvangst via stuklijstjournaal op stock
- Op itemfiche: tab Parameters → "Collected item for purchase" aanvinken

---

## 4. Boekhouding / General Ledger

### 4.1 Periodes

> ⚠️ **NOOIT een periode op CLOSED zetten!**

- Boekingsperiodes openzetten: in live doet Boekan dit
- Nieuw boekjaar aanmaken: gewenste periodelengte = 1 maand

---

### 4.2 SII (Spanje – INSOL / Cosmo)

Bij problemen (mail komt niet toe, file niet in "Sent"):

1. Ga naar `Boekhouding > Periodiek > SII > Create statement`
2. Verwijder online batch-gebruikers: `Administratie > Online gebruikers`
3. Herstart de batch server
4. Controleer in SOL de Batchlijst op Awaiting/Executing batchen → zet op Withold
5. Verwijder Lock-files op: `K:\Insol\Cosmo\...`
6. Controleer het aantal online batch-gebruikers (2 per AOS)

---

## 5. Verkooporders (Sales Orders)

### 5.1 Flow verkooporder (itemtransactie status)

| Stap | Status |
|---|---|
| Sales order posted | In behandeling |
| Create picking list (not registered) | Fysiek gereserveerd |
| Register/Update pickinglist | Opgenomen (Picked) |
| Delivery note posted | Ingehouden (Deducted) |
| Invoice posted | Verkocht (Sold) |

---

### 5.2 SO blijft op "Open Order" staan (niet op "Gefactureerd")

**Oplossing 1:** Voor elke lijn met status "Open Order" → tab General → vinkje "Stopped" aanzetten. Status wordt "Invoiced".

**Oplossing 2:** Hoeveelheid terugzetten naar oorspronkelijke waarde → `Functions > Deliver remainder > Cancel quantity`.

---

### 5.3 SO met multiline discount – status komt niet op "Gefactureerd"

**Workaround:** Ga op de kortingslijn staan → `Functies > Nog te leveren` → geen hoeveelheid invullen → OK.

---

### 5.4 Zendnota tegenboeken

1. Vul op de detaillijn bij "Nu te leveren" de terug te draaien hoeveelheid in
2. Vul een locatie in voor de goederen
3. Klik op `Boeken > Zendnota`
4. Kies "Nu te leveren" bij hoeveelheid en boek

---

## 6. Aankooporders (Purchase Orders)

### 6.1 Aankoopordertypen

| Type | Beschrijving |
|---|---|
| Purchase order | Standaard aankooporder |
| Geretourneerd item | Retour naar leverancier |
| Journal | Intercompany (nog geen transacties) |
| Blanket order | Contract met prijsafspraak |

> Intercompany PO's staan in het **rood** zolang ze niet bevestigd zijn. Eens de zus het order post, verdwijnt de rode kleur.

---

### 6.2 Aankooporder annuleren (na boeking)

Een geboekte PO kan niet rechtstreeks geannuleerd worden.

**Oplossing:**
1. Detaillijn → `Functies > Deliver remainder` → hoeveelheid op 0 zetten
2. Leverancier op de hoogte brengen
3. Nieuw aankooporder aanmaken indien gewenst

---

### 6.3 Flow aankooporder

1. Aanmaken PO
2. Boeken PO (= doorsturen naar leverancier)
3. Goederen ontvangen via `Stock management > Journals > Item arrival` (status = Registered)
4. Delivery note maken via `item arrival > Functions > Delivery note` (status = Received)
5. Factuur boeken via `Posting > Invoice` (status = Purchased)

---

## 7. Voorraadbeheer

### 7.1 Coveragegroepen

| Code | Omschrijving |
|---|---|
| STD | Geen standaard item, stock besteld indien nodig voor een SO |
| MIN | Besteld ifv de minimum voorraad |
| MAN | Manuele aankoop |

---

### 7.2 Itemtelling / Counting journal

**Import via txt-bestand (Tab delimited):**

| Kolom | Inhoud |
|---|---|
| A | Itemnummer |
| B | Magazijn |
| C | Locatie |
| D | Configuratie |
| E | Datum (01/12/2020) |
| F | Hoeveelheid |
| H | Counted |

---

## 8. Masterplanning

### 8.1 Waarom staat een artikel niet op de masterplanning?

- Is het artikel onderdeel van een KITA? → Definieer minimum op componenten, niet op KITO/KITA
- Controleer coverage group op artikel → moet MIN zijn
- Controleer minimum stock
- Controleer positive & negative days op coverage group MIN
- Controleer lead time op artikel

---

### 8.2 Coveragegroepen

| Instelling | Werking |
|---|---|
| MIN | Stock item, bestellen op basis van minimumhoeveelheid |
| STD | On-order item, enkel bestellen bij verkooporder |
| MAN | Manueel, niet in masterplanning |

---

## 9. Webshop / SANA

### 9.1 Nieuwe klant aanmaken voor webshop

1. Eerst aanmaken in Axapta
2. In SANA: manueel "Customer import" scheduled task uitvoeren (of wachten op automatische run)
3. Shop account/login aanmaken en Axapta-klantnr koppelen
4. Klantkorting instellen via MDC

### 9.2 Validatieregels webshop

- Alleen artikels met status ACT, EOL of DEL (niet OBS)
- Enkel EUR-prijzen
- Klant gestopt = "Alle" → klant kan niet inloggen (serverf fout)
- Leveringsmethode niet ingevuld → klant kan geen order plaatsen

---

## 10. Referenties

| Document | Locatie |
|---|---|
| Stock Take Procedure | SharePoint → Axapta Procedures → Stock Take |
| Aanmaken leverancier | SharePoint → Internal → AX3 → Purchase |
| NRS opladen & verwijderen | SharePoint → Internal → AX3 → Stock management |
| Invoice Methods | SharePoint → Axapta Procedures → Invoice methods |
| Procedure Masterplanning | SharePoint → Axapta Procedures → Masterplanning |
