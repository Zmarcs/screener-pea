"""Tests du score QVM sur un univers SYNTHÉTIQUE de 50 sociétés inventées.

Composition : secteur A = 20 sociétés, B = 15, C = 10 (exactement le minimum),
D = 5 (moins de 10 → percentile sur l'univers entier). Graine fixe : résultats reproductibles.
"""
import random

import pytest

from pipeline.calc import qvm as Q
from pipeline.common import config

CFG = config()
MIN = CFG["qvm"]["min_societes_secteur"]
POIDS = CFG["qvm"]["poids"]


def univers_synthetique():
    rng = random.Random(42)
    secteurs = ["A"] * 20 + ["B"] * 15 + ["C"] * 10 + ["D"] * 5
    univers = []
    for i, s in enumerate(secteurs):
        m = {code: rng.uniform(-1, 1) for code in Q.METRIQUES}
        univers.append({"id": f"S{i:02d}", "secteur": s, "metriques": m})
    # Métriques manquantes volontaires
    univers[0]["metriques"]["V2"] = None
    univers[1]["metriques"].update({"M1": None, "M2": None, "M3": None})   # plus de momentum
    return univers


def test_percentile_formule():
    assert Q.percentile(1, [1, 2, 3]) == 0
    assert Q.percentile(3, [1, 2, 3]) == 100
    assert Q.percentile(2, [1, 2, 3]) == 50
    assert Q.percentile(2, [2, 2, 3]) == 25          # une égalité hors soi → demi-rang
    assert Q.percentile(5, [5]) == 50


def test_bornes_et_base_de_comparaison():
    u = univers_synthetique()
    pct = Q.calculer_percentiles(u, MIN)
    for s in u:
        for code, v in pct[s["id"]].items():
            assert 0 <= v["percentile"] <= 100
            if s["secteur"] == "D":
                assert v["base"].startswith("univers entier")
            elif not (s["id"] == "S00" and code == "V2"):
                assert v["base"] == f"secteur {s['secteur']}"


def test_secteur_de_10_societes_reste_sectoriel():
    pct = Q.calculer_percentiles(univers_synthetique(), MIN)
    c = [k for k, v in pct.items() if v["Q1"]["base"] == "secteur C"]
    assert len(c) == 10


def test_sens_plus_bas_est_mieux():
    u = univers_synthetique()
    secteur_a = [s for s in u if s["secteur"] == "A"]
    meilleur_q3 = min(secteur_a, key=lambda s: s["metriques"]["Q3"])   # accruals : plus bas = mieux
    pire_q1 = min(secteur_a, key=lambda s: s["metriques"]["Q1"])       # ROCE : plus haut = mieux
    pct = Q.calculer_percentiles(u, MIN)
    assert pct[meilleur_q3["id"]]["Q3"]["percentile"] == 100
    assert pct[pire_q1["id"]]["Q1"]["percentile"] == 0


def test_metrique_manquante_exclue_jamais_remplacee():
    u = univers_synthetique()
    pct = Q.calculer_percentiles(u, MIN)
    assert "V2" not in pct["S00"]
    s = Q.scores(pct["S00"], POIDS)
    attendu = (pct["S00"]["V1"]["percentile"] + pct["S00"]["V3"]["percentile"]) / 2
    assert s["sous_scores"]["valeur"] == pytest.approx(attendu)


def test_score_pondere():
    u = univers_synthetique()
    pct = Q.calculer_percentiles(u, MIN)
    s = Q.scores(pct["S10"], POIDS)
    ss = s["sous_scores"]
    assert s["score"] == pytest.approx(0.4 * ss["qualite"] + 0.3 * ss["valeur"] + 0.3 * ss["momentum"])
    assert s["partiel"] is False


def test_sous_score_absent_renormalise_et_signale():
    pct = Q.calculer_percentiles(univers_synthetique(), MIN)
    s = Q.scores(pct["S01"], POIDS)
    assert s["sous_scores"]["momentum"] is None and s["partiel"] is True
    ss = s["sous_scores"]
    assert s["score"] == pytest.approx((0.4 * ss["qualite"] + 0.3 * ss["valeur"]) / 0.7)


def test_rang_moyen_des_scores_autour_de_50():
    pct = Q.calculer_percentiles(univers_synthetique(), MIN)
    scores = [Q.scores(p, POIDS)["score"] for p in pct.values()]
    assert 40 < sum(scores) / len(scores) < 60


def test_metriques_fondamentales():
    m = Q.metriques_fondamentales({"ebit": 20, "actif_total": 200, "dettes_courantes": 100,
                                   "cash_flow_operationnel": 30, "capex": 10, "resultat_net": 10,
                                   "marges_ebit_5ans": [0.1, 0.1, 0.1]})
    assert m["Q1"]["valeur"] == pytest.approx(0.2)        # 20 / (200 − 100)
    assert m["Q2"]["valeur"] == pytest.approx(2.0)        # (30 − 10) / 10
    assert m["Q3"]["valeur"] == pytest.approx(-0.1)       # (10 − 30) / 200
    assert m["Q4"]["valeur"] == pytest.approx(0.0)


def test_conversion_fcf_non_interpretable_si_perte():
    m = Q.metriques_fondamentales({"cash_flow_operationnel": 30, "capex": 10, "resultat_net": -5})
    assert m["Q2"]["valeur"] is None


def test_metriques_valeur_et_per_negatif_exclu():
    d = {"capitalisation": 1000, "ebit": 100, "dette_long_terme": 200, "dette_court_terme": 50,
         "tresorerie": 250, "cash_flow_operationnel": 80, "capex": 30,
         "per_actuel": 20, "per_mediane_5ans": 25}
    m = Q.metriques_valeur(d)
    assert m["V1"]["valeur"] == pytest.approx(0.1)        # 100 / (1000 + 200 + 50 − 250)
    assert m["V2"]["valeur"] == pytest.approx(0.8)
    assert m["V3"]["valeur"] == pytest.approx(0.05)
    assert Q.metriques_valeur({**d, "per_actuel": -4})["V2"]["valeur"] is None


def test_metriques_momentum():
    cours = [100.0] * 300
    cours[-1 - 252] = 50.0          # il y a 12 mois
    cours[-1 - 21] = 100.0          # il y a 1 mois
    indice = [100.0] * 300
    indice[-1 - 126] = 80.0
    m = Q.metriques_momentum(cours, indice, 2.2, 2.0, CFG["momentum"])
    assert m["M1"]["valeur"] == pytest.approx(1.0)        # 100 / 50 − 1
    assert m["M2"]["valeur"] == pytest.approx(1 / 1.25 - 1)
    assert m["M3"]["valeur"] == pytest.approx(0.1)
