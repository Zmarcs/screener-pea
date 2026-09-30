"""Tests du Piotroski F-score (P4).

Deux sociétés réelles, valeurs relevées À LA MAIN dans les tableaux des rapports annuels
publiés (en millions d'euros), calcul refait à la main dans docs/rapport_etape1.md :
- Hermès : Document d'enregistrement universel 2025 (PDF), compte de résultat p. 364,
  bilan p. 365, flux de trésorerie p. 367 (folios imprimés ; pages 356, 357, 359 du PDF).
- ASML : 2025 Annual Report based on IFRS (PDF), compte de résultat p. 270, bilan p. 272,
  flux de trésorerie p. 275.
"""
import pytest

from pipeline.calc import porte as P
from pipeline.common import config

CFG = config()

HERMES_2025 = dict(resultat_net=4524, cash_flow_operationnel=5374, actif_total=24322,
                   dette_long_terme=34, actif_courant=15911, dettes_courantes=3186,
                   nombre_actions=105_569_412, concept_actions="ifrs-full:NumberOfSharesIssuedAndFullyPaid",
                   chiffre_affaires=16002, marge_brute=11379, ebit=6569)
HERMES_2024 = dict(resultat_net=4603, cash_flow_operationnel=5139, actif_total=23084,
                   dette_long_terme=61, actif_courant=15476, dettes_courantes=3629,
                   nombre_actions=105_569_412, concept_actions="ifrs-full:NumberOfSharesIssuedAndFullyPaid",
                   chiffre_affaires=15170, marge_brute=10660, ebit=6150)

# ASML : actions en circulation (rapport ESEF, NumberOfSharesOutstanding, en millions)
ASML_2025 = dict(resultat_net=10213.0, cash_flow_operationnel=13826.5, actif_total=55576.8,
                 dette_long_terme=2709.0, actif_courant=30240.5, dettes_courantes=24439.4,
                 nombre_actions=385.4, concept_actions="ifrs-full:NumberOfSharesOutstanding",
                 chiffre_affaires=32667.3, marge_brute=16931.4, ebit=12054.0)
ASML_2024 = dict(resultat_net=8349.0, cash_flow_operationnel=12369.7, actif_total=52566.5,
                 dette_long_terme=3677.3, actif_courant=30357.2, dettes_courantes=20049.5,
                 nombre_actions=393.3, concept_actions="ifrs-full:NumberOfSharesOutstanding",
                 chiffre_affaires=28262.9, marge_brute=14283.8, ebit=9937.1)


def points(f):
    return {t["code"]: t["point"] for t in f["tests"]}


def test_hermes_calcul_a_la_main():
    f = P.fscore(HERMES_2025, HERMES_2024)
    # ROA 2025 = 4524/24322 = 0,1860 < ROA 2024 = 4603/23084 = 0,1994 → F3 = 0
    assert points(f) == {"F1": 1, "F2": 1, "F3": 0, "F4": 1, "F5": 1, "F6": 1, "F7": 1, "F8": 1, "F9": 1}
    assert f["score"] == 8 and f["tests_disponibles"] == 9
    t = {x["code"]: x for x in f["tests"]}
    assert t["F1"]["valeur_n"] == pytest.approx(0.18600, abs=1e-5)
    assert t["F6"]["valeur_n"] == pytest.approx(4.99404, abs=1e-5)      # 15911 / 3186
    assert t["F6"]["valeur_n1"] == pytest.approx(4.26454, abs=1e-5)     # 15476 / 3629
    assert t["F8"]["valeur_n"] == pytest.approx(0.71110, abs=1e-5)      # 11379 / 16002
    assert P.p4_fscore(f, CFG)["statut"] == P.OK


def test_asml_calcul_a_la_main():
    f = P.fscore(ASML_2025, ASML_2024)
    # Liquidité courante 30240,5/24439,4 = 1,2374 < 30357,2/20049,5 = 1,5141 → F6 = 0
    assert points(f) == {"F1": 1, "F2": 1, "F3": 1, "F4": 1, "F5": 1, "F6": 0, "F7": 1, "F8": 1, "F9": 1}
    assert f["score"] == 8
    t = {x["code"]: x for x in f["tests"]}
    assert t["F5"]["valeur_n"] == pytest.approx(0.048744, abs=1e-6)     # 2709,0 / 55576,8
    assert t["F9"]["valeur_n1"] == pytest.approx(0.537660, abs=1e-6)    # 28262,9 / 52566,5


def test_substitution_marge_brute_par_marge_ebit():
    n = {**HERMES_2025, "marge_brute": None}
    f = P.fscore(n, HERMES_2024)
    t = {x["code"]: x for x in f["tests"]}
    assert f["substitution_marge_brute"] is True
    assert "EBIT" in t["F8"]["test"]
    assert t["F8"]["valeur_n"] == pytest.approx(6569 / 16002)


def test_emission_d_actions():
    n = {**HERMES_2025, "nombre_actions": 106_000_000}
    assert points(P.fscore(n, HERMES_2024))["F7"] == 0


def test_actions_de_nature_differente_non_comparees():
    n = {**HERMES_2025, "concept_actions": "ifrs-full:WeightedAverageShares"}
    assert points(P.fscore(n, HERMES_2024))["F7"] is None


def test_f_score_partiel_statuts():
    base = P.fscore(HERMES_2025, HERMES_2024)
    # 8 points avec 9 tests → OK ; score partiel qui ne peut plus atteindre 6 → KO ; sinon NE
    assert P.p4_fscore(base, CFG)["statut"] == P.OK
    assert P.p4_fscore({"score": 3, "tests_disponibles": 7, "tests": []}, CFG)["statut"] == P.KO
    assert P.p4_fscore({"score": 5, "tests_disponibles": 8, "tests": []}, CFG)["statut"] == P.NE


def test_f1_f3_f5_f9_actif_ouverture_vs_cloture_hermes():
    """Piotroski original : actif au DÉBUT de l'exercice (= actif de clôture de l'exercice
    précédent), pas l'actif de clôture retenu par le pipeline (hypothèse #10). Actif total
    FY2023 (ouverture de FY2024) = 20 447 M€ (source : pipeline/ESEF, non relevé à la main
    pour ce complément). F9 change de résultat : rotation N (16 002/23 084 = 0,693375) devient
    inférieure à rotation N−1 (15 170/20 447 = 0,741971), alors qu'à actif de clôture elle lui
    était supérieure (16 002/24 322 = 0,657894 > 15 170/23 084 = 0,657304)."""
    r = P.fscore_f1_f3_f5_f9_ouverture(rn_n=4524, rn_n1=4603, at_n1=23084, at_n2=20447,
                                       dlt_n=34, dlt_n1=61, ca_n=16002, ca_n1=15170)
    assert {k: v["point"] for k, v in r.items()} == {"F1": 1, "F3": 0, "F5": 1, "F9": 0}
    clot = points(P.fscore(HERMES_2025, HERMES_2024))
    assert clot["F9"] == 1 and r["F9"]["point"] == 0          # le score change : 8/9 → 7/9


def test_f1_f3_f5_f9_actif_ouverture_vs_cloture_asml():
    """Actif total FY2023 (ouverture de FY2024) = 43 078,6 M€ (source : pipeline/ESEF).
    F9 change aussi : rotation N (32 667,3/52 566,5) devient inférieure à rotation N−1
    (28 262,9/43 078,6), alors qu'à actif de clôture elle lui était supérieure."""
    r = P.fscore_f1_f3_f5_f9_ouverture(rn_n=10213.0, rn_n1=8349.0, at_n1=52566.5, at_n2=43078.6,
                                       dlt_n=2709.0, dlt_n1=3677.3, ca_n=32667.3, ca_n1=28262.9)
    assert {k: v["point"] for k, v in r.items()} == {"F1": 1, "F3": 1, "F5": 1, "F9": 0}
    clot = points(P.fscore(ASML_2025, ASML_2024))
    assert clot["F9"] == 1 and r["F9"]["point"] == 0          # le score change : 8/9 → 7/9


def test_fscore_convention_ouverture_devient_la_reference_hermes():
    """Règle ajoutée : l'actif d'OUVERTURE (Piotroski original) devient le calcul de référence
    de P4 quand l'historique le permet. Pour Hermès, F9 change (cf. test ci-dessus) : le score de
    référence devient 7/9, la clôture (8/9) n'est plus que l'affichage indicatif."""
    f = P.fscore_convention(HERMES_2025, HERMES_2024, at_n2=20447)
    assert f["convention"] == "ouverture" and f["convention_disponible"] is True
    assert f["score"] == 7 and f["tests_disponibles"] == 9
    assert points(f)["F9"] == 0
    assert f["cloture"]["score"] == 8                          # affichage indicatif, inchangé
    assert P.p4_fscore(f, CFG)["statut"] == P.OK                # seuil ≥ 6 : atteint dans les deux cas


def test_fscore_convention_non_evaluable_si_historique_insuffisant():
    """Actif d'ouverture indisponible (pas d'exercice N−2) : F1/F3/F5/F9 en convention
    d'ouverture sont non évaluables (pas de repli silencieux sur la clôture) ; les 5 autres
    tests restent inchangés."""
    f = P.fscore_convention(HERMES_2025, HERMES_2024, at_n2=None)
    assert f["convention_disponible"] is False
    assert f["tests_disponibles"] == 5                          # F2,F4,F6,F7,F8 seulement
    pts = points(f)
    assert pts["F1"] is None and pts["F3"] is None and pts["F5"] is None and pts["F9"] is None
    assert P.p4_fscore(f, CFG)["statut"] == P.NE                # 5 tests dispo, score max = 5 < 6


def test_p4_fiabilite_sans_effet_garde_le_calcul_fiable():
    p4_avec = {"statut": P.KO, "score": 3, "tests_disponibles": 7, "raison": "F-score 3 < 6"}
    p4_fiable = {"statut": P.KO, "score": 2, "tests_disponibles": 6, "raison": "F-score 2 < 6"}
    r = P.p4_fiabilite(p4_avec, p4_fiable)
    assert r["statut"] == P.KO and r["score"] == 2                # calcul fiable gardé, pas plafonné
    assert r["fiabilite_verifiee"]["conclusion_identique"] is True


def test_p4_fiabilite_avec_effet_plafonne_a_non_evaluable():
    p4_avec = {"statut": P.OK, "score": 7, "tests_disponibles": 8, "raison": "—"}
    p4_fiable = {"statut": P.KO, "score": 3, "tests_disponibles": 7, "raison": "F-score 3 < 6"}
    r = P.p4_fiabilite(p4_avec, p4_fiable)
    assert r["statut"] == P.NE
    assert r["fiabilite"]["statut"] == P.DEPEND_DONNEE_NON_RECOUPEE
    assert r["donnees_fiables"]["statut"] == P.KO and r["statut_calcule"] == P.OK


def test_p2_fiabilite_non_recoupe_si_source_100_pourcent_yfinance():
    fiab = P.p2_fiabilite("yfinance", None, CFG)
    assert fiab["statut"] == "non recoupé"


def test_p2_fiabilite_non_fiable_si_ecart_ebit_au_dela_du_seuil():
    retard = {"derniere_esef": "2024-12-31", "cloture_attendue": "2025-12-31",
              "comparaison_exercice_commun": [{"poste": "ebit", "ecart": -0.264}]}
    fiab = P.p2_fiabilite("ESEF", retard, CFG)
    assert fiab["statut"] == P.DEPEND_DONNEE_NON_RECOUPEE


def test_p2_fiabilite_aucune_si_ecart_sous_le_seuil():
    retard = {"derniere_esef": "2024-12-31",
              "comparaison_exercice_commun": [{"poste": "ebit", "ecart": -0.006}]}
    assert P.p2_fiabilite("ESEF", retard, CFG) is None
    assert P.p2_fiabilite("ESEF", None, CFG) is None


def test_tous_les_tests_a_zero():
    n = dict(resultat_net=-10, cash_flow_operationnel=-20, actif_total=100, dette_long_terme=50,
             actif_courant=10, dettes_courantes=20, nombre_actions=110, chiffre_affaires=50,
             marge_brute=5, ebit=-5)
    n1 = dict(resultat_net=10, cash_flow_operationnel=20, actif_total=100, dette_long_terme=40,
              actif_courant=30, dettes_courantes=20, nombre_actions=100, chiffre_affaires=60,
              marge_brute=20, ebit=10)
    f = P.fscore(n, n1)
    assert f["score"] == 0 and f["tests_disponibles"] == 9
