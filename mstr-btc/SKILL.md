---
name: mstr-btc
description: Dashboard MSTR/BTC — double stratégie, régime BTC, mNAV, recommandation d'asset, état du cycle, actions.
requires:
  - repo: backtester (à cloner dans /home/agent/backtester si absent)
  - python: yfinance, pandas
---

# Skill : MSTR/BTC Investment Dashboard

## Prérequis

Le repo backtester doit être présent dans `/home/agent/backtester`.
Si absent : `git clone https://github.com/lockey33/backtester /home/agent/backtester`

## Exécution

**Étape 1 — Données + Dashboard** (en parallèle avec étape 2) :
```bash
cd /home/agent/backtester/packages/quant && python -m research.mstr_btc_dashboard 2>/dev/null
```
Le script auto-refresh les CSV BTC et MSTR si périmés (>4h). Parser le JSON retourné.

**Étape 2 — Kill switch scan** (WebSearch, en parallèle avec étape 1) :
Lancer une recherche web pour vérifier les kill switches. Requêtes à exécuter :
1. `WebSearch("MicroStrategy MSTR Saylor Bitcoin sell 2026")` — Saylor/MSTR vend du BTC ?
2. `WebSearch("MicroStrategy SEC investigation lawsuit 2026")` — Action SEC ?
3. `WebSearch("MicroStrategy bankruptcy Chapter 11 debt 2026")` — Problèmes financiers ?
4. `WebSearch("Bitcoin critical vulnerability hack 2026")` — Incident protocol BTC ?

Analyser les résultats et classer chaque kill switch comme :
- **CLEAR** : aucune news inquiétante
- **WATCH** : news ambiguë, à surveiller
- **ALERT** : kill switch potentiellement déclenché → signaler en rouge

## Affichage

Dashboard structuré en français :

### 1. En-tête
```
## Dashboard MSTR/BTC — {date}
```

### 2. Fraîcheur des données
Si `btc_stale` ou `mstr_stale` est true :
```
Données obsolètes (BTC: {btc_last_date}, MSTR: {mstr_last_date})
Rafraîchir : cd /home/agent/backtester/packages/quant/data && python -c "import yfinance as yf; yf.download('BTC-USD', period='max').to_csv('BTC-USD_daily.csv'); yf.download('MSTR', period='max').to_csv('MSTR_1d.csv')"
```

### 3. Stratégie active (depuis `strategy`) — SECTION PRINCIPALE

C'est la section la plus importante. Afficher clairement :
- **Stratégie active** : MSTR_CYCLE ou BTC_KISS
- **Asset recommandé** : MSTR ou BTC
- **Phase BTC** (`btc_phase`) : ACCUMULATION / HOLD / DISTRIBUTION / EXITED
- **Phase MSTR** (`mstr_state.phase`) : ACCUMULATION / HOLD / DISTRIBUTION
- **Raison** du choix (texte explicatif)

**IMPORTANT** : BTC et MSTR ont des exits DIFFÉRENTS :
- BTC = KISS+ (trailing stop, fixed sell 5%, dump all)
- MSTR = mNAV ramp (pas de trailing stop, sell_pct = clip(0.10 × (mNAV - 2.0), 0, 0.35))

Logique de sélection d'asset :
- Bear → MSTR (acheter le levier pas cher)
- Bull + mNAV ≥ 1.5 → MSTR (levier fonctionne)
- Bull + mNAV < 1.5 → BTC (pas de levier MSTR)

### 4. Régime BTC (depuis `btc_regime`)

Tableau : régime (BEAR/BULL), BTC weekly close, EMA 200W weekly, distance %.

### 5. BTC Indicateurs (depuis `btc`)

Tableau : BTC price, SMA 200W (daily), EMA 200W (daily), distance.

### 6. MSTR & mNAV (depuis `mnav`)

Tableau : MSTR price, mNAV, mNAV z-score, BTC holdings, shares outstanding.
Signaler si `fundamentals_date` > 30 jours.

Si `strategy.mstr_state` disponible :
- **mNAV vs anchor** : distance au seuil de vente 2.0x
- **Sell pace estimée** : % estimé de vente si mNAV > 2.0x
- **Phase MSTR** : ACCUMULATION / HOLD / DISTRIBUTION

### 7. Risk Monitors (depuis `risk_monitors`)

**Circuit breaker** (`risk_monitors.circuit_breaker`) :
- `consecutive_days_below` : nombre de jours consécutifs où MSTR < EMA 200D
- `confirm_days` : seuil adaptatif (ajusté à la vol : `round(10 × (0.88 / vol_20d))`)
- `triggered` : true si consecutive_days_below ≥ confirm_days
- `phase_applicable` : **le CB ne s'applique qu'après ≥1 exit mNAV** (distribution)

Affichage :
- Si `triggered` ET `phase_applicable` → **ALERTE ROUGE** : "Circuit breaker DÉCLENCHÉ — {consecutive_days_below}j sous EMA 200D (seuil {confirm_days}j). Action : flatten la position MSTR."
- Si `triggered` ET PAS `phase_applicable` → **Info** : "CB informatif : {consecutive_days_below}j, inactif en accumulation."
- Si pas triggered → "CB OK : {consecutive_days_below}j / {confirm_days}j"

**Volatilité** : `vol_20d` vs `baseline_vol` (0.88)

**Kill switches** (résultats du web scan) :
```
- [CLEAR/WATCH/ALERT] Description — résumé
```

### 8. Cycle actuel — $10K (depuis `current_cycle`)

- **Début du cycle** : `current_cycle.start_date`
- **Position** : valeur BTC, % exposure, cash restant
- **PnL** : performance depuis début du cycle vs Buy & Hold
- **Prochain DCA** : `current_cycle.next_dca_date`

### 9. Simulation KISS+ historique (depuis `kiss_cycle`)

État actuel + performance historique (PnL %, Max drawdown, buys/sells).

### 10. Actions concrètes

Liste numérotée de `actions` (alertes risque, kill switches, timing DCA, buy/sell/hold).

### 11. Paramètres (depuis `params`)

Tableau des seuils DCAParams + mnav_switch_threshold + mnav_sell_anchor.

### 12. Référence : Logique d'investissement

```
**Sélection d'asset** (régime BTC weekly EMA 200W + mNAV)
- Bear → MSTR | Bull + mNAV ≥ 1.5x → MSTR | Bull + mNAV < 1.5x → BTC

**BTC — Exits KISS+** : DCA <30%, Hold 30-100%, Sell 5% >100%, Trailing stop -30%, Dump all

**MSTR — Exits mNAV ramp** : DCA bear, distribution mNAV ≥ 2.0x, CB après ≥1 exit
```

## Questions de suivi

- **"What if distance à X% ?"** → Règles KISS+ BTC : DCA si <30%, hold si 30-100%, sell 5% si >100%
- **"Et pour MSTR ?"** → mNAV ramp, distribution quand mNAV ≥ 2.0x
- **"Backtest complet ?"** → `cd /home/agent/backtester/packages/quant && python research/btc_ma_cycle_backtest.py`
- **"Mettre à jour les données"** → Commande yfinance de refresh
