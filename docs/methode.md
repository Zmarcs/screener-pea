# Méthode de sélection — Hybride « Porte + Score QVM + Timing »

Source de vérité unique pour les calculs du pipeline ET le contenu de la page /methode.
Horizon d'investissement : 2 à 5 ans. Fenêtre d'analyse : 5 derniers exercices.
Univers V1 : actions éligibles PEA, hors banques, assurances et foncières.

Tags d'origine affichés sur chaque carte :
- `FORMATION` = critère issu de la formation
- `COMPLÉMENT` = ajout méthodologique (facteur documenté)
- `PARAMÈTRE` = seuil ou pondération de départ, à calibrer

---

## ÉTAGE 1 — PORTE (éliminatoire : tous les critères doivent être validés)

### P1 — Croissance du chiffre d'affaires `FORMATION`
- Seuil : CAGR 5 ans ≥ 10 % ET au maximum 1 année en baisse. `PARAMÈTRE`
- Affiché aussi : pente log-linéaire, historique en barres (années en baisse en rouge).
- Limite : croissance externe et effets de change gonflent le CA.
- Historique insuffisant : moins de 6 exercices disponibles (= 5 variations annuelles) → critère
  « non évaluable », jamais ✅. Le CAGR calculé sur l'historique existant est affiché avec son
  libellé réel (ex. « CAGR 3 ans ») et son année de base. `PARAMÈTRE` (minimum : 6 exercices)

### P2 — Marges `FORMATION`
- Marge EBIT > 20 % (mode strict) OU top quartile du secteur (mode relatif).
- Marge nette > 10 %.
- Tendance des marges : pente ≥ −0,5 pt/an. `PARAMÈTRE`
- Marge EBITDA affichée pour information seulement (IFRS 16 la gonfle depuis 2019).
- Fiabilité `COMPLÉMENT` : si le dernier exercice utilisé vient de yfinance (retard de
  publication ESEF) et que son EBIT diffère de l'ESEF de plus de 5 % sur l'exercice commun
  (`PARAMÈTRE`), P2 est recalculé sur les seules années ESEF disponibles (plus anciennes) et
  comparé au calcul complet. Même conclusion → gardée sans plafonnement (le calcul ESEF seul
  devient la référence). Conclusion différente → statut « dépend d'une donnée non recoupée »,
  non évaluable, verdict plafonné à SURVEILLANCE. Ce libellé (pas « non fiable ») est délibéré :
  le calcul sur années ESEF plus anciennes ne prouve pas que la donnée yfinance est fausse, il
  montre seulement que la conclusion dépend de la donnée retenue. Sans aucun rapport ESEF du
  tout (source 100 % yfinance) : statut « non recoupé », non évaluable (aucun repli possible).

### P3 — Croissance du BNPA `FORMATION`
- Seuil : CAGR 5 ans ≥ 10 %.
- BNPA de départ négatif ou nul : CAGR non calculable → critère ❌ avec mention explicite.
- Historique insuffisant (moins de 6 exercices) : « non évaluable », même règle que P1. `PARAMÈTRE`

### P4 — Piotroski F-score ≥ 6 `COMPLÉMENT`
Santé financière en 9 tests binaires (1 point chacun), sur 2 exercices :
- Rentabilité : ROA > 0 ; cash-flow opérationnel > 0 ; ROA en hausse ; cash-flow opérationnel > résultat net.
- Structure : dette long terme / actif en baisse ; ratio de liquidité courante en hausse ; pas d'émission d'actions nouvelles.
- Efficacité : marge brute en hausse ; rotation de l'actif (CA / actif) en hausse.
- Si la marge brute n'est pas publiée (compte de résultat par nature) : remplacée par la marge EBIT, avec badge.
- Actif de référence `COMPLÉMENT` : les 4 tests utilisant l'actif total (ROA, ROA en hausse,
  levier, rotation de l'actif) sont calculés en convention Piotroski originale — actif
  D'OUVERTURE (= actif de clôture de l'exercice précédent), pas de clôture. Si l'actif
  d'ouverture de l'exercice N−1 est indisponible (historique insuffisant) : ces 4 tests sont non
  évaluables, sans repli silencieux sur la clôture (affichée à titre indicatif seulement).
- Fiabilité `COMPLÉMENT` : même règle que P2 — pour les sociétés à données en retard (dernier
  exercice yfinance), le F-score est recalculé sur les seules années ESEF disponibles (N−1 vs
  N−2, plus anciennes) et comparé au calcul avec l'exercice yfinance. Même conclusion → gardée
  sans plafonnement. Conclusion différente → statut « dépend d'une donnée non recoupée », non
  évaluable, verdict plafonné à SURVEILLANCE (le calcul ESEF seul, plus ancien, ne prouve pas que
  yfinance est faux).

### P5 — Altman Z''-score > 1,1 `COMPLÉMENT`
Risque de défaillance (version non-industrielle) :
Z'' = 6,56·X1 + 3,26·X2 + 6,72·X3 + 1,05·X4
- X1 = BFR / actif total ; X2 = réserves / actif total ; X3 = EBIT / actif total ; X4 = capitaux propres / dettes totales.
- Zones : > 2,6 saine ; 1,1 à 2,6 zone grise (badge) ; < 1,1 détresse (exclusion).

### P6 — Liquidité `COMPLÉMENT`
- Volume moyen quotidien sur 3 mois > 100 000 €. `PARAMÈTRE`
- Pourquoi : sur une valeur illiquide, le RSI est du bruit et la sortie est difficile.

---

## ÉTAGE 2 — SCORE QVM (0 à 100, classement par percentile au sein du secteur)

Chaque métrique est convertie en percentile dans son secteur (secteur européen ;
si moins de 10 sociétés, percentile sur l'univers entier). Sous-score = moyenne des
percentiles. Métrique manquante = exclue de la moyenne, jamais remplacée.

### Qualité — 40 % `PARAMÈTRE`
- Q1 ROCE = EBIT / (actif total − dettes courantes) — plus haut = mieux.
- Q2 Conversion FCF = (cash-flow opérationnel − capex) / résultat net — plus haut = mieux.
- Q3 Accruals = (résultat net − cash-flow opérationnel) / actif total — plus bas = mieux.
- Q4 Stabilité de la marge EBIT = écart-type sur 5 ans — plus bas = mieux.

### Valeur — 30 % `PARAMÈTRE`
- V1 Rendement EBIT / EV — plus haut = mieux.
- V2 PER actuel / médiane du PER sur 5 ans (PER négatifs exclus) — plus bas = mieux. `FORMATION` (adapté : 5 ans, médiane)
  - Approximation : « PER actuel » = cours du jour / BNPA du dernier exercice publié
    (ESEF ne fournit pas de BNPA sur 12 mois glissants). Affiché sous le nom
    « PER sur dernier exercice publié (FYxxxx) ». Le BNPA 12 mois de yfinance est montré
    à titre indicatif seulement, il n'entre pas dans le calcul.
  - PER historique d'un exercice = cours de clôture du dernier jour de l'exercice / BNPA de
    l'exercice. Cours et BNPA toujours dans la même devise (conversion au taux BCE de la date
    du cours si nécessaire).
- V3 Rendement FCF = FCF / capitalisation — plus haut = mieux.

### Momentum — 30 % `PARAMÈTRE`
- M1 Performance 12 mois hors dernier mois — plus haut = mieux.
- M2 Force relative 6 mois vs indice de référence (STOXX Europe 600) — plus haut = mieux.
- M3 Variation du BNPA sur le dernier exercice — plus haut = mieux (proxy des révisions de consensus, indisponibles gratuitement).

---

## ÉTAGE 3 — TIMING (signal d'entrée, n'entre jamais dans le score)

- 🟢 ENTRÉE : cours > MM200 ET MM200 en hausse sur 1 mois ET (RSI 14 entre 35 et 45 OU cours à ±2 % de la MM50).
- 🟡 ATTENDRE : tendance haussière mais pas de repli (RSI > 45), ou surachat (RSI ≥ 70 : ne pas initier).
- 🔴 TENDANCE BAISSIÈRE : cours < MM200 → pas d'entrée, même si RSI < 30 (risque de « couteau qui tombe »).
- `FORMATION` : le RSI 14 journalier reste l'outil de timing ; seule la zone change (repli dans une tendance haussière plutôt que survente).
- Exécution : entrée en 2 ou 3 fois.

---

## VERDICT (règles déterministes)

- ACHAT : porte ✅ ET score ≥ 70 ET timing 🟢.
- SURVEILLANCE : porte ✅ ET score ≥ 50, timing 🟡/🔴 ou score entre 50 et 70.
- REJET : porte ❌ OU score < 50.
- Critère de porte « non évaluable » (historique insuffisant ou donnée indisponible), sans aucun ❌ :
  verdict plafonné à SURVEILLANCE (jamais ACHAT). `PARAMÈTRE`
- Justification en 3 points générée par règles : les 3 éléments les plus discriminants (critère de porte le plus juste, meilleur et pire sous-score).
- Seuils 50 / 70 : `PARAMÈTRE`.

---

## SORTIE ET PORTEFEUILLE

Critères de sortie (un seul suffit à déclencher une alerte) :
- F-score ≤ 4.
- Cours < MM200 depuis plus de 8 semaines ET momentum 12 mois négatif.
- PER > médiane 5 ans + 1 écart-type sans croissance du BNPA qui le justifie.
- Croissance du CA < 5 % sur 2 exercices consécutifs.
- Rupture de thèse (appréciation manuelle).

Portefeuille :
- 15 à 25 lignes, 5-8 % maximum par ligne, 25 % maximum par secteur.
- Revue après chaque publication (semestrielle pour la plupart des sociétés européennes).

---

## DONNÉES REQUISES (toutes gratuites)

- ESEF (filings.xbrl.org) : CA, EBIT, résultat net, BNPA, cash-flow opérationnel, capex,
  actif total, actif et dettes courants, dette long terme, capitaux propres, réserves,
  dettes totales, trésorerie, nombre d'actions, marge brute si publiée.
- yfinance : cours et volumes journaliers, secteur, indice de référence ; repli pour les
  fondamentaux des sociétés hors ESEF (Euronext Growth, Allemagne, Irlande) → badge « historique court ».

Rappel affiché sur le site : analyse, pas un conseil en investissement personnalisé.
