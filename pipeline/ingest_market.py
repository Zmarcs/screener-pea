"""Données de marché : cours et volumes journaliers, secteur, splits, indice, taux BCE.

- yfinance (source principale). Les cours « Close » de Yahoo sont ajustés des splits
  (pas des dividendes) : le BNPA doit donc être exprimé sur la même base d'actions.
- Stooq (secours) : depuis 2026, stooq.com exige une vérification JavaScript
  (anti-robot). On la détecte et on la signale ; on ne la contourne pas.
- Taux de change : taux de référence quotidiens de la BCE (data-api.ecb.europa.eu),
  exprimés en unités de devise pour 1 EUR. Conversion au taux de la DATE de chaque cours.
"""
from __future__ import annotations

import datetime as dt
import io

import pandas as pd

from .common import JOURNAL, aujourd_hui, cache_json, chemin_cache, http_get

HISTORIQUE = "8y"   # couvre la médiane des PER sur 5 exercices + MM200


def _cache_csv(categorie: str, cle: str, producteur) -> pd.DataFrame:
    """Cache journalier (clé datée) pour les séries de cours."""
    p = chemin_cache(categorie, f"{cle}_{aujourd_hui().isoformat()}", "csv")
    if p.exists():
        return pd.read_csv(p, parse_dates=["Date"])
    df = producteur()
    if df is not None and len(df):
        df.to_csv(p, index=False)
    return df


def cours_yfinance(ticker: str) -> pd.DataFrame | None:
    import yfinance as yf

    def produire():
        h = yf.Ticker(ticker).history(period=HISTORIQUE, auto_adjust=False, actions=True)
        if h is None or h.empty:
            return None
        h = h.reset_index()
        h["Date"] = pd.to_datetime(h["Date"]).dt.tz_localize(None).dt.normalize()
        return h[["Date", "Open", "High", "Low", "Close", "Volume"]]
    try:
        df = _cache_csv("cours", ticker, produire)
    except Exception as e:  # noqa: BLE001
        JOURNAL.erreur(ticker, f"cours yfinance indisponibles : {e}")
        df = None
    if df is None or df.empty:
        df = cours_stooq(ticker)
    return df


def cours_stooq(ticker: str) -> pd.DataFrame | None:
    symbole = ticker.lower().replace(".pa", ".fr").replace(".as", ".nl").replace(".mi", ".it")
    try:
        r = http_get("https://stooq.com/q/d/l/", params={"s": symbole, "i": "d"}, essais=2)
        if "requires JavaScript" in r.text or not r.text.startswith("Date"):
            JOURNAL.avertissement(ticker, "Stooq (secours) indisponible : vérification JavaScript anti-robot")
            return None
        df = pd.read_csv(io.StringIO(r.text), parse_dates=["Date"])
        df = df.rename(columns={"Zamkniecie": "Close"})
        return df
    except Exception as e:  # noqa: BLE001
        JOURNAL.avertissement(ticker, f"Stooq (secours) inaccessible : {e}")
        return None


def infos_yfinance(ticker: str) -> dict:
    import yfinance as yf

    champs = ["longName", "shortName", "sector", "industry", "currency", "financialCurrency",
              "trailingEps", "sharesOutstanding", "marketCap", "country", "exchange"]

    def produire():
        tk = yf.Ticker(ticker)
        info = tk.info or {}
        sortie = {k: info.get(k) for k in champs}
        sortie["splits"] = [{"date": d.date().isoformat(), "ratio": float(r)}
                            for d, r in tk.splits.items() if r and float(r) != 1.0]
        return sortie
    try:
        return cache_json("infos", f"{ticker}_{aujourd_hui().isoformat()}", produire)
    except Exception as e:  # noqa: BLE001
        JOURNAL.erreur(ticker, f"infos yfinance indisponibles : {e}")
        return {"splits": []}


# --------------------------------------------------------------------------- BCE
def taux_bce(devise: str) -> pd.Series | None:
    """Série date → unités de `devise` pour 1 EUR. EUR → None (pas de conversion)."""
    if devise in (None, "EUR"):
        return None

    def produire():
        r = http_get(f"https://data-api.ecb.europa.eu/service/data/EXR/D.{devise}.EUR.SP00.A",
                     params={"startPeriod": "2018-01-01", "format": "csvdata"})
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text), usecols=["TIME_PERIOD", "OBS_VALUE"])
        return {"dates": df["TIME_PERIOD"].tolist(), "valeurs": df["OBS_VALUE"].tolist()}
    try:
        d = cache_json("bce", f"{devise}_{aujourd_hui().isoformat()}", produire)
    except Exception as e:  # noqa: BLE001
        JOURNAL.erreur(devise, f"taux BCE indisponibles : {e}")
        return None
    return pd.Series(d["valeurs"], index=pd.to_datetime(d["dates"])).sort_index()


def taux_a_la_date(taux: pd.Series, dates: pd.Series) -> tuple[pd.Series, int]:
    """Taux BCE de chaque date de cours. Jour sans fixing BCE (férié TARGET) : dernier
    fixing antérieur. Renvoie (taux, nombre de jours sans fixing du jour)."""
    alignes = taux.reindex(pd.DatetimeIndex(dates), method="ffill")
    exacts = pd.DatetimeIndex(dates).isin(taux.index)
    return pd.Series(alignes.values, index=dates.index), int((~exacts).sum())


def convertir(montant: float, de: str, vers: str, date: dt.date) -> tuple[float | None, str]:
    """Conversion ponctuelle via l'EUR au taux BCE de `date` (ou dernier fixing antérieur)."""
    if de == vers:
        return montant, "même devise"
    t = pd.Timestamp(date)
    en_eur = montant
    note = []
    if de != "EUR":
        s = taux_bce(de)
        if s is None:
            return None, f"taux BCE {de} indisponible"
        r = s[:t]
        if r.empty:
            return None, f"pas de taux BCE {de} avant {date}"
        en_eur = montant / r.iloc[-1]
        note.append(f"{de}/EUR BCE {r.index[-1].date()} = {r.iloc[-1]}")
    if vers != "EUR":
        s = taux_bce(vers)
        if s is None:
            return None, f"taux BCE {vers} indisponible"
        r = s[:t]
        en_eur = en_eur * r.iloc[-1]
        note.append(f"{vers}/EUR BCE {r.index[-1].date()} = {r.iloc[-1]}")
    return en_eur, " ; ".join(note)


def volume_moyen_eur(cours: pd.DataFrame, devise: str, seances: int) -> dict:
    """Moyenne sur `seances` séances de (volume × cours de clôture × taux BCE du jour)."""
    if cours is None or cours.empty:
        return {"valeur": None, "raison": "cours indisponibles"}
    df = cours.dropna(subset=["Close", "Volume"]).tail(seances).copy()
    if len(df) < seances:
        return {"valeur": None, "raison": f"historique insuffisant ({len(df)} séances)"}
    montant = df["Volume"] * df["Close"]
    sans_fixing = 0
    if devise != "EUR":
        taux = taux_bce(devise)
        if taux is None:
            return {"valeur": None, "raison": f"taux BCE {devise} indisponible"}
        t, sans_fixing = taux_a_la_date(taux, df["Date"])
        montant = montant / t
    # Devises cotées en centimes (ex. GBp) : hors univers PEA, non gérées.
    return {"valeur": float(montant.mean()), "seances": seances,
            "du": df["Date"].iloc[0].date().isoformat(), "au": df["Date"].iloc[-1].date().isoformat(),
            "devise_cotation": devise, "jours_sans_fixing_bce": sans_fixing,
            "source": "yfinance (volume × clôture)" + ("" if devise == "EUR" else " × taux BCE du jour")}
