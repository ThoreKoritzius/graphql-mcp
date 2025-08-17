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

    // Private helper method: builds and executes the introspection query for a given type,
    // then pretty–prints the __type portion of the JSON response.
    async fn introspect_type_details(&self, type_name: &str) -> Result<String, String> {
        // Build the introspection query using the provided type_name.
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
                    inputFields {{
                        name
                        description
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

        // Execute the query and obtain the JSON response.
        let json = match fetch_query(&self.endpoint, &introspection).await {
            Ok(j) => j,
            Err(err) => return Err(format!("Error fetching query: {:?}", err)),
        };

        // Locate the __type field in the response.
        let type_info = match json.pointer("/data/__type") {
            Some(ti) => ti,
            None => {
                return Err(format!(
                    "Type information '{}' was missing in GraphQL response from '{}'.\nRaw response:\n{}",
                    type_name,
                    self.endpoint,
                    serde_json::to_string_pretty(&json)
                        .unwrap_or_else(|_| "<unserializable response>".to_string())
                ));
            }
        };

        // Pretty–print the type info.
        let pretty = serde_json::to_string_pretty(type_info)
            .unwrap_or_else(|_| format!("Failed to pretty-print type info: {:?}", type_info));

        Ok(pretty)
    }

    #[tool(description = "Get detailed GraphQL schema info for a type")]
    async fn get_graphql_type_details(
        &self,
        #[tool(param)]
        #[schemars(description = "Name of schema type")]
        type_name: String,
    ) -> Result<CallToolResult, McpError> {
        match self.introspect_type_details(&type_name).await {
            Ok(pretty) => Ok(CallToolResult::success(vec![Content::text(pretty)])),
            Err(msg) => Ok(CallToolResult::error(vec![Content::text(msg)])),
        }
    }

    #[tool(description = "Discover all available schema type names + entry point")]
    async fn get_type_overview(&self) -> Result<CallToolResult, McpError> {
        // Introspection query for schema types.
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

        // Fetch Query type details by calling our helper method directly.
        let query_details = match self.introspect_type_details("Query").await {
            Ok(pretty) => pretty,
            Err(msg) => format!("<failed to get Query type details: {}>", msg),
        };

        let output = format!(
            "These are all available types in the Schema:\n{}\n\n--- GraphQL entry point type 'Query' details ---\n{}",
            names.join("\n"),
            query_details
        );

        Ok(CallToolResult::success(vec![Content::text(output)]))
    }

    #[tool(
        description = "Run a precise GraphQL query (after understanding the schema via discovery tools)"
    )]
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
        // Return the raw JSON text as the tool result.
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
            instructions: Some("
            This server lets you connect to a GraphQL server. ALWAYS use the 'get_type_overview' tool first, then 'get_graphql_type_details' for the relevant types and finally 
            'execute_query' with the correct graphql syntax with a query that is executed and you get the result. 
            Make sure to use the best fitting entry point in query with all necessary filters to answer user question, which my be nested and need to be discovered first.
            ".to_string()),
        }
    }
}
