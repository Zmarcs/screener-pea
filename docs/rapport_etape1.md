# Rapport — Étape 1 : ingestion et calculs sur 10 sociétés test

Généré le 2026-09-30 par `pipeline/report_etape1.py` à partir de `data/processed/`. Analyse, pas un conseil en investissement personnalisé.

- Tests unitaires : `123 passed in 0.56s` (`.venv/bin/python -m pytest tests`).
- Relancer : `.venv/bin/python -m pipeline.run` puis `.venv/bin/python -m pipeline.report_etape1`.
- Les scores QVM de ce panel sont **non significatifs** (10 sociétés, percentiles sur l'univers entier).

## 0. Panel et identification

| Société | ISIN actuel | LEI (source) | Autres ISIN rattachés | Marché | Fondamentaux | Exercices disponibles | Référentiel comptable |
|---|---|---|---|---|---|---|---|
| Hermès International | FR0000052292 | 969500Y4IJGHJE2MTJ13 (GLEIF (filtre ISIN)) | — | Euronext Paris | ESEF : 6 rapport(s) retenu(s) | **7** (FY2019→FY2025) | IFRS (ESEF) |
| ASML Holding | NL0010273215 | 724500Y6DUVHQD6OXN27 (GLEIF (filtre ISIN)) | + 1 ISIN GLEIF non vérifiés (obligations…) | Euronext Amsterdam | ESEF : 5 rapport(s) retenu(s) | **7** (FY2019→FY2025) | IFRS (ESEF) |
| SAP | DE0007164600 | 529900D6BF99LW9R2E68 (GLEIF (filtre ISIN)) | + 9 ISIN GLEIF non vérifiés (obligations…) | Xetra | ESEF introuvable (aucun rapport indexé pour ce LEI) — **repli yfinance, historique court** | **4** (FY2022→FY2025) | yfinance (référentiel non garanti) |
| Atlas Copco A | SE0017486889 | 213800T8PC8Q4FYJZR07 (GLEIF (filtre ISIN)) | + 7 ISIN GLEIF non vérifiés (obligations…) | Nasdaq Stockholm | ESEF : 4 rapport(s) retenu(s) — **données en retard** | **6** (FY2020→FY2025) | IFRS (ESEF) |
| Boliden | SE0020050417 | 21380059QU7IM1ONDJ56 (GLEIF (filtre ISIN)) | + 18 ISIN GLEIF non vérifiés (obligations…) | Nasdaq Stockholm | ESEF : 4 rapport(s) retenu(s) — **données en retard** | **6** (FY2020→FY2025) | IFRS (ESEF) |
| Brunello Cucinelli | IT0004764699 | 5493003CX2RZ0FOBH256 (GLEIF (filtre ISIN)) | + 2 ISIN GLEIF non vérifiés (obligations…) | Euronext Milan | ESEF : 4 rapport(s) retenu(s), 1 exclu(s) pour incohérence — **données en retard** | **6** (FY2020→FY2025) | IFRS (ESEF) |
| Thermador Groupe | FR0013333432 | 969500SSIGMAGT008F11 (GLEIF (filtre ISIN)) | — | Euronext Paris | ESEF : 4 rapport(s) retenu(s) | **7** (FY2019→FY2025) | IFRS (ESEF) |
| Sidetrade | FR0010202606 | 969500C43H7W90FX6G79 (GLEIF (filtre ISIN)) | — | Euronext Growth Paris | ESEF introuvable (aucun rapport indexé pour ce LEI) — **repli yfinance, historique court** | **4** (FY2022→FY2025) | yfinance (référentiel non garanti) |
| Mycronic | SE0025158629 | 549300S5CCFESE4C6Y07 (manuel) | SE0000375115 (historique)<br>SE0002135970 (non_identifie) | Nasdaq Stockholm | ESEF : 4 rapport(s) retenu(s) — **données en retard** | **6** (FY2020→FY2025) | IFRS (ESEF) |
| Valneva | FR0004056851 | 969500DIVIP5VKNW4948 (GLEIF (filtre ISIN)) | + 2 ISIN GLEIF non vérifiés (obligations…) | Euronext Paris | ESEF : 5 rapport(s) retenu(s) | **7** (FY2019→FY2025) | IFRS (ESEF) |

Mycronic : l'ISIN SE0000375115 de mon plan n'est plus l'ISIN de l'action. Vérification : l'API Nasdaq Nordic (`api.nasdaq.com/api/nordic/search`) renvoie pour « Mycronic » le seul instrument du groupe *Shares Main Market* : **SE0025158629** (symbole MYCR, orderbookId TX310) ; SE0000375115 et SE0002135970 y sont inconnus (`NO_INST_FOUND`). Le LEI de GLEIF (549300S5CCFESE4C6Y07) est bien celui des déclarations FI que tu cites. Les deux ISIN sont consignés dans `data/manual/isin_lei.csv` avec leur statut et leur source. yfinance enregistre un split ×2 le 2025-06-03, ce qui est cohérent avec un changement d'ISIN en 2025 (non confirmé par une source officielle).

**Référentiel comptable (item 24)** : les données ESEF sont TOUJOURS en IFRS (obligation réglementaire européenne, aucune vérification par société nécessaire). Le repli yfinance ne garantit pas le même référentiel : **ASML**, double coté (Euronext Amsterdam + Nasdaq), publie aussi un Form 20-F réconcilié en US GAAP pour la SEC. Source : [communiqué ASML, résultats T4 et année 2025, 28/01/2026](https://www.asml.com/en/news/press-releases/2026/q4-2025-financial-results). FY2025 : résultat net IFRS 10 213,0 M€ (retenu par le pipeline, source ESEF) contre résultat net US GAAP **9 609,4 M€** ; BNPA de base IFRS 26,29 € (retenu) contre BNPA de base US GAAP **24,73 €** — écart ≈ 6 %, confirmé par ASML. Le pipeline utilise EXCLUSIVEMENT l'IFRS via ESEF pour ASML (pas de repli yfinance nécessaire, 5 rapports ESEF disponibles) : aucun mélange de référentiels dans les calculs. Le risque ne concerne que les sociétés en repli yfinance total (SAP, Sidetrade) ou partiel (données en retard) si leur filiale de cotation américaine influençait les données yfinance — non observé dans ce panel (yfinance suit la cotation primaire européenne pour ces titres).

## a) Les 10 sociétés : porte, score QVM, timing

Légende : ✅ validé · ❌ échec · ⚪ n.é. = non évaluable (historique insuffisant ou donnée indisponible : jamais ✅, plafonne le verdict à SURVEILLANCE).

### a.1 Porte, critère par critère (règle stricte : 6 exercices minimum)

| Société | Ex. | P1 CA | P2 Marges | P3 BNPA | P4 F-score | P5 Z'' | P6 Liquidité | **Porte** | Porte avec 5 ex. | Porte mode relatif |
|---|---|---|---|---|---|---|---|---|---|---|
| Hermès International | 7 | ✅ 20,2 % | ✅ EBIT 41,1 % · net 28,3 % | ✅ 26,6 % | ✅ 7/9 | ✅ 11,41 | ✅ 154,67 M€ | **✅** | ✅ | ✅ |
| ASML Holding | 7 | ✅ 18,5 % | ✅ EBIT 36,9 % · net 31,3 % | ✅ 24,4 % | ✅ 7/9 | ✅ 3,92 | ✅ 863,12 M€ | **✅** | ✅ | ✅ |
| SAP | 4 | ⚪ n.é. 7,6 % | ⚪ n.é. *non recoupé* EBIT 26,1 % · net 19,5 % | ⚪ n.é. 46,3 % | ✅ 7/9 | ✅ 5,25 | ✅ 424,40 M€ | **⚪ n.é.** | ⚪ n.é. | ⚪ n.é. |
| Atlas Copco A | 6 | ✅ 11,0 % | ✅ EBIT 20,7 % · net 15,7 % | ✅ 12,3 % | ⚪ n.é. 5/7 | ✅ 5,00 | ✅ 67,81 M€ | **⚪ n.é.** | ⚪ n.é. | ❌ |
| Boliden | 6 | ✅ 10,7 % | ❌ EBIT 15,3 % · net 11,2 % | ⚪ n.é. 1,2 % | ⚪ n.é. 5/8 | ✅ 4,08 | ✅ 50,01 M€ | **❌** | ❌ | ❌ |
| Brunello Cucinelli | 6 | ✅ 20,9 % | ❌ EBIT 17,2 % · net 9,6 % | ⚪ n.é. indicatif 26,2 % | ⚪ n.é. 5/8 | ✅ 2,16 | ✅ 21,65 M€ | **❌** | ❌ | ❌ |
| Thermador Groupe | 7 | ❌ 4,9 % | ❌ EBIT 11,8 % · net 8,8 % | ❌ 4,1 % | ❌ 5/9 | ✅ 7,85 | ✅ 0,37 M€ | **❌** | ❌ | ❌ |
| Sidetrade | 4 | ⚪ n.é. 20,6 % | ⚪ n.é. *non recoupé* EBIT 14,2 % · net 14,0 % | ⚪ n.é. 37,4 % | ❌ 4/9 | ⚪ n.é. — | ✅ 0,32 M€ | **❌** | ❌ | ❌ |
| Mycronic | 6 | ✅ 15,4 % | ✅ EBIT 25,4 % · net 19,7 % | ⚪ n.é. 17,2 % | ⚪ n.é. 3/7 | ✅ 7,05 | ✅ 7,09 M€ | **⚪ n.é.** | ⚪ n.é. | ❌ |
| Valneva | 7 | ❌ 9,6 % | ❌ EBIT -47,0 % · net -66,0 % | ❌ non calc. | ❌ 2/8 | ❌ -4,43 | ✅ 2,14 M€ | **❌** | ❌ | ❌ |

Seuils : P1 CAGR ≥ 10 % et ≤ 1 année en baisse ; P2 marge EBIT > 20 %, marge nette > 10 %, pente ≥ −0,5 pt/an ; P3 CAGR BNPA ≥ 10 % ; P4 F-score ≥ 6 (x/y = points / tests disponibles) ; P5 Z'' > 1,1 ; P6 volume moyen 3 mois > 100 000 €.

*non recoupé* (P2, règle ajoutée) : dernier exercice 100 % yfinance, aucun rapport ESEF pour recouper → statut ramené à non évaluable, verdict plafonné à SURVEILLANCE. *dépend d'une donnée non recoupée* (P2 et P4) : écart EBIT yfinance/ESEF > 5 % sur l'exercice commun (P2) ou F-score divergent (P4) ET la conclusion change selon la donnée retenue (recalculée sur les seules années ESEF, plus anciennes) → non évaluable. Ce libellé remplace « non fiable » (item 32) : le calcul sur années ESEF plus anciennes ne PROUVE pas que la donnée yfinance est fausse, il montre seulement que la conclusion en dépend. Si la conclusion ne change pas (ex. Boliden P2, Atlas Copco P4), le statut calculé sur les données ESEF est gardé SANS plafonnement (détail en c.1).

Mode relatif de P2 (3e quartile de la marge EBIT) : calculé sur le panel de 10 sociétés, **non significatif** ici.

### a.2 Détail des croissances (P1, P3) : année de base et pente de régression

| Société | P1 : CAGR (libellé réel) | Base | Pente log-linéaire | Années en baisse | P3 : CAGR BNPA | Base | Pente log-linéaire | Si 5 exercices acceptés |
|---|---|---|---|---|---|---|---|---|
| Hermès International | ✅ 20,2 % — CAGR 5 ans (FY2020→FY2025) | FY2020 ⚠️ Covid | 19,8 % | 0 | ✅ 26,6 % — CAGR 5 ans (FY2020→FY2025) | FY2020 ⚠️ Covid | 25,8 % | P1 ✅ · P3 ✅ |
| ASML Holding | ✅ 18,5 % — CAGR 5 ans (FY2020→FY2025) | FY2020 ⚠️ Covid | 17,9 % | 0 | ✅ 24,4 % — CAGR 5 ans (FY2020→FY2025) | FY2020 ⚠️ Covid | 21,3 % | P1 ✅ · P3 ✅ |
| SAP | ⚪ n.é. 7,6 % — CAGR 3 ans (FY2022→FY2025) | FY2022 | 7,8 % | 0 | ⚪ n.é. 46,3 % — CAGR 3 ans (FY2022→FY2025) | FY2022 | 31,7 % | P1 ⚪ n.é. · P3 ⚪ n.é. |
| Atlas Copco A | ✅ 11,0 % — CAGR 5 ans (FY2020→FY2025) | FY2020 ⚠️ Covid | 12,8 % | 1 | ✅ 12,3 % — CAGR 5 ans (FY2020→FY2025) | FY2020 ⚠️ Covid | 13,9 % | P1 ✅ · P3 ✅ |
| Boliden | ✅ 10,7 % — CAGR 5 ans (FY2020→FY2025) | FY2020 ⚠️ Covid | 9,7 % | 1 | ⚪ n.é. 1,2 % — CAGR 4 ans (FY2021→FY2025) | FY2021 | -1,2 % | P1 ✅ · P3 ❌ |
| Brunello Cucinelli | ✅ 20,9 % — CAGR 5 ans (FY2020→FY2025) | FY2020 ⚠️ Covid | 21,2 % | 0 | ⚪ n.é. non évaluable — BNPA de départ ≤ 0 (perte, FY2020) mais retour aux bénéfices (BNPA FY2025 > 0) : non évaluable, jamais ❌ (réservé aux sociétés encore déficitaires) (CAGR 4 ans (FY2021→FY2025) depuis la première année positive : 26,2 %) | FY2020 ⚠️ Covid | — | P1 ✅ · P3 ⚪ n.é. |
| Thermador Groupe | ❌ 4,9 % — CAGR 5 ans (FY2020→FY2025) | FY2020 ⚠️ Covid | 3,9 % | 2 | ❌ 4,1 % — CAGR 5 ans (FY2020→FY2025) | FY2020 ⚠️ Covid | 1,4 % | P1 ❌ · P3 ❌ |
| Sidetrade | ⚪ n.é. 20,6 % — CAGR 3 ans (FY2022→FY2025) | FY2022 | 20,9 % | 0 | ⚪ n.é. 37,4 % — CAGR 3 ans (FY2022→FY2025) | FY2022 | 37,5 % | P1 ⚪ n.é. · P3 ⚪ n.é. |
| Mycronic | ✅ 15,4 % — CAGR 5 ans (FY2020→FY2025) | FY2020 ⚠️ Covid | 15,2 % | 0 | ⚪ n.é. 17,2 % — CAGR 4 ans (FY2021→FY2025) | FY2021 | 23,2 % | P1 ✅ · P3 ✅ |
| Valneva | ❌ 9,6 % — CAGR 5 ans (FY2020→FY2025) | FY2020 ⚠️ Covid | -2,0 % | 1 | ❌ non calculable (valeur de départ ≤ 0 (-0.71) : CAGR non calculable) | FY2020 ⚠️ Covid | — | P1 ❌ · P3 ❌ |

### a.3 Score QVM (mention obligatoire : **non significatif**), timing et verdict

Percentiles calculés sur 10 sociétés seulement (aucun secteur n'atteint 10 sociétés → univers entier). Ces scores servent à vérifier la mécanique de calcul, **pas à classer**.

Règle ajoutée : univers (10 sociétés) < `qvm.min_univers_verdict` (30) → tout ACHAT ou REJET **déterminé par le score** devient **PROVISOIRE** (le verdict qu'il serait est indiqué entre parenthèses). Un REJET dû à la porte ❌ n'est jamais concerné.

| Société | Score QVM | Qualité | Valeur | Momentum | Timing | Verdict | Justification (3 points) |
|---|---|---|---|---|---|---|---|
| Hermès International | 57 *(non significatif)* | 68 | 81 | 19 | 🔴 RSI 36,3, cours/MM200 -22,4 % | **SURVEILLANCE** (porte ✅, score 57 entre 50 et 70) | Critère de porte le plus juste : P4 ✅ (écart au seuil +17%)<br>Meilleur sous-score : valeur (81/100)<br>Pire sous-score : momentum (19/100) |
| ASML Holding | 63 *(non significatif)* | 80 | 11 | 93 | 🟡 RSI 67,9, cours/MM200 22,0 % | **SURVEILLANCE** (porte ✅, score 63 entre 50 et 70) | Critère de porte le plus juste : P4 ✅ (écart au seuil +17%)<br>Meilleur sous-score : momentum (93/100)<br>Pire sous-score : valeur (11/100) |
| SAP | 61 *(non significatif)* | 47 | 77 | 63 | 🟡 RSI 53,4, cours/MM200 11,0 % | **SURVEILLANCE** (critère(s) de porte non évaluable(s) : verdict plafonné à SURVEILLANCE) | Critère de porte le plus juste : P4 ✅ (écart au seuil +17%)<br>Meilleur sous-score : valeur (77/100)<br>Pire sous-score : qualite (47/100) |
| Atlas Copco A | 56 *(non significatif)* | 66 | 46 | 52 | 🟡 RSI 58,6, cours/MM200 12,5 % | **SURVEILLANCE** (critère(s) de porte non évaluable(s) : verdict plafonné à SURVEILLANCE) | Critère de porte le plus juste : P2 ✅ (écart au seuil +3%)<br>Meilleur sous-score : qualite (66/100)<br>Pire sous-score : valeur (46/100) |
| Boliden | 49 *(non significatif)* | 36 | 64 | 52 | 🔴 RSI 43,7, cours/MM200 -6,7 % | **REJET** (porte ❌) | Critère de porte le plus juste : P2 ❌ (écart au seuil -23%)<br>Meilleur sous-score : valeur (64/100)<br>Pire sous-score : qualite (36/100) |
| Brunello Cucinelli | 50 *(non significatif)* | 45 | 59 | 48 | 🔴 RSI 55,5, cours/MM200 -0,8 % | **REJET** (porte ❌) | Critère de porte le plus juste : P2 ❌ (écart au seuil -14%)<br>Meilleur sous-score : valeur (59/100)<br>Pire sous-score : qualite (45/100) |
| Thermador Groupe | 65 *(non significatif)* | 67 | 83 | 44 | 🔴 RSI 40,8, cours/MM200 -5,0 % | **REJET** (porte ❌) | Critère de porte le plus juste : P3 ❌ (écart au seuil -59%)<br>Meilleur sous-score : valeur (83/100)<br>Pire sous-score : momentum (44/100) |
| Sidetrade | 34 *(non significatif)* | 19 | 32 | 56 | 🟡 RSI 56,9, cours/MM200 11,0 % | **REJET** ⚠️ *REJET sur données non recoupées* (porte ❌) | Critère de porte le plus juste : P4 ❌ (écart au seuil -33%)<br>Meilleur sous-score : momentum (56/100)<br>Pire sous-score : qualite (19/100) |
| Mycronic | 44 *(non significatif)* | 34 | 30 | 70 | 🟡 RSI 60,5, cours/MM200 26,5 % | **PROVISOIRE** (score non significatif (univers 10 < 30) : serait REJET (score 44 < 50)) | Critère de porte le plus juste : P2 ✅ (écart au seuil +27%)<br>Meilleur sous-score : momentum (70/100)<br>Pire sous-score : valeur (30/100) |
| Valneva | 14 *(non significatif)* | 33 | 0 | 4 | 🔴 RSI 47,5, cours/MM200 -11,4 % | **REJET** (porte ❌) | Critère de porte le plus juste : P5 ❌ (écart au seuil -503%)<br>Meilleur sous-score : qualite (33/100)<br>Pire sous-score : valeur (0/100) |

### a.4 Valorisation (devise de cotation = devise des comptes pour tout le panel)

| Société | Cours (date) | PER sur dernier exercice publié | Médiane PER 5 ans (PER positifs) | BNPA 12 mois yfinance (indicatif) | Métriques QVM manquantes |
|---|---|---|---|---|---|
| Hermès International | 1 357,00 EUR (2026-09-30) | 31,4 (PER sur dernier exercice publié (FY2025)) | 49,2 | 42,96 | — |
| ASML Holding | 1 623,80 EUR (2026-09-30) | 61,8 (PER sur dernier exercice publié (FY2025)) | 33,1 | 25,36 | — |
| SAP | 184,34 EUR (2026-09-30) | 30,0 (PER sur dernier exercice publié (FY2025)) | 41,6 | 6,68 | — |
| Atlas Copco A | 210,20 SEK (2026-09-30) | 38,7 (PER sur dernier exercice publié (FY2025)) | 30,1 | 5,46 | — |
| Boliden | 516,80 SEK (2026-09-30) | 15,5 (PER sur dernier exercice publié (FY2025)) | 11,0 | 44,76 | — |
| Brunello Cucinelli | 83,20 EUR (2026-09-30) | 41,9 (PER sur dernier exercice publié (FY2025)) | 58,3 | 111 944,91 ⚠️ incohérent avec le BNPA publié (donnée yfinance aberrante, ignorée) | — |
| Thermador Groupe | 70,30 EUR (2026-09-30) | 14,6 (PER sur dernier exercice publié (FY2025)) | 14,8 | 4,96 | — |
| Sidetrade | 193,80 EUR (2026-09-30) | 32,2 (PER sur dernier exercice publié (FY2025)) | 42,2 | 6,27 | — |
| Mycronic | 341,00 SEK (2026-09-30) | 42,7 (PER sur dernier exercice publié (FY2025)) | 25,8 | 8,87 | — |
| Valneva | 2,74 EUR (2026-09-30) | négatif : exclu (PER sur dernier exercice publié (FY2025)) | — | -0,90 | Q2 (résultat net ≤ 0 : ratio non interprétable)<br>V2 (PER actuel négatif ou indisponible : exclu) |

## b) Vérification manuelle : Hermès et ASML

Méthode : chaque poste a été relevé **à la main** dans le tableau du rapport annuel publié (PDF officiel, page indiquée), puis comparé au fait XBRL retenu automatiquement par le pipeline. Les calculs ci-dessous sont refaits à partir des **valeurs publiées**. Les mêmes valeurs figurent dans `tests/test_fscore.py` et `tests/test_zscore.py`. Source des relevés : `data/manual/verification_etape1.yaml`.

### Hermès International

Document publié : [Document d'enregistrement universel 2025 incluant le rapport financier annuel (FR)](https://assets-finance.hermes.com/s3fs-public/node/pdf_file/2026-04/1777391814/260319_hermes_urd2025_fr.pdf). Montants en millions d'euros sauf mention.

| Poste | Exercice | Valeur publiée | Tableau, ligne (page imprimée / page PDF) | Valeur XBRL retenue | Concept IFRS | Rapport ESEF | Écart |
|---|---|---|---|---|---|---|---|
| Chiffre d'affaires | FY2025 | 16 002 | 5.1 Compte de résultat consolidé, « Chiffre d'affaires » (p. 364 / PDF 356) | 16 002,0 | `ifrs-full:Revenue` (fait fc_174269) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Chiffre d'affaires | FY2024 | 15 170 | 5.1 Compte de résultat consolidé, « Chiffre d'affaires » (p. 364 / PDF 356) | 15 170,0 | `ifrs-full:Revenue` (fait fc_174270) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Marge brute | FY2025 | 11 379 | 5.1 Compte de résultat consolidé, « Marge brute » (p. 364 / PDF 356) | 11 379,0 | `ifrs-full:GrossProfit` (fait fc_174273) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Marge brute | FY2024 | 10 660 | 5.1 Compte de résultat consolidé, « Marge brute » (p. 364 / PDF 356) | 10 660,0 | `ifrs-full:GrossProfit` (fait fc_174274) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| EBIT (résultat opérationnel) | FY2025 | 6 569 | 5.1 Compte de résultat consolidé, « Résultat opérationnel » (p. 364 / PDF 356) | 6 569,0 | `ifrs-full:ProfitLossFromOperatingActivities` (fait fc_174283) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| EBIT (résultat opérationnel) | FY2024 | 6 150 | 5.1 Compte de résultat consolidé, « Résultat opérationnel » (p. 364 / PDF 356) | 6 150,0 | `ifrs-full:ProfitLossFromOperatingActivities` (fait fc_174284) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Résultat net part du groupe | FY2025 | 4 524 | 5.1 Compte de résultat consolidé, « Résultat net – part du groupe » (p. 364 / PDF 356) | 4 524,0 | `ifrs-full:ProfitLossAttributableToOwnersOfParent` (fait fc_174297) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Résultat net part du groupe | FY2024 | 4 603 | 5.1 Compte de résultat consolidé, « Résultat net – part du groupe » (p. 364 / PDF 356) | 4 603,0 | `ifrs-full:ProfitLossAttributableToOwnersOfParent` (fait fc_174298) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| BNPA de base | FY2025 | 43,15 | 5.1 Compte de résultat consolidé, « Résultat de base par action en euros » (p. 364 / PDF 356) | 43,15 | `ifrs-full:BasicEarningsLossPerShare` (fait fc_174299) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| BNPA de base | FY2024 | 43,93 | 5.1 Compte de résultat consolidé, « Résultat de base par action en euros » (p. 364 / PDF 356) | 43,93 | `ifrs-full:BasicEarningsLossPerShare` (fait fc_174300) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Actif courant | FY2025 | 15 911 | 5.3 Bilan consolidé – actif, « Actifs courants » (p. 365 / PDF 357) | 15 911,0 | `ifrs-full:CurrentAssets` (fait fc_174353) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Actif courant | FY2024 | 15 476 | 5.3 Bilan consolidé – actif, « Actifs courants » (p. 365 / PDF 357) | 15 476,0 | `ifrs-full:CurrentAssets` (fait fc_174354) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Actif total | FY2025 | 24 322 | 5.3 Bilan consolidé – actif, « TOTAL ACTIF » (p. 365 / PDF 357) | 24 322,0 | `ifrs-full:Assets` (fait fc_174355) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Actif total | FY2024 | 23 084 | 5.3 Bilan consolidé – actif, « TOTAL ACTIF » (p. 365 / PDF 357) | 23 084,0 | `ifrs-full:Assets` (fait fc_174356) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Capitaux propres | FY2025 | 18 846 | 5.3 Bilan consolidé – passif, « Capitaux propres » (p. 365 / PDF 357) | 18 846,0 | `ifrs-full:Equity` (fait fc_174375) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Capitaux propres | FY2024 | 17 334 | 5.3 Bilan consolidé – passif, « Capitaux propres » (p. 365 / PDF 357) | 17 334,0 | `ifrs-full:Equity` (fait fc_174376) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Dette long terme | FY2025 | 34 | 5.3 Bilan consolidé – passif, « Emprunts et dettes financières à plus d'un an » (p. 365 / PDF 357) | 34,0 | `ifrs-full:LongtermBorrowings` (fait fc_174377) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Dette long terme | FY2024 | 61 | 5.3 Bilan consolidé – passif, « Emprunts et dettes financières à plus d'un an » (p. 365 / PDF 357) | 61,0 | `ifrs-full:LongtermBorrowings` (fait fc_174378) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Dettes courantes | FY2025 | 3 186 | 5.3 Bilan consolidé – passif, « Passifs courants » (p. 365 / PDF 357) | 3 186,0 | `ifrs-full:CurrentLiabilities` (fait fc_174407) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Dettes courantes | FY2024 | 3 629 | 5.3 Bilan consolidé – passif, « Passifs courants » (p. 365 / PDF 357) | 3 629,0 | `ifrs-full:CurrentLiabilities` (fait fc_174408) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Réserves (résultats non distribués) | FY2025 | 19 054 | 5.4 État de variation des capitaux propres consolidés, « Colonne « Réserves consolidées et résultat net part du groupe », soldes au 31 décembre » (p. 366 / PDF 358) | 19 054,0 | `ifrs-full:Equity[ifrs-full:ComponentsOfEquityAxis=ifrs-full:RetainedEarningsMember]` (fait fc_174608) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Réserves (résultats non distribués) | FY2024 | 17 163 | 5.4 État de variation des capitaux propres consolidés, « Colonne « Réserves consolidées et résultat net part du groupe », soldes au 31 décembre » (p. 366 / PDF 358) | 17 163,0 | `ifrs-full:Equity[ifrs-full:ComponentsOfEquityAxis=ifrs-full:RetainedEarningsMember]` (fait fc_174512) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Cash-flow opérationnel | FY2025 | 5 374 | 5.5 État des flux de trésorerie consolidés, « Flux de trésorerie liés à l'activité (A) » (p. 367 / PDF 359) | 5 374,0 | `ifrs-full:CashFlowsFromUsedInOperatingActivities` (fait fc_174639) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Cash-flow opérationnel | FY2024 | 5 139 | 5.5 État des flux de trésorerie consolidés, « Flux de trésorerie liés à l'activité (A) » (p. 367 / PDF 359) | 5 139,0 | `ifrs-full:CashFlowsFromUsedInOperatingActivities` (fait fc_174640) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Nombre d'actions | FY2025 | 105 569 412 | 5.4 État de variation des capitaux propres consolidés, « Nombre d'actions au 31 décembre » (p. 366 / PDF 358) | 105 569 412,0 | `ifrs-full:NumberOfSharesIssuedAndFullyPaid` (fait fc_174604) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |
| Nombre d'actions | FY2024 | 105 569 412 | 5.4 État de variation des capitaux propres consolidés, « Nombre d'actions au 31 décembre » (p. 366 / PDF 358) | 105 569 412,0 | `ifrs-full:NumberOfSharesIssuedAndFullyPaid` (fait fc_174508) | [969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0](https://filings.xbrl.org/969500Y4IJGHJE2MTJ13/2026-12-31/ESEF/FR/0/hermes-2025-12-31-1/reports/ixbrlviewer.html) | 0 |

- Bilan p. 365 : « Réserves » 14 443 (N) / 12 464 (N−1) et « Résultat net – part du groupe » 4 524 / 4 603, soit 18 967 / 17 067. L'écart de 87 M€ (2025) et 96 M€ (2024) avec la colonne de l'état de variation p. 366 correspond aux écarts actuariels (−87 / −95 selon ce tableau), présentés dans « Réserves » au bilan mais dans une colonne distincte à la p. 366. Le pipeline retient le fait ESEF ifrs-full:Equity[RetainedEarningsMember] = 19 054, qui est la valeur de la p. 366.
- Dettes totales : aucun total « dettes » au bilan ; calculées = TOTAL PASSIF − Capitaux propres = 24 322 − 18 846 = 5 476 (N) et 23 084 − 17 334 = 5 750 (N−1).

**F-score (FY2025 vs FY2024), calcul ligne par ligne sur les valeurs publiées — actif de CLÔTURE, affichage indicatif seulement (voir ci-dessous pour le calcul de référence)**

| Test | Calcul (actif de clôture) | Valeur N | Valeur N−1 | Point |
|---|---|---|---|---|
| F1 ROA > 0 | ROA 2025 = 4 524,0 / 24 322,0 | 0,1860 | — | **1** |
| F2 Cash-flow opérationnel > 0 | CFO 2025 = 5 374,0 | 5 374,0 | — | **1** |
| F3 ROA en hausse | ROA 2025 (F1) vs ROA 2024 = 4 603,0 / 23 084,0 | 0,1860 | 0,1994 | **0** |
| F4 Cash-flow opérationnel > résultat net | CFO 5 374,0 vs résultat net 4 524,0 | 5 374,0000 | 4 524,0000 | **1** |
| F5 Dette long terme / actif en baisse | 34,0 / 24 322,0 vs 61,0 / 23 084,0 | 0,0014 | 0,0026 | **1** |
| F6 Ratio de liquidité courante en hausse | 15 911,0 / 3 186,0 vs 15 476,0 / 3 629,0 | 4,9940 | 4,2645 | **1** |
| F7 Pas d'émission d'actions nouvelles | actions 105 569 412,0 vs 105 569 412,0 | 105 569 412,0 | 105 569 412,0 | **1** |
| F8 Marge brute en hausse | 11 379,0 / 16 002,0 vs 10 660,0 / 15 170,0 | 0,7111 | 0,7027 | **1** |
| F9 Rotation de l'actif en hausse | 16 002,0 / 24 322,0 vs 15 170,0 / 23 084,0 | 0,6579 | 0,6572 | **1** |

Total à la main, actif de clôture (indicatif) : **8/9**.

**F-score de RÉFÉRENCE (règle ajoutée, remplace la clôture ci-dessus comme calcul principal de P4) : actif D'OUVERTURE, convention Piotroski originale**

ATO 2025 (actif total à l'ouverture de FY2025, = actif de clôture FY2024) = 23 084,0 — déjà relevé à la main ci-dessus. ATO 2024 (actif total à l'ouverture de FY2024, = actif de clôture FY2023) = 20 447,0 : non relevé à la main pour ce complément, source pipeline/ESEF (déjà recoupé pour FY2025 et FY2024 ci-dessus).

| Test | Actifs utilisés (ATO N / ATO N−1) | Valeur N | Valeur N−1 | Point | Point clôture (indicatif) | Change ? |
|---|---|---|---|---|---|---|
| F1 ROA > 0 | 23 084,0 / 20 447,0 | 0,1960 | — | **1** | 1 | non |
| F3 ROA en hausse | 23 084,0 / 20 447,0 | 0,1960 | 0,2251 | **0** | 0 | non |
| F5 Dette long terme / actif en baisse | 23 084,0 / 20 447,0 | 0,0015 | 0,0030 | **1** | 1 | non |
| F9 Rotation de l'actif en hausse | 23 084,0 / 20 447,0 | 0,6932 | 0,7419 | **0** | 1 | **oui** |

**Score de référence (actif d'ouverture) : 7/9** contre 8/9 en clôture (indicatif). Pipeline (valeurs XBRL, même convention) : **7/9** → identique ✅. Seuil P4 : ≥ 6 → ✅.

**Z''-score (FY2025), calcul ligne par ligne sur les valeurs publiées**

- X1 = BFR / actif total = (15 911,0 − 3 186,0) / 24 322,0 = **0,523189**
- X2 = réserves / actif total = 19 054,0 / 24 322,0 = **0,783406**
- X3 = EBIT / actif total = 6 569,0 / 24 322,0 = **0,270085**
- X4 = capitaux propres / dettes totales = 18 846,0 / (24 322,0 − 18 846,0 = 5 476,0) = **3,441563**
- Z'' = 6,56 × 0,523189 + 3,26 × 0,783406 + 6,72 × 0,270085 + 1,05 × 3,441563
  = 3,432119 + 2,553903 + 1,814969 + 3,613641 = **11,4146**
- Pipeline (valeurs XBRL) : **11,4146** → identique ✅ ; zone **saine** (> 2,6).

**F5 avec / sans dettes locatives IFRS 16 dans la dette long terme**

Dettes locatives non courantes (`ifrs-full:NoncurrentLeaseLiabilities`, source pipeline/ESEF) : FY2025 1 987,0, FY2024 1 781,0.

| | Dette LT retenue | Dette LT + IFRS16 |
|---|---|---|
| FY2025 | 34,0 → levier 0,0014 | 2 021,0 → levier 0,0831 |
| FY2024 | 61,0 → levier 0,0026 | 1 842,0 → levier 0,0798 |
| **F5** (levier en baisse ?) | **1** (retenu par le pipeline) | **0** |

**Le point F5 change** selon que les dettes locatives IFRS 16 sont incluses ou non : hors dettes locatives (choix retenu, hypothèse #7), le levier baisse → F5 = 1 ; avec, le levier augmente → F5 = 0.

### ASML Holding N.V.

Document publié : [2025 Annual Report based on IFRS (EN)](https://ourbrand.asml.com/m/6ea363f69344ebd4/original/asml-2025-annual-report-based-on-ifrs.pdf). Montants en millions d'euros sauf mention.

| Poste | Exercice | Valeur publiée | Tableau, ligne (page imprimée / page PDF) | Valeur XBRL retenue | Concept IFRS | Rapport ESEF | Écart |
|---|---|---|---|---|---|---|---|
| Chiffre d'affaires | FY2025 | 32 667,30 | Consolidated statement of profit or loss, « Total net sales » (p. 270 / PDF 270) | 32 667,3 | `ifrs-full:RevenueFromContractsWithCustomers` (fait f-9) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Chiffre d'affaires | FY2024 | 28 262,90 | Consolidated statement of profit or loss, « Total net sales » (p. 270 / PDF 270) | 28 262,9 | `ifrs-full:RevenueFromContractsWithCustomers` (fait f-8) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Marge brute | FY2025 | 16 931,40 | Consolidated statement of profit or loss, « Gross profit » (p. 270 / PDF 270) | 16 931,4 | `ifrs-full:GrossProfit` (fait f-21) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Marge brute | FY2024 | 14 283,80 | Consolidated statement of profit or loss, « Gross profit » (p. 270 / PDF 270) | 14 283,8 | `ifrs-full:GrossProfit` (fait f-20) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| EBIT (résultat opérationnel) | FY2025 | 12 054,00 | Consolidated statement of profit or loss, « Operating income » (p. 270 / PDF 270) | 12 054,0 | `ifrs-full:ProfitLossFromOperatingActivities` (fait f-30) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| EBIT (résultat opérationnel) | FY2024 | 9 937,10 | Consolidated statement of profit or loss, « Operating income » (p. 270 / PDF 270) | 9 937,1 | `ifrs-full:ProfitLossFromOperatingActivities` (fait f-29) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Résultat net part du groupe | FY2025 | 10 213,00 | Consolidated statement of profit or loss, « Net income » (p. 270 / PDF 270) | 10 213,0 | `ifrs-full:ProfitLoss` (fait f-51) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Résultat net part du groupe | FY2024 | 8 349,00 | Consolidated statement of profit or loss, « Net income » (p. 270 / PDF 270) | 8 349,0 | `ifrs-full:ProfitLoss` (fait f-50) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| BNPA de base | FY2025 | 26,29 | Consolidated statement of profit or loss, « Basic net income per ordinary share » (p. 270 / PDF 270) | 26,29 | `ifrs-full:BasicEarningsLossPerShare` (fait f-54) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| BNPA de base | FY2024 | 21,23 | Consolidated statement of profit or loss, « Basic net income per ordinary share » (p. 270 / PDF 270) | 21,23 | `ifrs-full:BasicEarningsLossPerShare` (fait f-53) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Actif courant | FY2025 | 30 240,50 | Consolidated statement of financial position, « Total current assets » (p. 272 / PDF 272) | 30 240,5 | `ifrs-full:CurrentAssets` (fait f-148) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Actif courant | FY2024 | 30 357,20 | Consolidated statement of financial position, « Total current assets » (p. 272 / PDF 272) | 30 357,2 | `ifrs-full:CurrentAssets` (fait f-147) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Actif total | FY2025 | 55 576,80 | Consolidated statement of financial position, « Total assets » (p. 272 / PDF 272) | 55 576,8 | `ifrs-full:Assets` (fait f-150) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Actif total | FY2024 | 52 566,50 | Consolidated statement of financial position, « Total assets » (p. 272 / PDF 272) | 52 566,5 | `ifrs-full:Assets` (fait f-149) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Capitaux propres | FY2025 | 24 185,00 | Consolidated statement of financial position, « Shareholders' equity » (p. 272 / PDF 272) | 24 185,0 | `ifrs-full:Equity` (fait f-152) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Capitaux propres | FY2024 | 22 021,90 | Consolidated statement of financial position, « Shareholders' equity » (p. 272 / PDF 272) | 22 021,9 | `ifrs-full:Equity` (fait f-151) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Dette long terme | FY2025 | 2 709,00 | Consolidated statement of financial position, « Long-term debt » (p. 272 / PDF 272) | 2 709,0 | `ifrs-full:LongtermBorrowings` (fait f-154) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Dette long terme | FY2024 | 3 677,30 | Consolidated statement of financial position, « Long-term debt » (p. 272 / PDF 272) | 3 677,3 | `ifrs-full:LongtermBorrowings` (fait f-153) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Dettes courantes | FY2025 | 24 439,40 | Consolidated statement of financial position, « Total current liabilities » (p. 272 / PDF 272) | 24 439,4 | `ifrs-full:CurrentLiabilities` (fait f-178) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Dettes courantes | FY2024 | 20 049,50 | Consolidated statement of financial position, « Total current liabilities » (p. 272 / PDF 272) | 20 049,5 | `ifrs-full:CurrentLiabilities` (fait f-177) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Réserves (résultats non distribués) | FY2025 | 16 534,80 | Consolidated statement of changes in equity (continued), « Retained earnings + Net income, balance at December 31 (6 321,8 + 10 213,0 ; 5 166,6 + 8 349,0) » (p. 274 / PDF 274) | 16 534,8 | `ifrs-full:Equity[ifrs-full:ComponentsOfEquityAxis=ifrs-full:RetainedEarningsExcludingProfitLossForReportingPeriodMember] + ifrs-full:Equity[ifrs-full:ComponentsOfEquityAxis=ifrs-full:RetainedEarningsProfitLossForReportingPeriodMember]` (fait f-488, f-490) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Réserves (résultats non distribués) | FY2024 | 13 515,60 | Consolidated statement of changes in equity (continued), « Retained earnings + Net income, balance at December 31 (6 321,8 + 10 213,0 ; 5 166,6 + 8 349,0) » (p. 274 / PDF 274) | 13 515,6 | `ifrs-full:Equity[ifrs-full:ComponentsOfEquityAxis=ifrs-full:RetainedEarningsExcludingProfitLossForReportingPeriodMember] + ifrs-full:Equity[ifrs-full:ComponentsOfEquityAxis=ifrs-full:RetainedEarningsProfitLossForReportingPeriodMember]` (fait f-387, f-389) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Cash-flow opérationnel | FY2025 | 13 826,50 | Consolidated statement of cash flows, « Net cash provided by operating activities » (p. 275 / PDF 275) | 13 826,5 | `ifrs-full:CashFlowsFromUsedInOperatingActivities` (fait f-542) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Cash-flow opérationnel | FY2024 | 12 369,70 | Consolidated statement of cash flows, « Net cash provided by operating activities » (p. 275 / PDF 275) | 12 369,7 | `ifrs-full:CashFlowsFromUsedInOperatingActivities` (fait f-541) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Nombre d'actions | FY2025 | 385,4 | Consolidated statement of changes in equity (continued), « Issued and outstanding shares, balance at December 31 » (p. 274 / PDF 274) | 385,4 | `ifrs-full:NumberOfSharesOutstanding` (fait f-484) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |
| Nombre d'actions | FY2024 | 393,3 | Consolidated statement of changes in equity (continued), « Issued and outstanding shares, balance at December 31 » (p. 274 / PDF 274) | 393,3 | `ifrs-full:NumberOfSharesOutstanding` (fait f-383) | [724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0](https://filings.xbrl.org/724500Y6DUVHQD6OXN27/2025-12-31/ESEF/NL/0/asml-2025-12-31-1-en/reports/ixbrlviewer.html) | 0 |

- Dettes totales : calculées = Total assets − Shareholders' equity = 55 576,8 − 24 185,0 = 31 391,8 (N) et 52 566,5 − 22 021,9 = 30 544,6 (N−1).
- Résultat net : ASML n'a pas d'intérêts minoritaires ; « Net income » = résultat part du groupe (concept ESEF ifrs-full:ProfitLoss).

**F-score (FY2025 vs FY2024), calcul ligne par ligne sur les valeurs publiées — actif de CLÔTURE, affichage indicatif seulement (voir ci-dessous pour le calcul de référence)**

| Test | Calcul (actif de clôture) | Valeur N | Valeur N−1 | Point |
|---|---|---|---|---|
| F1 ROA > 0 | ROA 2025 = 10 213,0 / 55 576,8 | 0,1838 | — | **1** |
| F2 Cash-flow opérationnel > 0 | CFO 2025 = 13 826,5 | 13 826,5 | — | **1** |
| F3 ROA en hausse | ROA 2025 (F1) vs ROA 2024 = 8 349,0 / 52 566,5 | 0,1838 | 0,1588 | **1** |
| F4 Cash-flow opérationnel > résultat net | CFO 13 826,5 vs résultat net 10 213,0 | 13 826,5000 | 10 213,0000 | **1** |
| F5 Dette long terme / actif en baisse | 2 709,0 / 55 576,8 vs 3 677,3 / 52 566,5 | 0,0487 | 0,0700 | **1** |
| F6 Ratio de liquidité courante en hausse | 30 240,5 / 24 439,4 vs 30 357,2 / 20 049,5 | 1,2374 | 1,5141 | **0** |
| F7 Pas d'émission d'actions nouvelles | actions 385,4 vs 393,3 | 385,4 | 393,3 | **1** |
| F8 Marge brute en hausse | 16 931,4 / 32 667,3 vs 14 283,8 / 28 262,9 | 0,5183 | 0,5054 | **1** |
| F9 Rotation de l'actif en hausse | 32 667,3 / 55 576,8 vs 28 262,9 / 52 566,5 | 0,5878 | 0,5377 | **1** |

Total à la main, actif de clôture (indicatif) : **8/9**.

**F-score de RÉFÉRENCE (règle ajoutée, remplace la clôture ci-dessus comme calcul principal de P4) : actif D'OUVERTURE, convention Piotroski originale**

ATO 2025 (actif total à l'ouverture de FY2025, = actif de clôture FY2024) = 52 566,5 — déjà relevé à la main ci-dessus. ATO 2024 (actif total à l'ouverture de FY2024, = actif de clôture FY2023) = 43 078,6 : non relevé à la main pour ce complément, source pipeline/ESEF (déjà recoupé pour FY2025 et FY2024 ci-dessus).

| Test | Actifs utilisés (ATO N / ATO N−1) | Valeur N | Valeur N−1 | Point | Point clôture (indicatif) | Change ? |
|---|---|---|---|---|---|---|
| F1 ROA > 0 | 52 566,5 / 43 078,6 | 0,1943 | — | **1** | 1 | non |
| F3 ROA en hausse | 52 566,5 / 43 078,6 | 0,1943 | 0,1938 | **1** | 1 | non |
| F5 Dette long terme / actif en baisse | 52 566,5 / 43 078,6 | 0,0515 | 0,0854 | **1** | 1 | non |
| F9 Rotation de l'actif en hausse | 52 566,5 / 43 078,6 | 0,6214 | 0,6561 | **0** | 1 | **oui** |

**Score de référence (actif d'ouverture) : 7/9** contre 8/9 en clôture (indicatif). Pipeline (valeurs XBRL, même convention) : **7/9** → identique ✅. Seuil P4 : ≥ 6 → ✅.

**Z''-score (FY2025), calcul ligne par ligne sur les valeurs publiées**

- X1 = BFR / actif total = (30 240,5 − 24 439,4) / 55 576,8 = **0,104380**
- X2 = réserves / actif total = 16 534,8 / 55 576,8 = **0,297513**
- X3 = EBIT / actif total = 12 054,0 / 55 576,8 = **0,216889**
- X4 = capitaux propres / dettes totales = 24 185,0 / (55 576,8 − 24 185,0 = 31 391,8) = **0,770424**
- Z'' = 6,56 × 0,104380 + 3,26 × 0,297513 + 6,72 × 0,216889 + 1,05 × 0,770424
  = 0,684732 + 0,969891 + 1,457494 + 0,808945 = **3,9211**
- Pipeline (valeurs XBRL) : **3,9211** → identique ✅ ; zone **saine** (> 2,6).

**F5 avec / sans dettes locatives IFRS 16 dans la dette long terme**

Aucun concept IFRS séparé pour les dettes locatives non courantes n'est balisé par ASML Holding N.V. (`ifrs-full:NoncurrentLeaseLiabilities` absent) : comparaison impossible, hors risque pour ce calcul.
**Choix retenu (documenté dans les hypothèses, c.3)** : `dette_long_terme` EXCLUT les dettes locatives IFRS 16 (hypothèse #7 déjà en place). Le tableau ci-dessus montre que ce choix n'est pas neutre pour Hermès (F5 change) : c'est une raison supplémentaire de le documenter explicitement plutôt que de le laisser implicite. ASML ne permet pas la comparaison (donnée non balisée séparément).

## b.1) Distorsion connue du résultat net 2025 des grandes entreprises françaises

Source : [communiqué Hermès International, 12/02/2026](https://finance.hermes.com) — la « contribution exceptionnelle sur les bénéfices des grandes entreprises » (loi de finances 2025, France) est une surtaxe temporaire sur l'impôt sur les sociétés qui pèse sur le résultat net 2025 des grandes sociétés françaises. Résultat net part du groupe *ajusté* (hors contribution exceptionnelle) communiqué par Hermès : **4,86 Md€ (+5,5 %)**, contre **4 524 M€** *publié* (celui retenu par le pipeline, `ifrs-full:ProfitLossAttributableToOwnersOfParent`) — écart ≈ 336 M€. Le pipeline utilise le résultat PUBLIÉ (aucune correction), ce qui est cohérent avec la règle « donnée manquante = null, jamais d'estimation silencieuse » — mais cela biaise à la baisse le résultat net 2025 (et donc le F-score, le ROA, le PER) de toutes les grandes sociétés françaises assujetties, pas seulement Hermès. Aucune correction automatique n'est appliquée : si un ajustement est souhaité, il doit passer par `data/manual/{isin}.yaml` (mécanisme déjà prévu, prime sur les données automatiques), poste par poste, avec sa source vérifiée.


## c) Données introuvables, anomalies de source et hypothèses

### c.1 Par société

#### Hermès International
- Fondamentaux : ESEF : 6 rapport(s) retenu(s) ; source retenue : **ESEF** ; 7 exercices (2019, 2020, 2021, 2022, 2023, 2024, 2025).
- Rapport `969500Y4IJGHJE2MTJ13-2026-12-31-ESEF-FR-0` réintégré (métadonnée d'index corrigée) : Index filings.xbrl.org : period_end = 2026-12-31. Contenu vérifié le 2026-09-29 : fichier JSON nommé hermes-2025-12-31-1-fr.json, déposé le 2026-03-24 ; 267 faits sur la période 01/01/2025 → 31/12/2025, 148 sur 2024, bilans au 31/12/2024 et 31/12/2025 ; aucun fait sur 2026. C'est le rapport annuel FY2025 : seule la métadonnée d'index est fausse.
- Contrôles d'identité exécutés par exercice (règle ajoutée) : FY2019 3/4; FY2020 3/4; FY2021 3/4; FY2022 3/4; FY2023 3/4; FY2024 3/4; FY2025 3/4

#### ASML Holding
- Fondamentaux : ESEF : 5 rapport(s) retenu(s) ; source retenue : **ESEF** ; 7 exercices (2019, 2020, 2021, 2022, 2023, 2024, 2025).
- Retraitement nombre_actions FY2022 **non expliqué** (rapport d'origine `724500Y6DUVHQD6OXN27-2022-12-31-ESEF-NL-0` → comparatif écarté `724500Y6DUVHQD6OXN27-2025-12-31-ESEF-NL-0`) : comparatif 394 600 000,000 écarté (facteur observé 0.992205, aucun split yfinance correspondant), valeur d'origine **397 700 000,000 conservée**. Recoupement yfinance : 384 100 000 actions actuelles (3,5 % vs valeur conservée) — écart NON expliqué à ce stade (actuel, pas historique ; une émission/rachat réel n'est pas exclu, à vérifier).
- Contrôles d'identité exécutés par exercice (règle ajoutée) : FY2019 3/4; FY2020 4/4; FY2021 4/4; FY2022 4/4; FY2023 4/4; FY2024 4/4; FY2025 4/4
- Badge : somme partielle : composant(s) non balisé(s) ifrs-full:ShorttermBorrowings.

#### SAP
- Fondamentaux : ESEF introuvable (aucun rapport indexé pour ce LEI) ; source retenue : **yfinance** ; 4 exercices (2022, 2023, 2024, 2025).
- **P2 non recoupé** (règle ajoutée) : aucun rapport ESEF pour recouper l'EBIT yfinance → statut ramené à non évaluable (calculé sur les seules données fiables : — ; avec la donnée douteuse : ✅), verdict plafonné à SURVEILLANCE.
- Contrôles d'identité exécutés par exercice (règle ajoutée) : FY2022 3/4; FY2023 3/4; FY2024 3/4; FY2025 3/4

#### Atlas Copco A
- Fondamentaux : ESEF : 4 rapport(s) retenu(s) ; source retenue : **ESEF** ; 6 exercices (2020, 2021, 2022, 2023, 2024, 2025).
- Rapport écarté `213800T8PC8Q4FYJZR07-2021-12-31-ESEF-SE-1` : doublon de langue ; retenu : 213800T8PC8Q4FYJZR07-2021-12-31-ESEF-SE-0.
- Rapport écarté `213800T8PC8Q4FYJZR07-2022-12-31-ESEF-SE-0` : doublon de langue ; retenu : 213800T8PC8Q4FYJZR07-2022-12-31-ESEF-SE-1.
- Rapport écarté `213800T8PC8Q4FYJZR07-2023-12-31-ESEF-SE-0` : doublon de langue ; retenu : 213800T8PC8Q4FYJZR07-2023-12-31-ESEF-SE-1.
- Rapport écarté `213800T8PC8Q4FYJZR07-2024-12-31-ESEF-SE-0` : doublon de langue ; retenu : 213800T8PC8Q4FYJZR07-2024-12-31-ESEF-SE-1.
- **Données en retard** : dernier ESEF exploitable FY2024, attendu FY2025 (délai légal de 4 mois dépassé). Exercice(s) ajouté(s) depuis yfinance : 2025-12-31.
  - Contrôle des définitions sur l'exercice commun FY2024 (yfinance vs ESEF) : Chiffre d'affaires ESEF 176 771 000 000 / yfinance 176 771 000 000 (0,0 %); EBIT (résultat opérationnel) ESEF 38 166 000 000 / yfinance 37 951 000 000 (-0,6 % ⚠️); Résultat net part du groupe ESEF 29 782 000 000 / yfinance 29 782 000 000 (0,0 %); BNPA de base ESEF 6,11 / yfinance 6,11 (0,0 %); Actif total ESEF 208 538 000 000 / yfinance 208 538 000 000 (0,0 %).
  - ⚠️ EBIT (résultat opérationnel) : définition yfinance différente de l'ESEF → les valeurs FY2025 de ce poste ne sont pas strictement comparables à l'historique ESEF.
  - F-score : compare FY2025 (yfinance) à FY2024 (ESEF) : sources mixtes.
- **P4, fiabilité vérifiée** (règle ajoutée) : exercice le plus récent (yfinance) sans effet sur la conclusion : même statut avec les seules données ESEF (N−1 vs N−2). statut ⚪ n.é. gardé sans plafonnement (recalculé sur les seules années ESEF).
- Retraitement bnpa FY2021 : 14,890 → 3,720 (facteur 4.002688) (rapport d'origine `213800T8PC8Q4FYJZR07-2021-12-31-ESEF-SE-0` → comparatif retraitant `213800T8PC8Q4FYJZR07-2022-12-31-ESEF-SE-1`) : expliqué par un split yfinance.
- BNPA/actions ajustés du split yfinance : bnpa FY2020 12,160 → 3,040 (2022-05-13 ×4).
- Contrôles d'identité exécutés par exercice (règle ajoutée) : FY2020 3/4; FY2021 3/4; FY2022 3/4; FY2023 3/4; FY2024 3/4; FY2025 3/4
- Données introuvables (null + badge « indisponible ») : Dette long terme (FY2020, FY2021, FY2022, FY2023, FY2024); Dette court terme (FY2020, FY2021, FY2022, FY2023, FY2024); Nombre d'actions (FY2020, FY2021, FY2022, FY2023, FY2024)

#### Boliden
- Fondamentaux : ESEF : 4 rapport(s) retenu(s) ; source retenue : **ESEF** ; 6 exercices (2020, 2021, 2022, 2023, 2024, 2025).
- Rapport écarté `21380059QU7IM1ONDJ56-2023-12-31-ESEF-NO-0` : même rapport déposé dans un autre pays (NO, double cotation) ; retenu : 21380059QU7IM1ONDJ56-2023-12-31-ESEF-SE-0.
- Rapport écarté `21380059QU7IM1ONDJ56-2024-12-31-ESEF-NO-0` : même rapport déposé dans un autre pays (NO, double cotation) ; retenu : 21380059QU7IM1ONDJ56-2024-12-31-ESEF-SE-0.
- **Données en retard** : dernier ESEF exploitable FY2024, attendu FY2025 (délai légal de 4 mois dépassé). Exercice(s) ajouté(s) depuis yfinance : 2025-12-31.
  - Contrôle des définitions sur l'exercice commun FY2024 (yfinance vs ESEF) : Chiffre d'affaires ESEF 89 207 000 000 / yfinance 89 207 000 000 (0,0 %); EBIT (résultat opérationnel) ESEF 13 692 000 000 / yfinance 10 071 000 000 (-26,4 % ⚠️); Résultat net part du groupe ESEF 10 022 000 000 / yfinance 10 022 000 000 (0,0 %); BNPA de base ESEF 36,65 / yfinance 36,65 (0,0 %); Actif total ESEF 116 192 000 000 / yfinance 116 192 000 000 (0,0 %).
  - ⚠️ EBIT (résultat opérationnel) : définition yfinance différente de l'ESEF → les valeurs FY2025 de ce poste ne sont pas strictement comparables à l'historique ESEF.
  - F-score : compare FY2025 (yfinance) à FY2024 (ESEF) : sources mixtes.
- **P2, fiabilité vérifiée** (règle ajoutée) : écart EBIT yfinance/ESEF de -26% sur l'exercice commun FY2024 (seuil 5%) — dépend d'une donnée non recoupée (yfinance FY2025) — sans effet sur la conclusion : même statut avec les seules données ESEF fiables. statut ❌ gardé sans plafonnement (recalculé sur les seules données ESEF fiables).
- **P4 dépend d'une donnée non recoupée** (règle ajoutée) : la conclusion dépend d'une donnée non recoupée (yfinance FY2025) : données fiables seules (N−1 vs N−2, exercice plus ancien, ne prouve pas que yfinance est faux) = ok ; avec l'exercice yfinance = ne. → statut ramené à non évaluable (avec l'exercice yfinance : ⚪ n.é. 5/8 ; sur les seules années ESEF 2023-12-31 → 2024-12-31 : ✅ 8/9), verdict plafonné à SURVEILLANCE.
- Retraitement nombre_actions FY2021 **non expliqué** (rapport d'origine `21380059QU7IM1ONDJ56-2021-12-31-ESEF-SE-0` → comparatif écarté `21380059QU7IM1ONDJ56-2022-12-31-ESEF-SE-0`) : comparatif 2 735 111,000 écarté (facteur observé 0.01, aucun split yfinance correspondant), valeur d'origine **273 511 169,000 conservée**. Recoupement yfinance : 283 962 452 actions actuelles (-3,7 % vs valeur conservée) — écart NON expliqué à ce stade (actuel, pas historique ; une émission/rachat réel n'est pas exclu, à vérifier).
- Contrôles d'identité exécutés par exercice (règle ajoutée) : FY2020 3/4; FY2021 3/4; FY2022 3/4; FY2023 3/4; FY2024 3/4; FY2025 3/4
- Données introuvables (null + badge « indisponible ») : BNPA de base (FY2020)
- Badge : somme partielle : composant(s) non balisé(s) ifrs-full:PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities.
- Badge : somme partielle : composant(s) non balisé(s) ifrs-full:ShorttermBorrowings.

#### Brunello Cucinelli
- Fondamentaux : ESEF : 4 rapport(s) retenu(s), 1 exclu(s) pour incohérence ; source retenue : **ESEF** ; 6 exercices (2020, 2021, 2022, 2023, 2024, 2025).
- Rapport écarté `5493003CX2RZ0FOBH256-2025-12-31-ESEF-IT-0` : incohérent avec le rapport précédent (erreur de balisage probable).
- **Erreur de balisage de l'émetteur** : `5493003CX2RZ0FOBH256-2025-12-31-ESEF-IT-0` donne pour chiffre_affaires FY2024 188 000 contre 1 278 540 000 dans `5493003CX2RZ0FOBH256-2024-12-31-ESEF-IT-0` → rapport exclu, exercice remplacé par yfinance (badge).
- **Données en retard** : dernier ESEF exploitable FY2024, attendu FY2025 (délai légal de 4 mois dépassé). Exercice(s) ajouté(s) depuis yfinance : 2025-12-31.
  - Contrôle des définitions sur l'exercice commun FY2024 (yfinance vs ESEF) : Chiffre d'affaires ESEF 1 278 540 000 / yfinance 1 278 540 000 (0,0 %); EBIT (résultat opérationnel) ESEF 211 671 000 / yfinance 219 660 000 (3,8 % ⚠️); Résultat net part du groupe ESEF 119 478 000 / yfinance 119 478 000 (0,0 %); BNPA de base ESEF 1,76 / yfinance 1,76 (0,0 %); Actif total ESEF 1 744 893 000 / yfinance 1 744 893 000 (0,0 %).
  - ⚠️ EBIT (résultat opérationnel) : définition yfinance différente de l'ESEF → les valeurs FY2025 de ce poste ne sont pas strictement comparables à l'historique ESEF.
  - F-score : compare FY2025 (yfinance) à FY2024 (ESEF) : sources mixtes.
- **P4 dépend d'une donnée non recoupée** (règle ajoutée) : la conclusion dépend d'une donnée non recoupée (yfinance FY2025) : données fiables seules (N−1 vs N−2, exercice plus ancien, ne prouve pas que yfinance est faux) = ok ; avec l'exercice yfinance = ne. → statut ramené à non évaluable (avec l'exercice yfinance : ⚪ n.é. 5/8 ; sur les seules années ESEF 2023-12-31 → 2024-12-31 : ✅ 6/8), verdict plafonné à SURVEILLANCE.
- Contrôles d'identité exécutés par exercice (règle ajoutée) : FY2020 2/4; FY2021 2/4; FY2022 2/4; FY2023 2/4; FY2024 2/4; FY2025 3/4
- **Contrôles d'identité : contrôle partiel** (< 3/4 concluant) : FY2020 (2/4), FY2021 (2/4), FY2022 (2/4), FY2023 (2/4), FY2024 (2/4).
- Données introuvables (null + badge « indisponible ») : Marge brute (FY2020, FY2021, FY2022, FY2023, FY2024); Réserves (résultats non distribués) (FY2020, FY2021, FY2022, FY2023, FY2024); Nombre d'actions (FY2020, FY2021, FY2022, FY2023, FY2024)
- Badge : actif courant calculé (actif total − actif non courant).
- Badge : dettes courantes calculées (dettes totales − passifs non courants).
- Badge : somme partielle : composant(s) non balisé(s) ifrs-full:CurrentPortionOfLongtermBorrowings.

#### Thermador Groupe
- Fondamentaux : ESEF : 4 rapport(s) retenu(s) ; source retenue : **ESEF** ; 7 exercices (2019, 2020, 2021, 2022, 2023, 2024, 2025).
- Rapport écarté `969500SSIGMAGT008F11-2022-12-31-ESEF-FR-0` : rapport non converti par filings.xbrl.org (paquet ZIP seul) : l'exercice n'est connu que par le comparatif du rapport suivant.
- Contrôles d'identité exécutés par exercice (règle ajoutée) : FY2019 2/4; FY2020 2/4; FY2021 2/4; FY2022 2/4; FY2023 2/4; FY2024 2/4; FY2025 2/4
- **Contrôles d'identité : contrôle partiel** (< 3/4 concluant) : FY2019 (2/4), FY2020 (2/4), FY2021 (2/4), FY2022 (2/4), FY2023 (2/4), FY2024 (2/4), FY2025 (2/4).
- Données introuvables (null + badge « indisponible ») : Marge brute (FY2020, FY2021, FY2022, FY2023, FY2024, FY2025); Réserves (résultats non distribués) (FY2020, FY2021)
- Badge : concept propre à la société (Bilan : lignes « Réserves consolidées » + « Résultat de l'exercice - Part du groupe » (ESEF 2025)).
- Badge : concept propre à la société (Compte de résultat : ligne « RÉSULTAT OPÉRATIONNEL » (ESEF 2021)).
- Badge : concept propre à la société (NON VÉRIFIÉ contre le rapport publié dans cette session (pas d'accès Internet) — à la différence des deux entrées ci-dessus. Nom du concept auto-descriptif (« sorties pour l'acquisition d'immobilisations corporelles et incorporelles »), cohérent avec la définition capex de l'hypothèse #7 et avec le tableau des flux de trésorerie (valeurs négatives, ex. -12 221 000 € en FY2021, cohérentes avec un flux sortant). À confirmer contre le rapport annuel imprimé avant de considérer la vérification complète (item 29).).
- Badge : somme partielle : composant(s) non balisé(s) ifrs-full:ShorttermBorrowings.

#### Sidetrade
- Fondamentaux : ESEF introuvable (aucun rapport indexé pour ce LEI) ; source retenue : **yfinance** ; 4 exercices (2022, 2023, 2024, 2025).
- **P2 non recoupé** (règle ajoutée) : aucun rapport ESEF pour recouper l'EBIT yfinance → statut ramené à non évaluable (calculé sur les seules données fiables : — ; avec la donnée douteuse : ❌), verdict plafonné à SURVEILLANCE.
- Contrôles d'identité exécutés par exercice (règle ajoutée) : FY2022 3/4; FY2023 3/4; FY2024 3/4; FY2025 3/4
- Données introuvables (null + badge « indisponible ») : Dette court terme (FY2024); Réserves (résultats non distribués) (FY2025)

#### Mycronic
- Fondamentaux : ESEF : 4 rapport(s) retenu(s) ; source retenue : **ESEF** ; 6 exercices (2020, 2021, 2022, 2023, 2024, 2025).
- **Données en retard** : dernier ESEF exploitable FY2024, attendu FY2025 (délai légal de 4 mois dépassé). Exercice(s) ajouté(s) depuis yfinance : 2025-12-31.
  - Contrôle des définitions sur l'exercice commun FY2024 (yfinance vs ESEF) : Chiffre d'affaires ESEF 7 057 000 000 / yfinance 7 057 000 000 (0,0 %); EBIT (résultat opérationnel) ESEF 2 021 000 000 / yfinance 2 014 000 000 (-0,3 %); Résultat net part du groupe ESEF 1 683 000 000 / yfinance 1 683 000 000 (0,0 %); BNPA de base ESEF 8,62 / yfinance 8,62 (-0,1 %); Actif total ESEF 10 412 000 000 / yfinance 10 412 000 000 (0,0 %).
  - F-score : compare FY2025 (yfinance) à FY2024 (ESEF) : sources mixtes.
- **P4 dépend d'une donnée non recoupée** (règle ajoutée) : la conclusion dépend d'une donnée non recoupée (yfinance FY2025) : données fiables seules (N−1 vs N−2, exercice plus ancien, ne prouve pas que yfinance est faux) = ok ; avec l'exercice yfinance = ko. → statut ramené à non évaluable (avec l'exercice yfinance : ❌ 3/7 ; sur les seules années ESEF 2023-12-31 → 2024-12-31 : ✅ 7/7), verdict plafonné à SURVEILLANCE.
**Mycronic — détail des 9 tests F-score côte à côte, exercice FY2025 (yfinance) vs FY2024 (ESEF), convention ouverture** (item 33)

| Test | Poste(s) | Valeur FY2025 | Valeur FY2024 | Point | Source FY2025 | Source FY2024 | Dépend d'une donnée non recoupée ? |
|---|---|---|---|---|---|---|---|
| F1 ROA > 0 | resultat_net | 0,1498 | — | 1 | yfinance | ESEF | oui |
| F2 Cash-flow opérationnel > 0 | cash_flow_operationnel | 1 407 000 000,0000 | — | 1 | yfinance | ESEF | oui |
| F3 ROA en hausse | resultat_net | 0,1498 | 0,2018 | 0 | yfinance | ESEF | oui |
| F4 Cash-flow opérationnel > résultat net | cash_flow_operationnel, resultat_net | 1 407 000 000,0000 | 1 560 000 000,0000 | 0 | yfinance; yfinance | ESEF; ESEF | oui |
| F5 Dette long terme / actif en baisse | dette_long_terme, actif_total | 0,0012 | — | None | yfinance; yfinance | —; ESEF | oui |
| F6 Ratio de liquidité courante en hausse | actif_courant, dettes_courantes | 2,3049 | 2,1463 | 1 | yfinance; yfinance | ESEF; ESEF | oui |
| F7 Pas d'émission d'actions nouvelles | nombre_actions | 195 833 018,0000 | — | None | yfinance | — | oui |
| F8 Marge brute en hausse | marge_brute, chiffre_affaires | 0,5244 | 0,5270 | 0 | yfinance; yfinance | ESEF; ESEF | oui |
| F9 Rotation de l'actif en hausse | chiffre_affaires | 0,7624 | 0,8462 | 0 | yfinance | ESEF | oui |

**Contexte marge EBIT (hors F-score, pour juger réel vs définition)** : FY2024 (ESEF) 28,6 % → FY2025 (yfinance) 25,4 %. Sur l'exercice commun FY2024, l'EBIT yfinance ne s'écartait que de -0,3 % de l'ESEF (contrôle « données en retard », c.1) : les définitions concordent pour cette société (à la différence de Boliden, écart -26 %) — **la baisse de marge FY2025 est donc probablement une évolution réelle de l'activité, pas un artefact de définition**, sans que cela ne change le statut « dépend d'une donnée non recoupée » du F-score (la fiabilité de la DÉFINITION n'est pas la même chose que la fiabilité de la VALEUR exacte d'un exercice non encore confirmé par un rapport ESEF).


Sur les 7 tests disponibles avec l'exercice yfinance, **7 dépendent de FY2025 (yfinance)** — c'est-à-dire TOUS (FY2025 est 100 % yfinance pour Mycronic, aucun poste ESEF cette année-là : tout test utilisant l'exercice N en dépend). F5 et F7 sont indisponibles pour des raisons de données ESEF antérieures (dette long terme et nombre d'actions non balisés sur plusieurs exercices), sans rapport avec yfinance.
Sur les seules années ESEF (FY2024 vs FY2023) : **7/7**, statut ✅ — très différent du 3/7 avec l'exercice yfinance : la conclusion dépend d'une donnée non recoupée (yfinance FY2025). Le calcul ESEF seul porte sur un exercice PLUS ANCIEN (FY2024) : il ne prouve pas que la donnée yfinance FY2025 est fausse, seulement que la conclusion en dépend (item 32).

- BNPA/actions ajustés du split yfinance : bnpa FY2022 7,590 → 3,795 (2025-06-03 ×2).
- BNPA/actions ajustés du split yfinance : bnpa FY2021 8,480 → 4,240 (2025-06-03 ×2).
- BNPA/actions ajustés du split yfinance : bnpa FY2023 10,220 → 5,110 (2025-06-03 ×2).
- BNPA/actions ajustés du split yfinance : bnpa FY2024 17,250 → 8,625 (2025-06-03 ×2).
- Contrôles d'identité exécutés par exercice (règle ajoutée) : FY2020 3/4; FY2021 3/4; FY2022 3/4; FY2023 3/4; FY2024 3/4; FY2025 3/4
- Données introuvables (null + badge « indisponible ») : BNPA de base (FY2020); Dette long terme (FY2022, FY2023, FY2024); Dette court terme (FY2020, FY2021, FY2022, FY2023, FY2024); Nombre d'actions (FY2020, FY2021, FY2022, FY2023, FY2024)

#### Valneva
- Fondamentaux : ESEF : 5 rapport(s) retenu(s) ; source retenue : **ESEF** ; 7 exercices (2019, 2020, 2021, 2022, 2023, 2024, 2025).
- Contrôles d'identité exécutés par exercice (règle ajoutée) : FY2019 2/4; FY2020 3/4; FY2021 3/4; FY2022 3/4; FY2023 3/4; FY2024 3/4; FY2025 3/4
- **Contrôle d'identité non concluant (règle ajoutée)** : FY2022 : BNPA × actions DE CLÔTURE (pas de nombre pondéré balisé) = -1.71576e+08 ≠ résultat net -1.43279e+08 (écart -20%) — non concluant, pas de quarantaine : l'écart peut venir du dénominateur (clôture, pas moyen pondéré), pas des données.
- **Contrôles d'identité : contrôle partiel** (< 3/4 concluant) : FY2019 (2/4).
- Données introuvables (null + badge « indisponible ») : Nombre d'actions (FY2023, FY2024, FY2025)
- Badge : somme partielle : composant(s) non balisé(s) ifrs-full:ShorttermBorrowings.

### c.2 Sources inaccessibles ou limitées

- **Stooq** (secours des cours) : inutilisable en automatique depuis ce Mac, le site exige une vérification JavaScript anti-robot. Non contournée. yfinance a fourni tous les cours.
- **SAP** (Allemagne) : LEI trouvé, aucun rapport sur filings.xbrl.org → repli yfinance (4 exercices).
- **Sidetrade** (Euronext Growth) : aucun rapport ESEF (pas d'obligation) → repli yfinance (4 exercices).
- **Suède (Atlas Copco, Boliden, Mycronic)** : rapports FY2025 non indexés sur filings.xbrl.org au 2026-09-29 → FY2025 pris dans yfinance (badge « données en retard »).
- **Thermador FY2022** : filings.xbrl.org n'a pas converti le rapport (paquet ZIP seul) ; les chiffres FY2022 viennent du comparatif du rapport FY2023.
- **Brunello Cucinelli FY2025** : dimensions inversées dans le balisage (totaux balisés « parties liées »), BNPA balisé 1 986,5 € au lieu d'environ 1,99 € (erreur ×1000) → rapport exclu, FY2025 pris dans yfinance. **Vérification demandée : le contrôle d'identité (c.1, règle ajoutée) aurait-il détecté cette erreur SEUL, sans le contrôle de cohérence CA existant ?** Non — vérifié sur le rapport écarté `5493003CX2RZ0FOBH256-2025-12-31-ESEF-IT-0` : à cause de l'inversion de dimensions, `marge_brute`, `ebit` et `nombre_actions` n'y sont PAS balisés sans dimension (donc absents, pas juste faux) — seuls `chiffre_affaires` (188 000, lui aussi faux) et `bnpa` (1 986,5) le sont. Le contrôle BNPA × actions ≈ résultat net ne peut pas s'exécuter sans `nombre_actions` (non balisé pour Cucinelli, cf. ci-dessus) ; marge brute ≤ CA et la borne de marge EBIT ne peuvent pas s'exécuter sans `marge_brute`/`ebit` (absents dans ce rapport). C'est uniquement le contrôle de cohérence CA PRÉEXISTANT (`rapports_incoherents`, comparatif N−1 entre rapports successifs, seuil 50 %) qui exclut ce rapport avant que les contrôles d'identité ne voient ses valeurs. Les deux mécanismes sont complémentaires mais pas redondants ici. Nuance : sur la série RETENUE (rapports 2020-2024, après exclusion du rapport corrompu), Cucinelli obtient 2/4 contrôles exécutés par exercice (c.1), pas 0/4 — le cas « 0/4, non contrôlé » décrit un exercice hypothétique où même ces 2 contrôles manqueraient de données, pas la situation réelle de ce panel.
- **Nombre d'actions** : non balisé par Atlas Copco, Brunello Cucinelli, Mycronic (tous exercices ESEF) et Valneva (2023-2025) → F7 (émission d'actions) indisponible. Pas de dérivation « résultat / BNPA » : l'arrondi du BNPA à 2 décimales créerait de fausses émissions.
- **Boliden — retraitement « nombre d'actions ÷ 100 sans split »** (poste `nombre_actions`, exercice FY2021) : le rapport `21380059QU7IM1ONDJ56-2021-12-31-ESEF-SE-0` (déposé 2022-03-22) publie 273 511 169 actions (`ifrs-full:NumberOfSharesOutstanding`) au 31/12/2021 ; le comparatif du même poste dans le rapport suivant `21380059QU7IM1ONDJ56-2022-12-31-ESEF-SE-0` (déposé 2023-05-09) donne 2 735 111 pour la même date (facteur observé 0,01, exactement ÷ 100). **Hypothèse** : erreur de balisage dans le comparatif du rapport FY2022 (confusion d'échelle iXBRL probable), pas un évènement capitalistique réel. Correction appliquée (règle ajoutée, item 15/19) : la valeur D'ORIGINE du rapport FY2021 (273 511 169) est conservée, le comparatif ÷ 100 est écarté — cette règle ne s'applique qu'à bnpa/nombre_actions (jamais à CA, EBIT, actifs, voir item 19). Conséquence : le contrôle d'identité BNPA × actions ≈ résultat net (c.1) ne trouve plus d'écart et ne quarantine plus rien pour FY2021 (31,81 × 273 511 169 ≈ 8,701 Md SEK ≈ résultat net publié 8,701 Md SEK, écart < 0,01 %).
  - **Vérification demandée (item 20)** — y a-t-il eu une émission d'actions réelle entre FY2021 et FY2025 ? Historique du nombre d'actions dans les rapports ESEF successifs (`ifrs-full:NumberOfSharesOutstanding`, exercice propre à chaque rapport, pas les comparatifs suspects) : FY2021 = 273 511 169 ; FY2022 = 273 511 169 (rapport FY2022, fait « 2023-01-01 », confirmant que 273 511 169 — pas 2 735 111 — est la bonne valeur début 2022) ; FY2023 = 273 503 169 (-8 000) ; FY2024 = 273 471 169 (-32 000). **Aucune émission dans les rapports ESEF publiés (FY2021-FY2024) : au contraire, une légère réduction nette (-40 000 actions, -0,015 %), cohérente avec des rachats, pas des émissions.** Le nombre d'actions yfinance utilisé pour FY2025 (retard ESEF) est en revanche sensiblement plus élevé : 284 225 454 (yfinance, poste `nombre_actions`, ligne « Share Issued ») et 283 962 452 (`sharesOutstanding` yfinance, utilisé pour le recoupement en c.1) — soit environ +10,75 M actions (+3,9 %) par rapport à FY2024 ESEF. **Je ne peux pas confirmer si c'est une émission réelle en 2025 (le rapport ESEF FY2025 n'est pas encore publié) ou un artefact de source yfinance** : signalé comme tel, badge « écart NON expliqué » (corrigé, la mention précédente « écart normal » n'était pas vérifiée). Sans lien avec le retraitement ÷ 100 (déjà écarté ci-dessus, qui concernait le comparatif FY2021 dans le rapport FY2022, pas l'écart FY2024→FY2025). Impact sur F7 (émission d'actions, P4) : déjà neutralisé par la règle existante « F7 comparé seulement si même concept » (`ifrs-full:NumberOfSharesOutstanding` ESEF vs `yfinance:Share Issued`, concepts différents) — F7 est exclu (non disponible), pas faussé.
- **Certificats SSL** : le Python de python.org n'a pas de magasin de certificats (dossier `etc/openssl` vide). Aucun proxy : la chaîne GlobalSign reçue est authentique. Le pipeline utilise `certifi` ; `verify=False` n'est jamais utilisé. Correctif système facultatif : lancer « Install Certificates.command » dans le dossier Python 3.14.

### c.3 Hypothèses prises (absentes de methode.md, à valider)

1. Clé interne = LEI ; correspondance ISIN → LEI par `isin_lei.csv` puis GLEIF, jamais par nom.
2. Exercice d'un rapport ESEF = période annuelle la plus fréquente de ses faits (pas la métadonnée d'index). Rapport dont l'index diffère des faits : exclu, sauf explication dans `esef_overrides.yaml` (cas Hermès « 2026 » = FY2025).
3. Doublons : un rapport par exercice ; priorité au pays de dépôt principal, puis au dépôt le plus récent, puis à la langue (fr, en). Les chiffres clés des doublons sont comparés (tous identiques ici).
4. Chiffres de chaque exercice : rapport le plus récent qui les contient (comparatif retraité), écart avec l'original signalé au-delà de 0,5 %.
5. Contrôle de cohérence : comparatif N−1 du CA ou de l'actif total différent de plus de 50 % du chiffre publié l'année précédente → rapport exclu (erreur de balisage). Seuil dans config.yaml.
6. Délai légal de publication de 4 mois (directive Transparence) pour détecter les « données en retard ».
7. Résultat net = part du groupe ; BNPA = de base ; capex = acquisitions d'immobilisations corporelles + incorporelles (somme partielle signalée) ; dette LT = emprunts non courants hors dettes locatives IFRS 16 ; dette CT = emprunts courants hors dettes locatives ; capitaux propres = totaux (minoritaires inclus).
8. « Réserves » du Z'' = résultats non distribués au sens d'Altman, résultat de l'exercice inclus (ifrs-full:RetainedEarnings ou composantes équivalentes). Extensions « maison » d'Hermès et de Thermador utilisées en dernier recours, libellés vérifiés dans leurs rapports.
9. Dettes totales absentes du balisage = actif total − capitaux propres (identité comptable, badge). Actif et passif courants absents = total − non courant (badge).
10. F-score : bilans de clôture N et N−1 (Piotroski utilise l'actif d'ouverture) ; « en baisse / en hausse » au sens strict ; F7 = nombre d'actions N ≤ N−1, comparé seulement si même concept ; test indisponible exclu, statut ✅ si score ≥ 6, ❌ si même avec les tests manquants < 6, sinon n.é.
11. P2 : marge EBIT et marge nette du dernier exercice ; tendance = pente de la marge EBIT (points/an) sur la fenêtre ; mode relatif = 3e quartile (interpolation linéaire) de la marge EBIT du dernier exercice.
12. P6 : 3 mois = 63 séances ; montant = volume × clôture × taux BCE du jour (dernier fixing antérieur les jours sans fixing BCE).
13. Percentile = (inférieurs + ½ égalités) / (n − 1) × 100 ; sous-score absent → poids renormalisés (badge).
14. Q2 non interprétable si résultat net ≤ 0 ; Q4 = écart-type (population) des 5 dernières marges EBIT.
15. V1 : EV = capitalisation + dette LT + dette CT − trésorerie ; capitalisation = cours × actions de clôture du dernier exercice (yfinance `sharesOutstanding` si absentes, badge).
16. M1 = clôture il y a 21 séances / clôture il y a 252 séances − 1 ; M2 = rendement 126 séances de l'action / rendement de l'indice ^STOXX − 1 ; cours hors dividendes (indice de prix).
17. Timing : RSI de Wilder ; MM200 « en hausse sur 1 mois » = MM200 du jour > MM200 d'il y a 21 séances ; cours > MM200 sans repli exploitable (RSI < 35 et loin de la MM50) → 🟡.
18. Justification : critère de porte le plus juste = plus petite marge relative au seuil (un ❌ est prioritaire), meilleur et pire sous-score.
19. Secteur = secteur yfinance (classification Morningstar), faute de source sectorielle européenne gratuite.
20. Verdict PROVISOIRE (règle ajoutée) : univers < `qvm.min_univers_verdict` (30) → un ACHAT ou un REJET déterminé par le score devient PROVISOIRE (verdict qu'il serait affiché) ; un REJET dû à la porte ❌ n'est jamais concerné, ni un plafond SURVEILLANCE déjà appliqué (porte non évaluable, score < seuil d'achat). Seuil arbitraire (aucune référence dans methode.md), à valider.
21. P4 F-score partiel : affichage « x/y tests évaluables » (x = points obtenus, y = tests disponibles).
22. P2 fiabilité (règle ajoutée, corrigée) : dernier exercice 100 % yfinance (aucun ESEF) → « non recoupé », non évaluable (pas de repli fiable possible). Écart EBIT yfinance/ESEF > 5 % sur l'exercice commun (cas « données en retard ») : P2 est RECALCULÉ sur les seules données ESEF fiables (exercice yfinance exclu) et comparé au calcul complet ; même conclusion (même statut) → gardée SANS plafonnement (ex. Boliden, ❌ sur sa marge ESEF FY2024, 15,3 %) ; conclusion différente → « dépend d'une donnée non recoupée » (renommé depuis « non fiable », item 32 : le calcul ESEF seul porte sur un exercice plus ancien, il ne prouve pas que yfinance est faux), non évaluable. Seuil de 5 % arbitraire (aucune référence dans methode.md).
23. Contrôles d'identité (règle ajoutée, corrigés) : BNPA × actions moyen pondéré ≈ résultat net (poste auxiliaire `nombre_actions_moyen_pondere`, balisé seulement par ASML dans ce panel) et actif total ≈ dettes totales + capitaux propres, tolérance ± 15 % (non spécifiée dans la demande pour la 2e identité, réutilisée par simplicité) ; marge brute ≤ CA ; marge EBIT ∈ [-100 %, 100 %]. Contrôle exécuté sur les vraies clôtures d'exercice seulement (dates_clotures), pas sur les faits isolés à une autre date (ex. solde d'ouverture retraité IFRS 16 « au 1er janvier »). Sans nombre d'actions moyen pondéré balisé (Boliden, Valneva, Cucinelli...), le contrôle BNPA × actions est « non concluant » (calculé mais jamais de quarantaine) plutôt que d'utiliser le nombre d'actions DE CLÔTURE, structurellement différent du dénominateur du BNPA (IAS 33) en cas d'émission/rachat en cours d'exercice (cas Valneva FY2022, écart -20 % non concluant). En cas d'échec sur l'identité actif/passif (2 postes), on ne peut pas déterminer lequel est fautif : les deux sont mis en quarantaine par convention, capitaux propres sert de référence. Compteur « contrôles exécutés x/4 » par société et exercice (c.1) ; badge « non contrôlé » à 0/4.
24. Retraitement non expliqué de BNPA/nombre_actions (règle ajoutée, corrigée) : un comparatif retraité sans split yfinance correspondant n'est PLUS appliqué — la valeur D'ORIGINE du rapport de l'exercice est conservée (ex. Boliden FY2021 nombre_actions : 273 511 169 conservé, pas le comparatif ÷100 du rapport FY2022), recoupée pour information avec le nombre d'actions yfinance actuel (badge, écart NON expliqué à ce stade — voir Boliden en c.2, item 20). Auparavant, le pipeline gardait le comparatif retraité par défaut (philosophie générale « dernier rapport fait foi »), ce qui retenait une valeur visiblement fausse pour ce cas précis. **Portée limitée (item 19)** : cette règle ne s'applique QU'aux postes par action et nombre d'actions (la boucle de `ajuster_splits`, voir son docstring). Le chiffre d'affaires, l'EBIT, les actifs (flux et stocks) restent gouvernés par `fusionner_rapports` (rapport le plus récent = référence, y compris pour un écart légitime important — activités abandonnées, changement de norme) ; seul un échec du contrôle de cohérence > 50 % (`rapports_incoherents`) exclut alors le rapport entier, jamais une correction poste par poste. Testé (test_ca_ebit_non_revertis_meme_si_ecart_important).
25. P4 fiabilité (règle ajoutée, même principe que P2) : pour les sociétés à données en retard (dernier exercice yfinance, ex. Mycronic, Atlas Copco, Boliden), P4 est recalculé sur les seules années ESEF (N−1 vs N−2) et comparé au calcul avec l'exercice yfinance. Même conclusion → calcul fiable gardé sans plafonnement (Atlas Copco). Conclusion différente → « dépend d'une donnée non recoupée » (renommé depuis « non fiable », item 32 : le F-score ESEF seul porte sur N−1/N−2, des exercices plus anciens que l'exercice yfinance contesté — il ne prouve pas que yfinance est faux), non évaluable, verdict plafonné à SURVEILLANCE — cas marquants : Mycronic (3/7 KO avec yfinance vs 7/7 OK sur les seules données ESEF : la totalité des tests disponibles avec yfinance porte sur un exercice 100 % yfinance, détail en c.1) et Boliden (5/8 n.é. avec yfinance vs 8/9 OK en ESEF seul).
26. Contrôle partiel (règle ajoutée) : badge distinct de « non contrôlé » quand 0 < contrôles exécutés < `controles_identite.seuil_partiel` (3, PARAMÈTRE arbitraire).
27. P3 retour aux bénéfices (règle ajoutée) : BNPA de départ ≤ 0 (perte) mais dernier BNPA de la fenêtre > 0 → non évaluable (jamais ❌), CAGR indicatif affiché depuis la première année positive de la fenêtre (cas Cucinelli : perte Covid FY2020, CAGR indicatif calculé FY2021→FY2025). Le ❌ (CAGR non calculable) reste réservé aux sociétés encore déficitaires en fin de fenêtre (Valneva).
28. Référentiel comptable (item 24) : ESEF = IFRS toujours (réglementaire, aucune vérification requise). Repli yfinance : référentiel non garanti identique — signalé pour ASML (double cotation Nasdaq, 20-F réconcilié en US GAAP) bien que non utilisé ici (ASML dispose de 5 rapports ESEF, aucun repli yfinance pour ses fondamentaux). Chiffres US GAAP confirmés par le communiqué ASML du 28/01/2026 (source citée en §0).
29. REJET sur données non recoupées (règle ajoutée) : badge sur tout verdict REJET fondé sur une société 100 % yfinance (aucun rapport ESEF, ex. Sidetrade) — le rejet n'a pas pu être confirmé par une source indépendante.
30. F-score de référence (règle ajoutée, remplace l'ancien calcul par défaut) : l'actif D'OUVERTURE (convention Piotroski originale — à vérifier, certaines implémentations utilisent l'actif moyen) devient le calcul principal de P4 pour F1/F3/F5/F9 ; l'actif de clôture (ancien calcul par défaut) n'est plus qu'un affichage indicatif. Si l'actif d'ouverture de l'exercice N−1 (= actif de clôture de N−2) est indisponible, ces 4 tests sont non évaluables (pas de repli silencieux sur la clôture) : le F-score peut alors reposer sur moins de 9 tests, via le mécanisme déjà existant du score partiel.
31. cash_flow_operationnel : un seul concept mappé (`ifrs-full:CashFlowsFromUsedInOperatingActivities`, flux net APRÈS variation du BFR), jamais la ligne « avant variation du BFR » (vérifié : Hermès FY2025 distingue les deux, 5 607 M€ avant vs 5 374 M€ après, retenu). Testé (test_cfo_ne_prend_jamais_...).
32. F5 dettes locatives IFRS 16 : choix retenu = dette_long_terme les EXCLUT (hypothèse déjà en place, #7). Non neutre : pour Hermès, F5 change selon la convention (b, comparaison chiffrée). ASML ne permet pas la comparaison (aucun concept IFRS séparé balisé pour ses dettes locatives non courantes).
33. dette_long_terme (item 28) : `NoncurrentFinancialLiabilitiesAtAmortisedCost` / `OtherNoncurrentFinancialLiabilities` (Atlas Copco, Mycronic) délibérément NON mappés — rejetés par le contrôle yfinance Long Term Debt (écart systématique > 10 %, détail en d.2). F5 reste non évaluable pour ces exercices.
34. capex Thermador (item 29) : extension `thermador:OutflowsForTheAcquisitionOfTangibleAndIntangibleFixedAssets` ajoutée, libellé NON vérifié contre le rapport publié dans cette session (pas d'accès Internet, à la différence de `ebit`/`reserves` pour cette société). Signe inversé (valeur absolue) car le concept maison tague un flux sortant négatif, contrairement aux concepts génériques (magnitude positive) — testé.
35. marge_brute Valneva (item 30) : calcul de secours `chiffre_affaires − cout_des_ventes` (nouveau poste auxiliaire `cout_des_ventes` → `ifrs-full:CostOfSales`), badge « marge brute reconstituée ». N'affecte pas Cucinelli/Thermador (présentation par nature, aucun `CostOfSales` balisé, hypothèse déjà correcte).

### c.4 Journal du dernier run

- [AVERT] `213800T8PC8Q4FYJZR07` : données en retard : dernier ESEF 2024-12-31, attendu 2025-12-31 ; complété par yfinance (2025-12-31)
- [AVERT] `21380059QU7IM1ONDJ56` : données en retard : dernier ESEF 2024-12-31, attendu 2025-12-31 ; complété par yfinance (2025-12-31)
- [AVERT] `5493003CX2RZ0FOBH256` : rapport 5493003CX2RZ0FOBH256-2025-12-31-ESEF-IT-0 exclu : comparatif chiffre_affaires 2024-12-31 = 188000 contre 1.27854e+09 publié dans 5493003CX2RZ0FOBH256-2024-12-31-ESEF-IT-0
- [AVERT] `5493003CX2RZ0FOBH256` : données en retard : dernier ESEF 2024-12-31, attendu 2025-12-31 ; complété par yfinance (2025-12-31)
- [AVERT] `5493003CX2RZ0FOBH256` : contrôles d'identité FY2020 : contrôle partiel (2/4 < seuil 3)
- [AVERT] `5493003CX2RZ0FOBH256` : contrôles d'identité FY2021 : contrôle partiel (2/4 < seuil 3)
- [AVERT] `5493003CX2RZ0FOBH256` : contrôles d'identité FY2022 : contrôle partiel (2/4 < seuil 3)
- [AVERT] `5493003CX2RZ0FOBH256` : contrôles d'identité FY2023 : contrôle partiel (2/4 < seuil 3)
- [AVERT] `5493003CX2RZ0FOBH256` : contrôles d'identité FY2024 : contrôle partiel (2/4 < seuil 3)
- [AVERT] `969500SSIGMAGT008F11-2022-12-31-ESEF-FR-0` : rapport non converti par filings.xbrl.org (paquet ZIP seul, pas de xBRL-JSON) : exclu
- [AVERT] `969500SSIGMAGT008F11` : contrôles d'identité FY2019 : contrôle partiel (2/4 < seuil 3)
- [AVERT] `969500SSIGMAGT008F11` : contrôles d'identité FY2020 : contrôle partiel (2/4 < seuil 3)
- [AVERT] `969500SSIGMAGT008F11` : contrôles d'identité FY2021 : contrôle partiel (2/4 < seuil 3)
- [AVERT] `969500SSIGMAGT008F11` : contrôles d'identité FY2022 : contrôle partiel (2/4 < seuil 3)
- [AVERT] `969500SSIGMAGT008F11` : contrôles d'identité FY2023 : contrôle partiel (2/4 < seuil 3)
- [AVERT] `969500SSIGMAGT008F11` : contrôles d'identité FY2024 : contrôle partiel (2/4 < seuil 3)
- [AVERT] `969500SSIGMAGT008F11` : contrôles d'identité FY2025 : contrôle partiel (2/4 < seuil 3)
- [AVERT] `549300S5CCFESE4C6Y07` : données en retard : dernier ESEF 2024-12-31, attendu 2025-12-31 ; complété par yfinance (2025-12-31)
- [AVERT] `969500DIVIP5VKNW4948` : contrôles d'identité FY2019 : contrôle partiel (2/4 < seuil 3)

## d) Diagnostic des postes manquants (items 25bis, 27) — preuves, sans code

Méthode : recherche exhaustive, dans tous les rapports ESEF en cache de chaque société, des concepts XBRL dont le nom contient les mots-clés indiqués (faits sans dimension uniquement, ceux que le pipeline peut lire). Aucun changement de code dans cette section.

### d.1 — F7 : nombre d'actions (item 25bis, option (a) conservée : indisponible)

**Atlas Copco A** — concepts contenant « Shares » trouvés :

| Concept | Type | Exemple |
|---|---|---|
| `atla:AcquisitionOfSeriesAShares` | montant SEK (flux de trésorerie, rachat d'actions propres) | 416 000 000 SEK (2021) |
| `atla:DivestmentOfSeriesAShares` / `atla:DivestmentOfSeriesBShares` | montant SEK (cession d'actions propres) | 702 000 000 SEK (2021) |
| `atla:RedemptionOfShares` | montant SEK (rachat/annulation) | -157 000 000 SEK (2022) |
| `ifrs-full:DescriptionOfAccountingPolicyForTreasurySharesExplanatory` | **bloc TEXTE** (suédois, non numérique) | « När Atlas Copcos aktier som är klassificerade... » |
| `ifrs-full:DisclosureOfTreasurySharesExplanatory` | **bloc TEXTE** contenant « Antal aktier » (= « Nombre d'actions ») en toutes lettres | texte narratif |

**Diagnostic** : le nombre d'actions figure bien dans le rapport, mais seulement en texte narratif à l'intérieur d'un bloc « explicatif » (balisage ESEF de type texte, pas un fait numérique isolé). Les seuls faits NUMÉRIQUES tagués contenant « Shares » sont des MONTANTS en SEK (rachats/cessions d'actions propres), pas des comptes d'actions. Atlas Copco a bien des actions de catégorie A et B (confirmé par les noms de concepts), mais aucune n'est balisée comme un nombre. **Aucun concept alternatif ni somme de catégories A+B n'est possible : la donnée numérique n'existe pas dans le XBRL.**

**Brunello Cucinelli** — recherche identique : **aucun concept contenant « Shares » dans aucun rapport**, ni montant ni texte. Le nombre d'actions n'apparaît nulle part dans le XBRL balisé.

**Mycronic** — même profil qu'Atlas Copco : seuls `ifrs-full:DescriptionOfAccountingPolicyForTreasurySharesExplanatory` et `ifrs-full:DisclosureOfTreasurySharesExplanatory` (blocs texte suédois, LTIP inclus) contiennent « Shares » — aucun fait numérique.

**Valneva** — cas différent : `ifrs-full:NumberOfSharesOutstanding` (unité `xbrli:shares`, bien un compte) EST balisé, mais seulement dans les rapports FY2019 à FY2022 (6 faits, dernier exemple : 138 367 482 au 31/12/2022). **Aucun fait de ce type dans les rapports FY2023, FY2024 ou FY2025** : Valneva a cessé de baliser ce concept à partir de l'exercice FY2023, sans que la raison soit déterminable depuis le XBRL seul (changement de logiciel de balisage, de cabinet, ou choix éditorial — hypothèses, non vérifiées).

**Conclusion (item 25bis)** : aucune des 4 sociétés n'offre de concept alternatif ou de dimension à sommer — le nombre d'actions est structurellement absent du XBRL balisé (texte narratif ou rien du tout), pas mal mappé. **Option (a) confirmée et conservée : F7 reste indisponible, aucun code changé.**

### d.2 — dette_long_terme / dette_court_terme (item 27, décision item 28 : REJETÉ, aucun code)

**Décision** : `NoncurrentFinancialLiabilitiesAtAmortisedCost` et `OtherNoncurrentFinancialLiabilities` ne sont PAS mappés (catégories IFRS 7 : mélangent emprunts bancaires, dettes locatives et autres passifs financiers). Recherche complémentaire d'une ligne « emprunts / interest-bearing liabilities » ou d'une note détaillée : `ifrs-full:DisclosureOfBorrowingsExplanatory` existe pour les deux sociétés, mais c'est un **bloc TEXTE narratif** (comme les blocs « Treasury Shares » du d.1), sans axe de dimension structuré (`ifrs-full:ComponentsOfEquityAxis` est le seul axe utilisé dans les deux rapports) : aucune ventilation numérique par type d'emprunt n'est extractible. **Aucune ligne fiable trouvée : F5 reste non évaluable pour ces exercices, aucun code changé.**

**Contrôle demandé (comparaison au candidat écarté vs yfinance Long Term Debt, écart > 10 % → rejeté), sur tous les exercices communs disponibles :**

| Société | Exercice | Concept ESEF écarté | Valeur ESEF | yfinance Long Term Debt | Écart | Décision |
|---|---|---|---|---|---|---|
| Atlas Copco A | FY2022 | `OtherNoncurrentFinancialLiabilities` | 23 770 M SEK | 20 233 M SEK | +17,5 % | **rejeté** |
| Atlas Copco A | FY2023 | idem | 29 967 M SEK | 25 598 M SEK | +17,1 % | **rejeté** |
| Atlas Copco A | FY2024 | idem | 31 688 M SEK | 26 240 M SEK | +20,8 % | **rejeté** |
| Mycronic | FY2022 | `NoncurrentFinancialLiabilitiesAtAmortisedCost` | 193 M SEK | 7 M SEK | +2 657 % | **rejeté** |

Écart systématique et massif dans les deux cas (jamais < 17 %, jusqu'à ×27 pour Mycronic) : confirme quantitativement l'hypothèse qualitative — ces concepts « Financial Liabilities » incluent bien d'autres passifs que la seule dette financière comparable à yfinance Long Term Debt. **Décision finale : aucun des deux concepts n'est mappé.**

### d.3 — capex (item 27/29, Thermador, tous exercices) — IMPLÉMENTÉ

`thermador:OutflowsForTheAcquisitionOfTangibleAndIntangibleFixedAssets` ajouté en extension pour le LEI Thermador dans `mapping_ifrs.yaml` (même mécanisme déjà en place pour `ebit`/`reserves` de cette société). **Limite assumée** : à la différence des deux entrées `ebit`/`reserves` (vérifiées contre le rapport publié dans une session antérieure), **le libellé de ce concept n'a PAS pu être vérifié contre le rapport imprimé dans cette session (pas d'accès Internet)** — la source indiquée dans `mapping_ifrs.yaml` le précise explicitement. Le nom du concept est auto-descriptif et cohérent avec l'hypothèse #7, mais reste une vérification en attente.

**Correction additionnelle découverte en implémentant** : ce concept maison tague un flux SORTANT NÉGATIF (ex. -12 221 000 € en FY2021), alors que tous les concepts capex génériques déjà mappés (utilisés par les 6 autres sociétés du panel) sont des magnitudes POSITIVES. Sans correction, cela aurait faussé silencieusement Q2/V3 (FCF = CFO − capex serait devenu CFO + |capex|). Valeur absolue retenue, badge « signe inversé » ajouté (`pipeline/normalize.py`, testé). Capex Thermador maintenant disponible sur les 7 exercices (ex. FY2021 : 12 221 000 €, FY2025 : 5 697 000 €).

### d.4 — marge_brute (item 27/30, Cucinelli, Thermador, Valneva) — IMPLÉMENTÉ (Valneva)

- **Brunello Cucinelli et Thermador** : présentation par nature confirmée (aucun `CostOfSales`), aucune correction possible — hypothèse déjà correcte, inchangée.
- **Valneva** : `marge_brute = chiffre_affaires − cout_des_ventes` (nouveau poste auxiliaire `cout_des_ventes` → `ifrs-full:CostOfSales`, calcul de secours dans `normalize._secours()`, même mécanisme que `dettes_totales`/`actif_courant`/`dettes_courantes`). Badge « marge brute reconstituée (chiffre d'affaires − coût des ventes) ». Disponible sur les 7 exercices désormais (ex. FY2025 : 67 520 000 €). Testé (secours appliqué seulement si `GrossProfit` n'est pas balisé directement).

