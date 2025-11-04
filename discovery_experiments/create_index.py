#!/usr/bin/env python3
"""
embed_gql_fields.py

Reads a GraphQL SDL file (benchmark.txt), flattens every type->field
combination into a text snippet with all available metadata, sends
those snippets to OpenAI embeddings (openai>=1.0.0 interface), and
saves a JSONL with id/metadata/embedding for vector indexing.

Output format (one JSON object per line):
{
  "id": "Type->field",
  "name": "Type.field",
  "kind": "TypeField",
  "metadata": { ... },
  "embedding": [...]
}
"""

import os
import json
import time
import argparse
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
load_dotenv()
from graphql import parse, print_ast, TypeInfo, visit
from graphql.language.ast import (
    ObjectTypeDefinitionNode,
    InterfaceTypeDefinitionNode,
    InputObjectTypeDefinitionNode,
    EnumTypeDefinitionNode,
    UnionTypeDefinitionNode,
    ScalarTypeDefinitionNode,
    FieldDefinitionNode,
    InputValueDefinitionNode,
    NamedTypeNode,
)
from openai import OpenAI

# ----------------------------
# Helpers for GraphQL TypeNode -> readable string
# ----------------------------
def type_node_to_str(node) -> str:
    """Return human readable GraphQL type string (e.g. [String!]!)."""
    if node is None:
        return "Unknown"
    k = node.kind
    if k == "named_type":
        return node.name.value
    if k == "non_null_type":
        return f"{type_node_to_str(node.type)}!"
    if k == "list_type":
        return f"[{type_node_to_str(node.type)}]"
    return str(node)

def value_node_to_python(node):
    """Convert GraphQL ValueNode to Python literal (for defaults)."""
    if node is None:
        return None
    kt = node.kind
    if kt == "int_value":
        return int(node.value)
    if kt == "float_value":
        return float(node.value)
    if kt == "string_value":
        return node.value
    if kt == "boolean_value":
        return node.value.lower() == "true"
    if kt == "enum_value":
        return node.value
    if kt == "list_value":
        return [value_node_to_python(v) for v in node.values]
    if kt == "object_value":
        return {f.name.value: value_node_to_python(f.value) for f in node.fields}
    return None

# ----------------------------
# Parse SDL and build a map of definitions
# ----------------------------
def parse_sdl_into_map(sdl_text: str) -> Tuple[Any, Dict[str, Any]]:
    """
    Parse SDL and return (ast, defs_map)
    defs_map: name -> dict with keys: kind, node, description, raw, extra
    """
    ast = parse(sdl_text)
    defs: Dict[str, Any] = {}
    for defn in ast.definitions:
        name = getattr(defn, "name", None)
        name_val = name.value if name is not None else None
        kind = defn.kind  # e.g. 'object_type_definition'
        raw = print_ast(defn)
        desc = getattr(defn, "description", None)
        desc_val = desc.value if desc else None
        defs[name_val] = {
            "kind": kind,
            "node": defn,
            "raw": raw,
            "description": desc_val,
        }
    return ast, defs

# ----------------------------
# Extract interfaces implemented by object types
# ----------------------------
def get_interfaces_of_type(node) -> List[str]:
    if not hasattr(node, "interfaces") or node.interfaces is None:
        return []
    return [i.name.value for i in node.interfaces]

# ----------------------------
# Create flattened text document for type->field
# ----------------------------
def build_type_field_doc(type_name: str, type_def: Any, field: Any, defs_map: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return dict:
    {
      id: "Type->field",
      name: "Type.field",
      kind: "TypeField",
      metadata: {...},
      text: "the flattened text to embed"
    }
    """
    field_name = field.name.value
    field_type_str = type_node_to_str(field.type)
    type_kind = type_def["kind"]
    type_node = type_def["node"]
    type_desc = type_def.get("description")
    type_interfaces = get_interfaces_of_type(type_node) if hasattr(type_node, "interfaces") else []
    # field description & args
    field_desc = getattr(field, "description", None)
    field_desc_val = field_desc.value if field_desc else None
    args_list = []
    # arguments can be for field on object/interface
    args = getattr(field, "arguments", None) or getattr(field, "arguments", None) or getattr(field, "args", None)
    if args:
        for a in args:
            args_list.append({
                "name": a.name.value,
                "type": type_node_to_str(a.type),
                "default": value_node_to_python(getattr(a, "default_value", None)),
                "description": a.description.value if getattr(a, "description", None) else None,
            })
    # if the field type is named, fetch referenced type info (enums, inputs, objects)
    named_type_name = None
    # dig to the named type
    def _named(node):
        if node.kind == "named_type":
            return node.name.value
        return _named(node.type)
    try:
        named_type_name = _named(field.type)
    except Exception:
        named_type_name = None

    referenced = {}
    if named_type_name and named_type_name in defs_map:
        ref = defs_map[named_type_name]
        referenced["kind"] = ref["kind"]
        referenced["description"] = ref.get("description")
        # If enum, include members
        if ref["kind"] == "enum_type_definition":
            enum_vals = []
            for v in getattr(ref["node"], "values", []) or []:
                enum_vals.append({"name": v.name.value, "description": v.description.value if getattr(v, "description", None) else None})
            referenced["enumValues"] = enum_vals
        # If input/object, include a short list of fields
        if ref["kind"] in ("input_object_type_definition", "object_type_definition", "interface_type_definition"):
            subfields = []
            for sf in getattr(ref["node"], "fields", []) or []:
                subfields.append({"name": sf.name.value, "type": type_node_to_str(sf.type)})
            referenced["fields_summary"] = subfields[:50]  # limit size
        # unions: union members
        if ref["kind"] == "union_type_definition":
            members = [t.name.value for t in getattr(ref["node"], "types", []) or []]
            referenced["unionMembers"] = members

    # Build metadata dictionary
    metadata = {
        "type_name": type_name,
        "type_kind": type_kind,
        "type_description": type_desc,
        "type_interfaces": type_interfaces,
        "field_name": field_name,
        "field_type": field_type_str,
        "field_description": field_desc_val,
        "field_args": args_list,
        "referenced_type": named_type_name,
        "referenced": referenced,
        "sdl_snippet": (print_ast(type_node)[:4000] if type_node is not None else ""),
    }

    # Build flattened text (concise, includes metadata and small SDL snippets)
    lines: List[str] = []
    lines.append(f"{type_name} -> {field_name}")
    if type_desc:
        lines.append(f"Type description: {type_desc}")
    if type_interfaces:
        lines.append("Implements: " + ", ".join(type_interfaces))
    lines.append(f"Field: {field_name}: {field_type_str}")
    if field_desc_val:
        lines.append(f"Field description: {field_desc_val}")
    if args_list:
        args_s = []
        for a in args_list:
            arg_default = f" = {a['default']}" if a.get("default") is not None else ""
            args_s.append(f"{a['name']}: {a['type']}{arg_default}")
        lines.append("Args: " + ", ".join(args_s))
    if named_type_name:
        lines.append(f"Referenced type: {named_type_name}")
        if referenced.get("description"):
            lines.append(f"Referenced description: {referenced['description']}")
        if "enumValues" in referenced:
            vals = [v["name"] for v in referenced["enumValues"]]
            lines.append("Enum values: " + ", ".join(vals))
        if "fields_summary" in referenced:
            sample = ", ".join([f"{f['name']}: {f['type']}" for f in referenced["fields_summary"][:20]])
            lines.append("Referenced fields: " + sample)
        if "unionMembers" in referenced:
            lines.append("Union members: " + ", ".join(referenced["unionMembers"]))
    # SDL provenance snippet
    snippet = metadata["sdl_snippet"]
    if snippet:
        lines.append("SDL snippet:")
        lines.append(snippet)
    text = "\n".join(lines)

    return {
        "id": f"{type_name}->{field_name}",
        "name": f"{type_name}.{field_name}",
        "kind": "TypeField",
        "metadata": metadata,
        "text": text,
    }

# ----------------------------
# Generate docs for all type->field combos (including inputs)
# ----------------------------
def generate_all_type_field_docs(defs_map: Dict[str, Any]) -> List[Dict[str, Any]]:
    docs = []
    for name, defn in defs_map.items():
        kind = defn["kind"]
        node = defn["node"]
        # handle object types, interfaces, input objects
        if kind in ("object_type_definition", "interface_type_definition"):
            fields = getattr(node, "fields", None) or []
            for f in fields:
                docs.append(build_type_field_doc(name, defn, f, defs_map))
        elif kind == "input_object_type_definition":
            # input fields are also InputValueDefinitionNode list under "fields"
            fields = getattr(node, "fields", None) or []
            for f in fields:
                # adapt InputValueDefinitionNode to same builder
                # create a fake FieldDefinitionNode-like wrapper
                fake_field = f  # InputValueDefinitionNode has name, type, description
                docs.append(build_type_field_doc(name, defn, fake_field, defs_map))
        else:
            # For enums/scalars/unions we don't create type->field embeddings because
            # there's no field. Optionally create Type->__type entries if desired.
            pass

    return docs

# ----------------------------
# Batch embeddings using OpenAI >=1.0.0 client
# ----------------------------
def batch_iter(iterable, n):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= n:
            yield batch
            batch = []
    if batch:
        yield batch

def embed_documents(docs: List[Dict[str, Any]],
                    model: str = "text-embedding-3-small",
                    batch_size: int = 64,
                    sleep_between: float = 0.6) -> List[Dict[str, Any]]:
    """
    Uses openai.OpenAI client (>=1.0.0).
    Returns input docs augmented with 'embedding' vector.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Please set OPENAI_API_KEY environment variable.")

    client = OpenAI(api_key=api_key)
    out = []
    for batch in batch_iter(docs, batch_size):
        inputs = [d["text"] for d in batch]
        resp = client.embeddings.create(model=model, input=inputs)
        # resp.data is list of objects with .embedding
        for doc, emb_obj in zip(batch, resp.data):
            emb = emb_obj.embedding
            doc_copy = dict(doc)
            doc_copy["embedding"] = emb
            out.append(doc_copy)
        time.sleep(sleep_between)
    return out

# ----------------------------
# Save JSONL
# ----------------------------
def save_jsonl(out_docs: List[Dict[str, Any]], out_path: str):
    with open(out_path, "w", encoding="utf-8") as fh:
        for d in out_docs:
            tosave = {
                "id": d["id"],
                "name": d["name"],
                "kind": d["kind"],
                "metadata": d["metadata"],
                "embedding": d["embedding"],
            }
            fh.write(json.dumps(tosave) + "\n")

# ----------------------------
# CLI
# ----------------------------
def main():
    parser = argparse.ArgumentParser(description="Embed GraphQL type->field combos.")
    parser.add_argument("--input", "-i", required=True, help="Input SDL file (graphQL schema)")
    parser.add_argument("--out", "-o", required=True, help="Output JSONL file path")
    parser.add_argument("--model", default="text-embedding-3-small", help="Embedding model")
    parser.add_argument("--batch", type=int, default=64, help="Batch size for embedding requests")
    parser.add_argument("--sleep", type=float, default=0.6, help="Seconds to sleep between batches")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as fh:
        sdl = fh.read()

    print("Parsing SDL...")
    ast, defs_map = parse_sdl_into_map(sdl)
    print(f"Parsed {len(defs_map)} named definitions.")

    print("Generating type->field documents...")
    docs = generate_all_type_field_docs(defs_map)
    print(f"Created {len(docs)} type->field docs to embed.")

    if len(docs) == 0:
        print("No type->field docs found. Exiting.")
        return

    # Optional: you might want to prioritize certain kinds (object > interface > input).
    # For now we keep given order.
    print("Creating embeddings (OpenAI)...")
    docs_with_embeddings = embed_documents(docs, model=args.model, batch_size=args.batch, sleep_between=args.sleep)
    print(f"Received embeddings for {len(docs_with_embeddings)} docs.")

    print(f"Saving to {args.out} ...")
    save_jsonl(docs_with_embeddings, args.out)
    print("Done.")

if __name__ == "__main__":
    main()
