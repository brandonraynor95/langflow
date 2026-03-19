# Cloud Compatibility Analysis — All Langflow Components

> **Target environment:** IBM WXO ephemeral pods — limited CPU/memory, no persistent storage, no local GPU, no local servers. Network access to external APIs is available.

## Summary

| Status | Count | Description |
|--------|-------|-------------|
| COMPATIBLE | ~330 | Works in cloud as-is |
| INCOMPATIBLE | 13 | Cannot work in cloud — hidden when cloud toggle is on |
| MIXED | 8 | Works but has localhost defaults — defaults overridden in cloud mode |

---

## INCOMPATIBLE Components (`cloud_compatible = False`)

These are **hidden entirely** when cloud mode is active.

| Directory | Component | Class | Reason |
|-----------|-----------|-------|--------|
| `ollama` | Ollama | `ChatOllamaComponent` | Requires local Ollama server at `localhost:11434` |
| `ollama` | Ollama Embeddings | `OllamaEmbeddingsComponent` | Requires local Ollama server for embeddings |
| `lmstudio` | LM Studio | `LMStudioModelComponent` | Requires local LM Studio server at `localhost:1234` |
| `lmstudio` | LM Studio Embeddings | `LMStudioEmbeddingsComponent` | Requires local LM Studio server |
| `vllm` | vLLM | `VllmComponent` | Requires local vLLM GPU inference server at `localhost:8000` |
| `vllm` | vLLM Embeddings | `VllmEmbeddingsComponent` | Requires local vLLM server |
| `FAISS` | FAISS | `FaissVectorStoreComponent` | Requires `persist_directory` for local filesystem storage |
| `files_and_knowledge` | Directory | `DirectoryComponent` | Reads from local filesystem paths |
| `docling` | Docling (Inline) | `DoclingInlineComponent` | Downloads and runs OCR/VLM models locally; heavy compute |
| `vectorstores` | Local DB | `LocalDBComponent` | Local Chroma DB with `persist_directory`; explicitly disabled in cloud with error message |
| `nvidia` | NVIDIA System-Assist | `NvidiaSystemAssistComponent` | Windows-only; requires local GPU driver interaction |

### Also incompatible in the unified model dropdowns

The **Language Model** and **Embedding Model** unified components remain visible but the **Ollama** provider is filtered from their model dropdowns when cloud mode is active.

---

## MIXED Components (cloud_default_overrides applied)

These components **remain visible** but their localhost default values are **cleared** and replaced with placeholder text when cloud mode is active.

| Directory | Component | Class | Field | Default | Cloud Placeholder |
|-----------|-----------|-------|-------|---------|-------------------|
| `chroma` | Chroma DB | `ChromaVectorStoreComponent` | `chroma_server_host` | *(empty)* | "Enter Chroma Cloud host" |
| `qdrant` | Qdrant | `QdrantVectorStoreComponent` | `host` | `localhost` | "Enter Qdrant Cloud host" |
| `weaviate` | Weaviate | `WeaviateVectorStoreComponent` | `url` | `http://localhost:8080` | "Enter Weaviate Cloud URL" |
| `redis` | Redis Chat Memory | `RedisIndexChatMemory` | `host` | `localhost` | "Enter Redis Cloud host" |
| `clickhouse` | ClickHouse | `ClickhouseVectorStoreComponent` | `host` | `localhost` | "Enter ClickHouse Cloud host" |
| `milvus` | Milvus | `MilvusVectorStoreComponent` | `uri` | `http://localhost:19530` | "Enter Milvus Cloud URI" |
| `elastic` | Elasticsearch | `ElasticsearchVectorStoreComponent` | `elasticsearch_url` | `http://localhost:9200` | "Enter Elasticsearch Cloud URL or use Cloud ID" |
| `litellm` | LiteLLM Proxy | `LiteLLMProxyComponent` | `api_base` | `http://localhost:4000/v1` | "Enter LiteLLM proxy URL" |

### Also mixed: SaveToFile

The **Write File** component's "Local" storage option is hidden from the SortableList dropdown when cloud mode is active (via `cloud_incompatible_options` metadata). AWS and Google Drive options remain.

---

## COMPATIBLE Components — Full List by Directory

### LLM Providers (all COMPATIBLE — external API calls)

| Directory | Component | Notes |
|-----------|-----------|-------|
| `anthropic` | Anthropic | Anthropic API |
| `openai` | OpenAI, OpenAI Embeddings | OpenAI API |
| `azure` | Azure OpenAI, Azure OpenAI Embeddings | Azure API |
| `groq` | Groq | Groq Cloud API |
| `cohere` | Cohere, Cohere Embeddings, Cohere Rerank | Cohere API |
| `mistral` | Mistral AI, Mistral AI Embeddings | Mistral API |
| `deepseek` | DeepSeek | DeepSeek API |
| `perplexity` | Perplexity | Perplexity API |
| `google` | Google Generative AI, Google Generative AI Embeddings | Google AI API |
| `vertexai` | Vertex AI, Vertex AI Embeddings | Google Cloud |
| `amazon` | Bedrock, Bedrock Converse, Bedrock Embeddings | AWS API |
| `nvidia` | NVIDIA Model, NVIDIA Embeddings, NVIDIA Rerank, NVIDIA Ingest | NVIDIA API (`integrate.api.nvidia.com`) |
| `ibm` | Watsonx AI, Watsonx Embeddings | IBM Cloud endpoints |
| `huggingface` | HuggingFace Endpoints | HF Inference API |
| `huggingface` | HuggingFace Embeddings Inference | Defaults to `api-inference.huggingface.co` (cloud) |
| `sambanova` | SambaNova | SambaNova Cloud API |
| `baidu` | Qianfan | Baidu API |
| `maritalk` | Maritalk | Maritalk API |
| `xai` | xAI (Grok) | xAI API |
| `novita` | Novita AI | OpenAI-compatible cloud API |
| `openrouter` | OpenRouter | Multi-provider routing API |
| `aiml` | AI/ML Model, AI/ML Embeddings | AI/ML API |
| `cloudflare` | Cloudflare Workers AI Embeddings | Cloudflare API |
| `notdiamond` | Not Diamond | Router API |
| `litellm` | LiteLLM (non-proxy) | LLM routing library |

### Cloud Vector Stores (all COMPATIBLE)

| Directory | Component | Notes |
|-----------|-----------|-------|
| `pinecone` | Pinecone | SaaS vector DB |
| `supabase` | Supabase | Cloud PostgreSQL |
| `mongodb` | MongoDB Atlas | Cloud document DB |
| `pgvector` | PGVector | Works with cloud PostgreSQL (AWS RDS, etc.) |
| `couchbase` | Couchbase | Cloud-managed cluster |
| `vectara` | Vectara, Vectara RAG | SaaS vector/RAG |
| `upstash` | Upstash | Serverless Redis |
| `cassandra` | Cassandra/Astra DB | DataStax Astra cloud |
| `datastax` | Astra DB (12+ components) | All cloud-native Astra DB services |

### Search & Web Tools (all COMPATIBLE)

| Directory | Component | Notes |
|-----------|-----------|-------|
| `tavily` | Tavily Search, Tavily Extract | Cloud search API |
| `exa` | Exa Search | Cloud search API |
| `duckduckgo` | DuckDuckGo | Web search |
| `bing` | Bing Search | Microsoft API |
| `searchapi` | SearchAPI | Multi-engine search |
| `serpapi` | SerpAPI | Search engine results |
| `yahoosearch` | Yahoo Finance | Public finance API |
| `wikipedia` | Wikipedia, Wikidata | Public APIs |
| `wolframalpha` | Wolfram Alpha | Computation API |
| `arxiv` | ArXiv | Public paper API |

### Document Processing (all COMPATIBLE)

| Directory | Component | Notes |
|-----------|-----------|-------|
| `unstructured` | Unstructured API | Cloud document parsing (requires API key) |
| `docling` | Docling Remote | Remote Docling service |
| `docling` | Chunk Docling Document | Text chunking only (no model downloads) |
| `docling` | Export Docling Document | Format conversion only |
| `firecrawl` | Firecrawl (4 components) | Cloud web scraping |
| `scrapegraph` | ScrapeGraph (3 components) | Cloud scraping API |
| `apify` | Apify Actors | Cloud web scraping |
| `confluence` | Confluence | Cloud documentation API |

### Agent Frameworks (all COMPATIBLE)

| Directory | Component | Notes |
|-----------|-----------|-------|
| `models_and_agents` | Agent, Memory, Prompt | Unified agent components |
| `models_and_agents` | Language Model | MIXED at provider level (Ollama filtered) |
| `models_and_agents` | Embedding Model | MIXED at provider level (Ollama filtered) |
| `models_and_agents` | MCP | Supports HTTP clients |
| `crewai` | CrewAI (5 components) | Agent orchestration |
| `agentics` | Semantic Aggregator, Semantic Map, Synthetic Data Generator | LLM-powered data ops |
| `agentql` | AgentQL | Agent API |
| `altk` | ALTK Agent | Agent framework |
| `cuga` | Cuga | Advanced agent |

### Communication & Integrations (all COMPATIBLE)

| Directory | Component | Notes |
|-----------|-----------|-------|
| `Notion` | Notion (8 components) | HTTP API calls |
| `google` | BigQuery, Google Search, Google Serper | Cloud APIs |
| `composio` | Composio (60+ components) | Tool integration platform |
| `assemblyai` | AssemblyAI (6 components) | Cloud speech-to-text |
| `youtube` | YouTube (3 components) | YouTube API |
| `amazon` | S3 Uploader | AWS S3 API |
| `glean` | Glean Search | Enterprise search API |
| `langwatch` | LangWatch | Monitoring API |
| `cleanlab` | Cleanlab (3 components) | Evaluation API |
| `cometapi` | CometAPI | Model routing API |
| `jigsawstack` | JigsawStack (11 components) | AI utility APIs |
| `twelvelabs` | TwelveLabs (2 components) | Video/text embeddings |
| `needle` | Needle | Retriever API |
| `olivya` | Olivya | Outbound calls API |
| `vlmrun` | VLM Run | Video transcription API |
| `icosacomputing` | Combinatorial Reasoner | External API |

### Processing & Utilities (all COMPATIBLE — pure computation)

| Directory | Component | Notes |
|-----------|-----------|-------|
| `processing` | Text Operations, Split Text, Filter Data, etc. | In-memory text/data processing |
| `flow_controls` | Conditional Router, Loop, Listen, Notify, etc. (9 components) | Flow logic |
| `input_output` | Chat Input, Chat Output, Text Input, Text Output, Webhook | I/O components |
| `output_parsers` | Various parsers | JSON/string parsing |
| `textsplitters` | Various splitters | Text chunking |
| `llm_operations` | Batch Run, Guardrails, Lambda Filter, etc. (6 components) | LLM-powered ops |
| `langchain_utilities` | 25+ utility components | Agents, QA chains, SQL tools |
| `utilities` | ID Generator, etc. | Pure utility |
| `tools` | Tool wrappers | Generic tool framework |
| `custom_component` | Custom Component | User template |
| `prototypes` | Python Function | Custom code execution |
| `embeddings` | Embedding Similarity, Text Embedder | Vector math |
| `data` | Various data components | Data manipulation |
| `data_source` | API Request, CSV, JSON, URL, RSS, etc. | Data ingestion |

### Memory (all COMPATIBLE except noted above)

| Directory | Component | Notes |
|-----------|-----------|-------|
| `zep` | Zep Chat Memory | Requires external Zep instance (cloud-deployable) |
| `mem0` | Mem0 | Requires neo4j graph store; disabled in Astra cloud |

### Legacy / Deactivated

| Directory | Component | Notes |
|-----------|-----------|-------|
| `google` | Gmail Loader, Google Drive Search, Google Drive, Google OAuth Token | Legacy; require local credentials files |
| `deactivated` | Various | Deprecated components; should not be used |
| `homeassistant` | Home Assistant Control, List States | Requires local network Home Assistant instance (`192.168.x.x`) |
| `git` | Git Loader, Git Extractor | Clones repos to local temp dirs; requires `git` CLI |

> **Note on legacy Google components:** These are marked `legacy = True` with replacements suggested. They require local credentials JSON files which won't work on ephemeral pods. They're already hidden when "Show Legacy" is off.

> **Note on Home Assistant:** These require a Home Assistant instance on the local network. While technically they make HTTP requests, the default URL points to `192.168.0.10:8123` which is a local network address inaccessible from cloud pods.

> **Note on Git components:** These clone repositories to temp directories and require the `git` command-line tool. While they use temp storage (acceptable on ephemeral pods), the reliance on the `git` binary and local file operations makes them unreliable in constrained environments.
