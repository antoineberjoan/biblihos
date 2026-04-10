# Biblihos

Données de référence pour [Rheos](https://github.com/antoineberjoan/rheos) — gestion de patrimoine pour CGP.

## Structure

```
biblihos/
├── data/
│   ├── scpi/           # Un dossier par société de gestion, un fichier par véhicule
│   └── retraite/       # Un fichier par régime (CNAV, Agirc-Arrco, IRCANTEC)
├── schemas/            # JSON Schema (Draft 2020-12) en YAML — validation stricte
├── scrapers/           # Scripts Python d'extraction automatisée (Scrapling)
├── scripts/            # Utilitaires (validation, conversion)
└── .github/workflows/  # CI : validation + scraping programmé
```

## Conventions

| Règle | Détail |
|-------|--------|
| Donnée manquante | `"—"` (tiret cadratin U+2014), jamais `null` ni champ absent |
| Pourcentages | Décimales (`0.065` = 6,5 %) |
| Montants | Euros, sans séparateur de milliers |
| Ordre des champs | Identique pour tous les fichiers d'une même catégorie |
| Noms de champs | camelCase, alignés sur le glossaire Rheos |

## Validation

```bash
pip install -e ".[dev]"
python scripts/validate.py schemas/scpi.yaml data/scpi/
python scripts/validate.py schemas/retraite.yaml data/retraite/
```

## Ajout d'une SCPI

1. Créer `data/scpi/<societe-de-gestion>/<nom-fonds>.yaml`
2. Copier le template `data/scpi/corum/origin.yaml` comme base
3. Remplir les champs connus, mettre `"—"` pour les autres
4. Valider : `python scripts/validate.py schemas/scpi.yaml data/scpi/<societe>/<fonds>.yaml`
