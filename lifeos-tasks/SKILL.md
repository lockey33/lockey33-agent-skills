---
name: lifeos-tasks
description: >
  Gestion des tâches Notion : voir, prioriser, détecter les stagnations.
  Triggers: "mes tâches", "tâches actives", "qu'est-ce qui stagne", "backlog", "priorités", "prochaine tâche".
requires:
  - mcp: bridgeai (lifeos_tasks, lifeos_prioritize, lifeos_stagnation, lifeos_challenge, lifeos_heartbeat)
---

# Skill : LifeOS Gestion des tâches

## Cas d'usage

### "Mes tâches" / vue générale
```
lifeos_tasks({ active: true })
lifeos_prioritize()
```
Afficher les tâches actives + top 3 prioritaires.

### "Qu'est-ce qui stagne ?"
```
lifeos_stagnation()
```
Lister tâches stagnantes (>14j) et backlog mort (>30j). Proposer des actions : archiver, relancer, reprioriser.

### "Challenge mes tâches"
```
lifeos_challenge()
```
Confronte les tâches actives aux objectifs stratégiques. Signaler les tâches hors-objectifs.

### "Objectifs récurrents / heartbeat"
```
lifeos_heartbeat()
```
Afficher les objectifs récurrents et l'état des checklists itératives.

## Format

Format Telegram (skill telegram-output). Toujours :
- Tâches groupées par statut si >5 tâches
- Top 3 en gras en tête de liste
- Stagnations signalées clairement avec durée de stagnation
- Proposer des actions concrètes, pas juste lister

## Notes

- `lifeos_tasks` accepte `--active`, `--completed`, `--statuses`
- Ne jamais modifier les tâches directement — Diego est en lecture seule sur les tâches (pas de tool d'écriture exposé)
