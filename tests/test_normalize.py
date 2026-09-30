"""Tests de la normalisation ESEF (faits xBRL-JSON synthétiques) et des utilitaires marché."""
import datetime as dt

import pandas as pd
import pytest

from pipeline import ingest_market as M
from pipeline import normalize as N
from pipeline.common import config
from pipeline.ingest_esef import analyser_periode, cloture_reelle, date_fin
from pipeline.run import cloture_attendue

CFG = config()

D = dt.date


def fait(concept, periode, valeur, unite="iso4217:EUR", **dims):
    return {"value": str(valeur), "decimals": -3,
            "dimensions": {"concept": concept, "entity": "scheme:X", "period": periode, "unit": unite, **dims}}


def annee(a):
    return f"{a}-01-01T00:00:00/{a + 1}-01-01T00:00:00"


def fin(a):
    return f"{a + 1}-01-01T00:00:00"


def rapport(cloture_annee, faits, date_ajout, fxo=None):
    return {"fxo_id": fxo or f"X-{cloture_annee}", "cloture": f"{cloture_annee}-12-31", "date_ajout": date_ajout,
            "faits": {"facts": {f"f{i}": f for i, f in enumerate(faits)}}, "viewer_url": None,
            "erreurs": 0, "avertissements": 0, "incoherences": 0}


# --------------------------------------------------------------------------- périodes
def test_convention_de_fin_xbrl_json():
    assert date_fin("2026-01-01T00:00:00") == D(2025, 12, 31)
    assert analyser_periode(annee(2025)) == (D(2025, 1, 1), D(2025, 12, 31))
    assert analyser_periode(fin(2025)) == (None, D(2025, 12, 31))


def test_cloture_reelle_prend_l_exercice_courant_pas_le_comparatif():
    faits = {"facts": {str(i): fait("ifrs-full:Revenue", annee(2025 if i < 5 else 2024), 1) for i in range(8)}}
    assert cloture_reelle(faits) == D(2025, 12, 31)


def test_cloture_attendue_delai_de_4_mois():
    # clôture 31/12/2024 → échéance de publication 30/04/2025
    assert cloture_attendue(D(2024, 12, 31), 4, D(2026, 9, 29)) == D(2025, 12, 31)
    assert cloture_attendue(D(2023, 12, 31), 4, D(2025, 4, 30)) == D(2023, 12, 31)
    assert cloture_attendue(D(2023, 12, 31), 4, D(2025, 5, 1)) == D(2024, 12, 31)


# --------------------------------------------------------------------------- extraction
def test_faits_ventiles_ignores_sauf_demande_explicite():
    r = rapport(2025, [
        fait("ifrs-full:Revenue", annee(2025), 188),
        fait("ifrs-full:Revenue", annee(2025), 1000, **{"ifrs-full:SegmentsAxis": "x:EuropeMember"}),
        fait("ifrs-full:Equity", fin(2025), 70, **{"ifrs-full:ComponentsOfEquityAxis": "ifrs-full:RetainedEarningsMember"}),
    ], "2026-03-01")
    postes = {"chiffre_affaires": {"type": "flux", "concepts": ["ifrs-full:Revenue"]},
              "reserves": {"type": "stock", "concepts": [
                  "ifrs-full:Equity[ifrs-full:ComponentsOfEquityAxis=ifrs-full:RetainedEarningsMember]"]}}
    ex = N.extraire_rapport(r, postes)
    assert ex["chiffre_affaires"][D(2025, 12, 31)]["valeur"] == 188
    assert ex["reserves"][D(2025, 12, 31)]["valeur"] == 70


def test_somme_partielle_signalee_et_somme_complete_exigee():
    r = rapport(2025, [fait("ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities", annee(2025), 40),
                       fait("ifrs-full:RetainedEarningsProfitLossForReportingPeriod", fin(2025), 10)], "2026-03-01")
    postes = {
        "capex": {"type": "flux", "partielle_autorisee": True, "sommes": [[
            "ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
            "ifrs-full:PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities"]]},
        "reserves": {"type": "stock", "partielle_autorisee": False, "sommes": [[
            "ifrs-full:RetainedEarningsExcludingProfitLossForReportingPeriod",
            "ifrs-full:RetainedEarningsProfitLossForReportingPeriod"]]},
    }
    ex = N.extraire_rapport(r, postes)
    capex = ex["capex"][D(2025, 12, 31)]
    assert capex["valeur"] == 40 and "somme partielle" in capex["badges"][0]
    assert ex["reserves"] == {}                     # composant manquant : pas de valeur inventée


def test_extension_societe_utilisee_seulement_en_dernier_recours():
    r = rapport(2021, [fait("thermador:OperatingProfit", annee(2021), 51)], "2022-03-01")
    postes = {"ebit": {"type": "flux", "concepts": ["ifrs-full:ProfitLossFromOperatingActivities"]}}
    ext = {"ebit": {"concepts": ["thermador:OperatingProfit"], "source": "test"}}
    v = N.extraire_rapport(r, postes, ext)["ebit"][D(2021, 12, 31)]
    assert v["valeur"] == 51 and "concept propre" in v["badges"][0]


def test_cfo_ne_prend_jamais_la_ligne_avant_bfr():
    """Hermès FY2025 (rapport réel, vérifié à la main) : la ligne « avant variation du BFR »
    (ifrs-full:CashFlowsFromUsedInOperationsBeforeChangesInWorkingCapital, 5 607 M€) ne doit
    jamais être retenue à la place de la ligne finale (ifrs-full:CashFlowsFromUsedInOperating-
    Activities, 5 374 M€), même si les deux sont balisées dans le rapport."""
    r = rapport(2025, [
        fait("ifrs-full:CashFlowsFromUsedInOperationsBeforeChangesInWorkingCapital", annee(2025), 5_607_000_000),
        fait("ifrs-full:CashFlowsFromUsedInOperatingActivities", annee(2025), 5_374_000_000),
    ], "2026-03-24")
    from pipeline.common import mapping
    postes = {"cash_flow_operationnel": mapping()["postes"]["cash_flow_operationnel"]}
    ex = N.extraire_rapport(r, postes)
    assert ex["cash_flow_operationnel"][D(2025, 12, 31)]["valeur"] == 5_374_000_000


# --------------------------------------------------------------------------- fusion
def _deux_rapports(bnpa_orig, bnpa_retraite, ca_retraite=1000):
    r1 = rapport(2021, [fait("ifrs-full:Revenue", annee(2021), 1000), fait("ifrs-full:Revenue", annee(2020), 900),
                        fait("ifrs-full:BasicEarningsLossPerShare", annee(2021), bnpa_orig, "iso4217:EUR/xbrli:shares"),
                        fait("ifrs-full:BasicEarningsLossPerShare", annee(2020), 12.0, "iso4217:EUR/xbrli:shares")],
                 "2022-03-15")
    r2 = rapport(2022, [fait("ifrs-full:Revenue", annee(2022), 1100), fait("ifrs-full:Revenue", annee(2021), ca_retraite),
                        fait("ifrs-full:BasicEarningsLossPerShare", annee(2022), 4.5, "iso4217:EUR/xbrli:shares"),
                        fait("ifrs-full:BasicEarningsLossPerShare", annee(2021), bnpa_retraite, "iso4217:EUR/xbrli:shares")],
                 "2023-03-15")
    return [r1, r2]


def test_fusion_prend_le_rapport_le_plus_recent_et_trace_l_origine():
    s = N.fusionner_rapports(_deux_rapports(16.0, 4.0, ca_retraite=990))
    v = s["chiffre_affaires"][D(2021, 12, 31)]
    assert v["valeur"] == 990 and v["valeur_origine"] == 1000
    assert any(b.startswith("retraité") for b in v["badges"])


def test_ca_ebit_non_revertis_meme_si_ecart_important():
    """Portée de la règle « retraitement non expliqué → valeur d'origine conservée » (item 19) :
    limitée à bnpa/nombre_actions. Le chiffre d'affaires (ici un écart de 20 %, ex. activités
    abandonnées reclassées — bien en dessous du seuil d'incohérence de 50 % qui exclurait tout
    le rapport) reste gouverné par `fusionner_rapports` : le rapport le plus récent (990... ici
    800, écart 20 %) reste la référence, `ajuster_splits` ne le touche pas (il n'agit que sur
    bnpa/nombre_actions, cf. la boucle `for poste in ("bnpa", "nombre_actions")`)."""
    s = N.fusionner_rapports(_deux_rapports(16.0, 4.0, ca_retraite=800))   # 1000 → 800, -20 %
    v_avant = dict(s["chiffre_affaires"][D(2021, 12, 31)])
    N.ajuster_splits(s, [])                                                # aucun split : bnpa/actions reversés
    v_apres = s["chiffre_affaires"][D(2021, 12, 31)]
    assert v_apres["valeur"] == 800 == v_avant["valeur"]                   # inchangé par ajuster_splits
    assert v_apres["valeur_origine"] == 1000                               # toujours tracé, pas restauré
    assert any(b.startswith("retraité") for b in v_apres["badges"])
    assert s["bnpa"][D(2021, 12, 31)]["valeur"] == 16.0                    # bnpa, lui, est reversé (portée limitée)


def test_split_explique_et_etendu_aux_exercices_anciens():
    s = N.fusionner_rapports(_deux_rapports(16.0, 4.0))
    journal = N.ajuster_splits(s, [{"date": "2022-05-13", "ratio": 4.0}])
    assert s["bnpa"][D(2021, 12, 31)]["valeur"] == 4.0                 # déjà retraité par le rapport 2022
    assert s["bnpa"][D(2020, 12, 31)]["valeur"] == pytest.approx(3.0)  # 12 / 4, ajusté du split yfinance
    assert any(j.get("explique") and j.get("facteur_observe") == 4.0 for j in journal)


def test_retraitement_sans_split_non_explique_valeur_origine_conservee():
    """Retraitement non expliqué (règle ajoutée) : on n'applique pas le comparatif du rapport le
    plus récent (4.0) sans preuve — on revient à la valeur d'origine du rapport de l'exercice
    (16.0, cas Boliden réel : nombre_actions FY2021 273 511 169 conservé, pas le comparatif ÷100
    du rapport FY2022)."""
    s = N.fusionner_rapports(_deux_rapports(16.0, 4.0))
    journal = N.ajuster_splits(s, [])
    assert s["bnpa"][D(2020, 12, 31)]["valeur"] == 12.0                # pas d'extension
    assert s["bnpa"][D(2021, 12, 31)]["valeur"] == 16.0                # valeur d'origine conservée
    assert any(j["explique"] is False and j["valeur_retenue"] == 16.0 and j["valeur_ecartee"] == 4.0
              for j in journal)
    assert any("non expliqué" in b for b in s["bnpa"][D(2021, 12, 31)]["badges"])
    assert not any(b.startswith("retraité :") for b in s["bnpa"][D(2021, 12, 31)]["badges"])


def test_retraitement_non_explique_recoupe_avec_yfinance_actions():
    # Boliden réel : nombre_actions FY2021 273 511 169 (rapport FY2021) vs comparatif 2 735 111
    # (rapport FY2022, ÷100 sans split) → valeur d'origine conservée + recoupement yfinance.
    r1 = rapport(2021, [fait("ifrs-full:Revenue", annee(2021), 1000),
                        fait("ifrs-full:NumberOfSharesOutstanding", fin(2021), 273_511_169)], "2022-03-22")
    r2 = rapport(2022, [fait("ifrs-full:Revenue", annee(2022), 1100),
                        fait("ifrs-full:NumberOfSharesOutstanding", fin(2021), 2_735_111)], "2023-05-09")
    s = N.fusionner_rapports([r1, r2])
    journal = N.ajuster_splits(s, [], actions_yfinance=273_000_000.0)
    v = s["nombre_actions"][D(2021, 12, 31)]
    assert v["valeur"] == 273_511_169.0
    assert any("recoupement yfinance" in b for b in v["badges"])
    assert any(j["poste"] == "nombre_actions" and j.get("ecart_vs_yfinance_actuel") is not None for j in journal)


def test_extension_capex_signe_inverse_si_negatif():
    """Item 29 : l'extension Thermador tague un flux sortant négatif (convention du concept
    maison), alors que les concepts capex génériques du mapping sont des magnitudes positives —
    valeur absolue retenue, signalée par un badge."""
    r = rapport(2021, [fait("thermador:OutflowsForTheAcquisitionOfTangibleAndIntangibleFixedAssets",
                            annee(2021), -12221000)], "2022-03-01")
    postes = {"capex": {"type": "flux", "concepts": [
        "ifrs-full:PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets"]}}
    ext = {"capex": {"concepts": ["thermador:OutflowsForTheAcquisitionOfTangibleAndIntangibleFixedAssets"],
                     "source": "test"}}
    v = N.extraire_rapport(r, postes, ext)["capex"][D(2021, 12, 31)]
    assert v["valeur"] == 12221000
    assert any("signe inversé" in b for b in v["badges"])


def test_secours_ebit_et_dettes():
    r = rapport(2025, [fait("ifrs-full:ProfitLossBeforeTax", annee(2025), 100),
                       fait("ifrs-full:FinanceCosts", annee(2025), 15),
                       fait("ifrs-full:FinanceIncome", annee(2025), 5),
                       fait("ifrs-full:Assets", fin(2025), 500), fait("ifrs-full:Equity", fin(2025), 300),
                       fait("ifrs-full:NoncurrentLiabilities", fin(2025), 120)], "2026-03-01")
    s = N.fusionner_rapports([r])
    d = D(2025, 12, 31)
    assert s["ebit"][d]["valeur"] == 110 and "reconstitué" in s["ebit"][d]["badges"][0]
    assert s["dettes_totales"][d]["valeur"] == 200
    assert s["dettes_courantes"][d]["valeur"] == 80


def test_secours_marge_brute_par_difference():
    """Item 30 : GrossProfit non balisé mais CostOfSales oui (présentation par fonction sans
    sous-total de marge brute explicite, cas Valneva) → marge brute reconstituée = CA − coût
    des ventes, badge dédié."""
    r = rapport(2025, [fait("ifrs-full:Revenue", annee(2025), 220),
                       fait("ifrs-full:CostOfSales", annee(2025), 107)], "2026-03-01")
    s = N.fusionner_rapports([r])
    d = D(2025, 12, 31)
    assert s["marge_brute"][d]["valeur"] == 113
    assert "reconstituée" in s["marge_brute"][d]["badges"][0]


def test_pas_de_secours_marge_brute_si_gross_profit_balise():
    r = rapport(2025, [fait("ifrs-full:Revenue", annee(2025), 220),
                       fait("ifrs-full:GrossProfit", annee(2025), 130),
                       fait("ifrs-full:CostOfSales", annee(2025), 107)], "2026-03-01")
    s = N.fusionner_rapports([r])
    assert s["marge_brute"][D(2025, 12, 31)]["valeur"] == 130   # GrossProfit prioritaire


def test_rapport_incoherent_detecte():
    rapports = _deux_rapports(16.0, 16.0, ca_retraite=0.188)
    inc = N.rapports_incoherents(rapports, None)
    assert inc and inc[0]["fxo_id"] == "X-2022" and inc[0]["poste"] == "chiffre_affaires"


# --------------------------------------------------------------------------- contrôles d'identité
def _serie(**postes):
    # controler_identites ne parcourt que les vraies clôtures d'exercice (dates_clotures : une
    # date a un chiffre_affaires) : on en fournit un par défaut si le test n'en passe pas.
    d = D(2025, 12, 31)
    postes.setdefault("chiffre_affaires", 1.0)
    return {poste: {d: {"valeur": v}} for poste, v in postes.items()}


def test_quarantaine_bnpa_actions_si_pondere_balise_et_ecart():
    # Nombre d'actions moyen pondéré balisé : le contrôle peut conclure et quarantiner.
    s = _serie(bnpa=31.81, nombre_actions_moyen_pondere=2_735_111.0, resultat_net=8_701_000_000.0)
    r = N.controler_identites(s, CFG, "test")
    assert D(2025, 12, 31) not in s["bnpa"] and D(2025, 12, 31) not in s["nombre_actions_moyen_pondere"]
    assert len(r["quarantaine"]) == 2 and {j["poste_retire"] for j in r["quarantaine"]} == {"bnpa", "nombre_actions_moyen_pondere"}
    assert r["resume"]["2025-12-31"]["etats"]["bnpa_actions"] == "quarantaine"


def test_bnpa_actions_non_concluant_sans_pondere_balise_pas_de_quarantaine():
    # Valneva FY2022 (réel) : seul le nombre d'actions DE CLÔTURE est balisé (pas de moyenne
    # pondérée) → écart possible mais non concluant, AUCUNE quarantaine.
    s = _serie(bnpa=-1.24, nombre_actions=138_367_482.0, resultat_net=-143_279_000.0)
    r = N.controler_identites(s, CFG, "test")
    assert r["quarantaine"] == []
    assert D(2025, 12, 31) in s["bnpa"] and D(2025, 12, 31) in s["nombre_actions"]
    assert r["resume"]["2025-12-31"]["etats"]["bnpa_actions"] == "non_concluant"
    assert r["resume"]["2025-12-31"]["executes"] == 0          # seul contrôle possible ici, non concluant
    assert len(r["non_concluant"]) == 1


def test_pas_de_quarantaine_si_bnpa_actions_coherents():
    s = _serie(bnpa=43.15, nombre_actions_moyen_pondere=105_569_412.0, resultat_net=4_524_000_000.0)  # Hermès 2025
    r = N.controler_identites(s, CFG, "test")
    assert r["quarantaine"] == [] and D(2025, 12, 31) in s["bnpa"]
    assert r["resume"]["2025-12-31"]["etats"]["bnpa_actions"] == "ok"


def test_quarantaine_actif_incoherent_avec_passif_et_capitaux_propres():
    s = _serie(actif_total=1000.0, dettes_totales=400.0, capitaux_propres=400.0)  # 800 ≠ 1000
    r = N.controler_identites(s, CFG, "test")
    assert {j["poste_retire"] for j in r["quarantaine"]} == {"actif_total", "dettes_totales"}


def test_pas_de_quarantaine_actif_si_identite_comptable_respectee():
    s = _serie(actif_total=1000.0, dettes_totales=550.0, capitaux_propres=450.0)
    assert N.controler_identites(s, CFG, "test")["quarantaine"] == []


def test_quarantaine_marge_brute_superieure_au_ca():
    s = _serie(marge_brute=120.0, chiffre_affaires=100.0)
    r = N.controler_identites(s, CFG, "test")
    assert r["quarantaine"][0]["poste_retire"] == "marge_brute"


def test_quarantaine_marge_ebit_hors_bornes():
    s = _serie(ebit=250.0, chiffre_affaires=100.0)               # marge EBIT 250 % > 100 %
    r = N.controler_identites(s, CFG, "test")
    assert r["quarantaine"][0]["poste_retire"] == "ebit"


def test_controle_partiel_sous_le_seuil():
    # Seul actif_passif conclut (1/4 < seuil_partiel = 3) : "partiel", pas "non_controle".
    s = _serie(actif_total=1000.0, dettes_totales=550.0, capitaux_propres=450.0)
    r = N.controler_identites(s, CFG, "test")
    assert r["resume"]["2025-12-31"]["executes"] == 1
    assert r["resume"]["2025-12-31"]["partiel"] is True
    assert r["resume"]["2025-12-31"]["non_controle"] is False


def test_non_controle_si_aucun_controle_concluant():
    # Cas Brunello Cucinelli (rapport corrompu, hypothétique s'il n'était pas déjà écarté par
    # ailleurs) : seuls chiffre_affaires et bnpa sont balisés, aucun des 4 contrôles ne conclut.
    s = _serie(chiffre_affaires=188_000.0, bnpa=1986.5, resultat_net=141_989_000.0)
    r = N.controler_identites(s, CFG, "test")
    assert r["resume"]["2025-12-31"]["non_controle"] is True
    assert r["resume"]["2025-12-31"]["executes"] == 0


def test_pas_de_quarantaine_marge_ebit_dans_les_bornes():
    s = _serie(ebit=-80.0, chiffre_affaires=100.0)                # marge EBIT -80 %, dans [-100 %, 100 %]
    assert N.controler_identites(s, CFG, "test")["quarantaine"] == []


# --------------------------------------------------------------------------- marché / BCE
def test_taux_bce_a_la_date_avec_jour_sans_fixing():
    taux = pd.Series([11.0, 11.5], index=pd.to_datetime(["2026-01-02", "2026-01-05"]))
    dates = pd.Series(pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-05"]))
    t, sans = M.taux_a_la_date(taux, dates)
    assert list(t) == [11.0, 11.0, 11.5] and sans == 1


def test_volume_moyen_eur_conversion_au_taux_du_jour(monkeypatch):
    taux = pd.Series([10.0, 20.0], index=pd.to_datetime(["2026-01-02", "2026-01-05"]))
    monkeypatch.setattr(M, "taux_bce", lambda devise: taux)
    cours = pd.DataFrame({"Date": pd.to_datetime(["2026-01-02", "2026-01-05"]),
                          "Close": [100.0, 100.0], "Volume": [1000, 1000]})
    r = M.volume_moyen_eur(cours, "SEK", 2)
    assert r["valeur"] == pytest.approx((100_000 / 10 + 100_000 / 20) / 2)


def test_conversion_meme_devise():
    assert M.convertir(5.0, "EUR", "EUR", D(2026, 1, 2)) == (5.0, "même devise")
