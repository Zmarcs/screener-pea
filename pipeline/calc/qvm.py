"""Étage 2 — Score QVM (0 à 100) par percentiles sectoriels.

- Percentile calculé dans le secteur si le secteur compte au moins `min_societes_secteur`
  sociétés ayant la métrique ; sinon sur l'univers entier (methode.md).
- HYPOTHÈSE (formule du percentile) : p = (nb de valeurs inférieures + 0,5 × nb d'égales
  hors soi) / (n − 1) × 100 ; la meilleure valeur vaut 100, la pire 0 ; n = 1 → 50.
  Pour les métriques « plus bas = mieux », p est inversé (100 − p).
- Sous-score = moyenne des percentiles disponibles (métrique manquante exclue, jamais remplacée).
- Score = moyenne pondérée des sous-scores disponibles, poids renormalisés si un sous-score
  manque entièrement (HYPOTHÈSE, signalée par le badge « score partiel »).
"""
from __future__ import annotations

import statistics

# code → (sous-score, sens) ; sens +1 = plus haut = mieux, −1 = plus bas = mieux
METRIQUES = {
    "Q1": ("qualite", +1), "Q2": ("qualite", +1), "Q3": ("qualite", -1), "Q4": ("qualite", -1),
    "V1": ("valeur", +1), "V2": ("valeur", -1), "V3": ("valeur", +1),
    "M1": ("momentum", +1), "M2": ("momentum", +1), "M3": ("momentum", +1),
}
LIBELLES = {
    "Q1": "ROCE = EBIT / (actif total − dettes courantes)",
    "Q2": "Conversion FCF = (CFO − capex) / résultat net",
    "Q3": "Accruals = (résultat net − CFO) / actif total",
    "Q4": "Écart-type de la marge EBIT sur 5 ans",
    "V1": "Rendement EBIT / EV",
    "V2": "PER (dernier exercice publié) / médiane du PER sur 5 ans",
    "V3": "Rendement FCF = FCF / capitalisation",
    "M1": "Performance 12 mois hors dernier mois",
    "M2": "Force relative 6 mois vs STOXX Europe 600",
    "M3": "Variation du BNPA sur le dernier exercice",
}


def percentile(valeur: float, groupe: list[float]) -> float:
    n = len(groupe)
    if n <= 1:
        return 50.0
    inferieurs = sum(1 for g in groupe if g < valeur)
    egaux = sum(1 for g in groupe if g == valeur) - 1
    return 100.0 * (inferieurs + 0.5 * egaux) / (n - 1)


def calculer_percentiles(univers: list[dict], min_secteur: int) -> dict[str, dict]:
    """univers : [{id, secteur, metriques: {code: valeur|None}}].
    Renvoie {id: {code: {percentile, base, n}}}."""
    sortie: dict[str, dict] = {s["id"]: {} for s in univers}
    for code, (_, sens) in METRIQUES.items():
        avec = [s for s in univers if s["metriques"].get(code) is not None]
        for s in avec:
            meme_secteur = [x for x in avec if x["secteur"] == s["secteur"] and s["secteur"]]
            if len(meme_secteur) >= min_secteur:
                groupe, base = meme_secteur, f"secteur {s['secteur']}"
            else:
                groupe, base = avec, "univers entier (secteur < %d sociétés)" % min_secteur
            p = percentile(s["metriques"][code], [x["metriques"][code] for x in groupe])
            if sens < 0:
                p = 100.0 - p
            sortie[s["id"]][code] = {"percentile": p, "base": base, "n": len(groupe)}
    return sortie


def scores(percentiles: dict[str, dict], poids: dict[str, float]) -> dict:
    sous = {}
    for sous_score in poids:
        ps = [v["percentile"] for code, v in percentiles.items() if METRIQUES[code][0] == sous_score]
        sous[sous_score] = statistics.fmean(ps) if ps else None
    dispo = {k: v for k, v in sous.items() if v is not None}
    if not dispo:
        return {"sous_scores": sous, "score": None, "partiel": True}
    total_poids = sum(poids[k] for k in dispo)
    score = sum(poids[k] * v for k, v in dispo.items()) / total_poids
    return {"sous_scores": sous, "score": score, "partiel": len(dispo) < len(poids)}


# --------------------------------------------------------------------------- métriques
def _div(a, b):
    return None if a is None or b in (None, 0) else a / b


def metriques_fondamentales(d: dict) -> dict:
    """d : postes du dernier exercice (N) + historiques. Renvoie {code: {valeur, detail}}."""
    m = {}
    ebit, at, dc = d.get("ebit"), d.get("actif_total"), d.get("dettes_courantes")
    m["Q1"] = {"valeur": _div(ebit, None if None in (at, dc) else at - dc)}
    cfo, capex, rn = d.get("cash_flow_operationnel"), d.get("capex"), d.get("resultat_net")
    fcf = None if None in (cfo, capex) else cfo - capex
    if rn is not None and rn <= 0:
        m["Q2"] = {"valeur": None, "detail": "résultat net ≤ 0 : ratio non interprétable"}
    else:
        m["Q2"] = {"valeur": _div(fcf, rn)}
    m["Q3"] = {"valeur": _div(None if None in (rn, cfo) else rn - cfo, at)}
    marges = d.get("marges_ebit_5ans") or []
    m["Q4"] = ({"valeur": statistics.pstdev(marges), "detail": f"{len(marges)} exercices"}
               if len(marges) >= 2 else {"valeur": None, "detail": "moins de 2 marges EBIT"})
    return m


def metriques_valeur(d: dict) -> dict:
    """Toutes les valeurs dans la devise publiée des comptes (capitalisation convertie si besoin)."""
    m = {}
    capi, ebit = d.get("capitalisation"), d.get("ebit")
    dlt, dct, treso = d.get("dette_long_terme"), d.get("dette_court_terme"), d.get("tresorerie")
    if None in (capi, dlt, dct, treso):
        manq = [k for k, v in (("capitalisation", capi), ("dette_long_terme", dlt),
                                ("dette_court_terme", dct), ("tresorerie", treso)) if v is None]
        m["V1"] = {"valeur": None, "detail": "EV incalculable : " + ", ".join(manq) + " indisponible(s)"}
    else:
        ev = capi + dlt + dct - treso
        m["V1"] = {"valeur": _div(ebit, ev) if ev > 0 else None, "ev": ev,
                   "detail": None if ev > 0 else "EV ≤ 0"}
    per, med = d.get("per_actuel"), d.get("per_mediane_5ans")
    if per is None or per <= 0:
        m["V2"] = {"valeur": None, "detail": "PER actuel négatif ou indisponible : exclu"}
    elif med is None:
        m["V2"] = {"valeur": None, "detail": "aucun PER historique positif"}
    else:
        m["V2"] = {"valeur": per / med}
    fcf = None if None in (d.get("cash_flow_operationnel"), d.get("capex")) \
        else d["cash_flow_operationnel"] - d["capex"]
    m["V3"] = {"valeur": _div(fcf, capi)}
    return m


def metriques_momentum(cours: list[float], indice: list[float], bnpa_n, bnpa_n1, cfg_m: dict) -> dict:
    """cours / indice : clôtures chronologiques (dernière = aujourd'hui)."""
    m = {}
    s12, s1, s6 = cfg_m["seances_12m"], cfg_m["seances_1m"], cfg_m["seances_6m"]
    if len(cours) > s12:
        m["M1"] = {"valeur": cours[-1 - s1] / cours[-1 - s12] - 1}
    else:
        m["M1"] = {"valeur": None, "detail": "moins de 12 mois de cours"}
    if len(cours) > s6 and len(indice) > s6:
        m["M2"] = {"valeur": (cours[-1] / cours[-1 - s6]) / (indice[-1] / indice[-1 - s6]) - 1}
    else:
        m["M2"] = {"valeur": None, "detail": "moins de 6 mois de cours"}
    if bnpa_n is None or bnpa_n1 in (None, 0):
        m["M3"] = {"valeur": None, "detail": "BNPA N ou N−1 indisponible ou nul"}
    else:
        m["M3"] = {"valeur": (bnpa_n - bnpa_n1) / abs(bnpa_n1)}
    return m
