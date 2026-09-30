# Données manuelles (priment sur les données automatiques)

- `isin_lei.csv` : correspondances ISIN → LEI vérifiées à la main (prioritaires sur GLEIF),
  avec statut `actuel` / `historique` / `non_identifie` et la source de la vérification.
- `esef_overrides.yaml` : rapports ESEF à métadonnée incohérente, réintégrés avec explication.
- `pea_exceptions.csv` : exceptions d'éligibilité PEA.
- `{isin}.yaml` : corrections de valeurs. Format :
  ```yaml
  corrections:
    - poste: dette_long_terme      # nom de poste de pipeline/mapping_ifrs.yaml
      exercice: 2024               # année de clôture
      valeur: 0
      source: "Rapport annuel 2024, bilan consolidé, p. 312"
      motif: "Aucun emprunt : poste absent du balisage"
  ```
- `portefeuille.yaml` : positions personnelles. **Ignoré par git, ne jamais le publier.**
