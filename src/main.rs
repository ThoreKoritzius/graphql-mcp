use bluejay_parser::ast::{
    definition::{DefinitionDocument, SchemaDefinition},
    Parse,
};

use bluejay_core::definition::{ SchemaDefinition as SchemaDefinitionCore};

use anyhow::Result;
use rmcp::{ServiceExt};
use tracing_subscriber::{self, EnvFilter};

mod common;

use crate::common::explorer::Explorer;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize the tracing subscriber with file and stdout logging
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive(tracing::Level::DEBUG.into()))
        .with_writer(std::io::stderr)
        .with_ansi(false)
        .init();

    tracing::info!("Starting MCP server");


    let s = std::fs::read_to_string("./src/schema.graphql").unwrap();
    let document = DefinitionDocument::parse(s.as_str()).unwrap();

    let schema_definition: SchemaDefinition =
        SchemaDefinition::try_from(&document).expect("Schema had errors");
    
    let explorer = Explorer::new(schema_definition);


    //let service = Explorer::new(schema_definition).serve().await.inspect_err(|e| {
    //     tracing::error!("serving error: {:?}", e);
   // })?;
    
    //example parsing function
    parse();

    /*let service = Explorer::new().serve(stdio()).await.inspect_err(|e| {
        tracing::error!("serving error: {:?}", e);
    })?;

    service.waiting().await?; */

    //TODO: implement MCP tools
    Ok(())

}


// parse simple schema
fn parse() {
    let s = std::fs::read_to_string("./src/schema.graphql").unwrap();
    let document = DefinitionDocument::parse(s.as_str()).unwrap();

    let schema_definition: SchemaDefinition =
        SchemaDefinition::try_from(&document).expect("Schema had errors");
    
    println!("{:#?}", schema_definition.query());
}