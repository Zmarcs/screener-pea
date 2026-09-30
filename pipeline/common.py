"""Outils partagés : chemins, configuration, HTTP (retries + backoff), cache disque, journal.

Certificats SSL : le Python installé depuis python.org n'embarque pas de certificats
(dossier etc/openssl vide tant que « Install Certificates.command » n'a pas été lancé).
Toutes les requêtes passent donc par `requests`, qui utilise le paquet `certifi`.
La vérification SSL n'est JAMAIS désactivée.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import time
from pathlib import Path

import certifi
import requests
import yaml

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_CACHE = RACINE / "data" / "cache"
DOSSIER_MANUEL = RACINE / "data" / "manual"
DOSSIER_SORTIE = RACINE / "data" / "processed"

# Bibliothèques tierces utilisant la pile SSL standard : on leur indique le magasin certifi.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())


def charger_yaml(chemin: Path | str) -> dict:
    with open(chemin, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def config() -> dict:
    return charger_yaml(RACINE / "pipeline" / "config.yaml")


def mapping() -> dict:
    return charger_yaml(RACINE / "pipeline" / "mapping_ifrs.yaml")


# --------------------------------------------------------------------------- journal
class Journal:
    """Collecte les erreurs et avertissements pour le rapport de fin de run."""

    def __init__(self) -> None:
        self.entrees: list[dict] = []

    def ajouter(self, niveau: str, cle: str, message: str) -> None:
        self.entrees.append({"niveau": niveau, "cle": cle, "message": message})
        print(f"[{niveau}] {cle} : {message}")

    def erreur(self, cle: str, message: str) -> None:
        self.ajouter("ERREUR", cle, message)

    def avertissement(self, cle: str, message: str) -> None:
        self.ajouter("AVERT", cle, message)

    def resume(self) -> str:
        n_err = sum(e["niveau"] == "ERREUR" for e in self.entrees)
        n_av = sum(e["niveau"] == "AVERT" for e in self.entrees)
        lignes = [f"Rapport d'erreurs : {n_err} erreur(s), {n_av} avertissement(s)"]
        lignes += [f"  [{e['niveau']}] {e['cle']} : {e['message']}" for e in self.entrees]
        return "\n".join(lignes)


JOURNAL = Journal()


# --------------------------------------------------------------------------- HTTP
_SESSION: requests.Session | None = None


def session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers["User-Agent"] = "screener-pea/0.1 (usage personnel, non commercial)"
    return _SESSION


def http_get(url: str, *, params: dict | None = None, headers: dict | None = None,
             essais: int = 4, attente: float = 2.0, timeout: float = 60) -> requests.Response:
    """GET avec retries et backoff exponentiel (2 s, 4 s, 8 s…). Lève l'exception finale."""
    derniere: Exception | None = None
    for i in range(essais):
        try:
            r = session().get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            return r
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            derniere = e
            if i < essais - 1:
                time.sleep(attente * (2 ** i))
    assert derniere is not None
    raise derniere


# --------------------------------------------------------------------------- cache disque
def chemin_cache(categorie: str, cle: str, extension: str = "json") -> Path:
    sur = "".join(c if c.isalnum() or c in "-_." else "_" for c in cle)
    if len(sur) > 120:
        sur = sur[:80] + "_" + hashlib.sha1(cle.encode()).hexdigest()[:12]
    d = DOSSIER_CACHE / categorie
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{sur}.{extension}"


def cache_json(categorie: str, cle: str, producteur, *, max_age_jours: float | None = None):
    """Renvoie le JSON en cache, ou appelle `producteur()` et l'enregistre."""
    p = chemin_cache(categorie, cle)
    if p.exists():
        age = (time.time() - p.stat().st_mtime) / 86400
        if max_age_jours is None or age <= max_age_jours:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    donnees = producteur()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False)
    return donnees


def aujourd_hui() -> dt.date:
    return dt.date.today()


def ecrire_json(chemin: Path, donnees) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1, default=str)
