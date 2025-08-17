use crate::common::graphql_client::{fetch_query, introspect_type_query, unwrap_named_type};
use rmcp::{Error as McpError, ServerHandler, const_string, model::*, schemars, tool};
use serde_json::Value;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct Explorer {
    pub endpoint: String,
}

impl Explorer {
    pub fn new(endpoint: String) -> Result<Self, McpError> {
        println!("Explorer created for GraphQL endpoint: '{}'", endpoint);
        Ok(Explorer { endpoint })
    }
}

// -------------------- tools --------------------
#[tool(tool_box)]
impl Explorer {
    /// Discover Query root fields
    #[tool(description = "List Query root fields (name, args, return type)")]
    pub async fn get_query_fields(&self) -> Result<CallToolResult, McpError> {
        let q = introspect_type_query("Query");
        let json = match fetch_query(&self.endpoint, &q).await {
            Ok(j) => j,
            Err(err) => return Ok(err),
        };

        let fields = json
            .pointer("/data/__type/fields")
            .cloned()
            .unwrap_or(Value::Null);

        let out = serde_json::json!({
            "queryFields": fields
        });

        Ok(CallToolResult::success(vec![Content::text(
            serde_json::to_string_pretty(&out).unwrap(),
        )]))
    }

    /// Inspect a single Query field in depth:
    /// - signature.args augmented with namedType/namedKind
    /// - inputObjects: map input object name -> its __type node
    /// - returnShape: heuristics + full typeDetails for the return type
    #[tool(
        description = "Inspect a Query field: returns signature, input object shapes, and return-type shape"
    )]
    pub async fn inspect_field(
        &self,
        #[tool(param)]
        #[schemars(description = "Name of the Query field to inspect (e.g. 'astronauts')")]
        field_name: String,
    ) -> Result<CallToolResult, McpError> {
        // Introspect Query (find the field)
        let q = introspect_type_query("Query");
        let json = match fetch_query(&self.endpoint, &q).await {
            Ok(j) => j,
            Err(err) => return Ok(err),
        };

        let fields = json
            .pointer("/data/__type/fields")
            .and_then(|v| v.as_array());
        let field = match fields {
            Some(arr) => arr
                .iter()
                .find(|f| f.get("name").and_then(|n| n.as_str()) == Some(field_name.as_str())),
            None => None,
        };

        let field = match field {
            Some(f) => f.clone(),
            None => {
                // Propagate a clear CallToolResult::error so callers/tooling don't have double-wrapped errors.
                let available = fields
                    .map(|a| {
                        a.iter()
                            .filter_map(|f| f.get("name").and_then(|n| n.as_str()))
                            .collect::<Vec<_>>()
                            .join(", ")
                    })
                    .unwrap_or_else(|| "<could not list>".to_string());
                let msg = format!(
                    "Field '{}' not found on Query. Available fields: {}",
                    field_name, available
                );
                return Ok(CallToolResult::error(vec![Content::text(msg)]));
            }
        };

        // Build signature with unwrapped named types
        let mut signature_args: Vec<Value> = Vec::new();
        let mut input_objects: HashMap<String, Value> = HashMap::new();

        if let Some(args) = field.get("args").and_then(|a| a.as_array()) {
            for arg in args {
                let mut arg_node = arg.clone();
                if let Some(t) = arg.get("type") {
                    if let Some((name, kind)) = unwrap_named_type(t) {
                        arg_node.as_object_mut().map(|m| {
                            m.insert("namedType".to_string(), Value::String(name.clone()));
                            m.insert("namedKind".to_string(), Value::String(kind.clone()));
                        });
                    }
                }
                signature_args.push(arg_node);
            }
        }

        // Introspect any input objects referenced by args
        for arg in signature_args
            .iter()
            .filter_map(|a| a.get("namedType").and_then(|n| n.as_str()))
        {
            let q_in = introspect_type_query(arg);
            if let Ok(j) = fetch_query(&self.endpoint, &q_in).await {
                if let Some(tn) = j.pointer("/data/__type") {
                    input_objects.insert(arg.to_string(), tn.clone());
                }
            }
        }

        // Inspect return type details and heuristics
        let mut return_shape = serde_json::Map::new();
        if let Some(ret_type) = field.get("type") {
            if let Some((ret_name, _ret_kind)) = unwrap_named_type(ret_type) {
                let q_ret = introspect_type_query(&ret_name);
                if let Ok(j) = fetch_query(&self.endpoint, &q_ret).await {
                    if let Some(rt) = j.pointer("/data/__type") {
                        let fields_arr = rt.pointer("/fields").and_then(|f| f.as_array());
                        let has_total_count = fields_arr.map_or(false, |arr| {
                            arr.iter().any(|f| {
                                f.get("name").and_then(|n| n.as_str()) == Some("totalCount")
                            })
                        });
                        let has_results = fields_arr.map_or(false, |arr| {
                            arr.iter()
                                .any(|f| f.get("name").and_then(|n| n.as_str()) == Some("results"))
                        });
                        let has_nodes = fields_arr.map_or(false, |arr| {
                            arr.iter()
                                .any(|f| f.get("name").and_then(|n| n.as_str()) == Some("nodes"))
                        });
                        let has_edges = fields_arr.map_or(false, |arr| {
                            arr.iter()
                                .any(|f| f.get("name").and_then(|n| n.as_str()) == Some("edges"))
                        });
                        let has_page_info = fields_arr.map_or(false, |arr| {
                            arr.iter()
                                .any(|f| f.get("name").and_then(|n| n.as_str()) == Some("pageInfo"))
                        });

                        return_shape.insert(
                            "namedReturnType".to_string(),
                            Value::String(ret_name.clone()),
                        );
                        return_shape.insert("typeDetails".to_string(), rt.clone());
                        return_shape
                            .insert("hasTotalCount".to_string(), Value::Bool(has_total_count));
                        return_shape.insert("hasResults".to_string(), Value::Bool(has_results));
                        return_shape.insert("hasNodes".to_string(), Value::Bool(has_nodes));
                        return_shape.insert("hasEdges".to_string(), Value::Bool(has_edges));
                        return_shape.insert("hasPageInfo".to_string(), Value::Bool(has_page_info));

                        // Try to detect element type for connections (results/nodes/edges.node)
                        let mut element_type_name: Option<String> = None;
                        if let Some(fields_arr) = rt.pointer("/fields").and_then(|f| f.as_array()) {
                            for f in fields_arr {
                                if let Some(fname) = f.get("name").and_then(|n| n.as_str()) {
                                    if fname == "results" || fname == "nodes" {
                                        if let Some(typ) = f.get("type") {
                                            if let Some((ename, _)) = unwrap_named_type(typ) {
                                                element_type_name = Some(ename);
                                                break;
                                            }
                                        }
                                    }
                                    if fname == "edges" {
                                        if let Some(typ) = f.get("type") {
                                            if let Some((edges_typename, _)) =
                                                unwrap_named_type(typ)
                                            {
                                                let q_edges =
                                                    introspect_type_query(&edges_typename);
                                                if let Ok(j2) =
                                                    fetch_query(&self.endpoint, &q_edges).await
                                                {
                                                    if let Some(edges_td) = j2
                                                        .pointer("/data/__type/fields")
                                                        .and_then(|x| x.as_array())
                                                    {
                                                        for ef in edges_td {
                                                            if let Some(en) = ef
                                                                .get("name")
                                                                .and_then(|n| n.as_str())
                                                            {
                                                                if en == "node" {
                                                                    if let Some((nn, _)) =
                                                                        unwrap_named_type(
                                                                            &ef["type"],
                                                                        )
                                                                    {
                                                                        element_type_name =
                                                                            Some(nn);
                                                                        break;
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        if let Some(el) = element_type_name {
                            return_shape.insert("elementType".to_string(), Value::String(el));
                        }
                    }
                }
            }
        }

        let out = serde_json::json!({
            "field": field.get("name").cloned().unwrap_or(Value::String(field_name.clone())),
            "signature": {
                "args": signature_args,
                "type": field.get("type").cloned().unwrap_or(Value::Null),
                "description": field.get("description").cloned().unwrap_or(Value::Null)
            },
            "inputObjects": input_objects,
            "returnShape": Value::Object(return_shape)
        });

        Ok(CallToolResult::success(vec![Content::text(
            serde_json::to_string_pretty(&out).unwrap(),
        )]))
    }

    /// Execute any GraphQL query. Returns success JSON or propagates the error
    #[tool(description = "Execute a precise GraphQL query and return the response JSON")]
    pub async fn execute_query(
        &self,
        #[tool(param)]
        #[schemars(description = "GraphQL query text (use variables where possible)")]
        query: String,
    ) -> Result<CallToolResult, McpError> {
        let json = match fetch_query(&self.endpoint, &query).await {
            Ok(j) => j,
            Err(err) => return Ok(err),
        };

        if json.get("errors").is_some() {
            let payload = serde_json::to_string_pretty(&json)
                .unwrap_or_else(|_| "<unserializable error>".to_string());
            return Ok(CallToolResult::error(vec![Content::text(payload)]));
        }

        let pretty = serde_json::to_string_pretty(&json)
            .unwrap_or_else(|_| format!("Could not pretty-print response: {:?}", json));
        Ok(CallToolResult::success(vec![Content::text(pretty)]))
    }
}

const_string!(Echo = "echo");

#[tool(tool_box)]
impl ServerHandler for Explorer {
    fn get_info(&self) -> ServerInfo {
        ServerInfo {
            protocol_version: ProtocolVersion::V_2024_11_05,
            capabilities: ServerCapabilities::builder().enable_tools().build(),
            server_info: Implementation::from_build_env(),
            instructions: Some(
                "GraphQL Toolserver to retrieve information:\n\
                1) Call get_query_fields() to discover Query root fields.\n\
                2) Call inspect_field(<field>) for the chosen root field. Use the returned 'signature' and 'inputObjects' to learn exact arg names and input-object shapes.\n\
                3) Inspect 'returnShape' from inspect_field(). If 'hasTotalCount' is true, prefer querying totalCount for counts. If returnShape contains 'elementType', that's the object type for results/nodes.\n\
                4) When building selection sets: NEVER assume object fields are scalars. If any selected field is an OBJECT, you MUST include a nested selection (e.g. agency { id name }). Use the typeDetails returned from inspect_field() to choose scalar fields (id,name,+scalars).\n\
                5) Build queries using variables (preferred) and call execute_query(query)."
                .to_string(),
            ),
        }
    }
}
