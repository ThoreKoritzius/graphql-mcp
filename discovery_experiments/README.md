# GraphQL Schema Discovery Experiments

This project provides scripts to experiment with schema discovery for GraphQL MCP Servers.

Our approach flattens the schema into a `Type->Field` structure, embeds each entry, and stores them in a vector database. This enables fast, flexible search via cosine similarity, with optional constraints based on schema dependencies.

This example indexes the benchmark schema from the [GraphQL-WG-Benchmark](https://github.com/graphql/ai-wg/blob/main/benchmark/GraphQL%20Schema%20Benchmark%20Suite.md).


## Getting Started

1. Create a `.env` file with your API key:
   ```
   OPENAI_API_KEY=<your-openai-key>
   ```

2. Run a vector search (type-to-field) with:
   ```
   python3 query.py --query "What kinds of rooms does the Hilton Downtown have?" --embeddings indexed_benchmark
   ```

**Arguments:**
- `--topk` (int, default=10): Maximum number of results.
- `--constrain-results` (bool, default=True): If set, results will be recursively grouped and expanded by signature/type relation using `constrain_results_recursively`.

Optional: Create index based on your schema
```
python3 create_index.py --input "benchmark_schema.txt" --out indexed_benchmark 
```

## Idea
One could combine discovery with filtering. If discovery simply applies a scoring function on a flattened layer, we can select based on `top_k` or relevance thresholds. A quick coding example (using OAI embeddings) to test this with the benchmark dataset. Each flattened `type->field` combo (644 instances) is embedded and scored by cosine similarity.

query="I need to cancel part of my reservation and get a refund, can you help me with that?", top_k=5
``` results
CancellationPolicy
  refundableUntilHours [score=0.352, signature=Int!]
RoomType
  cancellationPolicy [score=0.348, signature=CancellationPolicy]
Hotel
  cancellationPolicy [score=0.347, signature=CancellationPolicy]
Refund
  payment [score=0.337, signature=Payment!]
Mutation
  cancelBooking [score=0.334, signature=Booking!]
```

query="What kinds of rooms does the Hilton Downtown have?", top_k=7
``` results
Hotel
  rooms [score=0.366, signature=RoomTypeConnection!]
  conferenceRooms [score=0.349, signature=[ConferenceRoom!]]
HotelFeatures
  CONFERENCE_HALL [score=0.347, signature=Boolean!]
  STEAM_ROOM [score=0.346, signature=Boolean!]
  MEETING_ROOMS [score=0.346, signature=Boolean!]
  GAME_ROOM [score=0.342, signature=Boolean!]
  BUSINESS_CENTER [score=0.341, signature=Boolean!]
```

However, this does not yet include relevant graph connections constrains in the lookup, just matching fields based on the query. For example, "Hotel->rooms" is of type RoomTypeConnection, but LLM doesn't know that type. If we **constrain** the rest of the results to the previous signature and match **recursively with breadth-first expansion** we would constrain based on similarity and type dependencies together until we finish the `top_k` window

``` results
Hotel
  rooms [score=0.366, signature=RoomTypeConnection!]
RoomTypeConnection
  totalCount [score=0.236, signature=Int!]
  edges [score=0.235, signature=[RoomTypeEdge!]!]
RoomTypeEdge
  node [score=0.252, signature=RoomType!]
RoomType
  id [score=0.301, signature=ID!]
  name [score=0.300, signature=String!]
  description [score=0.292, signature=String]
```


So, we could recursively constrain the results to improve relevant field results, to expand based on the relevant fields.