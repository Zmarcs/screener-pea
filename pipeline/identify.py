"""Identification : ISIN → LEI (clé interne) et liste des ISIN rattachés.

Ordre : 1) data/manual/isin_lei.csv (prioritaire, vérifié à la main)
        2) API GLEIF (filtre ISIN)
Pas de recherche par nom (risque de faux positif). Si rien : LEI introuvable,
donc « ESEF introuvable » affiché sur la fiche.
"""
from __future__ import annotations

import csv

from .common import DOSSIER_MANUEL, JOURNAL, cache_json, http_get

GLEIF = "https://api.gleif.org/api/v1/lei-records"


def correspondances_manuelles() -> list[dict]:
    p = DOSSIER_MANUEL / "isin_lei.csv"
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _gleif_par_isin(isin: str) -> dict | None:
    def produire():
        r = http_get(GLEIF, params={"filter[isin]": isin})
        r.raise_for_status()
        return r.json()
    donnees = cache_json("gleif", f"isin_{isin}", produire, max_age_jours=30)
    if not donnees.get("data"):
        return None
    rec = donnees["data"][0]
    return {"lei": rec["id"], "nom_legal": rec["attributes"]["entity"]["legalName"]["name"]}


def _gleif_isins(lei: str) -> list[str]:
    def produire():
        r = http_get(f"{GLEIF}/{lei}/isins", params={"page[size]": 100})
        r.raise_for_status()
        return r.json()
    try:
        donnees = cache_json("gleif", f"isins_{lei}", produire, max_age_jours=30)
        return [x["attributes"]["isin"] for x in donnees.get("data", [])]
    except Exception as e:  # noqa: BLE001
        JOURNAL.avertissement(lei, f"liste des ISIN GLEIF indisponible : {e}")
        return []


def _gleif_nom(lei: str) -> str | None:
    def produire():
        r = http_get(f"{GLEIF}/{lei}")
        r.raise_for_status()
        return r.json()
    try:
        d = cache_json("gleif", f"lei_{lei}", produire, max_age_jours=30)
        return d["data"]["attributes"]["entity"]["legalName"]["name"]
    except Exception:  # noqa: BLE001
        return None


def identifier(isin: str) -> dict:
    """Renvoie {lei, nom_legal, source_lei, isins: [{isin, statut, source}]}.

    lei = None si introuvable (la fiche affichera « LEI introuvable → ESEF introuvable »).
    """
    manuelles = correspondances_manuelles()
    ligne = next((m for m in manuelles if m["isin"] == isin), None)
    if ligne:
        lei, source_lei = ligne["lei"], f"manuel (isin_lei.csv) : {ligne['source']}"
        nom = _gleif_nom(lei)
    else:
        try:
            trouve = _gleif_par_isin(isin)
        except Exception as e:  # noqa: BLE001
            JOURNAL.erreur(isin, f"GLEIF inaccessible : {e}")
            trouve = None
        if not trouve:
            JOURNAL.avertissement(isin, "LEI introuvable (ni isin_lei.csv, ni GLEIF) → ESEF introuvable")
            return {"lei": None, "nom_legal": None, "source_lei": None,
                    "isins": [{"isin": isin, "statut": "actuel", "source": "test_isins.yaml"}]}
        lei, nom, source_lei = trouve["lei"], trouve["nom_legal"], "GLEIF (filtre ISIN)"

    isins = [{"isin": isin, "statut": "actuel", "source": "test_isins.yaml"}]
    for m in manuelles:
        if m["lei"] == lei and m["isin"] != isin:
            isins.append({"isin": m["isin"], "statut": m["statut"], "source": m["source"]})
    for autre in _gleif_isins(lei):
        if all(i["isin"] != autre for i in isins):
            isins.append({"isin": autre, "statut": "gleif_non_verifie", "source": "GLEIF"})
    return {"lei": lei, "nom_legal": nom, "source_lei": source_lei, "isins": isins}
