#![allow(dead_code)]
use rmcp::{Error as McpError, ServerHandler, model::*, tool};

use bluejay_parser::ast::{
    Parse,
    definition::{DefinitionDocument, SchemaDefinition},
};

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

    #[tool(description = "Return the GraphQL schema query")]
    async fn get_schema(&self) -> Result<CallToolResult, McpError> {
        let s = std::fs::read_to_string(self.schema_path.clone()).unwrap();
        let document = DefinitionDocument::parse(s.as_str()).unwrap();
        let schema_definition: SchemaDefinition =
            SchemaDefinition::try_from(&document).expect("Schema had errors");

        let output = format!("{:#?}", schema_definition.query());
        println!("{}", output);
        Ok(CallToolResult::success(vec![Content::text(output)]))
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
