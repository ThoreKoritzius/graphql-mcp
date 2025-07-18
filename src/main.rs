use anyhow::Result;
use clap::Parser;
use rmcp::{ServiceExt, transport::sse_server::SseServer};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

mod common;
use crate::common::explorer::Explorer;
const BIND_ADDRESS: &str = "0.0.0.0:5001";

#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
struct Args {
    /// GraphQL Server endpoint
    #[arg(long, short = 'e', default_value = "http://127.0.0.1:8000")]
    endpoint: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Tracing
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "debug".to_string().into()),
        )
        .with(
            tracing_subscriber::fmt::layer()
                .with_writer(std::io::stderr)
                .with_ansi(false),
        )
        .init();

    // Parse CLI
    let args = Args::parse();
    tracing::info!("Starting GraphQL-MCP SSE server on {}", BIND_ADDRESS);
    tracing::info!("Proxying GraphQL endpoint: {}", args.endpoint);

    // Build one Explorer instance that we can clone
    let explorer = Explorer::new(args.endpoint.clone()).map_err(|e| {
        tracing::error!("Failed to initialize Explorer: {:?}", e);
        e
    })?;

    // Serve over SSE, and for each new connection clone your Explorer
    let server = SseServer::serve(BIND_ADDRESS.parse()?)
        .await?
        .with_service({
            let explorer = explorer.clone();
            move || explorer.clone()
        });

    // Wait for Ctrl-C
    tokio::signal::ctrl_c().await?;
    tracing::info!("Shutting down SSE server");
    server.cancel();
    Ok(())
}
