"""Génère docs/rapport_etape1.md à partir de data/processed/ et de
data/manual/verification_etape1.yaml. Lancer après le pipeline :
    .venv/bin/python -m pipeline.report_etape1
"""
from __future__ import annotations

import json
import subprocess
import sys

from .calc import porte as P
from .common import DOSSIER_MANUEL, DOSSIER_SORTIE, RACINE, charger_yaml, config

ICONE = {"ok": "✅", "ko": "❌", "ne": "⚪ n.é."}
TIMING = {"vert": "🟢", "jaune": "🟡", "rouge": "🔴", "ne": "⚪ n.é."}
LIBELLES_POSTES = {
    "chiffre_affaires": "Chiffre d'affaires", "marge_brute": "Marge brute", "ebit": "EBIT (résultat opérationnel)",
    "resultat_net": "Résultat net part du groupe", "bnpa": "BNPA de base", "actif_courant": "Actif courant",
    "actif_total": "Actif total", "capitaux_propres": "Capitaux propres", "dette_long_terme": "Dette long terme",
    "dettes_courantes": "Dettes courantes", "reserves": "Réserves (résultats non distribués)",
    "cash_flow_operationnel": "Cash-flow opérationnel", "nombre_actions": "Nombre d'actions",
    "dettes_totales": "Dettes totales", "dette_court_terme": "Dette court terme", "tresorerie": "Trésorerie",
    "capex": "Capex", "resultat_avant_impot": "Résultat avant impôt",
}


# --------------------------------------------------------------------------- format
def nb(x, dec=0):
    if x is None:
        return "—"
    s = f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s


def pct(x, dec=1):
    return "—" if x is None else f"{x * 100:.{dec}f} %".replace(".", ",")


def ic(statut):
    return ICONE.get(statut, statut or "—")


# --------------------------------------------------------------------------- chargement
def charger():
    synth = json.load(open(DOSSIER_SORTIE / "synthese.json", encoding="utf-8"))
    societes = [json.load(open(DOSSIER_SORTIE / f"{s['cle']}.json", encoding="utf-8")) for s in synth["societes"]]
    journal = json.load(open(DOSSIER_SORTIE / "journal.json", encoding="utf-8"))
    return synth, societes, journal


def resultat_tests() -> str:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", str(RACINE / "tests")],
                       capture_output=True, text=True, cwd=RACINE)
    return (r.stdout.strip().splitlines() or ["(aucune sortie)"])[-1]


# --------------------------------------------------------------------------- sections
def section_panel(societes) -> list[str]:
    L = ["## 0. Panel et identification", "",
         "| Société | ISIN actuel | LEI (source) | Autres ISIN rattachés | Marché | Fondamentaux | "
         "Exercices disponibles | Référentiel comptable |",
         "|---|---|---|---|---|---|---|---|"]
    for r in societes:
        s, idt = r["societe"], r["identite"]
        autres = [f"{i['isin']} ({i['statut']})" for i in idt["isins"][1:] if i["statut"] != "gleif_non_verifie"]
        n_gleif = sum(i["statut"] == "gleif_non_verifie" for i in idt["isins"])
        if n_gleif:
            autres.append(f"+ {n_gleif} ISIN GLEIF non vérifiés (obligations…)")
        src_lei = "manuel" if (idt["source_lei"] or "").startswith("manuel") else (idt["source_lei"] or "—")
        ex = r["exercices"]
        ref = "IFRS (ESEF)" if r["source_fondamentaux"] == "ESEF" else "yfinance (référentiel non garanti)"
        L.append(f"| {s['nom']} | {s['isin']} | {idt['lei'] or '**introuvable**'} ({src_lei}) | "
                 f"{'<br>'.join(autres) or '—'} | {s['marche']} | {r['statut_esef']}"
                 f"{' — **repli yfinance, historique court**' if r['source_fondamentaux'] == 'yfinance' else ''}"
                 f"{' — **données en retard**' if 'données en retard' in r['badges'] else ''} | "
                 f"**{r['nb_exercices']}** (FY{ex[0][:4]}→FY{ex[-1][:4]}) | {ref} |")
    L += ["", "Mycronic : l'ISIN SE0000375115 de mon plan n'est plus l'ISIN de l'action. Vérification : "
          "l'API Nasdaq Nordic (`api.nasdaq.com/api/nordic/search`) renvoie pour « Mycronic » le seul "
          "instrument du groupe *Shares Main Market* : **SE0025158629** (symbole MYCR, orderbookId TX310) ; "
          "SE0000375115 et SE0002135970 y sont inconnus (`NO_INST_FOUND`). Le LEI de GLEIF "
          "(549300S5CCFESE4C6Y07) est bien celui des déclarations FI que tu cites. Les deux ISIN sont "
          "consignés dans `data/manual/isin_lei.csv` avec leur statut et leur source. yfinance enregistre "
          "un split ×2 le 2025-06-03, ce qui est cohérent avec un changement d'ISIN en 2025 (non confirmé par "
          "une source officielle).", "",
          "**Référentiel comptable (item 24)** : les données ESEF sont TOUJOURS en IFRS (obligation "
          "réglementaire européenne, aucune vérification par société nécessaire). Le repli yfinance ne "
          "garantit pas le même référentiel : **ASML**, double coté (Euronext Amsterdam + Nasdaq), publie "
          "aussi un Form 20-F réconcilié en US GAAP pour la SEC. Source : [communiqué ASML, résultats T4 et "
          "année 2025, 28/01/2026](https://www.asml.com/en/news/press-releases/2026/q4-2025-financial-results). "
          "FY2025 : résultat net IFRS 10 213,0 M€ (retenu par le pipeline, source ESEF) contre résultat net "
          "US GAAP **9 609,4 M€** ; BNPA de base IFRS 26,29 € (retenu) contre BNPA de base US GAAP **24,73 €** "
          "— écart ≈ 6 %, confirmé par ASML. Le pipeline utilise EXCLUSIVEMENT l'IFRS via ESEF pour ASML (pas "
          "de repli yfinance nécessaire, 5 rapports ESEF disponibles) : aucun mélange de référentiels dans "
          "les calculs. Le risque ne concerne que les sociétés en repli yfinance total (SAP, Sidetrade) ou "
          "partiel (données en retard) si leur filiale de cotation américaine influençait les données "
          "yfinance — non observé dans ce panel (yfinance suit la cotation primaire européenne pour ces "
          "titres).", ""]
    return L


def section_a(societes, cfg) -> list[str]:
    L = ["## a) Les 10 sociétés : porte, score QVM, timing", "",
         "Légende : ✅ validé · ❌ échec · ⚪ n.é. = non évaluable (historique insuffisant ou donnée "
         "indisponible : jamais ✅, plafonne le verdict à SURVEILLANCE).", "",
         "### a.1 Porte, critère par critère (règle stricte : 6 exercices minimum)", "",
         "| Société | Ex. | P1 CA | P2 Marges | P3 BNPA | P4 F-score | P5 Z'' | P6 Liquidité | **Porte** | Porte avec 5 ex. | Porte mode relatif |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in societes:
        c = r["criteres"]
        p1, p2, p3, p4, p5, p6 = (c[k] for k in ("P1", "P2", "P3", "P4", "P5", "P6"))
        f4 = f"{p4.get('score')}/{p4.get('tests_disponibles')}" if p4.get("score") is not None else "—"
        p2_fiab = f" *{p2['fiabilite']['statut']}*" if p2.get("fiabilite") else ""
        if p3.get("valeur") is not None:
            p3_txt = pct(p3["valeur"])
        elif p3.get("valeur_indicative") is not None:
            p3_txt = f"indicatif {pct(p3['valeur_indicative'])}"
        else:
            p3_txt = "non calc."
        L.append(
            f"| {r['societe']['nom']} | {r['nb_exercices']} "
            f"| {ic(p1['statut'])} {pct(p1.get('valeur'))} "
            f"| {ic(p2['statut_strict'])}{p2_fiab} EBIT {pct(p2.get('marge_ebit'))} · net {pct(p2.get('marge_nette'))} "
            f"| {ic(p3['statut'])} {p3_txt} "
            f"| {ic(p4['statut'])} {f4} "
            f"| {ic(p5['statut'])} {nb(p5.get('valeur'), 2)} "
            f"| {ic(p6['statut'])} {nb((p6.get('valeur') or 0) / 1e6, 2) if p6.get('valeur') else '—'} M€ "
            f"| **{ic(r['porte'])}** | {ic(r['porte_5_exercices'])} | {ic(r['porte_relatif'])} |")
    L += ["", "Seuils : P1 CAGR ≥ 10 % et ≤ 1 année en baisse ; P2 marge EBIT > 20 %, marge nette > 10 %, "
          "pente ≥ −0,5 pt/an ; P3 CAGR BNPA ≥ 10 % ; P4 F-score ≥ 6 (x/y = points / tests disponibles) ; "
          "P5 Z'' > 1,1 ; P6 volume moyen 3 mois > 100 000 €.", "",
          "*non recoupé* (P2, règle ajoutée) : dernier exercice 100 % yfinance, aucun rapport ESEF pour recouper "
          "→ statut ramené à non évaluable, verdict plafonné à SURVEILLANCE. *dépend d'une donnée non recoupée* "
          "(P2 et P4) : écart EBIT yfinance/ESEF > 5 % sur l'exercice commun (P2) ou F-score divergent (P4) ET "
          "la conclusion change selon la donnée retenue (recalculée sur les seules années ESEF, plus anciennes) "
          "→ non évaluable. Ce libellé remplace « non fiable » (item 32) : le calcul sur années ESEF plus "
          "anciennes ne PROUVE pas que la donnée yfinance est fausse, il montre seulement que la conclusion en "
          "dépend. Si la conclusion ne change pas (ex. Boliden P2, Atlas Copco P4), le statut calculé sur les "
          "données ESEF est gardé SANS plafonnement (détail en c.1).", "",
          "Mode relatif de P2 (3e quartile de la marge EBIT) : calculé sur le panel de 10 sociétés, "
          "**non significatif** ici.", "",
          "### a.2 Détail des croissances (P1, P3) : année de base et pente de régression", "",
          "| Société | P1 : CAGR (libellé réel) | Base | Pente log-linéaire | Années en baisse | P3 : CAGR BNPA | Base | Pente log-linéaire | Si 5 exercices acceptés |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in societes:
        p1, p3 = r["criteres"]["P1"], r["criteres"]["P3"]
        alt = r["alternatif_5_exercices"]

        def base(p):
            if p.get("annee_base") is None:
                return "—"
            return f"FY{p['annee_base']}" + (f" ⚠️ {p['note_base']}" if p.get("note_base") else "")

        def val(p):
            if p.get("valeur") is None:
                if p.get("valeur_indicative") is not None:
                    return f"non évaluable — {p['raison']} ({p['libelle_indicatif']} : {pct(p['valeur_indicative'])})"
                return f"non calculable ({p.get('raison_non_calculable') or p.get('raison')})"
            return f"{pct(p['valeur'])} — {p['libelle']}"
        L.append(f"| {r['societe']['nom']} | {ic(p1['statut'])} {val(p1)} | {base(p1)} | {pct(p1.get('pente_log'))} "
                 f"| {p1.get('annees_en_baisse', '—')} | {ic(p3['statut'])} {val(p3)} | {base(p3)} "
                 f"| {pct(p3.get('pente_log'))} | P1 {ic(alt['P1']['statut'])} · P3 {ic(alt['P3']['statut'])} |")
    L += ["", "### a.3 Score QVM (mention obligatoire : **non significatif**), timing et verdict", "",
          "Percentiles calculés sur 10 sociétés seulement (aucun secteur n'atteint 10 sociétés → univers entier). "
          "Ces scores servent à vérifier la mécanique de calcul, **pas à classer**.", "",
          f"Règle ajoutée : univers ({len(societes)} sociétés) < `qvm.min_univers_verdict` "
          f"({cfg['qvm']['min_univers_verdict']}) → tout ACHAT ou REJET **déterminé par le score** devient "
          "**PROVISOIRE** (le verdict qu'il serait est indiqué entre parenthèses). Un REJET dû à la porte ❌ "
          "n'est jamais concerné.", "",
          "| Société | Score QVM | Qualité | Valeur | Momentum | Timing | Verdict | Justification (3 points) |",
          "|---|---|---|---|---|---|---|---|"]
    for r in societes:
        q, t = r["qvm"], r["timing"]
        ss = q["sous_scores"]
        tim = f"{TIMING.get(t['signal'])} " + (f"RSI {nb(t.get('rsi'), 1)}, cours/MM200 {pct(t['cours'] / t['mm200'] - 1) if t.get('mm200') else '—'}"
                                                 if t.get("rsi") is not None else "; ".join(t.get("raisons", [])))
        badge_v = f" ⚠️ *{r['verdict']['badge']}*" if r["verdict"].get("badge") else ""
        L.append(f"| {r['societe']['nom']} | {nb(q['score'])} *(non significatif)*{' · partiel' if q['partiel'] else ''} "
                 f"| {nb(ss['qualite'])} | {nb(ss['valeur'])} | {nb(ss['momentum'])} | {tim} "
                 f"| **{r['verdict']['verdict']}**{badge_v} ({r['verdict']['raison']}) | {'<br>'.join(r['justification'])} |")
    L += ["", "### a.4 Valorisation (devise de cotation = devise des comptes pour tout le panel)", "",
          "| Société | Cours (date) | PER sur dernier exercice publié | Médiane PER 5 ans (PER positifs) | BNPA 12 mois yfinance (indicatif) | Métriques QVM manquantes |",
          "|---|---|---|---|---|---|"]
    for r in societes:
        v = r["valorisation"]
        manq = [f"{k} ({m.get('detail') or 'indisponible'})" for k, m in r["metriques"].items() if m.get("valeur") is None]
        per = v.get("per_actuel")
        ttm, dern = v.get("bnpa_12m_yfinance_indicatif"), v.get("bnpa_dernier_exercice")
        ttm_txt = nb(ttm, 2)
        if ttm is not None and dern and dern > 0 and ttm > 0 and not 0.1 < ttm / dern < 10:
            ttm_txt += " ⚠️ incohérent avec le BNPA publié (donnée yfinance aberrante, ignorée)"
        L.append(f"| {r['societe']['nom']} | {nb(v.get('cours'), 2)} {r['devise_cotation']} ({v.get('date_cours')}) "
                 f"| {nb(per, 1) if per and per > 0 else ('négatif : exclu' if per else '—')} "
                 f"({v.get('per_actuel_libelle', '—')}) | {nb(v.get('per_mediane_5ans'), 1)} "
                 f"| {ttm_txt} | {'<br>'.join(manq) or '—'} |")
    return L


def _serie_val(r, poste, annee):
    for d, v in r["series"].get(poste, {}).items():
        if d.startswith(str(annee)):
            return v
    return None


def section_b(societes) -> list[str]:
    verif = charger_yaml(DOSSIER_MANUEL / "verification_etape1.yaml")["societes"]
    coefs = config()["porte"]["p5_zscore"]["coefficients"]
    L = ["## b) Vérification manuelle : Hermès et ASML", "",
         "Méthode : chaque poste a été relevé **à la main** dans le tableau du rapport annuel publié "
         "(PDF officiel, page indiquée), puis comparé au fait XBRL retenu automatiquement par le pipeline. "
         "Les calculs ci-dessous sont refaits à partir des **valeurs publiées**. Les mêmes valeurs figurent "
         "dans `tests/test_fscore.py` et `tests/test_zscore.py`. "
         "Source des relevés : `data/manual/verification_etape1.yaml`.", ""]
    par_lei = {r["cle"]: r for r in societes}
    for lei, v in verif.items():
        r = par_lei[lei]
        N, N1 = v["exercices"]["N"], v["exercices"]["N-1"]
        L += [f"### {v['nom']}", "",
              f"Document publié : [{v['document']}]({v['url']}). Montants en {v['unite']} sauf mention.", "",
              "| Poste | Exercice | Valeur publiée | Tableau, ligne (page imprimée / page PDF) | Valeur XBRL retenue | Concept IFRS | Rapport ESEF | Écart |",
              "|---|---|---|---|---|---|---|---|"]
        publie = {}
        for poste, x in v["valeurs"].items():
            mult = x.get("multiplicateur", v["multiplicateur"])
            for cle, an in (("N", N), ("N-1", N1)):
                pub = x[cle]
                publie.setdefault(an, {})[poste] = pub
                s = _serie_val(r, poste, an) or {}
                auto = s.get("valeur")
                ecart = "—" if auto is None else ("0" if abs(auto - pub * mult) < 0.5 * mult / 10 else nb(auto / mult - pub, 1))
                lien = f"[{s.get('rapport')}]({s.get('lien')})" if s.get("lien") else (s.get("rapport") or "—")
                fid = s.get("fact_id")
                fid = ", ".join(fid) if isinstance(fid, list) else fid
                dec = 2 if poste == "bnpa" or mult == 1_000_000 and isinstance(pub, float) else 0
                L.append(f"| {LIBELLES_POSTES[poste]} | FY{an} | {nb(pub, dec if poste != 'nombre_actions' else (1 if mult > 1 else 0))} "
                         f"| {x['tableau']}, « {x['ligne']} » (p. {x['page']} / PDF {x['page_pdf']}) "
                         f"| {nb(auto / mult if auto is not None else None, 2 if poste == 'bnpa' else 1)} "
                         f"| `{s.get('concept', '—')}`{f' (fait {fid})' if fid else ''} | {lien} | {ecart} |")
        L += [""] + [f"- {n}" for n in v.get("notes", [])] + [""]

        # ---- F-score ligne par ligne sur valeurs publiées
        def dic(an):
            d = dict(publie[an])
            d["concept_actions"] = "publié"
            return d
        f = P.fscore(dic(N), dic(N1))
        pn, pn1 = publie[N], publie[N1]
        lignes = {
            "F1": f"ROA {N} = {nb(pn['resultat_net'], 1)} / {nb(pn['actif_total'], 1)}",
            "F2": f"CFO {N} = {nb(pn['cash_flow_operationnel'], 1)}",
            "F3": f"ROA {N} (F1) vs ROA {N1} = {nb(pn1['resultat_net'], 1)} / {nb(pn1['actif_total'], 1)}",
            "F4": f"CFO {nb(pn['cash_flow_operationnel'], 1)} vs résultat net {nb(pn['resultat_net'], 1)}",
            "F5": f"{nb(pn['dette_long_terme'], 1)} / {nb(pn['actif_total'], 1)} vs {nb(pn1['dette_long_terme'], 1)} / {nb(pn1['actif_total'], 1)}",
            "F6": f"{nb(pn['actif_courant'], 1)} / {nb(pn['dettes_courantes'], 1)} vs {nb(pn1['actif_courant'], 1)} / {nb(pn1['dettes_courantes'], 1)}",
            "F7": f"actions {nb(pn['nombre_actions'], 1)} vs {nb(pn1['nombre_actions'], 1)}",
            "F8": f"{nb(pn['marge_brute'], 1)} / {nb(pn['chiffre_affaires'], 1)} vs {nb(pn1['marge_brute'], 1)} / {nb(pn1['chiffre_affaires'], 1)}",
            "F9": f"{nb(pn['chiffre_affaires'], 1)} / {nb(pn['actif_total'], 1)} vs {nb(pn1['chiffre_affaires'], 1)} / {nb(pn1['actif_total'], 1)}",
        }
        L += [f"**F-score (FY{N} vs FY{N1}), calcul ligne par ligne sur les valeurs publiées — "
              "actif de CLÔTURE, affichage indicatif seulement (voir ci-dessous pour le calcul de référence)**",
              "", "| Test | Calcul (actif de clôture) | Valeur N | Valeur N−1 | Point |", "|---|---|---|---|---|"]
        for t in f["tests"]:
            vn = t["valeur_n"]
            vn1 = t["valeur_n1"]
            fmt = (lambda x: nb(x, 4)) if t["code"] not in ("F2", "F7") else (lambda x: nb(x, 1))
            L.append(f"| {t['code']} {t['test']} | {lignes[t['code']]} | {fmt(vn) if vn is not None else '—'} "
                     f"| {fmt(vn1) if vn1 is not None else '—'} | **{t['point']}** |")
        clot_tests = {t["code"]: t for t in f["tests"]}
        L += ["", f"Total à la main, actif de clôture (indicatif) : **{f['score']}/9**.", ""]

        # ---- F-score de référence : actif D'OUVERTURE (Piotroski original), règle ajoutée
        mult = v["multiplicateur"]
        at_n2_s = _serie_val(r, "actif_total", N - 2)
        at_n2 = at_n2_s["valeur"] / mult if at_n2_s and at_n2_s.get("valeur") is not None else None
        ato_n = pn1["actif_total"]           # ATO N = actif à l'ouverture de N = actif de clôture de N−1
        L += ["**F-score de RÉFÉRENCE (règle ajoutée, remplace la clôture ci-dessus comme calcul "
              "principal de P4) : actif D'OUVERTURE, convention Piotroski originale**", "",
              f"ATO {N} (actif total à l'ouverture de FY{N}, = actif de clôture FY{N1}) = "
              f"{nb(ato_n, 1)} — déjà relevé à la main ci-dessus. ATO {N1} (actif total à "
              f"l'ouverture de FY{N1}, = actif de clôture FY{N - 2}) = {nb(at_n2, 1)} : non relevé "
              "à la main pour ce complément, source pipeline/ESEF (déjà recoupé pour FY"
              f"{N} et FY{N1} ci-dessus).", ""]
        f_ouv = P.fscore_convention(dic(N), dic(N1), at_n2)
        if at_n2 is None:
            L.append(f"ATO {N1} indisponible (historique insuffisant) : F1/F3/F5/F9 non évaluables en "
                     "convention d'ouverture (pas de repli silencieux sur la clôture).")
        else:
            ov = {t["code"]: t for t in f_ouv["tests"]}
            L += ["| Test | Actifs utilisés (ATO N / ATO N−1) | Valeur N | Valeur N−1 | Point | "
                  "Point clôture (indicatif) | Change ? |", "|---|---|---|---|---|---|---|"]
            for code in ("F1", "F3", "F5", "F9"):
                o, cl = ov[code], clot_tests[code]
                change = "**oui**" if o["point"] != cl["point"] else "non"
                L.append(f"| {code} {o['test']} | {nb(ato_n, 1)} / {nb(at_n2, 1)} | {nb(o['valeur_n'], 4)} "
                         f"| {nb(o.get('valeur_n1'), 4) if o.get('valeur_n1') is not None else '—'} "
                         f"| **{o['point']}** | {cl['point']} | {change} |")
        auto_f = r["criteres"]["P4"]
        L += ["", f"**Score de référence (actif d'ouverture) : {f_ouv['score']}/{f_ouv['tests_disponibles']}** "
                  f"contre {f['score']}/9 en clôture (indicatif). Pipeline (valeurs XBRL, même convention) : "
                  f"**{auto_f['score']}/{auto_f['tests_disponibles']}** → "
                  f"{'identique ✅' if auto_f['score'] == f_ouv['score'] and auto_f['tests_disponibles'] == f_ouv['tests_disponibles'] else 'DIFFÉRENT ❌'}. "
                  f"Seuil P4 : ≥ 6 → {ic(P.p4_fscore(f_ouv, config())['statut'])}.", ""]

        # ---- Z'' ligne par ligne
        dtot = pn["actif_total"] - pn["capitaux_propres"]
        z = P.zscore(pn["actif_courant"], pn["dettes_courantes"], pn["reserves"], pn["ebit"],
                     pn["actif_total"], pn["capitaux_propres"], dtot, coefs)
        L += [f"**Z''-score (FY{N}), calcul ligne par ligne sur les valeurs publiées**", "",
              f"- X1 = BFR / actif total = ({nb(pn['actif_courant'], 1)} − {nb(pn['dettes_courantes'], 1)}) / {nb(pn['actif_total'], 1)} = **{nb(z['x1'], 6)}**",
              f"- X2 = réserves / actif total = {nb(pn['reserves'], 1)} / {nb(pn['actif_total'], 1)} = **{nb(z['x2'], 6)}**",
              f"- X3 = EBIT / actif total = {nb(pn['ebit'], 1)} / {nb(pn['actif_total'], 1)} = **{nb(z['x3'], 6)}**",
              f"- X4 = capitaux propres / dettes totales = {nb(pn['capitaux_propres'], 1)} / ({nb(pn['actif_total'], 1)} − {nb(pn['capitaux_propres'], 1)} = {nb(dtot, 1)}) = **{nb(z['x4'], 6)}**",
              f"- Z'' = 6,56 × {nb(z['x1'], 6)} + 3,26 × {nb(z['x2'], 6)} + 6,72 × {nb(z['x3'], 6)} + 1,05 × {nb(z['x4'], 6)}",
              f"  = {nb(6.56 * z['x1'], 6)} + {nb(3.26 * z['x2'], 6)} + {nb(6.72 * z['x3'], 6)} + {nb(1.05 * z['x4'], 6)} = **{nb(z['valeur'], 4)}**",
              f"- Pipeline (valeurs XBRL) : **{nb(r['criteres']['P5']['valeur'], 4)}** → "
              f"{'identique ✅' if abs(r['criteres']['P5']['valeur'] - z['valeur']) < 1e-3 else 'DIFFÉRENT ❌'} ; "
              f"zone **{P.p5_zscore(z, config())['zone']}** (> 2,6).", ""]

        # ---- F5 avec/sans dettes locatives IFRS 16 (règle ajoutée)
        loc_n_s, loc_n1_s = _serie_val(r, "dette_location_ifrs16", N), _serie_val(r, "dette_location_ifrs16", N1)
        L += ["**F5 avec / sans dettes locatives IFRS 16 dans la dette long terme**", ""]
        if loc_n_s is None or loc_n1_s is None:
            L.append(f"Aucun concept IFRS séparé pour les dettes locatives non courantes n'est balisé par "
                     f"{v['nom']} (`ifrs-full:NoncurrentLeaseLiabilities` absent) : comparaison impossible, "
                     "hors risque pour ce calcul.")
        else:
            loc_n, loc_n1 = loc_n_s["valeur"] / mult, loc_n1_s["valeur"] / mult
            dlt_n_avec, dlt_n1_avec = pn["dette_long_terme"] + loc_n, pn1["dette_long_terme"] + loc_n1
            lev_hors_n, lev_hors_n1 = pn["dette_long_terme"] / pn["actif_total"], pn1["dette_long_terme"] / pn1["actif_total"]
            lev_avec_n, lev_avec_n1 = dlt_n_avec / pn["actif_total"], dlt_n1_avec / pn1["actif_total"]
            f5_hors, f5_avec = int(lev_hors_n < lev_hors_n1), int(lev_avec_n < lev_avec_n1)
            L += [f"Dettes locatives non courantes (`ifrs-full:NoncurrentLeaseLiabilities`, source pipeline/ESEF) "
                  f": FY{N} {nb(loc_n, 1)}, FY{N1} {nb(loc_n1, 1)}.", "",
                  "| | Dette LT retenue | Dette LT + IFRS16 |", "|---|---|---|",
                  f"| FY{N} | {nb(pn['dette_long_terme'], 1)} → levier {nb(lev_hors_n, 4)} "
                  f"| {nb(dlt_n_avec, 1)} → levier {nb(lev_avec_n, 4)} |",
                  f"| FY{N1} | {nb(pn1['dette_long_terme'], 1)} → levier {nb(lev_hors_n1, 4)} "
                  f"| {nb(dlt_n1_avec, 1)} → levier {nb(lev_avec_n1, 4)} |",
                  f"| **F5** (levier en baisse ?) | **{f5_hors}** (retenu par le pipeline) | **{f5_avec}** |", ""]
            if f5_hors != f5_avec:
                L.append(f"**Le point F5 change** selon que les dettes locatives IFRS 16 sont incluses ou non : "
                         "hors dettes locatives (choix retenu, hypothèse #7), le levier baisse → F5 = "
                         f"{f5_hors} ; avec, le levier {'baisse' if f5_avec else 'augmente'} → F5 = {f5_avec}.")
            else:
                L.append("Le point F5 ne change pas selon les deux conventions pour cette société.")
            L.append("")
    L += ["**Choix retenu (documenté dans les hypothèses, c.3)** : `dette_long_terme` EXCLUT les dettes "
          "locatives IFRS 16 (hypothèse #7 déjà en place). Le tableau ci-dessus montre que ce choix n'est "
          "pas neutre pour Hermès (F5 change) : c'est une raison supplémentaire de le documenter explicitement "
          "plutôt que de le laisser implicite. ASML ne permet pas la comparaison (donnée non balisée séparément).", ""]

    # ---- Distorsion fiscale connue (règle ajoutée) : contribution exceptionnelle France 2025
    L += ["## b.1) Distorsion connue du résultat net 2025 des grandes entreprises françaises", "",
          "Source : [communiqué Hermès International, 12/02/2026](https://finance.hermes.com) — la "
          "« contribution exceptionnelle sur les bénéfices des grandes entreprises » (loi de finances 2025, "
          "France) est une surtaxe temporaire sur l'impôt sur les sociétés qui pèse sur le résultat net 2025 "
          "des grandes sociétés françaises. Résultat net part du groupe *ajusté* (hors contribution "
          "exceptionnelle) communiqué par Hermès : **4,86 Md€ (+5,5 %)**, contre **4 524 M€** *publié* "
          "(celui retenu par le pipeline, `ifrs-full:ProfitLossAttributableToOwnersOfParent`) — écart ≈ 336 M€. "
          "Le pipeline utilise le résultat PUBLIÉ (aucune correction), ce qui est cohérent avec la règle "
          "« donnée manquante = null, jamais d'estimation silencieuse » — mais cela biaise à la baisse le "
          "résultat net 2025 (et donc le F-score, le ROA, le PER) de toutes les grandes sociétés françaises "
          "assujetties, pas seulement Hermès. Aucune correction automatique n'est appliquée : si un ajustement "
          "est souhaité, il doit passer par `data/manual/{isin}.yaml` (mécanisme déjà prévu, prime sur les "
          "données automatiques), poste par poste, avec sa source vérifiée.", ""]
    return L


def _detail_p4_mycronic(r, p4) -> list[str]:
    """Item 21 : détail des 9 tests F-score de Mycronic, un par un (valeur, source ESEF/yfinance,
    split appliqué), et identification de ceux qui dépendent de l'exercice yfinance."""
    dfa, dff = p4["detail_avec_yfinance"], p4["detail_fiable"]
    n_annee, n1_annee = dfa["exercices"][1][:4], dfa["exercices"][0][:4]
    postes_test = {
        "F1": ["resultat_net"], "F2": ["cash_flow_operationnel"], "F3": ["resultat_net"],
        "F4": ["cash_flow_operationnel", "resultat_net"], "F5": ["dette_long_terme", "actif_total"],
        "F6": ["actif_courant", "dettes_courantes"], "F7": ["nombre_actions"],
        "F8": ["marge_brute", "chiffre_affaires"], "F9": ["chiffre_affaires"],
    }

    def source(poste, annee):
        v = r["series"].get(poste, {}).get(f"{annee}-12-31")
        if v is None:
            return "—"
        s = v.get("source", "—")
        split = "; split appliqué" if any("split" in b for b in v.get("badges", [])) else ""
        return f"{s}{split}"

    L = [f"**Mycronic — détail des 9 tests F-score côte à côte, exercice FY{n_annee} (yfinance) vs "
         f"FY{n1_annee} (ESEF), convention {dfa['convention']}** (item 33)", "",
         "| Test | Poste(s) | Valeur FY" + n_annee + " | Valeur FY" + n1_annee + " | Point | "
         "Source FY" + n_annee + " | Source FY" + n1_annee + " | Dépend d'une donnée non recoupée ? |",
         "|---|---|---|---|---|---|---|---|"]
    for t in dfa["tests"]:
        postes = postes_test[t["code"]]
        src_n = "; ".join(source(p, n_annee) for p in postes)
        src_n1 = "; ".join(source(p, n1_annee) for p in postes)
        depend = "oui" if "yfinance" in src_n else ("non concerné" if t["point"] is None else "non")
        vn = nb(t["valeur_n"], 4) if t.get("valeur_n") is not None else "—"
        vn1 = nb(t.get("valeur_n1"), 4) if t.get("valeur_n1") is not None else "—"
        L.append(f"| {t['code']} {t['test']} | {', '.join(postes)} | {vn} | {vn1} | {t['point']} "
                 f"| {src_n} | {src_n1} | {depend} |")
    n_yfinance = sum(1 for t in dfa["tests"] if t["point"] is not None
                     and "yfinance" in "; ".join(source(p, n_annee) for p in postes_test[t["code"]]))
    marges_ebit = r["criteres"]["P2"].get("marges_ebit", {})
    m_n, m_n1 = marges_ebit.get(n_annee), marges_ebit.get(n1_annee)
    retard = r.get("retard") or {}
    ebit_ecart_commun = next((c for c in retard.get("comparaison_exercice_commun", [])
                              if c["poste"] == "ebit"), None)
    if m_n is not None and m_n1 is not None:
        L += ["", f"**Contexte marge EBIT (hors F-score, pour juger réel vs définition)** : "
                  f"FY{n1_annee} (ESEF) {pct(m_n1)} → FY{n_annee} (yfinance) {pct(m_n)}. "
                  + (f"Sur l'exercice commun FY{n1_annee}, l'EBIT yfinance ne s'écartait que de "
                     f"{pct(ebit_ecart_commun['ecart'])} de l'ESEF (contrôle « données en retard », c.1) : "
                     "les définitions concordent pour cette société (à la différence de Boliden, écart "
                     "-26 %) — **la baisse de marge FY" + n_annee + " est donc probablement une évolution "
                     "réelle de l'activité, pas un artefact de définition**, sans que cela ne change le "
                     "statut « dépend d'une donnée non recoupée » du F-score (la fiabilité de la DÉFINITION "
                     "n'est pas la même chose que la fiabilité de la VALEUR exacte d'un exercice non encore "
                     "confirmé par un rapport ESEF)." if ebit_ecart_commun and ebit_ecart_commun.get("ecart") is not None
                     else "Aucun contrôle de définition disponible pour comparer."), ""]
    L += ["", f"Sur les {dfa['tests_disponibles']} tests disponibles avec l'exercice yfinance, **{n_yfinance} "
              f"dépendent de FY{n_annee} (yfinance)** — c'est-à-dire TOUS (FY{n_annee} est 100 % yfinance pour "
              f"Mycronic, aucun poste ESEF cette année-là : tout test utilisant l'exercice N en dépend). F5 et "
              "F7 sont indisponibles pour des raisons de données ESEF antérieures (dette long terme et nombre "
              "d'actions non balisés sur plusieurs exercices), sans rapport avec yfinance.",
         f"Sur les seules années ESEF (FY{dff['exercices'][1][:4]} vs FY{dff['exercices'][0][:4]}) : "
         f"**{dff['score']}/{dff['tests_disponibles']}**, statut {ic(dff['statut'])} — très différent du "
         f"{dfa['score']}/{dfa['tests_disponibles']} avec l'exercice yfinance : la conclusion dépend d'une "
         "donnée non recoupée (yfinance FY" + n_annee + "). Le calcul ESEF seul porte sur un exercice PLUS "
         "ANCIEN (FY" + dff['exercices'][1][:4] + ") : il ne prouve pas que la donnée yfinance FY" + n_annee +
         " est fausse, seulement que la conclusion en dépend (item 32).", ""]
    return L


def section_c(societes, journal, cfg) -> list[str]:
    L = ["## c) Données introuvables, anomalies de source et hypothèses", "",
         "### c.1 Par société", ""]
    for r in societes:
        L.append(f"#### {r['societe']['nom']}")
        L.append(f"- Fondamentaux : {r['statut_esef']} ; source retenue : **{r['source_fondamentaux']}**"
                 f" ; {r['nb_exercices']} exercices ({', '.join(e[:4] for e in r['exercices'])}).")
        for e in r["rapports_ecartes"]:
            L.append(f"- Rapport écarté `{e['fxo_id']}` : {e['motif']}.")
        for e in r["rapports_esef"]:
            if e.get("explication_override"):
                L.append(f"- Rapport `{e['fxo_id']}` réintégré (métadonnée d'index corrigée) : {e['explication_override']}")
        for i in r.get("incoherences_rapports", []):
            L.append(f"- **Erreur de balisage de l'émetteur** : `{i['fxo_id']}` donne pour {i['poste']} FY{i['exercice'][:4]} "
                     f"{nb(i['valeur_comparatif'])} contre {nb(i['valeur_rapport_precedent'])} dans `{i['rapport_precedent']}` "
                     "→ rapport exclu, exercice remplacé par yfinance (badge).")
        if r.get("retard"):
            rt = r["retard"]
            L.append(f"- **Données en retard** : dernier ESEF exploitable FY{rt['derniere_esef'][:4]}, attendu "
                     f"FY{rt['cloture_attendue'][:4]} (délai légal de 4 mois dépassé). Exercice(s) ajouté(s) depuis yfinance : "
                     f"{', '.join(rt['exercices_ajoutes_yfinance']) or 'aucun'}.")
            tol = cfg["sources"]["tolerance_ecart_relatif"]
            comp = "; ".join(f"{LIBELLES_POSTES.get(c['poste'], c['poste'])} ESEF {nb(c['esef'], 2 if c['poste'] == 'bnpa' else 0)}"
                             f" / yfinance {nb(c['yfinance'], 2 if c['poste'] == 'bnpa' else 0)}"
                             + (f" ({pct(c['ecart'])}{' ⚠️' if abs(c['ecart']) > tol else ''})" if c['ecart'] is not None else "")
                             for c in rt["comparaison_exercice_commun"])
            L.append(f"  - Contrôle des définitions sur l'exercice commun FY{rt['derniere_esef'][:4]} "
                     f"(yfinance vs ESEF) : {comp}.")
            ecarts = [c for c in rt["comparaison_exercice_commun"] if c["ecart"] is not None and abs(c["ecart"]) > tol]
            if ecarts:
                L.append("  - ⚠️ " + ", ".join(LIBELLES_POSTES.get(c["poste"], c["poste"]) for c in ecarts)
                         + " : définition yfinance différente de l'ESEF → les valeurs FY"
                         + rt["cloture_attendue"][:4] + " de ce poste ne sont pas strictement comparables à l'historique ESEF.")
            L.append(f"  - F-score : compare FY{rt['cloture_attendue'][:4]} (yfinance) à FY{rt['derniere_esef'][:4]} (ESEF) : "
                     "sources mixtes.")
        p2 = r["criteres"]["P2"]
        if p2.get("fiabilite"):
            fiab = p2["fiabilite"]
            L.append(f"- **P2 {fiab['statut']}** (règle ajoutée) : {fiab['raison']} → statut ramené à non évaluable "
                     f"(calculé sur les seules données fiables : {ic(p2.get('donnees_fiables', {}).get('statut_strict', '—'))} ; "
                     f"avec la donnée douteuse : {ic(p2['statut_strict_calcule'])}), verdict plafonné à SURVEILLANCE.")
        elif p2.get("fiabilite_verifiee"):
            fv = p2["fiabilite_verifiee"]
            L.append(f"- **P2, fiabilité vérifiée** (règle ajoutée) : {fv['raison']} statut {ic(p2['statut_strict'])} "
                     "gardé sans plafonnement (recalculé sur les seules données ESEF fiables).")
        p4 = r["criteres"]["P4"]
        if p4.get("fiabilite"):
            fiab = p4["fiabilite"]
            dfa, dff = p4.get("detail_avec_yfinance", {}), p4.get("detail_fiable", {})
            L.append(f"- **P4 {fiab['statut']}** (règle ajoutée) : {fiab['raison']} → statut ramené à non "
                     f"évaluable (avec l'exercice yfinance : {ic(p4['statut_calcule'])} "
                     f"{dfa.get('score')}/{dfa.get('tests_disponibles')} ; sur les seules années ESEF "
                     f"{' → '.join(dff.get('exercices', []))} : {ic(dff.get('statut'))} "
                     f"{dff.get('score')}/{dff.get('tests_disponibles')}), verdict plafonné à SURVEILLANCE.")
        elif p4.get("fiabilite_verifiee"):
            fv = p4["fiabilite_verifiee"]
            L.append(f"- **P4, fiabilité vérifiée** (règle ajoutée) : {fv['raison']} statut {ic(p4['statut'])} "
                     "gardé sans plafonnement (recalculé sur les seules années ESEF).")
        if r["cle"] == "549300S5CCFESE4C6Y07" and p4.get("detail_avec_yfinance"):
            L += _detail_p4_mycronic(r, p4)
        for j in r["splits_journal"]:
            if j.get("type") == "ajustement":
                L.append(f"- BNPA/actions ajustés du split yfinance : {j['poste']} FY{j['cloture'][:4]} "
                         f"{nb(j['valeur_publiee'], 3)} → {nb(j['valeur_ajustee'], 3)} "
                         f"({', '.join(s['date'] + ' ×' + format(s['ratio'], 'g') for s in j['splits_yfinance'])}).")
            elif j["explique"]:
                rapports = f" (rapport d'origine `{j['rapport_origine']}` → comparatif retraitant `{j['rapport_retraitant']}`)" \
                    if j.get("rapport_origine") else ""
                L.append(f"- Retraitement {j['poste']} FY{j['cloture'][:4]} : {nb(j['valeur_origine'], 3)} → "
                         f"{nb(j['valeur_retraitee'], 3)} (facteur {j['facteur_observe']}){rapports} : "
                         "expliqué par un split yfinance.")
            else:
                rapports = f" (rapport d'origine `{j['rapport_origine']}` → comparatif écarté `{j['rapport_retraitant']}`)" \
                    if j.get("rapport_origine") else ""
                yf = (f" Recoupement yfinance : {nb(j['nombre_actions_yfinance_actuel'], 0)} actions actuelles "
                     f"({pct(j['ecart_vs_yfinance_actuel'])} vs valeur conservée) — écart NON expliqué à ce "
                     "stade (actuel, pas historique ; une émission/rachat réel n'est pas exclu, à vérifier)."
                     if j.get("nombre_actions_yfinance_actuel") is not None else "")
                L.append(f"- Retraitement {j['poste']} FY{j['cloture'][:4]} **non expliqué**{rapports} : comparatif "
                         f"{nb(j['valeur_ecartee'], 3)} écarté (facteur observé {j['facteur_observe']}, aucun split "
                         f"yfinance correspondant), valeur d'origine **{nb(j['valeur_retenue'], 3)} conservée**.{yf}")
        ci = r.get("controles_identite", {})
        if ci.get("resume"):
            L.append("- Contrôles d'identité exécutés par exercice (règle ajoutée) : "
                     + "; ".join(f"FY{d[:4]} {s['executes']}/{s['sur']}" for d, s in sorted(ci["resume"].items())))
        for q in ci.get("quarantaine", []):
            L.append(f"- **Contrôle d'identité (règle ajoutée)** : {q['poste_retire']} FY{q['cloture'][:4]} "
                     f"mis en quarantaine ({nb(q['valeur'], 3)} retiré) : {q['motif']}")
        for nc in ci.get("non_concluant", []):
            L.append(f"- **Contrôle d'identité non concluant (règle ajoutée)** : FY{nc['cloture'][:4]} : {nc['motif']}")
        non_controles = [d for d, s in ci.get("resume", {}).items() if s["non_controle"]]
        if non_controles:
            L.append(f"- **Contrôles d'identité : non contrôlé** (0/4 concluant, données insuffisantes) : "
                     + ", ".join(f"FY{d[:4]}" for d in sorted(non_controles)) + ".")
        partiels = [d for d, s in ci.get("resume", {}).items() if s.get("partiel")]
        if partiels:
            seuil_p = cfg["controles_identite"]["seuil_partiel"]
            L.append(f"- **Contrôles d'identité : contrôle partiel** (< {seuil_p}/4 concluant) : "
                     + ", ".join(f"FY{d[:4]} ({ci['resume'][d]['executes']}/4)" for d in sorted(partiels)) + ".")
        if r["donnees_manquantes"]:
            L.append("- Données introuvables (null + badge « indisponible ») : " + "; ".join(
                f"{LIBELLES_POSTES.get(p, p)} ({', '.join('FY' + d[:4] for d in ds)})" for p, ds in r["donnees_manquantes"].items()))
        badges = sorted({b for s in r["series"].values() for v in s.values() for b in v.get("badges", [])
                         if b.startswith(("EBIT reconstitué", "somme partielle", "concept propre", "actif courant calculé",
                                          "dettes courantes calculées"))})
        for b in badges:
            L.append(f"- Badge : {b}.")
        for c in r.get("corrections_manuelles", []):
            L.append(f"- Correction manuelle : {c}.")
        L.append("")
    L += ["### c.2 Sources inaccessibles ou limitées", "",
          "- **Stooq** (secours des cours) : inutilisable en automatique depuis ce Mac, le site exige une "
          "vérification JavaScript anti-robot. Non contournée. yfinance a fourni tous les cours.",
          "- **SAP** (Allemagne) : LEI trouvé, aucun rapport sur filings.xbrl.org → repli yfinance (4 exercices).",
          "- **Sidetrade** (Euronext Growth) : aucun rapport ESEF (pas d'obligation) → repli yfinance (4 exercices).",
          "- **Suède (Atlas Copco, Boliden, Mycronic)** : rapports FY2025 non indexés sur filings.xbrl.org au "
          "2026-09-29 → FY2025 pris dans yfinance (badge « données en retard »).",
          "- **Thermador FY2022** : filings.xbrl.org n'a pas converti le rapport (paquet ZIP seul) ; les chiffres "
          "FY2022 viennent du comparatif du rapport FY2023.",
          "- **Brunello Cucinelli FY2025** : dimensions inversées dans le balisage (totaux balisés « parties liées »), "
          "BNPA balisé 1 986,5 € au lieu d'environ 1,99 € (erreur ×1000) → rapport exclu, FY2025 pris dans yfinance. "
          "**Vérification demandée : le contrôle d'identité (c.1, règle ajoutée) aurait-il détecté cette erreur "
          "SEUL, sans le contrôle de cohérence CA existant ?** Non — vérifié sur le rapport écarté "
          "`5493003CX2RZ0FOBH256-2025-12-31-ESEF-IT-0` : à cause de l'inversion de dimensions, "
          "`marge_brute`, `ebit` et `nombre_actions` n'y sont PAS balisés sans dimension (donc absents, pas "
          "juste faux) — seuls `chiffre_affaires` (188 000, lui aussi faux) et `bnpa` (1 986,5) le sont. Le "
          "contrôle BNPA × actions ≈ résultat net ne peut pas s'exécuter sans `nombre_actions` (non balisé pour "
          "Cucinelli, cf. ci-dessus) ; marge brute ≤ CA et la borne de marge EBIT ne peuvent pas s'exécuter sans "
          "`marge_brute`/`ebit` (absents dans ce rapport). C'est uniquement le contrôle de cohérence CA "
          "PRÉEXISTANT (`rapports_incoherents`, comparatif N−1 entre rapports successifs, seuil 50 %) qui exclut "
          "ce rapport avant que les contrôles d'identité ne voient ses valeurs. Les deux mécanismes sont "
          "complémentaires mais pas redondants ici. Nuance : sur la série RETENUE (rapports 2020-2024, après "
          "exclusion du rapport corrompu), Cucinelli obtient 2/4 contrôles exécutés par exercice (c.1), pas "
          "0/4 — le cas « 0/4, non contrôlé » décrit un exercice hypothétique où même ces 2 contrôles "
          "manqueraient de données, pas la situation réelle de ce panel.",
          "- **Nombre d'actions** : non balisé par Atlas Copco, Brunello Cucinelli, Mycronic (tous exercices ESEF) et "
          "Valneva (2023-2025) → F7 (émission d'actions) indisponible. Pas de dérivation « résultat / BNPA » : "
          "l'arrondi du BNPA à 2 décimales créerait de fausses émissions.",
          "- **Boliden — retraitement « nombre d'actions ÷ 100 sans split »** (poste `nombre_actions`, "
          "exercice FY2021) : le rapport `21380059QU7IM1ONDJ56-2021-12-31-ESEF-SE-0` (déposé 2022-03-22) publie "
          "273 511 169 actions (`ifrs-full:NumberOfSharesOutstanding`) au 31/12/2021 ; le comparatif du même "
          "poste dans le rapport suivant `21380059QU7IM1ONDJ56-2022-12-31-ESEF-SE-0` (déposé 2023-05-09) donne "
          "2 735 111 pour la même date (facteur observé 0,01, exactement ÷ 100). **Hypothèse** : erreur de "
          "balisage dans le comparatif du rapport FY2022 (confusion d'échelle iXBRL probable), pas un évènement "
          "capitalistique réel. Correction appliquée (règle ajoutée, item 15/19) : la valeur D'ORIGINE du "
          "rapport FY2021 (273 511 169) est conservée, le comparatif ÷ 100 est écarté — cette règle ne s'applique "
          "qu'à bnpa/nombre_actions (jamais à CA, EBIT, actifs, voir item 19). Conséquence : le contrôle "
          "d'identité BNPA × actions ≈ résultat net (c.1) ne trouve plus d'écart et ne quarantine plus rien "
          "pour FY2021 (31,81 × 273 511 169 ≈ 8,701 Md SEK ≈ résultat net publié 8,701 Md SEK, écart < 0,01 %).",
          "  - **Vérification demandée (item 20)** — y a-t-il eu une émission d'actions réelle entre FY2021 et "
          "FY2025 ? Historique du nombre d'actions dans les rapports ESEF successifs (`ifrs-full:"
          "NumberOfSharesOutstanding`, exercice propre à chaque rapport, pas les comparatifs suspects) : "
          "FY2021 = 273 511 169 ; FY2022 = 273 511 169 (rapport FY2022, fait « 2023-01-01 », confirmant que "
          "273 511 169 — pas 2 735 111 — est la bonne valeur début 2022) ; FY2023 = 273 503 169 (-8 000) ; "
          "FY2024 = 273 471 169 (-32 000). **Aucune émission dans les rapports ESEF publiés (FY2021-FY2024) : "
          "au contraire, une légère réduction nette (-40 000 actions, -0,015 %), cohérente avec des rachats, "
          "pas des émissions.** Le nombre d'actions yfinance utilisé pour FY2025 (retard ESEF) est en revanche "
          "sensiblement plus élevé : 284 225 454 (yfinance, poste `nombre_actions`, ligne « Share Issued ») et "
          "283 962 452 (`sharesOutstanding` yfinance, utilisé pour le recoupement en c.1) — soit environ "
          "+10,75 M actions (+3,9 %) par rapport à FY2024 ESEF. **Je ne peux pas confirmer si c'est une "
          "émission réelle en 2025 (le rapport ESEF FY2025 n'est pas encore publié) ou un artefact de source "
          "yfinance** : signalé comme tel, badge « écart NON expliqué » (corrigé, la mention précédente "
          "« écart normal » n'était pas vérifiée). Sans lien avec le retraitement ÷ 100 (déjà écarté ci-dessus, "
          "qui concernait le comparatif FY2021 dans le rapport FY2022, pas l'écart FY2024→FY2025). Impact sur "
          "F7 (émission d'actions, P4) : déjà neutralisé par la règle existante « F7 comparé seulement si même "
          "concept » (`ifrs-full:NumberOfSharesOutstanding` ESEF vs `yfinance:Share Issued`, concepts "
          "différents) — F7 est exclu (non disponible), pas faussé.",
          "- **Certificats SSL** : le Python de python.org n'a pas de magasin de certificats (dossier "
          "`etc/openssl` vide). Aucun proxy : la chaîne GlobalSign reçue est authentique. Le pipeline utilise "
          "`certifi` ; `verify=False` n'est jamais utilisé. Correctif système facultatif : lancer "
          "« Install Certificates.command » dans le dossier Python 3.14.", ""]
    L += ["### c.3 Hypothèses prises (absentes de methode.md, à valider)", ""]
    hyp = [
        "Clé interne = LEI ; correspondance ISIN → LEI par `isin_lei.csv` puis GLEIF, jamais par nom.",
        "Exercice d'un rapport ESEF = période annuelle la plus fréquente de ses faits (pas la métadonnée d'index). "
        "Rapport dont l'index diffère des faits : exclu, sauf explication dans `esef_overrides.yaml` (cas Hermès « 2026 » = FY2025).",
        "Doublons : un rapport par exercice ; priorité au pays de dépôt principal, puis au dépôt le plus récent, "
        "puis à la langue (fr, en). Les chiffres clés des doublons sont comparés (tous identiques ici).",
        "Chiffres de chaque exercice : rapport le plus récent qui les contient (comparatif retraité), écart avec "
        "l'original signalé au-delà de 0,5 %.",
        "Contrôle de cohérence : comparatif N−1 du CA ou de l'actif total différent de plus de 50 % du chiffre "
        "publié l'année précédente → rapport exclu (erreur de balisage). Seuil dans config.yaml.",
        "Délai légal de publication de 4 mois (directive Transparence) pour détecter les « données en retard ».",
        "Résultat net = part du groupe ; BNPA = de base ; capex = acquisitions d'immobilisations corporelles + "
        "incorporelles (somme partielle signalée) ; dette LT = emprunts non courants hors dettes locatives IFRS 16 ; "
        "dette CT = emprunts courants hors dettes locatives ; capitaux propres = totaux (minoritaires inclus).",
        "« Réserves » du Z'' = résultats non distribués au sens d'Altman, résultat de l'exercice inclus "
        "(ifrs-full:RetainedEarnings ou composantes équivalentes). Extensions « maison » d'Hermès et de Thermador "
        "utilisées en dernier recours, libellés vérifiés dans leurs rapports.",
        "Dettes totales absentes du balisage = actif total − capitaux propres (identité comptable, badge). "
        "Actif et passif courants absents = total − non courant (badge).",
        "F-score : bilans de clôture N et N−1 (Piotroski utilise l'actif d'ouverture) ; « en baisse / en hausse » "
        "au sens strict ; F7 = nombre d'actions N ≤ N−1, comparé seulement si même concept ; test indisponible "
        "exclu, statut ✅ si score ≥ 6, ❌ si même avec les tests manquants < 6, sinon n.é.",
        "P2 : marge EBIT et marge nette du dernier exercice ; tendance = pente de la marge EBIT (points/an) sur "
        "la fenêtre ; mode relatif = 3e quartile (interpolation linéaire) de la marge EBIT du dernier exercice.",
        "P6 : 3 mois = 63 séances ; montant = volume × clôture × taux BCE du jour (dernier fixing antérieur les "
        "jours sans fixing BCE).",
        "Percentile = (inférieurs + ½ égalités) / (n − 1) × 100 ; sous-score absent → poids renormalisés (badge).",
        "Q2 non interprétable si résultat net ≤ 0 ; Q4 = écart-type (population) des 5 dernières marges EBIT.",
        "V1 : EV = capitalisation + dette LT + dette CT − trésorerie ; capitalisation = cours × actions de clôture "
        "du dernier exercice (yfinance `sharesOutstanding` si absentes, badge).",
        "M1 = clôture il y a 21 séances / clôture il y a 252 séances − 1 ; M2 = rendement 126 séances de "
        "l'action / rendement de l'indice ^STOXX − 1 ; cours hors dividendes (indice de prix).",
        "Timing : RSI de Wilder ; MM200 « en hausse sur 1 mois » = MM200 du jour > MM200 d'il y a 21 séances ; "
        "cours > MM200 sans repli exploitable (RSI < 35 et loin de la MM50) → 🟡.",
        "Justification : critère de porte le plus juste = plus petite marge relative au seuil (un ❌ est prioritaire), "
        "meilleur et pire sous-score.",
        "Secteur = secteur yfinance (classification Morningstar), faute de source sectorielle européenne gratuite.",
        "Verdict PROVISOIRE (règle ajoutée) : univers < `qvm.min_univers_verdict` (30) → un ACHAT ou un REJET "
        "déterminé par le score devient PROVISOIRE (verdict qu'il serait affiché) ; un REJET dû à la porte ❌ "
        "n'est jamais concerné, ni un plafond SURVEILLANCE déjà appliqué (porte non évaluable, score < seuil "
        "d'achat). Seuil arbitraire (aucune référence dans methode.md), à valider.",
        "P4 F-score partiel : affichage « x/y tests évaluables » (x = points obtenus, y = tests disponibles).",
        "P2 fiabilité (règle ajoutée, corrigée) : dernier exercice 100 % yfinance (aucun ESEF) → « non recoupé », "
        "non évaluable (pas de repli fiable possible). Écart EBIT yfinance/ESEF > 5 % sur l'exercice commun (cas "
        "« données en retard ») : P2 est RECALCULÉ sur les seules données ESEF fiables (exercice yfinance "
        "exclu) et comparé au calcul complet ; même conclusion (même statut) → gardée SANS plafonnement (ex. "
        "Boliden, ❌ sur sa marge ESEF FY2024, 15,3 %) ; conclusion différente → « dépend d'une donnée non "
        "recoupée » (renommé depuis « non fiable », item 32 : le calcul ESEF seul porte sur un exercice plus "
        "ancien, il ne prouve pas que yfinance est faux), non évaluable. Seuil de 5 % arbitraire (aucune "
        "référence dans methode.md).",
        "Contrôles d'identité (règle ajoutée, corrigés) : BNPA × actions moyen pondéré ≈ résultat net (poste "
        "auxiliaire `nombre_actions_moyen_pondere`, balisé seulement par ASML dans ce panel) et actif total ≈ "
        "dettes totales + capitaux propres, tolérance ± 15 % (non spécifiée dans la demande pour la 2e identité, "
        "réutilisée par simplicité) ; marge brute ≤ CA ; marge EBIT ∈ [-100 %, 100 %]. Contrôle exécuté sur les "
        "vraies clôtures d'exercice seulement (dates_clotures), pas sur les faits isolés à une autre date (ex. "
        "solde d'ouverture retraité IFRS 16 « au 1er janvier »). Sans nombre d'actions moyen pondéré balisé "
        "(Boliden, Valneva, Cucinelli...), le contrôle BNPA × actions est « non concluant » (calculé mais jamais "
        "de quarantaine) plutôt que d'utiliser le nombre d'actions DE CLÔTURE, structurellement différent du "
        "dénominateur du BNPA (IAS 33) en cas d'émission/rachat en cours d'exercice (cas Valneva FY2022, "
        "écart -20 % non concluant). En cas d'échec sur l'identité actif/passif (2 postes), on ne peut pas "
        "déterminer lequel est fautif : les deux sont mis en quarantaine par convention, capitaux propres sert "
        "de référence. Compteur « contrôles exécutés x/4 » par société et exercice (c.1) ; badge « non contrôlé » "
        "à 0/4.",
        "Retraitement non expliqué de BNPA/nombre_actions (règle ajoutée, corrigée) : un comparatif retraité "
        "sans split yfinance correspondant n'est PLUS appliqué — la valeur D'ORIGINE du rapport de l'exercice "
        "est conservée (ex. Boliden FY2021 nombre_actions : 273 511 169 conservé, pas le comparatif ÷100 du "
        "rapport FY2022), recoupée pour information avec le nombre d'actions yfinance actuel (badge, écart NON "
        "expliqué à ce stade — voir Boliden en c.2, item 20). Auparavant, le pipeline gardait le comparatif "
        "retraité par défaut (philosophie générale « dernier rapport fait foi »), ce qui retenait une valeur "
        "visiblement fausse pour ce cas précis. **Portée limitée (item 19)** : cette règle ne s'applique QU'aux "
        "postes par action et nombre d'actions (la boucle de `ajuster_splits`, voir son docstring). Le chiffre "
        "d'affaires, l'EBIT, les actifs (flux et stocks) restent gouvernés par `fusionner_rapports` (rapport le "
        "plus récent = référence, y compris pour un écart légitime important — activités abandonnées, "
        "changement de norme) ; seul un échec du contrôle de cohérence > 50 % (`rapports_incoherents`) exclut "
        "alors le rapport entier, jamais une correction poste par poste. Testé "
        "(test_ca_ebit_non_revertis_meme_si_ecart_important).",
        "P4 fiabilité (règle ajoutée, même principe que P2) : pour les sociétés à données en retard (dernier "
        "exercice yfinance, ex. Mycronic, Atlas Copco, Boliden), P4 est recalculé sur les seules années ESEF "
        "(N−1 vs N−2) et comparé au calcul avec l'exercice yfinance. Même conclusion → calcul fiable gardé sans "
        "plafonnement (Atlas Copco). Conclusion différente → « dépend d'une donnée non recoupée » (renommé "
        "depuis « non fiable », item 32 : le F-score ESEF seul porte sur N−1/N−2, des exercices plus anciens "
        "que l'exercice yfinance contesté — il ne prouve pas que yfinance est faux), non évaluable, verdict "
        "plafonné à SURVEILLANCE — cas marquants : Mycronic (3/7 KO avec yfinance vs 7/7 OK sur les seules "
        "données ESEF : la totalité des tests disponibles avec yfinance porte sur un exercice 100 % yfinance, "
        "détail en c.1) et Boliden (5/8 n.é. avec yfinance vs 8/9 OK en ESEF seul).",
        "Contrôle partiel (règle ajoutée) : badge distinct de « non contrôlé » quand 0 < contrôles exécutés < "
        "`controles_identite.seuil_partiel` (3, PARAMÈTRE arbitraire).",
        "P3 retour aux bénéfices (règle ajoutée) : BNPA de départ ≤ 0 (perte) mais dernier BNPA de la fenêtre "
        "> 0 → non évaluable (jamais ❌), CAGR indicatif affiché depuis la première année positive de la "
        "fenêtre (cas Cucinelli : perte Covid FY2020, CAGR indicatif calculé FY2021→FY2025). Le ❌ (CAGR non "
        "calculable) reste réservé aux sociétés encore déficitaires en fin de fenêtre (Valneva).",
        "Référentiel comptable (item 24) : ESEF = IFRS toujours (réglementaire, aucune vérification requise). "
        "Repli yfinance : référentiel non garanti identique — signalé pour ASML (double cotation Nasdaq, "
        "20-F réconcilié en US GAAP) bien que non utilisé ici (ASML dispose de 5 rapports ESEF, aucun repli "
        "yfinance pour ses fondamentaux). Chiffres US GAAP confirmés par le communiqué ASML du 28/01/2026 "
        "(source citée en §0).",
        "REJET sur données non recoupées (règle ajoutée) : badge sur tout verdict REJET fondé sur une société "
        "100 % yfinance (aucun rapport ESEF, ex. Sidetrade) — le rejet n'a pas pu être confirmé par une "
        "source indépendante.",
        "F-score de référence (règle ajoutée, remplace l'ancien calcul par défaut) : l'actif D'OUVERTURE "
        "(convention Piotroski originale — à vérifier, certaines implémentations utilisent l'actif moyen) "
        "devient le calcul principal de P4 pour F1/F3/F5/F9 ; l'actif de clôture (ancien calcul par défaut) "
        "n'est plus qu'un affichage indicatif. Si l'actif d'ouverture de l'exercice N−1 (= actif de clôture de "
        "N−2) est indisponible, ces 4 tests sont non évaluables (pas de repli silencieux sur la clôture) : "
        "le F-score peut alors reposer sur moins de 9 tests, via le mécanisme déjà existant du score partiel.",
        "cash_flow_operationnel : un seul concept mappé (`ifrs-full:CashFlowsFromUsedInOperatingActivities`, "
        "flux net APRÈS variation du BFR), jamais la ligne « avant variation du BFR » (vérifié : Hermès FY2025 "
        "distingue les deux, 5 607 M€ avant vs 5 374 M€ après, retenu). Testé (test_cfo_ne_prend_jamais_...).",
        "F5 dettes locatives IFRS 16 : choix retenu = dette_long_terme les EXCLUT (hypothèse déjà en place, "
        "#7). Non neutre : pour Hermès, F5 change selon la convention (b, comparaison chiffrée). ASML ne permet "
        "pas la comparaison (aucun concept IFRS séparé balisé pour ses dettes locatives non courantes).",
        "dette_long_terme (item 28) : `NoncurrentFinancialLiabilitiesAtAmortisedCost` / "
        "`OtherNoncurrentFinancialLiabilities` (Atlas Copco, Mycronic) délibérément NON mappés — "
        "rejetés par le contrôle yfinance Long Term Debt (écart systématique > 10 %, détail en d.2). "
        "F5 reste non évaluable pour ces exercices.",
        "capex Thermador (item 29) : extension `thermador:OutflowsForTheAcquisitionOfTangibleAnd"
        "IntangibleFixedAssets` ajoutée, libellé NON vérifié contre le rapport publié dans cette "
        "session (pas d'accès Internet, à la différence de `ebit`/`reserves` pour cette société). "
        "Signe inversé (valeur absolue) car le concept maison tague un flux sortant négatif, "
        "contrairement aux concepts génériques (magnitude positive) — testé.",
        "marge_brute Valneva (item 30) : calcul de secours `chiffre_affaires − cout_des_ventes` "
        "(nouveau poste auxiliaire `cout_des_ventes` → `ifrs-full:CostOfSales`), badge « marge "
        "brute reconstituée ». N'affecte pas Cucinelli/Thermador (présentation par nature, aucun "
        "`CostOfSales` balisé, hypothèse déjà correcte).",
    ]
    L += [f"{i}. {h}" for i, h in enumerate(hyp, 1)]
    L += ["", "### c.4 Journal du dernier run", ""]
    L += [f"- [{e['niveau']}] `{e['cle']}` : {e['message']}" for e in journal] or ["- aucune entrée"]
    return L


def section_d() -> list[str]:
    """Items 25bis et 27 : preuves de diagnostic (inspection du JSON brut des rapports ESEF
    en cache) pour les postes manquants, et propositions de correction NON codées."""
    L = ["## d) Diagnostic des postes manquants (items 25bis, 27) — preuves, sans code", "",
         "Méthode : recherche exhaustive, dans tous les rapports ESEF en cache de chaque société, "
         "des concepts XBRL dont le nom contient les mots-clés indiqués (faits sans dimension "
         "uniquement, ceux que le pipeline peut lire). Aucun changement de code dans cette section.",
         "", "### d.1 — F7 : nombre d'actions (item 25bis, option (a) conservée : indisponible)", ""]

    L += ["**Atlas Copco A** — concepts contenant « Shares » trouvés :", "",
          "| Concept | Type | Exemple |", "|---|---|---|",
          "| `atla:AcquisitionOfSeriesAShares` | montant SEK (flux de trésorerie, rachat d'actions "
          "propres) | 416 000 000 SEK (2021) |",
          "| `atla:DivestmentOfSeriesAShares` / `atla:DivestmentOfSeriesBShares` | montant SEK "
          "(cession d'actions propres) | 702 000 000 SEK (2021) |",
          "| `atla:RedemptionOfShares` | montant SEK (rachat/annulation) | -157 000 000 SEK (2022) |",
          "| `ifrs-full:DescriptionOfAccountingPolicyForTreasurySharesExplanatory` | **bloc TEXTE** "
          "(suédois, non numérique) | « När Atlas Copcos aktier som är klassificerade... » |",
          "| `ifrs-full:DisclosureOfTreasurySharesExplanatory` | **bloc TEXTE** contenant « Antal "
          "aktier » (= « Nombre d'actions ») en toutes lettres | texte narratif |", "",
          "**Diagnostic** : le nombre d'actions figure bien dans le rapport, mais seulement en "
          "texte narratif à l'intérieur d'un bloc « explicatif » (balisage ESEF de type texte, "
          "pas un fait numérique isolé). Les seuls faits NUMÉRIQUES tagués contenant « Shares » "
          "sont des MONTANTS en SEK (rachats/cessions d'actions propres), pas des comptes "
          "d'actions. Atlas Copco a bien des actions de catégorie A et B (confirmé par les noms de "
          "concepts), mais aucune n'est balisée comme un nombre. **Aucun concept alternatif ni "
          "somme de catégories A+B n'est possible : la donnée numérique n'existe pas dans le XBRL.**",
          "", "**Brunello Cucinelli** — recherche identique : **aucun concept contenant « Shares » "
          "dans aucun rapport**, ni montant ni texte. Le nombre d'actions n'apparaît nulle part "
          "dans le XBRL balisé.", "",
          "**Mycronic** — même profil qu'Atlas Copco : seuls `ifrs-full:DescriptionOfAccounting"
          "PolicyForTreasurySharesExplanatory` et `ifrs-full:DisclosureOfTreasurySharesExplanatory` "
          "(blocs texte suédois, LTIP inclus) contiennent « Shares » — aucun fait numérique.", "",
          "**Valneva** — cas différent : `ifrs-full:NumberOfSharesOutstanding` (unité `xbrli:shares`, "
          "bien un compte) EST balisé, mais seulement dans les rapports FY2019 à FY2022 (6 faits, "
          "dernier exemple : 138 367 482 au 31/12/2022). **Aucun fait de ce type dans les rapports "
          "FY2023, FY2024 ou FY2025** : Valneva a cessé de baliser ce concept à partir de l'exercice "
          "FY2023, sans que la raison soit déterminable depuis le XBRL seul (changement de logiciel "
          "de balisage, de cabinet, ou choix éditorial — hypothèses, non vérifiées).", "",
          "**Conclusion (item 25bis)** : aucune des 4 sociétés n'offre de concept alternatif ou de "
          "dimension à sommer — le nombre d'actions est structurellement absent du XBRL balisé "
          "(texte narratif ou rien du tout), pas mal mappé. **Option (a) confirmée et conservée : "
          "F7 reste indisponible, aucun code changé.**", ""]

    L += ["### d.2 — dette_long_terme / dette_court_terme (item 27, décision item 28 : REJETÉ, aucun code)", "",
          "**Décision** : `NoncurrentFinancialLiabilitiesAtAmortisedCost` et "
          "`OtherNoncurrentFinancialLiabilities` ne sont PAS mappés (catégories IFRS 7 : mélangent "
          "emprunts bancaires, dettes locatives et autres passifs financiers). Recherche "
          "complémentaire d'une ligne « emprunts / interest-bearing liabilities » ou d'une note "
          "détaillée : `ifrs-full:DisclosureOfBorrowingsExplanatory` existe pour les deux sociétés, "
          "mais c'est un **bloc TEXTE narratif** (comme les blocs « Treasury Shares » du d.1), sans "
          "axe de dimension structuré (`ifrs-full:ComponentsOfEquityAxis` est le seul axe utilisé "
          "dans les deux rapports) : aucune ventilation numérique par type d'emprunt n'est "
          "extractible. **Aucune ligne fiable trouvée : F5 reste non évaluable pour ces exercices, "
          "aucun code changé.**", "",
          "**Contrôle demandé (comparaison au candidat écarté vs yfinance Long Term Debt, écart "
          "> 10 % → rejeté), sur tous les exercices communs disponibles :**", "",
          "| Société | Exercice | Concept ESEF écarté | Valeur ESEF | yfinance Long Term Debt | "
          "Écart | Décision |", "|---|---|---|---|---|---|---|",
          "| Atlas Copco A | FY2022 | `OtherNoncurrentFinancialLiabilities` | 23 770 M SEK | "
          "20 233 M SEK | +17,5 % | **rejeté** |",
          "| Atlas Copco A | FY2023 | idem | 29 967 M SEK | 25 598 M SEK | +17,1 % | **rejeté** |",
          "| Atlas Copco A | FY2024 | idem | 31 688 M SEK | 26 240 M SEK | +20,8 % | **rejeté** |",
          "| Mycronic | FY2022 | `NoncurrentFinancialLiabilitiesAtAmortisedCost` | 193 M SEK | "
          "7 M SEK | +2 657 % | **rejeté** |", "",
          "Écart systématique et massif dans les deux cas (jamais < 17 %, jusqu'à ×27 pour "
          "Mycronic) : confirme quantitativement l'hypothèse qualitative — ces concepts « Financial "
          "Liabilities » incluent bien d'autres passifs que la seule dette financière comparable à "
          "yfinance Long Term Debt. **Décision finale : aucun des deux concepts n'est mappé.**", ""]

    L += ["### d.3 — capex (item 27/29, Thermador, tous exercices) — IMPLÉMENTÉ", "",
          "`thermador:OutflowsForTheAcquisitionOfTangibleAndIntangibleFixedAssets` ajouté en "
          "extension pour le LEI Thermador dans `mapping_ifrs.yaml` (même mécanisme déjà en place "
          "pour `ebit`/`reserves` de cette société). **Limite assumée** : à la différence des deux "
          "entrées `ebit`/`reserves` (vérifiées contre le rapport publié dans une session "
          "antérieure), **le libellé de ce concept n'a PAS pu être vérifié contre le rapport "
          "imprimé dans cette session (pas d'accès Internet)** — la source indiquée dans "
          "`mapping_ifrs.yaml` le précise explicitement. Le nom du concept est auto-descriptif et "
          "cohérent avec l'hypothèse #7, mais reste une vérification en attente.", "",
          "**Correction additionnelle découverte en implémentant** : ce concept maison tague un "
          "flux SORTANT NÉGATIF (ex. -12 221 000 € en FY2021), alors que tous les concepts capex "
          "génériques déjà mappés (utilisés par les 6 autres sociétés du panel) sont des magnitudes "
          "POSITIVES. Sans correction, cela aurait faussé silencieusement Q2/V3 (FCF = CFO − capex "
          "serait devenu CFO + |capex|). Valeur absolue retenue, badge « signe inversé » ajouté "
          "(`pipeline/normalize.py`, testé). Capex Thermador maintenant disponible sur les 7 "
          "exercices (ex. FY2021 : 12 221 000 €, FY2025 : 5 697 000 €).", ""]

    L += ["### d.4 — marge_brute (item 27/30, Cucinelli, Thermador, Valneva) — IMPLÉMENTÉ (Valneva)", "",
          "- **Brunello Cucinelli et Thermador** : présentation par nature confirmée (aucun "
          "`CostOfSales`), aucune correction possible — hypothèse déjà correcte, inchangée.",
          "- **Valneva** : `marge_brute = chiffre_affaires − cout_des_ventes` (nouveau poste "
          "auxiliaire `cout_des_ventes` → `ifrs-full:CostOfSales`, calcul de secours dans "
          "`normalize._secours()`, même mécanisme que `dettes_totales`/`actif_courant`/"
          "`dettes_courantes`). Badge « marge brute reconstituée (chiffre d'affaires − coût des "
          "ventes) ». Disponible sur les 7 exercices désormais (ex. FY2025 : 67 520 000 €). Testé "
          "(secours appliqué seulement si `GrossProfit` n'est pas balisé directement).", ""]
    return L


def main() -> None:
    cfg = config()
    synth, societes, journal = charger()
    tests = resultat_tests()
    L = ["# Rapport — Étape 1 : ingestion et calculs sur 10 sociétés test", "",
         f"Généré le {synth['date']} par `pipeline/report_etape1.py` à partir de `data/processed/`. "
         "Analyse, pas un conseil en investissement personnalisé.", "",
         f"- Tests unitaires : `{tests}` (`.venv/bin/python -m pytest tests`).",
         "- Relancer : `.venv/bin/python -m pipeline.run` puis `.venv/bin/python -m pipeline.report_etape1`.",
         "- Les scores QVM de ce panel sont **non significatifs** (10 sociétés, percentiles sur l'univers entier).", ""]
    L += section_panel(societes)
    L += section_a(societes, cfg) + [""]
    L += section_b(societes) + [""]
    L += section_c(societes, journal, cfg) + [""]
    L += section_d()
    (RACINE / "docs" / "rapport_etape1.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("docs/rapport_etape1.md écrit")


if __name__ == "__main__":
    main()
