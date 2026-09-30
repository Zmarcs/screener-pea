"""Tests du verdict déterministe et de la règle « non évaluable → SURVEILLANCE au plus »."""
import pytest

from pipeline.calc import verdict as V
from pipeline.calc.porte import KO, NE, OK
from pipeline.common import config

CFG = config()["verdict"]


@pytest.mark.parametrize("porte,score,timing,attendu", [
    (OK, 75, "vert", V.ACHAT),
    (OK, 75, "jaune", V.SURVEILLANCE),
    (OK, 75, "rouge", V.SURVEILLANCE),
    (OK, 60, "vert", V.SURVEILLANCE),
    (OK, 70, "vert", V.ACHAT),            # seuil inclus (≥ 70)
    (OK, 50, "rouge", V.SURVEILLANCE),    # seuil inclus (≥ 50)
    (OK, 49.9, "vert", V.REJET),
    (KO, 95, "vert", V.REJET),
    (NE, 95, "vert", V.SURVEILLANCE),     # règle ajoutée : plafonné
    (NE, 40, "vert", V.REJET),
    (OK, None, "vert", V.INDETERMINE),
])
def test_verdict(porte, score, timing, attendu):
    assert V.verdict(porte, score, timing, CFG)["verdict"] == attendu


@pytest.mark.parametrize("porte,score,timing,taille,seuil,attendu,indicatif", [
    (OK, 75, "vert", 10, 30, V.PROVISOIRE, V.ACHAT),      # ACHAT par le score, univers trop petit
    (OK, 30, "vert", 10, 30, V.PROVISOIRE, V.REJET),      # REJET par le score, univers trop petit
    (NE, 30, "vert", 10, 30, V.PROVISOIRE, V.REJET),      # porte NE mais REJET vient du score < surv
    (KO, 95, "vert", 10, 30, V.REJET, None),              # REJET par la porte ❌ : jamais PROVISOIRE
    (NE, 95, "vert", 10, 30, V.SURVEILLANCE, None),       # SURVEILLANCE (plafond porte) : pas concerné
    (OK, 75, "vert", 30, 30, V.ACHAT, None),              # univers ≥ seuil : verdict définitif
    (OK, 75, "vert", None, None, V.ACHAT, None),          # paramètres absents : comportement inchangé
])
def test_verdict_provisoire_univers_non_significatif(porte, score, timing, taille, seuil, attendu, indicatif):
    r = V.verdict(porte, score, timing, CFG, taille, seuil)
    assert r["verdict"] == attendu
    if indicatif:
        assert r["verdict_indicatif"] == indicatif


@pytest.mark.parametrize("verd,source,attendu", [
    (V.REJET, "yfinance", "REJET sur données non recoupées"),
    (V.REJET, "ESEF", None),
    (V.SURVEILLANCE, "yfinance", None),
])
def test_badge_donnees_non_recoupees(verd, source, attendu):
    assert V.badge_donnees_non_recoupees(verd, source) == attendu


def test_justification_trois_points():
    criteres = {
        "P1": {"statut": OK, "valeur": 0.11, "seuil": 0.10},     # marge +10 %
        "P4": {"statut": OK, "score": 8, "seuil": 6},            # marge +33 %
        "P5": {"statut": NE, "valeur": None},
    }
    pts = V.justification(criteres, {"qualite": 80, "valeur": 30, "momentum": 55})
    assert pts[0].startswith("Critère de porte le plus juste : P1 ✅")
    assert pts[1] == "Meilleur sous-score : qualite (80/100)"
    assert pts[2] == "Pire sous-score : valeur (30/100)"


def test_justification_critere_en_echec_prioritaire():
    criteres = {"P1": {"statut": OK, "valeur": 0.11, "seuil": 0.10},
                "P3": {"statut": KO, "valeur": 0.02, "seuil": 0.10}}
    assert "P3 ❌" in V.justification(criteres, {})[0]
