

// Function: embedding
async fn embedding(query: &str) -> Result<Vec<f32>, Box<dyn std::error::Error>> {
    // Retrieve the OpenAI API key from the environment
    let api_key = std::env::var("OPENAI_API_KEY")?;
    let client = reqwest::Client::new();

    // Build the JSON payload for the OpenAI embedding request
    let payload = serde_json::json!({
        "input": query,
        "model": "text-embedding-3-small"
    });

    // Send the request to the OpenAI embeddings endpoint
    let res = client.post("https://api.openai.com/v1/embeddings")
        .bearer_auth(api_key)
        .json(&payload)
        .send()
        .await?;

    // Deserialize the JSON response
    let json: serde_json::Value = res.json().await?;
    println!("{:?}", json); 
  
    // Extract the embedding vector from the response
    let embedding = json["data"][0]["embedding"]
        .as_array()
        .ok_or("Missing embedding field")?
        .iter()
        .map(|val| val.as_f64().unwrap() as f32)
        .collect();

    Ok(embedding)
}