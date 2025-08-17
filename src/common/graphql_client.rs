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
