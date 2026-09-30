"""Corrections manuelles : data/manual/{isin}.yaml (priment sur les données automatiques)."""
from __future__ import annotations

import datetime as dt

from .common import DOSSIER_MANUEL, charger_yaml


def appliquer_corrections(isin: str, series: dict[str, dict[dt.date, dict]]) -> list[dict]:
    p = DOSSIER_MANUEL / f"{isin}.yaml"
    if not p.exists():
        return []
    appliquees = []
    for c in charger_yaml(p).get("corrections", []) or []:
        serie = series.setdefault(c["poste"], {})
        # Exercice désigné par l'année de clôture : on retrouve la date exacte si elle existe.
        cible = next((d for d in serie if d.year == int(c["exercice"])), None) \
            or dt.date(int(c["exercice"]), 12, 31)
        avant = serie.get(cible, {}).get("valeur")
        serie[cible] = {"valeur": c["valeur"], "source": "manuel", "concept": "correction manuelle",
                        "devise": serie.get(cible, {}).get("devise"), "rapport": None,
                        "lien": None, "date_rapport": None, "qualite": None,
                        "badges": [f"correction manuelle : {c.get('motif', '')} ({c['source']})"],
                        "valeur_automatique": avant}
        appliquees.append({**c, "valeur_automatique": avant})
    return appliquees
