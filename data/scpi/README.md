# Données SCPI

Données de référence des SCPI et SCI, organisées par société de gestion.

## Organisation

```
data/scpi/
├── corum/
│   ├── origin.yaml
│   ├── xl.yaml
│   └── eurion.yaml
├── iroko/
│   └── zen.yaml
└── ...
```

Un dossier par société de gestion (kebab-case), un fichier par véhicule (kebab-case).

## Conventions

- Pourcentages en décimales : `0.065` = 6,5 %
- Montants en euros (sans séparateur)
- Données non disponibles : `"—"` (tiret cadratin U+2014), jamais `null`
- L'ordre des champs est IDENTIQUE pour tous les fichiers — ne pas réordonner

## Sources

Données extraites des documents officiels : DIC, rapports annuels, bulletins trimestriels, sites des sociétés de gestion et agrégateurs (france-scpi.com, primaliance.com, louveinvest.com).

## Mise à jour

Fréquence cible : trimestrielle (après publication des bulletins trimestriels).
Le scraper `scrapers/scpi/` automatise l'extraction.
