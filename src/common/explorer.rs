#![allow(dead_code)]
use crate::common::graphql_client::fetch_query;
use rmcp::{Error as McpError, ServerHandler, const_string, model::*, schemars, tool};

#[derive(Debug, Clone)]
pub struct Explorer {
    pub endpoint: String,
}

#[tool(tool_box)]
impl Explorer {
    pub fn new(endpoint: String) -> Result<Self, McpError> {
        println!("Explorer created for GraphQL endpoint: '{}'", endpoint);
        Ok(Explorer { endpoint })
    }
    #[tool(description = "Return all available type names by introspecting the GraphQL endpoint")]
    async fn get_type_overview(&self) -> Result<CallToolResult, McpError> {
        let introspection = r#"
            query IntrospectionTypes {
                __schema {
                    types {
                        name
                    }
                }
            }
        "#;

        let json = match fetch_query(&self.endpoint, introspection).await {
            Ok(j) => j,
            Err(err) => return Ok(err),
        };

        let types = match json
            .pointer("/data/__schema/types")
            .and_then(|v| v.as_array())
        {
            Some(arr) => arr,
            None => {
                let msg = format!(
                    "Schema types were missing in GraphQL response from '{}'.\nRaw response:\n{}",
                    self.endpoint,
                    serde_json::to_string_pretty(&json)
                        .unwrap_or_else(|_| "<unserializable response>".to_string())
                );
                return Ok(CallToolResult::error(vec![Content::text(msg)]));
            }
        };

        let names: Vec<String> = types
            .iter()
            .filter_map(|t| t.get("name").and_then(|n| n.as_str()).map(String::from))
            .collect();

        let output = format!(
            "These are all available types in the Schema:\n{}",
            names.join("\n")
        );

        Ok(CallToolResult::success(vec![Content::text(output)]))
    }

    #[tool(description = "Return detailed discovery info for a specific GraphQL type/field")]
    async fn get_graphql_type_details(
        &self,
        #[tool(param)]
        #[schemars(description = "Name of schema type")]
        type_name: String,
    ) -> Result<CallToolResult, McpError> {
        let introspection = format!(
            r#"
                query IntrospectType {{
                    __type(name: "{typename}") {{
                        name
                        kind
                        description
                        fields(includeDeprecated: true) {{
                            name
                            description
                            args {{
                                name
                                description
                                type {{
                                    name
                                    kind
                                    ofType {{ name kind }}
                                }}
                            }}
                            type {{
                                name
                                kind
                                ofType {{ name kind }}
                            }}
                        }}
                    }}
                }}
            "#,
            typename = type_name
        );

        let json = match fetch_query(&self.endpoint, &introspection).await {
            Ok(j) => j,
            Err(err) => return Ok(err),
        };

        let type_info = match json.pointer("/data/__type") {
            Some(ti) => ti,
            None => {
                let msg = format!(
                    "Type information '{}' was missing in GraphQL response from '{}'.\nRaw response:\n{}",
                    type_name,
                    self.endpoint,
                    serde_json::to_string_pretty(&json)
                        .unwrap_or_else(|_| "<unserializable response>".to_string())
                );
                return Ok(CallToolResult::error(vec![Content::text(msg)]));
            }
        };
        let pretty = serde_json::to_string_pretty(type_info)
            .unwrap_or_else(|_| format!("Failed to pretty-print type info: {:?}", type_info));
        Ok(CallToolResult::success(vec![Content::text(pretty)]))
    }

    #[tool(description = "Execute a GraphQL query against the configured endpoint")]
    async fn execute_query(
        &self,
        #[tool(param)]
        #[schemars(
            description = "GraphQL query, must be as precise as possible, e.g. by applying filters"
        )]
        query: String,
    ) -> Result<CallToolResult, McpError> {
        let json = match fetch_query(&self.endpoint, &query).await {
            Ok(j) => j,
            Err(err) => return Ok(err),
        };
        // Return the raw JSON text as the tool result
        let pretty = serde_json::to_string_pretty(&json)
            .unwrap_or_else(|_| format!("Could not pretty-print response: {:?}", json));
        Ok(CallToolResult::success(vec![Content::text(pretty)]))
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
            instructions: Some("This server lets you connect to a graphql server".to_string()),
        }
    }
}
