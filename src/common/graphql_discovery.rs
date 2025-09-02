//!
//! This module defines a GraphQL exploration tool for dynamic, "discovery-style" clients.
//! Rather than dumping the entire schema at once, it offers focused inspection utilities
//! for clients that want to explore GraphQL APIs field-by-field and type-by-type.  
//!
//! ## Capabilities Provided
//! - **get_query_fields**: List all available top-level `Query` fields in SDL-like signature format.
//! - **inspect_field**: For any given query field, returns its SDL-style signature along with
//!   definitions of any involved input objects and a summary of its return type - suitable for building precise queries.
//! - **execute_query**: Submit fully constructed GraphQL queries and retrieve the raw JSON response.
//!
use crate::common::graphql_client::{fetch_query, introspect_type_query, unwrap_named_type};
use rmcp::{Error as McpError, ServerHandler, const_string, model::*, schemars, tool};
use serde_json::Value;
use std::collections::HashMap;

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
    #[tool(description = "List Query root fields with SDL-like signatures")]
    pub async fn get_query_fields(&self) -> Result<CallToolResult, McpError> {
        let q = introspect_type_query("Query");
        let json = match fetch_query(&self.endpoint, &q).await {
            Ok(j) => j,
            Err(err) => return Ok(err),
        };

        let fields = json
            .pointer("/data/__type/fields")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();

        let mut sdl_list = String::new();
        for field in fields {
            let fname = field
                .get("name")
                .and_then(|n| n.as_str())
                .unwrap_or("<unnamed>");
            let mut field_sig = format!("{}(", fname);

            if let Some(args) = field.get("args").and_then(|a| a.as_array()) {
                let arg_list: Vec<String> = args
                    .iter()
                    .map(|arg| {
                        let aname = arg.get("name").and_then(|v| v.as_str()).unwrap_or("");
                        let atyp = type_ref_to_sdl(&arg["type"]);
                        format!("{aname}: {atyp}")
                    })
                    .collect();
                field_sig.push_str(&arg_list.join(", "));
            }
            field_sig.push_str(")");
            field_sig.push_str(": ");
            field_sig.push_str(&type_ref_to_sdl(field.get("type").unwrap_or(&Value::Null)));

            sdl_list.push_str(&field_sig);
            sdl_list.push('\n');
        }

        Ok(CallToolResult::success(vec![Content::text(sdl_list)]))
    }
    /// Inspect a Query field and return SDL-formatted schema
    #[tool(description = "Return SDL for a Query field, including input objects and return type")]
    pub async fn inspect_field(
        &self,
        #[tool(param)]
        #[schemars(description = "Name of the Query field to inspect")]
        field_name: String,
    ) -> Result<CallToolResult, McpError> {
        let q = introspect_type_query("Query");
        let json = match fetch_query(&self.endpoint, &q).await {
            Ok(j) => j,
            Err(err) => return Ok(err),
        };

        let fields = json
            .pointer("/data/__type/fields")
            .and_then(|v| v.as_array());
        let field = fields.and_then(|arr| {
            arr.iter().find(|f| {
                f.get("name")
                    .and_then(|n| n.as_str())
                    .map(|n| n.eq_ignore_ascii_case(&field_name))
                    .unwrap_or(false)
            })
        });

        let field = match field {
            Some(f) => f.clone(),
            None => {
                let available = fields
                    .map(|a| {
                        a.iter()
                            .filter_map(|f| f.get("name").and_then(|n| n.as_str()))
                            .collect::<Vec<_>>()
                            .join(", ")
                    })
                    .unwrap_or_else(|| "<none>".to_string());
                return Ok(CallToolResult::error(vec![Content::text(format!(
                    "Field '{}' not found on Query. Available fields: {}",
                    field_name, available
                ))]));
            }
        };

        // Collect SDL for input objects
        let mut input_sdl = String::new();
        if let Some(args) = field.get("args").and_then(|a| a.as_array()) {
            for arg in args {
                if let Some((name, _)) = unwrap_named_type(&arg["type"]) {
                    let q_in = introspect_type_query(name.as_str());
                    if let Ok(j) = fetch_query(&self.endpoint, &q_in).await {
                        if let Some(tn) = j.pointer("/data/__type") {
                            if let Some(sdl) = type_to_sdl(tn) {
                                input_sdl.push_str(&sdl);
                                input_sdl.push('\n');
                            }
                        }
                    }
                }
            }
        }

        // Collect SDL for return type
        let mut return_sdl = String::new();
        if let Some(ret_type) = field.get("type") {
            if let Some((name, _)) = unwrap_named_type(ret_type) {
                let q_ret = introspect_type_query(name.as_str());
                if let Ok(j) = fetch_query(&self.endpoint, &q_ret).await {
                    if let Some(tn) = j.pointer("/data/__type") {
                        if let Some(sdl) = type_to_sdl(tn) {
                            return_sdl.push_str(&sdl);
                            return_sdl.push('\n');
                        }
                    }
                }
            }
        }

        // Construct field signature in SDL form
        let mut field_sig = format!("{}(", field_name);
        if let Some(args) = field.get("args").and_then(|a| a.as_array()) {
            let arg_list: Vec<String> = args
                .iter()
                .map(|arg| {
                    let aname = arg.get("name").and_then(|v| v.as_str()).unwrap_or("");
                    let atyp = type_ref_to_sdl(&arg["type"]);
                    format!("{aname}: {atyp}")
                })
                .collect();
            field_sig.push_str(&arg_list.join(", "));
        }
        field_sig.push_str(")");
        field_sig.push_str(": ");
        field_sig.push_str(&type_ref_to_sdl(field.get("type").unwrap_or(&Value::Null)));

        let sdl_output = format!(
            "# Field: {}\n# Input objects\n{}\n# Return type\n{}",
            field_sig, input_sdl, return_sdl
        );

        Ok(CallToolResult::success(vec![Content::text(sdl_output)]))
    }

    /// Execute a GraphQL query
    #[tool(description = "Execute a precise GraphQL query and return the response JSON")]
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
                1) Call inspect_field(<field>) to get SDL form for the field and its input objects.\n\
                2) Use this SDL to construct queries.\n\
                3) Execute queries via execute_query(query)."
                    .to_string(),
            ),
        }
    }
}
