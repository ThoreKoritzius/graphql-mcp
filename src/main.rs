use bluejay_parser::ast::{
    definition::{DefinitionDocument, SchemaDefinition},
    Parse,
};

use bluejay_core::definition::{ SchemaDefinition as SchemaDefinitionCore};


use rmcp::{ServiceExt};

fn main() {
    parse();
}

// parse simple schema
fn parse() {
    let s = std::fs::read_to_string("./src/schema.graphql").unwrap();
    let document = DefinitionDocument::parse(s.as_str()).unwrap();

    let schema_definition: SchemaDefinition =
        SchemaDefinition::try_from(&document).expect("Schema had errors");
    
    println!("{:#?}", schema_definition.query());
}