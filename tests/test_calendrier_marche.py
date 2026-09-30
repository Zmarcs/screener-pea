"""Tests du calendrier de marché (pipeline/calendrier_marche.py).

Couvre les 9 places demandées (Stockholm, Oslo, Helsinki, Copenhague, Madrid, Milan, Varsovie,
Vienne, Athènes) : fuseau + heure de clôture déclarés ; jours fériés locaux (une séance
manquante dans la série suffit — pas de calendrier de jours fériés séparé, voir
test_ecart_ferie_n_affecte_pas_la_regle) ; demi-séances du 24/12 et du 31/12 (heure réduite
connue Euronext, prudence explicite ailleurs) ; passage à l'heure d'hiver du 25/10/2026
(zoneinfo/tzdata gère la bascule automatiquement — le test vérifie que le calcul reste correct
de part et d'autre de la transition, pas que le code la traite lui-même).
"""
import datetime as dt

from pipeline import calendrier_marche as C

PLACES_DEMANDEES = {
    "ST": ("Europe/Stockholm", (17, 25)),
    "OL": ("Europe/Oslo", (16, 20)),
    "HE": ("Europe/Helsinki", (18, 25)),
    "CO": ("Europe/Copenhagen", (17, 0)),
    "MC": ("Europe/Madrid", (17, 30)),
    "MI": ("Europe/Rome", (17, 30)),
    "WA": ("Europe/Warsaw", (16, 50)),
    "VI": ("Europe/Vienna", (17, 30)),
    "AT": ("Europe/Athens", (17, 20)),
}


def test_neuf_places_demandees_ont_fuseau_et_cloture_sources():
    for suffixe, (fuseau, cloture) in PLACES_DEMANDEES.items():
        info = C.PLACES[suffixe]
        assert info["fuseau"] == fuseau
        assert info["cloture"] == cloture
        assert info["source"], f"{suffixe} : source manquante"


def test_avant_cloture_plus_delai_seance_incomplete():
    # Stockholm clôture 17:25 ; delai par defaut 60 min -> 18:25. A 18:00 locale, incomplet.
    maintenant = dt.datetime(2026, 9, 30, 16, 0, tzinfo=dt.timezone.utc)  # 18:00 Europe/Stockholm (CEST, +2)
    diag = C.seance_complete("ATCO-A.ST", dt.date(2026, 9, 30), maintenant)
    assert diag["complete"] is False


def test_apres_cloture_plus_delai_seance_complete():
    maintenant = dt.datetime(2026, 9, 30, 16, 30, tzinfo=dt.timezone.utc)  # 18:30 Europe/Stockholm
    diag = C.seance_complete("ATCO-A.ST", dt.date(2026, 9, 30), maintenant)
    assert diag["complete"] is True


def test_barre_d_hier_toujours_complete_quelle_que_soit_l_heure():
    # Même juste après l'ouverture du jour suivant, une barre datée d'hier est complète.
    maintenant = dt.datetime(2026, 9, 30, 5, 1, tzinfo=dt.timezone.utc)  # 07:01 Europe/Warsaw
    diag = C.seance_complete("PKN.WA", dt.date(2026, 9, 29), maintenant)
    assert diag["complete"] is True


def test_ecart_ferie_n_affecte_pas_la_regle():
    """Un jour férié local (ex. 6 janvier, Épiphanie, férié en Grèce/Pologne/Autriche) ne
    produit simplement aucune barre dans la série renvoyée par yfinance — la règle ne
    s'appuie jamais sur un calendrier de jours fériés séparé, seulement sur la date de la
    DERNIÈRE barre présente. Ex. : dernière barre 2026-01-02 (vendredi), aujourd'hui
    2026-01-06 (férié Athènes) : le vide du 5/01 (WE) et du 6/01 (férié) n'a pas besoin
    d'être modélisé, la barre du 2/01 est simplement antérieure à aujourd'hui."""
    maintenant = dt.datetime(2026, 1, 6, 12, 0, tzinfo=dt.timezone.utc)
    diag = C.seance_complete("ETE.AT", dt.date(2026, 1, 2), maintenant)
    assert diag["complete"] is True


def test_demi_seance_euronext_heure_reduite_appliquee():
    # Paris, 24/12/2026 (jeudi) : clôture réduite 14:05 (Euronext, sourcé). A 15:10 locale
    # (avec le délai par défaut de 60 min, cloture+delai = 15:05) -> complet.
    maintenant = dt.datetime(2026, 12, 24, 14, 10, tzinfo=dt.timezone.utc)  # 15:10 Europe/Paris (CET, +1)
    diag = C.seance_complete("RMS.PA", dt.date(2026, 12, 24), maintenant)
    assert diag["complete"] is True
    assert diag["demi_seance_non_modelisee"] is False


def test_demi_seance_euronext_avant_cloture_reduite_incomplete():
    maintenant = dt.datetime(2026, 12, 24, 12, 30, tzinfo=dt.timezone.utc)  # 13:30 Europe/Paris
    diag = C.seance_complete("RMS.PA", dt.date(2026, 12, 24), maintenant)
    assert diag["complete"] is False


def test_demi_seance_place_non_verifiee_prudence_heure_standard():
    # Stockholm n'a pas d'heure de clôture réduite vérifiée pour le 24/12 : on garde l'heure
    # standard (17:25) par prudence, avec le drapeau explicite — jamais d'heure inventée.
    maintenant = dt.datetime(2026, 12, 24, 13, 10, tzinfo=dt.timezone.utc)  # 14:10 Europe/Stockholm (CET, +1)
    diag = C.seance_complete("ATCO-A.ST", dt.date(2026, 12, 24), maintenant)
    assert diag["demi_seance_non_modelisee"] is True
    # 14:10 < 17:25 + 60 min -> incomplet (la place est peut-être déjà fermée en vrai, mais on
    # ne peut pas l'affirmer sans l'heure vérifiée : direction sûre, jamais l'inverse).
    assert diag["complete"] is False


def test_place_non_reconnue_jamais_complete_par_defaut():
    diag = C.seance_complete("XYZ.ZZ", dt.date(2020, 1, 1), dt.datetime(2026, 9, 30, tzinfo=dt.timezone.utc))
    assert diag["complete"] is None


def test_passage_heure_hiver_25_10_2026_paris():
    """Le 25/10/2026 à 01:00 UTC, l'Europe passe de CEST (UTC+2) à CET (UTC+1). zoneinfo (via
    tzdata) doit refléter cette bascule sans code dédié dans calendrier_marche.py."""
    avant = dt.datetime(2026, 10, 25, 0, 30, tzinfo=dt.timezone.utc)   # encore CEST
    apres = dt.datetime(2026, 10, 25, 1, 30, tzinfo=dt.timezone.utc)   # déjà CET
    tz = __import__("zoneinfo").ZoneInfo("Europe/Paris")
    assert avant.astimezone(tz).utcoffset() == dt.timedelta(hours=2)
    assert apres.astimezone(tz).utcoffset() == dt.timedelta(hours=1)
    # Conséquence pratique : une barre du 25/10 évaluée juste après la bascule (02:15 locale
    # CET) doit toujours se comparer à la clôture 17:30 CET de ce même jour, pas CEST.
    diag = C.seance_complete("RMS.PA", dt.date(2026, 10, 25), apres)
    assert diag["complete"] is False  # 02:15 locale < 17:30 + délai


def test_delai_stabilisation_lu_depuis_config():
    assert C._delai_stabilisation_minutes() == 60  # pipeline/config.yaml: marche.delai_stabilisation_minutes
