---
name: lifeos-standup
description: >
  Standup du matin de Laurent : tâches prioritaires, métriques, leads, candidatures.
  Triggers: "standup", "quoi faire aujourd'hui", "brief du matin", "morning", "priorités du jour".
requires:
  - mcp: bridgeai (lifeos_context, lifeos_standup, lifeos_prioritize, lifeos_orchestrate)
---

# Skill : LifeOS Standup du matin

## Étape 1 — Contexte

```
lifeos_context()
```

Détecte le mode actuel (heure, jour). Adapter le ton selon le mode retourné.

## Étape 2 — Fetch parallèle

Lancer en parallèle :
```
lifeos_standup()
lifeos_prioritize()
```

`lifeos_standup()` retourne un snapshot complet : tâches actives, métriques du jour, leads chauds, candidatures en cours.

`lifeos_prioritize()` retourne le top 3 déterministe.

## Étape 3 — Affichage

Format Telegram (skill telegram-output). Structurer ainsi :

### Bonjour Laurent ☀️ — {date}

**Top 3 priorités du jour**
1. [tâche] — [raison]
2. ...
3. ...

**En cours** : N tâches actives

**Leads chauds** : liste des leads Chaud avec dernière action

**Candidatures** : en attente / relances à faire

**Métriques** : abonnés X, vues, leads Malt du jour si dispos

**Recommandation** : 1-2 phrases sur comment démarrer la journée (focus, blockers à résoudre).

## Notes

- Si `lifeos_orchestrate()` est disponible, l'appeler en supplément pour des recommandations contextuelles
- Ne pas appeler `lifeos_standup` + `lifeos_prioritize` séquentiellement — les lancer en parallèle
