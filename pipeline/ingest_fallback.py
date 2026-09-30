"""Repli fondamentaux yfinance (sociétés sans ESEF, ou exercice pas encore indexé).

yfinance fournit en général 4 exercices annuels : badge « historique court ».
Les libellés de lignes sont définis dans mapping_ifrs.yaml (section yfinance).
Les définitions de Yahoo peuvent différer des états IFRS publiés (ex. « Operating Income »).
"""
from __future__ import annotations

import datetime as dt
import math

from .common import JOURNAL, aujourd_hui, cache_json, mapping


def _etats(ticker: str) -> dict:
    import yfinance as yf

    def produire():
        tk = yf.Ticker(ticker)
        sortie = {}
        for nom, df in (("compte_resultat", tk.income_stmt), ("bilan", tk.balance_sheet),
                        ("flux", tk.cashflow)):
            if df is None or df.empty:
                sortie[nom] = {}
                continue
            sortie[nom] = {str(col.date()): {str(k): (None if (v is None or (isinstance(v, float) and math.isnan(v)))
                                                      else float(v)) for k, v in df[col].items()}
                           for col in df.columns}
        sortie["devise"] = (tk.info or {}).get("financialCurrency")
        return sortie
    return cache_json("yf_fondamentaux", f"{ticker}_{aujourd_hui().isoformat()}", produire)


def fondamentaux_yfinance(ticker: str, motif_badge: str) -> dict[str, dict[dt.date, dict]]:
    try:
        etats = _etats(ticker)
    except Exception as e:  # noqa: BLE001
        JOURNAL.erreur(ticker, f"fondamentaux yfinance indisponibles : {e}")
        return {}
    libelles = mapping()["yfinance"]
    series: dict[str, dict[dt.date, dict]] = {}
    for poste, lignes in libelles.items():
        serie = {}
        for etat in ("compte_resultat", "bilan", "flux"):
            for date_txt, lignes_col in etats.get(etat, {}).items():
                d = dt.date.fromisoformat(date_txt)
                if d in serie:
                    continue
                for ligne in lignes:
                    v = lignes_col.get(ligne)
                    if v is not None:
                        if poste == "capex":
                            v = abs(v)
                        serie[d] = {"valeur": v, "source": "yfinance", "concept": f"yfinance:{ligne}",
                                    "devise": None if poste in ("nombre_actions",) else etats.get("devise"),
                                    "rapport": None, "lien": f"https://finance.yahoo.com/quote/{ticker}/financials",
                                    "date_rapport": aujourd_hui().isoformat(),
                                    "qualite": None, "badges": [motif_badge]}
                        break
        series[poste] = serie
    return series
