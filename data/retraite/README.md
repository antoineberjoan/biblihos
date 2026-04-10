# Données Retraite

Données de référence des régimes de retraite français.

## Organisation

```
data/retraite/
├── cnav.yaml           # Régime général de base (salariés privé)
├── agirc-arrco.yaml    # Complémentaire salariés privé
└── ircantec.yaml       # Complémentaire agents non titulaires de l'État
```

## Conventions

- Taux en décimales : `0.50` = 50 %
- Montants en euros
- Données non disponibles : `"—"` (tiret cadratin U+2014), jamais `null`
- Durées en mois (ex: `ageLegalMois: 768` = 64 ans)

## Sources

- CNAV : service-public.gouv.fr, circulaires CNAV, Code de la Sécurité sociale
- Agirc-Arrco : agirc-arrco.fr, ANI
- IRCANTEC : ircantec.retraites.fr

## Mise à jour

Fréquence : annuelle (revalorisation au 1er janvier ou au 1er novembre selon le régime).
