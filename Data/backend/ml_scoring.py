import numpy as np
import pandas as pd
import networkx as nx
from sklearn.ensemble import IsolationForest

def calculate_ml_scores(df: pd.DataFrame, G: nx.MultiDiGraph, accounts: list[str], flags_by_acc: dict, roles_by_acc: dict, xmlt_scores: dict = None) -> dict:
    """
    4-Pillar Scoring System:
    - GAT (35%)
    - LSTM (25%)
    - EIF (20%)
    - Rules (20%)
    Multiplies final sum by role multiplier, issues Decision.
    """
    if not accounts:
        return {}
        
    scores = {}

    # --- 1. EIF (Extended Isolation Forest - 12 features mock) ---
    # We will compute 12 features for the accounts to pass to IsolationForest
    # Features: in_degree, out_degree, vol_in, vol_out, unique_senders, unique_receivers,
    # mean_in_amt, mean_out_amt, max_in_amt, max_out_amt, txn_count, balance_delta
    feature_list = []
    
    # Precompute aggregates using pandas for speed
    events_in = df[["receiver_id", "amount"]].rename(columns={"receiver_id": "account"})
    grp_in = events_in.groupby("account")["amount"].agg(['count', 'sum', 'mean', 'max', 'nunique'])
    
    events_out = df[["sender_id", "amount"]].rename(columns={"sender_id": "account"})
    grp_out = events_out.groupby("account")["amount"].agg(['count', 'sum', 'mean', 'max', 'nunique'])

    for acc in accounts:
        in_d = G.in_degree(acc)
        out_d = G.out_degree(acc)
        
        # Safe access to pandas precomputed stats
        in_counts = grp_in.loc[acc] if acc in grp_in.index else pd.Series([0,0,0,0,0], index=['count', 'sum', 'mean', 'max', 'nunique'])
        out_counts = grp_out.loc[acc] if acc in grp_out.index else pd.Series([0,0,0,0,0], index=['count', 'sum', 'mean', 'max', 'nunique'])
        
        v_in = in_counts['sum']
        v_out = out_counts['sum']
        
        f = [
            in_d, out_d, v_in, v_out,
            in_counts['nunique'], out_counts['nunique'],
            in_counts['mean'], out_counts['mean'],
            in_counts['max'], out_counts['max'],
            in_counts['count'] + out_counts['count'],
            abs(v_in - v_out)
        ]
        # Replace NaNs with 0
        f = [0 if pd.isna(x) else x for x in f]
        feature_list.append(f)

    # Run Isolation Forest on the 12 features
    feature_df = pd.DataFrame(feature_list).fillna(0)
    contamination = 0.05 if len(feature_df) >= 20 else "auto"
    iso = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
    iso.fit(feature_df.values)
    raw_eif_scores = iso.decision_function(feature_df.values)
    
    min_s, max_s = raw_eif_scores.min(), raw_eif_scores.max()
    if max_s - min_s > 0:
        normalized_eif = (max_s - raw_eif_scores) / (max_s - min_s)
    else:
        normalized_eif = np.zeros(len(raw_eif_scores))
        
    eif_scores_100 = np.clip(normalized_eif * 100, 0, 100)

    # --- 2. GAT (Graph Topology Proxy) & LSTM (Burst Timing Proxy) ---
    # For MVP speed, we approximate GAT by eigenvalue/page-rank centrality metrics + cross-edges
    # We approximate LSTM by variance in transaction timestamps
    
    # Precompute PageRank for GAT
    try:
        pr = nx.pagerank(G, alpha=0.85, max_iter=50) # Fallback if takes too long
    except Exception:
        pr = {n: 0.1 for n in G.nodes()}
        
    pr_values = list(pr.values())
    pr_min, pr_max = min(pr_values), max(pr_values) if pr_values else 1
    if pr_max == pr_min: pr_max += 1

    events_df = pd.concat([
        df[["sender_id", "timestamp"]].rename(columns={"sender_id": "account"}),
        df[["receiver_id", "timestamp"]].rename(columns={"receiver_id": "account"})
    ], ignore_index=True)
    events_df.sort_values(["account", "timestamp"], inplace=True)
    grp_ts = events_df.groupby("account")

    for i, acc in enumerate(accounts):
        # EIF score [0-100]
        eif_val = eif_scores_100[i]
        
        # Rules score [0-100] (10 flags, each worth 10 pts)
        flags = flags_by_acc.get(acc, [])
        rules_val = min(100.0, len(flags) * 15.0) # Up to 15 per flag for spread
        
        # GAT score [0-100]
        # Blends PageRank graph centrality with dynamic xMLT progression delta + layering chain memberships
        normalized_pr = (pr.get(acc, 0) - pr_min) / (pr_max - pr_min)
        cycle_bonus = 30 if "F10" in flags else 0 
        
        # Add xMLT score component (scaled to 0-30 max)
        xmlt_val = xmlt_scores.get(acc, {}).get("total_xmlt", 0.0) if xmlt_scores else 0.0
        xmlt_bonus = min(30.0, xmlt_val / 5.0)
        
        # Add layering chain bonus
        layering_bonus = 20 if "layering_chain_member" in flags else 0
        
        gat_val = min(100.0, normalized_pr * 50 + cycle_bonus + xmlt_bonus + layering_bonus)
        
        # LSTM score [0-100]
        # Burst timing: if timestamps are very tightly clustered, it's a burst attack.
        lstm_val = 0
        if acc in grp_ts.groups:
            ts = grp_ts.get_group(acc)["timestamp"].values
            if len(ts) >= 3:
                # Calculate variance in minutes
                diffs = np.diff(ts).astype('timedelta64[m]').astype(int)
                mean_diff = np.mean(diffs)
                # If mean diff is very small (burst), high score
                if mean_diff < 5:
                    lstm_val = 90
                elif mean_diff < 30:
                    lstm_val = 70
                elif mean_diff < 120:
                    lstm_val = 40
                else:
                    lstm_val = 10
            else:
                lstm_val = 20 # Low activity
                
        # Base Weighted Score
        base_score = (gat_val * 0.35) + (lstm_val * 0.25) + (eif_val * 0.20) + (rules_val * 0.20)
        
        # Apply Role Multiplier
        role_info = roles_by_acc.get(acc, {"role": "LEAF", "multiplier": 1.0})
        final_score = base_score * role_info.get("multiplier", 1.0)
        final_score = min(100.0, max(0.0, final_score))
        
        # Decision
        if final_score >= 80:
            decision = "BLOCK"
        elif final_score >= 45:
            decision = "REVIEW"
        else:
            decision = "APPROVE"
            
        scores[acc] = {
            "score": round(final_score, 1),
            "decision": decision,
            "role": role_info.get("role", "LEAF"),
            "components": {
                "GAT": round(gat_val, 1),
                "LSTM": round(lstm_val, 1),
                "EIF": round(eif_val, 1),
                "Rules": round(rules_val, 1)
            }
        }
        
    return scores
