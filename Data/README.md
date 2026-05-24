# 🛡️ MoneyMal — Financial Forensics Engine

> Graph-based money muling detection engine / Financial Crime Detection

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white)
![NetworkX](https://img.shields.io/badge/NetworkX-Graph_Theory-orange)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-GAT_|_LSTM_|_EIF-F7931E)
![Performance](https://img.shields.io/badge/10k_transactions-~5_seconds-brightgreen)

🔗 **Deployment link**
https://money-mal-nxch.vercel.app/

---

## 📋 Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Detection Pipeline](#detection-pipeline)
- [RBI/NPCI Rules Engine](#rbinpci-rules-engine)
- [Account-Type Thresholds](#account-type-thresholds)
- [4-Pillar Scoring & Decisions](#4-pillar-scoring--decisions)
- [Structural Roles](#structural-roles)
- [CSV Format & Column Mapping](#csv-format--column-mapping)
- [Installation & Setup](#installation--setup)
- [Usage Instructions](#usage-instructions)
- [Performance Benchmarks](#performance-benchmarks)
- [Known Limitations](#known-limitations)
- [Team Members](#team-members)

---

## Overview

MoneyMal is an advanced web-based financial forensics engine that processes transaction CSV data and exposes money muling networks through graph analysis and interactive visualization. It integrates a **modern 4-Pillar Machine Learning Pipeline (GAT, LSTM, EIF, Rules)** alongside **RBI/NPCI-compliant fraud detection rules** to identify circular fund routing, smurfing patterns, layered shell networks, and structuring attacks.

It actively assigns structural hierarchy roles (HUB, BRIDGE, MULE, LEAF) to exposed network entities and generates concrete enforcement decisions (BLOCK / REVIEW / APPROVE).

### Key Features

- **Secure Authentication Layer:** Analysts log in to access full forensic context securely.
- **Flexible CSV Ingestion:** Auto-maps column name variants — no manual reformatting needed.
- **Account-Type Pre-Filter:** Separate fraud thresholds for Savings, General, Premium, Business, and Credit Card accounts — runs before ML.
- **Upload CSV** → analysis in ~5 seconds for 10,000 transactions.
- **Interactive network graph** with color-coded risk tiers and structural roles.
- **Multi-Pillar ML Scoring:** 4-pillar architecture (Graph Attention Networks, LSTMs, Extended Isolation Forests, and Rule heuristics).
- **Enforcement Decisions:** Automated BLOCK, REVIEW, or APPROVE verdicts per account.
- **Downloadable JSON report** in hackathon-spec format.
- **Fraud ring summary table** detailing risk scores and hierarchy.
- **Dark "Threat Matrix" UI** with glassmorphism and micro-animations.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Vite 7, vis-network (vis.js), Tailwind CSS 4 |
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **Authentication** | OAuth2 with JWT hashing (bcrypt + python-jose) |
| **Graph Engine** | NetworkX (MultiDiGraph) |
| **ML & AI** | scikit-learn (Isolation Forest), PageRank/Degree Centrality, Burst Timing Analysis |
| **Numerical** | NumPy, Pandas |
| **Fuzzy Mapping** | rapidfuzz |
| **Config** | PyYAML (account thresholds) |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)              │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌────────┐  │
│  │ Login.jsx│  │NetworkGraph  │  │FraudTable│  │Forensic│  │
│  │ Dashboard│  │ Interactive  │  │ Ring     │  │ Card   │  │
│  │ Upload   │  │ Graph        │  │ Summary  │  │ Detail │  │
│  └────┬─────┘  └──────────────┘  └──────────┘  └────────┘  │
│       │  POST /api/analyze (Auth JWT Token Required)        │
├───────┼─────────────────────────────────────────────────────┤
│       ▼           BACKEND (FastAPI - Auth Guarded)          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  DataIngestor — flexible column mapping (rapidfuzz)  │   │
│  │  AccountTypeFilter — per-type threshold pre-filter   │   │
│  │  ForensicsEngine (OOP)                               │   │
│  │                                                      │   │
│  │  1. load_data() ──── MultiDiGraph construction       │   │
│  │  2. detect_cycles() ─ Union-Find bounded DFS         │   │
│  │  3. detect_shells() ─ Passthrough chain walking      │   │
│  │  4. detect_velocity() ─ Burst + 24h window           │   │
│  │  5. detect_smurfing() ─ Fan-in sliding window        │   │
│  │  6. detect_structuring() ─ Band + window scan        │   │
│  │  7. consolidate_rings() ─ Jaccard merge              │   │
│  │  8. calculate_suspicion_scores()                     │   │
│  │     ├── run_all_flags() ─ RBI Rules (injected cycles)│   │
│  │     ├── assign_roles() ─ HUB/BRIDGE/MULE/LEAF        │   │
│  │     └── calculate_ml_scores() ─ 4-pillar scoring     │   │
│  │  9. generate_json() + get_graph_data()               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Detection Pipeline

The engine runs 6 detection stages in sequence before scoring:

| Stage | Method | What It Catches |
|---|---|---|
| **Cycle Detection** | Bounded DFS + Union-Find merge | Circular fund routing (A→B→C→A) |
| **Shell Detection** | Passthrough ratio + chain walking | Layered shell account networks |
| **Velocity Detection** | Two-tier sliding window | Rapid in→out within 1h; 5+ tx/24h |
| **Smurfing Detection** | Fan-in 72h window + soft scoring | Multiple senders funnelling to one hub |
| **Structuring Detection** | Band filter + two-pointer window | Repeated transactions just below reporting limits |
| **Business Immunity** | Payroll/merchant pattern matching | Suppresses legitimate high-volume accounts |

---

## RBI/NPCI Rules Engine

9 active rules (F1–F10, F7 removed — no device data available):

| Flag | Rule | Detection Method |
|---|---|---|
| **F1** | ≥90% of inbound re-transmitted within 2 hours | Vectorized time-window scan |
| **F2** | Dormant account (180+ day gap) suddenly bursts | Real gap detection + burst count |
| **F3** | 50+ small payments (<₹500) from 25+ unique senders | Aggregated groupby count |
| **F4** | Total transaction volume > 10× dataset median × 20 | Volume threshold check |
| **F5** | 4+ outbound transactions within 1 hour of receiving | Per-event sliding window |
| **F6** | Coordinated group — shares identical top-receiver pattern with 3+ accounts | Receiver fingerprint matching |
| **F8** | Low-value account profile with outlier high-value transaction | CV + max/median ratio |
| **F9** | Account < 7 days old with 2+ high-value transactions | First-seen age check |
| **F10** | Part of a detected cycle of length ≥ 4 | Pre-computed from engine cycle sets |

> F10 uses pre-computed cycle sets from the engine — no per-account DFS, making it O(1) per account.

---

## Account-Type Thresholds

Separate fraud thresholds per account type, configurable in `backend/account_thresholds.yaml` without touching code.

| Account Type | Single Tx Limit | Velocity (10 min) | Daily Limit |
|---|---|---|---|
| **SAVINGS** | ₹50,000 | 5 transactions | ₹1,00,000 |
| **GENERAL / CURRENT** | ₹2,00,000 | 10 transactions | ₹5,00,000 |
| **PREMIUM** | ₹10,00,000 | 15 transactions | ₹25,00,000 |
| **BUSINESS** | ₹50,00,000 | 30 transactions | ₹2,00,00,000 |
| **CREDIT_CARD** | 80% of credit limit | 8 tx in 5 min | Credit limit |

Any threshold breach sets `rule_based_fraud = True` on the transaction row and feeds a +25 boost into the Rules pillar score — ensuring breached accounts cannot be suppressed below REVIEW.

To change thresholds, edit `backend/account_thresholds.yaml` directly:
```yaml
SAVINGS:
  high_value_threshold: 50000
  velocity_tx_limit: 5
  daily_limit: 100000
```

---

## 4-Pillar Scoring & Decisions

Each account is scored across four independent pillars, then combined into a final weighted score:

| Pillar | Weight | What It Measures |
|---|---|---|
| **GAT** | 35% | Graph centrality (PageRank / degree) + cross-ring bridge ratio + cycle membership bonus |
| **LSTM** | 25% | Transaction burst timing — dampened for legitimate high-volume accounts |
| **EIF** | 20% | Isolation Forest on 12 behavioural features (degree, volume, variance, balance delta) |
| **Rules** | 20% | RBI flag hits + account-type threshold breach bonus |

Role multipliers (HUB: 1.25×, BRIDGE: 1.15×, MULE: 1.10×, LEAF: 1.0×) amplify the score based on structural position, capped at 1.3× to prevent score inflation.

### Enforcement Matrix

| Combined Score | Verdict | Action |
|---|---|---|
| **0 – 39** | **APPROVE** | Cleared for normal operations |
| **40 – 74** | **REVIEW** | Flagged for manual analyst verification |
| **75 – 100** | **BLOCK** | Immediate system blackout and asset freeze |

---

## Structural Roles

| Role | Visual | Description |
|---|---|---|
| **HUB** | 🟣 Purple | Central aggregator with highest degree in the ring |
| **BRIDGE** | 🟠 Orange | Connects ring members to outside accounts — cross-network relay |
| **MULE** | 🟡 Yellow | Forwarder — has both inbound and outbound, medium degree |
| **LEAF** | 🔵 Blue | Peripheral node — entry/exit point of the network |

---

## CSV Format & Column Mapping

The system automatically maps non-standard column names using fuzzy matching. You do not need to rename your columns manually.

### Canonical columns

| Column | Required | Auto-mapped from |
|---|---|---|
| `transaction_id` | Optional | `txn_id`, `id`, `ref_no`, `trx_id` |
| `sender_id` | Required* | `from_account`, `payer_id`, `originator`, `sender` |
| `receiver_id` | Required* | `to_account`, `payee_id`, `beneficiary`, `destination` |
| `amount` | Required* | `txn_amount`, `transaction_amount`, `amt`, `value` |
| `timestamp` | Required* | `date`, `txn_date`, `created_at`, `datetime` |
| `account_type` | Optional | Used for per-type threshold checks |
| `credit_limit` | Optional | Used for CREDIT_CARD accounts |

> *If `sender_id` or `receiver_id` are absent, surrogate row-index IDs are used as a fallback so graph features can still be computed.

Timestamp formats supported: ISO 8601, `DD-MM-YYYY`, `MM/DD/YYYY`, Unix epoch (seconds and milliseconds), and more.

---

## Installation & Setup

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm

### Backend

```bash
cd backend
pip install fastapi uvicorn python-multipart pandas networkx scikit-learn bcrypt python-jose[cryptography] passlib rapidfuzz pyyaml
python -m uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Login Credentials

| Username | Password | Role |
|---|---|---|
| `admin` | `Admin2026!` | Full access |
| `analyst` | `Analyst2026!` | Full access |
| `viewer` | `Viewer2026!` | Read-only (ML details hidden) |

---

## Usage Instructions

1. **Open** `http://localhost:5173` in your browser (backend must be running on port 8000).
2. **Log In** using analyst or admin credentials.
3. **Upload** your transaction CSV — column names are auto-mapped.
4. **Review the mapping preview** shown before analysis — confirm columns were detected correctly.
5. **Launch Analysis** and wait ~5 seconds for results.
6. **Analyze & Investigate:**
   - Review **Enforcement Decisions** (BLOCK/REVIEW/APPROVE) on the KPI dashboard.
   - Inspect the **Network graph** to trace relationships across HUB, BRIDGE, MULE, and LEAF nodes.
   - Examine the **Suspicious Accounts** table to see individual scores split across the 4 ML pillars.
   - Check **flag_reason** per account to see whether a rule breach or ML anomaly score drove the decision.
7. **Download** the generated JSON forensics report.

---

## Performance Benchmarks

Tested on a standard laptop (no GPU):

| Dataset Size | Processing Time |
|---|---|
| 1,000 transactions | ~1 second |
| 10,000 transactions | ~4–5 seconds |
| 50,000 transactions | ~25–35 seconds |
| 100,000 transactions | ~90–120 seconds |

> PageRank is automatically skipped for graphs with > 8,000 nodes and replaced with degree centrality to maintain speed on large datasets.

---

## Known Limitations

1. **No persistence** — results are computed per-request and not stored in a database.
2. **Single-file upload** — does not support multi-file batch processing.
3. **Graph rendering performance** — vis.js may lag with 1,000+ nodes. For massive datasets, consider server-side node filtering before rendering.
4. **GAT/LSTM are proxy implementations** — true Graph Attention Networks and LSTM temporal models are approximated via PageRank centrality and inter-transaction timing variance respectively. Full deep learning implementations would require GPU infrastructure.
5. **No device/IP signal** — F7 (mobile flagging) has been removed as no real device data is present in CSV uploads. F6 uses a receiver-fingerprint proxy instead.

---

## Team Members

Manas Prashant,
Akshay N Bhat,
Amogh Basavaraj

---

## License

MIT
