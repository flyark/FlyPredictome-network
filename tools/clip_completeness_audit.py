#!/usr/bin/env python3
"""
clip_completeness_audit.py — audit FlyPredictome-clip-data bundle completeness
against the FlyPredictome network.

Two independent gaps make a gene's cLIP interactome smaller than the network says:
  (1) BUNDLELESS PARTNER — the neighbour has no bundle at all, so the edge can
      never surface in cLIP (e.g. Delta, network degree 24, has no bundle).
  (2) ASYMMETRIC BUNDLING — a pair X-Y is written into only one endpoint's bundle,
      so the other's bundle silently omits it (proven: Akt1___foxo is in Akt1's
      bundle, absent from foxo's).

Phase A (no downloads) quantifies (1) from nodes.csv + edges.csv + the bundle id list.
Phase B (downloads each bundle) measures actual partner counts to expose (2).

Inputs:
  --nodes  nodes.csv  (gene,fbgn,degree,...)      authoritative network side
  --edges  edges.csv  (source,target,...)         names, mapped to FBgn via nodes
  --ids    fbgn_list.txt  (one FBgn per bundle)   the bundles that exist
  --bundles DIR   read FBgn*.zip locally (fast, for the pipeline); else fetch Pages
  --structural-only   run Phase A only
Outputs a summary to stdout and a full per-gene CSV (--out).
"""
import io, os, csv, sys, zipfile, argparse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, Counter

PAGES = "https://flyark.github.io/FlyPredictome-clip-data/"
TREE_API = "https://api.github.com/repos/flyark/FlyPredictome-clip-data/git/trees/main?recursive=1"
HERE = os.path.dirname(os.path.abspath(__file__))

def bundle_ids(a):
    """FBgn ids that have a bundle: from a local dir, an explicit list, or the repo tree."""
    import json
    if a.bundles:
        return set(f[:-4] for f in os.listdir(a.bundles) if f.endswith(".zip"))
    if a.ids:
        return set(l.strip() for l in open(a.ids) if l.strip())
    tree = json.loads(urllib.request.urlopen(TREE_API, timeout=30).read())
    return set(x["path"][:-4] for x in tree["tree"] if x["path"].endswith(".zip"))

def load_network(nodes_csv, edges_csv):
    name2fbgn, fbgn2name, degree = {}, {}, {}
    for r in csv.DictReader(open(nodes_csv)):
        name2fbgn[r["gene"]] = r["fbgn"]; fbgn2name[r["fbgn"]] = r["gene"]; degree[r["fbgn"]] = int(r["degree"])
    neighbors = defaultdict(set)
    for r in csv.DictReader(open(edges_csv)):
        s, t = name2fbgn.get(r["source"]), name2fbgn.get(r["target"])
        if s and t and s != t: neighbors[s].add(t); neighbors[t].add(s)
    return name2fbgn, fbgn2name, degree, neighbors

def read_bundle(fbgn, local_dir):
    if local_dir:
        data = open(os.path.join(local_dir, fbgn + ".zip"), "rb").read()
    else:
        data = urllib.request.urlopen(urllib.request.Request(PAGES + fbgn + ".zip", headers={"User-Agent": "audit/1.0"}), timeout=30).read()
    z = zipfile.ZipFile(io.BytesIO(data))
    cf = [n for n in z.namelist() if n.endswith(".csv")][0]
    toks = Counter()
    for r in csv.DictReader(io.TextIOWrapper(z.open(cf), "utf-8")):
        nm = r.get("name", "")
        for t in (nm.split("___") if "___" in nm else [nm]):
            toks[t] += 1
    if not toks: return set()
    bait = toks.most_common(1)[0][0]
    return set(toks) - {bait}                     # partner symbols

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", default=os.path.join(HERE, "..", "data", "nodes.csv"))
    ap.add_argument("--edges", default=os.path.join(HERE, "..", "data", "edges.csv"))
    ap.add_argument("--ids", default=None, help="file of FBgn ids (one per line); default: derive from --bundles or the clip-data repo")
    ap.add_argument("--bundles", default=None, help="local dir of FBgn*.zip; default: fetch from Pages")
    ap.add_argument("--out", default="clip_completeness_report.csv"); ap.add_argument("--structural-only", action="store_true")
    ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args()

    name2fbgn, fbgn2name, degree, neighbors = load_network(a.nodes, a.edges)
    have = bundle_ids(a)
    nodes = set(fbgn2name)

    # ---- Phase A: structural (no downloads) ----
    bundleless = sorted((f for f in nodes if f not in have), key=lambda f: -degree.get(f, 0))
    tot_edges = sum(len(v) for v in neighbors.values()) // 2
    invisible_edges = sum(1 for u in neighbors for v in neighbors[u] if u < v and (u not in have or v not in have))
    print(f"NETWORK: {len(nodes)} nodes, {tot_edges} edges   |   BUNDLES: {len(have)}")
    print(f"Phase A — BUNDLELESS nodes: {len(bundleless)} network genes have NO bundle "
          f"({sum(degree.get(f,0) for f in bundleless)} node-degree stranded)")
    print(f"  edges with >=1 bundleless endpoint (never visible in cLIP): {invisible_edges} / {tot_edges} "
          f"({100*invisible_edges/tot_edges:.1f}%)")
    print("  top bundleless hubs (degree — these lose the most):")
    for f in bundleless[:12]:
        print(f"    {fbgn2name[f]:16} {f}  degree {degree.get(f,0)}")

    if a.structural_only:
        return

    # ---- Phase B: per-bundle partner counts (downloads) ----
    print(f"\nPhase B — auditing {len(have)} bundles ({'local '+a.bundles if a.bundles else 'fetching from Pages'})…", flush=True)
    rows, done, errs = [], 0, 0
    def work(f):
        parts = read_bundle(f, a.bundles)
        pf = {name2fbgn[p] for p in parts if p in name2fbgn}
        net = neighbors.get(f, set())
        covered = net & pf
        missing = net - pf
        miss_bundleless = {m for m in missing if m not in have}
        return f, len(parts), degree.get(f, 0), len(net), len(covered), len(missing), len(miss_bundleless)
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(work, f): f for f in have}
        for fut in as_completed(futs):
            try:
                rows.append(fut.result());
            except Exception:
                errs += 1
            done += 1
            if done % 500 == 0: print(f"    {done}/{len(have)}…", flush=True)

    # summary
    incomplete = [r for r in rows if r[3] > 0 and r[5] > 0]        # missing >= 1 network neighbour
    fully = [r for r in rows if r[3] > 0 and r[5] == 0]
    with_deg = [r for r in rows if r[3] > 0]
    tot_missing = sum(r[5] for r in rows)
    tot_missing_bundleless = sum(r[6] for r in rows)
    print(f"\nPhase B results ({len(rows)} audited, {errs} errors):")
    print(f"  bundles fully covering their network neighbours: {len(fully)}/{len(with_deg)} ({100*len(fully)/max(1,len(with_deg)):.1f}%)")
    print(f"  bundles missing >=1 network neighbour:           {len(incomplete)}/{len(with_deg)} ({100*len(incomplete)/max(1,len(with_deg)):.1f}%)")
    print(f"  total missing (bundle vs network) edges: {tot_missing}  "
          f"(of which {tot_missing_bundleless} = partner has no bundle, {tot_missing-tot_missing_bundleless} = asymmetric/other)")
    print("  worst-covered bundles (degree>=8):")
    worst = sorted((r for r in rows if r[3] >= 8), key=lambda r: (r[4]/r[3]))[:12]
    for f, npart, deg, net, cov, miss, mbl in worst:
        print(f"    {fbgn2name[f]:16} {f}  network {net:3d}  bundle-covers {cov:3d} ({100*cov/net:3.0f}%)  missing {miss} ({mbl} bundleless)")

    with open(a.out, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["fbgn","gene","bundle_partners","network_degree","covered","missing","missing_bundleless","pct_covered"])
        for f, npart, deg, net, cov, miss, mbl in sorted(rows, key=lambda r: (r[4]/r[3] if r[3] else 1)):
            w.writerow([f, fbgn2name.get(f,""), npart, net, cov, miss, mbl, f"{100*cov/net:.1f}" if net else ""])
    print(f"\nfull report -> {a.out}")

if __name__ == "__main__":
    main()
