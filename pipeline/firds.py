"""Lecture des fichiers de référence FIRDS (ESMA, fichiers `FULINS_E_*`, catégorie Actions,
schéma ISO 20022 `auth.017.001.02`).

Champ venue : `TradgVnRltdAttrbts/Id` — PAS `TechAttrbts/RlvntTradgVn`. Ce second champ est un
attribut de NIVEAU ISIN (« venue la plus pertinente en liquidité » au sens RTS de transparence
post-marché), constant sur tous les enregistrements FIRDS d'un même ISIN quelle que soit leur
venue réelle — vérifié : 0 exception sur 729 992 enregistrements du fichier `FULINS_E` du
05/09/2026. `TradgVnRltdAttrbts/Id` est le vrai code venue par enregistrement : un ISIN a un
`RefData` par venue où il est effectivement admis, et c'est CE champ qui varie. Détail complet
de la découverte (avec exemples réels, Atlas Copco A et Paradox Interactive AB) : docs/univers.md
§9 et §16. Voir aussi `tests/test_firds.py` (régression) et `tests/fixtures/firds_extrait_reel.xml`
(extrait réel du fichier ESMA, pas de données inventées).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{urn:iso:std:iso:20022:tech:xsd:auth.017.001.02}"


def extraire_venue(ref_data: ET.Element) -> dict:
    """Extrait un enregistrement (ISIN, venue) d'un élément `RefData`."""
    gnl = ref_data.find(NS + "FinInstrmGnlAttrbts")
    tva = ref_data.find(NS + "TradgVnRltdAttrbts")
    return {
        "isin": gnl.findtext(NS + "Id") if gnl is not None else None,
        "cfi": gnl.findtext(NS + "ClssfctnTp") if gnl is not None else None,
        "devise": gnl.findtext(NS + "NtnlCcy") if gnl is not None else None,
        "nom": gnl.findtext(NS + "FullNm") if gnl is not None else None,
        "lei": ref_data.findtext(NS + "Issr"),
        "venue": tva.findtext(NS + "Id") if tva is not None else None,
        "terminee": tva.findtext(NS + "TermntnDt") if tva is not None else None,
        "premiere_negociation": tva.findtext(NS + "FrstTradDt") if tva is not None else None,
        "admission_demandee_par_emetteur": (tva.findtext(NS + "IssrReq") if tva is not None else None) == "true",
    }


def lire_fichier(chemin: str | Path) -> list[dict]:
    """Itère sur un fichier `FULINS_E` (ou tout extrait au même format) et renvoie un
    enregistrement par `RefData` — PAS un par ISIN : un même ISIN a un `RefData` par venue où
    il est admis (voir module docstring)."""
    enregistrements = []
    for _event, elem in ET.iterparse(str(chemin), events=("end",)):
        if elem.tag == NS + "RefData":
            enregistrements.append(extraire_venue(elem))
            elem.clear()
    return enregistrements
