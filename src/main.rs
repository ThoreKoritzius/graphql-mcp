use anyhow::Result;
use clap::{Parser, ValueEnum};
use rmcp::transport::sse_server::SseServer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

mod common;
use crate::common::graphql_discovery::Explorer as DiscoveryExplorer;
use crate::common::graphql_fullschema::Explorer as FullschemaExplorer;

const BIND_ADDRESS: &str = "0.0.0.0:5001";

#[derive(ValueEnum, Clone, Debug)]
enum Strategy {
    Discovery,
    Fullschema,
}

#[derive(Parser, Debug)]
#[command(version, about)]
struct Args {
    /// GraphQL Server endpoint
    #[arg(long, short = 'e', default_value = "http://127.0.0.1:8000")]
    endpoint: String,

    /// Exploration strategy
    #[arg(long, value_enum, default_value_t = Strategy::Discovery)]
    strategy: Strategy,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Tracing
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "debug".into()),
        )
        .with(
            tracing_subscriber::fmt::layer()
                .with_writer(std::io::stderr)
                .with_ansi(false),
        )
        .init();

    let args = Args::parse();
    tracing::info!("Starting GraphQL-MCP SSE server on {}", BIND_ADDRESS);
    tracing::info!("Proxying GraphQL endpoint: {}", args.endpoint);
    tracing::info!("Exploration strategy: {:?}", args.strategy);

    // Macro to avoid repeating explorer init + server wiring.
    macro_rules! serve_with {
        ($explorer_ty:ty, $name:expr) => {{
            let explorer = <$explorer_ty>::new(args.endpoint.clone()).map_err(|e| {
                tracing::error!("Failed to init {} Explorer: {:?}", $name, e);
                e
            })?;
            SseServer::serve(BIND_ADDRESS.parse()?)
                .await?
                .with_service({
                    let explorer = explorer.clone();
                    move || explorer.clone()
                })
        }};
    }

    let server = match args.strategy {
        Strategy::Discovery => serve_with!(DiscoveryExplorer, "Discovery"),
        Strategy::Fullschema => serve_with!(FullschemaExplorer, "Fullschema"),
    };

    // Wait for Ctrl-C, then stop.
    tokio::signal::ctrl_c().await?;
    tracing::info!("Shutting down SSE server");
    server.cancel();

    Ok(())
}
