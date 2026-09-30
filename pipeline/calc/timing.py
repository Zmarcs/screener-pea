"""Étage 3 — Timing (signal d'entrée, n'entre jamais dans le score).

RSI 14 : méthode de lissage de Wilder (HYPOTHÈSE : variante standard de J. W. Wilder, 1978).
MM : moyennes arithmétiques des clôtures.
"""
from __future__ import annotations

VERT, JAUNE, ROUGE, NE = "vert", "jaune", "rouge", "ne"


def moyenne_mobile(cours: list[float], n: int) -> list[float | None]:
    sortie: list[float | None] = []
    somme = 0.0
    for i, c in enumerate(cours):
        somme += c
        if i >= n:
            somme -= cours[i - n]
        sortie.append(somme / n if i >= n - 1 else None)
    return sortie


def rsi_wilder(cours: list[float], n: int = 14) -> list[float | None]:
    """RSI de Wilder : moyenne simple des n premières variations, puis
    moy = (moy_préc × (n − 1) + variation) / n."""
    sortie: list[float | None] = [None] * len(cours)
    if len(cours) <= n:
        return sortie
    hausses = [max(cours[i] - cours[i - 1], 0.0) for i in range(1, len(cours))]
    baisses = [max(cours[i - 1] - cours[i], 0.0) for i in range(1, len(cours))]
    mh, mb = sum(hausses[:n]) / n, sum(baisses[:n]) / n

    def valeur(h, b):
        if b == 0:
            return 100.0 if h > 0 else 50.0
        return 100.0 - 100.0 / (1.0 + h / b)

    sortie[n] = valeur(mh, mb)
    for i in range(n + 1, len(cours)):
        mh = (mh * (n - 1) + hausses[i - 1]) / n
        mb = (mb * (n - 1) + baisses[i - 1]) / n
        sortie[i] = valeur(mh, mb)
    return sortie


def signal(cours: list[float], cfg_t: dict) -> dict:
    n_long, n_court = cfg_t["mm_longue"], cfg_t["mm_courte"]
    pente = cfg_t["pente_mm200_seances"]
    if len(cours) < n_long + pente:
        return {"signal": NE, "raisons": [f"historique de cours insuffisant ({len(cours)} séances)"]}
    mm200 = moyenne_mobile(cours, n_long)
    mm50 = moyenne_mobile(cours, n_court)
    rsi = rsi_wilder(cours, cfg_t["rsi_periode"])
    c, m200, m200_avant, m50, r = cours[-1], mm200[-1], mm200[-1 - pente], mm50[-1], rsi[-1]
    ecart_mm50 = c / m50 - 1
    lo, hi = cfg_t["rsi_zone_entree"]
    res = {"cours": c, "mm50": m50, "mm200": m200, "mm200_il_y_a_1_mois": m200_avant,
           "rsi": r, "ecart_mm50": ecart_mm50}

    if c < m200:
        return {**res, "signal": ROUGE,
                "raisons": ["cours < MM200 : tendance baissière, pas d'entrée même si RSI < 30"]}
    hausse_mm200 = m200 > m200_avant
    repli = lo <= r <= hi or abs(ecart_mm50) <= cfg_t["ecart_mm50_max"]
    if c > m200 and hausse_mm200 and repli:
        pourquoi = []
        if lo <= r <= hi:
            pourquoi.append(f"RSI {r:.1f} dans la zone {lo}-{hi}")
        if abs(ecart_mm50) <= cfg_t["ecart_mm50_max"]:
            pourquoi.append(f"cours à {ecart_mm50:+.1%} de la MM50")
        return {**res, "signal": VERT, "raisons": ["cours > MM200 et MM200 en hausse sur 1 mois"] + pourquoi}
    raisons = []
    if r >= cfg_t["rsi_surachat"]:
        raisons.append(f"surachat (RSI {r:.1f} ≥ {cfg_t['rsi_surachat']}) : ne pas initier")
    elif r > hi:
        raisons.append(f"tendance haussière sans repli (RSI {r:.1f} > {hi})")
    elif not repli:
        raisons.append(f"pas de repli exploitable (RSI {r:.1f} < {lo}, cours à {ecart_mm50:+.1%} de la MM50)")
    if not hausse_mm200:
        raisons.append("MM200 pas en hausse sur 1 mois")
    if c == m200:
        raisons.append("cours = MM200")
    return {**res, "signal": JAUNE, "raisons": raisons}
