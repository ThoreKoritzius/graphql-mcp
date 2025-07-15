use anyhow::Result;
use clap::Parser;
use rmcp::{ServiceExt, transport::stdio};
use std::path::PathBuf;
use tracing_subscriber::{self, EnvFilter};

mod common;

use crate::common::explorer::Explorer;

#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
struct Args {
    /// GraphQL Server endpoint
    #[arg(long, short = 'e', default_value = "http://127.0.0.1:8000")]
    endpoint: String,
}

/// Entry point for the GraphQL-MCP server.
/// This server initializes tracing, parses args, loads the GraphQL schema,
/// serves it over a transport channel (stdio), and waits for requests on default http://localhost:5000/mcp
#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive(tracing::Level::DEBUG.into()))
        .with_writer(std::io::stderr)
        .with_ansi(false)
        .init();

    // Arguemnt parsing
    let args = Args::parse();
    // Start server
    tracing::info!("Starting GraphQL-MCP server");
    let explorer = Explorer::new(args.endpoint).map_err(|e| {
        tracing::error!("Failed to initialize Explorer: {:?}", e);
        e
    })?;
    let service = explorer.serve(stdio()).await.inspect_err(|e| {
        tracing::error!("Serving error: {:?}", e);
    })?;

    // Wait until the server completes
    service.waiting().await?;

    Ok(())
}
