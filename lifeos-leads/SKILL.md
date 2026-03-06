---
name: lifeos-leads
description: >
  Gestion des leads LinkedIn et candidatures emploi.
  Triggers: "leads", "prospects", "LinkedIn", "candidatures", "jobs", "re-qualifier".
requires:
  - mcp: bridgeai (lifeos_leads, lifeos_leads_qualify, lifeos_candidatures)
---

# Skill : LifeOS Leads & Candidatures

## Leads LinkedIn

### Vue générale
```
lifeos_leads()
```
Retourne tous les leads. Filtrer par statut si demandé : Chaud, Tiede, Froid.

Afficher :
- Leads **Chauds** en priorité avec dernière interaction et prochaine action
- Leads **Tièdes** avec date de dernier contact
- Résumé du pipeline (N chauds / N tièdes / N froids)

### Re-qualification (HIGH RISK)
```
lifeos_leads_qualify()
```
⚠️ Re-qualifie automatiquement les statuts dans Notion. Approbation Telegram requise.

Présenter d'abord les leads concernés et le nouveau statut proposé avant de lancer.

## Candidatures emploi

### Vue générale
```
lifeos_candidatures()
lifeos_candidatures({ active: true })
```
Afficher :
- Candidatures en cours avec statut (En attente, Entretien, Relance nécessaire)
- Relances à faire (dernière action > 7j sans réponse)
- Opportunités à saisir

## Format

Format Telegram (skill telegram-output) :

**Leads chauds** (N)
- [Nom] — [entreprise] — dernière action : [date] → action recommandée

**Pipeline**
Chauds: N | Tièdes: N | Froids: N

**Candidatures actives** (N)
- [Poste] @ [Entreprise] — [statut] — [prochaine action]
