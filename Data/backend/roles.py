import networkx as nx

def assign_roles(G: nx.MultiDiGraph, ring_members: list[str]) -> dict[str, dict]:
    """
    Assigns structural roles to members within a fraud ring.
    Returns a dict mapping account_id to {"role": str, "multiplier": float}.
    """
    if len(ring_members) <= 1:
        if ring_members:
            return {ring_members[0]: {"role": "LEAF", "multiplier": 1.0}}
        return {}

    roles = {}
    
    # Extract subgraph for the ring
    subgraph = G.subgraph(ring_members)
    
    # Calculate degree centrality (in + out) within the graph vs overall graph
    # Hub has highest degree overall, Bridge has high betweenness centrality or cross-edges
    
    degrees = {node: G.degree(node) for node in ring_members}
    in_degrees = {node: G.in_degree(node) for node in ring_members}
    out_degrees = {node: G.out_degree(node) for node in ring_members}
    
    max_deg = max(degrees.values()) if degrees else 0
    
    # We will approximate bridging using external connections
    # i.e., nodes that connect to members OUTSIDE the ring
    for node in ring_members:
        internal_deg = subgraph.degree(node)
        external_deg = degrees[node] - internal_deg
        
        # HUB assignment (Top degree or highly connected within ring)
        if degrees[node] == max_deg and degrees[node] > 2:
            roles[node] = {"role": "HUB", "multiplier": 1.25}
        
        # BRIDGE assignment (Many external connections, connecting sub-networks)
        elif external_deg > internal_deg and degrees[node] > 2:
            roles[node] = {"role": "BRIDGE", "multiplier": 1.15}
            
        # MULE assignment (Forwarder: high pass-through, degree >= 2)
        elif in_degrees[node] > 0 and out_degrees[node] > 0:
            roles[node] = {"role": "MULE", "multiplier": 1.10}
            
        # LEAF assignment (Peripheral, single degree or minimal activity)
        else:
            roles[node] = {"role": "LEAF", "multiplier": 1.0}
            
    # Guarantee at least one HUB if there are multiple members and no HUB assigned
    if "HUB" not in [v["role"] for v in roles.values()]:
        # Fallback to absolute max degree in the ring
        best_node = max(ring_members, key=lambda n: degrees[n])
        roles[best_node] = {"role": "HUB", "multiplier": 1.25}

    return roles
