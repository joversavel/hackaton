# KB-D365-002 — Dynamics 365: Functionele Handleiding – Voorraadbeheer

**Systeem:** Microsoft Dynamics 365 Finance & Operations  
**Categorie:** Functioneel  
**Taal:** NL/EN  
**Doelgroep:** Functioneel beheer, Support, Master Data

---

## 1. Inventory Management – Basisbegrippen

### 1.1 License Plate

Een **license plate** is de naam van het materiaal waarmee artikelen bewegen (bv. een pallet). Niet wanneer de pallet in het magazijn staat, maar wanneer ze **in beweging** is.

---

## 2. Artikelen (Items)

### 2.1 Mapping D365 – AX3

De mapping tussen D365 en AX3 artikelnummers is te vinden in tabel:  
`PWGINTERFACEMAPPINGPRODUCTS`

---

### 2.2 Artikelen aanmaken

Artikelen worden aangemaakt vanuit **Axapta (Master Data)**. De rest wordt door de gebruikers zelf gedaan. Support komt enkel tussen bij errors in de servicebus of bij vragen.

**Dimensiegroep:** 20 voor configs.

**Artikelen die niet doorkomen:** Eerst kijken in de servicebus.

#### Procedure: Dimensiegroep 10 (niet-configureerbaar)

1. Controleer of tab "AX-D365" leeg is → zo ja, nog geen mapping
2. `Item to interface > nieuw lijntje toevoegen` → artikel komt in de product staging
3. Types:
   - **Distinct product**: geen config
   - **Product master**: met config
   - **Distinct product variant**: config van de product master
4. Bij valideren: melding welke velden nog ontbreken → altijd eerst valideren, dan aanmaken
5. Na creatie: product code keert terug naar Axapta

#### Procedure: Configureerbaar artikel

1. Bij "Item to interface": selecteer de configuratie
2. Zet "product master" op Yes → in D365 wordt 1 extra lijn aangemaakt (product master + configuraties)
3. Eerst de product master aanmaken, daarna de varianten

#### Procedure: Configuratie als apart artikel in D365

1. Zet "product master" op NO → slechts 1 lijn in D365
2. Elke config krijgt een uniek nummer in D365
3. Selecteer "Product staging template" voor automatisch invullen van velden (type: grabstock, service no stock, consumables, …)

---

### 2.3 Hercreatie van een artikel

Zie handleiding op SharePoint:  
[Handleiding: Verwijderen en heraanmaken artikel in D365](https://polletgroupintranet.sharepoint.com/:w:/r/sites/PG_CORP_IT/Shared%20Documents/D365/General%20user%20manuals/Handleiding%20(Het%20verwijderen%20en%20het%20heraanmaken%20van%20een%20artikel%20in%20D365).docx)

Na hercreatie verdwijnen de mappings ook in Axapta. Pas "Product master Yes/No" aan, sla op en de artikelen worden opnieuw aangemaakt.

**Artikel met voorraad:**
1. Kijk welke transacties nog niet afgerond zijn → doorgeven aan het bedrijf
2. Kijk in welke BOM's het artikel zit via `Engineer > Where used`

---

### 2.4 Naam wijzigen

In D365 wordt de productnaam bepaald door de **EN-US** vertaling.

**Stappen:**
1. Open het artikel of de artikelvariant
2. Ga naar "Translations"
3. Update de waarde in **EN-US**
4. Optioneel: ook EN-GB bijwerken (heeft geen effect op de productnaam)

> ⚠️ Eenmaal een artikel aangemaakt is, worden **geen wijzigingen meer doorgegeven via de interface**. Alle aanpassingen moeten rechtstreeks in D365 gebeuren.

---

## 3. Artikeltypes

### 3.1 Overzicht

De meeste artikelen zijn **stock items** (eventueel met vaste locatie, niet verplicht). Voor grabstock worden geen labels geprint; artikelen gaan direct naar een locatie.

---

### 3.2 Replenishment (Bulk) item

Voorbeeld: pallet zand (voorraadeenheid = kilo). Enkel voor productie.

- Wordt niet gepickt maar geconsumeerd
- Stock moet altijd op dezelfde locatie zijn
- **Alles met decimale stock** (kilo, liter, …) is opgezet als bulk item

---

### 3.3 Multipallet artikelen (PCS+)

Gebruikt voor:
- Artikelen te groot voor 1 pallet
- Artikelen uit meerdere onderdelen

Kenmerken:
- Moeilijk te volgen via license plate
- Enkel voor MTO (Make To Order)

> ⚠️ Als een artikel eenmaal als PCS+ gedefinieerd is, **kan het niet meer terug naar PCS** als er al transacties op zijn.

---

### 3.4 KITO / KITA in D365

- **KITO** = Kit voor verkoop (picking). De hoofdcode wordt alleen op SO gebruikt.
- **KITA** = Kit voor aankoop. De hoofdcode wordt op PO gebruikt. Bij ontvangst worden componenten via stuklijstjournaal op stock gezet.
- **KITO/KITA** = hoofdcode op zowel PO als SO.

> Er mag **nooit voorraad** zijn van een KITO of KITA zelf. Enkel de onderdelen staan op voorraad.

---

### 3.5 Phantom items

- Geen artikel op zich
- Gebruikt om iets weg te halen of toe te voegen in BOM's
- Kunnen niet op voorraad zijn

---

### 3.6 Transportcodes

- 1 code voor transportkosten op SO's
- 2 codes voor transportkosten aankoop

---

## 4. Servicebus – Synchronisatie AX3 ↔ D365

### 4.1 Artikel komt niet door (niet in product staging)

1. Controleer of "Item to interface" correct is aangemaakt in AX3
2. Bekijk de servicebus via [https://platform.boekan.be/ReportingDashboard/](https://platform.boekan.be/ReportingDashboard/)
3. Als de sync in error staat → reprocess

### 4.2 Klant / leverancier komt niet door

Zie **KB-D365-001**, sectie 1.2.

---

## 5. Veelgestelde vragen

### Vraag: Hoe verander ik de naam van een artikel?

Zie sectie 2.4. Naam aanpassen via EN-US translatie in D365 (niet via de interface vanuit AX3).

### Vraag: Wat als een artikel hercreatie nodig heeft?

Zie sectie 2.3. Gebruik de officiële SharePoint handleiding. Let op: mappings verdwijnen tijdelijk in AX3.

### Vraag: Wanneer gebruik ik een bulk/replenishment item?

Wanneer de voorraadeenheid decimaal is (kilo, liter, ...) en de goederen direct worden geconsumeerd zonder pickproces.

### Vraag: Wat is het verschil tussen KITO en KITA?

- **KITO**: hoofdcode in SO, onderdelen worden gepickt. Nooit op PO.
- **KITA**: hoofdcode in PO, onderdelen komen op stock via stuklijstjournaal. Op SO worden de losse onderdelen gebruikt.

---

## 6. Referenties

| Document | Locatie |
|---|---|
| Hercreatie artikel handleiding | SharePoint → D365 → General user manuals |
| Servicebus dashboard | [https://platform.boekan.be/ReportingDashboard/](https://platform.boekan.be/ReportingDashboard/) |
| D365 productiehandleiding | SharePoint → D365 → Manuals |

| Tabel | Gebruik |
|---|---|
| PWGINTERFACEMAPPINGPRODUCTS | Mapping artikelnummers D365 ↔ AX3 |
