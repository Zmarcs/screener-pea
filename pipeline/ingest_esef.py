"""Ingestion ESEF depuis filings.xbrl.org (bibliothèque xbrl-filings-api).

Étapes :
1. lister les rapports d'une entité (LEI) ;
2. télécharger le fichier xBRL-JSON de chacun (cache disque) ;
3. déterminer l'exercice RÉEL à partir des faits (pas de la métadonnée d'index) ;
4. exclure les rapports incohérents, sauf réintégration explicite (esef_overrides.yaml) ;
5. dédoublonner : un seul rapport par exercice (langues multiples, rapports corrigés).

Convention xBRL-JSON : une date de fin « 2026-01-01T00:00:00 » signifie « fin de journée
du 31/12/2025 ». On retire donc un jour aux dates de fin et aux dates instantanées.
"""
from __future__ import annotations

import datetime as dt
import warnings
from collections import Counter

from .common import DOSSIER_MANUEL, JOURNAL, cache_json, charger_yaml, config, http_get

BASE = "https://filings.xbrl.org"


def _lister_via_bibliotheque(lei: str) -> list[dict]:
    import xbrl_filings_api as xf

    with warnings.catch_warnings():
        # « entity.identifier » fonctionne mais n'est pas dans la liste officielle de la lib.
        warnings.simplefilter("ignore", xf.FilterNotSupportedWarning)
        rapports = xf.get_filings({"entity.identifier": lei})
    sortie = []
    for f in rapports:
        sortie.append({
            "api_id": f.api_id,
            "fxo_id": f.filing_index,
            "period_end_index": f.last_end_date.isoformat() if f.last_end_date else None,
            "langue": f.language,
            "pays": f.country,
            "date_ajout": f.added_time.isoformat() if f.added_time else None,
            "erreurs": f.error_count,
            "avertissements": f.warning_count,
            "incoherences": f.inconsistency_count,
            "json_url": f.json_url,
            "xhtml_url": f.xhtml_url,
            "viewer_url": f.viewer_url,
        })
    return sortie


def lister_rapports(lei: str) -> list[dict]:
    try:
        return cache_json("esef_index", lei, lambda: _lister_via_bibliotheque(lei), max_age_jours=7)
    except Exception as e:  # noqa: BLE001
        JOURNAL.erreur(lei, f"filings.xbrl.org inaccessible : {e}")
        return []


def telecharger_faits(rapport: dict) -> dict | None:
    url = rapport["json_url"]
    if not url:
        JOURNAL.avertissement(rapport["fxo_id"], "rapport non converti par filings.xbrl.org "
                                                 "(paquet ZIP seul, pas de xBRL-JSON) : exclu")
        return None
    if url.startswith("/"):
        url = BASE + url

    def produire():
        r = http_get(url, timeout=120)
        r.raise_for_status()
        return r.json()
    try:
        return cache_json("esef_json", rapport["fxo_id"], produire)
    except Exception as e:  # noqa: BLE001
        JOURNAL.erreur(rapport["fxo_id"], f"téléchargement xBRL-JSON impossible : {e}")
        return None


# --------------------------------------------------------------------------- périodes
def date_fin(texte: str) -> dt.date:
    """Date de fin xBRL-JSON (exclusive à minuit) → date de clôture comptable."""
    d = dt.datetime.fromisoformat(texte)
    if d.time() == dt.time(0, 0):
        return (d - dt.timedelta(days=1)).date()
    return d.date()


def analyser_periode(periode: str) -> tuple[dt.date | None, dt.date]:
    """'debut/fin' → (debut, cloture) ; 'instant' → (None, date)."""
    if "/" in periode:
        debut, fin = periode.split("/")
        return dt.datetime.fromisoformat(debut).date(), date_fin(fin)
    return None, date_fin(periode)


def cloture_reelle(faits: dict) -> dt.date | None:
    """Exercice couvert = fin de la période annuelle (330 à 400 jours) la plus fréquente,
    en ne retenant que la plus récente des périodes annuelles fréquentes (le courant,
    pas le comparatif)."""
    compteur: Counter = Counter()
    for f in faits.get("facts", {}).values():
        p = f["dimensions"].get("period", "")
        if "/" not in p:
            continue
        debut, fin = analyser_periode(p)
        if 330 <= (fin - debut).days <= 400:
            compteur[fin] += 1
    if not compteur:
        return None
    frequentes = [d for d, n in compteur.items() if n >= 0.2 * max(compteur.values())]
    return max(frequentes)


def selectionner_rapports(lei: str) -> tuple[list[dict], list[dict]]:
    """Renvoie (rapports retenus avec faits, rapports écartés avec motif)."""
    cfg = config()
    langues = cfg["sources"]["esef_langues_preferees"]
    overrides = charger_yaml(DOSSIER_MANUEL / "esef_overrides.yaml").get("rapports", {}) or {}

    candidats, ecartes = [], []
    for r in lister_rapports(lei):
        faits = telecharger_faits(r)
        if faits is None:
            ecartes.append({**r, "motif": "rapport non converti par filings.xbrl.org (paquet ZIP seul) : "
                                          "l'exercice n'est connu que par le comparatif du rapport suivant"})
            continue
        cloture = cloture_reelle(faits)
        index = dt.date.fromisoformat(r["period_end_index"][:10]) if r["period_end_index"] else None
        r = {**r, "cloture": cloture.isoformat() if cloture else None, "faits": faits}
        if cloture is None:
            ecartes.append({**r, "motif": "aucune période annuelle trouvée dans les faits"})
            continue
        if index != cloture:
            ov = overrides.get(r["fxo_id"])
            if ov and dt.date.fromisoformat(str(ov["exercice_reel_cloture"])) == cloture:
                r["badges"] = ["métadonnée d'index corrigée (esef_overrides.yaml)"]
                r["explication_override"] = " ".join(str(ov["explication"]).split())
            else:
                ecartes.append({**r, "motif": f"période d'index {index} ≠ période des faits {cloture} "
                                              "(exclu tant que non expliqué dans esef_overrides.yaml)"})
                JOURNAL.avertissement(lei, f"rapport {r['fxo_id']} exclu : index {index} ≠ faits {cloture}")
                continue
        candidats.append(r)

    # Dédoublonnage : un rapport par exercice.
    # Priorité : dépôt le plus récent (corrections), puis langue préférée, puis moins d'erreurs.
    pays_frequent = max(set(r["pays"] for r in candidats), key=[r["pays"] for r in candidats].count) \
        if candidats else None

    def rang(r):
        langue = langues.index(r["langue"]) if r["langue"] in langues else len(langues)
        return (r["pays"] == pays_frequent, r["date_ajout"] or "", -langue, -(r["erreurs"] or 0))

    par_exercice: dict[str, list[dict]] = {}
    for r in candidats:
        par_exercice.setdefault(r["cloture"], []).append(r)
    retenus = []
    for cloture, groupe in sorted(par_exercice.items()):
        groupe.sort(key=rang, reverse=True)
        choisi = groupe[0]
        # Deux dépôts le même jour dans des langues différentes = versions linguistiques.
        for autre in groupe[1:]:
            meme_jour = (autre["date_ajout"] or "")[:10] == (choisi["date_ajout"] or "")[:10]
            if autre["pays"] != choisi["pays"]:
                motif = f"même rapport déposé dans un autre pays ({autre['pays']}, double cotation)"
            elif meme_jour and autre["langue"] != choisi["langue"]:
                motif = "doublon de langue"
            else:
                motif = "remplacé par un dépôt plus récent (correction probable)"
            ecartes.append({**autre, "motif": f"{motif} ; retenu : {choisi['fxo_id']}",
                            "doublon_de": choisi["fxo_id"]})
        choisi["doublons"] = [a["fxo_id"] for a in groupe[1:]]
        choisi["faits_doublons"] = [a["faits"] for a in groupe[1:]]
        retenus.append(choisi)
    return retenus, ecartes
