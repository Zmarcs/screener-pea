"""Porte A (étape 2), mode « échelle » : même test que test_yfinance_ci.py (mêmes champs,
même classification d'erreurs — réutilisés directement, pas dupliqués), mais paramétré par un
fichier JSON de tickers et avec une pause configurable entre requêtes, pour un usage à grande
échelle (liste du pilote FIRDS, docs/univers.md) sans marteler Yahoo.

NE PAS LANCER À GRANDE ÉCHELLE SANS VALIDATION — ce script est préparé, pas exécuté sur la
liste du pilote. Il peut être lancé sans risque sur le petit fichier d'exemple
(data/manual/tickers_test.json, 12 tickers) pour vérifier qu'il fonctionne.

Usage :
    .venv/bin/python scripts/test_yfinance_echelle.py \\
        --tickers-file data/manual/tickers_test.json \\
        --pause 1.0 \\
        --sortie rapport_test_yfinance_echelle

Sortie : <sortie>.json (détail complet) + <sortie>.md (résumé + tableau par tranche de 50) +
affichage du taux de succès et de 429 par tranche de 50 au fur et à mesure (journal, pas de
détail brut par ticker — conforme à la règle « jobs longs en arrière-plan avec un journal »).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import sys
import time

import yfinance

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from test_yfinance_ci import CHAMPS, tester_ticker  # noqa: E402  (reutilise la meme logique testee)

TAILLE_TRANCHE = 50


def charger_tickers(chemin: str) -> list[str]:
    with open(chemin, encoding="utf-8") as f:
        d = json.load(f)
    return d["tickers"] if isinstance(d, dict) else d


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tickers-file", default="data/manual/tickers_test.json",
                    help="Fichier JSON {\"tickers\": [...]} (défaut : le fichier d'exemple 12 tickers)")
    ap.add_argument("--pause", type=float, default=1.0, help="Pause en secondes entre chaque ticker (défaut 1.0)")
    ap.add_argument("--sortie", default="rapport_test_yfinance_echelle",
                    help="Préfixe des fichiers de sortie (.json/.md), sans extension")
    ap.add_argument("--limite", type=int, default=None,
                    help="Ne traiter que les N premiers tickers (pour un essai rapide)")
    args = ap.parse_args()

    tickers = charger_tickers(args.tickers_file)
    if args.limite:
        tickers = tickers[: args.limite]

    entete = {
        "date_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python": sys.version, "plateforme": platform.platform(),
        "yfinance_version": getattr(yfinance, "__version__", "inconnue"),
        "tickers_file": args.tickers_file, "n_tickers": len(tickers), "pause_s": args.pause,
    }
    print(f"=== Test yfinance à l'échelle — {len(tickers)} tickers, pause {args.pause}s, "
         f"fichier {args.tickers_file} ===")

    resultats: list[dict] = []
    tranches: list[dict] = []
    debut_run = time.monotonic()

    for i, ticker in enumerate(tickers):
        resultats.append(tester_ticker(ticker))
        if args.pause and i < len(tickers) - 1:
            time.sleep(args.pause)

        fin_tranche = (i + 1) % TAILLE_TRANCHE == 0 or i == len(tickers) - 1
        if fin_tranche:
            debut_idx = (len(tranches)) * TAILLE_TRANCHE
            lot = resultats[debut_idx:]
            n = len(lot)
            succes_total = sum(1 for r in lot if all(d.get("ok") for d in r["champs"].values()))
            succes_partiel = sum(1 for r in lot if any(d.get("ok") for d in r["champs"].values()))
            n_429 = sum(1 for r in lot if any(c.startswith("429") for c in r["erreurs_classees"]))
            n_blocage = sum(1 for r in lot if any("blocage" in c or "connexion" in c for c in r["erreurs_classees"]))
            tranche_resume = {
                "tranche": len(tranches) + 1, "de": debut_idx + 1, "a": debut_idx + n,
                "succes_total_pct": round(100 * succes_total / n, 1),
                "succes_partiel_pct": round(100 * succes_partiel / n, 1),
                "n_429": n_429, "n_blocage": n_blocage,
            }
            tranches.append(tranche_resume)
            print(f"[tranche {tranche_resume['tranche']}] tickers {tranche_resume['de']}-{tranche_resume['a']} : "
                 f"succès total {tranche_resume['succes_total_pct']}% · succès partiel "
                 f"{tranche_resume['succes_partiel_pct']}% · 429={n_429} · blocages={n_blocage} · "
                 f"écoulé={round(time.monotonic() - debut_run)}s")

    duree_totale = round(time.monotonic() - debut_run, 1)
    taux = {}
    for champ in CHAMPS:
        ok = sum(1 for r in resultats if r["champs"].get(champ, {}).get("ok"))
        taux[champ] = {"ok": ok, "total": len(resultats), "taux": round(100 * ok / len(resultats), 1)}
    toutes_erreurs = [c for r in resultats for c in r["erreurs_classees"]]
    compte_429 = sum(1 for c in toutes_erreurs if c.startswith("429"))
    compte_blocage = sum(1 for c in toutes_erreurs if "blocage" in c or "connexion" in c)
    compte_vide = sum(1 for c in toutes_erreurs if "vide" in c)

    resume = {"entete": entete, "duree_totale_s": duree_totale, "taux_par_champ": taux,
             "compte_429": compte_429, "compte_blocage": compte_blocage, "compte_vide": compte_vide,
             "tranches": tranches, "detail": resultats}

    print(f"\n=== Résumé final ({len(tickers)} tickers, {duree_totale}s) ===")
    for champ, t in taux.items():
        print(f"{champ}: {t['ok']}/{t['total']} ({t['taux']}%)")
    print(f"429 total: {compte_429}  Blocages: {compte_blocage}  Vides: {compte_vide}")

    with open(f"{args.sortie}.json", "w", encoding="utf-8") as f:
        json.dump(resume, f, ensure_ascii=False, indent=2, default=str)

    lignes = ["# Test yfinance à l'échelle (Porte A, mode échelle)", "",
             f"Fichier tickers : `{args.tickers_file}` ({len(tickers)} tickers) · Pause : {args.pause}s · "
             f"Durée totale : {duree_totale}s", "",
             "## Taux global par champ", "", "| Champ | Succès | Total | Taux |", "|---|---|---|---|"]
    for champ, t in taux.items():
        lignes.append(f"| {champ} | {t['ok']} | {t['total']} | {t['taux']}% |")
    lignes += ["", f"429 total : {compte_429} · Blocages/connexion : {compte_blocage} · Vides : {compte_vide}",
              "", "## Détail par tranche de 50", "",
              "| Tranche | Tickers | Succès total | Succès partiel | 429 | Blocages |",
              "|---|---|---|---|---|---|"]
    for tr in tranches:
        lignes.append(f"| {tr['tranche']} | {tr['de']}-{tr['a']} | {tr['succes_total_pct']}% | "
                      f"{tr['succes_partiel_pct']}% | {tr['n_429']} | {tr['n_blocage']} |")
    with open(f"{args.sortie}.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")


if __name__ == "__main__":
    main()
