---
name: lifeos-x
description: >
  Contenu X (Twitter) : tendances, génération de brouillons, publication.
  Triggers: "post X", "tweet", "contenu Twitter", "idées de posts", "publier sur X", "engagement X", "commenter".
requires:
  - mcp: bridgeai (lifeos_x_growth_trends, lifeos_x_growth_generate, lifeos_x_growth_publish, lifeos_x_engage, lifeos_content_x)
---

# Skill : LifeOS Contenu X

⚠️ **ATTENTION** : `lifeos_x_growth_publish` et `lifeos_x_engage` sont des actions HIGH RISK — elles publient réellement sur X. Une approbation Telegram sera demandée automatiquement. Ne jamais appeler sans confirmation explicite de Laurent.

## Flux de création

### Étape 1 — Tendances
```
lifeos_x_growth_trends()
```
Retourne les tendances dev/AI/freelance via Grok. Présenter les 3-5 tendances les plus pertinentes avec pourquoi elles sont virales.

### Étape 2 — Génération de brouillons
```
lifeos_x_growth_generate()
```
Génère 5 brouillons dans Notion. Présenter les brouillons générés. Demander à Laurent lesquels valider.

### Étape 3 — Publication (HIGH RISK)
```
lifeos_x_growth_publish()
```
⚠️ Publie les brouillons validés sur X. Approbation Telegram requise automatiquement.

## Flux d'engagement

### Commenter des posts viraux
```
lifeos_x_engage({ mode: "auto" })   // génère et poste automatiquement
lifeos_x_engage({ mode: "prep" })   // prépare les commentaires sans poster
```
⚠️ Mode `auto` = publication immédiate → approbation Telegram requise.
Préférer `mode: "prep"` pour review avant de poster.

## Voir les posts récents
```
lifeos_content_x()
```
Retourne les posts X récents publiés.

## Notes

- Toujours présenter les brouillons avant de proposer la publication
- En mode "prep", afficher les commentaires préparés et demander confirmation avant de lancer `auto`
- Le pipeline complet = trends → generate → review → publish
