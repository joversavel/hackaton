# KB-TICKET-CREATION-FLOW — Handleiding Ticketaanmaak
**Project:** IT Support (ITS) — polletgroup.atlassian.net  
**Systeem:** Jira Service Management + Unified AI Workspace Assistant  
**Taal:** NL  
**Doelgroep:** Alle medewerkers en externe aanvragers  
**Versie:** 1.0 — 20 april 2026

---

## Inhoudstafel

1. [De volledige aanmaakflow](#1-de-volledige-aanmaakflow)
2. [Verplichte velden](#2-verplichte-velden)
3. [Aanbevolen velden](#3-aanbevolen-velden)
4. [Checklist per ticketcategorie](#4-checklist-per-ticketcategorie)
5. [Wat gebeurt er na aanmaak](#5-wat-gebeurt-er-na-aanmaak)
6. [Veelgemaakte fouten](#6-veelgemaakte-fouten)

---

## 1. De volledige aanmaakflow

```
Stap 1: Probleem vaststellen
        ↓
Stap 2: Controleer of er al een oplossing bestaat (KB of eerder ticket)
        ↓
Stap 3: Ticket aanmaken via Jira of Teams Bot
        ↓
Stap 4: Verplichte velden invullen + categorie kiezen
        ↓
Stap 5: Beschrijving schrijven (zie richtlijnen per categorie)
        ↓
Stap 6: Bijlagen toevoegen indien van toepassing (screenshot, logfile)
        ↓
Stap 7: Indienen → bevestigingsmail ontvangen
        ↓
Stap 8: Smart Assign analyseert ticket en wijst toe
        ↓
Stap 9: Assignee ontvangt notificatie via Teams
        ↓
Stap 10: Opvolging via Jira of Teams Bot
```

### Stap 2 in detail — Eerst zoeken, dan aanmaken

Voordat je een ticket aanmaakt, controleer je eerst of het probleem al bekend is:

| Zoekbron | Wat vind je er? |
|---|---|
| Confluence kennisbank | Bekende oplossingen voor Axapta, D365, Infra |
| Jira (ITS-project) | Eerder opgeloste tickets met gelijkaardige foutmelding |
| Teams Bot | Typ je vraag — de bot zoekt automatisch in de historiek |

> 💡 **Tip:** Gebruik de Teams Bot met de vraag *"Is er een oplossing voor [foutmelding]?"* voordat je een nieuw ticket aanmaakt. Dit bespaart tijd voor jou én voor het supportteam.

---

## 2. Verplichte velden

Deze velden **moeten** altijd ingevuld zijn. Een ticket zonder deze informatie kan niet correct worden toegewezen of verwerkt.

| Veld | Omschrijving | Voorbeeld |
|---|---|---|
| **Samenvatting** | Korte, duidelijke omschrijving van het probleem. Max. 1 zin. | `URGENT: geen gezaagde buis meer in BOM na Edge-update` |
| **Beschrijving** | Volledige uitleg van het probleem (zie richtlijnen hieronder) | Zie sectie 4 |
| **Prioriteit** | Hoe kritisch is het probleem voor de bedrijfswerking? | `Medium` / `High` / `Critical` |
| **Bedrijf / Entiteit** | Voor welk bedrijf of welke entiteit is het ticket? | `Aquadeck`, `Sterima`, `PWG België`, `Pollet Group IT` |
| **Categorie** | Type probleem (zie sectie 4 voor de lijst) | `BOM — ontbrekend component` |
| **Aangemaakt door** | Jouw naam en e-mailadres zijn automatisch ingevuld via je login | Automatisch |

### Richtlijnen voor een goede beschrijving

Een goede beschrijving bevat **minimaal** de volgende elementen:

```
1. WAT is het probleem?
   → Beschrijf wat er fout gaat, zo concreet mogelijk.

2. WANNEER is het begonnen?
   → Geef een datum of tijdstip. "Sinds dinsdag 7 april" is beter dan "recent".

3. WAAR treedt het op?
   → Welke module, welk systeem, welke order of welk artikel?

4. HOE reproduceer je het?
   → Welke stappen leiden tot het probleem?

5. WAT is de impact?
   → Hoeveel gebruikers of orders zijn geblokkeerd?
```

**Goed voorbeeld** (gebaseerd op ITS-19257):
> "Sinds dinsdag 7 april staat het component 'Gezaagde en geboorde buis — Ø139,7x2x3875 RVS316' niet meer in de BOM van orders met constructie. Vastgesteld via MyAquadeck (app.hivecpq.com). Vermoedelijk na een configuratiewijziging in Edge (zie ook ITS-19215). Alle nieuwe orders met constructie zijn getroffen. Verzoek om z.s.m. te corrigeren."

**Slecht voorbeeld:**
> "BOM werkt niet meer. Graag oplossen."

---

## 3. Aanbevolen velden

Deze velden zijn **niet verplicht** maar verhogen de kwaliteit van de triage aanzienlijk. De Smart Assign-logica gebruikt deze informatie om het ticket aan de juiste persoon toe te wijzen.

| Veld | Waarom invullen? | Voorbeeld |
|---|---|---|
| **Gerelateerde tickets** | Legt verband met eerder gemelde problemen | `ITS-19215`, `ITS-18630` |
| **Betrokken ordernummer(s)** | Laat de assignee direct inzoomen | `AQDT-00002313`, `SO2600275` |
| **Betrokken artikelnummer(s)** | Cruciaal voor BOM- en D365-tickets | `22450000022`, `0704190001_WHT-9016` |
| **Foutmelding (exact)** | Kopieer de volledige foutmelding uit het systeem | `"The selected address on the line is no longer effective."` |
| **Screenshot / bijlage** | Versnelt diagnose bij visuele problemen | Schermafbeelding van de foutmelding |
| **Betrokken gebruikers** | Hoeveel mensen ondervinden hinder? | `3 gebruikers in Aquadeck NL` |
| **Systeem / module** | In welk systeem treedt het probleem op? | `D365 F&O`, `Axapta 3`, `SMT365`, `MySterima` |
| **Urgentie-toelichting** | Waarom is dit urgent? (buiten de prioriteit) | `Productieorder kan niet worden vrijgegeven` |

> ⚠️ **Attentie voor Smart Assign:** Hoe meer context je meegeeft in de beschrijving en de aanbevolen velden, hoe accurater de AI de juiste specialist kan aanwijzen. Een ticket met ordernummer, artikelnummer én foutmelding wordt sneller en beter toegewezen dan een ticket met alleen een samenvatting.

---

## 4. Checklist per ticketcategorie

### 🔧 BOM / Stuklijst / Configuratie
*(Aquadeck, Euraqua, Suko — Hive CPQ ↔ D365)*

- [ ] Betrokken ordernummer(s) vermeld (bijv. `AQDT-00002313`)
- [ ] Betrokken artikelnummer(s) vermeld
- [ ] Beschrijving van de ontbrekende of verkeerde component
- [ ] Aangegeven of het probleem systematisch is (alle orders) of enkelvoudig
- [ ] Vermeld of de order al in productie zit (ja/nee)
- [ ] Gerelateerde tickets gelinkt (bijv. eerder gemeld configuratieprobleem)
- [ ] Screenshot van de BOM in Hive of D365 bijgevoegd

**Veelvoorkomende categorieën:**
`BOM — ontbrekend component` | `BOM — verkeerde component` | `BOM — eenheid/unit` | `Configuratie — ongeldig` | `Configuratie — verdwenen` | `Productieorder — status blokkade`

---

### 🖥️ Infrastructuur / IT Algemeen
*(Phishing, certificaten, mailboxen, AD, Azure, netwerk)*

- [ ] Type probleem duidelijk benoemd (zie categorieën hieronder)
- [ ] Betrokken gebruiker(s) of toestel vermeld
- [ ] Voor certificaatfouten: welke applicatie (Outlook, Azure Portal, ...)?
- [ ] Voor mailboxen: gewenst adres, doorstuurregel, of externe afzender vermeld
- [ ] Voor Azure Secrets: applicatienaam + vervaldatum vermeld
- [ ] Voor phishing: originele verdachte e-mail doorgestuurd als bijlage (niet enkel beschreven)
- [ ] Voor wachtwoordproblemen: username in AD vermeld (geen wachtwoord meesturen!)

**Veelvoorkomende categorieën:**
`Phishing melding` | `Certificaatfout` | `Mailbox aanmaak/beheer` | `Nieuwe medewerker onboarding` | `SharePoint toegang` | `Azure Secret verloopt` | `Wachtwoord AD` | `Netwerk/FTP`

---

### 📦 Axapta 3 (AX3)
*(ERP — verkooporders, aankooporders, voorraadbeheer, masterplanning)*

- [ ] Betrokken firma/entiteit vermeld (bijv. MDC, SOL, AQD)
- [ ] Betrokken documenttype vermeld (SO, PO, factuur, pickinglijst, ...)
- [ ] Exacte foutmelding gekopieerd uit Axapta
- [ ] Betrokken ordernummer of documentnummer vermeld
- [ ] Betrokken artikelnummer vermeld indien van toepassing
- [ ] Aangegeven welke AOS-server betrokken is (indien bekend): AOS01–AOS05
- [ ] Beschreven welke stappen leiden tot de fout

**Veelvoorkomende categorieën:**
`AX3 — nummerreeks` | `AX3 — pickinglijst` | `AX3 — stock/BOM` | `AX3 — AOS/service` | `AX3 — batch job` | `AX3 — SII/COSMO`

---

### 💼 Dynamics 365 (D365 F&O)
*(Finance & Operations — artikelen, klanten, leveranciers, voorraadbeheer)*

- [ ] Betrokken firma/entiteit vermeld (bijv. 2000, Sterima, Aquadeck)
- [ ] Betrokken artikelnummer of klantnummer vermeld
- [ ] Exacte foutmelding gekopieerd uit D365
- [ ] Aangegeven of het probleem via de servicebus loopt (sync AX3 ↔ D365)
- [ ] Screenshot van de fout of de betrokken pagina bijgevoegd
- [ ] Vermeld of er transacties zijn op het betrokken artikel/klant/leverancier

**Veelvoorkomende categorieën:**
`D365 — synchronisatie` | `D365 — artikelaanmaak` | `D365 — klant/leverancier` | `D365 — picking/levering` | `D365 — facturatie` | `D365 — servicebus error`

---

### 🖨️ Printen / Labels
*(SMT365, dox42, D365 — Sterima, Aquadeck)*

- [ ] Betrokken printer of labeltype vermeld
- [ ] Betrokken applicatie vermeld (SMT365, dox42, D365)
- [ ] Exacte foutmelding gekopieerd (bijv. dox42-foutcode)
- [ ] Betrokken ordernummer of documentnummer vermeld
- [ ] Beschreven wat er verkeerd afdrukt (rotatie, inhoud, aantal, ...)
- [ ] Screenshot of foto van het probleem bijgevoegd

**Veelvoorkomende categorieën:**
`Print — label inhoud/rotatie` | `Print — dox42 fout` | `Print — packing slip` | `Print — vertraagd/geblokkeerd`

---

### 🔐 Toegang / Access
*(D365, SMT365, MySterima, Scilife, SharePoint)*

- [ ] Naam en e-mail van de betrokken gebruiker vermeld
- [ ] Welke applicatie of module? (bijv. D365 — Serial Numbers, SMT365 — Rework)
- [ ] Welk type toegang is nodig? (lezen, schrijven, beheer)
- [ ] Goedkeuring van leidinggevende vermeld of bijgevoegd (indien vereist)
- [ ] Reden voor de toegangsaanvraag kort beschreven

**Veelvoorkomende categorieën:**
`Toegang — D365` | `Toegang — SMT365` | `Toegang — SharePoint` | `Toegang — MySterima` | `Toegang — Scilife`

---

### 🔄 MySterima / Synchronisatie
*(D365 ↔ SMT365 ↔ MySterima)*

- [ ] Betrokken set- of ordernummer vermeld
- [ ] In welk systeem is de data correct, en in welk systeem ontbreekt/klopt ze niet?
- [ ] Betrokken veld of data beschreven (foto, BOM-data, historiek, ...)
- [ ] Tijdstip/datum van het probleem vermeld
- [ ] Screenshot van het verschil tussen de systemen bijgevoegd

**Veelvoorkomende categorieën:**
`MySterima — sync D365` | `MySterima — foto's` | `MySterima — BOM/fysieke controle` | `Sets geblokkeerd`

---

## 5. Wat gebeurt er na aanmaak

Zodra je je ticket hebt ingediend, neemt het systeem een reeks automatische stappen. Je hoeft hier niets extra's voor te doen.

```
Ticket ingediend
      ↓
✅ Bevestigingsmail ontvangen (Jira)
      ↓
🤖 AI analyseert het ticket (inhoud, categorie, historiek)
      ↓
🎯 Smart Assign bepaalt de beste assignee
      ├── Beste kandidaat met confidence %
      └── Alternatief indien eerste keuze niet beschikbaar
      ↓
📋 Oplossingsvoorstel wordt als comment toegevoegd aan het ticket
      ↓
📩 Assignee ontvangt notificatie via Microsoft Teams
      ↓
🔍 Assignee bekijkt ticket + voorgestelde oplossing
      ↓
🔧 Probleem wordt opgelost
      ↓
📚 Oplossing wordt automatisch omgezet naar kennisartikel in Confluence
      ↓
✅ Ticket gesloten — jij ontvangt bevestiging
```

### Wat betekent de Smart Assign-output?

Wanneer het systeem een ticket analyseert, zie je in Jira of via Teams een bericht zoals:

> **Smart Assign resultaat voor ITS-XXXXX**
> - 🥇 Voorgestelde assignee: **Arbi Taramov** — confidence 87%
>   *Reden: 9 gelijkaardige BOM/configuratietickets opgelost in de afgelopen 3 maanden*
> - 🥈 Alternatief: **Jana Decanniere** — confidence 61%
> - 💡 Oplossingsvoorstel: *Controleer de Edge-configuratieparameters en vergelijk met ITS-19215...*

Je kan als aanvrager:
- De toewijzing **accepteren** → assignee wordt direct genotificeerd
- De toewijzing **aanpassen** → je kiest zelf een andere persoon
- Het oplossingsvoorstel **bekijken** en feedback geven

### Verwachte reactietijden

| Prioriteit | Verwachte eerste reactie |
|---|---|
| Critical | Binnen 1 uur (werkuren) |
| High | Binnen 4 uur (werkuren) |
| Medium | Binnen 1 werkdag |
| Low | Binnen 3 werkdagen |

> ℹ️ **Opmerking:** De Teams Bot geeft je een directe terugkoppeling zodra het ticket is aangemaakt en toegewezen. Je hoeft niet te wachten op de e-mailbevestiging vanuit Jira.

---

## 6. Veelgemaakte fouten

| Fout | Gevolg | Hoe vermijden? |
|---|---|---|
| Samenvatting te vaag (`"werkt niet"`) | Ticket kan niet automatisch gecategoriseerd worden | Gebruik het formaat: `[Systeem] — [Probleem] — [Impact]` |
| Geen foutmelding meegestuurd | Assignee moet opnieuw contact opnemen | Kopieer altijd de exacte foutmelding uit het systeem |
| Verkeerde prioriteit (alles op Critical) | Echte urgente tickets verdrinken | Gebruik Critical enkel bij productiestilstand of dataverlies |
| Geen ordernummer of artikelnummer | Smart Assign kan geen historiek matchen | Vermeld altijd het betrokken document- of artikelnummer |
| Ticket aangemaakt zonder KB te checken | Dubbel werk voor supportteam | Vraag eerst de Teams Bot: *"Is er een oplossing voor...?"* |
| Meerdere problemen in 1 ticket | Toewijzing en opvolging wordt complex | 1 ticket = 1 probleem. Maak aparte tickets aan voor aparte issues. |

---

## Referenties

| Bron | Locatie |
|---|---|
| Jira ITS-project | [polletgroup.atlassian.net](https://polletgroup.atlassian.net) |
| Confluence kennisbank | KB-AX3-001, KB-AX3-002, KB-D365-001, KB-D365-002 |
| Teams Bot | Beschikbaar in Microsoft Teams — start een chat met *IT Support Bot* |
| Infra ticket top 10 | Intern rapport — `top10_infra_tickets.md` |
| Assignees overzicht | `ITS_assignees_reporters.md` |

---

*Document gegenereerd via Pollet Group AI Workspace Assistant — Hackathon 2026*  
*Vragen of aanvullingen? Maak een ticket aan met categorie `KB — aanpassing`.*
