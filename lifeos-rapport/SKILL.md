---
name: lifeos-rapport
description: >
  Bilan de fin de journée : tâches terminées, métriques, actions du lendemain.
  Triggers: "bilan", "rapport", "fin de journée", "recap du jour", "qu'est-ce que j'ai fait".
requires:
  - mcp: bridgeai (lifeos_rapport, lifeos_metrics, lifeos_stagnation)
---

# Skill : LifeOS Rapport de fin de journée

## Étape 1 — Fetch parallèle

```
lifeos_rapport()
lifeos_metrics()
lifeos_stagnation()
```

- `lifeos_rapport()` : tâches terminées + métriques du jour
- `lifeos_metrics()` : métriques X + Malt
- `lifeos_stagnation()` : tâches stagnantes >14j et backlog mort >30j

## Étape 2 — Affichage

Format Telegram (skill telegram-output). Structurer ainsi :

### Bilan — {date}

**Accompli aujourd'hui**
- [tâche terminée] ✓
- ...

**Métriques du jour**
- X : N abonnés (+/-N), N vues
- Malt : N leads, N vues profil

**À surveiller**
- Tâches stagnantes : [liste si >0]
- Backlog mort : [liste si >0]

**Pour demain**
- 2-3 actions concrètes basées sur ce qui reste et ce qui bloque

## Notes

- Si aucune tâche terminée, signaler sans dramatiser et proposer un focus pour demain
- Être concis — c'est un bilan, pas un roman
