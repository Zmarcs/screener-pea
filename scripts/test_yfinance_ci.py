"""Porte A (étape 2) : mesure ce que yfinance permet depuis un runner GitHub Actions.

Teste 12 tickers sur 12 marchés européens différents (suffixes .PA, .AS, .DE, .ST, .MI
demandés, plus .CO/.HE/.OL/.BR/.VI/.MC/.LS pour la diversité). Pour chaque ticker : cours
1 an (clôtures + volumes), splits, secteur, sharesOutstanding. Mesure le taux de succès,
le temps par appel et les messages d'erreur exacts (jamais de contournement en cas de
blocage : ce script se contente de mesurer et de journaliser).

Lancer : .venv/bin/python scripts/test_yfinance_ci.py
Sortie : docs/rapport_test_yfinance_ci.md (résumé) + affichage résumé sur stdout.
Aucun secret requis, aucun commit automatique (le workflow ne fait que publier le
rapport comme artefact téléchargeable).
"""
from __future__ import annotations

import datetime as dt
import json
import platform
import sys
import time
import traceback

import yfinance

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

CHAMPS = ("cours_1an", "volumes", "splits", "secteur", "sharesOutstanding")


def tester_ticker(ticker: str) -> dict:
    resultat = {"ticker": ticker, "champs": {}, "duree_s": None}
    debut = time.monotonic()
    try:
        t = yfinance.Ticker(ticker)

        hist = t.history(period="1y")
        resultat["champs"]["cours_1an"] = {
            "ok": not hist.empty and "Close" in hist.columns and hist["Close"].notna().any(),
            "n_lignes": len(hist), "erreur": None,
        }
        resultat["champs"]["volumes"] = {
            "ok": not hist.empty and "Volume" in hist.columns and hist["Volume"].notna().any(),
            "erreur": None,
        }

        splits = t.splits
        resultat["champs"]["splits"] = {"ok": splits is not None, "n_splits": len(splits) if splits is not None else 0,
                                        "erreur": None}

        info = t.info
        secteur = info.get("sector") if isinstance(info, dict) else None
        resultat["champs"]["secteur"] = {"ok": bool(secteur), "valeur": secteur, "erreur": None}

        actions = info.get("sharesOutstanding") if isinstance(info, dict) else None
        resultat["champs"]["sharesOutstanding"] = {"ok": bool(actions), "valeur": actions, "erreur": None}

    except Exception as e:  # noqa: BLE001 — on veut capturer et journaliser, jamais planter le run
        for champ in CHAMPS:
            resultat["champs"].setdefault(champ, {"ok": False})
            if resultat["champs"][champ].get("erreur") is None and not resultat["champs"][champ].get("ok"):
                resultat["champs"][champ]["erreur"] = f"{type(e).__name__}: {e}"
        resultat["exception_globale"] = f"{type(e).__name__}: {e}"
        resultat["traceback"] = traceback.format_exc()
    resultat["duree_s"] = round(time.monotonic() - debut, 2)
    return resultat


def main() -> None:
    entete = {
        "date_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python": sys.version,
        "plateforme": platform.platform(),
        "yfinance_version": getattr(yfinance, "__version__", "inconnue"),
    }
    print(f"=== Test yfinance depuis GitHub Actions — {entete['date_utc']} ===")
    print(f"Python {entete['python']} ; yfinance {entete['yfinance_version']}")
    print()

    resultats = []
    for ticker in TICKERS:
        print(f"--- {ticker}")
        r = tester_ticker(ticker)
        resultats.append(r)
        for champ, d in r["champs"].items():
            etat = "OK" if d.get("ok") else f"ÉCHEC ({d.get('erreur') or '—'})"
            print(f"  {champ}: {etat}")
        print(f"  durée: {r['duree_s']}s")

    # ---- résumé
    n = len(TICKERS)
    taux = {}
    for champ in CHAMPS:
        ok = sum(1 for r in resultats if r["champs"].get(champ, {}).get("ok"))
        taux[champ] = {"ok": ok, "total": n, "taux": round(100 * ok / n, 1)}
    duree_totale = round(sum(r["duree_s"] for r in resultats), 2)
    echecs = [r for r in resultats if any(not d.get("ok") for d in r["champs"].values())]

    resume = {"entete": entete, "taux_par_champ": taux, "duree_totale_s": duree_totale,
              "tickers_avec_au_moins_un_echec": [r["ticker"] for r in echecs], "detail": resultats}

    print()
    print("=== Résumé ===")
    for champ, t in taux.items():
        print(f"{champ}: {t['ok']}/{t['total']} ({t['taux']}%)")
    print(f"Durée totale: {duree_totale}s")
    print(f"Tickers avec au moins un échec: {resume['tickers_avec_au_moins_un_echec'] or 'aucun'}")

    with open("rapport_test_yfinance_ci.json", "w", encoding="utf-8") as f:
        json.dump(resume, f, ensure_ascii=False, indent=2, default=str)

    lignes = [
        "# Test yfinance depuis GitHub Actions (Porte A, étape 2)", "",
        f"Date : {entete['date_utc']}  ", f"Python : {entete['python'].splitlines()[0]}  ",
        f"Plateforme : {entete['plateforme']}  ", f"yfinance : {entete['yfinance_version']}", "",
        "| Champ | Succès | Total | Taux |", "|---|---|---|---|",
    ]
    for champ, t in taux.items():
        lignes.append(f"| {champ} | {t['ok']} | {t['total']} | {t['taux']}% |")
    lignes += ["", f"Durée totale : {duree_totale}s", "",
              "## Détail par ticker", "",
              "| Ticker | cours_1an | volumes | splits | secteur | sharesOutstanding | Durée | Erreur |",
              "|---|---|---|---|---|---|---|---|"]
    for r in resultats:
        c = r["champs"]
        lignes.append(
            f"| {r['ticker']} | {'✅' if c.get('cours_1an', {}).get('ok') else '❌'} "
            f"| {'✅' if c.get('volumes', {}).get('ok') else '❌'} "
            f"| {'✅' if c.get('splits', {}).get('ok') else '❌'} "
            f"| {'✅' if c.get('secteur', {}).get('ok') else '❌'} "
            f"| {'✅' if c.get('sharesOutstanding', {}).get('ok') else '❌'} "
            f"| {r['duree_s']}s | {r.get('exception_globale') or '—'} |")
    with open("rapport_test_yfinance_ci.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")


if __name__ == "__main__":
    main()
