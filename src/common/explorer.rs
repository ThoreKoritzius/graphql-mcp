#![allow(dead_code)]
use bluejay_parser::ast::{
    Parse,
    definition::{DefinitionDocument, SchemaDefinition},
};
use rmcp::{Error as McpError, ServerHandler, model::*, schemars, tool};

use bluejay_core::definition::SchemaDefinition as SchemaDefinitionCore;

#[derive(Debug, Clone)]
pub struct Explorer {
    pub schema_path: String,
}

#[tool(tool_box)]
impl Explorer {
    pub fn new(schema_path: String) -> Result<Self, McpError> {
        std::fs::read_to_string(&schema_path).map_err(|e| {
            McpError::invalid_params(
                format!("Invalid schema path or unreadable file: {}", e),
                None,
            )
        })?;

        Ok(Explorer { schema_path })
    }

    #[tool(description = "Return the GraphQL entry point")]
    async fn get_schema_overview(&self) -> Result<CallToolResult, McpError> {
        let s = std::fs::read_to_string(self.schema_path.clone()).unwrap();
        let document = DefinitionDocument::parse(s.as_str()).unwrap();
        let schema_definition: SchemaDefinition =
            SchemaDefinition::try_from(&document).expect("Schema had errors");

        // Return the entry point from the GraphQL schema (assumed to be the query type)
        let entry_point = format!("{:#?}", schema_definition.query());
        Ok(CallToolResult::success(vec![Content::text(entry_point)]))
    }

    #[tool(description = "Return detailed discovery info for a specific GraphQL type/field")]
    async fn get_graphql_type_details(
        &self,
        #[tool(param)]
        #[schemars(description = "The name of the GraphQL type")]
        type_name: String,
    ) -> Result<CallToolResult, McpError> {
        let file_contents = std::fs::read_to_string(self.schema_path.clone()).unwrap();
        let document = DefinitionDocument::parse(file_contents.as_str()).unwrap();
        let graphql_schema: SchemaDefinition =
            SchemaDefinition::try_from(&document).expect("Schema had errors");

        let matching_type = graphql_schema.type_definitions().find(|type_def| {
            type_def
                .name()
                .to_lowercase()
                .contains(&type_name.to_lowercase())
        });
        let mut type_details = String::from("Details for GraphQL type\n");
        type_details.push_str(&format!("{:#?}", matching_type));
        Ok(CallToolResult::success(vec![Content::text(type_details)]))
    }
}

#[tool(tool_box)]
impl ServerHandler for Explorer {
    fn get_info(&self) -> ServerInfo {
        ServerInfo {
            instructions: Some("GraphQL schema connector".into()),
            capabilities: ServerCapabilities::builder().enable_tools().build(),
            ..Default::default()
        }
    }
}
