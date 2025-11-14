#!/usr/bin/env python3
"""
Usage:
  python3 query.py --query "what are the best hotels?" --embeddings test

Notes:
 - Requires: pip install openai numpy
 - Set OPENAI_API_KEY environment variable.
 - Expects embeddings JSONL where each line contains {"id","name","metadata","embedding","text"?}
"""

import os
import json
import argparse
from typing import List, Dict, Any, Tuple
import numpy as np
from openai import OpenAI

# ----------------------------
# Loading embeddings
# ----------------------------
def load_jsonl_embeddings(path: str) -> Tuple[List[Dict[str, Any]], np.ndarray]:
    docs = []
    embeddings = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "embedding" not in obj:
                raise ValueError("Each JSONL line must contain an 'embedding' field.")
            docs.append(obj)
            embeddings.append(obj["embedding"])
    emb_array = np.array(embeddings, dtype=np.float32)
    if emb_array.ndim != 2:
        raise ValueError("Embeddings must be a 2D array (N, D).")
    return docs, emb_array

def constrain_results_by_first_signature(results: List[Tuple[float, Dict[str, Any]]]) -> List[Tuple[float, Dict[str, Any]]]:
    if not results:
        return []

    # Always include the first document
    first_result = results[0]
    first_doc = first_result[1]
    first_meta = first_doc.get("metadata", {})
    first_type = (first_meta.get("field_type") or "?").replace("!", "")

    def matches(doc):
        meta = doc.get("metadata", {})
        tname = meta.get("type_name")
        return tname == first_type

    filtered_rest = [
        (score, doc)
        for score, doc in results[1:]
        if matches(doc)
    ]

    return [first_result] + filtered_rest

def constrain_results_recursively(results: List[Tuple[float, Dict[str, Any]]], topk: int) -> List[Tuple[float, Dict[str, Any]]]:
    """
    Select up to `topk` results using recursive type-based expansion.

    Starting from the highest-scoring unused result (the "root"), add it to the output,
    then repeatedly expand by finding results whose `type_name` matches the current node's
    `field_type`, prioritized by their score. If fewer than `topk` results are found via
    connected expansions, start a new expansion from the next highest-scoring unused result.
    Repeat until `topk` results are collected or all results are exhausted.

    Args:
        results: List of (score, document) tuples, where document contains `metadata` with
                 `field_type` and `type_name` keys.
        topk: The desired number of results to select.

    Returns:
        List of up to `topk` (score, document) tuples, ranked by expansion traversal order.
    """
    if not results:
        return []

    selected = []
    used = set()

    # This tracks indices (like a work queue for BFS, prioritized by score)
    pending_roots = [i for i in range(len(results))]
    while len(selected) < topk and pending_roots:
        # Find next unused, highest-score result as current cluster root
        next_root = None
        for i in pending_roots:
            if i not in used:
                next_root = i
                break
        if next_root is None:
            break  # all used

        queue = [next_root]
        pending_roots = [i for i in pending_roots if i != next_root]

        while queue and len(selected) < topk:
            idx = queue.pop(0)
            if idx in used:
                continue
            score, doc = results[idx]
            selected.append((score, doc))
            used.add(idx)

            meta = doc.get("metadata", {})
            field_type = (meta.get("field_type") or "?").replace("!", "").replace("[", "").replace("]", "")

            # Find all unused children with matching type_name, sort by score desc
            children = [
                (j, results[j][0])
                for j in range(len(results))
                if j not in used
                and results[j][1].get("metadata", {}).get("type_name") == field_type
                and j not in queue
            ]
            children.sort(key=lambda x: -x[1])
            child_indices_sorted = [j for j, _ in children]
            # Add high-score children to the FRONT for high-score-first expansion
            queue = child_indices_sorted + queue

    return selected[:topk]

# ----------------------------
# Vector helpers
# ----------------------------
def normalize_rows(a: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(a, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return a / norms

def cosine_similarity_matrix(query_vec: np.ndarray, corpus_normed: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity (dot products) between a single query vector and an L2-normalized corpus.
    - query_vec: shape (D,) or (1, D) (not necessarily normalized)
    - corpus_normed: shape (N, D) and must be L2-normalized already
    Returns: sims shape (N,) (float32)
    """
    q = query_vec.reshape(-1).astype(np.float32)
    q_norm = q / (np.linalg.norm(q) or 1.0)
    # Matrix multiply: (N, D) @ (D,) -> (N,)
    sims = corpus_normed @ q_norm
    return sims  # shape (N,)

# ----------------------------
# OpenAI embedding
# ----------------------------
def get_query_embedding(client: OpenAI, query: str, model: str) -> List[float]:
    resp = client.embeddings.create(model=model, input=[query])
    return resp.data[0].embedding

# ----------------------------
# Retrieval (fast top-k)
# ----------------------------
def retrieve_top_k(query: str,
                   docs: List[Dict[str, Any]],
                   emb_array: np.ndarray,
                   client: OpenAI,
                   model: str = "text-embedding-3-small",
                   topk: int = 10) -> List[Tuple[float, Dict[str, Any]]]:
    if emb_array.size == 0:
        return []

    # Normalize corpus rows once
    corpus_normed = normalize_rows(emb_array)

    # Embed query
    q_emb = np.array(get_query_embedding(client, query, model), dtype=np.float32)

    # Similarities
    sims = cosine_similarity_matrix(q_emb, corpus_normed)

    N = sims.shape[0]
    k = min(topk, N)
    if k <= 0:
        return []

    # fast top-k with argpartition, then sort those
    idx_part = np.argpartition(-sims, range(k))[:k]
    idx_sorted = idx_part[np.argsort(-sims[idx_part])]
    results = [(float(sims[i]), docs[i]) for i in idx_sorted]
    return results

# ----------------------------
# Pretty printing
# ----------------------------
def print_results_tree(results):
    """Pretty print results as a tree by id hierarchy (type->field->subfield)."""
    # Build a dict tree: {root: {child: ...}}
    from collections import defaultdict

    def nested_dict():
        return defaultdict(nested_dict)

    tree = nested_dict()
    node_scores = {}
    node_types = {}
    node_signatures = {}

    for score, doc in results:
        id_path = str(doc["id"])
        parts = id_path.split("->")
        node = tree
        for part in parts:
            node = node[part]
        node_scores[id_path] = score
        meta = doc.get("metadata") or {}
        node_types[id_path] = meta.get("type_name") or meta.get("type") or "?"
        node_signatures[id_path] = meta.get("field_type") or "?"

    # Recursively print
    def print_node(node, path=[], level=0):
        indent = "  " * level
        for child, subnode in node.items():
            full_path = "->".join(path + [child])
            # Show score and signature if present
            extra = ""
            if full_path in node_scores:
                extra = f" [score={node_scores[full_path]:.3f}, signature={node_signatures[full_path]}]"
            print(f"{indent}{child}{extra}")
            print_node(subnode, path + [child], level+1)
    print_node(tree)

def print_results(results: List[Tuple[float, Dict[str, Any]]], show_text_len: int = 800):
    for rank, (score, doc) in enumerate(results, start=1):
        meta = doc.get("metadata", {})
        tname = meta.get("type_name") or meta.get("type") or "?"
        fname = meta.get("field_name") or "?"
        ftype = meta.get("field_type") or "?"
        fdesc = meta.get("field_description") or ""
        print(f"--- Rank {rank} | score={score:.6f} | id={doc.get('id')} | type={tname} | field={fname} | signature={ftype}")
        #print(f"Type: {tname}   Field: {fname}   Signature: {ftype}")
        if fdesc:
            print("Field description:", (fdesc if len(fdesc) <= show_text_len else fdesc[:show_text_len] + "..."))
        # Print short snippet if available (text or raw)
        text = doc.get("text") or doc.get("raw") or ""
        if text:
            snippet = text if len(text) <= show_text_len else text[:show_text_len] + "..."
            print("Snippet:")
            print(snippet)
        print()

from dotenv import load_dotenv
load_dotenv()

# ----------------------------
# CLI
# ----------------------------
def main():
    parser = argparse.ArgumentParser(description="Query type->field embeddings and retrieve top K relevant fields.")
    parser.add_argument("--embeddings", "-e", required=True, help="Path to embeddings JSONL (one object per line).")
    parser.add_argument("--query", "-q", required=True, help="Natural language query.")
    parser.add_argument("--model", "-m", default="text-embedding-3-small", help="Embedding model used for query (should match stored).")
    parser.add_argument("--topk", type=int, default=10, help="Number of top results to return.")
    parser.add_argument("--constrain-results", action=argparse.BooleanOptionalAction, default=True, help="Recursively constrain results based on breadth-first expansion")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Please set OPENAI_API_KEY environment variable before running.")
    client = OpenAI(api_key=api_key)

    print(f"Loading embeddings from {args.embeddings} ...")
    docs, emb_array = load_jsonl_embeddings(args.embeddings)

    results = retrieve_top_k(args.query, docs, emb_array, client, model=args.model, topk=len(docs))
    if args.constrain_results:
        results = constrain_results_recursively(results, args.topk)
    else:
        results = results[:args.topk]

    results = results[:args.topk]
    print("DONE")

    if not results:
        print("No results found.")
        return

    print_results(results)
    print_results_tree(results)

    # Print compact JSON output for programmatic use
    out_compact = []
    for score, doc in results:
        out_compact.append({
            "id": doc.get("id"),
            "name": doc.get("name"),
            "score": score,
            "metadata": doc.get("metadata"),
        })
    #print("=== JSON output (top results) ===")
    #print(json.dumps(out_compact, indent=2))

if __name__ == "__main__":
    main()
