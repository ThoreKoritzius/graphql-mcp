#![allow(dead_code)]
use rmcp::{
    Error as McpError,
    RoleServer,
    ServerHandler,
    model::*,
    tool,
};


use bluejay_parser::ast::{
    definition::{DefinitionDocument, SchemaDefinition},
    Parse,
};

use bluejay_core::definition::{ SchemaDefinition as SchemaDefinitionCore};

#[derive(Debug, Clone)]
pub struct Explorer {
    pub schema_path: String,
}

#[tool(tool_box)]
impl Explorer {
    pub fn new(schema_path: String) -> Self {
        Explorer { schema_path }
    }

    #[tool(description = "Print and return the schema query")]
    async fn print_schema(&self) -> Result<CallToolResult, McpError> {
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