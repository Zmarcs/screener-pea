"""Étage 1 — Porte (éliminatoire). Fonctions pures : entrées = nombres, sorties = dicts.

Statuts : "ok" (✅), "ko" (❌), "ne" (non évaluable : historique insuffisant ou donnée
indisponible ; jamais ✅, plafonne le verdict à SURVEILLANCE).
"""
from __future__ import annotations

import math

OK, KO, NE = "ok", "ko", "ne"


# --------------------------------------------------------------------------- outils
def cagr(debut: float | None, fin: float | None, annees: int) -> tuple[float | None, str | None]:
    """Taux de croissance annuel composé. Non calculable si une borne est ≤ 0 ou absente."""
    if debut is None or fin is None:
        return None, "donnée indisponible"
    if annees <= 0:
        return None, "moins de 2 exercices"
    if debut <= 0:
        return None, f"valeur de départ ≤ 0 ({debut:g}) : CAGR non calculable"
    if fin <= 0:
        return None, f"valeur d'arrivée ≤ 0 ({fin:g}) : CAGR non calculable"
    return (fin / debut) ** (1 / annees) - 1, None


def annees_en_baisse(valeurs: list[float]) -> int:
    return sum(1 for a, b in zip(valeurs, valeurs[1:]) if b < a)


def regression(xs: list[float], ys: list[float]) -> float | None:
    """Pente des moindres carrés de y en fonction de x."""
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def pente_log_lineaire(annees: list[int], valeurs: list[float]) -> float | None:
    """Croissance annuelle implicite de la régression de ln(valeur) : exp(pente) − 1."""
    if len(valeurs) < 2 or any(v <= 0 for v in valeurs):
        return None
    p = regression([float(a) for a in annees], [math.log(v) for v in valeurs])
    return None if p is None else math.exp(p) - 1


def _fenetre(points: list[tuple[int, float]], cfg_hist: dict) -> list[tuple[int, float]]:
    """Derniers (fenetre_exercices + 1) points : 5 variations = 6 exercices."""
    return points[-(cfg_hist["fenetre_exercices"] + 1):]


def _critere_croissance(points: list[tuple[int, float]], cagr_min: float, min_ex: int,
                        cfg_hist: dict, annees_atypiques: dict, max_baisses: int | None) -> dict:
    """Logique commune P1 (CA) / P3 (BNPA). points = [(année, valeur)] triés."""
    pts = _fenetre(points, cfg_hist)
    n = len(pts)
    res = {"exercices_disponibles": len(points), "exercices_utilises": n, "seuil": cagr_min,
           "min_exercices": min_ex, "serie": pts}
    if n < 2:
        return {**res, "statut": NE, "valeur": None, "libelle": "CAGR non calculable",
                "raison": f"{n} exercice(s) disponible(s)"}
    annees = n - 1
    base, fin = pts[0], pts[-1]
    v, raison = cagr(base[1], fin[1], annees)
    res.update({
        "valeur": v, "libelle": f"CAGR {annees} ans (FY{base[0]}→FY{fin[0]})",
        "annee_base": base[0], "note_base": annees_atypiques.get(base[0]),
        "pente_log": pente_log_lineaire([a for a, _ in pts], [x for _, x in pts]),
        "annees_en_baisse": annees_en_baisse([x for _, x in pts]),
        "raison_non_calculable": raison,
    })
    if n < min_ex:
        return {**res, "statut": NE,
                "raison": f"{n} exercices < {min_ex} requis : non évaluable (jamais ✅)"}
    if v is None:
        return {**res, "statut": KO, "raison": raison}
    ok = v >= cagr_min
    raisons = [] if ok else [f"CAGR {v:.1%} < {cagr_min:.0%}"]
    if max_baisses is not None and res["annees_en_baisse"] > max_baisses:
        ok = False
        raisons.append(f"{res['annees_en_baisse']} années en baisse > {max_baisses}")
    return {**res, "statut": OK if ok else KO, "raison": " ; ".join(raisons) or None}


# --------------------------------------------------------------------------- P1 à P3
def p1_croissance_ca(points, cfg: dict, min_ex: int | None = None) -> dict:
    c = cfg["porte"]["p1_croissance_ca"]
    return _critere_croissance(points, c["cagr_min"], min_ex or cfg["historique"]["min_exercices"],
                               cfg["historique"], cfg["historique"].get("annees_atypiques", {}), c["max_annees_baisse"])


def p3_croissance_bnpa(points, cfg: dict, min_ex: int | None = None) -> dict:
    """Règle ajoutée (item 23) : un BNPA de DÉPART ≤ 0 (perte, ex. Covid) alors que le DERNIER
    BNPA de la fenêtre est > 0 (retour aux bénéfices) n'est jamais ❌ — le CAGR classique n'est
    pas calculable (base ≤ 0) mais la société n'est plus déficitaire : "non évaluable", avec un
    CAGR indicatif calculé depuis la première année positive de la fenêtre à titre d'information.
    Le ❌ (CAGR non calculable) reste réservé aux sociétés encore déficitaires en fin de fenêtre
    (dernier BNPA ≤ 0, ex. Valneva)."""
    c = cfg["porte"]["p3_croissance_bnpa"]
    res = _critere_croissance(points, c["cagr_min"], min_ex or cfg["historique"]["min_exercices"],
                              cfg["historique"], cfg["historique"].get("annees_atypiques", {}), None)
    if res["statut"] == KO and res.get("valeur") is None and res.get("serie"):
        pts = res["serie"]
        base, fin = pts[0], pts[-1]
        if base[1] <= 0 and fin[1] > 0:
            positifs = [p for p in pts if p[1] > 0]
            base_pos = positifs[0] if positifs else None
            annees_pos = fin[0] - base_pos[0] if base_pos else 0
            v_ind = cagr(base_pos[1], fin[1], annees_pos)[0] if base_pos and annees_pos > 0 else None
            return {**res, "statut": NE,
                   "raison": (f"BNPA de départ ≤ 0 (perte, FY{base[0]}) mais retour aux bénéfices "
                              f"(BNPA FY{fin[0]} > 0) : non évaluable, jamais ❌ (réservé aux "
                              "sociétés encore déficitaires)"),
                   "valeur_indicative": v_ind,
                   "libelle_indicatif": (f"CAGR {annees_pos} ans (FY{base_pos[0]}→FY{fin[0]}) depuis la "
                                        "première année positive" if v_ind is not None else None)}
    return res


def p2_marges(ca: dict[int, float], ebit: dict[int, float], rn: dict[int, float], cfg: dict,
              seuil_relatif: float | None = None) -> dict:
    """ca/ebit/rn : {année: valeur}. seuil_relatif = 3e quartile sectoriel de la marge EBIT."""
    c = cfg["porte"]["p2_marges"]
    annees = sorted(a for a in ca if a in ebit and ca[a])
    marges_ebit = {a: ebit[a] / ca[a] for a in annees}
    marges_ebit = dict(list(marges_ebit.items())[-(cfg["historique"]["fenetre_exercices"] + 1):])
    if not marges_ebit:
        return {"statut": NE, "statut_strict": NE, "statut_relatif": NE,
                "raison": "CA ou EBIT indisponible"}
    derniere = max(marges_ebit)
    m_ebit = marges_ebit[derniere]
    m_nette = rn[derniere] / ca[derniere] if derniere in rn and ca.get(derniere) else None
    pente = regression([float(a) for a in marges_ebit], [100 * m for m in marges_ebit.values()])

    def verdict(cond_ebit: bool | None) -> str:
        conds = [cond_ebit, None if m_nette is None else m_nette > c["marge_nette_min"],
                 None if pente is None else pente >= c["pente_marge_min_pts"]]
        if any(x is False for x in conds):
            return KO
        if any(x is None for x in conds):
            return NE
        return OK

    strict = verdict(m_ebit > c["marge_ebit_min"])
    relatif = verdict(None if seuil_relatif is None else m_ebit >= seuil_relatif)
    return {
        "exercice": derniere, "marge_ebit": m_ebit, "marge_nette": m_nette,
        "pente_marge_ebit_pts": pente, "marges_ebit": marges_ebit,
        "seuil_ebit_strict": c["marge_ebit_min"], "seuil_ebit_relatif": seuil_relatif,
        "seuil_marge_nette": c["marge_nette_min"], "seuil_pente": c["pente_marge_min_pts"],
        "statut_strict": strict, "statut_relatif": relatif,
        "statut": strict if cfg["porte"]["mode"] == "strict" else relatif,
    }


# --------------------------------------------------------------------------- P4 F-score
def _div(a, b):
    return None if a is None or b in (None, 0) else a / b


def fscore(n: dict, n1: dict) -> dict:
    """Piotroski sur 2 exercices. n, n1 : postes de l'exercice N et N−1 :
    resultat_net, cash_flow_operationnel, actif_total, dette_long_terme, actif_courant,
    dettes_courantes, nombre_actions (+ concept_actions), chiffre_affaires, marge_brute, ebit.
    Test indisponible = None (exclu de la somme, signalé)."""
    tests = []

    def ajout(code, libelle, point, vn=None, vn1=None, detail=None):
        tests.append({"code": code, "test": libelle, "point": point, "valeur_n": vn,
                      "valeur_n1": vn1, "detail": detail})

    roa_n = _div(n.get("resultat_net"), n.get("actif_total"))
    roa_n1 = _div(n1.get("resultat_net"), n1.get("actif_total"))
    ajout("F1", "ROA > 0", None if roa_n is None else int(roa_n > 0), roa_n)
    cfo = n.get("cash_flow_operationnel")
    ajout("F2", "Cash-flow opérationnel > 0", None if cfo is None else int(cfo > 0), cfo)
    ajout("F3", "ROA en hausse", None if None in (roa_n, roa_n1) else int(roa_n > roa_n1), roa_n, roa_n1)
    rn = n.get("resultat_net")
    ajout("F4", "Cash-flow opérationnel > résultat net",
          None if None in (cfo, rn) else int(cfo > rn), cfo, rn)

    lev_n = _div(n.get("dette_long_terme"), n.get("actif_total"))
    lev_n1 = _div(n1.get("dette_long_terme"), n1.get("actif_total"))
    ajout("F5", "Dette long terme / actif en baisse",
          None if None in (lev_n, lev_n1) else int(lev_n < lev_n1), lev_n, lev_n1)
    liq_n = _div(n.get("actif_courant"), n.get("dettes_courantes"))
    liq_n1 = _div(n1.get("actif_courant"), n1.get("dettes_courantes"))
    ajout("F6", "Ratio de liquidité courante en hausse",
          None if None in (liq_n, liq_n1) else int(liq_n > liq_n1), liq_n, liq_n1)
    a_n, a_n1 = n.get("nombre_actions"), n1.get("nombre_actions")
    if None not in (a_n, a_n1) and n.get("concept_actions") != n1.get("concept_actions"):
        ajout("F7", "Pas d'émission d'actions nouvelles", None, a_n, a_n1,
              "nombres d'actions de nature différente (concepts distincts) : non comparable")
    else:
        ajout("F7", "Pas d'émission d'actions nouvelles",
              None if None in (a_n, a_n1) else int(a_n <= a_n1), a_n, a_n1)

    substitution = n.get("marge_brute") is None or n1.get("marge_brute") is None
    num = "ebit" if substitution else "marge_brute"
    mb_n = _div(n.get(num), n.get("chiffre_affaires"))
    mb_n1 = _div(n1.get(num), n1.get("chiffre_affaires"))
    ajout("F8", "Marge brute en hausse" if not substitution else "Marge EBIT en hausse (substitut de la marge brute)",
          None if None in (mb_n, mb_n1) else int(mb_n > mb_n1), mb_n, mb_n1,
          "marge brute non publiée : remplacée par la marge EBIT" if substitution else None)
    rot_n = _div(n.get("chiffre_affaires"), n.get("actif_total"))
    rot_n1 = _div(n1.get("chiffre_affaires"), n1.get("actif_total"))
    ajout("F9", "Rotation de l'actif en hausse",
          None if None in (rot_n, rot_n1) else int(rot_n > rot_n1), rot_n, rot_n1)

    disponibles = [t for t in tests if t["point"] is not None]
    return {"score": sum(t["point"] for t in disponibles), "tests_disponibles": len(disponibles),
            "tests": tests, "substitution_marge_brute": substitution}


def fscore_f1_f3_f5_f9_ouverture(rn_n, rn_n1, at_n1, at_n2, dlt_n, dlt_n1, ca_n, ca_n1) -> dict:
    """F1, F3, F5, F9 recalculés avec l'actif total D'OUVERTURE (Piotroski original : actif au
    début de l'exercice, soit l'actif de CLÔTURE de l'exercice précédent), pour comparaison avec
    la variante « actif de clôture » retenue par le pipeline (hypothèse #10 du rapport d'étape 1).
    at_n1 = actif total à la clôture de l'exercice N−1 (= ouverture de N) ; at_n2 = actif total à
    la clôture de l'exercice N−2 (= ouverture de N−1). F2, F4, F6, F7, F8 ne dépendent pas de
    l'actif total : inchangés par cette variante."""
    roa_n, roa_n1 = _div(rn_n, at_n1), _div(rn_n1, at_n2)
    lev_n, lev_n1 = _div(dlt_n, at_n1), _div(dlt_n1, at_n2)
    rot_n, rot_n1 = _div(ca_n, at_n1), _div(ca_n1, at_n2)
    return {
        "F1": {"valeur_n": roa_n, "point": None if roa_n is None else int(roa_n > 0)},
        "F3": {"valeur_n": roa_n, "valeur_n1": roa_n1,
              "point": None if None in (roa_n, roa_n1) else int(roa_n > roa_n1)},
        "F5": {"valeur_n": lev_n, "valeur_n1": lev_n1,
              "point": None if None in (lev_n, lev_n1) else int(lev_n < lev_n1)},
        "F9": {"valeur_n": rot_n, "valeur_n1": rot_n1,
              "point": None if None in (rot_n, rot_n1) else int(rot_n > rot_n1)},
    }


# Statut (règle ajoutée, item 32) : ni ✅ ni ❌ — le calcul sur les seules années ESEF porte sur
# un exercice PLUS ANCIEN que l'exercice yfinance contesté ; il ne PROUVE pas que yfinance est
# faux, il montre seulement que la conclusion change selon la donnée retenue. "non fiable"
# suggérait à tort un verdict sur la véracité de yfinance : renommé.
DEPEND_DONNEE_NON_RECOUPEE = "dépend d'une donnée non recoupée"


def p2_fiabilite(source_fondamentaux: str, retard: dict | None, cfg: dict) -> dict | None:
    """Fiabilité de la marge EBIT retenue par P2 quand le dernier exercice utilisé vient (en
    tout ou partie) de yfinance : aucun rapport ESEF pour recouper (source 100 % yfinance,
    ex. SAP, Sidetrade) → "non recoupé" ; écart EBIT yfinance/ESEF > seuil sur l'exercice
    commun (retard de publication ESEF complété par yfinance, ex. Boliden) →
    DEPEND_DONNEE_NON_RECOUPEE. Dans les deux cas, le verdict est plafonné à SURVEILLANCE (comme
    un critère de porte non évaluable : on réutilise le statut NE pour bénéficier du même
    plafonnement)."""
    seuil = cfg["porte"]["p2_marges"]["seuil_ecart_ebit_yfinance"]
    if source_fondamentaux == "yfinance":
        return {"statut": "non recoupé", "raison": "aucun rapport ESEF pour recouper l'EBIT yfinance"}
    if retard:
        ebit = next((c for c in retard.get("comparaison_exercice_commun", []) if c["poste"] == "ebit"), None)
        if ebit and ebit.get("ecart") is not None and abs(ebit["ecart"]) > seuil:
            return {"statut": DEPEND_DONNEE_NON_RECOUPEE,
                    "raison": f"écart EBIT yfinance/ESEF de {ebit['ecart']:+.0%} sur l'exercice commun "
                              f"FY{retard['derniere_esef'][:4]} (seuil {seuil:.0%}) — dépend d'une donnée "
                              f"non recoupée (yfinance FY{retard['cloture_attendue'][:4]})"}
    return None


def fscore_convention(n: dict, n1: dict, at_n2: float | None) -> dict:
    """F-score de RÉFÉRENCE (règle ajoutée, remplace l'ancien calcul par défaut) : convention
    Piotroski ORIGINALE — actif D'OUVERTURE (= actif de clôture de l'exercice précédent) pour
    F1/F3/F5/F9 (à vérifier : c'est la convention généralement attribuée à Piotroski 2000, mais
    « actif moyen » est aussi utilisé dans certaines implémentations). F2/F4/F6/F7/F8 ne dépendent
    pas de l'actif total : inchangés.
    at_n2 : actif total à la clôture de l'exercice N−2 (= ouverture de N−1). S'il est
    indisponible (historique insuffisant), F1/F3/F5/F9 en convention d'ouverture sont NON
    ÉVALUABLES (test indisponible, comme n'importe quelle donnée manquante) — pas de repli
    silencieux sur la clôture. La convention « clôture » (actif à la clôture de l'exercice
    lui-même, ancien calcul par défaut) reste toujours calculée, renvoyée à titre INDICATIF
    sous la clé `cloture`."""
    clot = fscore(n, n1)
    if at_n2 is None:
        tests = [{**t, "point": None, "detail": "actif d'ouverture indisponible (historique insuffisant)"}
                 if t["code"] in ("F1", "F3", "F5", "F9") else t for t in clot["tests"]]
    else:
        ouv_1349 = fscore_f1_f3_f5_f9_ouverture(
            rn_n=n.get("resultat_net"), rn_n1=n1.get("resultat_net"),
            at_n1=n1.get("actif_total"), at_n2=at_n2,
            dlt_n=n.get("dette_long_terme"), dlt_n1=n1.get("dette_long_terme"),
            ca_n=n.get("chiffre_affaires"), ca_n1=n1.get("chiffre_affaires"))
        tests = [{**t, "point": ouv_1349[t["code"]]["point"], "valeur_n": ouv_1349[t["code"]].get("valeur_n"),
                 "valeur_n1": ouv_1349[t["code"]].get("valeur_n1")} if t["code"] in ouv_1349 else t
                for t in clot["tests"]]
    disponibles = [t for t in tests if t["point"] is not None]
    ouv = {"score": sum(t["point"] for t in disponibles), "tests_disponibles": len(disponibles),
          "tests": tests, "substitution_marge_brute": clot["substitution_marge_brute"]}
    return {**ouv, "convention": "ouverture", "convention_disponible": at_n2 is not None,
           "cloture": clot, "actif_ouverture_n2": at_n2}


def p4_fiabilite(p4_avec: dict, p4_fiable: dict) -> dict:
    """P4 calculé avec le dernier exercice (potentiellement yfinance, retard de publication ESEF)
    comparé au P4 calculé sur les seules années ESEF disponibles (N−1 vs N−2 — règle ajoutée,
    même principe que P2, voir p2_marges_fiabilite). Même statut → le calcul FIABLE devient la
    référence, gardé SANS plafonnement (comme P2 : la donnée douteuse ne change rien à la
    conclusion). Statut différent → DEPEND_DONNEE_NON_RECOUPEE, statut ramené à non évaluable
    (verdict plafonné à SURVEILLANCE, réutilise NE) : le calcul « fiable » porte sur un exercice
    PLUS ANCIEN que l'exercice yfinance contesté — il ne prouve pas que yfinance est faux, il
    montre seulement que la conclusion dépend de la donnée retenue."""
    if p4_fiable["statut"] == p4_avec["statut"]:
        return {**p4_fiable, "fiabilite_verifiee": {"conclusion_identique": True,
                "statut_avec_donnee_douteuse": p4_avec["statut"],
                "raison": "exercice le plus récent (yfinance) sans effet sur la conclusion : "
                          "même statut avec les seules données ESEF (N−1 vs N−2)."}}
    annee_yfinance = p4_avec.get("exercices", [None, None])[-1]
    annee_yfinance = annee_yfinance[:4] if annee_yfinance else "?"
    return {**p4_avec, "fiabilite": {"statut": DEPEND_DONNEE_NON_RECOUPEE,
            "raison": f"la conclusion dépend d'une donnée non recoupée (yfinance FY{annee_yfinance}) : "
                      f"données fiables seules (N−1 vs N−2, exercice plus ancien, ne prouve pas que "
                      f"yfinance est faux) = {p4_fiable['statut']} ; avec l'exercice yfinance = "
                      f"{p4_avec['statut']}."},
            "donnees_fiables": p4_fiable, "statut_calcule": p4_avec["statut"], "statut": NE,
            "raison": f"P4 dépend d'une donnée non recoupée (yfinance FY{annee_yfinance}) : données "
                      f"fiables seules (N−1 vs N−2) = {p4_fiable['statut']} "
                      f"({p4_fiable['score']}/{p4_fiable['tests_disponibles']}) ; avec l'exercice "
                      f"yfinance = {p4_avec['statut']} ({p4_avec['score']}/{p4_avec['tests_disponibles']})."}


def p2_marges_fiabilite(ca: dict[int, float], ebit: dict[int, float], rn: dict[int, float], cfg: dict,
                        seuil_relatif: float | None, source_fondamentaux: str, retard: dict | None) -> dict:
    """P2 calculé avec les SEULES données fiables (règle ajoutée, remplace le simple plafonnement) :
    - aucun rapport ESEF (source 100 % yfinance) : pas de repli possible → statut non évaluable
      ("non recoupé").
    - dernier exercice complété par yfinance et écart EBIT signalé (p2_fiabilite) : recalcule P2
      SANS cet exercice (sur les seules données ESEF, un exercice plus ancien) et compare au calcul
      avec la donnée douteuse. Même conclusion (même statut) → on la garde, la donnée douteuse n'y
      change rien (ex. Boliden, qui reste ❌ sur sa marge ESEF FY2024). Conclusion différente →
      statut non évaluable (DEPEND_DONNEE_NON_RECOUPEE) : le calcul sur années ESEF plus anciennes
      ne prouve pas que yfinance est faux, seulement que la conclusion dépend de la donnée retenue."""
    p2 = p2_marges(ca, ebit, rn, cfg, seuil_relatif)
    fiab = p2_fiabilite(source_fondamentaux, retard, cfg)
    if fiab is None:
        return p2
    if fiab["statut"] == "non recoupé":
        return {**p2, "fiabilite": fiab, "statut_calcule": p2["statut"],
                "statut_strict_calcule": p2["statut_strict"], "statut_relatif_calcule": p2["statut_relatif"],
                "statut": NE, "statut_strict": NE, "statut_relatif": NE, "raison": fiab["raison"]}
    annee_douteuse = int(retard["cloture_attendue"][:4])
    ca_f = {a: v for a, v in ca.items() if a != annee_douteuse}
    ebit_f = {a: v for a, v in ebit.items() if a != annee_douteuse}
    rn_f = {a: v for a, v in rn.items() if a != annee_douteuse}
    p2_fiable = p2_marges(ca_f, ebit_f, rn_f, cfg, seuil_relatif)
    if p2_fiable["statut"] == p2["statut"]:
        return {**p2_fiable, "fiabilite_verifiee": {**fiab, "conclusion_identique": True,
                "statut_avec_donnee_douteuse": p2["statut"],
                "raison": fiab["raison"] + " — sans effet sur la conclusion : même statut avec "
                          "les seules données ESEF fiables."}}
    return {**p2, "fiabilite": fiab, "donnees_fiables": p2_fiable, "statut_calcule": p2["statut"],
            "statut_strict_calcule": p2["statut_strict"], "statut_relatif_calcule": p2["statut_relatif"],
            "statut": NE, "statut_strict": NE, "statut_relatif": NE,
            "raison": fiab["raison"] + f" — la conclusion dépend de la donnée douteuse "
                      f"(données fiables seules : {p2_fiable['statut']} ; avec yfinance : {p2['statut']})."}


def p4_fscore(f: dict, cfg: dict) -> dict:
    seuil = cfg["porte"]["p4_fscore"]["min"]
    manquants = 9 - f["tests_disponibles"]
    if f["score"] >= seuil:
        statut, raison = OK, None
    elif f["score"] + manquants < seuil:
        statut, raison = KO, f"F-score {f['score']} < {seuil}"
    else:
        statut, raison = NE, (f"F-score partiel : {f['score']}/{f['tests_disponibles']} tests évaluables "
                              f"({manquants} indisponible(s) pourraient changer le résultat)")
    return {**f, "seuil": seuil, "statut": statut, "raison": raison,
            "partiel": manquants > 0}


# --------------------------------------------------------------------------- P5 Z''
def zscore(bfr_actif_courant, dettes_courantes, reserves, ebit, actif_total, capitaux_propres,
           dettes_totales, coefs: dict) -> dict:
    postes = {"actif_courant": bfr_actif_courant, "dettes_courantes": dettes_courantes,
              "reserves": reserves, "ebit": ebit, "actif_total": actif_total,
              "capitaux_propres": capitaux_propres, "dettes_totales": dettes_totales}
    manquants = [k for k, v in postes.items() if v is None]
    if manquants or not actif_total or not dettes_totales:
        return {"valeur": None, "manquants": manquants or ["actif_total/dettes_totales nul"], "postes": postes}
    x1 = (bfr_actif_courant - dettes_courantes) / actif_total
    x2 = reserves / actif_total
    x3 = ebit / actif_total
    x4 = capitaux_propres / dettes_totales
    z = coefs["x1"] * x1 + coefs["x2"] * x2 + coefs["x3"] * x3 + coefs["x4"] * x4
    return {"valeur": z, "x1": x1, "x2": x2, "x3": x3, "x4": x4, "postes": postes, "manquants": []}


def p5_zscore(z: dict, cfg: dict) -> dict:
    c = cfg["porte"]["p5_zscore"]
    if z["valeur"] is None:
        return {**z, "statut": NE, "zone": None, "raison": "donnée(s) indisponible(s) : " + ", ".join(z["manquants"])}
    v = z["valeur"]
    zone = "saine" if v > c["seuil_sain"] else ("grise" if v > c["seuil_detresse"] else "détresse")
    statut = OK if v > c["seuil_detresse"] else KO
    return {**z, "statut": statut, "zone": zone, "seuil": c["seuil_detresse"],
            "raison": None if statut == OK else f"Z'' {v:.2f} ≤ {c['seuil_detresse']} (détresse)"}


# --------------------------------------------------------------------------- P6
def p6_liquidite(volume: dict, cfg: dict) -> dict:
    seuil = cfg["porte"]["p6_liquidite"]["volume_moyen_min_eur"]
    v = volume.get("valeur")
    if v is None:
        return {**volume, "statut": NE, "seuil": seuil}
    return {**volume, "seuil": seuil, "statut": OK if v > seuil else KO,
            "raison": None if v > seuil else f"volume moyen {v:,.0f} € ≤ {seuil:,} €"}


# --------------------------------------------------------------------------- synthèse
def statut_global(statuts: list[str]) -> str:
    if KO in statuts:
        return KO
    if NE in statuts:
        return NE
    return OK
