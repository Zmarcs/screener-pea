"""Verdict déterministe (methode.md) + règles ajoutées :
- un critère de porte non évaluable (sans aucun ❌) plafonne le verdict à SURVEILLANCE ;
- un ACHAT/REJET déterminé par le score sur un univers trop petit (< min_univers_verdict)
  devient PROVISOIRE : pas de décision définitive tant que le score n'est pas significatif,
  mais on affiche ce que serait le verdict."""
from __future__ import annotations

from .porte import KO, NE, OK

ACHAT, SURVEILLANCE, REJET, PROVISOIRE, INDETERMINE = \
    "ACHAT", "SURVEILLANCE", "REJET", "PROVISOIRE", "INDÉTERMINÉ"


def _verdict_brut(statut_porte: str, score: float | None, signal_timing: str, cfg_v: dict) -> dict:
    achat, surv = cfg_v["seuil_achat"], cfg_v["seuil_surveillance"]
    if statut_porte == KO:
        return {"verdict": REJET, "raison": "porte ❌"}
    if score is None:
        return {"verdict": INDETERMINE, "raison": "score QVM indisponible"}
    if score < surv:
        return {"verdict": REJET, "raison": f"score {score:.0f} < {surv}"}
    if statut_porte == NE:
        return {"verdict": SURVEILLANCE,
                "raison": "critère(s) de porte non évaluable(s) : verdict plafonné à SURVEILLANCE"}
    if score >= achat and signal_timing == "vert":
        return {"verdict": ACHAT, "raison": f"porte ✅, score {score:.0f} ≥ {achat}, timing 🟢"}
    detail = f"score {score:.0f} entre {surv} et {achat}" if score < achat else "timing non 🟢"
    return {"verdict": SURVEILLANCE, "raison": f"porte ✅, {detail}"}


def verdict(statut_porte: str, score: float | None, signal_timing: str, cfg_v: dict,
           taille_univers: int | None = None, seuil_univers: int | None = None) -> dict:
    """taille_univers / seuil_univers : nombre de sociétés dans l'univers de calcul des
    percentiles QVM, et seuil minimal (qvm.min_univers_verdict) pour qu'un ACHAT ou un REJET
    déterminé PAR LE SCORE soit définitif (un REJET dû à la porte ❌ n'est jamais concerné :
    ce n'est pas une décision du score)."""
    base = _verdict_brut(statut_porte, score, signal_timing, cfg_v)
    non_significatif = (taille_univers is not None and seuil_univers is not None
                        and taille_univers < seuil_univers)
    rejet_par_score = base["verdict"] == REJET and statut_porte != KO
    if non_significatif and (base["verdict"] == ACHAT or rejet_par_score):
        return {"verdict": PROVISOIRE,
                "raison": f"score non significatif (univers {taille_univers} < {seuil_univers}) : "
                          f"serait {base['verdict']} ({base['raison']})",
                "verdict_indicatif": base["verdict"]}
    return base


def badge_donnees_non_recoupees(verdict_: str, source_fondamentaux: str) -> str | None:
    """Règle ajoutée (item 26) : un REJET fondé sur des données 100 % yfinance (aucun rapport
    ESEF pour recouper, ex. Sidetrade) porte un badge d'avertissement — le rejet n'a pas pu être
    confirmé par une source indépendante, contrairement aux rejets appuyés sur des données ESEF."""
    if verdict_ == REJET and source_fondamentaux == "yfinance":
        return "REJET sur données non recoupées"
    return None


def marge_critere(code: str, c: dict) -> float | None:
    """Marge relative au seuil (négative = échec). Sert à trouver le critère « le plus juste »."""
    try:
        if code in ("P1", "P3"):
            return (c["valeur"] - c["seuil"]) / abs(c["seuil"])
        if code == "P2":
            return (c["marge_ebit"] - c["seuil_ebit_strict"]) / c["seuil_ebit_strict"]
        if code == "P4":
            return (c["score"] - c["seuil"]) / c["seuil"]
        if code == "P5":
            return (c["valeur"] - c["seuil"]) / c["seuil"]
        if code == "P6":
            return (c["valeur"] - c["seuil"]) / c["seuil"]
    except (KeyError, TypeError, ZeroDivisionError):
        return None
    return None


def justification(criteres: dict[str, dict], sous_scores: dict[str, float | None]) -> list[str]:
    """3 points : critère de porte le plus juste, meilleur sous-score, pire sous-score."""
    points = []
    marges = {k: marge_critere(k, c) for k, c in criteres.items() if c.get("statut") in (OK, KO)}
    marges = {k: m for k, m in marges.items() if m is not None}
    if marges:
        k = min(marges, key=lambda x: abs(marges[x]) if criteres[x]["statut"] == OK else -1e9 + marges[x])
        etat = "✅" if criteres[k]["statut"] == OK else "❌"
        points.append(f"Critère de porte le plus juste : {k} {etat} (écart au seuil {marges[k]:+.0%})")
    else:
        points.append("Critère de porte le plus juste : aucun critère évaluable")
    dispo = {k: v for k, v in sous_scores.items() if v is not None}
    if dispo:
        best = max(dispo, key=dispo.get)
        worst = min(dispo, key=dispo.get)
        points.append(f"Meilleur sous-score : {best} ({dispo[best]:.0f}/100)")
        points.append(f"Pire sous-score : {worst} ({dispo[worst]:.0f}/100)")
    return points
