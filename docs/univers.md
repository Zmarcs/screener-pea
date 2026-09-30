# Univers — mesures FIRDS (étape 2)

Généré à partir des fichiers FIRDS complets ESMA `FULINS_E_20260905_01of02/02of02` (catégorie
Actions, publication du 05/09/2026), croisés avec le registre officiel ISO 10383 (MIC) du
14/09/2026. Aucune donnée inventée. **Ce document est une mesure, pas encore un pilote : aucun
tirage n'a été effectué à aucun moment.**

**⚠️ Ce document a été entièrement recalculé le 30/09 après la découverte d'un bug de champ
FIRDS majeur (§1, §7).** Les chiffres qui font foi sont ceux des sections ci-dessous. Les
mesures antérieures à cette correction (fondées sur le mauvais champ) sont conservées en
annexe en fin de document, sous un avertissement explicite — **ne pas les utiliser**.

**Univers final (fait foi) : 5 806 ISIN / 5 700 LEI (sociétés).**

# Mesures valides (corrigées le 30/09, points 14-19 — fait foi)

**⚠️ Le §5 (effectifs), le §4bis (classification) et le §7 (strates) ci-dessus sont
SUPERSÉDÉS par cette partie.** En creusant le point 14, j'ai trouvé un bug plus profond que
celui décrit dans la consigne : **tout le comptage par venue depuis le début de la Porte B
utilisait le mauvais champ FIRDS.** Détail, correction et nouveaux chiffres ci-dessous.

## 9. Point 16 (traité en premier — c'est la cause racine du point 14)

**Le champ que j'utilisais pour « la venue » d'un enregistrement FIRDS était faux.**

`TechAttrbts/RlvntTradgVn` (ce que j'utilisais) n'est **pas** une venue par enregistrement :
c'est un attribut **de niveau ISIN** (« venue la plus pertinente en liquidité », un concept
RTS de transparence post-marché), **constant sur tous les enregistrements d'un même ISIN** —
vérifié sur les 729 992 enregistrements du fichier E : **0 exception**. Exemple Atlas Copco A
(SE0017486889) : 42 enregistrements FIRDS, `RlvntTradgVn` = « XSTO » sur les 42 — alors que
`TradgVnRltdAttrbts/Id` (le vrai code venue par enregistrement) vaut successivement AQEA, AQED,
BGEM, DUSB, EQTB, FRAB, HAMB, STUB, XSTO... (42 valeurs distinctes, XSTO n'apparaissant qu'une
fois). C'est ce bug — pas la classification des segments Nordic@Mid — qui explique la majeure
partie de l'écart signalé au point 14 (XSTO/SSME trop bas) : je ne comptais qu'une seule venue
« de référence » par ISIN, jamais ses admissions réelles.

**Correction : `TradgVnRltdAttrbts/Id` est le bon champ.** Reparsing complet des deux fichiers
FIRDS avec ce champ.

**Déduplication (isin, venue) — réponse au point 16 :** avec le bon champ, **0 doublon** sur
729 992 enregistrements (chaque RefData est une paire (ISIN, venue) unique — l'ancien
« doublon » n'existait que parce que je lisais un attribut constant). La logique de
déduplication que j'avais écrite (garder la publication la plus récente `PblctnPrd/FrDt`,
priorité de sécurité à toute présence de `TermntnDt` pour ne jamais perdre une terminaison) est
en place dans `analyse3_champ_correct.py` mais ne s'est déclenchée aucune fois sur ce fichier.

**`TermntnDt` — vérification demandée :** distribution des années très concentrée sur 2026-2028
(496 875 sur ~584 000 valeurs non nulles). Vérifié sur échantillon : ce ne sont **pas** des
artefacts — ce sont trois populations réelles avec une échéance légitime proche : (a) certificats/
warrants/produits structurés à maturité définie (ex. `HPE 7.625 09/01/27 CVT`), (b) droits de
souscription provisoires suédois « BTA » (échéance de quelques semaines, le temps de
l'enregistrement définitif), (c) ADR/certificats représentatifs à durée limitée. Dominés par les
venues allemandes Freiverkehr (STUB, STUH, FRAB, MUND, HAND) — cohérent avec leur rôle de
plateformes de cotation de produits dérivés/structurés. **26 094 valeurs = `9999-12-31`**,
un cas à part : ni une vraie terminaison ni un « actif » confirmable — traité par prudence
comme terminé (la règle existante « toute présence de `TermntnDt` exclut la venue » l'exclut
déjà, sans changement de code nécessaire).

## 10. Point 14 — Reconstruction complète + test décisif

Reparsing des 2 fichiers FIRDS avec le bon champ : **208 MIC réels observés** (contre 134 avant
— l'ancien chiffre ne comptait que des « venues de référence », pas les admissions réelles).

**Classification (item 17 également appliqué, voir §11) :** 54 A, 55 B, 99 C — méthode détaillée
au §11.

**Découverte supplémentaire pendant la vérification (pas dans la consigne, mais nécessaire pour
ne pas fausser l'univers avec le bon champ) : plusieurs venues au nom de marché « normal »
sont en réalité des cotations-reflet passives** qui reprennent automatiquement n'importe quelle
valeur liquide européenne ou mondiale, sans lien avec un choix d'admission de l'émetteur.
Détecté par recoupement avec le panel étape 1 (10 sociétés sans rapport entre elles — si une
venue apparaît sur 8 à 10 d'entre elles au hasard, ce n'est pas une admission choisie) :

| MIC | Occurrences panel étape 1 | Population réelle vérifiée | Décision |
|---|---|---|---|
| DUSD (Düsseldorf Quotrix MTF) | 10/10 | dominée par des blue-chips (Henkel, VW, SAP...) | **C** |
| EQTB (Berlin Equiduct) | 8/10 | idem | **C** |
| WBDM (Vienna MTF) | 5/10 | 1005 ISIN, dominés par des ADR étrangers (Samsung, Alibaba, Baidu...) | **C** |
| JBUL (Bulgarian SE International MTF) | 4/10 | nom explicite « International », dominé par ADR étrangers | **C** |
| BETA (Budapest BETA Market) | 1/10 (SAP) | **vérifié : 20/20 ISIN sont des blue-chips allemands, 0 PME hongroise** — contredit sa fonction officielle | **C** |
| XCAN (Bucharest CAN-ATS) | 1/10 (SAP) | **vérifié : 239/240 ISIN sont des PME roumaines authentiques** (agro-industrie, ateliers...), 1 seul cas anormal | **B conservé** (le cas SAP est un cas isolé, pas assez pour exclure 239 PME réelles) |
| XGRM (Tradegate Berlin, marché réglementé) | 1/10 (SAP) | **3 PME allemandes n'ont AUCUNE autre venue A/B** que XGRM | **A conservé** (les exclure sur un seul cas anormal aurait été disproportionné) |

**Règle de repli ajoutée** (pour ne jamais qu'une venue-écran cause une exclusion totale) :
si la SEULE venue A/B d'un ISIN candidat UE/EEE est DUSD/EQTB/WBDM/JBUL/BETA, elle est quand
même admise via son code registre — **203 ISIN UE/EEE** sont dans ce cas (dont Novo Nordisk sur
une de ses classes, et plusieurs petites allemandes/irlandaises/néerlandaises sans autre venue).

### Test décisif — panel étape 1 (10/10 dans l'univers)

| Société | Catégories | Venues A/B retenues |
|---|---|---|
| Hermès | A | XPAR |
| ASML | A | XAMS |
| SAP | A, B | FRAA, STUA, STUC, STUE, XCAN, XETA, XGRM |
| Atlas Copco A | A | DSTO, MSTO, XSTO |
| Boliden | A | DSTO, MSTO, XSTO |
| Brunello Cucinelli | A | MTAA |
| Thermador | A | XPAR |
| Sidetrade | B | ALXP |
| Mycronic | A | DSTO, MSTO, XSTO |
| Valneva | A | XPAR |

**Aucune absente.** Les segments Nordic@Mid/Auction on Demand (DSTO, MSTO...) apparaissent bien
pour Atlas Copco/Boliden/Mycronic, conformément au point 14 — mais désormais **en plus** de XSTO
lui-même (qui, avec le bon champ, apparaît directement comme une vraie venue admise, ce qui
n'était jamais le cas avec l'ancien champ).

## 11. Point 17 — Règle A/B strictement au sens registre, palier fonctionnel en information

**Nouvelle règle** : A = `RMKT` au registre ISO (marché réglementé au sens juridique — l'ESEF
est obligatoire), B = `MLTF` au registre (MTF — l'ESEF n'est pas obligatoire). Le palier
fonctionnel (« vrai marché de croissance avec accord de l'émetteur » vs « MTF générique ») n'est
plus utilisé pour trancher A/B — uniquement pour un **motif informatif** dans la table.

Conséquence directe : **XOAS et ABUL reviennent en A** (ils sont `RMKT` au registre — la
reclassification fonctionnelle en B du point 9 est annulée) :

| MIC | Marché | Code registre | Catégorie actuelle | Palier fonctionnel (information) |
|---|---|---|---|---|
| XOAS | Euronext Expand Oslo | RMKT | **A** | Palier de croissance (comme Euronext Growth), mais juridiquement un marché réglementé → ESEF obligatoire |
| ABUL | Bulgarian SE Alternative Market | RMKT | **A** | Accueille des sociétés petites/peu liquides comme un palier de croissance, mais juridiquement un marché réglementé → ESEF obligatoire |

Le C reste un filtre **avant** cette règle (dark/midpoint/internalisateurs/OTF/plateformes
tierces génériques) — appliqué même à des venues `RMKT` (XEMA, DMAD) quand ce ne sont
manifestement pas des marchés d'admission pour l'émetteur.

## 12. Point 15 — Contrôle de vraisemblance (comparaison à des chiffres publiés)

**⚠️ Correction du 30/09 (suite au point 21/22) : plusieurs citations de ce tableau, dans sa
version précédente, ne résistaient pas à une vérification directe de la source.** L'outil de
recherche utilisé donnait des réponses synthétisées avec une date et un chiffre précis
d'apparence fiable, mais qui ne correspondaient pas toujours à ce que la page citée contient
réellement une fois consultée directement. Trois exemples concrets, trouvés en revérifiant
chaque source à la main (`WebFetch` sur la page elle-même, pas la synthèse du moteur de
recherche) :

| Chiffre cité précédemment | Réalité trouvée en vérifiant la source directement |
|---|---|
| « Nasdaq Helsinki : 136 principal / 47 First North, T4 2025 » | Le communiqué Nasdaq « Annual Trading Statistics 2025 » cité ne donne **aucun chiffre par place** (seulement l'agrégat Nordique+Balte : 675 marché principal + 444 First North). Le chiffre 136/47 ne provient pas de cette source. |
| « Nasdaq Stockholm : 363 sociétés, 31/12/2025 » | La page Wikipédia réellement citée donne **383 (ou 385 principal + 447 secondaire = 832), au 31 MARS 2021** — pas 363, pas fin 2025. |
| « BME Growth + ScaleUp : 157 sociétés, déc. 2025 » | Le communiqué BME cité ne contient **pas ce chiffre** (il parle de turnover et d'emploi, pas d'un décompte de sociétés). Le chiffre 157 est introuvable dans la source citée. |

**Conséquence : je retire ces trois comparaisons et toute conclusion qui s'appuyait dessus (dont
le « 0,0 % exact » pour la Finlande et le « +34,4 % » pour BME Growth).** Nouvelle règle de
travail adoptée pour la suite : plus jamais de chiffre cité sans l'avoir lu moi-même sur la page
source (`WebFetch` direct), jamais depuis la réponse synthétisée d'un moteur de recherche seul.

**Ce qui reste effectivement vérifié en relisant les sources directement :**

| Place | Univers (sociétés) | Chiffre trouvé en lisant la source directement | Source, date réelle | Écart | Statut |
|---|---|---|---|---|---|
| **Suède, total** | 875 | **909** | OECD, *The Swedish Equity Market, Assessment and Policy Recommendations 2026*, chapitre 2 « Mapping the Swedish equity markets », page ouverte directement le 30/09/2026 : `oecd.org/en/publications/the-swedish-equity-market-assessment-and-policy-recommendations-2026_0db1ebf9-en/full-report/mapping-the-swedish-equity-markets_7baf7162.html` — « At the end of 2025, there were 909 listed companies on the Swedish equity market » | **−3,7 %** | ✅ conforme |
| Nasdaq Stockholm, marché principal (A, SE) | 347 | **346** | même page : « the main regulated market, which hosts 346 listed companies » (end-2025) | +0,3 % | ✅ quasi exact |
| Nasdaq First North Suède (partie de B, SE) | 306 | **339** (685 Nasdaq Stockholm total − 346 principal) | même page : « Nasdaq Stockholm... 685 listed companies » | −9,7 % | ✅ conforme |
| Spotlight Stock Market (partie de B, SE) | 126 | **124** | même page : « Spotlight Stock Market... has 124 listed companies » (end-2025) | +1,6 % | ✅ quasi exact |
| NGM Main Regulated + Nordic SME (partie de A+B, SE) | 95 (XNGM+NSME) | **100** (12 Main Regulated + 88 Nordic SME) | même page : « operates a regulated market called Main Regulated, which currently lists twelve companies, and an MTF, NGM Nordic SME, with 88 listed companies » | −5,0 % | ✅ conforme |
| Nasdaq Helsinki, marché principal + First North (A/B, FI) | 136 / 48 | **non trouvé** | recherché spécifiquement le 30/09/2026 (nasdaq.com/products/european-markets/helsinki, nasdaq.com/market-activity/stocks/screener, nasdaq.com/european-market-activity/shares, Wikipédia « List of companies listed on Nasdaq Helsinki » — page inexistante) : aucune page ouverte ne donne de chiffre net, daté et sourcé pour Helsinki spécifiquement | — | **❔ non vérifié** (la seule mention 134/50 trouvée reste l'infobox Wikipédia d'avril 2024, jugée insuffisante par la consigne du point 29) |
| Nasdaq Nordique + Baltique, agrégat (tous pays confondus) | — | 675 marché principal + 444 First North = 1 119 | Nasdaq, communiqué officiel « Annual Trading Statistics 2025 », page ouverte le 30/09/2026, **31/12/2025** | non décomposable par pays depuis cette source | ✅ source fiable, mais pas de détail par pays |

**BME Growth/ScaleUp et Bolsa de Madrid (111), Euronext Paris (« >800 »), GPW Varsovie,
Wiener Börse : aucun chiffre externe que j'ai pu confirmer en lisant la source primaire
moi-même.** Les **4 places explicitement sans aucun chiffre externe fiable trouvé** (demande du
point 22) : **Nasdaq Copenhague, Euronext Milan, Euronext Dublin, Wiener Börse** — dans les
quatre cas, toutes les pages consultées renvoyaient soit des agrégats multi-places, soit des
décomptes incluant d'autres types d'instruments (obligations, certificats), jamais un chiffre
net et daté pour la place seule.

**Point 28 — lequel des 3 chiffres retirés était faux, précisément :** les trois citations
retirées (Finlande 136/47 « T4 2025 », Suède 363 « 31/12/2025 », BME 157 « déc. 2025 »)
provenaient d'une synthèse de moteur de recherche, **aucune des trois n'était en réalité tirée
de la page OCDE** que vous citez pour votre cible de 909 — cette page OCDE, maintenant ouverte
et vérifiée ligne par ligne ci-dessus, est **exacte à 100 %** (909 = 346+339+12+88+124, tous les
sous-totaux confirmés mot pour mot). Le chiffre « Suède 363 » était le plus nettement faux des
trois : sa propre source (Wikipédia) ne le contient même pas (elle donne 383-385, datés de
mars 2021) — c'est une invention pure du moteur de recherche, pas une confusion de date sur un
vrai chiffre.

### BME Growth — ventilation par type d'instrument (point 22, ma propre donnée, vérifiable)

Je ne peux plus comparer à un total BME externe fiable, mais je peux expliquer avec certitude
**pourquoi mon propre chiffre ES-B (212 sociétés) est probablement gonflé au regard du
périmètre de methode.md**, en ventilant ma propre population (donnée FIRDS, vérifiable) :

| Catégorie | Effectif | Note |
|---|---|---|
| **Total ES classé B seul** | 212 | — |
| dont nom contient « SOCIMI » (foncière cotée espagnole) | **131 (61,8 %)** | **Hors périmètre `methode.md` ("V1 : hors banques, assurances et foncières")** |
| dont admis uniquement via XMLI (Euronext Access Paris, cross-cotation) | 45 | plusieurs sont elles-mêmes des SOCIMI (ex. « Barings Core Spain SOCIMI », « Iposa Properties Socimi ») — chevauche partiellement la ligne au-dessus |
| **ES-B hors SOCIMI** | **81** | population plausible de « vraies » PME de croissance espagnoles |
| Répartition par venue | GROW 111 · SCLE 50 · XMLI 45 · ALXP 8 · ENXL 2 · EXGM 1 | — |
| Répartition par CFI | `ESVUFR` 157 · `ESVUFB` 53 · autres 2 | actions ordinaires dans les deux cas — le type CFI ne distingue pas SOCIMI d'opérationnelle |

**Ceci explique une bonne partie de tout écart BME que j'aurais pu citer** : plus de 6 sociétés
sur 10 de mon ES-B sont des foncières (SOCIMI), une catégorie que `methode.md` exclut
explicitement de l'univers V1. **Cette exclusion n'est pas encore appliquée dans les chiffres
de ce document (le filtre sectoriel n'existe pas encore en code, aucun pipeline `univers.py`
écrit)** — c'est un écart de PÉRIMÈTRE (filtre sectoriel pas encore appliqué), pas un bug de
comptage de venues. Une fois le filtre sectoriel codé, ES-B tombera mécaniquement de 212 à
environ 81 (hors XMLI/SOCIMI se recoupant partiellement).

## 13. Point 18 — File de revue LEI en 3 niveaux

Reclassement de la file de revue du §6 (729 LEI) :

| Niveau | Effectif | Définition |
|---|---|---|
| **Changement de nom probable (avec source)** | 1 | Source externe confirmant le changement — Technomeca/Tecnoquark uniquement |
| **LEI douteux** | 12 | Noms FIRDS/GLEIF sans rapport apparent, secteurs d'activité différents, aucune explication plausible trouvée |
| **Concordance confirmée manuellement** | 10 | Faux positifs de l'algorithme (sigles/traductions légitimes identifiés manuellement — ex. EYDAP = sigle grec d'« Athens Water Supply Sewerage Company ») |
| **À revoir** | 706 | Ni confirmé ni clairement anormal — reste en attente |

**LEI douteux (liste complète, 12) :** KEYRUS/GOLDMAN SACHS PARIS ; FMG/WISE ENERGY ; Space Nord
Invest/Hifab Group ; ERWE Immobilien/KSLK Trust ; Lasernet Group/FormPipe Software ; IBSM/WISE
FINANCE ; Voim ASA/Electromagnetic Geoservices ; STOHID/YetiForce ; CIBIX/Befimmo ;
WATERA/Mascara Nouvelles Technologies ; QEV/SPEAR Investments ; Neles Oyj/TP ICAP (Europe).

**Règle appliquée (comme demandé) : aucun LEI douteux n'alimente l'ingestion ESEF avant
validation manuelle.** Ce n'est pas encore codé dans un pipeline (aucun code `pipeline/univers.py`
n'existe) — c'est une règle à respecter quand ce code sera écrit.

**Contrôle automatique proposé pour le pilote (design, pas codé, pas lancé)** : pour chaque
société, comparer le chiffre d'affaires du dernier exercice ESEF au chiffre d'affaires yfinance
le plus récent disponible ; écart relatif > 30 % → badge « LEI ou ticker suspect », routé en
revue manuelle, jamais silencieux. Nécessite le code ISIN→ticker (point 5 des décisions
précédentes, toujours pas écrit) avant de pouvoir s'exécuter.

Liste complète des 729 entrées : [`docs/revue_lei_gleif.csv`](revue_lei_gleif.csv) (mis à jour,
colonne `niveau`).

## 14. Point 19 — Stratification recalculée (méthode + pondération, toujours PAS TIRÉE)

**Recalcul avec les chiffres corrigés (§10/§11), même méthode qu'avant (plancher 5 + prorata) :**
40 strates (21 axe A, 19 axe B — la Norvège n'a que 1 société « A seul », 151 sont A-et-B et
comptées côté B, cf. tableau ; c'est un effet réel de la structure du marché norvégien —
Euronext Expand/Growth Oslo chevauche massivement le marché principal — pas une erreur).

| Strate | Axe | Pays regroupés | Population | Poids (N_h/N) | Échantillon proposé |
|---|---|---|---|---|---|
| PL | A | PL | 385 | 0,068 | 14 |
| SE | A | SE | 352 | 0,062 | 14 |
| DE | A | DE | 304 | 0,053 | 12 |
| FR | A | FR | 286 | 0,050 | 12 |
| BG | A | BG | 186 | 0,033 | 10 |
| IT | A | IT | 184 | 0,032 | 10 |
| Nordique restreint (A) | A | FI,IS | 160 | 0,028 | 9 |
| GR | A | GR | 125 | 0,022 | 8 |
| ES | A | ES | 119 | 0,021 | 8 |
| DK | A | DK | 105 | 0,018 | 8 |
| NL | A | NL | 105 | 0,018 | 8 |
| BE | A | BE | 100 | 0,018 | 7 |
| RO | A | RO | 85 | 0,015 | 7 |
| Micro-États (A) | A | MT,LU,LI | 73 | 0,013 | 7 |
| HR | A | HR | 69 | 0,012 | 7 |
| CY | A | CY | 68 | 0,012 | 7 |
| Baltique (A) | A | EE,LV,LT | 51 | 0,009 | 6 |
| AT | A | AT | 47 | 0,008 | 6 |
| Péninsule ibérique & Irlande (A) | A | PT,IE | 45 | 0,008 | 6 |
| HU | A | HU | 44 | 0,008 | 6 |
| Europe centrale (A) | A | CZ,SK,SI | 35 | 0,006 | 6 |
| NO | A | NO | 1 | 0,000 | 1 |
| SE | B | SE | 523 | 0,092 | 18 |
| PL | B | PL | 341 | 0,060 | 13 |
| FR | B | FR | 306 | 0,054 | 13 |
| RO | B | RO | 240 | 0,042 | 11 |
| IT | B | IT | 224 | 0,039 | 11 |
| ES | B | ES | 211 | 0,037 | 10 |
| NO | B | NO | 211 | 0,037 | 10 |
| DACH élargi (B) | B | DE,AT | 190 | 0,033 | 10 |
| Méditerranée (B) | B | GR,CY,MT | 108 | 0,019 | 8 |
| Benelux (B) | B | NL,BE,LU | 95 | 0,017 | 7 |
| Nordique restreint (B) | B | DK,FI,IS | 93 | 0,016 | 7 |
| BG | B | BG | 91 | 0,016 | 7 |
| Péninsule ibérique & Irlande (B) | B | PT,IE | 59 | 0,010 | 6 |
| Europe centrale & Balkans (B) | B | HU,HR,SI | 28 | 0,005 | 6 |
| CZ | B | CZ | 24 | 0,004 | 6 |
| Baltique (B) | B | EE,LT,LV | 19 | 0,003 | 5 |
| SK | B | SK | 7 | 0,001 | 5 |
| LI | B | LI | 1 | 0,000 | 1 |
| **Total (40 strates)** | | | **5700** | **1,000** | **333** (+10 témoins = 343) |

**Méthode de pondération et d'extrapolation pour le rapport du pilote (description, pas encore
exécutée)** :
- Poids de sondage par strate : `w_h = N_h / N` (population de la strate ÷ population totale de
  l'univers, colonne ci-dessus).
- Pour un taux mesuré dans le pilote (ex. % de sociétés avec ≥ 5 exercices ESEF), l'estimateur
  stratifié est `p̂ = Σ w_h × p̂_h` (moyenne des taux par strate pondérée par leur poids réel dans
  l'univers, pas par leur poids dans l'échantillon — corrige le sur-échantillonnage volontaire
  des petites strates).
- Variance stratifiée : `Var(p̂) = Σ w_h² × p̂_h(1−p̂_h) / (n_h−1)`, intervalle de confiance à
  95 % = `p̂ ± 1,96 × √Var(p̂)`.
- Les 10 témoins étape 1 ne sont **pas** intégrés à l'estimateur stratifié (ils ne sont pas un
  tirage aléatoire de leur strate) — affichés séparément dans le rapport du pilote, à titre de
  repère qualitatif uniquement.

**Toujours aucun tirage effectué.** Cette section documente la méthode d'extrapolation pour
quand le pilote sera lancé — après votre validation.

## 15. Fait / pas fait (points 14-19)

- **14 (reclassification Nordic@Mid/Auction, test décisif)** : fait, et complété par la
  découverte du bug de champ FIRDS sous-jacent (cause principale de l'écart signalé).
- **15 (contrôle de vraisemblance)** : fait, puis **corrigé au point 21-22** après découverte
  que 3 des citations initiales ne résistaient pas à une vérification directe de la source
  (voir §12) — retirées et remplacées par ce qui est réellement vérifié.
- **16 (déduplication FIRDS)** : fait — la réponse est que le bug de champ expliquait les
  « doublons » ; avec le bon champ, 0 doublon réel, 0 contradiction de `TermntnDt`.
- **17 (A = registre RMKT, palier fonctionnel en information)** : fait, XOAS et ABUL redevenus A.
- **18 (3 niveaux LEI + contrôle pilote CA ESEF/yfinance)** : fait pour le reclassement (1/12/10/706) ;
  le contrôle automatique est conçu mais pas codé (pas de pipeline ISIN→ticker encore écrit).
- **19 (pas de tirage avant 14/15, méthode de pondération)** : fait — aucun tirage effectué à
  aucun moment de cette session ; méthode d'extrapolation et d'IC documentée pour le pilote futur.

`docs/univers.md`, `docs/journal_etape2.md` et `CLAUDE.md` mis à jour. Pas de commit.

## 16. Point 24 — Table des champs FIRDS (sourcée ESMA) + non-régression

**Source officielle** : ESMA, *FIRDS Reference Data Reporting Instructions*, réf. ESMA65-11-1193,
version du 17/09/2020 (`esma.europa.eu/sites/default/files/library/esma65-11-1193_firds_reference_data_reporting_instructions_v2.1.pdf`),
§2.3.4.2 (définitions de champ) — citations exactes extraites du PDF, pages indiquées.

| Champ XPath | Définition ESMA (citation exacte) | Usage correct |
|---|---|---|
| `TradgVnRltdAttrbts/Id` (champ RTS n°6, p.19) | « Segment MIC for the trading venue or systematic internaliser, where available, otherwise operating MIC, where the financial instrument was admitted to trading or was traded, including where orders or quotes were placed through its system. » + note : « If an instrument is multi-listed a record for each segment MIC where the instrument is traded should be sent. » | **C'est le champ venue à utiliser.** Un `RefData` = une admission réelle sur UNE venue ; un ISIN multi-coté a un `RefData` par venue. |
| `TechAttrbts/RlvntTradgVn` (champ technique, pas de n° RTS, p.39-40) | « Identifies the MIC of the Trading Venue that reported the record considered as the reference for the data published by ESMA (RCA record), and used as well to perform automated consistency checks on the data received. » | **Champ technique interne à ESMA (contrôle de cohérence), PAS une venue d'admission.** Constant sur tous les `RefData` d'un même ISIN — confirmé empiriquement (0 exception sur 729 992 enregistrements) et confirmé par la définition ESMA elle-même (« reference... for consistency checks », pas « venue d'admission »). |
| `TradgVnRltdAttrbts/TermntnDt` (champ RTS n°12, p.20) | « Date and time when the financial instrument ceases to be traded or to be admitted to trading on the trading venue. Where this date and time is not yet known, the field shall not be populated. » | Absent = admission active sur cette venue. Présent = terminée sur CETTE venue (peut rester active sur une autre). |
| `TradgVnRltdAttrbts/IssrReq` (champ RTS n°8, p.19) | « Whether the issuer of the financial instrument has requested or approved the trading or admission to trading of their financial instruments on a trading venue. » | Utilisable à l'avenir pour distinguer une admission choisie par l'émetteur d'une admission passive (ex. un internalisateur systématique qui reprend un prix sans accord de l'émetteur) — pas encore exploité dans le code actuel. |

**Non-régression ajoutée** : [`tests/test_firds.py`](../tests/test_firds.py) (4 tests), sur un
extrait RÉEL de 2 enregistrements du fichier ESMA du 05/09/2026
([`tests/fixtures/firds_extrait_reel.xml`](../tests/fixtures/firds_extrait_reel.xml), pas de
données inventées) : Paradox Interactive AB (SE0008294953, admise sur SSME — First North Suède
— alors que son `RlvntTradgVn` affiche à tort XSTO) et Raisio Oyj (FI0009800395, admise sur
AQEU — MTF tiers — alors que son `RlvntTradgVn` affiche à tort DHEL). Un 4ᵉ test relit le
code source de `pipeline/firds.py` et échoue si `RlvntTradgVn` est un jour utilisé comme champ
venue.

**Nouveau module** : [`pipeline/firds.py`](../pipeline/firds.py) — la première brique de code
Porte B réellement écrite (parsing FIRDS uniquement ; pas de filtre candidat, pas de
classification A/B/C, pas de pipeline `univers.py` — ça reste à écrire après validation).

**Couverture des 134 (désormais 138) tests unitaires sur le parsing FIRDS** : **0 des 134 tests
précédents ne couvraient le parsing FIRDS** — tout le travail Porte B avant ce point était fait
par des scripts d'analyse ponctuels (`analyse2.py`, `analyse3_champ_correct.py`...), jamais
ajoutés à `pipeline/` ni testés par `pytest`. **Les 4 nouveaux tests de `test_firds.py` sont les
seuls à ce jour.** Total : **138 tests passants** (134 + 4).

## 17. Point 25 — Couverture de la vérification LEI sur l'univers final

**Confirmé sans relance nécessaire.** L'univers final corrigé (5 700 LEI) est un **sous-ensemble
strict** de l'ancien univers (6 169 LEI, mauvais champ) déjà entièrement vérifié auprès de
GLEIF : **0 LEI du nouvel univers n'a été vérifié** — les 5 700 étaient déjà dans le lot des
6 169 contrôlés. Pas de nouvel appel GLEIF nécessaire.

**Priorisation des 706 « à revoir »** (demandée) : vérification de la présence d'au moins un
rapport ESEF via `filings.xbrl.org` (`xbrl_filings_api`, par lots de 80 LEI, 114 s au total) —
**212 des 706 ont au moins un rapport ESEF disponible** (colonne `esef_disponible` ajoutée à
[`docs/revue_lei_gleif.csv`](revue_lei_gleif.csv), triée pour les faire remonter en premier).
**Priorisation par liquidité non faite** : nécessite le code ISIN→ticker (toujours pas écrit,
point 5 des décisions précédentes) pour interroger yfinance — bloqué en amont, pas oublié.

## 18. Point 26 — Contrôle permanent de dérive semaine à semaine (conception, pas lancé)

**Conception, pas de code de production ni d'exécution programmée** (aucune orchestration
Porte B n'existe encore). Mécanisme proposé pour quand le pipeline `univers.py` existera :

1. À chaque rafraîchissement hebdomadaire FIRDS, recalculer les effectifs par pays × catégorie
   (A seul / B seul / A+B, comme au §10 ci-dessus) et les écrire dans un fichier daté
   (`data/processed/univers_historique/AAAA-MM-JJ.json`).
2. Comparer au fichier de la semaine précédente, pays par pays et catégorie par catégorie.
3. **Écart relatif > 10 % sur un pays ou une catégorie → entrée dans le rapport d'erreurs**
   (`JOURNAL.avertissement`, même mécanisme que le reste du pipeline), jamais une exception
   silencieuse ni un blocage du run.
4. Cas **attendus et à ne pas confondre avec une anomalie** : IPO/radiations en nombre inhabituel
   un jour donné, republication FIRDS après une correction ESMA (rare mais déjà documenté par
   ESMA elle-même, cf. §16), premher rafraîchissement après un changement de code de
   classification (ex. si le §11 est à nouveau révisé).
5. Implémentation prévue : une fonction `pipeline/univers.py::controler_derive(actuel, precedent)`
   — écrite en même temps que le reste du pipeline `univers.py`, pas avant (pas de code sans
   les fondations qui vont avec).

**Rien n'est tiré, rien n'est lancé.**

## 19. Point 31 — Repérage des candidats hors périmètre V1 (HYPOTHÈSE, rien supprimé)

**HYPOTHÈSE — détection par mots-clés dans le nom FIRDS uniquement, pas de vérification
individuelle par société.** Taux de faux positifs/négatifs attendu (ex. un nom contenant
« Bank » n'est pas toujours une banque ; une SOCIMI peut ne pas contenir le mot dans son nom
commercial). **Rien n'est retiré de l'univers — uniquement marqué pour référence.** Catégories
recherchées (`methode.md` : "V1... hors banques, assurances et foncières" — fonds/SICAV/sociétés
d'investissement ajoutés par analogie, HYPOTHÈSE complémentaire) :

| Catégorie | Mots-clés (regex, insensible à la casse) |
|---|---|
| Foncière/REIT | SOCIMI, REIT, REAL ESTATE INVESTMENT TRUST, FASTIGHET(Suède), EIENDOM(Norvège), KIINTEISTÖ(Finlande), IMMOBILIEN, IMMOBILIARE, FONCIÈRE, PROPERTY/PROPERTIES |
| Banque | BANK, BANKA, BANCO, BANQUE, BANCA, SPARBANK, BANCAIRE |
| Assurance | INSURANCE, ASSURANCE, VERSICHERUNG, FÖRSÄKRING, SEGUROS, ASSICURAZIONI, RÉASSURANCE |
| Fonds/SICAV/investissement | SICAV, FUND, FONDS, FOND, INVESTMENT TRUST, ETF, ETP |

**370 ISIN / 364 sociétés (LEI) marquées** sur l'ensemble de l'univers (5 700 LEI, soit 6,4 %) :

| Catégorie hors-V1 | ISIN marqués |
|---|---|
| Foncière/REIT | 259 |
| Banque | 85 |
| Fonds/SICAV/investissement | 15 |
| Assurance | 11 |

**Par pays (sociétés, A et B) :**

| Pays | Total marqué | dont A | dont B |
|---|---|---|---|
| ES | 140 | 8 | 132 |
| BG | 58 | 56 | 20 |
| SE | 38 | 29 | 10 |
| IT | 15 | 15 | 0 |
| DK | 13 | 12 | 1 |
| DE | 10 | 5 | 6 |
| CY | 10 | 8 | 2 |
| AT | 9 | 8 | 4 |
| GR | 9 | 8 | 2 |
| MT | 7 | 6 | 1 |
| FR | 6 | 5 | 1 |
| NO | 6 | 2 | 6 |
| NL | 5 | 4 | 1 |
| HR | 5 | 5 | 0 |
| RO | 5 | 3 | 2 |
| PL, FI, IE | 4 chacun | — | — |
| LU, HU | 3 chacun | — | — |
| CZ, BE, EE, SK, SI, PT | 1-2 chacun | — | — |

**Confirmation du chiffre 131/212 pour l'Espagne (demandée)** : en relançant la détection avec
la liste de mots-clés élargie ci-dessus (pas seulement « SOCIMI » seul), je trouve **132**
sociétés espagnoles classées B et marquées foncière/REIT, contre 131 cité précédemment (simple
recherche du seul mot « SOCIMI »). Écart de 1, cohérent : un cas supplémentaire capté par un
mot-clé plus large (ex. « Property »/« Real Estate » sans le mot « SOCIMI » dans le nom). **Le
chiffre 212 (total ES-B) est confirmé exact.**

Note sur le nombre élevé en Bulgarie (58, dont 56 « banque ») : possible sur-détection — à
vérifier individuellement avant toute utilisation, non fait dans cette session (mot-clé « BANK »
peut capter des noms bulgares transittérés sans rapport). **Marqué HYPOTHÈSE, pas une conclusion.**

Liste complète (370 lignes, ISIN/LEI/nom/catégorie/CFI/catégorie A-B-C) :
[`docs/hors_v1_hypothese.csv`](hors_v1_hypothese.csv).

## 20. Fait / pas fait (points 20-26)

- **20 (réaffichage panel + vraisemblance + effectifs)** : fait, affiché dans la réponse de
  cette session (et déjà dans la précédente).
- **21 (source Finlande)** : fait — et la vérification a **invalidé** la citation précédente
  (§12) : la vraie source (Wikipédia, avril 2024, sans citation primaire) donne 134/50, pas
  136/47 T4 2025. Corrigé, pas caché.
- **22 (ventilation BME + comparaison Euronext Paris + 4 places nommées)** : fait pour BME
  (ventilation CFI/venue/SOCIMI, §12 — 61,8 % de foncières hors périmètre methode.md, explique
  une bonne part de tout écart) ; **pas fait** pour Euronext Paris par compartiment (aucune
  décomposition officielle trouvée, même en cherchant directement) ; 4 places nommées : Nasdaq
  Copenhague, Euronext Milan, Euronext Dublin, Wiener Börse.
- **23 (restructuration du document)** : fait — les mesures valides sont en tête, l'ancien
  contenu (mauvais champ) est dans une annexe explicitement marquée « NE PAS UTILISER » en fin
  de fichier.
- **24 (non-régression + table des champs sourcée ESMA)** : fait — `pipeline/firds.py`,
  `tests/test_firds.py` (4 tests, extrait réel), table sourcée ESMA65-11-1193 au §16. Confirmé :
  0 des 134 tests précédents ne couvrait le parsing FIRDS.
- **25 (couverture LEI)** : fait — confirmé complet, 0 relance nécessaire. 706 « à revoir »
  priorisés par présence ESEF (212/706) ; priorisation liquidité bloquée par l'absence du code
  ISIN→ticker (déjà connu).
- **26 (contrôle de dérive permanent)** : conçu, pas codé (pas de pipeline `univers.py` à brancher
  dessus pour l'instant).

## 21. Point 34 — Catégorie principale : A si ≥1 venue A, sinon B

**Règle adoptée** : une société est classée **A si elle a au moins une venue A, sinon B** — les
« A+B » (287 sociétés) **comptent en A**, plus de catégorie mixte. Ancien comptage A_et_B
(toujours utile pour comprendre la composition, gardé en information) : **NO 151, BG 60, DE 18**
(+ AT 11, CY 8, SE 7, CZ 6...).

**Quelle venue B ajoute ces sociétés, par pays :**

| Pays | Venue(s) B en cause | Explication |
|---|---|---|
| **NO (151)** | DOSE, MOSE, ONSE (chacune sur les mêmes 151 sociétés) | « First North Sweden - Norway... » : extension transfrontalière **documentée** de First North (infrastructure suédoise, mais nommément pour des émetteurs norvégiens) — 154/166 ISIN de ces 3 MIC sont à préfixe NO (§22/point 35). Pas une cotation-reflet : ces sociétés norvégiennes ont un vrai second point d'accès Nasdaq en plus de leur cotation principale Oslo Børs (XOSL). |
| **BG (60)** | MBUL (59) essentiellement | « MTF Sofia » — reclassée B par la règle registre stricte du point 17 (était C dans l'ancienne classification manuelle). 73/74 ISIN sur MBUL sont à préfixe BG (§22) : une vraie extension MTF bulgare, pas du bruit. |
| **DE (18)** | XCAN (15), XPRM (5), XRMO (3), avec chevauchement | **Bruit confirmé** (§22/point 35) : ce sont des cotations-reflet (Bucarest/Prague/RM-System) sur des sociétés allemandes déjà admises sur un vrai marché réglementé allemand — la règle « A si ≥1 venue A » les classe déjà correctement en A, donc ce bruit ne change aucun résultat pour ces 18 sociétés. |

## 22. Point 35 — Cohérence pays de la venue / pays de l'ISIN, pour chaque venue B

**XCAN, détail par pays (demandé nommément)** : RO 240 (93,4 %) · DE 15 (5,8 %) · PL 1 · CY 1.
**Part hors Roumanie : 6,6 %.** Confirmé au point précédent : ces 15 ISIN allemands ne sont
jamais la seule venue B d'une société (vérifié : 0 société allemande « B seul » n'a XCAN comme
unique venue B) — sans conséquence sur l'admission de ces 15 sociétés (déjà A par ailleurs).

**Même mesure pour toutes les venues B** (table complète :
[`docs/point35_venues_b.csv`](point35_venues_b.csv)) — cas les plus marquants :

| Venue | Pays de la venue | Part hors pays | Nature (établie en croisant avec le détail) |
|---|---|---|---|
| DOSE / MOSE / ONSE | SE (registre) | **98,8 %** (154/166 = NO) | Transfrontalier **documenté** (First North Sweden - Norway, cf. §21) — pas du bruit malgré le % élevé |
| JBUL | BG | **100 %** (0/8 = BG) | Bruit — 8 admissions de repli (venue-écran), 0 société bulgare |
| WBDM | AT | **86,2 %** (4/29) | Bruit — sous-ensemble des admissions de repli, dominé par des sociétés étrangères |
| XMLI | FR | **47,3 %** (68/129 = FR, 45 = ES) | Mixte : une vraie part française + une contamination espagnole substantielle (SOCIMI, cf. §12) |
| DUSD | DE | **44,3 %** (102/183 = DE) | Bruit partiel — sous-ensemble des admissions de repli (venue-écran) |
| XPRM | CZ | **71,1 %** (11/38 = CZ, 10 = AT) | Bruit probable, pas vérifié individuellement |
| ENAX | GR | **30,8 %** (9/13 = GR, 4 = CY) | Plausible : Chypre et Grèce partagent souvent une double cote (proximité économique) — pas vérifié individuellement |
| Toutes les autres venues B nommées (SSME, DNSE, MNSE, ALXP, GROW, NSME, FSME, DNFI, MNFI, DSME, DNDK, EBRA, FNEE, FNLV, ALXB, XESM, NPEX, XLJM, XZAP, ALXL...) | — | **0-16 %** | Cohérentes avec leur pays — pas de signal de bruit |

**Règle proposée (à valider, PAS codée)** : une venue B ne compte pour l'admission que si (a)
le pays de la venue = préfixe pays de l'ISIN, **ou** (b) la venue est explicitement listée comme
extension transfrontalière documentée (aujourd'hui : DOSE/MOSE/ONSE pour la Norvège — à
compléter si d'autres cas documentés apparaissent, jamais par déduction automatique du taux de
discordance seul, cf. ENAX ci-dessus où un taux élevé ne veut pas forcément dire « bruit »).

**Allemagne « B seul » (148) et XCAN : confirmé 0** — aucune société allemande classée B seul
n'a XCAN comme unique venue B (vérifié au point 21).

**Avant / après, par pays, si la règle stricte (sans aucune exception documentée sauf
DOSE/MOSE/ONSE) est appliquée :**

| Pays | Avant (total/A/B) | Après (total/A/B) | Sorties d'univers |
|---|---|---|---|
| SE | 875 / 359 / 516 | 873 / 359 / 514 | 2 |
| PL | 726 / 389 / 337 | 726 / 389 / 337 | 0 |
| FR | 592 / 287 / 305 | 588 / 287 / 301 | 4 |
| DE | 470 / 322 / 148 | 464 / 322 / 142 | 6 |
| IT | 408 / 185 / 223 | 387 / 185 / 202 | 21 |
| **ES** | 330 / 119 / 211 | **279 / 119 / 160** | **51** |
| RO | 325 / 85 / 240 | 325 / 85 / 240 | 0 |
| **NL** | 157 / 110 / 47 | **122 / 110 / 12** | **35** |
| DK | 147 / 109 / 38 | 136 / 109 / 27 | 11 |
| CY | 147 / 76 / 71 | 137 / 76 / 61 | 10 |
| GR | 146 / 126 / 20 | 135 / 126 / 9 | 11 |
| BE | 122 / 101 / 21 | 115 / 101 / 14 | 7 |
| **IE** | 57 / 15 / 42 | **23 / 15 / 8** | **34 (60 %)** |
| LU | 57 / 39 / 18 | 43 / 39 / 4 | 14 |
| MT | 44 / 36 / 8 | 37 / 36 / 1 | 7 |
| *(autres pays : 0-3 sorties)* | | | |
| **Total** | **5700** | **5478** | **222 (3,9 %)** |

**Irlande est la plus touchée en proportion (−60 %)** — cohérent avec le fait que l'Irlande a
très peu de marché de croissance domestique propre (XESM = Euronext Growth Dublin, seulement
8/57) et que le reste de son « B » vient de bruit (DUSD notamment). **Cette règle n'est PAS
appliquée aux chiffres de ce document — c'est une proposition à valider avant tout changement
de code.**

## 23. Point 36 — Finlande, chiffre unique

**Incohérence confirmée et corrigée** : une seule requête, une seule règle (point 34 : A si ≥1
venue A). **Finlande : 184 sociétés au total, 137 en catégorie A (union XHEL/DHEL/MHEL), 47 en
catégorie B (aucune venue A — First North seul, union FSME/DNFI/MNFI = 45, +2 sur d'autres
venues B).** Le tableau de vraisemblance du tour précédent (136/48) et le tableau par segment
(137/45) étaient deux calculs légèrement différents (le premier ignorait la règle du point 34,
pas encore formulée à ce moment) — **137/47 est le chiffre qui fait foi désormais**, partout.

## 24. Point 37 — Agrégat Nasdaq (marché principal + First North), comparé à 675/444

| Ensemble | Univers (union des LEI touchant ≥1 de ces MIC) | Nasdaq (31/12/2025) | Écart |
|---|---|---|---|
| Marché principal (XSTO, DSTO, MSTO, XHEL, DHEL, MHEL, XCSE, DCSE, XICE, DICE, XTAL, XRIS, XLIT) | **669** | 675 | **−0,9 %** ✅ quasi exact |
| First North (SSME, DNSE, MNSE, MOSE, FSME, DNFI, MNFI, DSME, DNDK, FNIS, FNEE, FNLV, FNLT) | **570** | 444 | **+28,4 %** ⚠️ |

**Explication de l'écart First North (pas « non décomposable », comme demandé) :** le détail par
pays montre **153 des 570 sont des sociétés à préfixe NO** (Norvège), via les MIC DOSE/MOSE/ONSE
— l'extension transfrontalière « First North Sweden - Norway » (cf. §21). Ces sociétés
norvégiennes ont Oslo Børs (Euronext, pas Nasdaq) comme marché réglementé principal ; leur
présence dans mon décompte « First North » gonfle probablement le chiffre au-delà de ce que
Nasdaq compte lui-même dans ses « 444 » (qui, plus vraisemblablement, ne couvre que les sociétés
dont First North EST le marché de rattachement Nasdaq). **En retirant les 153 norvégiennes :
570 − 153 = 417, soit −6,1 % vs 444** — dans la tolérance, et une bien meilleure explication que
« non décomposable ». Le reste de l'écart (417 vs 444, encore −27) n'est pas expliqué avec
certitude dans cette session (différences de date d'arrêté, sociétés radiées en cours d'année,
autres extensions transfrontalières non identifiées) — signalé sans explication inventée.

**Détail par pays (First North, union) :** SE 306 · NO 153 · FI 47 · DK 33 · EE 12 · LV 5 · IS 3
· CY 4 · LT 2 · MT 2 · BE 1 · NL 1 · LU 1.
**Détail par pays (marché principal, union) :** SE 348 · FI 137 · DK 106 · IS 24 · LT 22 · EE 19
· LV 7 · MT 2 · LU 2 · DE 1 · PL 1 (ces 2 derniers : sociétés étrangères avec une venue Nasdaq
secondaire, cohérent avec un chevauchement mineur déjà observé ailleurs).

## 25. Fait / pas fait (points 34-39)

- **34 (catégorie principale A/B)** : fait — règle adoptée (A si ≥1 venue A), NO/BG/DE expliqués.
- **35 (cohérence pays venue/ISIN, règle proposée, avant/après)** : fait — table complète des
  venues B, XCAN détaillé, règle proposée (pas codée), avant/après par pays (222 sorties, −3,9 %
  au total, Irlande −60 %).
- **36 (Finlande, chiffre unique)** : fait — 137 A / 47 B, incohérence expliquée et corrigée.
- **37 (agrégat Nasdaq vs 675/444)** : fait — marché principal quasi exact (−0,9 %) ; First North
  expliqué (pas « non décomposable ») : 153/570 sont norvégiennes via l'extension transfrontalière
  documentée, écart résiduel −6,1 % après retrait, non totalement expliqué au-delà.
- **38 (réaffichage point 31)** : fait, ci-dessous dans la réponse de cette session.
- **39 (résultat point 30)** : fait — résultat au §26.

## 26. Point 30 — Complétude ESEF par pays (méthode LEI, ne dépend d'aucune page web)

Deuxième passage (le premier, par filtre `country`, était invalidé — voir §25 point 39 ci-dessus
et la découverte SAP/AT). Méthode : pour chaque société catégorie A (3 216 LEI), requête
`filings.xbrl.org` par `entity.identifier` (la méthode déjà fiable du point 25), présence d'au
moins un rapport avec `last_end_date` en 2024 ou 2025.

**Résultat global : 1 541 / 3 216 (47,9 %).**

| Pays | Sociétés A | Avec ESEF 2024/2025 | Taux |
|---|---|---|---|
| IS | 24 | 23 | **95,8 %** |
| FI | 137 | 127 | 92,7 % |
| AT | 58 | 52 | 89,7 % |
| DK | 109 | 97 | 89,0 % |
| NL | 110 | 95 | 86,4 % |
| NO | 152 | 130 | 85,5 % |
| SE | 359 | 304 | 84,7 % |
| ES | 119 | 104 | 87,4 % |
| IT | 185 | 153 | 82,7 % |
| LT | 23 | 19 | 82,6 % |
| MT | 36 | 26 | 72,2 % |
| IE | 15 | 11 | 73,3 % |
| LU | 39 | 31 | 79,5 % |
| BE | 101 | 70 | 69,3 % |
| FR | 287 | 197 | 68,6 % |
| SI | 18 | 10 | 55,6 % |
| SK | 12 | 5 | 41,7 % |
| HU | 47 | 18 | 38,3 % |
| GR | 126 | 34 | 27,0 % |
| HR | 69 | 18 | 26,1 % |
| PT | 30 | 6 | 20,0 % |
| EE | 22 | 3 | 13,6 % |
| PL | 389 | 5 | **1,3 %** |
| CY | 76 | 3 | **3,9 %** |
| **DE** | 322 | 0 | **0,0 %** |
| **BG** | 246 | 0 | **0,0 %** |
| **RO** | 85 | 0 | **0,0 %** |
| **CZ** | 12 | 0 | **0,0 %** |
| **LV** | 7 | 0 | **0,0 %** |
| **LI** | 1 | 0 | **0,0 %** |

**Vérifié — ce n'est pas un bug de mon code (contrôle direct)** : j'ai requêté individuellement
3 sociétés allemandes A connues et réelles (ProCredit Holding AG, BayWa AG, Bremer
Lagerhaus-Gesellschaft — LEI confirmés exacts auprès de GLEIF) : **0 rapport chacune sur
`filings.xbrl.org`**, en requête individuelle comme en lot. `filings.xbrl.org` a bien des
données allemandes (SAP y figure, 7 dépôts — mais étiquetés `country=AT`, cf. §25) : la
couverture y est donc réelle mais **très incomplète pour l'Allemagne**, et apparemment nulle
pour BG/RO/CZ/LV/LI sur l'échantillon testé. **Cohérent avec une information déjà présente dans
ce projet** : `pipeline/test_isins.yaml` note déjà SAP comme « Allemagne : repli yfinance »,
anticipant ce genre de trou de couverture ESEF pour ce pays — ce point 30 le confirme et
l'étend à 5 autres pays.

**Sens inverse (LEI avec ESEF 2024 dans un pays mais hors univers)** : **pas fait** — nécessite
une méthode fiable de rattachement pays↔LEI côté `filings.xbrl.org`, et le point 39 vient de
démontrer que le champ `country` de cette API ne peut pas servir à ça (il indique l'OAM, pas le
pays de la société). Une version fiable demanderait de croiser chaque LEI candidat avec son pays
GLEIF (`legalAddress.country`) plutôt que le champ `country` de `filings.xbrl.org` — pas fait
dans cette session, signalé comme tel plutôt que produit avec une méthode déjà démontrée
non fiable.

Données complètes : [`docs/completude_esef.json`](completude_esef.json).

`docs/univers.md`, `docs/journal_etape2.md` et `CLAUDE.md` mis à jour. Pas de commit. Aucune
strate figée, aucun tirage.

---

# ANNEXE — Mesures corrigées le 30/09, NE PAS UTILISER

Conservées uniquement pour la traçabilité de la correction (voir §1/§7 ci-dessus pour la cause exacte). Ces sections utilisaient `TechAttrbts/RlvntTradgVn` — un attribut de niveau ISIN, pas une venue par admission réelle — au lieu de `TradgVnRltdAttrbts/Id`. **Le détail par MIC (ancien §4) et les effectifs (ancien §5) sont faux ; ne pas les citer.** La numérotation ci-dessous (§1 à §8) est celle d'origine, conservée telle quelle.

## 1. Méthode et périmètre retenu (règle d'origine, §2-4 — voir §4bis pour la règle actuelle)

Univers = actions ordinaires (CFI commençant par `ES`, confirmé conforme à ISO 10962 : groupe
« Common/Ordinary shares ») **ET** ISIN dont le préfixe pays est dans la liste d'inclusion
UE/EEE (30 pays : UE-27 + Islande, Liechtenstein, Norvège) **ET** au moins un lieu de
négociation qui est lui-même dans un pays UE/EEE, de catégorie `RMKT` (marché réglementé) ou
`MLTF` (marché de croissance / MTF) au sens du registre ISO 10383, **ET** dont cette cotation
n'est pas terminée (`TermntnDt` absent sur cette venue).

**Non restreint aux 5 groupes de bourses** de methode.md, conformément à la décision — la
composition finale sera tranchée après mesure de la couverture. La table des MIC retenus
(§4) est celle **effectivement utilisée** pour produire les chiffres de ce document.

## 2. Chiffres (règle d'origine RMKT/MLTF — non affectés par le bug de comptage du §4)

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

Ces compteurs par ISIN/LEI (membership) ne sont **pas** affectés par le bug de comptage du §4 :
ils comptent des clés de dictionnaire (un ISIN ou un LEI), pas des occurrences de ligne par MIC.
Seul le détail par MIC du §4 était faux.

### Répartition par pays (préfixe ISIN, 30 pays, règle d'origine)

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

*(Le cross-check GLEIF par échantillon de 50 LEI, fait à cette étape, est remplacé par la
vérification complète des 6 169 LEI au §6 — le cas Technomeca/Tecnoquark y est repris et
requalifié.)*

## 4. Table des MIC retenus, règle d'origine (134 MIC — comptage par MIC ERRONÉ, voir avertissement)

`RMKT` = marché réglementé · `MLTF` = marché de croissance / MTF, au sens du registre ISO 10383.

**⚠️ Avertissement (signalé le 30/09, corrigé au §5) : la colonne « N ISIN » ci-dessous compte
des occurrences de lignes FIRDS par (ISIN, MIC), pas des ISIN distincts.** Un même couple
(ISIN, MIC) peut apparaître plusieurs dizaines de fois dans les fichiers FIRDS bruts
(republications successives sans déduplication — vérifié : 4 431 des 6 335 ISIN de l'univers
ont au moins un MIC dupliqué dans leur propre liste de venues, jusqu'à 39 fois pour un seul
couple ISIN×MIC). C'est ce qui produisait des valeurs impossibles comme XPAR = 9 941, supérieures
au nombre total de l'univers (6 335 ISIN). Tableau **conservé tel quel pour la traçabilité de
l'erreur** ; ne pas l'utiliser pour un effectif. Table corrigée (ISIN et sociétés distincts,
univers final A/B) : §5.3.

| MIC | Pays | Type | Marché | « N ISIN » (occurrences de lignes, PAS un effectif) |
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

## 4bis. Point 9 — Classification A / B / C des 134 MIC (règle actuelle)

**Règle d'univers (remplace RMKT/MLTF ci-dessus) :** une société entre dans l'univers si elle a
**au moins une venue non terminée de catégorie A ou B**. Les venues C restent affichées en
information sur la fiche entreprise (elles ne comptent plus pour l'admission).

- **A = marché réglementé primaire.** Tout segment « marché réglementé » (catégorie ISO `RMKT`
  la plupart du temps, y compris les bourses régionales — allemandes, espagnoles — qui sont
  chacune leur propre marché réglementé, pas de fusion arbitraire avec le marché « principal »
  du pays).
- **B = marché de croissance opéré par une place, avec accord de l'émetteur** (First North,
  Euronext Growth/Access, BME Growth/ScaleUp, NewConnect, Scale, etc.), **quel que soit son code
  ISO d'origine** — ex. Euronext Expand Oslo et l'Alternative Market bulgare (ABUL) sont codés
  `RMKT` au registre mais reclassés B sur la fonction réelle (confirmé par recherche externe :
  ABUL accueille les sociétés petites/peu liquides comme un palier de croissance ;
  Bucharest CAN-ATS confirmé « système pour sociétés nouvelles / non éligibles au marché
  réglementé », fonctionnellement un marché de croissance malgré un code registre distinct de
  RMKT/MLTF).
- **C = autre** : Freiverkehr régionaux, plateformes dark/midpoint, réseaux de courtiers,
  enchères, hors carnet, après-séance, segments de fonds. **Application explicite de la
  consigne** : XEMA (Xetra Midpoint) et DMAD (Bolsa de Madrid Dark Midpoint) sont codés `RMKT`
  au registre ISO mais classés **C** ici — même traitement étendu par cohérence à tous les
  segments « midpoint »/« auction on demand » du même type trouvés dans la liste (DSTO, DHEL,
  DCSE, DICE, DNSE, DNDK, DNFI, MSTO, MHEL, MNSE, MNFI, MOSE, XEMB).

Table complète (134 MIC, triée A puis B puis C, pays, marché, catégorie, raison) :

| MIC | Pays | Marché | Catégorie | Raison |
|---|---|---|---|---|
| WBAH | AT | WIENER BOERSE AG AMTLICHER HANDEL (OFFICIAL MARKET) | A | Wiener Börse Amtlicher Handel (Official Market) — réglementé |
| XBRU | BE | EURONEXT - EURONEXT BRUSSELS | A | Euronext Brussels — marché réglementé primaire |
| ZBUL | BG | BULGARIAN STOCK EXCHANGE - MAIN MARKET | A | Bulgarian SE Main Market — marché réglementé primaire |
| XCYS | CY | CYPRUS STOCK EXCHANGE | A | Cyprus Stock Exchange — marché réglementé primaire |
| XPRA | CZ | PRAGUE STOCK EXCHANGE | A | Prague Stock Exchange — marché réglementé primaire |
| XRMZ | CZ | RM-SYSTEM CZECH STOCK EXCHANGE | A | RM-SYSTEM Czech Stock Exchange — marché réglementé primaire (bourse distincte de Prague) |
| DUSA | DE | BOERSE DUESSELDORF - REGULIERTER MARKT | A | Börse Düsseldorf — Regulierter Markt (réglementé régional) |
| DUSC | DE | BOERSE DUESSELDORF - QUOTRIX - REGULIERTER MARKT | A | Börse Düsseldorf — Quotrix — Regulierter Markt (réglementé) |
| EQTB | DE | BOERSE BERLIN EQUIDUCT TRADING - BERLIN SECOND REGUL... | A | Berlin Equiduct — Berlin Second Regulated Market ; réglementé (palier allégé, cas limite noté) |
| FRAA | DE | BOERSE FRANKFURT - REGULIERTER MARKT | A | Bourse de Francfort — Regulierter Markt (réglementé) |
| HAMA | DE | BOERSE HAMBURG - REGULIERTER MARKT | A | Börse Hamburg — Regulierter Markt (réglementé régional) |
| HANA | DE | BOERSE HANNOVER - REGULIERTER MARKT | A | Börse Hannover — Regulierter Markt (réglementé régional) |
| MUNA | DE | BOERSE MUENCHEN - REGULIERTER MARKT | A | Börse München — Regulierter Markt (réglementé régional) |
| STUA | DE | BOERSE STUTTGART - REGULIERTER MARKT | A | Börse Stuttgart — Regulierter Markt (réglementé régional) |
| XETA | DE | XETRA - REGULIERTER MARKT | A | Xetra — Regulierter Markt (réglementé) |
| XGRM | DE | TRADEGATE BERLIN STOCK EXCHANGE - REGULIERTER MARKT | A | Tradegate Berlin — Regulierter Markt (réglementé) |
| XCSE | DK | NASDAQ COPENHAGEN A/S | A | Nasdaq Copenhagen — carnet continu principal (réglementé) |
| XTAL | EE | NASDAQ TALLINN AS | A | Nasdaq Tallinn — marché réglementé primaire |
| XBAR | ES | BOLSA DE BARCELONA | A | Bolsa de Barcelona — marché réglementé (bourse régionale espagnole, groupe BME) |
| XBIL | ES | BOLSA DE VALORES DE BILBAO | A | Bolsa de Bilbao — marché réglementé (bourse régionale espagnole, groupe BME) |
| XMAD | ES | BOLSA DE MADRID | A | Bolsa de Madrid — marché réglementé primaire |
| XHEL | FI | NASDAQ HELSINKI LTD | A | Nasdaq Helsinki — carnet continu principal (réglementé) |
| XPAR | FR | EURONEXT - EURONEXT PARIS | A | Euronext Paris — marché réglementé primaire |
| XATH | GR | ATHENS EXCHANGE S.A. CASH MARKET | A | Athens Exchange Cash Market — marché réglementé primaire |
| XZAG | HR | ZAGREB STOCK EXCHANGE | A | Zagreb Stock Exchange — marché réglementé primaire |
| XBUD | HU | BUDAPEST STOCK EXCHANGE | A | Budapest Stock Exchange — marché réglementé primaire |
| XMSM | IE | EURONEXT DUBLIN | A | Euronext Dublin — marché réglementé primaire |
| XICE | IS | NASDAQ ICELAND HF. | A | Nasdaq Iceland — carnet continu principal (réglementé) |
| MTAA | IT | EURONEXT MILAN | A | Euronext Milan — marché réglementé primaire |
| XLIT | LT | AB NASDAQ VILNIUS | A | Nasdaq Vilnius — marché réglementé primaire |
| XLUX | LU | LUXEMBOURG STOCK EXCHANGE | A | Luxembourg Stock Exchange — marché réglementé primaire |
| XRIS | LV | NASDAQ RIGA AS | A | Nasdaq Riga — marché réglementé primaire |
| XMAL | MT | MALTA STOCK EXCHANGE | A | Malta Stock Exchange — marché réglementé primaire |
| XAMS | NL | EURONEXT - EURONEXT AMSTERDAM | A | Euronext Amsterdam — marché réglementé primaire |
| XOSL | NO | OSLO BORS | A | Euronext Oslo (Oslo Børs) — marché réglementé primaire |
| XWAR | PL | WARSAW STOCK EXCHANGE/EQUITIES/MAIN MARKET | A | Warsaw Stock Exchange Main Market — marché réglementé primaire |
| XLIS | PT | EURONEXT - EURONEXT LISBON | A | Euronext Lisbon — marché réglementé primaire |
| XBSE | RO | SPOT REGULATED MARKET - BVB | A | Bucharest Stock Exchange — Spot Regulated Market — marché réglementé primaire |
| XNGM | SE | NORDIC GROWTH MARKET | A | Nordic Growth Market (NGM) — marché réglementé à part entière malgré son nom (distinct de son propre segment MTF « Nordic SME » = NSME, classé B) |
| XSTO | SE | NASDAQ STOCKHOLM AB | A | Nasdaq Stockholm — carnet continu principal (réglementé) |
| XLJU | SI | LJUBLJANA STOCK EXCHANGE (OFFICIAL MARKET) | A | Ljubljana Stock Exchange (Official Market) — marché réglementé primaire |
| XBRA | SK | BRATISLAVA STOCK EXCHANGE | A | Bratislava Stock Exchange — marché réglementé primaire |
| WBDP | AT | WIENER BOERSE AG DIRECT MARKET PLUS | B | Wiener Börse — Direct Market Plus : segment allégé avec obligations d'émetteur (équivalent marché de croissance) |
| ALXB | BE | EURONEXT GROWTH BRUSSELS | B | Euronext Growth Brussels |
| MLXB | BE | EURONEXT ACCESS BRUSSELS | B | Euronext Access Brussels (Access inclus dans B par la consigne) |
| ABUL | BG | BULGARIAN STOCK EXCHANGE - ALTERNATIVE MARKET | B | Bulgarian SE Alternative Market : accueille les sociétés petites/peu liquides, fonction de marché de croissance malgré un statut formel « réglementé » — iotafinance/sseinitiative (consultés 30/09/2026) ; codé RMKT au registre ISO mais reclassé selon la fonction, pas le code |
| GBUL | BG | BULGARIAN STOCK EXCHANGE - SME GROWTH MARKET BEAM | B | Bulgarian SE — SME Growth Market BEAM (nommément un marché de croissance SME) |
| FRAS | DE | BOERSE FRANKFURT - SCALE | B | Börse Frankfurt — Scale (même segment de croissance que XETS) |
| XETS | DE | XETRA - SCALE | B | Xetra Scale — segment de croissance SME (nommément cité par la consigne) |
| DSME | DK | FIRST NORTH DENMARK -SME GROWTH MARKET | B | First North Denmark — SME Growth Market |
| FNEE | EE | FIRST NORTH ESTONIA | B | First North Estonia |
| GROW | ES | BME GROWTH MARKET | B | BME Growth Market (nommément cité par la consigne) |
| SCLE | ES | BME SCALEUP | B | BME ScaleUp : marché de croissance en phase de développement (même famille que BME Growth) |
| FSME | FI | FIRST NORTH FINLAND - SME GROWTH MARKET | B | First North Finland — SME Growth Market |
| ALXP | FR | EURONEXT GROWTH PARIS | B | Euronext Growth Paris |
| XMLI | FR | EURONEXT ACCESS PARIS | B | Euronext Access Paris (Access inclus dans B par la consigne) |
| ENAX | GR | ATHENS EXCHANGE ALTERNATIVE MARKET | B | Athens Exchange Alternative Market (ENA) : marché de croissance SME avec accord de l'émetteur |
| XZAP | HR | PROGRESS MARKET | B | Zagreb SE — Progress Market : marché de croissance SME |
| XTND | HU | BUDAPEST STOCK EXCHANGE - XTEND | B | Budapest SE — Xtend (marché de croissance SME, structure Euronext-like) |
| XACD | IE | EURONEXT ACCESS DUBLIN | B | Euronext Access Dublin (Access inclus dans B par la consigne) |
| XESM | IE | EURONEXT GROWTH DUBLIN | B | Euronext Growth Dublin |
| FNIS | IS | FIRST NORTH ICELAND | B | First North Iceland |
| EXGM | IT | EURONEXT GROWTH MILAN | B | Euronext Growth Milan |
| FNLT | LT | FIRST NORTH LITHUANIA | B | First North Lithuania |
| FNLV | LV | FIRST NORTH LATVIA | B | First North Latvia |
| PROS | MT | PROSPECTS | B | Malta SE — Prospects : marché de croissance SME |
| NPEX | NL | NPEX | B | NPEX : plateforme de financement SME néerlandaise avec accord de l'émetteur |
| MERK | NO | EURONEXT GROWTH - OSLO | B | Euronext Growth Oslo |
| XOAS | NO | EURONEXT EXPAND OSLO | B | Euronext Expand Oslo — palier de croissance Oslo (équivalent Euronext Growth), malgré le code ISO RMKT |
| XNCO | PL | WARSAW STOCK EXCHANGE/ EQUITIES/NEW CONNECT - MTF | B | Warsaw SE — NewConnect (MTF de croissance, nommément cité par la consigne) |
| ALXL | PT | EURONEXT GROWTH LISBON | B | Euronext Growth Lisbon |
| ENXL | PT | EURONEXT ACCESS LISBON | B | Euronext Access Lisbon (Access inclus dans B par la consigne) |
| XCAN | RO | CAN - ATS | B | Bucharest SE — CAN-ATS : système multilatéral pour sociétés nouvelles/non éligibles au marché réglementé — fonction de marché de croissance confirmée (tradinghours.com/iotafinance, consultés 30/09/2026), malgré un code registre distinct de RMKT/MLTF |
| NSME | SE | NORDIC SME | B | Nordic SME — segment MTF de croissance de Nordic Growth Market |
| SPDK | SE | SPOTLIGHT STOCK MARKET DENMARK | B | Spotlight Stock Market Denmark (extension du marché de croissance Spotlight) |
| SPNO | SE | SPOTLIGHT STOCK MARKET NORWAY | B | Spotlight Stock Market Norway (extension du marché de croissance Spotlight) |
| SSME | SE | FIRST NORTH SWEDEN - SME GROWTH MARKET | B | First North Sweden — SME Growth Market |
| XSAT | SE | SPOTLIGHT STOCK MARKET AB | B | Spotlight Stock Market — marché de croissance SME suédois (accord de l'émetteur) |
| XLJM | SI | SI ENTER | B | Ljubljana SE — SI ENTER : marché de croissance SME |
| WBDM | AT | WIENER BOERSE AG VIENNA MTF (VIENNA MTF) | C | Wiener Börse Vienna MTF : MTF générique, pas de marque de marché de croissance confirmée |
| VPXB | BE | EURONEXT - VENTES PUBLIQUES BRUSSELS | C | Euronext — Ventes Publiques Brussels : enchères publiques |
| JBUL | BG | BULGARIAN STOCK EXCHANGE - INTERNATIONAL MTF | C | Bulgarian SE — International MTF : MTF générique |
| MBUL | BG | MTF SOFIA | C | MTF Sofia : MTF générique, pas de marque de marché de croissance confirmée |
| XECM | CY | MTF - CYPRUS EXCHANGE | C | MTF - Cyprus Exchange : MTF générique, pas de marque de marché de croissance identifiée |
| XPRM | CZ | PRAGUE STOCK EXCHANGE - MTF | C | Prague SE — MTF : segment générique, pas de marque de marché de croissance confirmée |
| XRMO | CZ | RM-SYSTEM CZECH STOCK EXCHANGE - MTF | C | RM-SYSTEM Czech SE — MTF : segment générique de la bourse RM-SYSTEM |
| DUSB | DE | BOERSE DUESSELDORF - FREIVERKEHR | C | Börse Düsseldorf — Freiverkehr |
| DUSD | DE | BOERSE DUESSELDORF - QUOTRIX MTF | C | Börse Düsseldorf — Quotrix MTF : plateforme de négociation retail générique |
| ERFQ | DE | BLOCKMATCH EUROPE SELECT | C | BlockMatch Europe Select : plateforme dark/block-trading |
| FRAB | DE | BOERSE FRANKFURT - FREIVERKEHR | C | Börse Frankfurt — Freiverkehr |
| FRAV | DE | BOERSE FRANKFURT - FREIVERKEHR - OFF-BOOK | C | Börse Frankfurt — Freiverkehr — Off-Book |
| HAMB | DE | BOERSE HAMBURG - FREIVERKEHR | C | Börse Hamburg — Freiverkehr |
| HAMN | DE | BOERSE HAMBURG - LANG AND SCHWARZ EXCHANGE - FREIVER... | C | Börse Hamburg — Lang & Schwarz Exchange — Freiverkehr |
| HANB | DE | BOERSE HANNOVER - FREIVERKEHR | C | Börse Hannover — Freiverkehr |
| HAND | DE | BOERSE HANNOVER - FREIVERKEHR - EUROPEAN INVESTOR EX... | C | Börse Hannover — Freiverkehr — European Investor Exchange |
| MUNB | DE | BOERSE MUENCHEN - FREIVERKEHR | C | Börse München — Freiverkehr |
| MUND | DE | BOERSE MUENCHEN - GETTEX - FREIVERKEHR | C | Börse München — Gettex — Freiverkehr |
| STUB | DE | BOERSE STUTTGART - FREIVERKEHR | C | Börse Stuttgart — Freiverkehr |
| STUD | DE | BOERSE STUTTGART - FREIVERKEHR - TECHNICAL PLATFORM 2 | C | Börse Stuttgart — Freiverkehr — Technical Platform 2 |
| XEMA | DE | XETRA MIDPOINT REGULATED MARKET | C | Xetra Midpoint — segment dark/midpoint ; codé RMKT au registre mais explicitement signalé C par la consigne du 30/09 |
| XEMB | DE | XETRA MIDPOINT OPEN MARKET | C | Xetra Midpoint Open Market : segment midpoint (même famille que XEMA) |
| XETB | DE | XETRA - FREIVERKEHR | C | Xetra — Freiverkehr |
| XETU | DE | XETRA - REGULIERTERMARKT - OFF-BOOK | C | Xetra Regulierter Markt — Off-Book : négociation hors carnet |
| XGAT | DE | TRADEGATE BERLIN STOCK EXCHANGE - FREIVERKEHR | C | Tradegate Berlin — Freiverkehr |
| DCSE | DK | NASDAQ COPENHAGEN A/S - NORDIC@MID | C | Nasdaq Copenhagen — Nordic@Mid : segment midpoint (même famille que DSTO/DHEL/DICE) |
| DNDK | DK | FIRST NORTH DENMARK - NORDIC@MID | C | First North Denmark — Nordic@Mid : segment midpoint |
| DMAD | ES | BOLSA DE MADRID - DARK MIDPOINT | C | Bolsa de Madrid — Dark Midpoint ; codé RMKT mais explicitement signalé C par la consigne du 30/09 |
| MABX | ES | BME MTF EQUITY (IIC AND ECR SEGMENTS) | C | BME MTF Equity (segments IIC et ECR) : segments de fonds (véhicules de placement collectif / capital-risque), pas des actions de sociétés opérationnelles |
| POSE | ES | PORTFOLIO STOCK EXCHANGE | C | Portfolio Stock Exchange : plateforme alternative, fonction non confirmée comme marché de croissance |
| DHEL | FI | NASDAQ HELSINKI LTD - NORDIC@MID | C | Nasdaq Helsinki — Nordic@Mid : segment midpoint |
| DNFI | FI | FIRST NORTH FINLAND - NORDIC@MID | C | First North Finland — Nordic@Mid : segment midpoint |
| MHEL | FI | NASDAQ HELSINKI LTD -  AUCTION ON DEMAND | C | Nasdaq Helsinki — Auction on Demand : mécanisme d'enchère |
| MNFI | FI | FIRST NORTH FINLAND - AUCTION ON DEMAND | C | First North Finland — Auction on Demand : mécanisme d'enchère |
| AQEU | FR | AQUIS EXCHANGE EUROPE | C | Aquis Exchange Europe : plateforme MTF générique pan-européenne |
| LNEQ | FR | TP ICAP EU - MTF - LIQUIDNET EU EQUITY | C | TP ICAP EU — Liquidnet EU Equity : réseau de courtiers (block trading institutionnel) |
| SGMU | FR | SIGMA X EUROPE NON-DISPLAYED BOOK | C | Sigma X Europe Non-Displayed Book : plateforme dark |
| TPIR | FR | TP ICAP EU - MTF - REGISTRATION | C | TP ICAP EU — MTF Registration : réseau de courtiers |
| XPOS | IE | POSIT DARK | C | Posit Dark — plateforme dark |
| DICE | IS | NASDAQ ICELAND HF. - NORDIC@MID | C | Nasdaq Iceland — Nordic@Mid : segment midpoint, même famille que XEMA/DMAD |
| BGEM | IT | BORSA ITALIANA GLOBAL EQUITY MARKET | C | Borsa Italiana Global Equity Market : plateforme de cotation de titres étrangers, pas un marché de croissance |
| MTAH | IT | BORSA ITALIANA - TRADING AFTER HOURS | C | Borsa Italiana — Trading After Hours : séance après clôture |
| ARTX | LI | ARTEX GLOBAL MARKETS AG | C | Artex Global Markets — plateforme de titres tokenisés, hors typologie growth-market |
| EMTF | LU | EURO MTF | C | Euro MTF (Luxembourg) : MTF générique, usage principalement obligataire |
| TQEA | NL | TURQUOISE EUROPE - PERIODIC AUCTIONS ORDER BOOK | C | Turquoise Europe — Periodic Auctions Order Book : plateforme générique pan-européenne |
| TQEM | NL | TURQUOISE EUROPE - DARK | C | Turquoise Europe — Dark : plateforme dark |
| TQEX | NL | TURQUOISE EUROPE - LIT ORDER BOOK | C | Turquoise Europe — Lit Order Book : plateforme générique pan-européenne |
| TWEM | NL | TRADEWEB EU BV - MTF | C | Tradeweb EU — MTF : plateforme institutionnelle générique |
| XNXD | NL | NXCHANGE B.V. MTF | C | Nxchange B.V. MTF : plateforme alternative, fonction de marché de croissance non confirmée |
| DNSE | SE | FIRST NORTH SWEDEN - NORDIC@MID | C | First North Sweden — Nordic@Mid : segment midpoint |
| DSTO | SE | NASDAQ STOCKHOLM AB - NORDIC@MID | C | Nasdaq Stockholm — Nordic@Mid : segment midpoint (même famille que DCSE/DHEL/DICE) |
| MNSE | SE | FIRST NORTH SWEDEN - AUCTION ON DEMAND | C | First North Sweden — Auction on Demand : mécanisme d'enchère |
| MOSE | SE | FIRST NORTH SWEDEN - NORWAY AUCTION ON DEMAND | C | First North Sweden — Norway Auction on Demand : mécanisme d'enchère |
| MSTO | SE | NASDAQ STOCKHOLM AB - AUCTION ON DEMAND | C | Nasdaq Stockholm — Auction on Demand : mécanisme d'enchère, pas un marché de cotation |
| EBRA | SK | BRATISLAVA STOCK EXCHANGE - MTF | C | Bratislava SE — MTF : segment générique, pas de marque de marché de croissance confirmée |

## 5. Point 10 — Effectifs recalculés (règle A/B, unité = société/LEI)

**Univers final (règle A/B) :** parmi les 6 335 ISIN de l'ancienne règle (§2), ceux qui n'avaient
qu'une ou plusieurs venues C et aucune A/B sont exclus.

| Mesure | Valeur |
|---|---|
| ISIN retenus (≥1 venue A ou B, ancienne base 6 335) | **4 617** |
| ISIN exclus (venues C uniquement) | 1 718 |
| **Sociétés (LEI) retenues** | **4 564** |
| dont A seul | 2 648 |
| dont B seul | 1 915 |
| dont A **et** B (au moins une venue de chaque) | 1 |

### 5.1 Par pays (sociétés/LEI, pays = majorité des ISIN de la société)

| Pays | Total sociétés | A seul | B seul | A+B |
|---|---|---|---|---|
| PL | 726 | 389 | 337 | 0 |
| FR | 551 | 288 | 263 | 0 |
| IT | 395 | 185 | 210 | 0 |
| SE | 352 | 117 | 235 | 0 |
| DE | 331 | 322 | 9 | 0 |
| ES | 325 | 114 | 211 | 0 |
| RO | 325 | 85 | 240 | 0 |
| BG | 263 | 83 | 180 | 0 |
| NO | 212 | 145 | 67 | 0 |
| GR | 137 | 126 | 11 | 0 |
| NL | 131 | 110 | 21 | 0 |
| BE | 121 | 101 | 20 | 0 |
| DK | 106 | 94 | 12 | 0 |
| CY | 85 | 76 | 9 | 0 |
| HR | 72 | 69 | 3 | 0 |
| HU | 66 | 46 | 19 | 1 |
| AT | 65 | 58 | 7 | 0 |
| PT | 47 | 30 | 17 | 0 |
| LU | 39 | 38 | 1 | 0 |
| FI | 38 | 26 | 12 | 0 |
| MT | 38 | 34 | 4 | 0 |
| EE | 32 | 22 | 10 | 0 |
| LT | 25 | 23 | 2 | 0 |
| SI | 20 | 18 | 2 | 0 |
| IE | 20 | 15 | 5 | 0 |
| CZ | 12 | 12 | 0 | 0 |
| LV | 12 | 7 | 5 | 0 |
| SK | 12 | 12 | 0 | 0 |
| IS | 5 | 2 | 3 | 0 |
| LI | 1 | 1 | 0 | 0 |
| **Total** | **4564** | **2648** | **1915** | **1** |

### 5.2 PL / RO / BG / CY / GR — vérification de la représentation demandée

Ces 5 pays nommément cités sont bien présents en nombre dans les deux catégories : **PL**
389 A / 337 B, **RO** 85 A / 240 B, **BG** 83 A / 180 B, **CY** 76 A / 9 B, **GR** 126 A / 11 B.
CY et GR ont un effectif B modeste (9 et 11, sous le seuil de 40) : ils sont regroupés en strate
« Méditerranée (B) » avec Malte au §7, pas exclus.

### 5.3 Table par MIC — univers final A/B, effectifs corrigés (ISIN et sociétés DISTINCTS)

Correction du bug signalé au §4 : comptage par ISIN distinct (`set()` par société, pas par ligne
FIRDS). XPAR passe de « 9 941 » (faux) à 296 ISIN / 295 sociétés — cohérent avec le total de
l'univers (4 617 ISIN / 4 564 sociétés). Seuls les MIC classés A ou B apparaissent (les MIC C ne
comptent plus pour l'admission, cf. §4bis) :

| MIC | Catégorie | N ISIN distincts | N sociétés (LEI) |
|---|---|---|---|
| XWAR | A | 417 | 409 |
| XNCO | B | 338 | 338 |
| XPAR | A | 296 | 295 |
| XCAN | B | 242 | 242 |
| FRAA | A | 215 | 211 |
| ALXP | B | 204 | 204 |
| EXGM | B | 204 | 204 |
| MTAA | A | 198 | 196 |
| ABUL | B | 163 | 163 |
| XOSL | A | 157 | 154 |
| XATH | A | 131 | 131 |
| XSAT | B | 129 | 127 |
| XMLI | B | 129 | 128 |
| XSTO | A | 111 | 106 |
| GROW | B | 111 | 110 |
| XMAD | A | 111 | 111 |
| XETA | A | 109 | 109 |
| XBRU | A | 100 | 99 |
| XCSE | A | 96 | 93 |
| XBSE | A | 88 | 88 |
| XAMS | A | 88 | 86 |
| NSME | B | 87 | 87 |
| ZBUL | A | 82 | 82 |
| XCYS | A | 70 | 67 |
| XZAG | A | 69 | 69 |
| MERK | B | 69 | 69 |
| WBAH | A | 56 | 56 |
| SCLE | B | 52 | 52 |
| XBUD | A | 48 | 47 |
| XMAL | A | 34 | 34 |
| XLIS | A | 31 | 31 |
| XHEL | A | 25 | 25 |
| SSME | B | 22 | 21 |
| XLIT | A | 22 | 22 |
| XTND | B | 21 | 21 |
| XTAL | A | 19 | 19 |
| XLJU | A | 17 | 17 |
| GBUL | B | 17 | 17 |
| ENXL | B | 15 | 15 |
| XBRA | A | 15 | 11 |
| XMSM | A | 14 | 14 |
| XPRA | A | 13 | 13 |
| ENAX | B | 13 | 13 |
| NPEX | B | 12 | 12 |
| DUSA | A | 12 | 12 |
| FSME | B | 12 | 12 |
| FNEE | B | 10 | 10 |
| WBDP | B | 8 | 8 |
| XOAS | B | 8 | 8 |
| MLXB | B | 8 | 8 |
| XNGM | A | 8 | 7 |
| XETS | B | 7 | 7 |
| MUNA | A | 7 | 7 |
| XRIS | A | 7 | 7 |
| STUA | A | 6 | 6 |
| ALXB | B | 6 | 6 |
| FNLV | B | 5 | 5 |
| SPDK | B | 5 | 5 |
| XLUX | A | 5 | 5 |
| HAMA | A | 4 | 4 |
| EQTB | A | 4 | 4 |
| DSME | B | 4 | 4 |
| XESM | B | 4 | 4 |
| FNIS | B | 3 | 3 |
| XGRM | A | 3 | 3 |
| FRAS | B | 3 | 3 |
| XZAP | B | 3 | 3 |
| HANA | A | 2 | 2 |
| FNLT | B | 2 | 2 |
| XLJM | B | 2 | 2 |
| XRMZ | A | 1 | 1 |
| DUSC | A | 1 | 1 |
| XBIL | A | 1 | 1 |
| XBAR | A | 1 | 1 |
| XACD | B | 1 | 1 |
| XICE | A | 1 | 1 |
| PROS | B | 1 | 1 |
| SPNO | B | 1 | 1 |
| ALXL | B | 1 | 1 |

## 6. Point 11 — Vérification LEI complète (GLEIF, 6 169 LEI, sans échantillonnage)

**Méthode :** 124 lots de 50 LEI (`filter[lei]=...`, endpoint `api.gleif.org/api/v1/lei-records`),
pause 0,3 s entre lots — 6 169/6 169 trouvés (0 introuvable), ~110 s d'exécution. Comparaison :
nom FIRDS (`FullNm`) vs le meilleur score parmi le nom légal GLEIF **et** ses `otherNames`/
`transliteratedOtherNames` (GLEIF fournit une translittération ASCII pour les noms en alphabet
non latin — l'utiliser était nécessaire : une première passe sans cette translittération
donnait un taux de similarité ~0 systématique pour toutes les sociétés bulgares/grecques en
alphabet cyrillique/grec, un artefact de l'outil de comparaison, pas une vraie divergence).
Score = max(ratio caractère-à-caractère, taux de recouvrement des jetons après normalisation —
formes juridiques et descripteurs de valeur mobilière retirés : SA/AG/PLC/AB(publ)/Inhaber-
Aktien o.N./Ordinary Shares/etc.). Comparaison du pays ISIN au pays `legalAddress` GLEIF.
Détection d'un « sigle probable » (les initiales du nom FIRDS court correspondent aux mots du
nom légal GLEIF, ex. PZU → *Powszechny Zakład Ubezpieczeń*) pour ne pas classer ces cas en
divergence.

| Mesure | Valeur |
|---|---|
| LEI vérifiés | 6 169 / 6 169 (100 %) |
| Non comparable (aucun nom en alphabet latin chez GLEIF) | 13 (0,2 % — 12 BG, 1 CY) |
| Similarité = 1,0 (identique après normalisation) | 5 056 / 6 156 comparables (82,1 %) |
| Sigle probable (initiales ≠ nom mais cohérentes) | 20 |
| Pays ISIN ≠ pays GLEIF (`legalAddress`) | 54 |
| Statut GLEIF ≠ ACTIVE | 31 (tous `INACTIVE`) |
| **File de revue manuelle totale** (similarité < 0,7 hors sigles, OU pays incohérent, OU statut non actif, OU non comparable) | **713 / 6 169 (11,6 %)** |

**Aucune exclusion automatique** : ces 713 LEI restent dans l'univers, simplement marqués pour
revue manuelle. Liste complète : [`docs/revue_lei_gleif.csv`](revue_lei_gleif.csv) (colonnes
lei, nom_firds, nom_gleif, similarité, pays_isin, pays_gleif, motif), triée par similarité
croissante.

**Cas Technomeca, résolu comme demandé :** LEI `959800JG44HG76EPWH68` — FIRDS = « TECHNOMECA
AEROSPACE, S.A. », GLEIF = « TECNOQUARK TRUST S.A. », similarité 0,5 → dans la file de revue.
Classé **« changement de dénomination sociale probable »** (avis BME Growth du 16/09/2020,
Tecnoquark Trust → Technomeca Aerospace), pas une erreur de LEI. **Non exclu de l'univers.**

**Autres cas illustratifs de la file (non résolus, à revoir individuellement) :** plusieurs
suivent le même patron que Technomeca (nom FIRDS et nom GLEIF sans rapport apparent, même pays,
LEI actif) — candidats plausibles à un changement de nom, sans confirmation externe dans cette
session : `KEYRUS` (FR) / GLEIF « GOLDMAN SACHS PARIS INC ET CIE » ; `Space Nord Invest AB` (SE) /
GLEIF « Hifab Group AB » ; `ERWE Immobilien AG` (DE) / GLEIF « KSLK Trust GmbH » ; `Voim ASA`
(NO) / GLEIF « ELECTROMAGNETIC GEOSERVICES ASA » ; `WATERA` (FR) / GLEIF « Mascara Nouvelles
Technologies » ; `CIBIX` (BE) / GLEIF « BEFIMMO ». **Aucun n'est classé « mauvais LEI » sur la
seule base de cette différence de nom** — tous en revue manuelle, aucun exclu.

## 7. Point 12 — Stratification proposée du pilote (PROPOSITION, PILOTE NON LANCÉ)

**Règle** : strate = (pays, ou groupe documenté si < 40 sociétés dans cette catégorie) × (A seul
/ a au moins une venue B — la société A-et-B unique du §5 est comptée côté B). 37 strates au
total (22 sur l'axe A, 15 sur l'axe B). Chaque pays < 40 dans une catégorie est regroupé avec des
pays de la même zone géographique/institutionnelle (regroupement documenté ci-dessous, motif =
proximité géographique, jamais un critère de score). PL, RO, BG restent des strates autonomes
(déjà ≥ 40 dans les deux catégories) ; CY et GR ne sont regroupés que côté B (9 et 11 < 40),
leur strate A est autonome.

**Allocation proposée** (à valider, **pilote non lancé**) : plancher 5 sociétés/strate (37 × 5 =
185), reste réparti au prorata de la population de chaque strate, cible totale 350 = 340 tirées
dans les strates + 10 témoins étape 1 (dans la fourchette 300-400 demandée) :

| Strate | Axe | Pays regroupés | Population | Échantillon proposé |
|---|---|---|---|---|
| PL | A | PL | 389 | 18 |
| DE | A | DE | 322 | 16 |
| FR | A | FR | 288 | 15 |
| IT | A | IT | 185 | 11 |
| NO | A | NO | 145 | 10 |
| GR | A | GR | 126 | 9 |
| SE | A | SE | 117 | 9 |
| ES | A | ES | 114 | 9 |
| NL | A | NL | 110 | 9 |
| BE | A | BE | 101 | 8 |
| DK | A | DK | 94 | 8 |
| RO | A | RO | 85 | 8 |
| BG | A | BG | 83 | 8 |
| CY | A | CY | 76 | 8 |
| Micro-États (A) | A | MT,LU,LI | 73 | 7 |
| HR | A | HR | 69 | 7 |
| AT | A | AT | 58 | 7 |
| Baltique (A) | A | EE,LV,LT | 52 | 7 |
| HU | A | HU | 46 | 7 |
| Péninsule ibérique & Irlande (A) | A | PT,IE | 45 | 7 |
| Europe centrale (A) | A | CZ,SK,SI | 42 | 6 |
| Nordique restreint (A) | A | FI,IS | 28 | 6 |
| PL | B | PL | 337 | 16 |
| FR | B | FR | 263 | 14 |
| RO | B | RO | 240 | 13 |
| SE | B | SE | 235 | 13 |
| ES | B | ES | 211 | 12 |
| IT | B | IT | 210 | 12 |
| BG | B | BG | 180 | 11 |
| NO | B | NO | 67 | 7 |
| Benelux (B) | B | NL,BE,LU | 42 | 6 |
| Nordique restreint (B) | B | DK,FI,IS | 27 | 6 |
| Europe centrale & Balkans (B) | B | HU,HR,SI | 25 | 6 |
| Méditerranée (B) | B | GR,CY,MT | 24 | 6 |
| Péninsule ibérique & Irlande (B) | B | PT,IE | 22 | 6 |
| Baltique (B) | B | EE,LT,LV | 17 | 6 |
| DACH élargi (B) | B | DE,AT | 16 | 6 |
| **Total (37 strates)** | | | **4564** | **340** (+10 témoins = 350) |

**Groupes documentés** : Baltique = EE+LV+LT · Europe centrale = CZ+SK+SI (axe A) ou HU+HR+SI
(axe B, HU trop peuplé pour être seul mais < 40 en B) · Nordique restreint = FI+IS (axe A) ou
DK+FI+IS (axe B) · Péninsule ibérique & Irlande = PT+IE · Micro-États = MT+LU+LI (axe A
seulement) · Benelux = NL+BE+LU (axe B seulement) · Méditerranée = GR+CY+MT (axe B seulement) ·
DACH élargi = DE+AT (axe B seulement, DE est autonome en A).

**Rien n'a été tiré** : ce tableau montre la conception de la stratification et une proposition
d'allocation, pas un échantillon. J'attends votre validation avant tout tirage.

## 8. Points ouverts (règle d'origine — voir §9 pour l'état actuel)

1. ~~Décider si les segments Freiverkehr régionaux allemands sont retenus~~ — **tranché par la
   classification A/B/C du §4bis** : Freiverkehr = C, informationnel seulement, plus de décision
   binaire à prendre.
2. ~~La seule incohérence LEI trouvée (`959800JG44HG76EPWH68`) reste à investiguer~~ — **résolue
   au §6** (changement de dénomination sociale probable, non exclu).
3. 713 LEI en file de revue manuelle (§6) — non résolus individuellement dans cette session
   (hors Technomeca), non exclus de l'univers.
4. Allocation proposée au §7 non validée, pilote non lancé.
5. Le point 5 des décisions précédentes (ISIN → ticker Yahoo via OpenFIGI, filtre pays +
   devise) reste à coder — aucun tirage nominatif de sociétés n'a eu lieu, donc aucun besoin de
   ticker à ce stade.

---

