#![allow(dead_code)]
use rmcp::{Error as McpError, ServerHandler, const_string, model::*, schemars, tool};
use serde_json::Value;
use serde_json::json;

#[derive(Debug, Clone)]
pub struct Explorer {
    pub endpoint: String,
}

#[tool(tool_box)]
impl Explorer {
    pub fn new(endpoint: String) -> Result<Self, McpError> {
        Ok(Explorer { endpoint })
    }

    #[tool(description = "Return all available type names by introspecting the GraphQL endpoint")]
    async fn get_type_overview(&self) -> Result<CallToolResult, McpError> {
        // 1. Build the introspection query
        let introspection = r#"
        query IntrospectionTypes {
            __schema {
            types {
                name
            }
            }
        }
        "#;

        let payload = serde_json::json!({ "query": introspection });

        // 2. Send it to the endpoint
        let client = reqwest::Client::new();
        let resp = client
            .post(&self.endpoint)
            .header("Content-Type", "application/json")
            .json(&payload)
            .send()
            .await
            .map_err(|e| McpError::internal_error(format!("HTTP request error: {}", e), None))?;

        let status = resp.status();
        let body_text = resp.text().await.map_err(|e| {
            McpError::internal_error(format!("Failed to read response: {}", e), None)
        })?;

        if !status.is_success() {
            return Err(McpError::internal_error(
                format!("GraphQL returned {}: {}", status, body_text),
                None,
            ));
        }

        // 3. Parse the JSON and extract type names
        let json: Value = serde_json::from_str(&body_text)
            .map_err(|e| McpError::internal_error(format!("Invalid JSON: {}", e), None))?;

        let types = json
            .pointer("/data/__schema/types")
            .and_then(|v| v.as_array())
            .ok_or_else(|| McpError::internal_error("Missing __schema.types in response", None))?;

        let names: Vec<String> = types
            .iter()
            .filter_map(|t| t.get("name").and_then(|n| n.as_str()).map(String::from))
            .collect();

        // 4. Format and return
        let output = format!("These are all available type names:\n{}", names.join("\n"));

        Ok(CallToolResult::success(vec![Content::text(output)]))
    }

    #[tool(description = "Return detailed discovery info for a specific GraphQL type/field")]
    async fn get_graphql_type_details(
        &self,
        #[tool(param)]
        #[schemars(description = "Name of schema type")]
        type_name: String,
    ) -> Result<CallToolResult, McpError> {
        // 1. Build the introspection query for a single type
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

        let payload = serde_json::json!({ "query": introspection });

        // 2. Send it to the endpoint
        let client = reqwest::Client::new();
        let resp = client
            .post(&self.endpoint)
            .header("Content-Type", "application/json")
            .json(&payload)
            .send()
            .await
            .map_err(|e| McpError::internal_error(format!("HTTP request error: {}", e), None))?;

        let status = resp.status();
        let body_text = resp.text().await.map_err(|e| {
            McpError::internal_error(format!("Failed to read response: {}", e), None)
        })?;

        if !status.is_success() {
            return Err(McpError::internal_error(
                format!("GraphQL returned {}: {}", status, body_text),
                None,
            ));
        }

        // 3. Parse the JSON and pull out the __type object
        let json: serde_json::Value = serde_json::from_str(&body_text)
            .map_err(|e| McpError::internal_error(format!("Invalid JSON: {}", e), None))?;

        let type_info = json
            .pointer("/data/__type")
            .ok_or_else(|| McpError::internal_error("Missing __type in response", None))?;

        // 4. Pretty-print the JSON fragment for user visibility
        let pretty = serde_json::to_string_pretty(type_info)
            .map_err(|e| McpError::internal_error(format!("Failed to format JSON: {}", e), None))?;

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
        // Build the JSON payload
        let payload = json!({ "query": query });

        // Send the POST request
        let client = reqwest::Client::new();
        let resp = client
            .post(&self.endpoint)
            .header("Content-Type", "application/json")
            .json(&payload)
            .send()
            .await
            .map_err(|e| McpError::internal_error(format!("HTTP request error: {}", e), None))?;

        // Check for non-2xx
        let status = resp.status();
        let text = resp.text().await.map_err(|e| {
            McpError::internal_error(format!("Failed to read response body: {}", e), None)
        })?;

        if !status.is_success() {
            return Err(McpError::internal_error(
                format!("GraphQL endpoint returned {}: {}", status, text),
                None,
            ));
        }

        // Return the raw JSON text as the tool result
        Ok(CallToolResult::success(vec![Content::text(text)]))
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
            instructions: Some("This server lets you connecto to graphql".to_string()),
        }
    }
}
