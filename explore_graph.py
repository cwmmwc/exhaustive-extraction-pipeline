#!/usr/bin/env python3
"""
Knowledge Graph Explorer — Build and query a graph from the extraction databases.

Combines KCA (historical_docs) and Survey of Conditions into a single NetworkX graph.
Every entity is a node. Relationships, fee patents, correspondence, testimony, and
index card connections become edges.

Usage:
    python3 explore_graph.py                    # build graph, enter interactive mode
    python3 explore_graph.py --stats            # print graph statistics
    python3 explore_graph.py --find "Collier"   # find nodes matching a name
    python3 explore_graph.py --paths "John Collier" "Burton Wheeler"  # shortest paths
    python3 explore_graph.py --neighbors "Mattie Sturm" --depth 2     # neighborhood
    python3 explore_graph.py --export graph.gexf                      # export for Gephi
"""

import argparse
import sys
from collections import Counter

import networkx as nx
import psycopg2
from psycopg2.extras import RealDictCursor


def load_graph(databases=None):
    """Build a unified graph from multiple extraction databases."""
    if databases is None:
        databases = ['historical_docs', 'survey_of_conditions']

    G = nx.MultiDiGraph()  # directed, allows multiple edges between same nodes

    for db_name in databases:
        print(f"\nLoading {db_name}...")
        conn = psycopg2.connect(dbname=db_name, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        # Prefix for node IDs to avoid cross-database collisions
        # But we'll merge nodes with the same name+type across databases
        prefix = db_name[:3]  # 'his' or 'sur'

        # --- Documents as nodes ---
        cur.execute("SELECT id, file_name, display_title, collection FROM documents")
        for doc in cur.fetchall():
            doc_id = f"doc:{prefix}:{doc['id']}"
            G.add_node(doc_id,
                        label=doc['display_title'] or doc['file_name'],
                        node_type='document',
                        database=db_name,
                        collection=doc.get('collection', ''))

        # --- Entities as nodes ---
        cur.execute("SELECT id, name, type, context FROM entities")
        entities_by_id = {}
        for ent in cur.fetchall():
            # Use name+type as the canonical node ID so entities merge across databases
            node_id = f"ent:{ent['name']}:{ent['type']}"
            entities_by_id[ent['id']] = node_id
            if not G.has_node(node_id):
                G.add_node(node_id,
                            label=ent['name'],
                            node_type='entity',
                            entity_type=ent['type'],
                            context=ent['context'] or '',
                            databases=[db_name])
            else:
                # Entity exists from another database — record cross-database presence
                dbs = G.nodes[node_id].get('databases', [])
                if db_name not in dbs:
                    dbs.append(db_name)
                    G.nodes[node_id]['databases'] = dbs

        # --- Mentions: entity ↔ document edges ---
        cur.execute("SELECT entity_id, document_id, context FROM mentions")
        for m in cur.fetchall():
            ent_node = entities_by_id.get(m['entity_id'])
            doc_node = f"doc:{prefix}:{m['document_id']}"
            if ent_node and G.has_node(doc_node):
                G.add_edge(ent_node, doc_node,
                           edge_type='mentioned_in',
                           context=m.get('context', '')[:200])

        # --- Relationships as edges ---
        try:
            cur.execute("SELECT * FROM relationships")
            for rel in cur.fetchall():
                doc_node = f"doc:{prefix}:{rel['document_id']}"
                # Try entity ID-based linking first (historical_docs)
                if rel.get('source_entity_id') and rel.get('target_entity_id'):
                    src = entities_by_id.get(rel['source_entity_id'])
                    tgt = entities_by_id.get(rel['target_entity_id'])
                # Fall back to text-based (survey_of_conditions)
                else:
                    src = f"ent:{rel.get('subject', '?')}:person" if rel.get('subject') else None
                    tgt = f"ent:{rel.get('object', '?')}:person" if rel.get('object') else None
                    # Add nodes if they don't exist
                    if src and not G.has_node(src):
                        G.add_node(src, label=rel['subject'], node_type='entity',
                                   entity_type='person', context='', databases=[db_name])
                    if tgt and not G.has_node(tgt):
                        G.add_node(tgt, label=rel['object'], node_type='entity',
                                   entity_type='person', context='', databases=[db_name])

                if src and tgt:
                    G.add_edge(src, tgt,
                               edge_type=rel.get('type', 'related_to'),
                               context=rel.get('context', '')[:200],
                               document=doc_node)
        except Exception:
            conn.rollback()

        # --- Fee patents as edges ---
        try:
            cur.execute("SELECT * FROM fee_patents")
            for fp in cur.fetchall():
                doc_node = f"doc:{prefix}:{fp['document_id']}"
                allottee = fp.get('allottee', '')
                if not allottee:
                    continue

                allottee_node = f"ent:{allottee}:person"
                if not G.has_node(allottee_node):
                    G.add_node(allottee_node, label=allottee, node_type='entity',
                               entity_type='person', context='allottee', databases=[db_name])

                # Allottee → land parcel
                allotment = fp.get('allotment_number', '')
                if allotment:
                    parcel_node = f"ent:Allotment {allotment}:land_parcel"
                    if not G.has_node(parcel_node):
                        G.add_node(parcel_node, label=f"Allotment {allotment}",
                                   node_type='entity', entity_type='land_parcel',
                                   acreage=fp.get('acreage', ''), databases=[db_name])
                    G.add_edge(allottee_node, parcel_node,
                               edge_type='allottee_of',
                               patent_date=fp.get('patent_date', ''),
                               mechanism=fp.get('trust_to_fee_mechanism', ''),
                               document=doc_node)

                # Buyer edge
                buyer = fp.get('subsequent_buyer', '')
                if buyer and buyer.lower() not in ('', 'unknown', 'not specified', 'not mentioned'):
                    buyer_node = f"ent:{buyer}:person"
                    if not G.has_node(buyer_node):
                        G.add_node(buyer_node, label=buyer, node_type='entity',
                                   entity_type='person', context='buyer', databases=[db_name])
                    G.add_edge(allottee_node, buyer_node,
                               edge_type='sold_to',
                               sale_price=fp.get('sale_price', ''),
                               document=doc_node)

                # Mortgage edge
                mortgage_holder = fp.get('mortgage_holder', '') or ''
                mortgage_amt = fp.get('mortgage_amount', '') or ''
                if mortgage_holder and mortgage_holder.lower() not in ('', 'unknown', 'not specified'):
                    mort_node = f"ent:{mortgage_holder}:organization"
                    if not G.has_node(mort_node):
                        G.add_node(mort_node, label=mortgage_holder, node_type='entity',
                                   entity_type='organization', context='mortgage holder',
                                   databases=[db_name])
                    G.add_edge(allottee_node, mort_node,
                               edge_type='mortgaged_to',
                               amount=mortgage_amt,
                               document=doc_node)
        except Exception:
            conn.rollback()

        # --- Correspondence as edges ---
        try:
            cur.execute("SELECT * FROM correspondence")
            for corr in cur.fetchall():
                doc_node = f"doc:{prefix}:{corr['document_id']}"
                sender = corr.get('sender', '')
                recipient = corr.get('recipient', '')
                if not sender or not recipient:
                    continue

                sender_node = f"ent:{sender}:person"
                recip_node = f"ent:{recipient}:person"
                for node_id, name in [(sender_node, sender), (recip_node, recipient)]:
                    if not G.has_node(node_id):
                        G.add_node(node_id, label=name, node_type='entity',
                                   entity_type='person', context='', databases=[db_name])

                G.add_edge(sender_node, recip_node,
                           edge_type='wrote_to',
                           date=corr.get('date', ''),
                           subject=corr.get('subject', '')[:200],
                           document=doc_node)
        except Exception:
            conn.rollback()

        # --- Testimony as edges ---
        try:
            cur.execute("SELECT * FROM testimony")
            for test in cur.fetchall():
                doc_node = f"doc:{prefix}:{test['document_id']}"
                witness = test.get('witness', '')
                if not witness:
                    continue

                witness_node = f"ent:{witness}:person"
                if not G.has_node(witness_node):
                    G.add_node(witness_node, label=witness, node_type='entity',
                               entity_type='person',
                               context=test.get('witness_title', ''),
                               databases=[db_name])

                G.add_edge(witness_node, doc_node,
                           edge_type='testified_in',
                           date=test.get('date', ''),
                           subject=test.get('subject', '')[:200],
                           key_claims=test.get('key_claims', '')[:500])

                # Questioner edge
                questioner = test.get('questioner', '')
                if questioner and questioner.lower() not in ('', 'unknown', 'not specified',
                                                              'not identifiable', 'not identifiable (affidavit format)'):
                    q_node = f"ent:{questioner}:person"
                    if not G.has_node(q_node):
                        G.add_node(q_node, label=questioner, node_type='entity',
                                   entity_type='person', context='questioner',
                                   databases=[db_name])
                    G.add_edge(q_node, witness_node,
                               edge_type='questioned',
                               document=doc_node)
        except Exception:
            conn.rollback()

        # Count what we loaded
        print(f"  Loaded from {db_name}")
        conn.close()

    return G


def print_stats(G):
    """Print graph statistics."""
    nodes = G.number_of_nodes()
    edges = G.number_of_edges()

    node_types = Counter(d.get('node_type', '?') for _, d in G.nodes(data=True))
    edge_types = Counter(d.get('edge_type', '?') for _, _, d in G.edges(data=True))

    # Cross-database entities
    cross_db = sum(1 for _, d in G.nodes(data=True)
                   if d.get('node_type') == 'entity' and len(d.get('databases', [])) > 1)

    print(f"\n{'='*60}")
    print(f"KNOWLEDGE GRAPH STATISTICS")
    print(f"{'='*60}")
    print(f"Nodes: {nodes:,}")
    print(f"Edges: {edges:,}")
    print(f"\nNode types:")
    for t, n in node_types.most_common():
        print(f"  {t:<20} {n:>8,}")
    print(f"\nEdge types:")
    for t, n in edge_types.most_common():
        print(f"  {t:<20} {n:>8,}")
    print(f"\nCross-database entities (appear in both KCA and Survey): {cross_db:,}")

    # Most connected nodes
    print(f"\nMost connected entities (by degree):")
    entity_degrees = [(n, G.degree(n), G.nodes[n].get('label', ''))
                      for n in G.nodes() if G.nodes[n].get('node_type') == 'entity']
    entity_degrees.sort(key=lambda x: x[1], reverse=True)
    for _, deg, label in entity_degrees[:20]:
        print(f"  {deg:>6} connections: {label}")


def find_nodes(G, query):
    """Find nodes matching a search query."""
    query_lower = query.lower()
    matches = []
    for node_id, data in G.nodes(data=True):
        label = data.get('label', '')
        if query_lower in label.lower():
            matches.append((node_id, data))
    matches.sort(key=lambda x: x[1].get('label', ''))
    return matches


def get_neighbors(G, node_id, depth=1):
    """Get the neighborhood of a node up to a given depth."""
    if not G.has_node(node_id):
        return None
    # Use BFS
    visited = {node_id}
    frontier = [node_id]
    subgraph_nodes = {node_id}

    for d in range(depth):
        next_frontier = []
        for n in frontier:
            for neighbor in set(list(G.successors(n)) + list(G.predecessors(n))):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.append(neighbor)
                    subgraph_nodes.add(neighbor)
        frontier = next_frontier

    return G.subgraph(subgraph_nodes)


def find_paths(G, source_query, target_query, max_length=5):
    """Find paths between two entities by name."""
    # Find best matching nodes
    src_matches = find_nodes(G, source_query)
    tgt_matches = find_nodes(G, target_query)

    if not src_matches:
        print(f"No nodes found matching '{source_query}'")
        return
    if not tgt_matches:
        print(f"No nodes found matching '{target_query}'")
        return

    src_id = src_matches[0][0]
    tgt_id = tgt_matches[0][0]
    src_label = src_matches[0][1].get('label', src_id)
    tgt_label = tgt_matches[0][1].get('label', tgt_id)

    print(f"\nPaths from '{src_label}' to '{tgt_label}' (max length {max_length}):")

    # Convert to undirected for path finding
    UG = G.to_undirected()

    try:
        paths = list(nx.all_simple_paths(UG, src_id, tgt_id, cutoff=max_length))
        if not paths:
            print("  No paths found.")
            return

        # Sort by length
        paths.sort(key=len)
        for i, path in enumerate(paths[:10]):
            print(f"\n  Path {i+1} (length {len(path)-1}):")
            for j, node in enumerate(path):
                data = G.nodes[node]
                label = data.get('label', node)
                ntype = data.get('entity_type', data.get('node_type', ''))
                print(f"    {'→ ' if j > 0 else '  '}{label} [{ntype}]")
                # Show edge info
                if j > 0:
                    prev = path[j-1]
                    edges = list(G.edges(prev, data=True, keys=True)) + list(G.edges(node, data=True, keys=True))
                    edges = [(u, v, d) for u, v, k, d in edges if (u == prev and v == node) or (u == node and v == prev)]
                    for _, _, edata in edges[:1]:
                        etype = edata.get('edge_type', '')
                        ctx = edata.get('context', edata.get('subject', ''))[:100]
                        if ctx:
                            print(f"      ({etype}: {ctx})")
                        else:
                            print(f"      ({etype})")

        if len(paths) > 10:
            print(f"\n  ... and {len(paths) - 10} more paths")

    except nx.NetworkXNoPath:
        print("  No paths found.")
    except nx.NodeNotFound as e:
        print(f"  Node not found: {e}")


def interactive_mode(G):
    """Interactive query mode."""
    print("\n" + "="*60)
    print("KNOWLEDGE GRAPH EXPLORER — Interactive Mode")
    print("="*60)
    print("\nCommands:")
    print("  find <name>              — search for entities")
    print("  neighbors <name>         — show connections (1 hop)")
    print("  neighbors2 <name>        — show connections (2 hops)")
    print("  paths <name1> -> <name2> — find paths between entities")
    print("  stats                    — graph statistics")
    print("  quit                     — exit")
    print()

    while True:
        try:
            cmd = input("graph> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not cmd:
            continue
        if cmd == 'quit':
            break
        if cmd == 'stats':
            print_stats(G)
            continue

        if cmd.startswith('find '):
            query = cmd[5:].strip()
            matches = find_nodes(G, query)
            if not matches:
                print(f"  No nodes matching '{query}'")
            else:
                print(f"  {len(matches)} matches:")
                for node_id, data in matches[:30]:
                    label = data.get('label', '')
                    ntype = data.get('entity_type', data.get('node_type', ''))
                    dbs = data.get('databases', [])
                    db_str = f" [{', '.join(dbs)}]" if dbs else ""
                    print(f"    {label} ({ntype}){db_str}")
            continue

        if cmd.startswith('neighbors2 '):
            query = cmd[11:].strip()
            matches = find_nodes(G, query)
            if not matches:
                print(f"  No nodes matching '{query}'")
                continue
            node_id = matches[0][0]
            sub = get_neighbors(G, node_id, depth=2)
            if sub:
                print(f"\n  Neighborhood of '{matches[0][1].get('label', '')}' (2 hops):")
                print(f"  {sub.number_of_nodes()} nodes, {sub.number_of_edges()} edges")
                # Show by type
                by_type = {}
                for n, d in sub.nodes(data=True):
                    if n == node_id:
                        continue
                    t = d.get('entity_type', d.get('node_type', '?'))
                    by_type.setdefault(t, []).append(d.get('label', n))
                for t, names in sorted(by_type.items()):
                    print(f"\n    {t} ({len(names)}):")
                    for name in sorted(names)[:15]:
                        print(f"      {name}")
                    if len(names) > 15:
                        print(f"      ... and {len(names)-15} more")
            continue

        if cmd.startswith('neighbors '):
            query = cmd[10:].strip()
            matches = find_nodes(G, query)
            if not matches:
                print(f"  No nodes matching '{query}'")
                continue
            node_id = matches[0][0]
            label = matches[0][1].get('label', '')
            print(f"\n  Direct connections of '{label}':")
            # Outgoing
            for _, tgt, data in G.edges(node_id, data=True):
                tgt_label = G.nodes[tgt].get('label', tgt)
                etype = data.get('edge_type', '')
                print(f"    → {tgt_label} ({etype})")
            # Incoming
            for src, _, data in G.in_edges(node_id, data=True):
                src_label = G.nodes[src].get('label', src)
                etype = data.get('edge_type', '')
                print(f"    ← {src_label} ({etype})")
            continue

        if '->' in cmd and cmd.startswith('paths '):
            parts = cmd[6:].split('->')
            if len(parts) == 2:
                find_paths(G, parts[0].strip(), parts[1].strip())
            continue

        print(f"  Unknown command. Type 'quit' to exit.")


def main():
    parser = argparse.ArgumentParser(description="Knowledge Graph Explorer")
    parser.add_argument("--stats", action="store_true", help="Print graph statistics")
    parser.add_argument("--find", help="Find nodes matching a name")
    parser.add_argument("--paths", nargs=2, metavar=("SOURCE", "TARGET"),
                        help="Find paths between two entities")
    parser.add_argument("--neighbors", help="Show neighborhood of an entity")
    parser.add_argument("--depth", type=int, default=1, help="Neighborhood depth (default: 1)")
    parser.add_argument("--export", help="Export graph to GEXF file (for Gephi)")
    parser.add_argument("--db", nargs='+', default=['historical_docs', 'survey_of_conditions'],
                        help="Databases to include")
    args = parser.parse_args()

    G = load_graph(args.db)

    if args.export:
        # GEXF requires all attributes to be str/int/float/bool — no None or lists
        for node in G.nodes():
            data = G.nodes[node]
            for k, v in list(data.items()):
                if isinstance(v, list):
                    data[k] = ','.join(str(x) for x in v)
                elif v is None:
                    data[k] = ''
        for u, v, data in G.edges(data=True):
            for k, val in list(data.items()):
                if isinstance(val, list):
                    data[k] = ','.join(str(x) for x in val)
                elif val is None:
                    data[k] = ''
        nx.write_gexf(G, args.export)
        print(f"\nExported to {args.export}")
        print_stats(G)
        return

    if args.stats:
        print_stats(G)
        return

    if args.find:
        matches = find_nodes(G, args.find)
        for node_id, data in matches[:30]:
            label = data.get('label', '')
            ntype = data.get('entity_type', data.get('node_type', ''))
            print(f"  {label} ({ntype})")
        return

    if args.paths:
        find_paths(G, args.paths[0], args.paths[1])
        return

    if args.neighbors:
        matches = find_nodes(G, args.neighbors)
        if matches:
            node_id = matches[0][0]
            sub = get_neighbors(G, node_id, depth=args.depth)
            if sub:
                print(f"\nNeighborhood of '{matches[0][1].get('label', '')}' (depth {args.depth}):")
                print(f"{sub.number_of_nodes()} nodes, {sub.number_of_edges()} edges")
        return

    # Default: interactive mode
    print_stats(G)
    interactive_mode(G)


if __name__ == "__main__":
    main()
