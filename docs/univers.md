# Univers — mesures FIRDS (étape 2, points 1-3)

Généré le 2026-09-30 à partir des fichiers FIRDS complets `FULINS_E_20260905_01of02.zip` et
`02of02.zip` (ESMA, catégorie Actions, publication hebdomadaire du 05/09/2026), croisés avec
le registre officiel ISO 10383 (MIC) du 14/09/2026. Aucune donnée inventée : toute ligne du
tableau MIC ci-dessous provient du registre ISO téléchargé ce jour ; tout ISIN retenu provient
d'un fait FIRDS réel. **Ce document est une mesure, pas encore un pilote : aucun code pipeline
n'a été lancé sur cet univers.**

## 1. Méthode et périmètre retenu

Univers = actions ordinaires (CFI commençant par `ES`, confirmé conforme à ISO 10962 : groupe
« Common/Ordinary shares ») **ET** ISIN dont le préfixe pays est dans la liste d'inclusion
UE/EEE (30 pays : UE-27 + Islande, Liechtenstein, Norvège) **ET** au moins un lieu de
négociation qui est lui-même dans un pays UE/EEE, de catégorie `RMKT` (marché réglementé) ou
`MLTF` (marché de croissance / MTF) au sens du registre ISO 10383, **ET** dont cette cotation
n'est pas terminée (`TermntnDt` absent sur cette venue).

**Non restreint aux 5 groupes de bourses** de methode.md, conformément à la décision — la
composition finale sera tranchée après mesure de la couverture. La table des MIC retenus
(ci-dessous, §4) est celle **effectivement utilisée** pour produire les chiffres de ce document.

## 2. Chiffres

| Mesure | Valeur |
|---|---|
| ISIN distincts (brut, toute classification, avant filtres) | 193 036 |
| ISIN avec CFI = `ES*` et préfixe ISIN UE/EEE (avant filtre MIC/venue) | 6 385 |
| **ISIN retenus** (univers final : CFI ES*, ISIN UE/EEE, ≥1 venue UE/EEE RMKT/MLTF non terminée) | **6 335** |
| **LEI distincts (sociétés, unité retenue — voir §3)** | **6 169** |
| Sociétés (LEI) avec plusieurs ISIN retenus | 150 |
| ISIN retenus sans LEI dans FIRDS | 0 |
| Sociétés avec ≥1 venue en marché réglementé (RMKT) | 3 311 |
| Sociétés uniquement en marché de croissance/MTF (MLTF seul) | 3 024 |
| ISIN luxembourgeois cotés sur XPAR ou XAMS | 5 (Aperam, Reinet Investments, ArcelorMittal, InPost, Younited Financial) |

### Répartition par pays (préfixe ISIN, 30 pays)

| Pays | N | Pays | N | Pays | N |
|---|---|---|---|---|---|
| SE | 960 | NL | 185 | LT | 29 |
| PL | 733 | CY | 162 | IS | 27 |
| DE | 723 | DK | 159 | SI | 22 |
| FR | 612 | GR | 151 | SK | 22 |
| IT | 424 | LU | 75 | LV | 12 |
| ES | 373 | AT | 75 | LI | 5 |
| RO | 325 | IE | 74 | | |
| BG | 277 | HR | 72 | | |
| NO | 225 | HU | 68 | | |
| FI | 196 | PT | 48 | | |
| BE | 187 | MT | 45 | | |
| | | EE | 38 | | |
| | | CZ | 31 | | |

## 3. Unité = société (LEI) — règle de titre de référence

Deux compteurs distincts, comme demandé : **6 335 ISIN** contre **6 169 LEI**. L'écart (150
sociétés à plusieurs ISIN) vient presque exclusivement de catégories d'actions doubles
(A/B, ordinaire/vote multiple) — ex. Carlsberg A/S (DK0010181676 + DK0010181759), A.P.
Møller-Mærsk (A + B), Raisio Oyj (R + V).

**Règle de titre de référence proposée (déjà en place ailleurs dans ce pipeline, pas une
invention) :** `pipeline/identify.py` interroge déjà GLEIF pour obtenir `legalName.name`
par LEI (`_gleif_nom`), et c'est CE nom — pas le `FullNm` FIRDS, qui varie selon l'ISIN et le
lieu de cotation — qui sert de nom canonique partout ailleurs dans le pipeline. Je propose de
réutiliser exactement cette règle pour l'univers : **le titre de référence d'une société est
son nom légal GLEIF**, pas un nom FIRDS. Exemple vérifié : FIRDS donne `FullNm` = « Revoil S.A.
Namens-Aktien EO -,30 » (contient la forme des actions) contre GLEIF = « ΡΕΒΟΙΛ ΑΝΩΝΥΜΟΣ ΕΛΛΗΝΙΚΗ
ΕΤΑΙΡΕΙΑ ΠΕΤΡΕΛΑΙΟΕΙΔΩΝ » (nom légal grec, transformé en « REVOIL S.A. » côté forme ASCII
translittérée) — GLEIF est la source la plus stable et déjà utilisée pour l'affichage.

### Cross-check LEI vs GLEIF (échantillon)

**Non exhaustif : 6 169 sociétés dépasseraient largement le débit GLEIF praticable en
recherche (60 requêtes/minute) — une vérification complète nécessite le pipeline codé (hors
périmètre de cette phase).** Échantillon aléatoire de 50 LEI (graine fixe 42), interrogé en un
seul appel GLEIF par lot (`filter[lei]=...`, endpoint confirmé supportant les lots) :

- **50/50 LEI trouvés dans GLEIF (100 %).**
- 49/50 noms cohérents (différences de forme juridique/traduction normales : « AG » vs
  « Aktiengesellschaft », translittération grecque/cyrillique, suffixes de type d'action
  retirés — attendu, pas une anomalie).
- **1 incohérence détectée** : LEI `959800JG44HG76EPWH68` — FIRDS = « TECHNOMECA AEROSPACE,
  S.A. », GLEIF = « TECNOQUARK TRUST S.A. » — **noms sans rapport apparent**, contrairement à
  toutes les autres paires de l'échantillon. Signalé tel quel, cause non déterminée dans cette
  session (changement de raison sociale ? réattribution de LEI ? erreur FIRDS ?) — à
  investiguer si cette société entre dans un pilote futur.

Sur les **10 sociétés connues du panel étape 1**, déjà vérifié précédemment : **10/10 LEI FIRDS
identiques aux LEI GLEIF/filings.xbrl.org déjà utilisés dans ce projet**, y compris le nouvel
ISIN Mycronic (SE0025158629) et Sidetrade sur Euronext Growth.

## 4. Table des MIC retenus (134 MIC, triés par nombre d'ISIN)

`RMKT` = marché réglementé · `MLTF` = marché de croissance / MTF, au sens du registre ISO 10383.

| MIC | Pays | Type | Marché | N ISIN |
|---|---|---|---|---|
| XPAR | FR | RMKT | EURONEXT - EURONEXT PARIS | 9941 |
| FRAA | DE | RMKT | BOERSE FRANKFURT - REGULIERTER MARKT | 7353 |
| MTAA | IT | RMKT | EURONEXT MILAN | 6183 |
| DSTO | SE | RMKT | NASDAQ STOCKHOLM AB - NORDIC@MID | 5801 |
| XOSL | NO | RMKT | OSLO BORS | 5248 |
| XETA | DE | RMKT | XETRA - REGULIERTER MARKT | 3911 |
| XMAD | ES | RMKT | BOLSA DE MADRID | 3580 |
| ALXP | FR | MLTF | EURONEXT GROWTH PARIS | 3253 |
| DHEL | FI | RMKT | NASDAQ HELSINKI LTD - NORDIC@MID | 3238 |
| XBRU | BE | RMKT | EURONEXT - EURONEXT BRUSSELS | 3130 |
| MSTO | SE | RMKT | NASDAQ STOCKHOLM AB - AUCTION ON DEMAND | 3084 |
| XSTO | SE | RMKT | NASDAQ STOCKHOLM AB | 2939 |
| XCSE | DK | RMKT | NASDAQ COPENHAGEN A/S | 2906 |
| XAMS | NL | RMKT | EURONEXT - EURONEXT AMSTERDAM | 2826 |
| XWAR | PL | RMKT | WARSAW STOCK EXCHANGE/EQUITIES/MAIN MARKET | 2137 |
| MNSE | SE | MLTF | FIRST NORTH SWEDEN - AUCTION ON DEMAND | 2041 |
| WBAH | AT | RMKT | WIENER BOERSE AG AMTLICHER HANDEL (OFFICIAL MARKET) | 1648 |
| DNSE | SE | MLTF | FIRST NORTH SWEDEN - NORDIC@MID | 1401 |
| MUNB | DE | MLTF | BOERSE MUENCHEN - FREIVERKEHR | 1165 |
| EXGM | IT | MLTF | EURONEXT GROWTH MILAN | 1056 |
| XATH | GR | RMKT | ATHENS EXCHANGE S.A. CASH MARKET | 1037 |
| XLIS | PT | RMKT | EURONEXT - EURONEXT LISBON | 940 |
| MERK | NO | MLTF | EURONEXT GROWTH - OSLO | 917 |
| FRAB | DE | MLTF | BOERSE FRANKFURT - FREIVERKEHR | 829 |
| SGMU | FR | MLTF | SIGMA X EUROPE NON-DISPLAYED BOOK | 760 |
| XMLI | FR | MLTF | EURONEXT ACCESS PARIS | 750 |
| XGAT | DE | MLTF | TRADEGATE BERLIN STOCK EXCHANGE - FREIVERKEHR | 749 |
| XHEL | FI | RMKT | NASDAQ HELSINKI LTD | 670 |
| DUSB | DE | MLTF | BOERSE DUESSELDORF - FREIVERKEHR | 625 |
| XBUD | HU | RMKT | BUDAPEST STOCK EXCHANGE | 563 |
| XSAT | SE | MLTF | SPOTLIGHT STOCK MARKET AB | 549 |
| XNCO | PL | MLTF | WARSAW STOCK EXCHANGE/ EQUITIES/NEW CONNECT - MTF | 522 |
| STUB | DE | MLTF | BOERSE STUTTGART - FREIVERKEHR | 479 |
| DCSE | DK | RMKT | NASDAQ COPENHAGEN A/S - NORDIC@MID | 460 |
| XMSM | IE | RMKT | EURONEXT DUBLIN | 424 |
| MHEL | FI | RMKT | NASDAQ HELSINKI LTD - AUCTION ON DEMAND | 395 |
| GROW | ES | MLTF | BME GROWTH MARKET | 339 |
| XETB | DE | MLTF | XETRA - FREIVERKEHR | 298 |
| MNFI | FI | MLTF | FIRST NORTH FINLAND - AUCTION ON DEMAND | 283 |
| HAMB | DE | MLTF | BOERSE HAMBURG - FREIVERKEHR | 267 |
| XPRA | CZ | RMKT | PRAGUE STOCK EXCHANGE | 255 |
| XCAN | RO | MLTF | CAN - ATS | 242 |
| ABUL | BG | RMKT | BULGARIAN STOCK EXCHANGE - ALTERNATIVE MARKET | 221 |
| DNDK | DK | MLTF | FIRST NORTH DENMARK - NORDIC@MID | 213 |
| XOAS | NO | RMKT | EURONEXT EXPAND OSLO | 208 |
| ZBUL | BG | RMKT | BULGARIAN STOCK EXCHANGE - MAIN MARKET | 192 |
| NSME | SE | MLTF | NORDIC SME | 171 |
| FSME | FI | MLTF | FIRST NORTH FINLAND - SME GROWTH MARKET | 161 |
| XETS | DE | MLTF | XETRA - SCALE | 158 |
| XLIT | LT | RMKT | AB NASDAQ VILNIUS | 151 |
| SSME | SE | MLTF | FIRST NORTH SWEDEN - SME GROWTH MARKET | 143 |
| XBSE | RO | RMKT | SPOT REGULATED MARKET - BVB | 134 |
| XEMA | DE | RMKT | XETRA MIDPOINT REGULATED MARKET | 133 |
| DUSA | DE | RMKT | BOERSE DUESSELDORF - REGULIERTER MARKT | 125 |
| DMAD | ES | RMKT | BOLSA DE MADRID - DARK MIDPOINT | 123 |
| XPOS | IE | MLTF | POSIT DARK | 108 |
| EQTB | DE | RMKT | BOERSE BERLIN EQUIDUCT TRADING - BERLIN SECOND REGULATED MARKET | 105 |
| XTAL | EE | RMKT | NASDAQ TALLINN AS | 99 |
| TQEA | NL | MLTF | TURQUOISE EUROPE - PERIODIC AUCTIONS ORDER BOOK | 98 |
| XESM | IE | MLTF | EURONEXT GROWTH DUBLIN | 96 |
| DNFI | FI | MLTF | FIRST NORTH FINLAND - NORDIC@MID | 91 |
| HAMN | DE | MLTF | BOERSE HAMBURG - LANG AND SCHWARZ EXCHANGE - FREIVERKEHR | 80 |
| XECM | CY | MLTF | MTF - CYPRUS EXCHANGE | 79 |
| STUA | DE | RMKT | BOERSE STUTTGART - REGULIERTER MARKT | 79 |
| DICE | IS | RMKT | NASDAQ ICELAND HF. - NORDIC@MID | 79 |
| TPIR | FR | MLTF | TP ICAP EU - MTF - REGISTRATION | 74 |
| VPXB | BE | MLTF | EURONEXT - VENTES PUBLIQUES BRUSSELS | 72 |
| MUNA | DE | RMKT | BOERSE MUENCHEN - REGULIERTER MARKT | 72 |
| XETU | DE | RMKT | XETRA - REGULIERTERMARKT - OFF-BOOK | 72 |
| XCYS | CY | RMKT | CYPRUS STOCK EXCHANGE | 72 |
| ENXL | PT | MLTF | EURONEXT ACCESS LISBON | 71 |
| AQEU | FR | MLTF | AQUIS EXCHANGE EUROPE | 71 |
| XZAG | HR | RMKT | ZAGREB STOCK EXCHANGE | 69 |
| FRAS | DE | MLTF | BOERSE FRANKFURT - SCALE | 68 |
| XLJU | SI | RMKT | LJUBLJANA STOCK EXCHANGE (OFFICIAL MARKET) | 65 |
| DUSD | DE | MLTF | BOERSE DUESSELDORF - QUOTRIX MTF | 63 |
| HAMA | DE | RMKT | BOERSE HAMBURG - REGULIERTER MARKT | 63 |
| XTND | HU | MLTF | BUDAPEST STOCK EXCHANGE - XTEND | 62 |
| FRAV | DE | MLTF | BOERSE FRANKFURT - FREIVERKEHR - OFF-BOOK | 56 |
| SCLE | ES | MLTF | BME SCALEUP | 54 |
| ALXB | BE | MLTF | EURONEXT GROWTH BRUSSELS | 51 |
| XPRM | CZ | MLTF | PRAGUE STOCK EXCHANGE - MTF | 48 |
| MLXB | BE | MLTF | EURONEXT ACCESS BRUSSELS | 45 |
| HANA | DE | RMKT | BOERSE HANNOVER - REGULIERTER MARKT | 44 |
| ENAX | GR | MLTF | ATHENS EXCHANGE ALTERNATIVE MARKET | 43 |
| ERFQ | DE | MLTF | BLOCKMATCH EUROPE SELECT | 42 |
| WBDM | AT | MLTF | WIENER BOERSE AG VIENNA MTF (VIENNA MTF) | 41 |
| BGEM | IT | MLTF | BORSA ITALIANA GLOBAL EQUITY MARKET | 38 |
| XRMZ | CZ | RMKT | RM-SYSTEM CZECH STOCK EXCHANGE | 37 |
| XMAL | MT | RMKT | MALTA STOCK EXCHANGE | 34 |
| DUSC | DE | RMKT | BOERSE DUESSELDORF - QUOTRIX - REGULIERTER MARKT | 33 |
| POSE | ES | MLTF | PORTFOLIO STOCK EXCHANGE | 31 |
| XNGM | SE | RMKT | NORDIC GROWTH MARKET | 31 |
| XRIS | LV | RMKT | NASDAQ RIGA AS | 30 |
| XGRM | DE | RMKT | TRADEGATE BERLIN STOCK EXCHANGE - REGULIERTER MARKT | 27 |
| TQEX | NL | MLTF | TURQUOISE EUROPE - LIT ORDER BOOK | 27 |
| TWEM | NL | MLTF | TRADEWEB EU BV - MTF | 25 |
| TQEM | NL | MLTF | TURQUOISE EUROPE - DARK | 24 |
| XBRA | SK | RMKT | BRATISLAVA STOCK EXCHANGE | 23 |
| XLUX | LU | RMKT | LUXEMBOURG STOCK EXCHANGE | 20 |
| DSME | DK | MLTF | FIRST NORTH DENMARK - SME GROWTH MARKET | 17 |
| GBUL | BG | MLTF | BULGARIAN STOCK EXCHANGE - SME GROWTH MARKET BEAM | 17 |
| FNEE | EE | MLTF | FIRST NORTH ESTONIA | 14 |
| SPDK | SE | MLTF | SPOTLIGHT STOCK MARKET DENMARK | 13 |
| MBUL | BG | MLTF | MTF SOFIA | 13 |
| MTAH | IT | MLTF | BORSA ITALIANA - TRADING AFTER HOURS | 12 |
| NPEX | NL | MLTF | NPEX | 12 |
| XRMO | CZ | MLTF | RM-SYSTEM CZECH STOCK EXCHANGE - MTF | 11 |
| WBDP | AT | MLTF | WIENER BOERSE AG DIRECT MARKET PLUS | 11 |
| STUD | DE | MLTF | BOERSE STUTTGART - FREIVERKEHR - TECHNICAL PLATFORM 2 | 10 |
| FNLV | LV | MLTF | FIRST NORTH LATVIA | 9 |
| EBRA | SK | MLTF | BRATISLAVA STOCK EXCHANGE - MTF | 6 |
| ALXL | PT | MLTF | EURONEXT GROWTH LISBON | 6 |
| EMTF | LU | MLTF | EURO MTF | 5 |
| LNEQ | FR | MLTF | TP ICAP EU - MTF - LIQUIDNET EU EQUITY | 4 |
| FNLT | LT | MLTF | FIRST NORTH LITHUANIA | 4 |
| MOSE | SE | MLTF | FIRST NORTH SWEDEN - NORWAY AUCTION ON DEMAND | 4 |
| JBUL | BG | MLTF | BULGARIAN STOCK EXCHANGE - INTERNATIONAL MTF | 3 |
| FNIS | IS | MLTF | FIRST NORTH ICELAND | 3 |
| HANB | DE | MLTF | BOERSE HANNOVER - FREIVERKEHR | 3 |
| XZAP | HR | MLTF | PROGRESS MARKET | 3 |
| XICE | IS | RMKT | NASDAQ ICELAND HF. | 3 |
| SPNO | SE | MLTF | SPOTLIGHT STOCK MARKET NORWAY | 3 |
| XNXD | NL | MLTF | NXCHANGE B.V. MTF | 2 |
| HAND | DE | MLTF | BOERSE HANNOVER - FREIVERKEHR - EUROPEAN INVESTOR EXCHANGE | 2 |
| XLJM | SI | MLTF | SI ENTER | 2 |
| XEMB | DE | MLTF | XETRA MIDPOINT OPEN MARKET | 1 |
| XBIL | ES | RMKT | BOLSA DE VALORES DE BILBAO | 1 |
| XBAR | ES | RMKT | BOLSA DE BARCELONA | 1 |
| MABX | ES | MLTF | BME MTF EQUITY (IIC AND ECR SEGMENTS) | 1 |
| XACD | IE | MLTF | EURONEXT ACCESS DUBLIN | 1 |
| PROS | MT | MLTF | PROSPECTS | 1 |
| MUND | DE | MLTF | BOERSE MUENCHEN - GETTEX - FREIVERKEHR | 1 |
| ARTX | LI | MLTF | ARTEX GLOBAL MARKETS AG | 1 |

**Observation importante** : beaucoup de MIC allemands (`FRAB`, `MUNB`, `STUB`, `DUSB`, `XGAT`,
`HAMB`…) sont des marchés « Freiverkehr » régionaux qui cross-cotent des milliers de sociétés
non-UE (constaté précédemment : Canada, Australie, Japon, Chine...) à côté de vraies PME
allemandes. Ce tableau les inclut TOUS tant qu'au moins un ISIN UE/EEE valide y est coté — le
filtre pays (§2) élimine déjà les sociétés non-UE, mais **la décision de garder ou d'exclure
ces segments Freiverkehr pour les sociétés UE elles-mêmes reste à prendre** (ce ne sont pas
forcément les mêmes sociétés que celles visées par methode.md pour "Xetra").

## 5. Points ouverts avant un pilote

1. Décider si les segments Freiverkehr régionaux allemands (hors `XETA`) sont retenus pour les
   sociétés allemandes elles-mêmes, ou si seul `XETA`/`FRAA` (marché réglementé) compte.
2. La seule incohérence LEI trouvée (`959800JG44HG76EPWH68`) reste à investiguer si retenue.
3. Aucun pilote n'a été lancé — en attente de validation.
