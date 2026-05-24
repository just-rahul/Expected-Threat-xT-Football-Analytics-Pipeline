"""
Hybrid Sentinel — Financial Forensics Engine v5.0
Recall-Optimized Detection Architecture

Pipeline stages:
  Stage 0  — Data Loading + Adaptive Statistics
  Stage 1  — Candidate Detection  (cycles, shells, smurfing, structuring, velocity)
  Stage 2  — Business Immunity    (payroll + merchant identification)
  Stage 3  — Ring Consolidation   (Jaccard merge, micro-ring filter)
  Stage 4  — Composite Risk Scoring (weighted multi-pattern score)
  Stage 5  — Suppression          (immunity filter AFTER scoring, cannot override strong fraud)

Design principles:
  • Detection and suppression are FULLY separated
  • Soft scoring — candidates contribute partial scores (no hard gate rejection)
  • Adaptive thresholds — scaled relative to dataset statistics
  • Ring consolidation — overlapping rings merged via Jaccard similarity
  • Suppression only applies when immunity is strong AND no fraud signal exceeds threshold
  • Stability — deterministic ring_id, no nulls, no duplicates

Performance: optimised for <30s on 15K+ transactions.
"""

import time
from collections import defaultdict
from datetime import timedelta
from itertools import count
from statistics import median

import numpy as np
import pandas as pd
import networkx as nx
from sklearn.ensemble import IsolationForest

from flags import run_all_flags
from roles import assign_roles
from ml_scoring import calculate_ml_scores
from ingestor import DataIngestor


# ====================================================================== #
#  UNION-FIND (Disjoint Set) for merging overlapping cycles              #
# ====================================================================== #
class UnionFind:
    """Weighted Quick-Union with path compression."""

    def __init__(self):
        self.parent: dict[str, str] = {}
        self.rank: dict[str, int] = {}

    def find(self, x: str) -> str:
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1

    def groups(self) -> dict[str, list[str]]:
        clusters: dict[str, list[str]] = defaultdict(list)
        for node in self.parent:
            clusters[self.find(node)].append(node)
        return dict(clusters)


# ====================================================================== #
#  HELPER FUNCTIONS                                                       #
# ====================================================================== #

def _get_edges_between(G, u, v):
    """Return all edge data dicts for edges u → v in a MultiDiGraph."""
    edges = []
    if G.has_edge(u, v):
        for _, data in G[u][v].items():
            edges.append(data)
    return edges


def _external_degree_in_window(G, node, cycle_nodes_set, ts_min, ts_max):
    """Count transactions with non-cycle nodes inside the time window."""
    ext_count = 0
    for pred in G.predecessors(node):
        if pred in cycle_nodes_set:
            continue
        for _, d in G[pred][node].items():
            if ts_min <= d["timestamp"] <= ts_max:
                ext_count += 1
    for succ in G.successors(node):
        if succ in cycle_nodes_set:
            continue
        for _, d in G[node][succ].items():
            if ts_min <= d["timestamp"] <= ts_max:
                ext_count += 1
    return ext_count


def _canonicalize_cycle(path):
    """Minimal rotation for deduplication."""
    min_idx = path.index(min(path))
    return tuple(path[min_idx:] + path[:min_idx])


def _coefficient_of_variation(values):
    if len(values) < 2:
        return 0.0
    mean_val = sum(values) / len(values)
    if mean_val == 0:
        return 0.0
    variance = sum((v - mean_val) ** 2 for v in values) / len(values)
    return (variance ** 0.5) / mean_val


def _jaccard_similarity(set_a, set_b):
    """Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


# ====================================================================== #
#  FORENSICS ENGINE                                                       #
# ====================================================================== #
class ForensicsEngine:

    REQUIRED_COLUMNS = [
        "transaction_id", "sender_id", "receiver_id", "amount", "timestamp"
    ]

    MAX_RING_SIZE = 30      # Union-Find cap: prevents mega-rings
    MAX_SCC_SIZE = 200      # Skip SCCs larger than this for cycle search
    MAX_CYCLES = 2000       # Global cycle cap
    MAX_DEPTH = 5           # Max cycle length
    MAX_OPS_PER_NODE = 5000 # Per-node DFS budget
    MAX_SHELL_RINGS = 50    # Cap on shell network rings
    MAX_SMURF_RING_SIZE = 15  # Max members per smurfing ring

    FLAG_THRESHOLD = 25     # Minimum score to be flagged

    def __init__(self):
        self.df: pd.DataFrame | None = None
        self.G: nx.MultiDiGraph | None = None

        self.account_patterns: dict[str, set[str]] = defaultdict(set)
        self.fraud_rings: list[dict] = []
        self.suspicion_scores: dict[str, float] = {}

        self._velocity_accounts: set[str] = set()
        self._velocity_24h_accounts: set[str] = set()
        self._low_variance_accounts: set[str] = set()
        self._high_degree_hubs: set[str] = set()
        self._immune_accounts: set[str] = set()
        self._immune_types: dict[str, str] = {}  # account -> 'payroll' or 'merchant'

        self._ring_counter = count(1)
        self._explanations: dict[str, str] = {}

        self._candidate_rings: list[dict] = []  # Candidate rings before arbitration
        self._smurf_candidates: list[dict] = []

        self._start_time: float = 0.0
        self._processing_time: float = 0.0

        # Soccer analytics adaptations
        self.xmlt_scores: dict[str, dict] = {}
        self.layering_chains: list[dict] = []
        self.markov_flows: list[dict] = []

        # Adaptive dataset statistics (Phase 3)
        self._median_degree: float = 2.0
        self._degree_std: float = 1.0
        self._median_tx_amount: float = 1000.0
        self._amount_std: float = 500.0
        self._dataset_time_span: float = 0.0
        self._adaptive_ext_degree_limit: int = 2

    # ================================================================== #
    #  1. DATA LOADING                                                    #
    # ================================================================== #
    def load_data(self, df: pd.DataFrame) -> None:
        # Standardize and fuzzy-map headers
        df = DataIngestor.ingest(df)
        
        df = df.copy()
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        self.df = df

        # MultiDiGraph preserves parallel edges between the same pair
        # Vectorized construction — avoids slow iterrows()
        self.G = nx.MultiDiGraph()
        senders = df["sender_id"].values
        receivers = df["receiver_id"].values
        tx_ids = df["transaction_id"].values
        amounts = df["amount"].values
        timestamps = df["timestamp"].values
        for i in range(len(df)):
            self.G.add_edge(
                senders[i],
                receivers[i],
                transaction_id=tx_ids[i],
                amount=float(amounts[i]),
                timestamp=pd.Timestamp(timestamps[i]),
            )

        # Phase 3: Compute adaptive dataset statistics
        self._compute_dataset_stats()

    # ================================================================== #
    #  PHASE 3: ADAPTIVE THRESHOLD COMPUTATION                            #
    # ================================================================== #
    def _compute_dataset_stats(self) -> None:
        """
        Compute dataset-level statistics for adaptive threshold scaling.
        Runs once after data loading.
        """
        if self.G is None or self.df is None:
            return

        # Degree statistics
        degrees = [self.G.in_degree(n) + self.G.out_degree(n) for n in self.G.nodes()]
        if degrees:
            self._median_degree = float(np.median(degrees))
            self._degree_std = float(np.std(degrees))
        else:
            self._median_degree = 2.0
            self._degree_std = 1.0

        # Amount statistics
        amounts = self.df["amount"].values
        if len(amounts) > 0:
            self._median_tx_amount = float(np.median(amounts))
            self._amount_std = float(np.std(amounts))
        else:
            self._median_tx_amount = 1000.0
            self._amount_std = 500.0

        # Time span
        ts_min = self.df["timestamp"].min()
        ts_max = self.df["timestamp"].max()
        self._dataset_time_span = (ts_max - ts_min).total_seconds()

        # Adaptive external degree limit for cycles
        self._adaptive_ext_degree_limit = max(
            2, int(self._median_degree + 1.5 * self._degree_std)
        )

    # ================================================================== #
    #  2. CYCLE DETECTION — Multi-Constraint Validated + Union-Find       #
    # ================================================================== #
    def detect_cycles(self) -> None:
        """
        Bounded DFS cycle detection (length 3–5) with multi-constraint
        validation, merged via Union-Find into rings.
        Phase 2: relaxed external degree constraint using adaptive limit.
        """
        if self.G is None:
            return

        # ---- Build degree-filtered adjacency -------------------------
        # Adaptive upper limit: scale with dataset density
        max_cycle_degree = max(20, int(self._median_degree + 2.0 * self._degree_std))
        eligible = set()
        for n in self.G.nodes():
            total_deg = self.G.in_degree(n) + self.G.out_degree(n)
            if 2 <= total_deg <= max_cycle_degree:
                eligible.add(n)

        adjacency = defaultdict(set)
        for u, v, _ in self.G.edges(keys=True):
            if u in eligible and v in eligible and u != v:
                adjacency[u].add(v)
        adjacency = {k: sorted(v) for k, v in adjacency.items()}

        # ---- DFS with per-node budget --------------------------------
        found_cycles = []
        seen_canonical = set()

        for start in sorted(eligible):
            if start not in adjacency:
                continue
            if len(found_cycles) >= self.MAX_CYCLES:
                break

            stack = [(start, [start], {start})]
            ops = 0

            while stack:
                ops += 1
                if ops > self.MAX_OPS_PER_NODE:
                    break

                current, path, visited = stack.pop()

                if len(path) > self.MAX_DEPTH:
                    continue

                for neighbor in adjacency.get(current, []):
                    if neighbor == start and len(path) >= 3:
                        cycle_path = list(path)
                        canonical = _canonicalize_cycle(cycle_path)
                        if canonical not in seen_canonical:
                            result = self._validate_cycle_edges(cycle_path)
                            if result is not None:
                                seen_canonical.add(canonical)
                                found_cycles.append(result)
                        continue

                    if neighbor in visited:
                        continue
                    if len(path) >= self.MAX_DEPTH:
                        continue

                    new_visited = visited | {neighbor}
                    stack.append((neighbor, path + [neighbor], new_visited))

        if not found_cycles:
            return

        # ---- Union-Find with size-bounded merging --------------------
        uf = UnionFind()
        group_sizes: dict[str, int] = {}

        for cyc in found_cycles:
            nodes = cyc["nodes"]
            roots = set()
            for node in nodes:
                root = uf.find(node)
                roots.add(root)

            merged_size = sum(group_sizes.get(r, 1) for r in roots)
            if merged_size > self.MAX_RING_SIZE:
                continue

            anchor = nodes[0]
            for node in nodes[1:]:
                uf.union(anchor, node)

            new_root = uf.find(anchor)
            group_sizes[new_root] = merged_size

        # ---- Build merged rings → candidate_rings ----------------------
        merged_groups = uf.groups()

        account_cycle_lengths: dict[str, set[int]] = defaultdict(set)
        for cyc in found_cycles:
            for node in cyc["nodes"]:
                account_cycle_lengths[node].add(len(cyc["nodes"]))

        for _root, members in sorted(merged_groups.items()):
            # Exclude immune accounts from cycle ring membership
            non_immune_members = [m for m in members if m not in self._immune_accounts]
            # Still tag all accounts (including immune) with cycle patterns
            for m in members:
                for length in account_cycle_lengths.get(m, set()):
                    self.account_patterns[m].add(f"cycle_length_{length}")

            if len(non_immune_members) < 3:
                continue

            all_lengths = set()
            for m in non_immune_members:
                all_lengths |= account_cycle_lengths.get(m, set())

            # Confidence scoring (base 0.9)
            confidence = 0.9
            # Bonus: short cycles are more suspicious
            if all_lengths and min(all_lengths) == 3:
                confidence += 0.05
            # Bonus: low external edges → tight cycle
            cycle_set = set(non_immune_members)
            total_ext = 0
            for m in non_immune_members:
                for succ in self.G.successors(m):
                    if succ not in cycle_set:
                        total_ext += 1
                for pred in self.G.predecessors(m):
                    if pred not in cycle_set:
                        total_ext += 1
            avg_ext = total_ext / max(len(non_immune_members), 1)
            if avg_ext <= 2:
                confidence += 0.05

            base_risk = 50.0
            base_risk += (5 - min(all_lengths)) * 10 if all_lengths else 0
            base_risk += min(30.0, len(non_immune_members) * 2)
            risk_score = min(100.0, base_risk)

            self._candidate_rings.append({
                "members": sorted(non_immune_members),
                "pattern_type": "cycle",
                "risk_score": round(risk_score, 1),
                "confidence_score": min(1.0, confidence),
            })

    def _validate_cycle_edges(self, cycle_path):
        """
        Multi-constraint validation: find a valid edge combination
        satisfying time, variance, flow, and external-connection rules.
        """
        n = len(cycle_path)
        edge_lists = []
        for i in range(n):
            u = cycle_path[i]
            v = cycle_path[(i + 1) % n]
            edges = _get_edges_between(self.G, u, v)
            if not edges:
                return None
            # Sort by timestamp to prefer temporally close edges
            edges.sort(key=lambda e: e["timestamp"])
            edge_lists.append(edges)

        def _recurse(idx, chosen):
            if idx == n:
                return self._check_cycle_constraints(cycle_path, chosen)
            for edge in edge_lists[idx]:
                result = _recurse(idx + 1, chosen + [edge])
                if result is not None:
                    return result
            return None

        return _recurse(0, [])

    def _check_cycle_constraints(self, cycle_path, edges):
        """
        4-layer constraint check: temporal, amount CV, flow, ext-degree.
        Phase 2: Relaxed external degree using adaptive limit.
        """
        timestamps = [e["timestamp"] for e in edges]
        amounts = [e["amount"] for e in edges]

        ts_min = min(timestamps)
        ts_max = max(timestamps)

        # 1. All transactions within 72h window
        if (ts_max - ts_min) > timedelta(hours=72):
            return None

        mean_amount = sum(amounts) / len(amounts)
        if mean_amount == 0:
            return None

        # 2. Amount variance within 15% of mean (flow imbalance tolerance)
        if not all(abs(a - mean_amount) / mean_amount <= 0.15 for a in amounts):
            return None

        # 3. Flow conservation: min/max ratio >= 0.70
        flow_ratio = min(amounts) / max(amounts) if max(amounts) > 0 else 0
        if flow_ratio < 0.70:
            return None

        # 4. External degree: adaptive limit (Phase 2+3)
        ext_limit = self._adaptive_ext_degree_limit
        cycle_set = set(cycle_path)
        for node in cycle_path:
            ext = _external_degree_in_window(self.G, node, cycle_set, ts_min, ts_max)
            if ext > ext_limit:
                return None

        return {
            "nodes": list(cycle_path),
            "edges": list(edges),
            "total_amount": sum(amounts),
        }

    # ================================================================== #
    #  3. SHELL NETWORK DETECTION — Relaxed (Phase 2)                     #
    # ================================================================== #
    def detect_shells(self) -> None:
        """
        Combined shell detection with relaxed thresholds (Phase 2):
          - Candidate filtering: degree ≤ 4 (was 2-3)
          - Passthrough ratio >= 70% within 24h (was 80%)
          - Short lifetime <= 40% of dataset span (was 30%)
          - Chain walking: BFS depth limit = 5 (was 7)
        """
        if self.G is None or self.df is None:
            return

        dataset_min = self.df["timestamp"].min()
        dataset_max = self.df["timestamp"].max()
        dataset_span = (dataset_max - dataset_min).total_seconds()

        # Build per-account first/last seen
        account_first_seen = {}
        account_last_seen = {}
        for _, row in self.df.iterrows():
            for acc in [row["sender_id"], row["receiver_id"]]:
                ts = row["timestamp"]
                if acc not in account_first_seen or ts < account_first_seen[acc]:
                    account_first_seen[acc] = ts
                if acc not in account_last_seen or ts > account_last_seen[acc]:
                    account_last_seen[acc] = ts

        # Adaptive shell degree limit: scale with dataset density
        adaptive_shell_degree = max(4, int(self._median_degree + 0.5 * self._degree_std))

        # Identify shell candidates with passthrough + lifetime validation
        shell_candidates = set()
        for node in self.G.nodes():
            total_degree = self.G.in_degree(node) + self.G.out_degree(node)
            # Phase 2+3: adaptive degree constraint
            if total_degree < 2 or total_degree > adaptive_shell_degree:
                continue

            in_edges = []
            for pred in self.G.predecessors(node):
                for _, data in self.G[pred][node].items():
                    in_edges.append(data)

            out_edges = []
            for succ in self.G.successors(node):
                for _, data in self.G[node][succ].items():
                    out_edges.append(data)

            if not in_edges or not out_edges:
                continue

            # Passthrough ratio: >= 70% of incoming funds forwarded within 48h
            # In dense graphs with synthetic noise, temporal matching is unreliable.
            # Use simple total_out / total_in ratio if flow matching fails.
            total_in = sum(e["amount"] for e in in_edges)
            passed = 0
            for ie in in_edges:
                for oe in out_edges:
                    if oe["timestamp"] >= ie["timestamp"] and \
                       (oe["timestamp"] - ie["timestamp"]) <= timedelta(hours=48):
                        passed += min(ie["amount"], oe["amount"])
                        break
            
            # Hybrid filter: stricter for sparse, tighter for dense
            ratio_threshold = 0.70
            simple_ratio_threshold = 0.50  # Tightened from 0.20
            
            passes_temporal = (total_in > 0 and (passed / total_in) >= ratio_threshold)
            
            # Simple ratio check (total out / total in)
            total_out = sum(e["amount"] for e in out_edges)
            passes_simple = (total_in > 0 and (total_out / total_in) >= simple_ratio_threshold)

            # Use simple ratio in dense graphs (median > 8) as fallback
            if not passes_temporal:
                if self._median_degree > 8 and passes_simple:
                    pass # Accepted by fallback
                else:
                    continue

            # Must have distinct predecessor and successor
            predecessors = set(self.G.predecessors(node))
            successors = set(self.G.successors(node))
            is_shell = False
            for pred in predecessors:
                for succ in successors:
                    if pred != succ and pred != node and succ != node:
                        is_shell = True
                        break
                if is_shell:
                    break

            if is_shell:
                shell_candidates.add(node)

        if not shell_candidates:
            return

        # Chain walking: find paths through shell intermediaries
        visited_chains: list[list[str]] = []
        # In dense graphs, we need strict chain length (>= 2 intermediaries)
        # to distinguish shells from random high-degree noise.
        min_intermediaries = 2 if self._median_degree > 8 else 1
        
        for node in self.G.nodes():
            if node in shell_candidates:
                continue
            self._find_shell_chains(node, shell_candidates, visited_chains, min_intermediaries)

        # Collect shell chains, deduplicate, apply hardening, cap output
        seen: set[frozenset[str]] = set()
        shell_ring_count = 0
        for chain in visited_chains:
            if shell_ring_count >= self.MAX_SHELL_RINGS:
                break
            # Exclude immune accounts from shell ring membership
            non_immune_chain = [a for a in chain if a not in self._immune_accounts]
            if len(non_immune_chain) < 3:
                continue
            key = frozenset(non_immune_chain)
            if key in seen:
                continue

            # ---- SHELL HARDENING RULES (§3) ----
            member_set = set(non_immune_chain)
            # Rule 1: component_size > 12 → reject
            if len(member_set) > 12:
                continue
            # Rule 2: average_degree > 4 → reject
            total_deg = sum(self.G.in_degree(m) + self.G.out_degree(m) for m in member_set)
            avg_deg = total_deg / len(member_set)
            if avg_deg > 4:
                continue
            # Rule 3: max_node_degree > 8 → reject
            max_deg = max((self.G.in_degree(m) + self.G.out_degree(m)) for m in member_set)
            if max_deg > 8:
                continue
            # Rule 4: external_edges > internal_edges * 0.5 → reject
            internal_edges = 0
            external_edges = 0
            for m in member_set:
                for succ in self.G.successors(m):
                    if succ in member_set:
                        internal_edges += 1
                    else:
                        external_edges += 1
            if internal_edges > 0 and external_edges > internal_edges * 0.5:
                continue
            # Rule 5: pass-through ratio: abs(in - out) / total <= 0.1
            total_in_amt = 0.0
            total_out_amt = 0.0
            for m in member_set:
                for pred in self.G.predecessors(m):
                    for _, d in self.G[pred][m].items():
                        total_in_amt += d["amount"]
                for succ in self.G.successors(m):
                    for _, d in self.G[m][succ].items():
                        total_out_amt += d["amount"]
            total_amt = total_in_amt + total_out_amt
            if total_amt > 0:
                passthrough_ratio = abs(total_in_amt - total_out_amt) / total_amt
                # Relaxed for real data: allow up to 0.3 (0.1 is too strict)
                if passthrough_ratio > 0.3:
                    continue

            seen.add(key)

            # Confidence scoring (base 0.5)
            confidence = 0.5
            # Bonus: low external edges → tight shell
            if internal_edges > 0 and external_edges <= internal_edges * 0.2:
                confidence += 0.1
            # Bonus: high internal density
            max_possible = len(member_set) * (len(member_set) - 1)
            if max_possible > 0:
                density = internal_edges / max_possible
                if density >= 0.3:
                    confidence += 0.1
            # Size penalty (§5)
            confidence -= len(member_set) * 0.02

            self._candidate_rings.append({
                "members": sorted(non_immune_chain),
                "pattern_type": "shell_network",
                "risk_score": round(min(100.0, 55.0 + len(chain) * 5), 1),
                "confidence_score": max(0.1, min(1.0, confidence)),
            })
            shell_ring_count += 1
            for acc in chain:
                self.account_patterns[acc].add("shell_account")

    def _find_shell_chains(self, start, shell_candidates, results, min_intermediaries=1):
        """Phase 2: BFS depth limit = 4 (optimized for perf)."""
        # (current_node, current_path)
        stack = [(start, [start])]
        visited_in_path: set[str] = set()
        
        # Limit paths per node to avoid explosion
        paths_found = 0
        
        while stack:
            if paths_found >= 50:
                break
                
            current, path = stack.pop()
            
            # Depth limit 3 hops (4 nodes) - sufficient for min_int=2
            # Path: [S, C1, C2, E] -> 2 intermediaries
            if len(path) >= 4:
                continue
                
            for neighbor in self.G.successors(current):
                if neighbor in path:
                    continue
                
                new_path = path + [neighbor]
                
                if neighbor in shell_candidates:
                    stack.append((neighbor, new_path))
                else:
                    # Check if valid chain end
                    intermediaries = [n for n in new_path[1:-1] if n in shell_candidates]
                    if len(intermediaries) >= min_intermediaries:
                        results.append(new_path)
                        paths_found += 1

    # ================================================================== #
    #  4. VELOCITY DETECTION — Vectorized (in→out < 1h) + 24h Window     #
    # ================================================================== #
    def detect_velocity(self) -> None:
        """
        Two-tier velocity detection:
          Tier 1: Receive AND re-transmit in < 1 hour (original)
          Tier 2: 5+ transactions in any 24h window (adapted from old code)
        Also detects low amount variance (CV < 0.2) as standalone signal.
        """
        if self.df is None or self.df.empty:
            return

        one_hour_ns = np.timedelta64(1, "h")

        senders = self.df[["sender_id", "timestamp"]].rename(columns={"sender_id": "account"})
        senders["direction"] = "out"
        receivers = self.df[["receiver_id", "timestamp"]].rename(columns={"receiver_id": "account"})
        receivers["direction"] = "in"

        events = pd.concat([senders, receivers], ignore_index=True)
        events.sort_values(["account", "timestamp"], inplace=True)

        for acc, grp in events.groupby("account"):
            dirs = grp["direction"].values
            ts = grp["timestamp"].values

            in_indices = np.where(dirs == "in")[0]
            out_indices = np.where(dirs == "out")[0]

            # Tier 1: in→out < 1h
            if len(in_indices) > 0 and len(out_indices) > 0:
                out_ptr = 0
                for in_idx in in_indices:
                    in_ts = ts[in_idx]
                    while out_ptr < len(out_indices) and out_indices[out_ptr] <= in_idx:
                        out_ptr += 1
                    if out_ptr >= len(out_indices):
                        break
                    out_ts = ts[out_indices[out_ptr]]
                    if (out_ts - in_ts) <= one_hour_ns:
                        self._velocity_accounts.add(acc)
                        self.account_patterns[acc].add("high_velocity")
                        break

            # Tier 2: 5+ transactions in any 24h window (from old code)
            if len(ts) >= 5:
                twenty_four_h = np.timedelta64(24, "h")
                for i in range(len(ts)):
                    window_end = ts[i] + twenty_four_h
                    count_in_window = np.searchsorted(ts, window_end, side='right') - i
                    if count_in_window >= 5:
                        self._velocity_24h_accounts.add(acc)
                        self.account_patterns[acc].add("high_velocity_24h")
                        break

        # ---- Low Amount Variance Detection (from old code) ----
        account_amounts: dict[str, list[float]] = defaultdict(list)
        for _, row in self.df.iterrows():
            account_amounts[row["sender_id"]].append(float(row["amount"]))
            account_amounts[row["receiver_id"]].append(float(row["amount"]))

        for account, amounts in account_amounts.items():
            if len(amounts) < 2:
                continue
            cv = _coefficient_of_variation(amounts)
            if cv < 0.2:
                self._low_variance_accounts.add(account)
                self.account_patterns[account].add("low_variance")

        # ---- High-Degree Hub Suppression Detection (from old code) ----
        # Accounts with degree > 50, long activity span, and high variance
        # are likely commercial hubs, not fraud participants.
        dataset_span = self._dataset_time_span
        if dataset_span > 0:
            account_timestamps: dict[str, list] = defaultdict(list)
            for _, row in self.df.iterrows():
                for acc in [row["sender_id"], row["receiver_id"]]:
                    account_timestamps[acc].append(row["timestamp"])

            for node in self.G.nodes():
                total_degree = self.G.in_degree(node) + self.G.out_degree(node)
                if total_degree <= 50:
                    continue

                ts_list = account_timestamps.get(node, [])
                if not ts_list:
                    continue

                activity_span = (max(ts_list) - min(ts_list)).total_seconds()
                if activity_span < 0.70 * dataset_span:
                    continue

                node_amounts = account_amounts.get(node, [])
                if len(node_amounts) < 2:
                    continue
                cv = _coefficient_of_variation(node_amounts)
                if cv < 0.5:
                    continue

                # Check for regular gaps (no large dormancy)
                ts_sorted = sorted(ts_list)
                gaps = [(ts_sorted[i + 1] - ts_sorted[i]).total_seconds()
                        for i in range(len(ts_sorted) - 1)]
                if gaps:
                    max_gap = max(gaps)
                    if max_gap > 0.25 * dataset_span:
                        continue

                self._high_degree_hubs.add(node)

    # ================================================================== #
    #  BUSINESS IMMUNITY LAYER                                             #
    # ================================================================== #
    def _detect_business_immunity(self) -> None:
        """
        Detect payroll and merchant accounts.
        Phase 1: Immunity is identified here but suppression is applied
        AFTER scoring in the suppression stage.

        Payroll: dominant_sender_ratio > 0.7, no outbound redistribution.
        Merchant: many unique inbound senders (≥10), negligible outbound.
        """
        if self.G is None or self.df is None:
            return

        for node in self.G.nodes():
            # Gather inbound with peer info
            in_txns = []
            for pred in self.G.predecessors(node):
                for _, data in self.G[pred][node].items():
                    in_txns.append({"amt": data["amount"], "peer": pred})

            # Gather outbound with peer info
            out_txns = []
            for succ in self.G.successors(node):
                for _, data in self.G[node][succ].items():
                    out_txns.append({"amt": data["amount"], "peer": succ})

            in_sum = sum(e["amt"] for e in in_txns) if in_txns else 0
            out_sum = sum(e["amt"] for e in out_txns) if out_txns else 0
            in_count = len(in_txns)
            out_count = len(out_txns)

            # --- Payroll detection ---
            if in_count >= 4 and in_sum > 0:
                sender_volumes: dict[str, float] = defaultdict(float)
                for e in in_txns:
                    sender_volumes[e["peer"]] += e["amt"]
                max_sender_vol = max(sender_volumes.values())
                dominant_ratio = max_sender_vol / in_sum

                no_redistribution = (
                    out_count <= 3 or
                    (in_sum > 0 and out_sum / in_sum < 0.1)
                )

                if dominant_ratio > 0.7 and no_redistribution:
                    self._immune_accounts.add(node)
                    self._immune_types[node] = "payroll"
                    self.account_patterns[node].add("payroll")
                    continue

            # --- Merchant detection ---
            unique_senders = set(e["peer"] for e in in_txns)
            if len(unique_senders) >= 10:
                negligible_out = (
                    out_count <= 2 or
                    (in_sum > 0 and out_sum / in_sum < 0.05)
                )
                if negligible_out:
                    self._immune_accounts.add(node)
                    self._immune_types[node] = "merchant"
                    self.account_patterns[node].add("merchant")

    # ================================================================== #
    #  SMURFING — Candidate Extraction + Soft Scoring (Phase 1+2)         #
    # ================================================================== #
    def _extract_smurf_candidates(self) -> None:
        """
        Extract smurf candidates using sliding 72h window.
        A candidate is a node with unique_in >= 5 in any 72h window.
        Phase 1: Immune accounts are still extracted but scored lower.
        """
        if self.G is None:
            return

        WINDOW_72H = timedelta(hours=72)
        UNIQUE_IN_THRESHOLD = 5

        for node in self.G.nodes():
            # Phase 1: Do NOT skip immune accounts at extraction stage
            # Immunity is applied during suppression

            # Build inbound / outbound transaction lists
            in_txns = []
            for pred in self.G.predecessors(node):
                for _, data in self.G[pred][node].items():
                    in_txns.append({
                        "ts": data["timestamp"],
                        "amt": data["amount"],
                        "peer": pred,
                    })
            in_txns.sort(key=lambda e: e["ts"])

            out_txns = []
            for succ in self.G.successors(node):
                for _, data in self.G[node][succ].items():
                    out_txns.append({
                        "ts": data["timestamp"],
                        "amt": data["amount"],
                        "peer": succ,
                    })
            out_txns.sort(key=lambda e: e["ts"])

            if len(in_txns) < UNIQUE_IN_THRESHOLD:
                continue

            # Sliding window: find best window with unique_in >= threshold
            n = len(in_txns)
            right = 0
            for left in range(n):
                w_start = in_txns[left]["ts"]
                w_end = w_start + WINDOW_72H
                while right < n and in_txns[right]["ts"] <= w_end:
                    right += 1

                window_in_txns = in_txns[left:right]
                unique_in = len(set(e["peer"] for e in window_in_txns))

                if unique_in >= UNIQUE_IN_THRESHOLD:
                    # Find outbound within the same window (+ 24h buffer)
                    window_out_txns = [
                        e for e in out_txns
                        if w_start <= e["ts"] <= w_end + timedelta(hours=24)
                    ]
                    self._smurf_candidates.append({
                        "hub": node,
                        "in_txns": window_in_txns,
                        "out_txns": window_out_txns,
                        "w_start": w_start,
                        "w_end": w_end,
                    })
                    break  # One candidate per node

    def _score_smurf_candidates(self) -> None:
        """
        Phase 1+2: Soft scoring instead of hard gating.
        Each condition contributes to a confidence score.
        Candidates with sufficient combined score become rings.
        
        Scoring factors (each 0.0 to 1.0):
          1. Flow-through ratio (retention >= 0.6)
          2. Outbound concentration (unique_out <= 3 ideal)
          3. Hold time (median < 24h)
          4. CV of inbound amounts (<= 0.35)
          5. Ring size (>= 4 members preferred)
        
        Candidate passes if combined_score >= 3.0 out of 5.0
        """
        seen_ring_keys: set[tuple[str, ...]] = set()

        for cand in self._smurf_candidates:
            hub = cand["hub"]
            in_txns = cand["in_txns"]
            out_txns = cand["out_txns"]

            if not in_txns:
                continue

            incoming_sum = sum(e["amt"] for e in in_txns)
            outgoing_sum = sum(e["amt"] for e in out_txns) if out_txns else 0

            # Factor 1: Flow-through ratio (retention ratio >= 0.6)
            if incoming_sum <= 0:
                continue
            retention = outgoing_sum / incoming_sum if incoming_sum > 0 else 0
            if retention >= 0.6:
                flow_score = 1.0
            elif retention >= 0.4:
                flow_score = 0.5
            else:
                flow_score = 0.0

            # Factor 2: Outbound concentration
            unique_out = len(set(e["peer"] for e in out_txns)) if out_txns else 0
            if unique_out <= 3:
                conc_score = 1.0
            elif unique_out <= 5:
                conc_score = 0.5
            else:
                conc_score = 0.0

            # Factor 3: Median hold time
            hold_times = []
            for ie in in_txns:
                best_out = None
                for oe in out_txns:
                    if oe["ts"] >= ie["ts"]:
                        best_out = oe
                        break
                if best_out is not None:
                    hold_secs = (best_out["ts"] - ie["ts"]).total_seconds()
                    hold_times.append(hold_secs)

            if hold_times:
                median_hold = median(hold_times)
                if median_hold < 24 * 3600:
                    hold_score = 1.0
                elif median_hold < 48 * 3600:
                    hold_score = 0.5
                else:
                    hold_score = 0.0
            else:
                # No outbound — still allow if other factors strong
                hold_score = 0.3

            # Factor 4: CV of inbound amounts (Phase 2: <= 0.35)
            in_amounts = [e["amt"] for e in in_txns]
            cv = _coefficient_of_variation(in_amounts)
            if cv <= 0.35:
                cv_score = 1.0
            elif cv <= 0.5:
                cv_score = 0.5
            else:
                cv_score = 0.0

            # Build ring members — exclude immune accounts from membership
            inbound_accounts = set(e["peer"] for e in in_txns) - self._immune_accounts
            outbound_accounts = (set(e["peer"] for e in out_txns) if out_txns else set()) - self._immune_accounts
            # Hub itself excluded if immune
            hub_set = set() if hub in self._immune_accounts else {hub}
            all_members_set = hub_set | inbound_accounts | outbound_accounts

            # Cap smurfing ring size to prevent mega-rings
            if len(all_members_set) > self.MAX_SMURF_RING_SIZE:
                # Keep hub + closest inbound/outbound by recency
                # Prioritize inbound (the smurf sources)
                keep = hub_set.copy()
                remaining_budget = self.MAX_SMURF_RING_SIZE - len(keep)
                # Add inbound accounts first, then outbound
                for acc in sorted(inbound_accounts)[:remaining_budget]:
                    keep.add(acc)
                remaining_budget = self.MAX_SMURF_RING_SIZE - len(keep)
                for acc in sorted(outbound_accounts)[:remaining_budget]:
                    keep.add(acc)
                all_members_set = keep

            all_members = sorted(all_members_set)

            # Factor 5: Ring size
            ring_size = len(all_members)
            if ring_size >= 5:
                size_score = 1.0
            elif ring_size >= 4:
                size_score = 0.8
            elif ring_size >= 3:
                size_score = 0.4
            else:
                size_score = 0.0

            # Combined score — threshold is 4.0 / 5.0 (tight to focus on true smurfs)
            combined_score = flow_score + conc_score + hold_score + cv_score + size_score
            if combined_score < 4.0:
                continue

            # Minimum ring size of 4
            if ring_size < 4:
                continue

            # Dedup
            ring_key = tuple(all_members)
            if ring_key in seen_ring_keys:
                continue
            seen_ring_keys.add(ring_key)

            # Confidence scoring (§1: smurf base = 0.7)
            confidence = 0.7
            # Scale by soft-scoring result
            confidence += (combined_score - 4.0) / 5.0 * 0.2  # Up to +0.06
            # Bonus: low external edges → high internal density
            member_set = set(all_members)
            ext_count = 0
            int_count = 0
            for m in member_set:
                for succ in self.G.successors(m):
                    if succ in member_set:
                        int_count += 1
                    else:
                        ext_count += 1
            if int_count > 0 and ext_count <= int_count:
                confidence += 0.05
            # Size penalty (§5)
            if ring_size > 15:
                confidence -= 0.1
            confidence -= ring_size * 0.005  # mild per-member penalty

            # Create candidate ring with dynamic risk score
            confidence_pct = combined_score / 5.0
            ring_risk = min(100.0, 40.0 + confidence_pct * 40.0 + ring_size * 2)

            self._candidate_rings.append({
                "members": all_members,
                "pattern_type": "smurfing",
                "risk_score": round(ring_risk, 1),
                "confidence_score": max(0.1, min(1.0, confidence)),
                "core_account": hub,  # Used for smurf consolidation
            })

            # Label accounts
            for acc in all_members:
                if acc == hub:
                    self.account_patterns[acc].add("smurfing")
                    self.account_patterns[acc].add("fan_in")
                elif acc in inbound_accounts:
                    self.account_patterns[acc].add("fan_in")
                else:
                    self.account_patterns[acc].add("fan_out")

    # ================================================================== #
    #  STRUCTURING — Strict Multi-Window Detection                        #
    # ================================================================== #
    def detect_structuring(self) -> None:
        """
        Strict structuring detection:
          - ≥5 transactions in near-threshold band ($8K–$9,999 or $4K–$4,999)
          - Within a 48h window
          - Pattern repeated across ≥2 separate windows (≥48h apart)
        """
        if self.df is None or self.df.empty:
            return

        BANDS = [(8000, 9999), (4000, 4999)]
        MIN_HITS_PER_WINDOW = 5
        MIN_WINDOWS = 2
        WINDOW_48H = timedelta(hours=48)

        for acc in set(self.df["sender_id"]).union(set(self.df["receiver_id"])):
            mask = (self.df["sender_id"] == acc) | (self.df["receiver_id"] == acc)
            acc_txns = self.df.loc[mask, ["amount", "timestamp"]].sort_values("timestamp")

            # Filter to band transactions
            band_txns = []
            for _, row in acc_txns.iterrows():
                amt = row["amount"]
                for lo, hi in BANDS:
                    if lo <= amt <= hi:
                        band_txns.append(row["timestamp"])
                        break

            if len(band_txns) < MIN_HITS_PER_WINDOW:
                continue

            # Find qualifying 48h windows
            qualifying_windows: list[pd.Timestamp] = []
            n = len(band_txns)
            right = 0
            for left in range(n):
                w_start = band_txns[left]
                w_end = w_start + WINDOW_48H
                while right < n and band_txns[right] <= w_end:
                    right += 1
                window_count = right - left
                if window_count >= MIN_HITS_PER_WINDOW:
                    # Check this window is ≥48h from previous qualifying window
                    if (not qualifying_windows or
                            (w_start - qualifying_windows[-1]).total_seconds() >= 48 * 3600):
                        qualifying_windows.append(w_start)

            if len(qualifying_windows) >= MIN_WINDOWS:
                self.account_patterns[acc].add("structuring")

    def _consolidate_rings(self) -> None:
        """
        2-stage ring consolidation pipeline (§2 + §4):
          1. Smurf Consolidation — merge overlapping smurf candidates per core
          2. Global Ring Arbitration — confidence-sorted exclusive node assignment
        """
        if len(self._candidate_rings) == 0:
            return

        # ---- Stage 1: SMURF CONSOLIDATION (§2) ----
        # Group smurf candidates by core_account.
        # Merge overlapping windows if Jaccard > 0.6.
        # Emit ONE consolidated smurf ring per core.
        self._candidate_rings = self._smurf_consolidation(self._candidate_rings)

        # ---- Stage 2: GLOBAL RING ARBITRATION (§4) ----
        self.fraud_rings = self._arbitrate_rings(self._candidate_rings)

    # ------------------------------------------------------------------ #
    #  Stage 1: Smurf Consolidation Per Core (§2)                        #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _smurf_consolidation(candidates: list[dict]) -> list[dict]:
        """
        Group smurf candidates by core_account.
        Within each core group, merge overlapping rings (Jaccard > 0.6).
        Emit ONE consolidated ring per core.
        Non-smurf candidates pass through unchanged.
        """
        non_smurf = [c for c in candidates if c["pattern_type"] != "smurfing"]
        smurf = [c for c in candidates if c["pattern_type"] == "smurfing"]

        if not smurf:
            return candidates

        # Group by core_account
        core_groups: dict[str, list[dict]] = defaultdict(list)
        for s in smurf:
            core = s.get("core_account", "unknown")
            core_groups[core].append(s)

        consolidated_smurfs = []
        for core, group in core_groups.items():
            if len(group) == 1:
                consolidated_smurfs.append(group[0])
                continue

            # Merge overlapping within this core group using Jaccard > 0.6
            n = len(group)
            parent = list(range(n))

            def find(x):
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x

            def union(a, b):
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[rb] = ra

            sets = [set(g["members"]) for g in group]
            for i in range(n):
                for j in range(i + 1, n):
                    if _jaccard_similarity(sets[i], sets[j]) > 0.6:
                        union(i, j)

            uf_groups: dict[int, list[int]] = defaultdict(list)
            for i in range(n):
                uf_groups[find(i)].append(i)

            # Emit ONE ring per merged group
            for indices in uf_groups.values():
                merged_members = set()
                best_confidence = 0.0
                best_risk = 0.0
                for idx in indices:
                    merged_members.update(group[idx]["members"])
                    best_confidence = max(best_confidence, group[idx]["confidence_score"])
                    best_risk = max(best_risk, group[idx]["risk_score"])

                consolidated_smurfs.append({
                    "members": sorted(merged_members),
                    "pattern_type": "smurfing",
                    "risk_score": round(best_risk, 1),
                    "confidence_score": best_confidence,
                    "core_account": core,
                })

        return non_smurf + consolidated_smurfs

    # ------------------------------------------------------------------ #
    #  Stage 2: Global Ring Arbitration (§4)                              #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _arbitrate_rings(candidates: list[dict]) -> list[dict]:
        """
        Global ring arbitration with exclusive node assignment.
        
        Sort by: confidence_score descending, then pattern priority
        (cycle > smurf > shell).
        
        For each candidate:
          - If overlap_ratio > 0.6 with existing rings → merge into strongest
          - Otherwise → accept ring, claim all its nodes
        
        Output stability:
          - Each account in at most one ring
          - No ring > 15 members unless cycle-based
          - Deterministic ring IDs
        """
        if not candidates:
            return []

        TYPE_PRIORITY = {"cycle": 0, "smurfing": 1, "shell_network": 2}

        # Sort: confidence desc, then priority asc (cycle first)
        sorted_cands = sorted(
            candidates,
            key=lambda c: (
                -c["confidence_score"],
                TYPE_PRIORITY.get(c["pattern_type"], 99),
            )
        )

        final_rings: list[dict] = []
        used_nodes: set[str] = set()
        # node → index in final_rings for O(N) lookup
        node_to_ring_idx: dict[str, int] = {}

        for cand in sorted_cands:
            members = set(cand["members"])
            overlap = members & used_nodes
            overlap_ratio = len(overlap) / len(members) if members else 0

            if overlap_ratio > 0.6:
                # Merge into the strongest overlapping ring
                # Find which ring has the most overlap
                ring_overlap_counts: dict[int, int] = defaultdict(int)
                for node in overlap:
                    if node in node_to_ring_idx:
                        ring_overlap_counts[node_to_ring_idx[node]] += 1

                if ring_overlap_counts:
                    best_ring_idx = max(ring_overlap_counts,
                                        key=ring_overlap_counts.get)
                    target_ring = final_rings[best_ring_idx]
                    # Only merge new nodes, cap at 15 for non-cycle
                    current_members = set(target_ring["member_accounts"])
                    new_nodes = members - current_members
                    if target_ring["pattern_type"] != "cycle":
                        budget = 15 - len(current_members)
                        new_nodes = set(sorted(new_nodes)[:max(0, budget)])
                    current_members.update(new_nodes)
                    target_ring["member_accounts"] = sorted(current_members)
                    target_ring["risk_score"] = max(
                        target_ring["risk_score"], cand["risk_score"])
                    # Update node index
                    for node in new_nodes:
                        used_nodes.add(node)
                        node_to_ring_idx[node] = best_ring_idx
                continue

            # Accept this ring
            accepted_members = sorted(members - used_nodes | (members & used_nodes))
            # Actually: allow all members but only claim unclaimed ones
            ring_members = sorted(members)

            # Size cap: non-cycle rings max 15
            if cand["pattern_type"] != "cycle" and len(ring_members) > 15:
                ring_members = ring_members[:15]

            if len(ring_members) < 3:
                continue

            ring_idx = len(final_rings)
            final_rings.append({
                "ring_id": "",  # assigned below
                "member_accounts": ring_members,
                "pattern_type": cand["pattern_type"],
                "risk_score": round(cand["risk_score"], 1),
            })

            for node in ring_members:
                used_nodes.add(node)
                node_to_ring_idx[node] = ring_idx

        # Sort by risk descending for deterministic output
        final_rings.sort(key=lambda r: (-r["risk_score"], r["pattern_type"]))

        # Assign ring IDs
        for idx, ring in enumerate(final_rings):
            ring["ring_id"] = f"RING_{idx + 1:03d}"

        return final_rings

    # ================================================================== #
    #  PATTERN HIERARCHY ENFORCEMENT                                       #
    # ================================================================== #
    def _apply_pattern_hierarchy(self) -> None:
        """
        Enforce classification priority:
          cycle > shell > smurfing > structuring > high_velocity

        For each account, keep only the highest-priority pattern class.
        Lower-priority patterns are removed to prevent double-counting.
        """
        HIERARCHY = [
            {"cycle_length_3", "cycle_length_4", "cycle_length_5"},  # Priority 1
            {"shell_account"},                                        # Priority 2
            {"smurfing", "fan_in", "fan_out"},                       # Priority 3
            {"structuring"},                                          # Priority 4
            {"high_velocity", "high_velocity_24h"},                   # Priority 5
            {"low_variance"},                                         # Priority 6
        ]

        # Patterns that are NOT classification labels (always kept)
        KEEP_ALWAYS = {"isolation_cluster", "payroll", "merchant"}

        for acc in list(self.account_patterns.keys()):
            patterns = self.account_patterns[acc]
            kept = patterns & KEEP_ALWAYS

            # Find the highest-priority group that this account belongs to
            for group in HIERARCHY:
                if patterns & group:
                    kept |= (patterns & group)
                    break  # Only keep the highest-priority group

            self.account_patterns[acc] = kept

    # ================================================================== #
    #  PHASE 5: COMPOSITE RISK SCORING AND ROLES                           #
    # ================================================================== #
    def calculate_suspicion_scores(self) -> None:
        """
        Phase 5: Apply new 4-pillar ML scoring + Rules + Roles
        """
        if self.G is None or not list(self.G.nodes()):
            return

        # 1. Run 10 RBI Rules
        nodes = list(self.G.nodes())
        flags_by_acc = run_all_flags(self.df, self.G, nodes)
        
        # Add flags to account patterns
        for acc, flags in flags_by_acc.items():
            for f in flags:
                self.account_patterns[acc].add(f)

        # 2. Assign Roles securely for all rings
        roles_by_acc = {}
        for ring in self.fraud_rings:
            ring_roles = assign_roles(self.G, ring["member_accounts"])
            roles_by_acc.update(ring_roles)

        # 3. Calculate 4-Pillar ML Scores
        self.ml_results = calculate_ml_scores(self.df, self.G, nodes, flags_by_acc, roles_by_acc, self.xmlt_scores)
        
        # Map back to engine state
        for node in nodes:
            res = self.ml_results.get(node)
            if res and res["score"] > 0:
                # Apply suppression as per previous logic (immune accounts with no strong fraud = 0)
                STRONG_FRAUD_PATTERNS = {
                    "cycle_length_3", "cycle_length_4", "cycle_length_5",
                    "shell_account", "smurfing", "F1", "F5", "F10"
                }
                has_strong_fraud = bool(self.account_patterns.get(node, set()) & STRONG_FRAUD_PATTERNS)
                
                if node in self._immune_accounts and not has_strong_fraud:
                    self.suspicion_scores[node] = 0.0
                elif node in self._high_degree_hubs and not has_strong_fraud:
                    self.suspicion_scores[node] = 0.0
                else:
                    self.suspicion_scores[node] = res["score"]
            else:
                self.suspicion_scores[node] = 0.0

    # ================================================================== #
    #  JSON GENERATION                                                     #
    # ================================================================== #
    def generate_json(self) -> dict:
        account_rings: dict[str, list[str]] = defaultdict(list)
        for ring in self.fraud_rings:
            for acc in ring["member_accounts"]:
                account_rings[acc].append(ring["ring_id"])

        suspicious_accounts = []
        for acc in self.G.nodes() if self.G else []:
            score = self.suspicion_scores.get(acc, 0.0)
            if score < self.FLAG_THRESHOLD:
                continue
                
            ml_data = self.ml_results.get(acc, {})
            suspicious_accounts.append({
                "account_id": acc,
                "suspicion_score": score,
                "role": ml_data.get("role", "LEAF"),
                "decision": ml_data.get("decision", "APPROVE"),
                "flag_hits": [p for p in sorted(self.account_patterns.get(acc, set())) if str(p).startswith("F") and len(p) <= 3],
                "ml_scores": ml_data.get("components", {}),
                "detected_patterns": sorted([p for p in self.account_patterns.get(acc, set()) if not (str(p).startswith("F") and len(p) <= 3)]),
                "ring_id": account_rings[acc][0] if account_rings[acc] else "NONE",
                "xmlt_score": self.xmlt_scores.get(acc, {}).get("total_xmlt", 0.0),
                "markov_flow": next((f["threat_vector_weight"] for f in self.markov_flows if f["account_id"] == acc), 0.0),
            })

        suspicious_accounts.sort(key=lambda x: (-x["suspicion_score"], x["account_id"]))

        return {
            "suspicious_accounts": suspicious_accounts,
            "fraud_rings": self.fraud_rings,
            "summary": {
                "total_accounts_analyzed": len(self.G.nodes()) if self.G else 0,
                "suspicious_accounts_flagged": len(suspicious_accounts),
                "fraud_rings_detected": len(self.fraud_rings),
                "processing_time_seconds": round(self._processing_time, 2),
            },
            "xmlt_scores": self.xmlt_scores,
            "layering_chains": self.layering_chains,
            "markov_flows": self.markov_flows[:15],
        }

    # ================================================================== #
    #  GRAPH DATA (Vis.js)                                                 #
    # ================================================================== #
    def get_graph_data(self) -> dict:
        if self.G is None:
            return {"nodes": [], "edges": []}

        nodes_list = []
        for node in self.G.nodes():
            score = self.suspicion_scores.get(node, 0)
            patterns = sorted(self.account_patterns.get(node, set()))
            ml_data = getattr(self, "ml_results", {}).get(node, {})
            role = ml_data.get("role", "LEAF")
            decision = ml_data.get("decision", "APPROVE")

            # HUB == Purple, BRIDGE == Orange, others based on score
            if role == "HUB":
                color, border, size = "#9B59B6", "#8E44AD", 35
            elif role == "BRIDGE":
                color, border, size = "#E67E22", "#D35400", 25
            elif decision == "BLOCK":
                color, border, size = "#E74C3C", "#C0392B", 30
            elif decision == "REVIEW":
                color, border, size = "#F1C40F", "#F39C12", 20
            else:
                color, border, size = "#3498DB", "#2980B9", 16

            in_deg = self.G.in_degree(node)
            out_deg = self.G.out_degree(node)
            total_in = round(sum(float(attrs.get("amount", 0)) for _, _, attrs in self.G.in_edges(node, data=True)), 2)
            total_out = round(sum(float(attrs.get("amount", 0)) for _, _, attrs in self.G.out_edges(node, data=True)), 2)

            nodes_list.append({
                "id": node,
                "label": node,
                "color": {"background": color, "border": border,
                          "highlight": {"background": border, "border": "#ECF0F1"}},
                "size": size,
                "title": f"{node} | {role}",
                "role": role,
                "decision": decision,
                "suspicion_score": score,
                "detected_patterns": patterns,
                "ring_ids": [r["ring_id"] for r in self.fraud_rings if node in r["member_accounts"]],
                "in_degree": in_deg,
                "out_degree": out_deg,
                "total_incoming": total_in,
                "total_outgoing": total_out,
                "xmlt_score": self.xmlt_scores.get(node, {}).get("total_xmlt", 0.0),
                "markov_flow": next((f["threat_vector_weight"] for f in self.markov_flows if f["account_id"] == node), 0.0),
            })

        # Deduplicate edges for vis.js (collapse MultiDiGraph parallel edges)
        edge_map: dict[tuple[str, str], float] = {}
        for u, v, data in self.G.edges(data=True):
            key = (u, v)
            edge_map[key] = edge_map.get(key, 0) + float(data.get("amount", 1))

        edges_list = []
        for (u, v), total_amount in edge_map.items():
            edges_list.append({
                "from": u,
                "to": v,
                "value": max(1, min(6, total_amount / 1000)),
                "title": f"${total_amount:,.2f}",
                "color": {"color": "rgba(52,152,219,0.4)", "highlight": "#3498DB"},
                "arrows": "to",
            })

        return {"nodes": nodes_list, "edges": edges_list}

    # ================================================================== #
    #  SOCCER ANALYTICS ADAPTATION 1: Expected Money Laundering Threat (xMLT)
    # ================================================================== #
    def _calculate_xmlt_scores(self) -> None:
        """
        Adapts Expected Threat (xT) model to financial transactions.
        Scores transactions based on transition risk jumps between account states.
        State definition: (Account Profile, Graph Centrality/Role, Velocity)
        """
        if self.G is None or self.df is None:
            return

        # Pre-assign profile and role scores
        profile_weights = {
            "SAVINGS": 0.2, "GENERAL": 0.4, "CURRENT": 0.4,
            "CREDIT_CARD": 0.5, "PREMIUM": 0.6, "BUSINESS": 0.9
        }
        
        # Calculate velocity and centrality for all nodes
        node_degrees = {n: self.G.degree(n) for n in self.G.nodes()}
        max_deg = max(node_degrees.values()) if node_degrees else 1

        # We will map each node to its base state threat value
        state_values = {}
        for node in self.G.nodes():
            # 1. Profile Risk
            acc_type = "SAVINGS"
            acc_rows = self.df[(self.df["sender_id"] == node) | (self.df["receiver_id"] == node)]
            if not acc_rows.empty:
                acc_type = str(acc_rows.iloc[0].get("account_type", "SAVINGS")).upper()
            
            p_score = profile_weights.get(acc_type, 0.2)

            # 2. Centrality / Role Risk
            deg = node_degrees.get(node, 1)
            norm_deg = deg / max_deg
            if norm_deg > 0.4:
                r_score = 0.9
            elif norm_deg > 0.15:
                r_score = 0.7
            elif deg >= 2:
                r_score = 0.5
            else:
                r_score = 0.2

            # 3. Velocity Risk
            tx_count = len(acc_rows)
            if tx_count >= 15:
                v_score = 0.9
            elif tx_count >= 5:
                v_score = 0.5
            else:
                v_score = 0.2

            # Compute State Threat Value (scaled to 0-100)
            val = (0.3 * p_score + 0.4 * r_score + 0.3 * v_score) * 100
            state_values[node] = round(val, 2)

        # For every edge in the graph, compute xMLT Delta
        for u, v, key, data in self.G.edges(keys=True, data=True):
            s_val = state_values.get(u, 20.0)
            r_val = state_values.get(v, 20.0)
            delta = max(0.0, r_val - s_val)
            self.G[u][v][key]["xmlt_value"] = delta

        # Aggregate total threat progression per account
        for node in self.G.nodes():
            in_xmlt = sum(float(d.get("xmlt_value", 0.0)) for _, _, d in self.G.in_edges(node, data=True))
            out_xmlt = sum(float(d.get("xmlt_value", 0.0)) for _, _, d in self.G.out_edges(node, data=True))
            
            self.xmlt_scores[node] = {
                "base_threat": state_values[node],
                "inbound_threat_progression": round(in_xmlt, 2),
                "outbound_threat_progression": round(out_xmlt, 2),
                "total_xmlt": round(in_xmlt + out_xmlt, 2)
            }

    # ================================================================== #
    #  SOCCER ANALYTICS ADAPTATION 2: Possession Chains (Layering Chains)
    # ================================================================== #
    def _extract_layering_chains(self) -> None:
        """
        Adapts soccer's Possession Chain tracking.
        Extracts multi-hop sequences where same/similar funds propagate within a close time window.
        """
        if self.G is None or self.df is None:
            return

        # We start from low-in-degree nodes (LEAFs/Sources) to track fund injection chains
        sources = [n for n in self.G.nodes() if self.G.in_degree(n) <= 1]
        
        outgoing_txns = defaultdict(list)
        for u, v, d in self.G.edges(data=True):
            outgoing_txns[u].append((v, d["timestamp"], d["amount"], d.get("xmlt_value", 0.0)))
        
        for u in outgoing_txns:
            outgoing_txns[u].sort(key=lambda x: x[1])

        chains = []
        max_chains_limit = 100
        
        path_start_time = lambda u, v: _get_edges_between(self.G, u, v)[0]["timestamp"] if _get_edges_between(self.G, u, v) else pd.Timestamp.now()

        for start_node in sources:
            if len(chains) >= max_chains_limit:
                break
                
            stack = []
            for v, ts, amt, xmlt in outgoing_txns[start_node]:
                stack.append((v, [start_node, v], ts, amt, xmlt))

            while stack and len(chains) < max_chains_limit:
                curr, path, last_ts, last_amt, cum_xmlt = stack.pop()

                if len(path) >= 5:
                    chains.append({
                        "path": path,
                        "length": len(path),
                        "start_time": path_start_time(start_node, path[1]),
                        "cumulative_xmlt": round(cum_xmlt, 2)
                    })
                    continue

                found_next = False
                for succ, ts, amt, xmlt in outgoing_txns[curr]:
                    if succ in path:
                        continue
                    
                    time_diff = (ts - last_ts).total_seconds()
                    if 0 <= time_diff <= 86400:
                        ratio = amt / last_amt if last_amt > 0 else 0
                        if 0.4 <= ratio <= 1.25:
                            found_next = True
                            stack.append((succ, path + [succ], ts, amt, cum_xmlt + xmlt))
                
                if not found_next and len(path) >= 3:
                    chains.append({
                        "path": path,
                        "length": len(path),
                        "start_time": last_ts,
                        "cumulative_xmlt": round(cum_xmlt, 2)
                    })

        # Sort and deduplicate chains by cumulative threat
        unique_chains = {}
        for c in chains:
            key = tuple(c["path"])
            if key not in unique_chains or c["cumulative_xmlt"] > unique_chains[key]["cumulative_xmlt"]:
                unique_chains[key] = c

        self.layering_chains = sorted(unique_chains.values(), key=lambda x: -x["cumulative_xmlt"])[:15]

        # Tag accounts participating in high-threat chains and give them a risk boost
        for chain in self.layering_chains:
            for acc in chain["path"]:
                self.account_patterns[acc].add("layering_chain_member")

    # ================================================================== #
    #  SOCCER ANALYTICS ADAPTATION 3: Markov Transition Matrix
    # ================================================================== #
    def _calculate_markov_flows(self) -> None:
        """
        Formulates the transaction graph as a Markov Transition Network.
        Calculates stationary probability flows and absorption profiles.
        """
        if self.G is None:
            return

        nodes = list(self.G.nodes())
        n = len(nodes)
        if n == 0:
            return

        node_to_idx = {node: i for i, node in enumerate(nodes)}

        P = np.zeros((n, n))
        for u in self.G.nodes():
            u_idx = node_to_idx[u]
            out_edges = self.G.out_edges(u, data=True)
            total_amt = sum(float(d.get("amount", 0.0)) for _, _, d in out_edges)
            
            if total_amt > 0:
                for _, v, d in out_edges:
                    v_idx = node_to_idx[v]
                    P[u_idx, v_idx] += float(d.get("amount", 0.0)) / total_amt
            else:
                P[u_idx, u_idx] = 1.0

        x = np.ones(n) / n
        for _ in range(30):
            x_new = x.dot(P)
            if np.linalg.norm(x_new - x) < 1e-4:
                x = x_new
                break
            x = x_new

        for i, node in enumerate(nodes):
            flow_val = float(x[i])
            self.markov_flows.append({
                "account_id": node,
                "stationary_probability": round(flow_val, 5),
                "threat_vector_weight": round(flow_val * 100, 2)
            })

        self.markov_flows.sort(key=lambda x: -x["stationary_probability"])

    # ================================================================== #
    #  ORCHESTRATOR — Recall-Optimized Pipeline                            #
    # ================================================================== #
    def run_all(self) -> dict:
        try:
            self._start_time = time.time()
            self._detect_business_immunity()
            self.detect_cycles()
            self.detect_shells()
            self.detect_velocity()
            self._extract_smurf_candidates()
            self._score_smurf_candidates()
            self.detect_structuring()

            immune_keep = {"payroll", "merchant"}
            for acc in self._immune_accounts:
                self.account_patterns[acc] = self.account_patterns[acc] & immune_keep

            cleaned_candidates = []
            for cand in self._candidate_rings:
                clean_members = [m for m in cand["members"]
                                 if m not in self._immune_accounts]
                if len(clean_members) >= 3:
                    cand["members"] = sorted(clean_members)
                    cleaned_candidates.append(cand)
            self._candidate_rings = cleaned_candidates

            self._consolidate_rings()
            self._apply_pattern_hierarchy()

            # --- SOCCER ANALYTICS PIPELINE ---
            self._calculate_xmlt_scores()
            self._extract_layering_chains()
            self._calculate_markov_flows()

            self.calculate_suspicion_scores()

            self._processing_time = time.time() - self._start_time

            ring_types = defaultdict(int)
            for r in self.fraud_rings:
                ring_types[r["pattern_type"]] += 1
            flagged = sum(1 for s in self.suspicion_scores.values() if s >= self.FLAG_THRESHOLD)

            print(f"\n{'='*50}")
            print(f"  MONEYMAL V2.0 — Detection Report")
            print(f"{'='*50}")
            print(f"  Rings detected: {len(self.fraud_rings)}")
            for rtype, cnt in sorted(ring_types.items()):
                print(f"    - {rtype}: {cnt}")
            print(f"  Flagged accounts: {flagged}")
            print(f"  Runtime: {self._processing_time:.2f}s")
            print(f"{'='*50}\n")

            return self.generate_json()
        except Exception as e:
            print(f"CRITICAL ERROR in Engine: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": str(e), "suspicious_accounts": [], "fraud_rings": [], "summary": {}}
