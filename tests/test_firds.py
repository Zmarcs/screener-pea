"""Régression sur le bug de champ FIRDS trouvé le 30/09 (docs/univers.md §9/§16) : le code doit
utiliser `TradgVnRltdAttrbts/Id` (la vraie venue par enregistrement) et jamais
`TechAttrbts/RlvntTradgVn` (un attribut de niveau ISIN, constant sur tous les enregistrements
d'un même ISIN, qui n'est PAS une venue d'admission réelle — confondre les deux avait fait
chuter les effectifs Nasdaq Stockholm/Helsinki de ~70 % dans l'univers avant correction).

Fixture : `tests/fixtures/firds_extrait_reel.xml`, un extrait RÉEL (2 RefData) du fichier ESMA
FULINS_E du 05/09/2026 — pas de données inventées.
"""
from pathlib import Path

from pipeline import firds

FIXTURE = Path(__file__).parent / "fixtures" / "firds_extrait_reel.xml"


def test_lire_fichier_renvoie_deux_enregistrements():
    enregistrements = firds.lire_fichier(FIXTURE)
    assert len(enregistrements) == 2


def test_paradox_interactive_venue_est_ssme_pas_xsto():
    """Paradox Interactive AB (SE0008294953) est admise sur SSME (First North Sweden - SME
    Growth Market, admission demandée par l'émetteur). Le champ RlvntTradgVn de CET
    enregistrement affiche pourtant XSTO (Nasdaq Stockholm) — la venue réelle de
    l'enregistrement reste SSME, pas XSTO."""
    enregistrements = firds.lire_fichier(FIXTURE)
    paradox = next(e for e in enregistrements if e["isin"] == "SE0008294953")
    assert paradox["venue"] == "SSME"
    assert paradox["nom"] == "Paradox Interactive AB"
    assert paradox["admission_demandee_par_emetteur"] is True
    assert paradox["terminee"] is None


def test_raisio_venue_est_aqeu_pas_dhel():
    """Raisio Oyj (FI0009800395) : cet enregistrement porte sur la venue AQEU (Aquis Exchange
    Europe, plateforme MTF tierce), pas DHEL (Nasdaq Helsinki) malgré ce qu'affiche
    RlvntTradgVn sur ce même enregistrement."""
    enregistrements = firds.lire_fichier(FIXTURE)
    raisio = next(e for e in enregistrements if e["isin"] == "FI0009800395")
    assert raisio["venue"] == "AQEU"
    assert raisio["lei"] == "74370083282NHIP4QD02"


def test_extraire_venue_ne_lit_jamais_rlvnttradgvn():
    """Garde-fou explicite : le module ne doit contenir aucune lecture de RlvntTradgVn comme
    source de la venue (relit le code source pour l'empêcher de réapparaître silencieusement)."""
    source = Path(firds.__file__).read_text(encoding="utf-8")
    assert '"venue":' in source
    # la seule mention de RlvntTradgVn dans le module doit être dans le docstring (l'avertissement),
    # jamais dans une ligne de code qui l'assigne à "venue"
    lignes_code = [l for l in source.splitlines() if "RlvntTradgVn" in l and not l.strip().startswith(("#", '"""'))]
    assert all("findtext" not in l for l in lignes_code), (
        "RlvntTradgVn ne doit jamais être lu comme champ venue — utiliser TradgVnRltdAttrbts/Id")
