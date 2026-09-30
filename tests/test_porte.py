"""Tests de l'étage 1 (hors F-score et Z'', testés à part)."""
import math

import pytest

from pipeline.calc import porte as P
from pipeline.common import config

CFG = config()


def test_cagr_simple():
    v, raison = P.cagr(100, 161.051, 5)          # 100 × 1,1^5 = 161,051
    assert raison is None
    assert v == pytest.approx(0.10, abs=1e-9)


@pytest.mark.parametrize("debut,fin", [(-1, 5), (0, 5), (5, -1), (5, 0)])
def test_cagr_non_calculable_si_borne_negative_ou_nulle(debut, fin):
    v, raison = P.cagr(debut, fin, 5)
    assert v is None and "non calculable" in raison


def test_annees_en_baisse():
    assert P.annees_en_baisse([100, 90, 95, 94, 120]) == 2


def test_pente_log_lineaire_croissance_constante():
    annees = [2020, 2021, 2022, 2023]
    valeurs = [100 * 1.2 ** i for i in range(4)]
    assert P.pente_log_lineaire(annees, valeurs) == pytest.approx(0.20)


def _serie(debut=2020, n=6, croissance=0.12):
    return [(debut + i, 100 * (1 + croissance) ** i) for i in range(n)]


def test_p1_ok_avec_6_exercices_et_note_covid():
    r = P.p1_croissance_ca(_serie(), CFG)
    assert r["statut"] == P.OK
    assert r["libelle"] == "CAGR 5 ans (FY2020→FY2025)"
    assert r["note_base"] == "Covid"
    assert r["valeur"] == pytest.approx(0.12)


def test_p1_fenetre_limitee_aux_6_derniers_exercices():
    r = P.p1_croissance_ca(_serie(2018, 8), CFG)
    assert r["annee_base"] == 2020 and r["exercices_disponibles"] == 8


def test_p1_non_evaluable_si_moins_de_6_exercices_meme_si_cagr_eleve():
    r = P.p1_croissance_ca(_serie(2022, 4, 0.30), CFG)
    assert r["statut"] == P.NE                       # jamais ✅
    assert r["libelle"] == "CAGR 3 ans (FY2022→FY2025)"
    assert r["valeur"] == pytest.approx(0.30)


def test_p1_regle_alternative_5_exercices():
    r = P.p1_croissance_ca(_serie(2021, 5), CFG, min_ex=5)
    assert r["statut"] == P.OK and r["libelle"].startswith("CAGR 4 ans")


def test_p1_ko_si_deux_annees_en_baisse():
    pts = [(2020, 100), (2021, 90), (2022, 150), (2023, 140), (2024, 170), (2025, 200)]
    r = P.p1_croissance_ca(pts, CFG)
    assert r["statut"] == P.KO and "2 années en baisse" in r["raison"]


def test_p1_ko_si_cagr_sous_le_seuil():
    r = P.p1_croissance_ca(_serie(croissance=0.05), CFG)
    assert r["statut"] == P.KO


def test_p3_bnpa_de_depart_negatif():
    pts = [(2020, -0.71), (2021, -0.75), (2022, -1.24), (2023, -0.73), (2024, -0.08), (2025, -0.68)]
    r = P.p3_croissance_bnpa(pts, CFG)
    assert r["statut"] == P.KO
    assert "non calculable" in r["raison"]


def test_p3_retour_aux_benefices_non_evaluable_pas_ko():
    # Cucinelli réel : perte Covid FY2020 (-0,48847), retour aux bénéfices dès FY2021, BNPA
    # FY2025 = 1,9865 > 0 → non évaluable (jamais ❌), CAGR indicatif depuis FY2021.
    pts = [(2020, -0.48847), (2021, 0.78415), (2022, 1.18528), (2023, 1.68576),
          (2024, 1.75713), (2025, 1.9865)]
    r = P.p3_croissance_bnpa(pts, CFG)
    assert r["statut"] == P.NE
    assert "retour aux bénéfices" in r["raison"]
    assert r["valeur_indicative"] == pytest.approx((1.9865 / 0.78415) ** (1 / 4) - 1)
    assert r["libelle_indicatif"] == "CAGR 4 ans (FY2021→FY2025) depuis la première année positive"


def test_p3_encore_deficitaire_reste_ko():
    # Valneva réel : jamais positif sur la fenêtre → CAGR non calculable, ❌ (pas NE).
    pts = [(2020, -0.71), (2021, -0.75), (2022, -1.24), (2023, -0.73), (2024, -0.08), (2025, -0.68)]
    r = P.p3_croissance_bnpa(pts, CFG)
    assert r["statut"] == P.KO
    assert "valeur_indicative" not in r


def test_p2_strict_et_relatif():
    ca = {a: 1000.0 for a in range(2020, 2026)}
    ebit = {a: 250.0 for a in ca}                     # marge EBIT 25 %
    rn = {a: 150.0 for a in ca}                       # marge nette 15 %
    r = P.p2_marges(ca, ebit, rn, CFG, seuil_relatif=0.30)
    assert r["statut_strict"] == P.OK
    assert r["statut_relatif"] == P.KO                # 25 % < 3e quartile de 30 %
    assert r["pente_marge_ebit_pts"] == pytest.approx(0.0)


def test_p2_ko_si_marges_en_baisse_rapide():
    ca = {a: 1000.0 for a in range(2020, 2026)}
    ebit = {a: 300.0 - 10 * (a - 2020) for a in ca}   # −1 pt/an
    rn = {a: 150.0 for a in ca}
    r = P.p2_marges(ca, ebit, rn, CFG)
    assert r["pente_marge_ebit_pts"] == pytest.approx(-1.0)
    assert r["statut_strict"] == P.KO


def test_p2_non_evaluable_sans_marge_nette():
    ca = {2024: 1000.0, 2025: 1000.0}
    ebit = {2024: 250.0, 2025: 250.0}
    r = P.p2_marges(ca, ebit, {}, CFG)
    assert r["statut_strict"] == P.NE


def test_p2_fiabilite_sans_effet_garde_le_statut_calcule():
    # Boliden (réel) : marge EBIT ESEF FY2024 15,3 % et marge EBIT yfinance FY2025 13,7 % sont
    # toutes deux < 20 % → même conclusion (KO) : pas de plafonnement, le statut KO est gardé.
    ca = {2020: 100.0, 2021: 105.0, 2022: 110.0, 2023: 108.0, 2024: 112.0, 2025: 115.0}
    ebit = {2020: 16.0, 2021: 17.0, 2022: 18.0, 2023: 11.0, 2024: 17.2, 2025: 15.8}   # 2024: 15,4% ; 2025: 13,7%
    rn = {a: 0.1 * v for a, v in ca.items()}
    retard = {"cloture_attendue": "2025-12-31", "derniere_esef": "2024-12-31",
              "comparaison_exercice_commun": [{"poste": "ebit", "ecart": -0.264}]}
    r = P.p2_marges_fiabilite(ca, ebit, rn, CFG, None, "ESEF", retard)
    assert r["statut_strict"] == P.KO
    assert "fiabilite" not in r and r.get("fiabilite_verifiee", {}).get("conclusion_identique") is True


def test_p2_fiabilite_avec_effet_plafonne_a_non_evaluable():
    # Marge ESEF FY2024 juste sous le seuil (KO) mais marge yfinance FY2025 largement au-dessus
    # (OK) → les deux calculs divergent : la conclusion dépend de la donnée douteuse.
    ca = {2020: 100.0, 2021: 100.0, 2022: 100.0, 2023: 100.0, 2024: 100.0, 2025: 100.0}
    ebit = {2020: 22.0, 2021: 22.0, 2022: 22.0, 2023: 22.0, 2024: 19.0, 2025: 35.0}
    rn = {a: 0.15 * v for a, v in ca.items()}
    retard = {"cloture_attendue": "2025-12-31", "derniere_esef": "2024-12-31",
              "comparaison_exercice_commun": [{"poste": "ebit", "ecart": -0.30}]}
    r = P.p2_marges_fiabilite(ca, ebit, rn, CFG, None, "ESEF", retard)
    assert r["statut_strict"] == P.NE
    assert r["fiabilite"]["statut"] == P.DEPEND_DONNEE_NON_RECOUPEE
    assert r["donnees_fiables"]["statut_strict"] == P.KO and r["statut_calcule"] == P.OK


def test_p2_fiabilite_non_recoupe_reste_non_evaluable():
    ca, ebit, rn = {2025: 100.0}, {2025: 25.0}, {2025: 15.0}
    r = P.p2_marges_fiabilite(ca, ebit, rn, CFG, None, "yfinance", None)
    assert r["statut_strict"] == P.NE and r["fiabilite"]["statut"] == "non recoupé"


def test_p6_liquidite():
    assert P.p6_liquidite({"valeur": 150_000}, CFG)["statut"] == P.OK
    assert P.p6_liquidite({"valeur": 100_000}, CFG)["statut"] == P.KO   # strictement > 100 000
    assert P.p6_liquidite({"valeur": None}, CFG)["statut"] == P.NE


def test_statut_global():
    assert P.statut_global([P.OK, P.OK]) == P.OK
    assert P.statut_global([P.OK, P.NE]) == P.NE
    assert P.statut_global([P.NE, P.KO]) == P.KO


def test_regression_pente():
    assert P.regression([1, 2, 3], [2, 4, 6]) == pytest.approx(2)
    assert P.regression([1], [1]) is None
    assert not math.isnan(P.regression([1, 2], [5, 5]))
