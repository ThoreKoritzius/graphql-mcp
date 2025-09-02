//!
//! Two main capabilities using the introspection API:  
//! 1. **Get Full Schema**: Retrieve the entire GraphQL schema as SDL (Schema Definition Language) text, reconstructed from the server's introspection query results.
//! 2. **Execute Query**: Execute arbitrary GraphQL queries against the endpoint and return the JSON response.
//!
//! ## Key Functions and Types
//! - `Explorer`: The primary client for communicating with a GraphQL endpoint.
//! - `get_full_schema`: Fetches, parses, and converts the introspected GraphQL schema to SDL text format.
//! - `execute_query`: Submits a provided GraphQL query string and returns the raw JSON response.
//! - SDL Helper Functions: Internal helpers to convert introspection JSON into SDL string output.
//!
use crate::common::graphql_client::fetch_query;
use rmcp::{Error as McpError, ServerHandler, const_string, model::*, schemars, tool};
use serde_json::Value;

// -------------------- Explorer --------------------
#[derive(Debug, Clone)]
pub struct Explorer {
    pub endpoint: String,
}

impl Explorer {
    pub fn new(endpoint: String) -> Result<Self, McpError> {
        println!("Explorer created for GraphQL endpoint: '{}'", endpoint);
        Ok(Explorer { endpoint })
    }
}

// -------------------- SDL Conversion --------------------
fn type_ref_to_sdl(typ: &Value) -> String {
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

fn type_to_sdl(t: &Value) -> Option<String> {
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

// -------------------- tools --------------------
#[tool(tool_box)]
impl Explorer {
    /// Return the full schema as SDL text
    #[tool(description = "Retrieve the full GraphQL schema in SDL format")]
    pub async fn get_full_schema(&self) -> Result<CallToolResult, McpError> {
        let introspection_query = r#"
        query IntrospectionQuery {
          __schema {
            types {
              kind
              name
              fields(includeDeprecated: true) {
                name
                args {
                  name
                  type { kind name ofType { kind name ofType { kind name ofType { kind name } } } }
                }
                type { kind name ofType { kind name ofType { kind name ofType { kind name } } } }
              }
              inputFields {
                name
                type { kind name ofType { kind name ofType { kind name ofType { kind name } } } }
              }
              enumValues(includeDeprecated: true) {
                name
              }
            }
          }
        }
        "#;

        let json = match fetch_query(&self.endpoint, introspection_query).await {
            Ok(j) => j,
            Err(err) => return Ok(err),
        };

        let types = json
            .pointer("/data/__schema/types")
            .and_then(|v| v.as_array().cloned())
            .unwrap_or_default();

        let mut sdl = String::new();
        for t in types {
            if let Some(ts) = type_to_sdl(&t) {
                sdl.push_str(&ts);
                sdl.push('\n');
            }
        }

        Ok(CallToolResult::success(vec![Content::text(sdl)]))
    }

    /// Execute a GraphQL query and return JSON
    #[tool(description = "Execute a GraphQL query and return JSON response")]
    pub async fn execute_query(
        &self,
        #[tool(param)] query: String,
    ) -> Result<CallToolResult, McpError> {
        let json = match fetch_query(&self.endpoint, &query).await {
            Ok(j) => j,
            Err(err) => return Ok(err),
        };

        if json.get("errors").is_some() {
            return Ok(CallToolResult::error(vec![Content::text(
                serde_json::to_string_pretty(&json).unwrap_or("<unserializable error>".into()),
            )]));
        }

        Ok(CallToolResult::success(vec![Content::text(
            serde_json::to_string_pretty(&json)
                .unwrap_or_else(|_| format!("Could not pretty-print response: {:?}", json)),
        )]))
    }
}

// -------------------- ServerHandler --------------------
const_string!(Echo = "echo");

#[tool(tool_box)]
impl ServerHandler for Explorer {
    fn get_info(&self) -> ServerInfo {
        ServerInfo {
            protocol_version: ProtocolVersion::V_2024_11_05,
            capabilities: ServerCapabilities::builder().enable_tools().build(),
            server_info: Implementation::from_build_env(),
            instructions: Some(
                "GraphQL Toolserver:\n\
                1) Call get_full_schema() to retrieve the full schema in SDL format.\n\
                2) Use that schema client-side to construct queries.\n\
                3) Call execute_query(query) to run queries."
                    .to_string(),
            ),
        }
    }
}
