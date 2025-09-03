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
use crate::common::graphql_client::{fetch_query, type_to_sdl};
use rmcp::{Error as McpError, ServerHandler, const_string, model::*, schemars, tool};

// -------------------- Explorer --------------------
#[derive(Debug, Clone)]
pub struct Explorer {
    pub endpoint: String,
}

impl Explorer {
    pub fn new(endpoint: String) -> Result<Self, McpError> {
        tracing::info!("Explorer created for endpoint: '{}'", endpoint);
        Ok(Explorer { endpoint })
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
