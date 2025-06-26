use anyhow::Result;
use rmcp::{
    ServerHandler, ServiceExt,
    transport::stdio,
};
use tracing_subscriber::{self, EnvFilter};

mod common;

use crate::common::explorer::Explorer;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive(tracing::Level::DEBUG.into()))
        .with_writer(std::io::stderr)
        .with_ansi(false)
        .init();

    tracing::info!("Starting GraphQL-MCP server");


    let service = Explorer::new("./src/schema.graphql".to_string()).serve(stdio()).await.inspect_err(|e| {
        tracing::error!("serving error: {:?}", e);
    })?;

    service.waiting().await?;

    Ok(())
}