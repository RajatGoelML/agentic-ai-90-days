# Financial Auction Intelligence RAG Platform – Architecture Review

## Enterprise AI Architect Critical Analysis

---

## Module-by-Module Review

---

### A. Ingestion Layer

#### What's Good
- Separating file intake from classification is correct — it enables independent scaling of I/O vs compute.
- Including OCR as a first-class pipeline element acknowledges the reality of scanned financial documents (common in Indian auction notices, recovery documents, and court filings).
- Layout Detection as a distinct submodule is architecturally sound — financial PDFs have multi-column, mixed table-text layouts that naive extraction destroys.

#### What's Bad / Risks
- **No document deduplication** — enterprise ingestion pipelines for auctions/banks will encounter the same document via multiple channels. Without content-hash deduplication, you'll pollute the index and inflate costs.
- **No document versioning** — financial documents get amended (revised valuation reports, updated annexures). Without version-aware ingestion, you'll retrieve stale data.
- **Missing: Document Quality Gate** — scanned PDFs vary wildly in quality. You need a quality scoring step (DPI check, OCR confidence threshold, page completeness) BEFORE entering the pipeline. Bad quality docs silently degrade retrieval.

#### Scalability Concern
- OCR is CPU/GPU intensive. If you process everything sequentially, a batch of 500 scanned PDFs will bottleneck the entire pipeline. You need an async job queue (Celery + Redis or Temporal) specifically for OCR workloads.

#### Suggested Improvements
| Current | Suggested | Why |
|---------|-----------|-----|
| No dedup | MinHash / SimHash fingerprinting at intake | Prevents index pollution, reduces storage cost |
| No versioning | Document lineage tracker (doc_id + version_id + supersedes_id) | Enables temporal queries ("latest valuation") |
| No quality gate | OCR confidence scorer + DPI validator | Prevents garbage-in-garbage-out |
| Synchronous OCR | Async worker pool (Temporal / Celery) | OCR is 10-100x slower than text extraction |

---

### B. Document Understanding Layer

#### What's Good
- Table Understanding Engine as a dedicated submodule is critical. Financial documents encode 60-80% of decision-relevant data in tables (balance sheets, amortization schedules, bid histories).
- Financial Entity Extraction is essential — identifying amounts, dates, party names, property descriptions, lien positions is domain-specific NER.
- Metadata Enrichment acknowledges that raw text alone is insufficient for enterprise retrieval.

#### What's Bad / Risks
- **Element Extractor is vague** — what elements? Titles? Sections? Headers? Footnotes? This needs sharper definition. In financial docs, footnotes and annexure references carry critical context.
- **No relationship extraction** — financial documents contain cross-references (e.g., "as per Schedule B attached herewith", "refer valuation report dated..."). Without relationship extraction, you lose inter-document and intra-document links.
- **Missing: Document Schema Inference** — different document types (auction notice vs valuation report vs balance sheet) have different implicit schemas. The system should infer and tag the document schema to enable schema-aware retrieval.

#### Architectural Risk
- If Table Understanding Engine and Element Extractor are tightly coupled, a failure in table parsing will cascade to the entire document. These should be **parallel independent extractors** that merge results downstream.

#### Better Alternatives
| Current | Suggested | Why |
|---------|-----------|-----|
| Generic Element Extractor | Typed Element Extractor (title, section, footnote, reference, signature block) | Enables element-type-aware retrieval |
| No relationship extraction | Cross-reference resolver + entity coreference | Enables multi-document reasoning |
| No schema inference | Document type classifier → schema template mapper | Enables structured queries per document type |

#### Industry Trend
- **Docling (IBM)** now supports document structure-aware element classification out of the box. It produces typed elements (title, paragraph, table, list, figure) with hierarchical nesting. This is superior to Unstructured.io for structured financial documents.
- **Azure Document Intelligence** (formerly Form Recognizer) has pre-built models for invoices, receipts, and financial statements. Consider as OCR+structure alternative for specific document types.

---

### C. Chunking Layer

#### What's Good
- Table-Preserving Chunker is architecturally correct. Splitting a balance sheet table across chunks is catastrophic for retrieval.
- Hierarchical Chunk Builder acknowledges that financial documents have natural hierarchy (Document → Section → Subsection → Paragraph/Table).
- Chunk Metadata Attachment is critical for enterprise filtering.

#### What's Bad / Risks
- **Sentence/Recursive Chunker is insufficient for financial text** — financial sentences are often extremely long (legal clauses, property descriptions spanning 200+ words). Recursive character splitting will break mid-entity. You need **semantic boundary detection** that respects financial clause structure.
- **No overlap strategy defined** — chunk overlap is critical for retrieval continuity. Without it, boundary queries will miss relevant content.
- **No chunk size optimization** — different document types may need different chunk sizes. Auction notices (short, dense) vs valuation reports (long, narrative) require different strategies.
- **Missing: Table chunk representation strategy** — how will tables be stored? As raw text? As markdown? As structured JSON? This decision dramatically impacts retrieval quality.

#### Critical Design Decision: Table Representation
| Representation | Pros | Cons | Recommendation |
|---------------|------|------|----------------|
| Raw text | Simple | Loses structure, embeddings poor | ❌ Avoid |
| Markdown table | Preserves structure, embeds reasonably | Large token count | ✅ Good default |
| JSON structured | Machine-readable, metadata-rich | Poor for dense embeddings | ✅ For metadata index |
| Natural language summary + original | Best of both worlds | Requires LLM at ingest time | ✅✅ Best for retrieval |

#### Suggested Improvements
- **Dual-representation for tables**: Store both (a) markdown table as chunk and (b) LLM-generated natural language summary of the table. Embed the summary for semantic search; return the original table for grounding.
- **Adaptive chunk sizing**: 256-512 tokens for narrative text, full-table for tables (regardless of size), 128 tokens for metadata-dense sections.
- **Chunk lineage**: Every chunk must trace back to (document_id, page_number, element_type, section_hierarchy). This enables citation and debugging.

#### Industry Trend
- **Chonkie** is a solid choice for sentence/recursive chunking — it's lightweight and fast.
- **Late chunking** (Jina AI, 2024) embeds the full document first, then chunks — preserving cross-chunk context in embeddings. Consider for long valuation reports.
- **Contextual chunking** (Anthropic pattern) — prepend a short context summary to each chunk before embedding. Dramatically improves retrieval for hierarchical documents.

---

### D. Embedding & Indexing Layer

#### What's Good
- Hybrid retrieval (dense + sparse) is the correct architecture for financial documents where both semantic similarity AND exact keyword matching matter.
- Metadata Index as a separate concern enables complex enterprise filtering (by date, property type, bank, loan amount range).

#### What's Bad / Risks
- **BGE / E5 are general-purpose embeddings** — they have no financial domain specialization. Financial terminology (e.g., "NPA", "SARFAESI", "reserve price", "encumbrance") may not embed well.
- **No embedding fine-tuning strategy** — for enterprise financial RAG, you MUST fine-tune embeddings on your domain corpus. General embeddings will plateau at 70-75% retrieval accuracy.
- **No multi-vector strategy for tables** — tables require token-level matching (which is why ColBERT is mentioned later), but this isn't reflected in the indexing architecture.
- **Missing: Embedding versioning** — when you upgrade models or fine-tune, you need to re-embed. Without versioning, you can't do rolling upgrades.

#### Scalability Concern
- Dense embeddings at scale (millions of chunks) require approximate nearest neighbor (ANN) search. Qdrant handles this, but you need to plan for:
  - Index build time during bulk ingestion
  - Memory requirements (768-dim float32 = 3KB per vector × millions)
  - Incremental index updates without full rebuild

#### Better Alternatives
| Current | Suggested | Why |
|---------|-----------|-----|
| BGE / E5 (general) | BGE-Finance or fine-tuned E5 on financial corpus | 10-15% retrieval improvement on domain queries |
| Single dense vector per chunk | ColBERT-style multi-vector for tables + single vector for text | Token-level matching for tabular data |
| No embedding versioning | Namespaced collections (v1, v2) with A/B routing | Zero-downtime model upgrades |

#### Industry Trend (2025-2026)
- **Matryoshka embeddings** (variable-dimension) — store full 1024-dim but search at 256-dim for speed, re-rank at full dimension. Reduces latency 4x.
- **Binary quantization** in Qdrant — 32x memory reduction with ~3% accuracy loss. Critical for scaling to millions of chunks.
- **Instructor/Nomic embeddings** — allow task-specific prefixes ("search_document:", "search_query:") improving retrieval alignment.

---

### E. Retrieval Orchestration Layer

#### What's Good
- Query Understanding Engine is essential — financial queries are highly varied ("What is the reserve price?" vs "Compare liabilities across all auction lots" vs "Which properties have clear title?").
- Retriever Router acknowledges that different queries need different retrieval paths.
- Reranking Layer is critical — initial retrieval recall is useless without precision optimization via reranking.

#### What's Bad / Risks
- **No query decomposition** — complex financial queries ("What is the net realizable value after deducting all encumbrances and outstanding dues?") require decomposition into sub-queries.
- **No retrieval feedback loop** — if initial retrieval returns low-confidence results, the system should automatically reformulate and retry. Single-shot retrieval is insufficient for complex financial analysis.
- **Retriever Router logic unspecified** — how does the system decide to route to dense vs sparse vs table retrieval? This needs explicit criteria (query type classification or learned routing).
- **Missing: Multi-hop retrieval** — financial due diligence requires following chains (auction notice → property details → valuation report → encumbrance certificate). Single-hop retrieval cannot answer cross-document questions.

#### Architectural Risk
- If Haystack controls retrieval and LlamaIndex also controls retrieval, you have **framework conflict**. Both want to own the retrieval pipeline. This creates:
  - Duplicate abstraction layers
  - Conflicting caching strategies
  - Debugging nightmares

#### Suggested Architecture
```
Query → Query Classifier → Route Decision
                              ├── Narrative Query → Dense Retrieval (Qdrant) → Rerank
                              ├── Exact Match Query → BM25 (Elasticsearch) → Rerank  
                              ├── Table Query → ColBERT multi-vector → Rerank
                              ├── Metadata Query → Filtered retrieval (Qdrant metadata)
                              └── Complex Query → Decompose → Multi-retrieval → Merge → Rerank
```

#### Better Alternatives
| Current | Suggested | Why |
|---------|-----------|-----|
| Haystack + LlamaIndex (dual framework) | Pick ONE: LlamaIndex for hierarchical + custom retrieval components | Eliminates abstraction conflict |
| No query decomposition | LLM-based query decomposer (sub-question query engine in LlamaIndex) | Handles complex multi-part financial queries |
| No feedback loop | Retrieval confidence scorer + auto-reformulation | Improves recall on hard queries |
| Single-hop only | Multi-hop retriever with document graph traversal | Enables cross-document reasoning |

#### Industry Trend
- **Agentic RAG** (2025+) — the retriever itself becomes an agent that decides how many hops, which indices, and when to stop. LlamaIndex's `QueryPlanAgent` and LangGraph's retrieval graphs enable this.
- **RAPTOR** (Recursive Abstractive Processing for Tree-Organized Retrieval) — builds hierarchical summaries for long documents. Ideal for 50+ page valuation reports.

---

### F. Context Engineering Layer

#### What's Good
- Context Compression acknowledges the fundamental constraint: LLM context windows are finite, but financial documents are long.
- Parent-Child Context Expansion is excellent — retrieving a chunk but expanding to its parent section for context is critical for financial paragraphs that reference preceding clauses.
- Citation Mapper enables traceability — non-negotiable for enterprise financial systems.

#### What's Bad / Risks
- **No context prioritization** — when you have 20 relevant chunks but a 4K context budget, how do you decide what to include? This needs explicit prioritization logic (relevance score × information density × recency).
- **No table-text interleaving strategy** — if you retrieve both narrative chunks and table chunks, how do you arrange them in context? Random ordering confuses LLMs.
- **Missing: Contradiction detection** — financial documents may contain conflicting information (different valuations from different dates). The context layer should flag contradictions rather than presenting conflicting evidence naively.

#### Suggested Improvements
- **Context budget allocator**: Given N retrieved chunks and a token budget, allocate proportionally by relevance score with a minimum threshold for citation coverage.
- **Structured context template**: 
  ```
  [Document Metadata]
  [Most Relevant Narrative Evidence]
  [Supporting Tables]
  [Cross-Document Corroboration]
  [Contradictions/Caveats]
  ```
- **Lossy compression via LLM summarization**: For low-relevance supporting context, summarize rather than include verbatim. Preserves signal while reducing tokens.

---

### G. Reasoning / Generation Layer

#### What's Good
- Grounding Validator is critical — financial answers MUST be traceable to source evidence.
- Citation Generator enables audit compliance — essential for banking/financial regulated environments.
- Separating Prompt Builder from Answer Generator allows prompt versioning and A/B testing.

#### What's Bad / Risks
- **No structured output enforcement** — financial answers often need to be structured (amounts, dates, entities, comparisons). Without structured output (JSON mode, function calling), you get inconsistent formats.
- **No confidence scoring** — the system should output a confidence score with every answer. Low-confidence answers should be flagged for human review.
- **No multi-step reasoning** — complex financial questions require chain-of-thought with intermediate verification steps, not single-shot generation.
- **Missing: Calculation verification** — financial queries often involve arithmetic (total liabilities, net value after deductions). LLMs are unreliable at math. You need a calculation verification step (code interpreter or symbolic math).

#### Architectural Risk
- If the Grounding Validator only runs post-generation, you've already wasted tokens on a potentially hallucinated answer. Consider **constrained generation** that only allows claims supported by retrieved evidence.

#### Better Alternatives
| Current | Suggested | Why |
|---------|-----------|-----|
| Unconstrained generation | Structured output (Pydantic models via Instructor library) | Consistent, parseable financial answers |
| No confidence scoring | Calibrated confidence via retrieval score + generation perplexity | Enables human-in-the-loop for uncertain answers |
| No math verification | Tool-augmented generation (Python code interpreter for calculations) | LLMs hallucinate arithmetic; code doesn't |
| Post-hoc grounding only | Inline citation during generation (ALCE-style) | Forces grounding during generation, not after |

#### Industry Trend
- **Instructor** (by Jason Liu) — Pydantic-based structured output extraction from LLMs. Production-proven for financial data extraction.
- **Guardrails AI** — output validation framework with financial-domain validators.
- **Tool-augmented generation** — LLM calls a calculator/spreadsheet tool for numerical questions. Essential for financial accuracy.

---

### H. Evaluation & Observability Layer

#### What's Good
- Including evaluation as a first-class architectural module is correct — most teams bolt this on later and suffer.
- Hallucination Detection is critical for financial compliance.
- Pipeline Tracing enables debugging in production.

#### What's Bad / Risks
- **No ground-truth dataset strategy** — RAGAS and DeepEval need ground-truth Q&A pairs. Who creates them? How are they maintained? Without this, evaluation is meaningless.
- **No A/B testing infrastructure** — when you change chunking strategy or embedding model, how do you measure improvement? You need comparative evaluation.
- **No retrieval regression detection** — a model upgrade might improve average quality but catastrophically regress on specific query types. You need per-category monitoring.
- **Missing: Financial-domain evaluation metrics** — generic RAGAS metrics (faithfulness, relevance) don't capture financial-specific quality (numerical accuracy, table comprehension, temporal correctness).

#### Suggested Improvements
- **Custom financial evaluation suite**:
  - Numerical accuracy (extracted amounts match source)
  - Table comprehension (can system answer questions requiring table understanding)
  - Temporal accuracy (dates, timelines correctly reported)
  - Cross-document consistency (same entity described consistently)
  - Citation completeness (every claim has a source)
- **Shadow evaluation pipeline**: Run new pipeline versions in shadow mode against production queries before cutover.
- **Annotation pipeline**: Build tooling for domain experts to annotate (query, expected_answer, source_evidence) tuples continuously.

---

## Framework & Tool Review

---

### PDF Parsing: pdfplumber → ✅ Good with caveats

**Why it's good**: Excellent table extraction, preserves coordinates, handles multi-column layouts.

**Risk**: Fails on scanned PDFs (it's text-extraction only, not OCR). Fails on complex merged-cell tables.

**Better combination**: 
- `pdfplumber` for text-native PDFs
- `Docling` for structure-aware parsing
- `pdf2image` + `PaddleOCR` for scanned PDFs
- **Marker** (by VikParuchuri) — new open-source tool that converts PDFs to markdown with excellent table/equation handling. Consider as primary parser.

---

### OCR: PaddleOCR → ⚠️ Acceptable but not optimal

**Why it's acceptable**: Open-source, good accuracy on printed text, supports multiple languages.

**Risks**:
- Poor on handwritten annotations (common in bank approval notes)
- Requires GPU for reasonable throughput
- No built-in layout understanding

**Better alternatives**:
| Tool | Advantage | When to Use |
|------|-----------|-------------|
| **Surya** (VikParuchuri) | Layout-aware OCR, better table detection, MIT license | Primary OCR for financial PDFs |
| **EasyOCR** | Simpler, lighter weight | Quick prototyping |
| **Azure Document Intelligence** | Best accuracy, pre-built financial models | If budget allows cloud APIs |
| **Tesseract 5 + preprocessing** | Free, decent for clean scans | Fallback for simple docs |

**Recommendation**: Use **Surya** as primary (layout-aware, open-source, GPU-efficient) with Azure Document Intelligence as premium tier for critical documents.

---

### Layout Detection: LayoutParser → ❌ Outdated

**Problem**: LayoutParser is no longer actively maintained. Last significant update was 2022.

**Better alternatives**:
- **Docling** (IBM, 2024) — includes layout detection as part of its pipeline
- **Surya** — has layout detection built-in
- **YOLO-based custom layout model** — if you need custom financial document layouts
- **Unstructured.io** — includes `hi_res` strategy with layout detection

**Recommendation**: Drop LayoutParser entirely. Use Docling or Surya which integrate layout detection with OCR+parsing.

---

### Excel Processing: openpyxl + pandas → ✅ Good

**Why it's good**: Preserves sheet structure, handles formulas, pandas enables analysis.

**Improvements needed**:
- **Sheet-level metadata** (sheet name as context for chunks)
- **Named range awareness** (financial Excels use named ranges extensively)
- **Formula evaluation** — store both formula and computed value
- **Multi-sheet relationship detection** — summary sheets reference detail sheets
- Consider **calamine** (Rust-based, faster) for large workbooks

---

### Chunking: Chonkie → ✅ Good choice

**Why it's good**: Fast, configurable, supports sentence and recursive strategies.

**What's missing**:
- No table-aware chunking (you'll need custom logic)
- No hierarchical chunking (you'll need to build this)
- Consider **semantic chunking** (embed sentences, split at semantic boundaries) for financial narratives

**Recommendation**: Use Chonkie for text chunking + custom table chunker + hierarchical assembler as three parallel paths.

---

### Vector DB: Qdrant → ✅ Excellent choice

**Why it's excellent**:
- Native hybrid search (dense + sparse in same collection)
- Rich metadata filtering (essential for enterprise: filter by bank, date, property type, amount range)
- Quantization support (binary, scalar) for cost optimization
- Multi-tenancy support (isolate different clients/projects)
- Excellent performance at scale

**Risks**:
- Self-hosted Qdrant requires operational expertise (clustering, backups, monitoring)
- No built-in full-text search (still needs Elasticsearch for complex text queries)

**Alternative consideration**: 
- **Weaviate** — has built-in BM25 + vector search, eliminating need for separate Elasticsearch. Simpler operational footprint.
- Stick with Qdrant if you need maximum metadata filtering flexibility and multi-vector (ColBERT) support.

---

### Hybrid Search: Elasticsearch → ⚠️ Operationally heavy

**Problem**: Running Elasticsearch alongside Qdrant means two search infrastructure systems to maintain, monitor, and scale.

**Better alternatives**:
| Option | Advantage | Trade-off |
|--------|-----------|-----------|
| **Qdrant sparse vectors (SPLADE)** | Single system, native hybrid | Slightly less flexible than full ES |
| **Weaviate (BM25 + vector)** | Single system | Different ecosystem |
| **OpenSearch** | AWS-native, cheaper | Similar complexity to ES |
| **Meilisearch** | Lightweight, fast keyword search | Less enterprise features |

**Recommendation**: Use Qdrant's native sparse vector support (SPLADE encoded) for hybrid search. Only add Elasticsearch if you have complex full-text query requirements (fuzzy matching, phonetic search, complex aggregations).

---

### Retrieval Frameworks: Haystack + LlamaIndex → ❌ Framework conflict

**Critical Issue**: Using both Haystack and LlamaIndex creates:
1. **Abstraction layer conflict** — both want to own the retrieval pipeline
2. **Duplicate concepts** — both have Document, Retriever, Pipeline abstractions
3. **Integration complexity** — keeping both in sync during upgrades
4. **Developer confusion** — which framework handles what?

**Recommendation**: Pick ONE primary framework.

| If you pick... | Use for... | Why |
|----------------|------------|-----|
| **LlamaIndex** | Everything retrieval | Best hierarchical retrieval, document intelligence, sub-question decomposition, agent integration |
| **Haystack** | Everything pipeline | Better pipeline abstraction, cleaner component architecture, better production deployment |

**My recommendation**: **LlamaIndex** as primary retrieval framework because:
- Native hierarchical index (critical for financial document hierarchy)
- Sub-question query engine (handles complex multi-part queries)
- Native multi-document agent
- Better table understanding integration
- Strong Qdrant integration

Use custom components (not Haystack) for anything LlamaIndex doesn't cover.

---

### Workflow Orchestration: LangGraph → ✅ Good for future agentic workflows

**Why it's good**: Stateful, cyclical graph execution. Enables complex multi-step financial analysis workflows.

**Risk**: LangGraph is tightly coupled to LangChain ecosystem. If you're not using LangChain for your core pipeline, the integration tax is high.

**Alternatives to consider**:
- **Temporal** — production-grade workflow orchestration with durability, retries, timeouts. Better for enterprise reliability.
- **Prefect** — Python-native workflow orchestration with observability built in.
- **Custom state machine** (you already have this in your codebase!) — for simpler workflows.

**Recommendation**: Use LangGraph for **agentic reasoning workflows** only (multi-step research, iterative retrieval). Use **Temporal** for **infrastructure workflows** (ingestion pipelines, batch processing, scheduled re-indexing).

---

### Evaluation: RAGAS + DeepEval → ✅ Good combination

**Why it's good**: RAGAS for retrieval quality metrics, DeepEval for generation quality and hallucination detection.

**What's missing**:
- **Domain-specific benchmarks** — create a financial document QA benchmark with 200+ annotated examples
- **Retrieval-specific metrics**: MRR@K, NDCG@K, Recall@K for different query categories
- **Table QA accuracy** — separate metric for table-dependent questions
- **Latency SLA monitoring** — p50, p95, p99 for end-to-end query time

---

### Observability: LangSmith + OpenTelemetry → ✅ Excellent

**Why**: LangSmith for LLM-specific tracing (prompt, completion, tokens, cost). OpenTelemetry for infrastructure-level observability.

**Improvement**: Add **Langfuse** as an open-source alternative to LangSmith for environments where data cannot leave the network (common in banking/financial institutions due to regulatory requirements).

---

## Cross-Cutting Architectural Concerns

---

### 1. Security & Compliance (MISSING)

**Critical Gap**: No mention of:
- Data encryption at rest and in transit
- Access control (document-level, collection-level)
- PII detection and redaction
- Audit logging (who queried what, when)
- Data retention policies
- Regulatory compliance (RBI guidelines for Indian banking, GDPR if applicable)

**This is a showstopper for enterprise financial deployment.**

---

### 2. Multi-Tenancy (MISSING)

- How are different banks/clients isolated?
- Shared index vs per-tenant index?
- Cost attribution per tenant?

**Recommendation**: Use Qdrant's multi-tenancy (payload-based filtering or collection-per-tenant) with API-level access control.

---

### 3. Data Freshness & Sync (MISSING)

- How are documents updated when source changes?
- What triggers re-ingestion?
- How do you handle stale embeddings?

**Recommendation**: Event-driven ingestion (file watcher / webhook) + scheduled full reindex as fallback.

---

### 4. Error Recovery & Resilience (MISSING)

- What happens when OCR fails on a page?
- What happens when the LLM is unavailable?
- What happens when Qdrant is slow?

**Recommendation**: 
- Graceful degradation (skip failed pages, log, continue)
- Circuit breakers on external services
- Fallback retrieval (if vector search fails, fall back to keyword search)

---

### 5. Cost Management (MISSING)

- LLM calls (embedding + generation) are the primary cost driver
- Embedding millions of chunks is expensive
- Re-ranking with cross-encoders is compute-intensive

**Recommendation**:
- Cache frequent queries and their results
- Use smaller models for routing/classification, larger models for generation
- Implement token budgets per query
- Batch embedding calls

---

## Summary Scorecard

| Module | Score | Key Issue |
|--------|-------|-----------|
| Ingestion Layer | 7/10 | Missing dedup, versioning, quality gate |
| Document Understanding | 7/10 | Missing relationship extraction, schema inference |
| Chunking Layer | 6/10 | Table representation strategy undefined, no adaptive sizing |
| Embedding & Indexing | 6/10 | No domain fine-tuning, no multi-vector architecture |
| Retrieval Orchestration | 5/10 | Framework conflict (Haystack + LlamaIndex), no multi-hop |
| Context Engineering | 7/10 | Missing prioritization and contradiction detection |
| Reasoning / Generation | 6/10 | No structured output, no math verification |
| Evaluation & Observability | 7/10 | No ground-truth strategy, no domain-specific metrics |
| Security & Compliance | 0/10 | Completely missing — critical for finance |
| Multi-Tenancy | 0/10 | Not addressed |
| Cost Management | 0/10 | Not addressed |

**Overall Architecture Score: 6.5/10**

---

## Top 10 Recommendations (Priority Order)

1. **Add Security & Compliance module** — non-negotiable for financial enterprise deployment
2. **Resolve framework conflict** — pick LlamaIndex OR Haystack, not both
3. **Replace LayoutParser** — use Docling or Surya (LayoutParser is abandoned)
4. **Define table representation strategy** — dual representation (markdown + NL summary)
5. **Add domain embedding fine-tuning** — general embeddings will cap retrieval quality
6. **Implement multi-hop retrieval** — financial due diligence requires cross-document reasoning
7. **Add structured output enforcement** — use Instructor/Pydantic for consistent financial answers
8. **Add calculation verification** — LLMs cannot reliably do financial math
9. **Eliminate Elasticsearch** — use Qdrant sparse vectors for hybrid search (reduce operational burden)
10. **Build ground-truth evaluation dataset** — without it, you cannot measure improvement

---

## Recommended Final Architecture Stack

| Layer | Tool | Reason |
|-------|------|--------|
| PDF Parsing | Marker + pdfplumber | Best text+table extraction |
| OCR | Surya (primary) + Azure Doc Intelligence (premium) | Layout-aware, accurate |
| Structure | Docling | Typed elements, hierarchy |
| Excel | openpyxl + pandas | Complete workbook understanding |
| Chunking | Chonkie (text) + custom (tables) + contextual prepend | Multi-strategy |
| Embeddings | Fine-tuned BGE/E5 + SPLADE sparse | Domain-optimized hybrid |
| Vector DB | Qdrant (dense + sparse + metadata) | Single system hybrid search |
| Retrieval | LlamaIndex (hierarchical + sub-question + multi-doc) | Best for financial doc intelligence |
| Orchestration | LangGraph (agentic) + Temporal (infrastructure) | Separation of concerns |
| Generation | GPT-4o / Claude + Instructor + code interpreter | Structured, verified answers |
| Evaluation | RAGAS + DeepEval + custom financial metrics | Comprehensive quality |
| Observability | Langfuse (self-hosted) + OpenTelemetry | Banking-compliant tracing |
| Security | Document-level ACL + PII redaction + audit log | Regulatory compliance |

---

*Review conducted from enterprise AI architect perspective. Recommendations prioritize production reliability, financial domain accuracy, and regulatory compliance over theoretical elegance.*

