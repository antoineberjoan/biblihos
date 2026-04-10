# Biblihos — Données retraite

Référentiel de barèmes et paramètres des régimes de retraite français, structurés en YAML et validés par schéma JSON Schema. Utilisé comme source de données par [Rheos](https://github.com/antoineberjoan/rheos).

## Couverture

| Catégorie | Régimes |
|-----------|---------|
| Salarié privé | CNAV, Agirc-Arrco, IRCANTEC |
| Fonctionnaire | SRE (État), CNRACL (territorial/hospitalier), ERAFP |
| Libéral | CNAVPL (chapeau), CARMF, CARPIMKO, CAVEC, CAVP, CNBF, CARCDSF, CAVAMAC |
| Autre | MSA (agricole), CRPCEN (notaires) |

## Structure

```
data/retraite/
├── salarie-prive/      # CNAV, Agirc-Arrco, IRCANTEC
├── fonctionnaire/      # SRE, CNRACL, ERAFP
├── liberal/            # CNAVPL + sections
└── autre/              # MSA, CRPCEN

schemas/
├── retraite.yaml              # salarié privé
├── retraite_fonctionnaire.yaml
└── retraite_liberal.yaml

scrapers/retraite/             # extraction automatisée
scripts/validate.py            # validation YAML contre schéma
```

## Conventions

| Règle | Détail |
|-------|--------|
| Donnée manquante | `"—"` (tiret cadratin U+2014), jamais `null` |
| Pourcentages | Décimales (`0.0823` = 8,23 %) |
| Montants | Euros, sans séparateur de milliers |
| Noms de champs | camelCase |

## Validation

```bash
pip install -e ".[dev]"
python scripts/validate.py schemas/retraite.yaml data/retraite/salarie-prive/
python scripts/validate.py schemas/retraite_fonctionnaire.yaml data/retraite/fonctionnaire/
python scripts/validate.py schemas/retraite_liberal.yaml data/retraite/liberal/
python scripts/validate.py schemas/retraite_fonctionnaire.yaml data/retraite/autre/
```

La CI GitHub Actions valide automatiquement à chaque push sur `data/` ou `schemas/`.
