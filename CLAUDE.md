# Projet : Screener PEA — méthode hybride « Porte + Score QVM + Timing »

## Contexte
Application de suivi d'actions éligibles PEA, horizon d'investissement 2 à 5 ans.
Méthode entièrement décrite dans `/docs/methode.md` : c'est la source de vérité unique.
Ne jamais inventer de seuil, de pondération ou de règle absent de ce fichier.
Budget données : 0 €. Architecture : pipeline Python batch + site statique.

## Univers
- V1 : actions éligibles PEA, hors banques, assurances et foncières.
- Éligibilité PEA : proxy pays ISIN ∈ UE/EEE, exclusion GB/CH, exceptions dans
  `/data/manual/pea_exceptions.csv` ; badge « à confirmer auprès du courtier ».
- Listes de départ : fichiers publics Euronext, Xetra, Nasdaq Nordic, BME, Wiener Börse, etc.

## Sources (100 % gratuites)
- Fondamentaux : API filings.xbrl.org (lib `xbrl-filings-api`), mapping des concepts IFRS
  dans `/pipeline/mapping_ifrs.yaml` (plusieurs concepts candidats par poste, ordre de priorité).
- Repli fondamentaux : yfinance (Euronext Growth, Allemagne, Irlande) → badge « historique court ».
- Prix, volumes, secteur, indice STOXX Europe 600 : yfinance, Stooq en secours.
- Indicateurs techniques (RSI 14, MM50, MM200) calculés localement.
- Corrections manuelles éventuelles : `/data/manual/{isin}.yaml` (prime sur les données auto).

## Règles non négociables
- 3 étages séparés : Porte (éliminatoire) / Score QVM (percentiles sectoriels) / Timing.
  Le timing n'entre jamais dans le score.
- Fenêtre de 5 exercices ; si moins disponibles, calcul sur l'historique existant + badge.
- Donnée manquante = `null` + badge « indisponible ». Jamais d'estimation silencieuse.
- Chaque valeur porte : source, date, flag qualité (erreurs de validation ESEF).
- Ratios dans la devise publiée ; conversion EUR uniquement pour comparer (volumes, capitalisation).
- Tous les seuils et pondérations dans `/pipeline/config.yaml` (tag PARAMÈTRE de methode.md).

## Front (Next.js export statique, Tailwind)
1. `/methode` : 1 carte par indicateur, regroupées par étage (Porte / Qualité / Valeur /
   Momentum / Timing / Sortie), tag d'origine visible, définition, seuil, pourquoi, limites.
2. `/screener` : cartes entreprises (nom, pays, secteur, porte ✅/❌, score QVM avec
   3 sous-scores, badge timing 🟢🟡🔴, verdict). Tri par score ; filtres pays / secteur /
   verdict / timing / mode strict-relatif.
3. `/entreprise/[isin]` : détail de la porte (valeur, seuil, ✅/❌), détail des percentiles
   QVM, timing, verdict + 3 points, alertes de sortie, données manquantes, sources ;
   graphiques (CA, marges, BNPA, PER vs médiane, cours + MM50 + MM200 + RSI).
4. `/mes-lignes` : critères de sortie et règles de diversification appliqués à mes positions
   (`/data/manual/portefeuille.yaml`).

## Orchestration
GitHub Actions (dépôt public) : prix quotidiens, fondamentaux hebdomadaires, cache disque,
retries avec backoff, rapport d'erreurs en fin de run.

## Livraison par étapes — attendre ma validation entre chaque étape
1. Ingestion + calculs sur 10 ISIN de test (mix large/small caps, FR/NL/IT/DE/SE,
   1 cyclique, 1 valeur Euronext Growth) + tests unitaires de chaque calcul
   (F-score et Z''-score vérifiés à la main sur 2 sociétés).
2. Rapport de couverture : % de l'univers avec ≥ 5 exercices, par pays et par marché ;
   % de valeurs par secteur (vérifier que le classement par percentile est possible).
3. Front `/methode` + `/screener`.
4. Fiche entreprise + `/mes-lignes`.
5. (Optionnel) Backtest indicatif, avec avertissement explicite : biais du survivant
   (sociétés radiées absentes) et historique court (ESEF depuis FY2020).

À chaque étape : lister les hypothèses prises et les données introuvables.

## Étape 2 : décisions prises (mesurer ce que le gratuit permet à grande échelle)

Détail complet, chiffres mesurés et points en attente : `docs/journal_etape2.md` (journal de
reprise) et `docs/univers.md` (mesures Porte B). Résumé des décisions actées :

- **Univers** : source = FIRDS (ESMA, `registers.esma.europa.eu`), pas les 5 bourses listées
  ci-dessus séparément (seule Xetra avait une liste ISIN gratuite en vrac confirmée). Filtre =
  liste d'**inclusion** UE/EEE (30 pays, pas d'exclusion — une exclusion laissait passer des
  milliers de sociétés non-UE cross-cotées sur des MTF allemands). CFI = actions ordinaires
  (`ES*`). Pas de restriction a priori aux 5 groupes de bourses pour le pilote : décidé après
  mesure de la couverture.
- **Unité = société (LEI)**, pas ISIN (sociétés à plusieurs catégories d'actions). Titre de
  référence = nom légal GLEIF (déjà la convention du pipeline), pas le nom FIRDS.
- **ISIN → LEI** : FIRDS d'abord, recoupé GLEIF (nom) + présence de rapport filings.xbrl.org.
- **ISIN → ticker** : OpenFIGI (données dans le domaine public, contrairement aux CGU Yahoo,
  jamais évaluées). Validation obligatoire nom + devise + cours, devise comparée strictement à
  celle de FIRDS. Recherche Yahoo par ISIN = dernier recours seulement, toujours signalé.
- **Stockage** : JSON brut ESEF jamais conservé à grande échelle — « extrait large » (faits
  numériques + concept/dimensions/période, sans blocs texte) compressé, brut supprimé après
  extraction (mesuré : ÷512 avec gzip, validé identique au brut sur le pipeline réel). Pas de
  TTL sur les rapports ESEF (immuables une fois déposés) ; fondamentaux yfinance en cache
  hebdomadaire, prix quotidiens.
- **Pilote** (~200 sociétés) : stratifié par pays × segment (marché réglementé vs Growth/MTF),
  jamais par capitalisation/secteur (circularité, ces données viennent de yfinance). Au moins
  5 sociétés par strate, graine fixe. Les 10 sociétés de l'étape 1 incluses comme témoins.
- **yfinance/Yahoo** : usage recherche personnelle uniquement, CGU Yahoo non garanties
  conformes (le README ne l'affirme pas). Porte A (test GitHub Actions) : positive à petite
  échelle (12/12, 9,95 s) mais pas encore testée pour les états financiers à distance ni à
  l'échelle du pilote.
- **Aucun pilote lancé à ce jour** — étape 2 encore en phase de mesure/validation, aucun code
  `pipeline/univers.py` ou `pipeline/isin_ticker.py` écrit.
