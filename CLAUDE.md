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
