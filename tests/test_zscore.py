"""Tests de l'Altman Z''-score (P5). Valeurs réelles en millions d'euros, relevées dans les
rapports annuels publiés (voir tests/test_fscore.py pour les pages) ; calcul à la main :

Hermès 2025 (DEU 2025, bilan p. 365, variation des capitaux propres p. 366) :
  X1 = (15 911 − 3 186) / 24 322 = 0,523189
  X2 = 19 054 / 24 322           = 0,783406   (réserves consolidées et résultat net part du groupe)
  X3 = 6 569 / 24 322            = 0,270085
  X4 = 18 846 / (24 322 − 18 846) = 18 846 / 5 476 = 3,441563
  Z'' = 6,56×0,523189 + 3,26×0,783406 + 6,72×0,270085 + 1,05×3,441563 = 11,4146

ASML 2025 (Annual Report 2025 IFRS, bilan p. 272) :
  X1 = (30 240,5 − 24 439,4) / 55 576,8 = 0,104380
  X2 = (6 321,8 + 10 213,0) / 55 576,8  = 0,297513   (retained earnings, composantes ESEF)
  X3 = 12 054,0 / 55 576,8              = 0,216889
  X4 = 24 185,0 / (55 576,8 − 24 185,0) = 0,770424
  Z'' = 3,9211
"""
import pytest

from pipeline.calc import porte as P
from pipeline.common import config

CFG = config()
COEFS = CFG["porte"]["p5_zscore"]["coefficients"]


def test_hermes_calcul_a_la_main():
    z = P.zscore(15911, 3186, 19054, 6569, 24322, 18846, 24322 - 18846, COEFS)
    assert z["x1"] == pytest.approx(0.523189, abs=1e-6)
    assert z["x2"] == pytest.approx(0.783406, abs=1e-6)
    assert z["x3"] == pytest.approx(0.270085, abs=1e-6)
    assert z["x4"] == pytest.approx(3.441563, abs=1e-6)
    assert z["valeur"] == pytest.approx(11.4146, abs=1e-4)
    assert P.p5_zscore(z, CFG)["zone"] == "saine"


def test_asml_calcul_a_la_main():
    z = P.zscore(30240.5, 24439.4, 6321.8 + 10213.0, 12054.0, 55576.8, 24185.0, 55576.8 - 24185.0, COEFS)
    assert z["valeur"] == pytest.approx(3.9211, abs=1e-4)


def test_formule_sur_valeurs_simples():
    # X1 = 0,1 ; X2 = 0,2 ; X3 = 0,1 ; X4 = 1 → 0,656 + 0,652 + 0,672 + 1,05 = 3,03
    z = P.zscore(30, 20, 20, 10, 100, 50, 50, COEFS)
    assert z["valeur"] == pytest.approx(3.03)


@pytest.mark.parametrize("valeur,statut,zone", [
    (2.61, P.OK, "saine"), (2.6, P.OK, "grise"), (1.11, P.OK, "grise"),
    (1.1, P.KO, "détresse"), (-4.0, P.KO, "détresse"),
])
def test_zones_et_seuils(valeur, statut, zone):
    r = P.p5_zscore({"valeur": valeur, "manquants": []}, CFG)
    assert (r["statut"], r["zone"]) == (statut, zone)


def test_donnee_manquante_non_evaluable():
    z = P.zscore(15911, 3186, None, 6569, 24322, 18846, 5476, COEFS)
    r = P.p5_zscore(z, CFG)
    assert r["statut"] == P.NE and "reserves" in r["raison"]
