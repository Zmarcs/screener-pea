"""Calendrier de marché : détermine si la dernière séance renvoyée par yfinance pour un
ticker est déjà clôturée, pour ne jamais traiter un cours intrajournalier comme une clôture
(RSI/MM50/MM200 et le cours affiché doivent porter sur des séances terminées).

Fuseau IANA + heure de clôture par suffixe Yahoo, avec la source citée pour chaque place
(12 places — HYPOTHÈSE : heure de la clôture continue, pas l'heure exacte de publication du
fixing d'enchère de clôture, qui suit de quelques minutes ; le délai de stabilisation
(config.yaml, `marche.delai_stabilisation_minutes`) absorbe ce délai de publication).

Place non reconnue (suffixe hors de PLACES) : `complete` renvoyé à `None`, jamais `True` par
défaut — même règle que le reste du projet (donnée incertaine = badge, pas d'estimation
silencieuse). Même principe pour les demi-séances (24/12, 31/12) sur une place non vérifiée :
l'heure de clôture standard est utilisée par prudence (jamais une heure de clôture réduite
inventée), avec un indicateur explicite `demi_seance_non_modelisee`.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from .common import config

MARGE_CLOTURE_MINUTES_DEFAUT = 60  # repli si config.yaml est absent (tests unitaires isolés)

# suffixe Yahoo -> fuseau IANA, heure de clôture locale (h, min), source (consultée 30/09/2026)
PLACES: dict[str, dict] = {
    "PA": {"fuseau": "Europe/Paris", "cloture": (17, 30),
           "source": "euronext.com/en/trading/trading-hours-holidays (Euronext Paris)"},
    "AS": {"fuseau": "Europe/Amsterdam", "cloture": (17, 30),
           "source": "euronext.com/en/trading/trading-hours-holidays (Euronext Amsterdam)"},
    "BR": {"fuseau": "Europe/Brussels", "cloture": (17, 30),
           "source": "euronext.com/en/trading/trading-hours-holidays (Euronext Brussels)"},
    "LS": {"fuseau": "Europe/Lisbon", "cloture": (17, 30),
           "source": "euronext.com/en/trading/trading-hours-holidays (Euronext Lisbon, heure locale WET/WEST)"},
    "DE": {"fuseau": "Europe/Berlin", "cloture": (17, 30),
           "source": "cashmarket.deutsche-boerse.com/.../Trading-calendar-and-trading-hours (Xetra, enchère de clôture 17:30)"},
    "MI": {"fuseau": "Europe/Rome", "cloture": (17, 30),
           "source": "borsaitaliana.it .../tradinghours (Euronext Milan)"},
    "MC": {"fuseau": "Europe/Madrid", "cloture": (17, 30),
           "source": "tradinghours.com/markets/bme (BME Madrid)"},
    "VI": {"fuseau": "Europe/Vienna", "cloture": (17, 30),
           "source": "tradinghours.com (Wiener Börse)"},
    "ST": {"fuseau": "Europe/Stockholm", "cloture": (17, 25),
           "source": "tradinghours.com/markets/nasdaq-stockholm"},
    "CO": {"fuseau": "Europe/Copenhagen", "cloture": (17, 0),
           "source": "tradinghours.com/markets/nasdaq-copenhagen"},
    "HE": {"fuseau": "Europe/Helsinki", "cloture": (18, 25),
           "source": "tradinghours.com/markets/nasdaq-helsinki (heure locale EET/EEST)"},
    "OL": {"fuseau": "Europe/Oslo", "cloture": (16, 20),
           "source": "tradinghours.com (Oslo Børs / Euronext Oslo)"},
    "WA": {"fuseau": "Europe/Warsaw", "cloture": (16, 50),
           "source": "tradinghours.com/markets/gpw (GPW, séance continue jusqu'à 16:50, "
                    "enchère de clôture 16:50-16:59:50)"},
    "AT": {"fuseau": "Europe/Athens", "cloture": (17, 20),
           "source": "athexgroup.gr/en/trade/trading-model (Main Market, période de prix de "
                    "clôture 17:05-17:20)"},
}

# Demi-séances CONFIRMÉES avec une heure de clôture réduite sourcée (Euronext : 24/12 et 31/12,
# clôture continue à 14:05 — euronext.com/en/trading/trading-hours-holidays, consulté 30/09/2026).
# N'inclut QUE les places vérifiées : pas d'heure de clôture réduite inventée pour les autres.
DEMI_SEANCES: dict[tuple[int, int], dict[str, tuple[int, int]]] = {
    (12, 24): {"PA": (14, 5), "AS": (14, 5), "BR": (14, 5), "LS": (14, 5)},
    (12, 31): {"PA": (14, 5), "AS": (14, 5), "BR": (14, 5), "LS": (14, 5)},
}
# Dates où certaines places sont confirmées ENTIÈREMENT FERMÉES (pas de séance du tout) —
# n'affecte pas la logique (l'absence de barre ce jour-là suffit), conservé pour traçabilité.
FERMETURES_CONNUES: dict[tuple[int, int], set[str]] = {
    (12, 24): {"DE", "MI"}, (12, 31): {"DE", "MI"},
}


def _delai_stabilisation_minutes() -> int:
    try:
        return config()["marche"]["delai_stabilisation_minutes"]
    except Exception:  # noqa: BLE001 — config absente (tests isolés) : repli documenté
        return MARGE_CLOTURE_MINUTES_DEFAUT


def _place(ticker: str) -> dict | None:
    if "." not in ticker:
        return None
    return PLACES.get(ticker.rsplit(".", 1)[-1])


def _heure_cloture_effective(suffixe: str, info: dict, date_locale: dt.date) -> tuple[tuple[int, int], bool]:
    """Renvoie ((h, min), demi_seance_non_modelisee). Utilise l'heure de clôture réduite
    connue si la place est dans DEMI_SEANCES pour cette date ; sinon, si la date est une
    demi-séance connue mais la place non vérifiée, renvoie l'heure standard (prudence :
    jamais une heure inventée) avec le drapeau à True."""
    cle = (date_locale.month, date_locale.day)
    reduites = DEMI_SEANCES.get(cle, {})
    if suffixe in reduites:
        return reduites[suffixe], False
    if cle in DEMI_SEANCES or cle in FERMETURES_CONNUES:
        return info["cloture"], True
    return info["cloture"], False


def seance_complete(ticker: str, date_derniere_barre: dt.date, maintenant: dt.datetime | None = None) -> dict:
    """`date_derniere_barre` (date de la dernière ligne renvoyée par yfinance) correspond-elle
    à une séance déjà clôturée (+ délai de stabilisation) sur la place de `ticker` ?

    Règle : retenue seulement si (a) sa date est antérieure à la date du jour dans le fuseau de
    la place, OU (b) elle est terminée depuis au moins le délai de stabilisation
    (`config.yaml: marche.delai_stabilisation_minutes`, défaut 60 min).

    Renvoie {"complete": bool | None, "as_of": ISO UTC, "raison": str,
    "demi_seance_non_modelisee": bool}."""
    info = _place(ticker)
    maintenant = maintenant or dt.datetime.now(dt.timezone.utc)
    as_of = maintenant.astimezone(dt.timezone.utc).isoformat()
    if info is None:
        return {"complete": None, "as_of": as_of,
                "raison": f"place non reconnue pour le suffixe de {ticker!r} (calendrier incomplet)",
                "demi_seance_non_modelisee": False}
    tz = ZoneInfo(info["fuseau"])
    maintenant_local = maintenant.astimezone(tz)
    suffixe = ticker.rsplit(".", 1)[-1]

    if date_derniere_barre < maintenant_local.date():
        return {"complete": True, "as_of": as_of,
                "raison": f"dernière barre {date_derniere_barre} antérieure à aujourd'hui ({info['fuseau']})",
                "demi_seance_non_modelisee": False}
    if date_derniere_barre > maintenant_local.date():
        return {"complete": None, "as_of": as_of,
                "raison": f"dernière barre {date_derniere_barre} postérieure à aujourd'hui ({info['fuseau']}) : incohérent",
                "demi_seance_non_modelisee": False}

    (h, m), demi_non_modelisee = _heure_cloture_effective(suffixe, info, maintenant_local.date())
    delai = _delai_stabilisation_minutes()
    cloture_avec_delai = maintenant_local.replace(hour=h, minute=m, second=0, microsecond=0) \
        + dt.timedelta(minutes=delai)
    complete = maintenant_local >= cloture_avec_delai
    raison = (f"{maintenant_local.strftime('%H:%M')} {info['fuseau']} "
             f"{'≥' if complete else '<'} clôture {h:02d}:{m:02d} + {delai} min de délai de stabilisation")
    if demi_non_modelisee:
        raison += " (demi-séance possible ce jour, heure de clôture standard utilisée par prudence)"
    return {"complete": complete, "as_of": as_of, "raison": raison,
           "demi_seance_non_modelisee": demi_non_modelisee}
