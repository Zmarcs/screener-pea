"""Normalisation : faits ESEF → une valeur par poste et par exercice, traçable.

Chaque valeur est un dictionnaire :
  valeur, cloture (date), source, concept, devise, rapport (fxo_id), lien, date_rapport,
  qualite {erreurs, avertissements, incoherences}, badges [..], et le cas échéant
  valeur_origine / ecart / details.

Règles :
- donnée absente = pas d'entrée (le calcul la verra comme None → badge « indisponible ») ;
- pour chaque exercice, on retient le chiffre du rapport LE PLUS RÉCENT qui le contient
  (comparatif retraité) ; l'écart avec le chiffre d'origine est signalé ;
- BNPA et nombre d'actions : un facteur n'est appliqué que s'il correspond à un split
  présent dans yfinance ; un retraitement sans split connu est signalé « retraitement non
  expliqué » et n'est pas étendu aux exercices plus anciens.
"""
from __future__ import annotations

import datetime as dt

from .common import JOURNAL, config, mapping
from .ingest_esef import BASE, analyser_periode

POSTES_PAR_ACTION = {"bnpa"}
POSTES_ACTIONS = {"nombre_actions"}


def _lien(rapport: dict) -> str | None:
    url = rapport.get("viewer_url") or rapport.get("xhtml_url")
    if url and url.startswith("/"):
        url = BASE + url
    return url


CHAMPS_DE_BASE = {"concept", "entity", "period", "unit", "language"}


def _cle_concept(spec: str) -> tuple[str, frozenset]:
    """'concept' ou 'concept[axe=membre]' → (concept, dimensions)."""
    if "[" not in spec:
        return spec, frozenset()
    concept, reste = spec.split("[", 1)
    axe, membre = reste.rstrip("]").split("=")
    return concept, frozenset({(axe, membre)})


def _index_faits(faits: dict) -> dict[tuple[str, frozenset], list[dict]]:
    """(concept, dimensions) → faits. Les faits ventilés ne sont lus que si le mapping
    demande explicitement leur dimension."""
    index: dict[tuple[str, frozenset], list[dict]] = {}
    for fid, f in faits.get("facts", {}).items():
        dims = f["dimensions"]
        extra = frozenset((k, v) for k, v in dims.items() if k not in CHAMPS_DE_BASE)
        index.setdefault((dims["concept"], extra), []).append({**f, "id": fid})
    return index


def _valeurs_concept(index, spec: str, type_poste: str) -> dict[dt.date, dict]:
    """Valeurs d'un concept par date de clôture (flux : périodes annuelles seulement)."""
    concept, dims = _cle_concept(spec)
    sortie: dict[dt.date, dict] = {}
    for f in index.get((concept, dims), []):
        if f.get("value") in (None, ""):
            continue
        debut, cloture = analyser_periode(f["dimensions"]["period"])
        duree_annuelle = debut is not None and 330 <= (cloture - debut).days <= 400
        if type_poste in ("flux", "par_action"):
            if not duree_annuelle:
                continue
        elif debut is not None and not (concept.endswith("WeightedAverageShares") and duree_annuelle):
            continue  # stock / actions : date instantanée (sauf moyenne pondérée)
        try:
            v = float(f["value"])
        except ValueError:
            continue
        unite = f["dimensions"].get("unit", "")
        devise = unite.split(":")[1].split("/")[0] if unite.startswith("iso4217:") else None
        if cloture in sortie:
            if abs(sortie[cloture]["valeur"] - v) > 1e-9 * max(1, abs(v)):
                sortie[cloture].setdefault("conflits", []).append(v)
            continue
        sortie[cloture] = {"valeur": v, "devise": devise, "fact_id": f["id"], "decimals": f.get("decimals")}
    return sortie


def _valeurs_poste(index, spec: dict, type_poste: str, meta: dict) -> dict[dt.date, dict]:
    valeurs: dict[dt.date, dict] = {}
    for concept in spec.get("concepts", []):
        for d, v in _valeurs_concept(index, concept, type_poste).items():
            if d not in valeurs:
                valeurs[d] = {**meta, **v, "concept": concept, "badges": []}
    partielle = spec.get("partielle_autorisee", True)
    for groupe in spec.get("sommes", []):
        composants = {c: _valeurs_concept(index, c, type_poste) for c in groupe}
        dates = set().union(*[set(x) for x in composants.values()])
        for d in sorted(dates):
            if d in valeurs:
                continue
            presents = [c for c in groupe if d in composants[c]]
            absents = [c for c in groupe if c not in presents]
            if absents and not partielle:
                continue
            badges = ["somme partielle : composant(s) non balisé(s) " + ", ".join(absents)] if absents else []
            valeurs[d] = {**meta, "valeur": sum(composants[c][d]["valeur"] for c in presents),
                          "devise": composants[presents[0]][d]["devise"],
                          "concept": " + ".join(presents), "badges": badges,
                          "fact_id": [composants[c][d]["fact_id"] for c in presents],
                          "composants": {c: composants[c][d]["valeur"] for c in presents}}
    return valeurs


def extraire_rapport(rapport: dict, postes: dict, extensions: dict | None = None) -> dict[str, dict[dt.date, dict]]:
    """Toutes les valeurs (courant + comparatifs) d'un rapport, par poste et date.
    extensions : concepts propres à la société (mapping_ifrs.yaml, section extensions)."""
    index = _index_faits(rapport["faits"])
    meta = {
        "source": "ESEF",
        "rapport": rapport["fxo_id"],
        "lien": _lien(rapport),
        "date_rapport": (rapport.get("date_ajout") or "")[:10],
        "cloture_rapport": rapport["cloture"],
        "qualite": {"erreurs": rapport.get("erreurs"), "avertissements": rapport.get("avertissements"),
                    "incoherences": rapport.get("incoherences")},
    }
    resultat: dict[str, dict[dt.date, dict]] = {}
    for poste, spec in postes.items():
        valeurs = _valeurs_poste(index, spec, spec["type"], meta)
        ext = (extensions or {}).get(poste)
        if ext:
            for d, v in _valeurs_poste(index, ext, spec["type"], meta).items():
                if d not in valeurs:
                    if poste == "capex" and v["valeur"] is not None and v["valeur"] < 0:
                        # convention capex = magnitude positive (comme les concepts génériques
                        # ifrs-full ci-dessus) ; certaines extensions maison taguent un flux
                        # sortant négatif (ex. Thermador) — valeur absolue, signalée.
                        v["valeur"] = abs(v["valeur"])
                        v["badges"].append("signe inversé (valeur absolue) : le concept maison taguait "
                                           "un flux sortant négatif, capex retenu en magnitude positive")
                    v["badges"].append(f"concept propre à la société ({ext.get('source', '')})")
                    valeurs[d] = v
        resultat[poste] = valeurs
    return resultat


def _secours(series: dict[str, dict[dt.date, dict]]) -> None:
    """Calculs de secours, toujours signalés par un badge."""
    def ajouter(poste, d, base, valeur, concept, badge, details):
        series.setdefault(poste, {})[d] = {**base, "valeur": valeur, "source": "calcul", "concept": concept,
                                           "badges": [badge], "details": details, "fact_id": None}

    ebit, rai = series.setdefault("ebit", {}), series.get("resultat_avant_impot", {})
    cf, pf = series.get("charges_financieres", {}), series.get("produits_financiers", {})
    for d, v in rai.items():
        if d not in ebit and d in cf and d in pf:
            ajouter("ebit", d, v, v["valeur"] + cf[d]["valeur"] - pf[d]["valeur"],
                    "ProfitLossBeforeTax + FinanceCosts − FinanceIncome",
                    "EBIT reconstitué (inclut la quote-part des mises en équivalence)",
                    {"resultat_avant_impot": v["valeur"], "charges_financieres": cf[d]["valeur"],
                     "produits_financiers": pf[d]["valeur"]})
    at, cp = series.get("actif_total", {}), series.get("capitaux_propres", {})
    dtot = series.setdefault("dettes_totales", {})
    for d, v in at.items():
        if d not in dtot and d in cp:
            ajouter("dettes_totales", d, v, v["valeur"] - cp[d]["valeur"], "Assets − Equity",
                    "dettes totales calculées (actif − capitaux propres)",
                    {"actif_total": v["valeur"], "capitaux_propres": cp[d]["valeur"]})
    anc, ac = series.get("actif_non_courant", {}), series.setdefault("actif_courant", {})
    for d, v in at.items():
        if d not in ac and d in anc:
            ajouter("actif_courant", d, v, v["valeur"] - anc[d]["valeur"], "Assets − NoncurrentAssets",
                    "actif courant calculé (actif total − actif non courant)",
                    {"actif_total": v["valeur"], "actif_non_courant": anc[d]["valeur"]})
    pnc, dc = series.get("passif_non_courant", {}), series.setdefault("dettes_courantes", {})
    for d, v in dtot.items():
        if d not in dc and d in pnc:
            ajouter("dettes_courantes", d, v, v["valeur"] - pnc[d]["valeur"], "dettes totales − NoncurrentLiabilities",
                    "dettes courantes calculées (dettes totales − passifs non courants)",
                    {"dettes_totales": v["valeur"], "passif_non_courant": pnc[d]["valeur"]})
    ca, cdv = series.get("chiffre_affaires", {}), series.get("cout_des_ventes", {})
    mb = series.setdefault("marge_brute", {})
    for d, v in ca.items():
        if d not in mb and d in cdv:
            ajouter("marge_brute", d, v, v["valeur"] - cdv[d]["valeur"], "Revenue − CostOfSales",
                    "marge brute reconstituée (chiffre d'affaires − coût des ventes)",
                    {"chiffre_affaires": v["valeur"], "cout_des_ventes": cdv[d]["valeur"]})


def rapports_incoherents(rapports: list[dict], lei: str | None) -> list[dict]:
    """Contrôle de cohérence entre rapports successifs : le comparatif N−1 d'un rapport doit
    correspondre (à `seuil_incoherence_rapport` près) au chiffre publié dans le rapport N−1,
    pour le CA et l'actif total. Un écart plus grand signale une erreur de balisage probable."""
    seuil = config()["sources"]["seuil_incoherence_rapport"]
    postes = {p: mapping()["postes"][p] for p in ("chiffre_affaires", "actif_total")}
    ext = (mapping().get("extensions") or {}).get(lei, {})
    tries = sorted(rapports, key=lambda r: r["cloture"])
    extraits = {r["fxo_id"]: extraire_rapport(r, postes, ext) for r in tries}
    incoherents = []
    for prec, suiv in zip(tries, tries[1:]):
        d = dt.date.fromisoformat(prec["cloture"])
        for p in postes:
            a = extraits[prec["fxo_id"]][p].get(d, {}).get("valeur")
            b = extraits[suiv["fxo_id"]][p].get(d, {}).get("valeur")
            if a and b is not None and abs(b - a) / abs(a) > seuil:
                incoherents.append({"fxo_id": suiv["fxo_id"], "poste": p, "exercice": prec["cloture"],
                                    "valeur_rapport_precedent": a, "valeur_comparatif": b,
                                    "rapport_precedent": prec["fxo_id"]})
    return incoherents


def fusionner_rapports(rapports: list[dict], lei: str | None = None) -> dict[str, dict[str, dict]]:
    """Série par poste : pour chaque date, valeur du rapport le plus récent + trace de l'origine."""
    cfg = config()
    tol = cfg["sources"]["tolerance_ecart_relatif"]
    postes = mapping()["postes"]
    ext = (mapping().get("extensions") or {}).get(lei, {})
    extraits = [(r, extraire_rapport(r, postes, ext)) for r in sorted(rapports, key=lambda r: r["cloture"])]

    series: dict[str, dict[dt.date, dict]] = {}
    for poste in postes:
        fusion: dict[dt.date, dict] = {}
        for rapport, ex in extraits:              # du plus ancien au plus récent
            for d, v in ex.get(poste, {}).items():
                if d > dt.date.fromisoformat(rapport["cloture"]):
                    continue
                precedent = fusion.get(d)
                v = {**v, "badges": list(v["badges"])}
                if precedent is not None:
                    origine = precedent.get("valeur_origine_complete", precedent)
                    v["valeur_origine_complete"] = origine
                    v["valeur_origine"] = origine["valeur"]
                    v["rapport_origine"] = origine["rapport"]
                    v["date_rapport_origine"] = origine["date_rapport"]
                fusion[d] = v
        for d, v in fusion.items():
            if "valeur_origine" in v:
                o = v["valeur_origine"]
                ecart = (v["valeur"] - o) / abs(o) if o else (0.0 if v["valeur"] == o else float("inf"))
                v["ecart_origine"] = ecart
                if abs(ecart) > tol:
                    v["badges"].append(
                        f"retraité : {o:g} dans le rapport d'origine ({v['rapport_origine']}), "
                        f"{v['valeur']:g} dans le rapport le plus récent ({v['rapport']})")
            v.pop("valeur_origine_complete", None)
        series[poste] = fusion
    _secours(series)
    return series


# --------------------------------------------------------------------------- splits
def ajuster_splits(series: dict[str, dict], splits: list[dict], actions_yfinance: float | None = None) -> list[dict]:
    """Ajuste BNPA et nombre d'actions des splits yfinance survenus APRÈS la publication
    du rapport source. Renvoie le journal des retraitements (expliqués ou non).

    splits : [{"date": "2022-05-17", "ratio": 4.0}] (ratio = nouvelles actions / anciennes).
    actions_yfinance : nombre d'actions yfinance actuel (`sharesOutstanding`), utilisé pour
    recouper un retraitement non expliqué du nombre d'actions (badge, pas une correction).

    PORTÉE DE LA RÈGLE « retraitement non expliqué → valeur d'origine conservée » (règle ajoutée) :
    limitée aux SEULS postes par action et nombre d'actions (la boucle `for poste in ("bnpa",
    "nombre_actions")` ci-dessous, aucun autre poste n'entre dans cette fonction). Aucun split ne
    justifiant le facteur observé, on ne garde PAS le comparatif du rapport le plus récent — on
    revient à la valeur D'ORIGINE (le rapport de l'exercice lui-même), jusqu'à preuve du contraire
    (badge). C'est le seul poste concerné qui est modifié : l'autre poste de l'identité BNPA ×
    actions ≈ résultat net (ex. le BNPA quand c'est le nombre d'actions qui est en cause) n'est
    pas mis en cause sans preuve.

    Pour le CHIFFRE D'AFFAIRES, l'EBIT, les ACTIFS (flux et stocks) : cette règle NE S'APPLIQUE
    PAS. Le rapport le plus récent reste la référence (`fusionner_rapports`, badge « retraité »
    simple si l'écart dépasse `tolerance_ecart_relatif`), y compris pour un écart important
    légitime (activités abandonnées reclassées, changement de norme comptable, périmètre de
    consolidation). Seul un échec du contrôle de cohérence CA/actif total à plus de 50 %
    (`rapports_incoherents`, `seuil_incoherence_rapport`) exclut alors le RAPPORT entier — jamais
    une correction silencieuse poste par poste comme ici. Voir test_normalize.py :
    test_ca_ebit_non_revertis_meme_si_ecart_important (portée vérifiée)."""
    tol = config()["sources"]["tolerance_split"]
    tol_ecart = config()["sources"]["tolerance_ecart_relatif"]
    journal = []
    splits = sorted(splits, key=lambda s: s["date"])

    for poste in ("bnpa", "nombre_actions"):
        for d, v in series.get(poste, {}).items():
            if v["source"] != "ESEF":
                continue
            publication = v["date_rapport"]
            facteur = 1.0
            appliques = []
            for s in splits:
                if s["date"] > publication and s["date"] > d.isoformat():
                    facteur *= s["ratio"]
                    appliques.append(s)
            # Retraitement observé entre rapport d'origine et rapport récent ?
            observe = None
            if v.get("valeur_origine") not in (None, 0) and v["valeur"] != 0:
                observe = v["valeur_origine"] / v["valeur"]
                if poste == "nombre_actions":
                    observe = 1 / observe
            if observe is not None and abs(observe - 1) > tol_ecart:
                # facteur observé : doit correspondre à un split entre les deux publications
                # splits survenus entre la publication d'origine et celle qui retraite
                entre = [s for s in splits if v["date_rapport_origine"] < s["date"] <= publication]
                attendu = 1.0
                for s in entre:
                    attendu *= s["ratio"]
                explique = entre and abs(observe / attendu - 1) <= tol
                entree = {"poste": poste, "cloture": d.isoformat(), "valeur_origine": v["valeur_origine"],
                          "valeur_retraitee": v["valeur"], "facteur_observe": round(observe, 6),
                          "splits_yfinance": entre, "explique": bool(explique),
                          "rapport_origine": v.get("rapport_origine"), "rapport_retraitant": v.get("rapport")}
                if explique:
                    v["badges"] = [b for b in v["badges"] if not b.startswith("retraité")]
                    v["badges"].append(f"retraité par le rapport {v['rapport']} (split yfinance "
                                       f"{', '.join(s['date'] + ' ×' + format(s['ratio'], 'g') for s in entre)})")
                else:
                    v["badges"] = [b for b in v["badges"] if not b.startswith("retraité")]
                    valeur_ecartee = v["valeur"]
                    v["valeur"] = v["valeur_origine"]
                    v["ecart_origine"] = 0.0
                    v["badges"].append(
                        f"retraitement non expliqué (facteur observé {observe:.4g}, aucun split yfinance "
                        f"correspondant) : valeur d'origine du rapport {v.get('rapport_origine')} conservée "
                        f"({v['valeur']:g}), comparatif du rapport {v.get('rapport')} écarté ({valeur_ecartee:g})")
                    entree["valeur_retenue"] = v["valeur"]
                    entree["valeur_ecartee"] = valeur_ecartee
                    if poste == "nombre_actions" and actions_yfinance:
                        ecart_yf = (v["valeur"] - actions_yfinance) / actions_yfinance
                        entree["nombre_actions_yfinance_actuel"] = actions_yfinance
                        entree["ecart_vs_yfinance_actuel"] = ecart_yf
                        v["badges"].append(
                            f"recoupement yfinance : {actions_yfinance:g} actions actuelles "
                            f"({ecart_yf:+.0%} vs valeur d'origine conservée {v['valeur']:g}) — écart non "
                            "expliqué à ce stade (nombre d'actions actuel, pas historique : une émission ou "
                            "un rachat réel entre l'exercice conservé et aujourd'hui n'est pas exclu, à "
                            "vérifier dans les rapports ESEF plus récents s'ils deviennent disponibles)")
                journal.append(entree)
            if facteur != 1.0:
                origine = v["valeur"]
                v["valeur_avant_split"] = origine
                v["valeur"] = origine / facteur if poste == "bnpa" else origine * facteur
                v["badges"].append(
                    f"ajusté du split yfinance ({', '.join(s['date'] + ' ×' + format(s['ratio'], 'g') for s in appliques)}) "
                    f": {origine:g} → {v['valeur']:g}")
                journal.append({"poste": poste, "cloture": d.isoformat(), "valeur_publiee": origine,
                                "valeur_ajustee": v["valeur"], "splits_yfinance": appliques,
                                "explique": True, "type": "ajustement"})
    return journal


# --------------------------------------------------------------------------- contrôles d'identité
CONTROLES = ("bnpa_actions", "actif_passif", "marge_brute_ca", "marge_ebit_bornes")


def controler_identites(series: dict[str, dict[dt.date, dict]], cfg: dict, cle: str) -> dict:
    """Contrôles de cohérence comptable (règle ajoutée), 4 par exercice : BNPA × actions ≈
    résultat net ; actif total ≈ dettes totales + capitaux propres (± `tolerance_ecart`) ; marge
    brute ≤ chiffre d'affaires ; marge EBIT dans [-`borne_marge_ebit`, +`borne_marge_ebit`].

    Chaque contrôle, par exercice, a l'un de ces états :
    - "ok" / "quarantaine" (exécuté : conclusion atteinte — écart mis en quarantaine, retiré de
      la série, badge + journal — quand plusieurs postes participent à une identité approximative,
      HYPOTHÈSE : on quarantaine le côté le moins directement balisé (BNPA + actions ; actif total
      + dettes totales), en gardant comme référence le poste au concept IFRS unique le plus scruté
      (résultat net ; capitaux propres) ; les inégalités ne mettent en quarantaine que le poste
      testé (marge_brute, ebit), le CA sert de référence) ;
    - "non_concluant" (exécuté mais sans conclusion fiable : cas du contrôle BNPA × actions sans
      nombre d'actions MOYEN PONDÉRÉ balisé — le poste `nombre_actions` du pipeline est le nombre
      d'actions DE CLÔTURE, hypothèse mapping_ifrs.yaml, pas comparable au dénominateur du BNPA
      (IAS 33) en cas d'émission/rachat d'actions en cours d'exercice (cas Valneva FY2022) : le
      résultat n'est montré qu'à titre indicatif, jamais de quarantaine) ;
    - "non_disponible" (donnée(s) manquante(s) : le contrôle n'a pas pu être exécuté du tout).

    Renvoie {"quarantaine": [...], "non_concluant": [...], "resume": {date_iso: {"executes": x,
    "sur": 4, "non_controle": bool, "partiel": bool}}} — "executes" = "ok" + "quarantaine" (une
    vraie conclusion a été atteinte) ; à 0/4 exécuté, "non_controle" (badge "non contrôlé" : aucun
    contrôle concluant, cas Brunello Cucinelli FY2025 si le rapport corrompu n'avait pas déjà été
    écarté par ailleurs) ; en dessous de `seuil_partiel` (règle ajoutée, PARAMÈTRE config.yaml)
    mais au moins 1, "partiel" (badge "contrôle partiel")."""
    c = cfg["controles_identite"]
    tol, borne_ebit = c["tolerance_ecart"], c["borne_marge_ebit"]
    quarantaine_j: list[dict] = []
    non_concluant_j: list[dict] = []
    resume: dict[str, dict] = {}

    def valeur(poste, d):
        return (series.get(poste, {}).get(d) or {}).get("valeur")

    def quarantaine(postes, d, motif):
        retires = []
        for poste in postes:
            v = series.get(poste, {}).pop(d, None)
            if v is not None:
                retires.append(poste)
                quarantaine_j.append({"postes": list(postes), "poste_retire": poste, "cloture": d.isoformat(),
                                      "valeur": v["valeur"], "motif": motif})
        if retires:
            JOURNAL.avertissement(cle, f"quarantaine {'/'.join(retires)} FY{d.year} : {motif}")

    # Seuls les exercices réels (clôtures ayant un chiffre d'affaires, comme dates_clotures())
    # sont contrôlés : certains postes portent aussi des faits isolés à des dates qui ne sont pas
    # des clôtures d'exercice (ex. solde d'ouverture retraité IFRS 16 « au 1er janvier N »,
    # comparatif d'un rapport plus ancien) — les inclure produirait des "0/4 non contrôlé" sur des
    # dates qui ne correspondent à aucun exercice réellement utilisé par le pipeline.
    dates = set(dates_clotures(series))

    for d in sorted(dates):
        etats = {}

        bnpa, rn = valeur("bnpa", d), valeur("resultat_net", d)
        pondere = valeur("nombre_actions_moyen_pondere", d)
        actions_cloture = valeur("nombre_actions", d)
        if None not in (bnpa, pondere, rn) and rn:
            estime = bnpa * pondere
            ecart = (estime - rn) / abs(rn)
            if abs(ecart) > tol:
                quarantaine(("bnpa", "nombre_actions_moyen_pondere"), d,
                            f"BNPA × actions moyen pondéré = {estime:,g} ≠ résultat net {rn:,g} "
                            f"(écart {ecart:+.0%} > {tol:.0%})")
                etats["bnpa_actions"] = "quarantaine"
            else:
                etats["bnpa_actions"] = "ok"
        elif None not in (bnpa, actions_cloture, rn) and rn:
            estime = bnpa * actions_cloture
            ecart = (estime - rn) / abs(rn)
            etats["bnpa_actions"] = "non_concluant"
            if abs(ecart) > tol:
                non_concluant_j.append({
                    "controle": "bnpa_actions", "cloture": d.isoformat(), "ecart_actions_cloture": ecart,
                    "motif": f"BNPA × actions DE CLÔTURE (pas de nombre pondéré balisé) = {estime:,g} ≠ "
                             f"résultat net {rn:,g} (écart {ecart:+.0%}) — non concluant, pas de quarantaine : "
                             "l'écart peut venir du dénominateur (clôture, pas moyen pondéré), pas des données."})
        else:
            etats["bnpa_actions"] = "non_disponible"

        at, dtot, cp = valeur("actif_total", d), valeur("dettes_totales", d), valeur("capitaux_propres", d)
        if None not in (at, dtot, cp) and at:
            ecart = (dtot + cp - at) / abs(at)
            if abs(ecart) > tol:
                quarantaine(("actif_total", "dettes_totales"), d,
                            f"actif total {at:,g} ≠ dettes totales + capitaux propres {dtot + cp:,g} "
                            f"(écart {ecart:+.0%} > {tol:.0%})")
                etats["actif_passif"] = "quarantaine"
            else:
                etats["actif_passif"] = "ok"
        else:
            etats["actif_passif"] = "non_disponible"

        mb, ca = valeur("marge_brute", d), valeur("chiffre_affaires", d)
        if None not in (mb, ca):
            if mb > ca:
                quarantaine(("marge_brute",), d, f"marge brute {mb:,g} > chiffre d'affaires {ca:,g}")
                etats["marge_brute_ca"] = "quarantaine"
            else:
                etats["marge_brute_ca"] = "ok"
        else:
            etats["marge_brute_ca"] = "non_disponible"

        ebit, ca2 = valeur("ebit", d), valeur("chiffre_affaires", d)
        if None not in (ebit, ca2) and ca2:
            marge = ebit / ca2
            if not (-borne_ebit <= marge <= borne_ebit):
                quarantaine(("ebit",), d, f"marge EBIT {marge:+.0%} hors bornes [-{borne_ebit:.0%}, +{borne_ebit:.0%}]")
                etats["marge_ebit_bornes"] = "quarantaine"
            else:
                etats["marge_ebit_bornes"] = "ok"
        else:
            etats["marge_ebit_bornes"] = "non_disponible"

        executes = sum(1 for e in etats.values() if e in ("ok", "quarantaine"))
        seuil_partiel = c["seuil_partiel"]
        resume[d.isoformat()] = {"etats": etats, "executes": executes, "sur": len(CONTROLES),
                                 "non_controle": executes == 0,
                                 "partiel": 0 < executes < seuil_partiel}
        if executes == 0:
            JOURNAL.avertissement(cle, f"contrôles d'identité FY{d.year} : non contrôlé (0/{len(CONTROLES)}, "
                                       "données insuffisantes)")
        elif executes < seuil_partiel:
            JOURNAL.avertissement(cle, f"contrôles d'identité FY{d.year} : contrôle partiel "
                                       f"({executes}/{len(CONTROLES)} < seuil {seuil_partiel})")

    return {"quarantaine": quarantaine_j, "non_concluant": non_concluant_j, "resume": resume}


# --------------------------------------------------------------------------- utilitaires
def en_liste(serie: dict, fenetre: int | None = None) -> list[tuple[dt.date, float]]:
    """{date: valeur} → [(date, valeur)] triée, valeurs non nulles, derniers `fenetre` points."""
    pts = sorted((d, v["valeur"]) for d, v in serie.items() if v and v.get("valeur") is not None)
    return pts[-fenetre:] if fenetre else pts


def dates_clotures(series: dict) -> list[dt.date]:
    """Exercices disponibles = dates ayant un chiffre d'affaires."""
    return sorted(d for d, v in series.get("chiffre_affaires", {}).items() if v.get("valeur") is not None)
