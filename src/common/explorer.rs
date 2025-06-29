#![allow(dead_code)]
use bluejay_parser::ast::{
    Parse,
    definition::{DefaultContext, DefinitionDocument, SchemaDefinition},
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
    fn get_schema_definition(&self) -> SchemaDefinition {
        let s = std::fs::read_to_string(self.schema_path.clone()).unwrap();
        let s_static: &'static str = Box::leak(s.into_boxed_str());
        let document = DefinitionDocument::<DefaultContext>::parse(s_static).unwrap();
        let leaked_document: &'static DefinitionDocument<DefaultContext> =
            Box::leak(Box::new(document));
        SchemaDefinition::try_from(leaked_document).expect("Schema had errors")
    }

    async fn get_fulll_query(&self) -> Result<CallToolResult, McpError> {
        let schema_definition: SchemaDefinition<'_> = self.get_schema_definition();
        let mut type_details = String::from("Query overview\n");
        type_details.push_str(&format!("{:#?}", schema_definition.query()));

        Ok(CallToolResult::success(vec![Content::text(type_details)]))
    }

    #[tool(description = "Return all available type names")]
    async fn get_type_overview(&self) -> Result<CallToolResult, McpError> {
        let schema_definition: SchemaDefinition<'_> = self.get_schema_definition();
        let type_names: Vec<&str> = schema_definition
            .type_definitions()
            .map(|a| a.name())
            .collect();
        let output = format!(
            "These are all available type names:\n{}",
            type_names.join("\n")
        );
        println!("{}", output);
        Ok(CallToolResult::success(vec![Content::text(output)]))
    }

    #[tool(description = "Return detailed discovery info for a specific GraphQL type/field")]
    async fn get_graphql_type_details(
        &self,
        #[tool(param)]
        #[schemars(description = "Name of schema type")]
        type_name: String,
    ) -> Result<CallToolResult, McpError> {
        let schema_definition = self.get_schema_definition();
        let matching_type = schema_definition.type_definitions().find(|type_def| {
            type_def
                .name()
                .to_lowercase()
                .contains(&type_name.to_lowercase())
        });
        let mut type_details = String::from("Details for type\n");
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
