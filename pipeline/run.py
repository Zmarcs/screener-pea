"""Point d'entrée : .venv/bin/python -m pipeline.run

Chaîne : identification (LEI) → ESEF (ou repli yfinance) → normalisation → splits →
corrections manuelles → marché → Porte / QVM / Timing → verdict → data/processed/.
"""
from __future__ import annotations

import datetime as dt
import statistics
from collections import Counter

import numpy as np

from . import identify, ingest_esef, ingest_fallback, ingest_market, manual, normalize
from .calc import porte as P
from .calc import qvm as Q
from .calc import timing as T
from .calc import verdict as V
from .common import DOSSIER_SORTIE, JOURNAL, RACINE, aujourd_hui, charger_yaml, config, ecrire_json, mapping


# --------------------------------------------------------------------------- utilitaires
def cloture_attendue(derniere: dt.date, delai_mois: int, today: dt.date) -> dt.date:
    """Dernière clôture (même jour/mois que `derniere`) dont le délai légal de publication
    est écoulé à la date `today`."""
    import calendar

    def plus_mois(d: dt.date, n: int) -> dt.date:
        a, m = divmod(d.month - 1 + n, 12)
        annee, mois = d.year + a, m + 1
        return dt.date(annee, mois, min(d.day, calendar.monthrange(annee, mois)[1]))

    d = derniere
    while True:
        suivante = d.replace(year=d.year + 1)
        if plus_mois(suivante, delai_mois) < today:   # échéance légale dépassée
            d = suivante
        else:
            return d


def valeurs_annee(series: dict, d: dt.date) -> dict:
    sortie = {p: (s.get(d) or {}).get("valeur") for p, s in series.items()}
    sortie["concept_actions"] = (series.get("nombre_actions", {}).get(d) or {}).get("concept")
    return sortie


def par_annee(serie: dict) -> dict[int, float]:
    return {d.year: v["valeur"] for d, v in serie.items() if v.get("valeur") is not None}


def cours_a_date(cours, d: dt.date):
    sous = cours[cours["Date"] <= np.datetime64(d)]
    if sous.empty:
        return None, None
    ligne = sous.iloc[-1]
    return float(ligne["Close"]), ligne["Date"].date()


def serialiser_series(series: dict) -> dict:
    return {p: {d.isoformat(): v for d, v in sorted(s.items())} for p, s in series.items()}


# --------------------------------------------------------------------------- collecte
def collecter(soc: dict, cfg: dict) -> dict:
    isin, ticker = soc["isin"], soc["ticker"]
    print(f"\n=== {soc['nom']} ({isin}, {ticker})")
    ident = identify.identifier(isin)
    lei = ident["lei"]
    res = {"societe": soc, "identite": ident, "cle": lei or f"ISIN-{isin}", "badges": []}

    # ---- fondamentaux ESEF
    retenus, ecartes = ([], [])
    if lei:
        retenus, ecartes = ingest_esef.selectionner_rapports(lei)
    if not lei:
        res["statut_esef"] = "ESEF introuvable (LEI introuvable)"
    elif not retenus:
        res["statut_esef"] = "ESEF introuvable (aucun rapport indexé pour ce LEI)"
    else:
        res["statut_esef"] = f"ESEF : {len(retenus)} rapport(s) retenu(s)"
    res["rapports_esef"] = [{k: v for k, v in r.items() if k not in ("faits", "faits_doublons")} for r in retenus]
    res["rapports_ecartes"] = [{k: v for k, v in r.items() if k not in ("faits", "faits_doublons")} for r in ecartes]

    # Contrôle de cohérence entre rapports successifs (erreurs de balisage de l'émetteur)
    incoherences = normalize.rapports_incoherents(retenus, lei) if retenus else []
    res["incoherences_rapports"] = incoherences
    exclus = {i["fxo_id"] for i in incoherences}
    if exclus:
        for i in incoherences:
            JOURNAL.avertissement(res["cle"], f"rapport {i['fxo_id']} exclu : comparatif {i['poste']} "
                                  f"{i['exercice']} = {i['valeur_comparatif']:g} contre "
                                  f"{i['valeur_rapport_precedent']:g} publié dans {i['rapport_precedent']}")
        res["rapports_ecartes"] += [{k: v for k, v in r.items() if k not in ("faits", "faits_doublons")}
                                    | {"motif": "incohérent avec le rapport précédent (erreur de balisage probable)"}
                                    for r in retenus if r["fxo_id"] in exclus]
        retenus = [r for r in retenus if r["fxo_id"] not in exclus]
        res["rapports_esef"] = [r for r in res["rapports_esef"] if r["fxo_id"] not in exclus]
        res["statut_esef"] = f"ESEF : {len(retenus)} rapport(s) retenu(s), {len(exclus)} exclu(s) pour incohérence"

    if retenus:
        series = normalize.fusionner_rapports(retenus, lei)
        res["source_fondamentaux"] = "ESEF"
        # Cohérence des doublons (autres langues, dépôts remplacés)
        postes = mapping()["postes"]
        ext = (mapping().get("extensions") or {}).get(lei, {})
        controles = []
        for r in retenus:
            principal = normalize.extraire_rapport(r, postes, ext)
            for fxo, faits in zip(r.get("doublons", []), r.get("faits_doublons", [])):
                autre = normalize.extraire_rapport({**r, "faits": faits, "fxo_id": fxo}, postes, ext)
                cl = dt.date.fromisoformat(r["cloture"])
                for p in ("chiffre_affaires", "resultat_net", "actif_total", "bnpa"):
                    a = principal.get(p, {}).get(cl, {}).get("valeur")
                    b = autre.get(p, {}).get(cl, {}).get("valeur")
                    controles.append({"retenu": r["fxo_id"], "doublon": fxo, "poste": p,
                                      "valeur_retenue": a, "valeur_doublon": b, "identique": a == b})
        res["controle_doublons"] = controles
        for c in controles:
            if not c["identique"]:
                JOURNAL.avertissement(res["cle"], f"doublon {c['doublon']} : {c['poste']} "
                                                  f"{c['valeur_doublon']} ≠ {c['valeur_retenue']}")
    else:
        series = ingest_fallback.fondamentaux_yfinance(ticker, "historique court (repli yfinance : ESEF introuvable)")
        res["source_fondamentaux"] = "yfinance"
        res["badges"].append("historique court")

    # ---- données en retard : dernier exercice attendu non indexé
    clotures = normalize.dates_clotures(series)
    if clotures and res["source_fondamentaux"] == "ESEF":
        attendue = cloture_attendue(clotures[-1], cfg["historique"]["delai_publication_mois"], aujourd_hui())
        if attendue > clotures[-1]:
            res["badges"].append("données en retard")
            badge = (f"exercice non indexé sur filings.xbrl.org (attendu : clôture {attendue}) : "
                     "repli yfinance")
            complement = ingest_fallback.fondamentaux_yfinance(ticker, badge)
            ajoutes = set()
            for p, serie in complement.items():
                for d, v in serie.items():
                    if clotures[-1] < d <= attendue:
                        series.setdefault(p, {})[d] = v
                        ajoutes.add(d)
            res["_complement"] = complement
            res["retard"] = {"cloture_attendue": attendue.isoformat(),
                             "derniere_esef": clotures[-1].isoformat(),
                             "exercices_ajoutes_yfinance": sorted(d.isoformat() for d in ajoutes)}
            JOURNAL.avertissement(res["cle"], f"données en retard : dernier ESEF {clotures[-1]}, attendu {attendue}"
                                  + (f" ; complété par yfinance ({', '.join(sorted(d.isoformat() for d in ajoutes))})"
                                     if ajoutes else " ; yfinance ne fournit pas non plus cet exercice"))

    # ---- marché
    infos = ingest_market.infos_yfinance(ticker)
    res["infos"] = infos
    res["splits_journal"] = normalize.ajuster_splits(series, infos.get("splits", []), infos.get("sharesOutstanding"))
    if res.get("retard"):
        # Comparaison yfinance / ESEF sur le dernier exercice commun (après ajustement des splits) :
        # mesure la compatibilité des définitions avant de mélanger les deux sources.
        commun = dt.date.fromisoformat(res["retard"]["derniere_esef"])
        comparaison = []
        for p in ("chiffre_affaires", "ebit", "resultat_net", "bnpa", "actif_total"):
            a = (series.get(p, {}).get(commun) or {}).get("valeur")
            b = (res["_complement"].get(p, {}).get(commun) or {}).get("valeur")
            comparaison.append({"poste": p, "exercice": commun.isoformat(), "esef": a, "yfinance": b,
                                "ecart": None if not a or b is None else (b - a) / abs(a)})
        res["retard"]["comparaison_exercice_commun"] = comparaison
    res["controles_identite"] = normalize.controler_identites(series, cfg, res["cle"])
    res["corrections_manuelles"] = manual.appliquer_corrections(isin, series)
    res["series"] = series
    cours = ingest_market.cours_yfinance(ticker)
    res["cours"] = cours
    res["cours_seance"] = cours.attrs.get("seance") if cours is not None else \
        {"complete": None, "as_of": None, "raison": "cours indisponibles"}
    return res


# --------------------------------------------------------------------------- calculs
def calculer(res: dict, indice, cfg: dict) -> None:
    series, cours, infos = res["series"], res["cours"], res["infos"]
    clotures = normalize.dates_clotures(series)
    res["exercices"] = [d.isoformat() for d in clotures]
    res["nb_exercices"] = len(clotures)
    devises = Counter(v.get("devise") for s in series.values() for v in s.values() if v.get("devise"))
    res["devise_comptes"] = devises.most_common(1)[0][0] if devises else infos.get("financialCurrency")
    res["devise_cotation"] = infos.get("currency")
    if len(devises) > 1:
        res["badges"].append("devises multiples dans les comptes : " + ", ".join(devises))

    # ---- données manquantes (postes attendus sur la fenêtre)
    fen = clotures[-(cfg["historique"]["fenetre_exercices"] + 1):]
    # Postes auxiliaires (servant seulement aux calculs de secours) : non listés s'ils manquent.
    auxiliaires = {"resultat_avant_impot", "charges_financieres", "produits_financiers",
                   "actif_non_courant", "passif_non_courant", "nombre_actions_moyen_pondere",
                   "dette_location_ifrs16", "cout_des_ventes"}
    res["donnees_manquantes"] = {p: [d.isoformat() for d in fen if (series.get(p, {}).get(d) or {}).get("valeur") is None]
                                 for p in mapping()["postes"] if p not in auxiliaires
                                 and any((series.get(p, {}).get(d) or {}).get("valeur") is None for d in fen)}

    ca = normalize.en_liste(series.get("chiffre_affaires", {}))
    bnpa = normalize.en_liste(series.get("bnpa", {}))
    pts_ca = [(d.year, v) for d, v in ca]
    pts_bnpa = [(d.year, v) for d, v in bnpa]
    crit = {}
    crit["P1"] = P.p1_croissance_ca(pts_ca, cfg)
    crit["P3"] = P.p3_croissance_bnpa(pts_bnpa, cfg)
    alt = cfg["historique"]["min_exercices_alternatif"]
    res["alternatif_5_exercices"] = {"P1": P.p1_croissance_ca(pts_ca, cfg, alt),
                                     "P3": P.p3_croissance_bnpa(pts_bnpa, cfg, alt)}

    if len(clotures) >= 2:
        n, n1 = valeurs_annee(series, clotures[-1]), valeurs_annee(series, clotures[-2])
        at_n2 = valeurs_annee(series, clotures[-3]).get("actif_total") if len(clotures) >= 3 else None
        f = P.fscore_convention(n, n1, at_n2)
        f["exercices"] = [clotures[-2].isoformat(), clotures[-1].isoformat()]
        p4_avec = P.p4_fscore(f, cfg)
        # ---- fiabilité (règle ajoutée, même principe que P2) : dernier exercice potentiellement
        # yfinance (retard de publication ESEF) → recalcule P4 sur les seules années ESEF
        # (N−1 vs N−2) et compare ; conclusion différente seulement → statut non fiable.
        if res.get("retard") and len(clotures) >= 3:
            n_f, n1_f = n1, valeurs_annee(series, clotures[-3])
            at_n2_f = valeurs_annee(series, clotures[-4]).get("actif_total") if len(clotures) >= 4 else None
            f_fiable = P.fscore_convention(n_f, n1_f, at_n2_f)
            f_fiable["exercices"] = [clotures[-3].isoformat(), clotures[-2].isoformat()]
            p4_fiable = P.p4_fscore(f_fiable, cfg)
            p4 = P.p4_fiabilite(p4_avec, p4_fiable)
            p4["detail_avec_yfinance"] = p4_avec
            p4["detail_fiable"] = p4_fiable
        else:
            p4 = p4_avec
        crit["P4"] = p4
    else:
        n = valeurs_annee(series, clotures[-1]) if clotures else {}
        crit["P4"] = {"statut": P.NE, "raison": "moins de 2 exercices", "score": None}
    z = P.zscore(n.get("actif_courant"), n.get("dettes_courantes"), n.get("reserves"), n.get("ebit"),
                 n.get("actif_total"), n.get("capitaux_propres"), n.get("dettes_totales"),
                 cfg["porte"]["p5_zscore"]["coefficients"])
    crit["P5"] = P.p5_zscore(z, cfg)
    if clotures:
        crit["P5"]["exercice"] = clotures[-1].isoformat()
    vol = ingest_market.volume_moyen_eur(cours, res["devise_cotation"] or "EUR",
                                         cfg["porte"]["p6_liquidite"]["fenetre_seances"])
    crit["P6"] = P.p6_liquidite(vol, cfg)
    res["criteres"] = crit
    res["n"] = n

    # ---- marges pour P2 (calculé après, car le mode relatif dépend du panel)
    res["_ca"] = par_annee(series.get("chiffre_affaires", {}))
    res["_ebit"] = par_annee(series.get("ebit", {}))
    res["_rn"] = par_annee(series.get("resultat_net", {}))

    # ---- valorisation (même devise pour cours et BNPA)
    val = {}
    dc, dq = res["devise_comptes"], res["devise_cotation"]
    if cours is not None and not cours.empty and clotures:
        prix, date_prix = float(cours["Close"].iloc[-1]), cours["Date"].iloc[-1].date()
        val["cours"], val["date_cours"] = prix, date_prix.isoformat()
        eps_n = n.get("bnpa")
        if eps_n is not None:
            eps_q, note = ingest_market.convertir(eps_n, dc, dq, date_prix)
            val["bnpa_dernier_exercice"] = eps_n
            val["bnpa_conversion"] = note
            val["per_actuel"] = prix / eps_q if eps_q else None
            val["per_actuel_libelle"] = f"PER sur dernier exercice publié (FY{clotures[-1].year})"
        pers = []
        for d in clotures[-cfg["historique"]["fenetre_exercices"]:]:
            e = (series.get("bnpa", {}).get(d) or {}).get("valeur")
            c, dc_date = cours_a_date(cours, d)
            if e is None or c is None:
                pers.append({"exercice": d.isoformat(), "per": None, "raison": "BNPA ou cours indisponible"})
                continue
            e_q, note = ingest_market.convertir(e, dc, dq, dc_date)
            per = c / e_q if e_q else None
            pers.append({"exercice": d.isoformat(), "cours_cloture": c, "date_cours": dc_date.isoformat(),
                         "bnpa": e, "per": per, "conversion": note,
                         "exclu": per is None or per <= 0})
        positifs = [p["per"] for p in pers if p.get("per") and p["per"] > 0]
        val["per_historiques"] = pers
        val["per_mediane_5ans"] = statistics.median(positifs) if positifs else None
        val["bnpa_12m_yfinance_indicatif"] = infos.get("trailingEps")
        actions = n.get("nombre_actions")
        v_act = series.get("nombre_actions", {}).get(clotures[-1]) or {}
        source_actions = f"{v_act.get('source')} ({v_act.get('concept')}, clôture {clotures[-1]})"
        if actions is None and infos.get("sharesOutstanding"):
            actions, source_actions = infos["sharesOutstanding"], "yfinance sharesOutstanding (badge)"
        if actions:
            capi_q = prix * actions
            capi, note = ingest_market.convertir(capi_q, dq, dc, date_prix)
            val.update({"capitalisation": capi, "capitalisation_devise": dc, "capitalisation_note": note,
                        "actions_utilisees": actions, "source_actions": source_actions})
            capi_eur, _ = ingest_market.convertir(capi_q, dq, "EUR", date_prix)
            val["capitalisation_eur"] = capi_eur
    res["valorisation"] = val

    # ---- métriques QVM
    marges = [res["_ebit"][a] / res["_ca"][a] for a in sorted(res["_ca"]) if a in res["_ebit"] and res["_ca"][a]]
    d = {**n, "marges_ebit_5ans": marges[-5:], "capitalisation": val.get("capitalisation"),
         "per_actuel": val.get("per_actuel"), "per_mediane_5ans": val.get("per_mediane_5ans")}
    m = {**Q.metriques_fondamentales(d), **Q.metriques_valeur(d)}
    closes = [] if cours is None else cours["Close"].dropna().tolist()
    idx = [] if indice is None else indice["Close"].dropna().tolist()
    eps_n1 = (valeurs_annee(series, clotures[-2]).get("bnpa") if len(clotures) >= 2 else None)
    m.update(Q.metriques_momentum(closes, idx, n.get("bnpa"), eps_n1, cfg["momentum"]))
    res["metriques"] = m

    # ---- timing
    res["timing"] = T.signal(closes, cfg["timing"])


def main() -> None:
    cfg = config()
    panel = charger_yaml(RACINE / "pipeline" / "test_isins.yaml")["societes"]
    indice = ingest_market.cours_yfinance(cfg["momentum"]["indice_reference"])
    resultats = []
    for soc in panel:
        try:
            res = collecter(soc, cfg)
            calculer(res, indice, cfg)
            resultats.append(res)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            JOURNAL.erreur(soc["isin"], f"échec du traitement : {e!r}")

    # ---- P2 (mode relatif : 3e quartile de la marge EBIT dans le secteur, sinon l'univers)
    q = cfg["porte"]["p2_marges"]["quantile_relatif"]
    min_sect = cfg["qvm"]["min_societes_secteur"]
    derniere_marge = {}
    for r in resultats:
        if r["_ca"] and r["_ebit"]:
            a = max(set(r["_ca"]) & set(r["_ebit"]), default=None)
            if a and r["_ca"][a]:
                derniere_marge[r["cle"]] = (r["infos"].get("sector"), r["_ebit"][a] / r["_ca"][a])
    for r in resultats:
        secteur = r["infos"].get("sector")
        meme = [mg for s, mg in derniere_marge.values() if s == secteur]
        groupe = meme if len(meme) >= min_sect else [mg for _, mg in derniere_marge.values()]
        seuil = float(np.quantile(groupe, q)) if groupe else None
        base_relatif = f"secteur {secteur}" if len(meme) >= min_sect else \
            f"univers du panel ({len(groupe)} sociétés, secteur < {min_sect})"
        p2 = P.p2_marges_fiabilite(r["_ca"], r["_ebit"], r["_rn"], cfg, seuil,
                                   r["source_fondamentaux"], r.get("retard"))
        p2["base_relatif"] = base_relatif
        r["criteres"]["P2"] = p2
        ordre = ["P1", "P2", "P3", "P4", "P5", "P6"]
        r["criteres"] = {k: r["criteres"][k] for k in ordre}
        r["porte"] = P.statut_global([c["statut"] for c in r["criteres"].values()])
        r["porte_relatif"] = P.statut_global([c.get("statut_relatif", c["statut"]) if k == "P2" else c["statut"]
                                              for k, c in r["criteres"].items()])
        alt = {**r["criteres"], **r["alternatif_5_exercices"]}
        r["porte_5_exercices"] = P.statut_global([c["statut"] for c in alt.values()])

    # ---- QVM (percentiles sur le panel : NON SIGNIFICATIF à l'étape 1)
    univers = [{"id": r["cle"], "secteur": r["infos"].get("sector"),
                "metriques": {k: v.get("valeur") for k, v in r["metriques"].items()}} for r in resultats]
    pct = Q.calculer_percentiles(univers, min_sect)
    taille_univers, seuil_univers = len(resultats), cfg["qvm"]["min_univers_verdict"]
    for r in resultats:
        r["percentiles"] = pct[r["cle"]]
        r["qvm"] = {**Q.scores(pct[r["cle"]], cfg["qvm"]["poids"]),
                    "mention": cfg["qvm"]["mention_panel_test"]}
        r["verdict"] = V.verdict(r["porte"], r["qvm"]["score"], r["timing"]["signal"], cfg["verdict"],
                                 taille_univers, seuil_univers)
        badge = V.badge_donnees_non_recoupees(r["verdict"]["verdict"], r["source_fondamentaux"])
        if badge:
            r["verdict"]["badge"] = badge
        r["justification"] = V.justification(r["criteres"], r["qvm"]["sous_scores"])

    # ---- écriture
    synthese = []
    for r in resultats:
        sortie = {k: v for k, v in r.items() if not k.startswith("_") and k != "cours"}
        sortie["series"] = serialiser_series(r["series"])
        ecrire_json(DOSSIER_SORTIE / f"{r['cle']}.json", sortie)
        synthese.append({"cle": r["cle"], "nom": r["societe"]["nom"], "isin": r["societe"]["isin"],
                         "porte": r["porte"], "score": r["qvm"]["score"], "timing": r["timing"]["signal"],
                         "verdict": r["verdict"]["verdict"]})
    ecrire_json(DOSSIER_SORTIE / "synthese.json", {"date": aujourd_hui().isoformat(), "societes": synthese})
    ecrire_json(DOSSIER_SORTIE / "journal.json", JOURNAL.entrees)
    print("\n" + JOURNAL.resume())


if __name__ == "__main__":
    main()
