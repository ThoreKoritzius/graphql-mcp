#![allow(dead_code)]
use rmcp::{
    Error as McpError,
    RoleServer,
    ServerHandler,
    model::*,
    schemars,
    service::RequestContext,
    tool
};
use bluejay_parser::ast::definition::SchemaDefinition;
use serde_json::json;
use bluejay_core::definition::{ SchemaDefinition as SchemaDefinitionCore};

/// Explorer stores a SchemaDefinition with an explicit lifetime.
pub struct Explorer<'a> {
    pub schema_definition: SchemaDefinition<'a>,
}

impl<'a> Explorer<'a> {
    /// Creates a new Explorer instance with the provided SchemaDefinition.
    pub fn new(schema_definition: SchemaDefinition<'a>) -> Self {
        Explorer { schema_definition }
    }

    /// Creates a resource text using the provided URI and name.
    fn _create_resource_text(&self, uri: &str, name: &str) -> Resource {
        RawResource::new(uri, name.to_string()).no_annotation()
    }

    /// Prints and returns a string representation of the schema's query.
    #[tool(description = "Print and return the schema query")]
    async fn print_schema(&self) -> Result<CallToolResult, McpError> {
        let output = format!("{:#?}", self.schema_definition.query());
        println!("{}", output);
        Ok(CallToolResult::success(vec![Content::text(output)]))
    }
}