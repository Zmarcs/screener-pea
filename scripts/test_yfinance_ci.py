"""Porte A (étape 2) : mesure ce que yfinance permet depuis un runner GitHub Actions.

Teste 12 tickers sur 12 marchés européens différents (suffixes .PA, .AS, .DE, .ST, .MI
demandés, plus .CO/.HE/.OL/.BR/.VI/.MC/.LS pour la diversité) sur EXACTEMENT ce que le
pipeline utilise en repli (`pipeline/ingest_fallback.py`, `pipeline/ingest_market.py`) :
- cours (t.history, période 8y — même profondeur que `pipeline/ingest_market.py::HISTORIQUE`,
  qui couvre la médiane des PER sur 5 exercices + MM200) : clôtures, volumes, nombre de
  séances, 3 dernières clôtures avec leur date, et si la DERNIÈRE séance renvoyée est déjà
  terminée (`pipeline/calendrier_marche.py` — même logique que le pipeline : ne jamais
  traiter un cours intrajournalier comme une clôture) ;
- splits (t.splits) ;
- secteur, sharesOutstanding (t.info, avec reprises : 3 essais, pause croissante 2s/4s) ;
- états financiers annuels utilisés en repli fondamentaux : compte de résultat
  (t.income_stmt), bilan (t.balance_sheet), flux de trésorerie (t.cashflow) — succès, nombre
  d'exercices (colonnes) et de lignes renvoyées.

Détecte et compte explicitement les 429/blocages/résultats vides (voir classer_erreur() et
resultat["vide"]). Jamais de contournement en cas de blocage : ce script mesure et journalise.

Lancer : .venv/bin/python scripts/test_yfinance_ci.py
Sortie : rapport_test_yfinance_ci.md / .json + affichage résumé sur stdout.
Aucun secret requis, aucun commit automatique (le workflow publie le rapport en artefact).

Commande locale pour comparer les cours sur ta machine (même tickers, même méthode) :
    .venv/bin/python -c "
    import yfinance
    for t in ['RMS.PA','ASML.AS','SAP.DE','ATCO-A.ST','BC.MI','NOVO-B.CO','NOKIA.HE',
              'EQNR.OL','UCB.BR','VIG.VI','ITX.MC','EDP.LS']:
        h = yfinance.Ticker(t).history(period='8y')
        if h.empty:
            print(t, 'VIDE'); continue
        print(t, h.index[-1].date(), round(float(h['Close'].iloc[-1]), 4), 'n_lignes=', len(h))
    "
"""
from __future__ import annotations

import datetime as dt
import json
import platform
import sys
import time
import traceback
from pathlib import Path

import pandas as pd
import yfinance

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.calendrier_marche import seance_complete  # noqa: E402  (même logique que le pipeline)

TICKERS = [
    "RMS.PA",     # Paris — Hermès
    "ASML.AS",    # Amsterdam — ASML
    "SAP.DE",     # Xetra — SAP
    "ATCO-A.ST",  # Stockholm — Atlas Copco
    "BC.MI",      # Milan — Brunello Cucinelli
    "NOVO-B.CO",  # Copenhague — Novo Nordisk
    "NOKIA.HE",   # Helsinki — Nokia
    "EQNR.OL",    # Oslo — Equinor
    "UCB.BR",     # Bruxelles — UCB
    "VIG.VI",     # Vienne — Vienna Insurance Group
    "ITX.MC",     # Madrid — Inditex
    "EDP.LS",     # Lisbonne — EDP
]

CHAMPS = ("cours_8ans", "volumes", "splits", "secteur", "sharesOutstanding",
         "compte_resultat", "bilan", "flux")

PERIODE_COURS = "8y"        # même valeur que pipeline/ingest_market.py::HISTORIQUE
INFO_ESSAIS = 3
INFO_PAUSE_INITIALE = 2.0   # secondes ; pause croissante 2s, 4s entre essais


def classer_erreur(exc: Exception) -> str:
    """Classe une exception en catégories utiles pour compter les blocages, sans jamais
    les contourner — juste les nommer précisément."""
    msg = str(exc)
    code = getattr(getattr(exc, "response", None), "status_code", None)
    if code == 429 or "429" in msg or "Too Many Requests" in msg:
        return "429 (limite de débit)"
    if code in (401, 403) or "403" in msg or "401" in msg or "Unauthorized" in msg or "Forbidden" in msg:
        return f"blocage HTTP {code or '401/403'}"
    if "JSONDecodeError" in type(exc).__name__ or "Expecting value" in msg:
        return "réponse vide/non-JSON (possible blocage silencieux)"
    if isinstance(exc, (ConnectionError, TimeoutError)) or "Connection" in type(exc).__name__:
        return "connexion (timeout/refus)"
    return f"autre : {type(exc).__name__}: {msg}"


def _etat_financier(df) -> dict:
    if df is None:
        return {"ok": False, "n_exercices": 0, "n_lignes": 0, "vide": True}
    vide = df.empty
    return {"ok": not vide, "n_exercices": 0 if vide else df.shape[1],
           "n_lignes": 0 if vide else df.shape[0], "vide": vide}


def _info_avec_reprises(t, essais: int = INFO_ESSAIS, pause_initiale: float = INFO_PAUSE_INITIALE) -> dict:
    """t.info avec reprises (pause croissante). Distingue « absent après reprises » (jamais
    réussi) d'un « échec transitoire » (réussi après au moins un échec) : c'est ce distinguo
    qui manquait quand VIG.VI a échoué au run #3 après avoir réussi au run #2."""
    derniere_exc = None
    for tentative in range(1, essais + 1):
        try:
            info = t.info or {}
            return {"info": info, "tentatives": tentative,
                    "echec_transitoire_recupere": tentative > 1, "absent_apres_reprises": False,
                    "erreur_finale": None}
        except Exception as e:  # noqa: BLE001
            derniere_exc = e
            if tentative < essais:
                time.sleep(pause_initiale * tentative)
    return {"info": {}, "tentatives": essais, "echec_transitoire_recupere": False,
           "absent_apres_reprises": True,
           "erreur_finale": f"{type(derniere_exc).__name__}: {derniere_exc}"}


def tester_ticker(ticker: str) -> dict:
    resultat = {"ticker": ticker, "champs": {}, "duree_s": None, "erreurs_classees": []}
    debut = time.monotonic()
    try:
        t = yfinance.Ticker(ticker)

        hist = t.history(period=PERIODE_COURS)
        vide_hist = hist.empty
        dernieres_3 = [] if vide_hist else [
            {"date": str(idx.date()), "close": None if pd.isna(c) else round(float(c), 4)}
            for idx, c in hist["Close"].tail(3).items()
        ]
        dernier_date_obj = None if vide_hist else hist.index[-1].date()
        diag_seance = ({"complete": None, "as_of": None, "raison": "cours vides"} if vide_hist
                       else seance_complete(ticker, dernier_date_obj))
        resultat["champs"]["cours_8ans"] = {
            "ok": not vide_hist and "Close" in hist.columns and hist["Close"].notna().any(),
            "n_jours": 0 if vide_hist else len(hist), "vide": vide_hist,
            "dernier_date": None if vide_hist else str(dernier_date_obj),
            "dernier_close": None if vide_hist else dernieres_3[-1]["close"] if dernieres_3 else None,
            "dernieres_3_clotures": dernieres_3,
            "derniere_seance_complete": diag_seance["complete"],
            "derniere_seance_as_of": diag_seance["as_of"],
            "derniere_seance_raison": diag_seance["raison"],
            "erreur": None,
        }
        resultat["champs"]["volumes"] = {
            "ok": not vide_hist and "Volume" in hist.columns and hist["Volume"].notna().any(),
            "vide": vide_hist, "erreur": None,
        }

        splits = t.splits
        resultat["champs"]["splits"] = {"ok": splits is not None,
                                        "n_splits": len(splits) if splits is not None else 0,
                                        "vide": splits is None or splits.empty, "erreur": None}

        info_diag = _info_avec_reprises(t)
        resultat["info_diag"] = {k: v for k, v in info_diag.items() if k != "info"}
        info = info_diag["info"]
        info_vide = not info
        secteur = info.get("sector") if isinstance(info, dict) else None
        resultat["champs"]["secteur"] = {"ok": bool(secteur), "valeur": secteur, "vide": info_vide,
                                         "erreur": info_diag["erreur_finale"] if info_vide else None}

        actions = info.get("sharesOutstanding") if isinstance(info, dict) else None
        resultat["champs"]["sharesOutstanding"] = {"ok": bool(actions), "valeur": actions,
                                                    "vide": info_vide,
                                                    "erreur": info_diag["erreur_finale"] if info_vide else None}

        # ---- etats financiers annuels utilises en repli (memes appels que ingest_fallback.py)
        resultat["champs"]["compte_resultat"] = _etat_financier(t.income_stmt)
        resultat["champs"]["bilan"] = _etat_financier(t.balance_sheet)
        resultat["champs"]["flux"] = _etat_financier(t.cashflow)

    except Exception as e:  # noqa: BLE001 — on veut capturer et journaliser, jamais planter le run
        categorie = classer_erreur(e)
        resultat["erreurs_classees"].append(categorie)
        for champ in CHAMPS:
            resultat["champs"].setdefault(champ, {"ok": False})
            if resultat["champs"][champ].get("erreur") is None and not resultat["champs"][champ].get("ok"):
                resultat["champs"][champ]["erreur"] = f"{type(e).__name__}: {e}"
        resultat["exception_globale"] = f"{type(e).__name__}: {e}"
        resultat["exception_categorie"] = categorie
        resultat["traceback"] = traceback.format_exc()
    # ---- resultats vides sans exception (comptes separement des exceptions).
    # "splits" vide est un fait metier normal (societe qui n'a jamais split), pas un signal
    # de blocage : exclu de cette detection.
    for champ, d in resultat["champs"].items():
        if champ != "splits" and d.get("vide") and not d.get("erreur"):
            resultat["erreurs_classees"].append(f"{champ} : vide sans exception")
    resultat["duree_s"] = round(time.monotonic() - debut, 2)
    return resultat


def main() -> None:
    entete = {
        "date_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python": sys.version,
        "plateforme": platform.platform(),
        "yfinance_version": getattr(yfinance, "__version__", "inconnue"),
        "periode_cours": PERIODE_COURS,
    }
    print(f"=== Test yfinance depuis GitHub Actions — {entete['date_utc']} ===")
    print(f"Python {entete['python']} ; yfinance {entete['yfinance_version']} ; période cours {PERIODE_COURS}")
    print()

    resultats = []
    for ticker in TICKERS:
        print(f"--- {ticker}")
        r = tester_ticker(ticker)
        resultats.append(r)
        for champ, d in r["champs"].items():
            if champ in ("compte_resultat", "bilan", "flux"):
                etat = f"OK ({d.get('n_exercices')} exercices, {d.get('n_lignes')} lignes)" if d.get("ok") \
                    else f"ÉCHEC (vide={d.get('vide')}, {d.get('erreur') or '—'})"
            elif champ == "cours_8ans":
                if d.get("ok"):
                    etat = (f"OK ({d.get('n_jours')} jours, dernier {d.get('dernier_date')}="
                           f"{d.get('dernier_close')}, séance complète={d.get('derniere_seance_complete')})")
                else:
                    etat = f"ÉCHEC ({d.get('erreur') or '—'})"
            else:
                etat = "OK" if d.get("ok") else f"ÉCHEC ({d.get('erreur') or '—'})"
            print(f"  {champ}: {etat}")
        if r.get("info_diag", {}).get("echec_transitoire_recupere"):
            print(f"  info : échec transitoire récupéré après {r['info_diag']['tentatives']} tentative(s)")
        if r.get("info_diag", {}).get("absent_apres_reprises"):
            print(f"  info : absent après {r['info_diag']['tentatives']} reprises ({r['info_diag']['erreur_finale']})")
        if r["erreurs_classees"]:
            print(f"  erreurs classées: {r['erreurs_classees']}")
        print(f"  durée: {r['duree_s']}s")

    # ---- résumé
    n = len(TICKERS)
    taux = {}
    for champ in CHAMPS:
        ok = sum(1 for r in resultats if r["champs"].get(champ, {}).get("ok"))
        taux[champ] = {"ok": ok, "total": n, "taux": round(100 * ok / n, 1)}
    duree_totale = round(sum(r["duree_s"] for r in resultats), 2)
    echecs = [r for r in resultats if any(not d.get("ok") for d in r["champs"].values())]

    toutes_erreurs = [c for r in resultats for c in r["erreurs_classees"]]
    compte_429 = sum(1 for c in toutes_erreurs if c.startswith("429"))
    compte_blocage = sum(1 for c in toutes_erreurs if "blocage" in c or "connexion" in c)
    compte_vide = sum(1 for c in toutes_erreurs if "vide" in c)
    n_info_transitoire = sum(1 for r in resultats if r.get("info_diag", {}).get("echec_transitoire_recupere"))
    n_info_absent = sum(1 for r in resultats if r.get("info_diag", {}).get("absent_apres_reprises"))
    n_seance_incomplete = sum(1 for r in resultats if r["champs"].get("cours_8ans", {}).get("derniere_seance_complete") is False)
    n_seance_non_verifiable = sum(1 for r in resultats if r["champs"].get("cours_8ans", {}).get("derniere_seance_complete") is None)

    resume = {"entete": entete, "taux_par_champ": taux, "duree_totale_s": duree_totale,
              "tickers_avec_au_moins_un_echec": [r["ticker"] for r in echecs],
              "compte_429": compte_429, "compte_blocage": compte_blocage, "compte_vide": compte_vide,
              "info_echec_transitoire_recupere": n_info_transitoire, "info_absent_apres_reprises": n_info_absent,
              "derniere_seance_incomplete": n_seance_incomplete,
              "derniere_seance_non_verifiable": n_seance_non_verifiable,
              "toutes_erreurs_classees": toutes_erreurs, "detail": resultats}

    print()
    print("=== Résumé ===")
    for champ, t in taux.items():
        print(f"{champ}: {t['ok']}/{t['total']} ({t['taux']}%)")
    print(f"Durée totale: {duree_totale}s")
    print(f"429 détectés: {compte_429}  Blocages/connexion: {compte_blocage}  Résultats vides: {compte_vide}")
    print(f"info — échecs transitoires récupérés: {n_info_transitoire}  absents après reprises: {n_info_absent}")
    print(f"Dernière séance : incomplète (retirée): {n_seance_incomplete}  non vérifiable (place inconnue): "
         f"{n_seance_non_verifiable}")
    print(f"Tickers avec au moins un échec: {resume['tickers_avec_au_moins_un_echec'] or 'aucun'}")

    with open("rapport_test_yfinance_ci.json", "w", encoding="utf-8") as f:
        json.dump(resume, f, ensure_ascii=False, indent=2, default=str)

    lignes = [
        "# Test yfinance depuis GitHub Actions (Porte A, étape 2)", "",
        f"Date : {entete['date_utc']}  ", f"Python : {entete['python'].splitlines()[0]}  ",
        f"Plateforme : {entete['plateforme']}  ", f"yfinance : {entete['yfinance_version']}  ",
        f"Période de cours demandée : {PERIODE_COURS} (même profondeur que le pipeline, "
        "cf. pipeline/ingest_market.py::HISTORIQUE)", "",
        "| Champ | Succès | Total | Taux |", "|---|---|---|---|",
    ]
    for champ, t in taux.items():
        lignes.append(f"| {champ} | {t['ok']} | {t['total']} | {t['taux']}% |")
    lignes += ["", f"Durée totale : {duree_totale}s", "",
              f"429 détectés : {compte_429} · Blocages/connexion : {compte_blocage} · Résultats vides : {compte_vide}",
              "",
              f"info (secteur/actions) — échecs transitoires récupérés (reprise réussie après ≥1 échec) : "
              f"{n_info_transitoire} · absents après {INFO_ESSAIS} reprises : {n_info_absent}",
              "",
              f"Dernière séance de cours — incomplète et retirée (séance en cours au moment du test) : "
              f"{n_seance_incomplete} · non vérifiable (place hors calendrier connu) : {n_seance_non_verifiable}",
              "", "## Détail par ticker", "",
              "| Ticker | Cours (jours, dernière clôture COMPLÈTE) | 3 dernières clôtures | Volumes | Splits | "
              "Secteur | Actions | info (tentatives) | Compte résultat | Bilan | Flux | Durée | Erreur |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in resultats:
        c = r["champs"]
        cours = c.get("cours_8ans", {})
        if cours.get("ok"):
            complet = cours.get("derniere_seance_complete")
            marque = {"True": "", True: "", "False": " ⚠️ séance en cours retirée",
                     False: " ⚠️ séance en cours retirée", None: " ❓ non vérifiable"}[complet]
            cours_txt = f"{cours.get('n_jours', 0)}j, {cours.get('dernier_date')}={cours.get('dernier_close')}{marque}"
            trois = "; ".join(f"{d['date']}={d['close']}" for d in cours.get("dernieres_3_clotures", []))
        else:
            cours_txt, trois = "❌", "—"

        def etat_fin(champ):
            d = c.get(champ, {})
            return f"{d.get('n_exercices')}ex/{d.get('n_lignes')}l" if d.get("ok") else "❌"

        info_diag = r.get("info_diag", {})
        info_txt = f"{info_diag.get('tentatives', '—')}"
        if info_diag.get("echec_transitoire_recupere"):
            info_txt += " (récupéré)"
        if info_diag.get("absent_apres_reprises"):
            info_txt += " (absent)"

        lignes.append(
            f"| {r['ticker']} | {cours_txt} | {trois} "
            f"| {'✅' if c.get('volumes', {}).get('ok') else '❌'} "
            f"| {'✅' if c.get('splits', {}).get('ok') else '❌'} "
            f"| {'✅' if c.get('secteur', {}).get('ok') else '❌'} "
            f"| {'✅' if c.get('sharesOutstanding', {}).get('ok') else '❌'} "
            f"| {info_txt} "
            f"| {etat_fin('compte_resultat')} | {etat_fin('bilan')} | {etat_fin('flux')} "
            f"| {r['duree_s']}s | {r.get('exception_categorie') or '—'} |")
    with open("rapport_test_yfinance_ci.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")


if __name__ == "__main__":
    main()
