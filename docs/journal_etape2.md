# Journal — Étape 2 (mesurer ce que le gratuit permet à grande échelle)

Document de reprise, écrit avant un `/clear` de contexte. Complète (ne remplace pas)
`docs/rapport_etape1.md` (étape 1, terminée, 123 tests) et `docs/univers.md` (mesures
détaillées de la Porte B). Règles de travail de l'étape 2 en fin de document (§6).

## 1. Où on en est

### Porte A — GitHub Actions / yfinance

**Statut : testée deux fois, résultat positif mais partiel.**

- Run #1 (local, sur cette machine) : 12/12 sur cours/volumes/splits/secteur/sharesOutstanding.
- **Run #2 (réel, sur GitHub Actions, lancé par l'utilisateur)** : **12/12 sur tous les champs
  testés à l'époque**, Python 3.14.7, yfinance 1.7.0, **9,95 s**.

**Ce que le run #2 prouve** : depuis un runner GitHub Actions (IP GitHub, pas cette machine),
Yahoo répond sans blocage pour un test ponctuel de 12 tickers sur les cours/infos.

**Ce que le run #2 NE prouve PAS** (script à l'époque incomplet) :
- Les **états financiers** (`income_stmt`/`balance_sheet`/`cashflow`, ce que le pipeline
  utilise réellement en repli fondamentaux) n'étaient **pas testés** sur GitHub — je les ai
  ajoutés au script *après* ce run (testés seulement en local depuis : 12/12, 4-5 exercices,
  45-90 lignes selon société). **Un run #3 sur GitHub est nécessaire** pour confirmer que ça
  marche aussi à distance pour les états financiers.
- Aucun test **à l'échelle** (des centaines/milliers de tickers) : un blocage/rate-limit
  pourrait n'apparaître qu'au volume, jamais testé.
- Un seul point dans le temps : le comportement de Yahoo peut varier selon l'heure, la
  rotation d'IP GitHub, etc. — un seul run positif n'est pas une garantie durable.
- Le mode « échelle » (`scripts/test_yfinance_echelle.py`) est écrit et testé UNIQUEMENT sur
  le petit fichier d'exemple (12 tickers), jamais lancé sur une vraie liste de pilote.

Fichiers : `.github/workflows/test_yfinance.yml` (runs-on ubuntu-24.04, timeout 15 min),
`scripts/test_yfinance_ci.py` (script principal), `scripts/test_yfinance_echelle.py` (mode
échelle), `data/manual/tickers_test.json` (fichier d'exemple, 12 tickers — à remplacer par la
vraie liste du pilote avant usage à l'échelle).

### Porte B — Univers, identification, ticker

**Statut : recherche et mesures terminées et livrées (`docs/univers.md`), STOP respecté (aucun
pilote lancé), aucun code pipeline écrit.**

| Sous-tâche | Fait / pas fait |
|---|---|
| Accès FIRDS, champs, taille, CGU | **Fait** — testé avec de vraies données, voir §3 |
| Test sur 10 ISIN connus | **Fait** — 10/10, LEI FIRDS = LEI déjà en base à 100 % |
| Mesure univers (inclusion UE/EEE, CFI=ES, MIC RMKT/MLTF) | **Fait** — 6 335 ISIN / 6 169 LEI |
| Table des 134 MIC retenus (registre ISO 10383 officiel) | **Fait** — `docs/univers.md` §4 |
| Cross-check LEI vs GLEIF | **Fait, échantillon seulement** (50/50 trouvés, 1 incohérence) — pas exhaustif (6 169 sociétés) |
| Validation extrait large (remplace le JSON brut) | **Fait** — 2 niveaux de preuve, voir §3 |
| Évaluation OpenFIGI (limites, CGU, couverture) | **Fait** — 98/100 résolus sur 100 ISIN/29 pays |
| Table Bloomberg → suffixe Yahoo | **Partiel** — construite empiriquement sur l'échantillon, incomplète (Lisbonne, Oslo, Athènes non observés) |
| Validation nom+devise+cours du mapping ticker | **Fait, mais méthode à corriger** — faille trouvée (voir §4.4) |
| README (mention yfinance) | **Brouillon écrit, pas ajouté au fichier** |
| `pipeline/univers.py`, `pipeline/isin_ticker.py`, etc. | **Pas codé** — attente de validation |
| Pilote (~200 sociétés) | **Pas lancé** — STOP demandé et respecté |

## 2. Décisions de l'étape 2 (avec raison)

| # | Décision | Raison (une ligne) |
|---|---|---|
| 1 | Stockage pilote = JSON compressés (gzip) | Mesuré : ×8,25 de réduction sur les 43 fichiers réels, sans perte |
| 2 | Stockage univers complet = « extrait large » par rapport (faits numériques + concept/dimensions/période, sans blocs texte), compressé, brut supprimé après extraction | Mesuré : ×34 (×512 avec gzip) ; validé identique au JSON brut par test sur le pipeline réel |
| 3 | Pas de TTL sur `esef_json` ; seul l'index se rafraîchit (7 j), on ne télécharge que les nouveaux identifiants de dépôt | Un rapport ESEF déposé est immuable (identifiant unique filings.xbrl.org) : pas besoin d'expiration |
| 4 | Fondamentaux yfinance en cache hebdomadaire, prix quotidiens | Conforme à methode.md (« fondamentaux hebdomadaires ») — **écart connu non encore corrigé dans le code** (actuellement caché par jour, voir §4.7) |
| 5 | `data/cache/pdf/` et `data/cache/xhtml/` non nettoyés | Décision explicite de l'utilisateur, hors sujet de cette phase |
| 6 | Univers = FIRDS (ESMA), pas les 4 sources Euronext/Xetra/Nasdaq Nordic/BME/Wiener Börse listées séparément | Seule Xetra avait une liste ISIN gratuite en vrac confirmée ; FIRDS est une source UE unifiée et officielle |
| 7 | Liste d'**inclusion** UE/EEE (30 pays), pas une liste d'exclusion | Une exclusion (GB/CH/US...) laissait passer des milliers de sociétés non-UE (Canada, Australie, Japon...) cross-cotées sur des MTF allemands (Freiverkehr) |
| 8 | Pas de restriction aux 5 groupes de bourses initiaux pour le pilote | Décider des pays/marchés à garder après mesure de la couverture réelle, pas a priori |
| 9 | ISIN luxembourgeois sur Paris/Amsterdam explicitement inclus et vérifiés | Confirmer que le filtre pays n'exclut pas des sociétés réellement cotées sur les marchés visés |
| 10 | Unité = société (LEI), pas ISIN | 150 sociétés ont plusieurs ISIN (catégories d'actions) : compter par ISIN les compterait en double |
| 11 | Titre de référence = nom légal GLEIF (`identify._gleif_nom`), pas `FullNm` FIRDS | Déjà la convention existante du pipeline ; le nom FIRDS varie selon l'ISIN/le lieu de cotation |
| 12 | ISIN → LEI : FIRDS d'abord, recoupé GLEIF (nom) + présence de rapport filings.xbrl.org | FIRDS porte un LEI par obligation réglementaire (MiFIR) ; GLEIF et filings.xbrl.org confirment de façon indépendante |
| 13 | ISIN → ticker : OpenFIGI, pas Yahoo directement | Gratuit, données FIGI dans le domaine public (contrairement aux CGU Yahoo, non évaluées) |
| 14 | Recherche Yahoo par ISIN = dernier recours seulement, systématiquement signalé | Fiabilité et CGU jamais évaluées pour cet usage |
| 15 | Validation obligatoire nom + devise + cours pour tout mapping ticker, avec comparaison stricte devise-retournée = devise-FIRDS | Faille trouvée : un mapping « premier résultat OpenFIGI » peut pointer vers une cotation secondaire dans une autre devise (Ericsson → coté allemand EUR au lieu du suédois SEK) |
| 16 | README : ne pas affirmer de conformité aux CGU Yahoo | CGU jamais évaluées formellement — ne pas prendre position légale non vérifiée |
| 17 | Stratification du pilote : pays × segment (marché réglementé vs Growth/MTF via le MIC), pas par capitalisation ni secteur | Capitalisation/secteur viennent de yfinance : les utiliser pour stratifier le test DE yfinance serait circulaire |
| 18 | Au moins 5 sociétés par strate, graine fixe | Reproductibilité ; éviter des strates trop petites pour être interprétables |
| 19 | Les 10 sociétés du panel étape 1 incluses comme témoins dans le pilote | Si le pilote ne redonne pas les mêmes résultats, c'est un signal d'alerte sur le pipeline, pas sur les nouvelles sociétés |
| 20 | Capitalisation et secteur mesurés après coup, pas comme critères de stratification | Cohérent avec la décision 17, tout en gardant la lecture des résultats par capitalisation/secteur possible |
| 21 | Aucun mapping IFRS/concept trop large (ex. `OtherNoncurrentFinancialLiabilities` rejeté) | Rappel de l'étape 1 (item 28) : écart >10 % vs yfinance Long Term Debt mesuré, mélange emprunts/leases/autres probable |

## 3. Chiffres mesurés

### Univers FIRDS (détail complet et à jour : `docs/univers.md`, tête du document (§1-19) — fait foi ; ancien §1-8 déplacé en annexe « NE PAS UTILISER » en fin de fichier)

**Mise à jour supplémentaire** : `pipeline/firds.py` (parsing FIRDS, champ correct) +
`tests/test_firds.py` (4 tests, extrait réel) ajoutés — première brique de code Porte B
réellement écrite et testée. LEI : couverture confirmée complète sur les 5 700 LEI de l'univers
final (0 relance nécessaire) ; 706 « à revoir » priorisés par présence ESEF (212/706 en ont un).
**Attention sourcing web** : plusieurs chiffres externes cités dans une itération précédente de
ce document (Finlande, Suède, BME Growth) se sont révélés faux en revérifiant la source
directement (le moteur de recherche synthétisait un chiffre/date qui ne correspondait pas à la
page réelle) — retirés, voir `docs/univers.md` §12. Règle adoptée (citée mot pour mot dans
`CLAUDE.md`) : ne plus citer un chiffre externe sans l'avoir lu soi-même sur la page source.
**Suède confirmée contre l'OCDE, ouverte directement** : 909 sociétés fin 2025
(346 principal + 339 First North + 12 NGM régulé + 88 NGM Nordic SME + 124 Spotlight), mon
univers à −3,7 %.

**Règle de catégorie principale (point 34)** : A si ≥1 venue A, sinon B — les 287 « A+B »
comptent en A. **Point 35** : plusieurs venues B sont contaminées par des cotations-reflet hors
pays (JBUL 100 %, WBDM 86 %, DUSD 44 %) ; une règle de filtrage pays-venue=pays-ISIN est
proposée (PAS codée) — ferait sortir 222 sociétés de l'univers (−3,9 %, Irlande −60 %).
**Point 37** : l'agrégat Nasdaq marché-principal colle à 0,9 % près au chiffre officiel (669 vs
675) ; le First North apparent (570 vs 444) s'explique aux 5/6 par 153 sociétés norvégiennes
rattachées via l'extension transfrontalière documentée First North Sweden-Norway.
**Point 30 (complétude ESEF par pays, indépendante du web)** : 47,9 % des sociétés A ont un ESEF
2024/2025 sur `filings.xbrl.org` — mais **0 % pour l'Allemagne, la Bulgarie, la Roumanie, la
Tchéquie, la Lettonie et le Liechtenstein** (vérifié : ce n'est pas un bug, 3 sociétés
allemandes réelles et connues — BayWa AG notamment — confirmées à 0 dépôt individuellement).
Cohérent avec `pipeline/test_isins.yaml` qui note déjà SAP comme repli yfinance pour
l'Allemagne — ce point 30 confirme et étend ce constat à 5 autres pays. Détail complet :
`docs/univers.md` §21-26.

**⚠️ Chiffres ci-dessous datés (§1-8 de `docs/univers.md`), conservés pour l'historique du bug,
NE PLUS UTILISER.** Bug trouvé le 30/09 (session suivante) : le champ FIRDS utilisé pour « la
venue » de chaque enregistrement (`TechAttrbts/RlvntTradgVn`) est en réalité un attribut de
niveau ISIN (constant sur tous les enregistrements d'un même ISIN, vérifié : 0 exception sur
729 992 enregistrements), pas une venue par admission réelle. Champ correct :
`TradgVnRltdAttrbts/Id`. Conséquence : 208 MIC réels observés (pas 134), univers recalculé à
**5 806 ISIN / 5 700 LEI** (règle A/B — A = `RMKT` registre, B = `MLTF` registre, palier
fonctionnel en information ; C = dark/midpoint/internalisateurs/plateformes-écran, avec une
règle de repli pour ne jamais exclure une société qui n'a qu'une venue-écran comme seule
option). Validé par un test décisif : les 10 sociétés du panel étape 1 sont toutes dans
l'univers. **Contrôle de vraisemblance (corrigé le 30/09 — 3 citations précédentes invalidées
en rouvrant les sources, voir `docs/univers.md` §12)** : Suède confirmée contre la source OCDE
2026 réellement ouverte (909 sociétés fin 2025 — 346 marché principal + 339 First North + 12
NGM régulé + 88 NGM Nordic SME + 124 Spotlight), mon univers (875) à −3,7 % ; Finlande contre
Wikipédia (134/50, avril 2024, source faible, non datée fin 2025) à +1,5 %/−4,0 % ; Nasdaq
Helsinki T4 2025 recherché spécifiquement sans succès → **non vérifié** ; BME Growth : pas de
chiffre externe confirmé, mais 61,8 % de mon ES-B (131-132/212) sont des SOCIMI (foncières),
hors périmètre `methode.md` — explique une bonne part de tout écart, filtre sectoriel pas encore
codé. File de revue LEI reclassée en 3 niveaux (1 changement de nom confirmé, 12 LEI douteux, 10
concordances confirmées manuellement, 706 à revoir, 212 avec ESEF disponible). Détail complet,
table par MIC, méthode de pondération pour l'extrapolation du pilote : `docs/univers.md` (tête
du document — ancien contenu en annexe « NE PAS UTILISER »). **Toujours aucun pilote lancé,
aucun tirage effectué.**

- Fichier `FULINS_E` (actions, hebdomadaire, 05/09/2026), 2 parties : **8,64 Mo + 3,61 Mo =
  12,25 Mo compressés** (public, sans authentification) ; **~550 Mo décompressés**.
- 193 036 ISIN bruts (toutes classifications) → **6 385** avec CFI `ES*` + préfixe ISIN UE/EEE
  → 6 335 ISIN retenus sous l'ANCIENNE règle RMKT/MLTF (§2 univers.md, non affectée par le bug
  de champ pour les compteurs ISIN/LEI eux-mêmes — seul le détail par MIC était faux ; règle
  remplacée depuis par A/B/C, voir ci-dessus).
- 5 ISIN luxembourgeois confirmés sur XPAR/XAMS (Aperam, Reinet, ArcelorMittal, InPost,
  Younited Financial).

### Cache et volumétrie (panel 10 sociétés, étape 1)
- Cache pertinent au pipeline : **163,5 Mo** (dont `esef_json` 159 Mo / 43 rapports, 8/10
  sociétés avec ESEF).
- `data/processed/` (sortie finale) : **1,3 Mo** (~130 Ko/société).
- `data/cache/pdf/` (45 Mo) et `data/cache/xhtml/` (97 Mo) : **orphelins**, non utilisés par le
  code du pipeline (aucune référence trouvée), conservés sur décision explicite (§2.5).
- Extrapolation univers ~4 300 sociétés (estimation par pays) : brut esef_json **~2,9 Go**.

### Extrait large (remplace le JSON brut)
- 166,5 Mo brut → **4,9 Mo extrait (÷34)** → **0,3 Mo extrait + gzip (÷512)**.
- **Validation à 2 niveaux, avec le vrai code du pipeline** (`extraire_rapport`,
  `fusionner_rapports`, `ajuster_splits`) sur les 43 rapports réels :
  - Niveau bas (extraction par rapport) : **1075/1075 valeurs identiques (100 %)**.
  - Niveau haut (série fusionnée + critères P1/P3/P4/P5, comparés aux résultats réels de
    l'étape 1) : **1039/1040 (99,9 %)**. Le seul écart restant est expliqué (sélection entre
    deux rapports concurrents SE-0/SE-1 pour le même exercice — un détail de test, pas une
    perte d'info). Les divergences de critères pour 4/8 sociétés sont **100 % expliquées** :
    leur exercice le plus récent vient de yfinance (retard ESEF), non rejoué par ce test
    (hors périmètre — l'extrait large ne concerne que le JSON ESEF).

### OpenFIGI
- CGU données (pas seulement outils) : FIGI et données de correspondance dans le domaine
  public, réutilisables et redistribuables librement (vérifié via les CGU officielles).
- Limite sans clé : 25 req/min, 10 ISIN/requête.
- Test sur **100 ISIN aléatoires (graine fixe), 29 pays représentés** : **98/100 résolus**
  (2 échecs : sociétés absentes d'OpenFIGI, "No identifier found").
- Validation nom+devise+cours sur 20 candidats : 16/20 (80 %) — mais méthode de sélection du
  résultat à corriger avant tout code (§4.4).

### GitHub Actions (Porte A, run #2)
12/12 tickers, tous champs testés à l'époque (cours/volumes/splits/secteur/actions) réussis.
Python 3.14.7, yfinance 1.7.0, **9,95 s** pour 12 tickers.

## 4. Points en attente de validation

1. ~~Décider si les segments Freiverkehr allemands régionaux sont retenus~~ — **tranché** :
   classification A/B/C (`docs/univers.md` §11), Freiverkehr = C partout.
2. ~~Investiguer l'incohérence LEI `959800JG44HG76EPWH68`~~ — **résolue** : changement de
   dénomination sociale confirmé (avis BME Growth du 16/09/2020), non exclu.
3. **Lancer un run #3 sur GitHub Actions** avec le script mis à jour (états financiers +
   détection 429 + `ubuntu-24.04`/`timeout-minutes: 15`) pour confirmer à distance.
4. Corriger la méthode de validation ISIN→ticker avant tout code : prioriser le code Bloomberg
   du pays de l'ISIN (pas le premier résultat OpenFIGI) ET rejeter si la devise retournée ≠
   devise FIRDS (`NtnlCcy`).
5. Compléter la table Bloomberg→Yahoo pour les codes non observés dans l'échantillon de 100
   (Lisbonne, Oslo, Athènes notamment).
6. Choisir concrètement l'implémentation de la stratégie de stockage actée (§2.1-2.2) —
   décidée mais pas codée.
7. Corriger dans le code l'écart cache quotidien (actuel) vs hebdomadaire (décidé) pour
   `yf_fondamentaux`/`infos` (`pipeline/ingest_fallback.py`, `pipeline/ingest_market.py`).
8. Valider le texte du README (brouillon donné en chat, pas encore ajouté au fichier).
9. Lancer le mode échelle du test yfinance (`scripts/test_yfinance_echelle.py`) avec la vraie
   liste du pilote — script prêt, jamais exécuté à cette échelle.
10. Après validation de tout ce qui précède : coder `pipeline/univers.py`,
    `pipeline/isin_ticker.py`, adapter `pipeline/run.py` pour un panel variable, et lancer le
    pilote (~200 sociétés) — rien de tout cela n'est encore codé.

## 5. Commandes utiles et emplacement des fichiers

```bash
# Pipeline (étape 1, 10 sociétés de test)
.venv/bin/python -m pipeline.run
.venv/bin/python -m pipeline.report_etape1

# Tests unitaires (123 passent actuellement)
.venv/bin/python -m pytest tests -q

# Test yfinance CI (local, avant de pousser sur GitHub)
.venv/bin/python scripts/test_yfinance_ci.py

# Mode échelle (SEULEMENT sur le fichier d'exemple tant que la vraie liste n'est pas prête)
.venv/bin/python scripts/test_yfinance_echelle.py --tickers-file data/manual/tickers_test.json --pause 1.0
```

**Toujours `.venv/bin/python` (Python 3.14), jamais `python`/`python3` nu.**

| Fichier | Rôle |
|---|---|
| `CLAUDE.md` | Instructions projet, source de vérité process (section étape 2 mise à jour) |
| `docs/methode.md` | Méthode de scoring — source de vérité unique, **non modifiée en étape 2** |
| `docs/rapport_etape1.md` | Rapport étape 1 (10 sociétés test), généré |
| `docs/univers.md` | Mesures Porte B étape 2 (univers FIRDS, MIC, LEI) |
| `docs/journal_etape2.md` | Ce document |
| `pipeline/config.yaml` | Tous les seuils/pondérations — **non modifié en étape 2** |
| `pipeline/mapping_ifrs.yaml` | Mapping concepts IFRS → postes |
| `pipeline/test_isins.yaml` | Panel de 10 sociétés (étape 1) |
| `.github/workflows/test_yfinance.yml` | Workflow Porte A (déclenchement manuel) |
| `scripts/test_yfinance_ci.py` | Script Porte A (12 tickers fixes) |
| `scripts/test_yfinance_echelle.py` | Script Porte A, mode échelle (fichier de tickers paramétrable) |
| `data/manual/tickers_test.json` | Fichier d'exemple (12 tickers) pour le mode échelle |
| `data/manual/isin_lei.csv` | Correspondances ISIN→LEI vérifiées à la main |
| `data/cache/` | Cache local (gitignore) |
| `data/processed/` | Sorties calculées (gitignore) |

## 6. Règles de travail (étape 2, héritées de l'étape 1)

- **Aucune donnée inventée.** Donnée manquante = `null` + raison explicite. Toute hypothèse
  listée et marquée HYPOTHÈSE.
- **Ne jamais contourner un blocage** (anti-robot, limite de débit, certificat) : le signaler
  et s'arrêter sur ce point précis, jamais de proxy/faux user-agent/contournement.
- **Aucun mapping IFRS trop large** (cf. étape 1, item 28) : toujours vérifier un concept
  candidat contre une source indépendante avant de l'ajouter.
- **Toute affirmation sur une cause de donnée manquante est accompagnée d'une preuve**
  (extrait JSON réel, réponse d'API réelle citée) — jamais une supposition seule.
- **À chaque livraison : liste « fait / pas fait »**, avec l'endroit exact du rapport où
  vérifier chaque point.
- **Jobs longs en arrière-plan avec un journal** ; ne montrer que des résumés, pas le détail
  brut ligne par ligne.
- **Ne jamais inventer de seuil, pondération ou règle absent de `docs/methode.md`** ; ne pas
  modifier `docs/methode.md` ni `pipeline/config.yaml` sans validation explicite.
- **Pas de commit** — l'utilisateur commite lui-même après relecture.
