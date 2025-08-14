use rmcp::model::{CallToolResult, Content};
use serde_json::Value;

pub async fn fetch_query(endpoint: &str, graphql_query: &str) -> Result<Value, CallToolResult> {
    let payload = serde_json::json!({ "query": graphql_query });

    let client = reqwest::Client::new();
    let resp = match client
        .post(endpoint)
        .header("Content-Type", "application/json")
        .json(&payload)
        .send()
        .await
    {
        Ok(r) => r,
        Err(e) => {
            let msg = format!(
                "Could not contact GraphQL endpoint at '{}'.\nNetwork error: {}",
                endpoint, e
            );
            return Err(CallToolResult::error(vec![Content::text(msg)]));
        }
    };

    let status = resp.status();
    let body_text = match resp.text().await {
        Ok(t) => t,
        Err(e) => {
            let msg = format!(
                "GraphQL endpoint '{}' responded, but reading the response failed: {}",
                endpoint, e
            );
            return Err(CallToolResult::error(vec![Content::text(msg)]));
        }
    };

    if !status.is_success() {
        let msg = format!(
            "GraphQL endpoint '{}' returned HTTP {}: {}",
            endpoint, status, body_text
        );
        return Err(CallToolResult::error(vec![Content::text(msg)]));
    }

    let json: Value = match serde_json::from_str(&body_text) {
        Ok(j) => j,
        Err(e) => {
            let msg = format!(
                "Invalid JSON received from endpoint '{}': {}\nRaw response:\n{}",
                endpoint, e, body_text
            );
            return Err(CallToolResult::error(vec![Content::text(msg)]));
        }
    };

    Ok(json)
}
