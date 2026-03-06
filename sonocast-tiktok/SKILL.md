---
name: sonocast-tiktok
description: >
  Generate TikTok videos from podcast episodes via Sonocast.
  Triggers: "TikTok", "generate tiktok", "sonocast video", "next video",
  "prochaine vidéo", "podcast to tiktok", "generate video from podcast".
requires:
  - repo: Build-Broadcast (à cloner dans /home/agent/Build-Broadcast si absent)
  - mcp: bridgeai (sonocast_search, sonocast_get_episode, sonocast_process_episode, sonocast_get_episode_insights)
  - system: ffmpeg, node/tsx
---

# Skill : Sonocast → TikTok Video Generator

Projet : `/home/agent/Build-Broadcast`

## Étape 1 — Discover

Demander un sujet à l'utilisateur (ou proposer des thèmes tech/AI/freelance tendance).

Chercher des épisodes via MCP :
```
sonocast_search({ query: "<sujet>", language: "fr" })
```

Privilégier les podcasts **français**. Présenter le top 3-5 résultats avec :
- Titre + podcast
- Durée
- Pourquoi ça ferait un bon TikTok (insight fort, quote percutante, sujet viral)

## Étape 2 — Select & Fetch

Une fois l'épisode choisi :
```
sonocast_get_episode({ episodeId: "<id>" })
```

Si statut non `processed` :
```
sonocast_process_episode({ episodeId: "<id>" })
```
Puis re-fetch avec `sonocast_get_episode`.

Récupérer les insights :
```
sonocast_get_episode_insights({ episodeId: "<id>" })
```

Assembler le JSON `{ status, episode, summaryBullets, chapters, insights, quotes }` et sauvegarder dans `/tmp/episode-<slug>.json`.

## Étape 3 — Generate

```bash
cd /home/agent/Build-Broadcast && npx tsx src/scripts/generate-tiktok.ts /tmp/episode-<slug>.json <flags>
```

### Flags
| Flag | Effet |
|---|---|
| _(aucun)_ | Contenu + slides uniquement, pas d'audio/vidéo |
| `--audio` | TTS système (rapide, gratuit, qualité moyenne) |
| `--audio-elevenlabs` | TTS ElevenLabs (meilleure qualité, payant) |
| `--final` | Alias de `--audio-elevenlabs` |

**Par défaut utiliser `--audio-elevenlabs`** sauf si demande contraire.

Le script :
1. Génère le contenu TikTok via LLM (titre, hook, key points, script TTS, hashtags)
2. Boucle de critique (Haiku note le script, régénère si score < 70)
3. Crée les slides carousel (1080x1920)
4. Génère l'audio TTS avec timestamps
5. Assemble la vidéo finale avec sous-titres ASS via ffmpeg

## Étape 4 — Review

Afficher :
- Chemin de sortie : `output/sonocast-<uuid>/`
- Fichier vidéo : `output/sonocast-<uuid>/final-tiktok.mp4`
- Titre, hook et hashtags

## Notes

- ffmpeg doit être installé dans le container
- Voix ElevenLabs : "Liam - Energetic Social Media Creator"
- Sous-titres word-by-word synchronisés (ElevenLabs timestamps)
