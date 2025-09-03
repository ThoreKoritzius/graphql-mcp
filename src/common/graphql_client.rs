use rmcp::model::{CallToolResult, Content};
use serde_json::Value;

pub async fn fetch_query(endpoint: &str, graphql_query: &str) -> Result<Value, CallToolResult> {
    let payload = serde_json::json!({ "query": graphql_query });

    let client = reqwest::Client::new();
    let resp = match client
        .post(endpoint)
        .header("Content-Type", "application/json")
        .json(&payload)
        .send()
        .await
    {
        Ok(r) => r,
        Err(e) => {
            let msg = format!(
                "Could not contact GraphQL endpoint at '{}'.\nNetwork error: {}",
                endpoint, e
            );
            return Err(CallToolResult::error(vec![Content::text(msg)]));
        }
    };

    let status = resp.status();
    let body_text = match resp.text().await {
        Ok(t) => t,
        Err(e) => {
            let msg = format!(
                "GraphQL endpoint '{}' responded, but reading the response failed: {}",
                endpoint, e
            );
            return Err(CallToolResult::error(vec![Content::text(msg)]));
        }
    };

    if !status.is_success() {
        let msg = format!(
            "GraphQL endpoint '{}' returned HTTP {}: {}",
            endpoint, status, body_text
        );
        return Err(CallToolResult::error(vec![Content::text(msg)]));
    }

    let json: Value = match serde_json::from_str(&body_text) {
        Ok(j) => j,
        Err(e) => {
            let msg = format!(
                "Invalid JSON received from endpoint '{}': {}\nRaw response:\n{}",
                endpoint, e, body_text
            );
            return Err(CallToolResult::error(vec![Content::text(msg)]));
        }
    };

    Ok(json)
}

/// Unwraps a GraphQL introspection "type" to the innermost named type.
/// e.g. NON_NULL -> LIST -> OBJECT(name="Astronaut") => returns ("Astronaut", "OBJECT")
pub fn unwrap_named_type(mut t: &Value) -> Option<(String, String)> {
    loop {
        if let Some(name) = t.get("name").and_then(|n| n.as_str()) {
            if !name.is_empty() {
                return Some((
                    name.to_string(),
                    t.get("kind")
                        .and_then(|k| k.as_str())
                        .unwrap_or("")
                        .to_string(),
                ));
            }
        }
        match t.get("ofType") {
            Some(next) if !next.is_null() => t = next,
            _ => break,
        }
    }
    None
}

/// Build an introspection query for a named type using a raw template then replace placeholder.
/// This avoids format! brace escaping issues.
pub fn introspect_type_query(typename: &str) -> String {
    let template = r#"
        query IntrospectType {
            __type(name: "__TYPENAME__") {
                name
                kind
                description
                fields(includeDeprecated: true) {
                    name
                    description
                    args {
                        name
                        description
                        type {
                            kind
                            name
                            ofType { kind name ofType { kind name } }
                        }
                    }
                    type { kind name ofType { kind name ofType { kind name } } }
                }
                inputFields {
                    name
                    description
                    type { kind name ofType { kind name ofType { kind name } } }
                }
                enumValues { name description }
                possibleTypes { name }
            }
        }
    "#;
    template.replace("__TYPENAME__", typename)
}

// -------------------- SDL Conversion --------------------
pub fn type_ref_to_sdl(typ: &Value) -> String {
    let kind = typ.get("kind").and_then(|v| v.as_str()).unwrap_or("");
    let name = typ.get("name").and_then(|v| v.as_str()).unwrap_or("");

    match kind {
        "NON_NULL" => {
            let of_type = typ.get("ofType").unwrap_or(&Value::Null);
            format!("{}!", type_ref_to_sdl(of_type))
        }
        "LIST" => {
            let of_type = typ.get("ofType").unwrap_or(&Value::Null);
            format!("[{}]", type_ref_to_sdl(of_type))
        }
        _ => name.to_string(),
    }
}

fn field_to_sdl(f: &Value) -> String {
    let name = f.get("name").and_then(|v| v.as_str()).unwrap_or("");
    let args = f
        .get("args")
        .and_then(|a| a.as_array())
        .map(|arr| {
            arr.iter()
                .map(|arg| {
                    let aname = arg.get("name").and_then(|v| v.as_str()).unwrap_or("");
                    let atyp = type_ref_to_sdl(&arg["type"]);
                    format!("{aname}: {atyp}")
                })
                .collect::<Vec<_>>()
                .join(", ")
        })
        .filter(|s| !s.is_empty())
        .map(|s| format!("({s})"))
        .unwrap_or_default();

    let typ = type_ref_to_sdl(&f["type"]);
    format!("  {name}{args}: {typ}")
}

fn input_field_to_sdl(f: &Value) -> String {
    let name = f.get("name").and_then(|v| v.as_str()).unwrap_or("");
    let typ = type_ref_to_sdl(&f["type"]);
    format!("  {name}: {typ}")
}

pub fn type_to_sdl(t: &Value) -> Option<String> {
    let kind = t.get("kind").and_then(|v| v.as_str()).unwrap_or("");
    let name = t.get("name").and_then(|v| v.as_str()).unwrap_or("");
    if name.is_empty() {
        return None;
    }

    match kind {
        "OBJECT" => {
            let mut s = format!("type {name} {{\n");
            if let Some(fields) = t.get("fields").and_then(|f| f.as_array()) {
                for f in fields {
                    s.push_str(&format!("{}\n", field_to_sdl(f)));
                }
            }
            s.push_str("}\n");
            Some(s)
        }
        "INPUT_OBJECT" => {
            let mut s = format!("input {name} {{\n");
            if let Some(fields) = t.get("inputFields").and_then(|f| f.as_array()) {
                for f in fields {
                    s.push_str(&format!("{}\n", input_field_to_sdl(f)));
                }
            }
            s.push_str("}\n");
            Some(s)
        }
        "ENUM" => {
            let mut s = format!("enum {name} {{\n");
            if let Some(vals) = t.get("enumValues").and_then(|v| v.as_array()) {
                for v in vals {
                    if let Some(vname) = v.get("name").and_then(|vv| vv.as_str()) {
                        s.push_str(&format!("  {vname}\n"));
                    }
                }
            }
            s.push_str("}\n");
            Some(s)
        }
        "SCALAR" => Some(format!("scalar {name}\n")),
        "INTERFACE" => Some(format!("interface {name} {{}}\n")),
        "UNION" => Some(format!("union {name} = ...\n")),
        _ => None,
    }
}
