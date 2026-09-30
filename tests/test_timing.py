"""Tests de l'étage 3 — Timing.

RSI : série d'exemple classique (StockCharts, « RSI »). Les valeurs publiées par StockCharts
(70,53 ; 66,32…) utilisent des moyennes arrondies à 2 décimales. Calcul exact à la main :
  14 premières variations : gains = 3,34 ; pertes = 1,40
  moyennes = 0,238571 et 0,100000 → RS = 2,385714 → RSI = 100 − 100 / 3,385714 = 70,4641
  variation suivante −0,28 : gains = (0,238571 × 13 + 0) / 14 = 0,221531
                              pertes = (0,1 × 13 + 0,28) / 14 = 0,112857
                              RS = 1,962929 → RSI = 66,2496
"""
import pytest

from pipeline.calc import timing as T
from pipeline.common import config

CFG = config()["timing"]

EXEMPLE = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03,
           45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22]


def test_rsi_wilder_valeurs_de_reference():
    rsi = T.rsi_wilder(EXEMPLE, 14)
    assert rsi[13] is None
    assert rsi[14] == pytest.approx(70.4641, abs=1e-4)
    assert rsi[15] == pytest.approx(66.2496, abs=1e-4)


def test_rsi_vs_reference_externe_stockcharts():
    """Comparaison avec les valeurs PUBLIÉES par StockCharts.com (article « Relative Strength
    Index (RSI) », série d'exemple ci-dessus) : RSI = 70,53 puis 66,32. StockCharts arrondit ses
    moyennes de gains/pertes à 2 décimales à chaque étape du lissage de Wilder, alors que le
    calcul de `rsi_wilder` ci-dessus garde la pleine précision ; d'où l'écart de quelques
    centièmes avec le calcul exact à la main (70,4641 ; 66,2496) et la tolérance de 0,1."""
    rsi = T.rsi_wilder(EXEMPLE, 14)
    assert rsi[14] == pytest.approx(70.53, abs=0.1)
    assert rsi[15] == pytest.approx(66.32, abs=0.1)


def test_rsi_hausse_continue_vaut_100():
    assert T.rsi_wilder([float(i) for i in range(1, 30)], 14)[-1] == 100.0


def test_moyenne_mobile():
    mm = T.moyenne_mobile([1, 2, 3, 4, 5], 3)
    assert mm == [None, None, 2.0, 3.0, 4.0]


def _tendance(n=300, pente=0.1, fin=None):
    cours = [100 + pente * i for i in range(n)]
    return cours + (fin or [])


def test_rouge_si_cours_sous_mm200():
    cours = _tendance() + [80.0]
    r = T.signal(cours, CFG)
    assert r["signal"] == T.ROUGE


def test_vert_sur_repli_vers_mm50_en_tendance_haussiere():
    cours = _tendance()
    mm50 = sum(cours[-50:]) / 50
    cours[-1] = mm50 * 1.01          # à +1 % de la MM50, au-dessus de la MM200 haussière
    r = T.signal(cours, CFG)
    assert r["signal"] == T.VERT
    assert r["mm200"] > r["mm200_il_y_a_1_mois"]


def test_jaune_si_surachat():
    cours = _tendance(pente=0.5)     # hausse continue : RSI 100, cours loin de la MM50
    r = T.signal(cours, CFG)
    assert r["signal"] == T.JAUNE
    assert "surachat" in r["raisons"][0]


def test_historique_insuffisant():
    assert T.signal([100.0] * 150, CFG)["signal"] == T.NE
