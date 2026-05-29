# Structured RAG POC — 1 Day (4-6 Hours)

## Objective

Build an end-to-end RAG pipeline over **structured financial documents** (Excel sheets, CSVs, structured tables in PDFs) to gain hands-on familiarity with:

- **Docling** (IBM) — structure-aware document understanding
- **Unstructured.io** — element-based parsing with built-in chunking
- **pdfplumber** — baseline table extraction
- Table extraction & preservation (compare 3 tools head-to-head)
- Structured chunking strategies
- Metadata-rich embeddings
- Hybrid retrieval (dense + sparse)
- Structured answer generation

This POC directly maps to Layers B, C, D, E, G of the enterprise architecture.

---

## What You'll Build

A system that can:
1. Ingest an Excel file (loan portfolio / auction data)
2. Ingest a structured PDF with tables (bank balance sheet or auction notice)
3. Extract and preserve table structure
4. Create metadata-enriched chunks
5. Store in a vector DB with metadata filtering
6. Answer questions like:
   - "What is the total outstanding amount for NPA accounts?"
   - "List all properties with reserve price above 50 lakhs"
   - "What are the liabilities in Schedule B?"

---

## Timeline

| Time Block | Activity | Duration |
|-----------|----------|----------|
| Block 1 | Setup + Data Preparation | 30 min |
| Block 2 | Excel Ingestion via Docling + Batch Pipeline | 60 min |
| Block 3A | PDF Table Extraction — pdfplumber (baseline) | 30 min |
| Block 3B | PDF Parsing — Docling (structure-aware) | 45 min |
| Block 3C | PDF Parsing — Unstructured.io (element-based) | 45 min |
| Block 4 | Chunking + Embedding + Indexing | 45 min |
| Block 5 | Retrieval + QA Pipeline | 45 min |
| Block 6 | Compare Parsers + Evaluation + Observations | 30 min |

> Total: ~5.5-6 hours. Block 2 now uses Docling for Excel (production-grade for multi-file scenarios).

---

## Block 1: Setup + Data Preparation (30 min)

### Environment Setup

```bash
# Core dependencies
pip install pandas openpyxl pdfplumber qdrant-client sentence-transformers openai python-dotenv rich
pip install llama-index llama-index-vector-stores-qdrant llama-index-embeddings-huggingface

# Docling (IBM) — structure-aware document understanding
pip install docling

# Unstructured.io — element-based document parsing
pip install "unstructured[pdf]" unstructured-client
# Note: For full unstructured features, you may also need:
# pip install "unstructured[all-docs]"  (heavier install, includes OCR deps)
```

> **Why both Docling and Unstructured?**  
> - **Docling** (by IBM) excels at structure-aware parsing — it understands document hierarchy, typed elements (title, paragraph, table, list), and outputs clean structured JSON/Markdown. Best for clean, well-formatted PDFs.
> - **Unstructured.io** excels at element-based chunking with metadata, handles messy real-world docs, and supports 25+ file formats. Has a `hi_res` strategy with layout model for complex layouts.
> - In this POC we compare both against pdfplumber to see which gives best results for YOUR financial documents.

### Sample Data to Use

Use publicly available financial data:

1. **Excel**: Download any sample loan dataset
   - [Lending Club Loan Data (Kaggle)](https://www.kaggle.com/datasets/wordsforthewise/lending-club)
   - OR create a small Excel with 20-30 rows mimicking an auction portfolio:
     ```
     | Loan ID | Borrower | Outstanding | Property | Reserve Price | Status |
     ```

2. **Structured PDF with Tables**: 
   - [Sample Bank Balance Sheet PDF](https://www.rbi.org.in/Scripts/AnnualReportPublications.aspx) — any RBI annual report
   - OR use any publicly available auction notice PDF from [eBkray](https://ebkray.nic.in/)
   - OR create a 2-page PDF with tables using any tool

### Project Structure

```
rag_Poc_Structured/
├── RAG_POC_STRUCTURED_PLAN.md
├── data/
│   ├── sample_loan_portfolio.xlsx
│   ├── sample_financial_statement.xlsx
│   └── sample_auction_notice.pdf
├── 01a_excel_docling.py              (Docling-based Excel ingestion)
├── 01b_excel_pandas_fallback.py      (pandas fallback for comparison)
├── 01c_excel_multi_file.py           (batch Excel processing)
├── 02a_pdf_pdfplumber.py
├── 02b_pdf_docling.py
├── 02c_pdf_unstructured.py
├── 02d_compare_parsers.py
├── 03_chunking_and_indexing.py
├── 04_retrieval_qa.py
├── 05_evaluation.py
└── requirements.txt
```

---

## Block 2: Excel Ingestion via Docling + Multi-File Strategy (60 min)

### Goal
Ingest Excel files using **Docling** for structure-aware table understanding, then build multiple chunking strategies. Since your real project will have many Excels, we also build a **batch ingestion pipeline**.

### Why Docling for Excel (not just pandas)
- **Docling understands table structure** — it identifies headers, data rows, merged cells, and multi-sheet relationships
- **Consistent API** — same `DocumentConverter` for PDFs AND Excels (one pipeline for everything)
- **Typed elements** — tables come out as proper Table elements with metadata, not just raw DataFrames
- **Handles complex Excels** — merged cells, multi-row headers, named ranges, multiple tables per sheet
- **Markdown/JSON export** — tables export cleanly for LLM context
- pandas is still used as a **secondary strategy** for numerical analysis and row-level chunking

### Key Concepts to Learn
- Docling Excel conversion (structure-aware)
- Multi-sheet handling
- Table-as-document vs row-as-document strategies
- Batch processing multiple Excel files
- Metadata-rich table chunks for enterprise filtering

### Implementation: `01a_excel_docling.py`

```python
"""
Excel ingestion using Docling — structure-aware table understanding.
Docling treats Excel tables as first-class structured elements.
"""
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from pathlib import Path
from collections import Counter

# --- Step 1: Initialize Docling Converter ---
converter = DocumentConverter()

excel_path = "data/sample_loan_portfolio.xlsx"
print(f"{'='*60}")
print(f"DOCLING EXCEL INGESTION: {excel_path}")
print(f"{'='*60}")

# --- Step 2: Convert Excel via Docling ---
result = converter.convert(excel_path)
doc = result.document

# --- Step 3: Export as Markdown (Docling's clean table output) ---
markdown_output = doc.export_to_markdown()
print(f"\n--- Docling Markdown Export ---")
print(markdown_output[:2000])

# --- Step 4: Iterate over elements (tables, text, headers) ---
documents_docling_excel = []

for item, level in doc.iterate_items():
    element_type = item.__class__.__name__
    
    if hasattr(item, 'export_to_markdown'):
        content = item.export_to_markdown()
    elif hasattr(item, 'text') and item.text:
        content = item.text
    else:
        continue
    
    if not content or len(content.strip()) < 5:
        continue
    
    documents_docling_excel.append({
        "content": content,
        "metadata": {
            "source": str(excel_path),
            "element_type": element_type.lower(),
            "hierarchy_level": level,
            "parser": "docling",
            "file_type": "excel",
        }
    })

print(f"\n[Docling] Extracted {len(documents_docling_excel)} elements from Excel")
print(f"\nElement types found:")
type_counts = Counter(d["metadata"]["element_type"] for d in documents_docling_excel)
for t, count in type_counts.most_common():
    print(f"  {t}: {count}")

# --- Step 5: Show extracted tables ---
print(f"\n--- Tables Extracted ---")
tables = [d for d in documents_docling_excel if d["metadata"]["element_type"] == "table"]
for i, t in enumerate(tables[:3]):
    print(f"\n[Table {i+1}] (level={t['metadata']['hierarchy_level']})")
    print(t["content"][:500])

# --- Step 6: Build chunking strategies from Docling output ---
excel_chunks = []

for doc_item in documents_docling_excel:
    if doc_item["metadata"]["element_type"] == "table":
        table_content = doc_item["content"]
        
        # Strategy A: Full table as one chunk (for small tables)
        if len(table_content) <= 1500:
            excel_chunks.append({
                "content": table_content,
                "metadata": {
                    **doc_item["metadata"],
                    "chunk_strategy": "full_table",
                }
            })
        else:
            # Strategy B: Split large tables by rows (preserve header)
            lines = table_content.split("\n")
            header_lines = lines[:2]  # Markdown table header + separator
            data_lines = lines[2:]
            
            # Chunk every N rows together, always including the header
            chunk_size = 15  # rows per chunk
            for i in range(0, len(data_lines), chunk_size):
                chunk_rows = data_lines[i:i + chunk_size]
                chunk_content = "\n".join(header_lines + chunk_rows)
                excel_chunks.append({
                    "content": chunk_content,
                    "metadata": {
                        **doc_item["metadata"],
                        "chunk_strategy": "table_row_batch",
                        "row_start": i,
                        "row_end": min(i + chunk_size, len(data_lines)),
                    }
                })
        
        # Strategy C: Natural language summary of the table
        row_count = table_content.count("\n") - 2  # subtract header lines
        # Extract column names from markdown header
        if "|" in table_content:
            cols = [c.strip() for c in table_content.split("\n")[0].split("|") if c.strip()]
            summary = f"Excel table with {row_count} rows and columns: {', '.join(cols)}."
        else:
            summary = f"Excel table with approximately {row_count} data rows."
        
        excel_chunks.append({
            "content": summary,
            "metadata": {
                **doc_item["metadata"],
                "chunk_strategy": "table_summary",
            }
        })
    else:
        # Non-table elements (headers, text annotations in Excel)
        excel_chunks.append({
            "content": doc_item["content"],
            "metadata": {
                **doc_item["metadata"],
                "chunk_strategy": "text_element",
            }
        })

print(f"\n{'='*60}")
print(f"CHUNKING RESULTS")
print(f"{'='*60}")
print(f"Total chunks: {len(excel_chunks)}")
strategy_counts = Counter(c["metadata"]["chunk_strategy"] for c in excel_chunks)
for s, count in strategy_counts.most_common():
    print(f"  {s}: {count}")
```

### Implementation: `01b_excel_pandas_fallback.py`

```python
"""
Pandas-based Excel ingestion — fallback and comparison.
Use when you need numerical analysis or Docling doesn't handle a specific Excel format.
Also useful for row-level semantic search.
"""
import pandas as pd
from pathlib import Path

excel_path = "data/sample_loan_portfolio.xlsx"
xl = pd.ExcelFile(excel_path)

print(f"Sheets found: {xl.sheet_names}")

documents_pandas = []

for sheet_name in xl.sheet_names:
    df = pd.read_excel(xl, sheet_name=sheet_name)
    print(f"\n[Sheet: {sheet_name}] {len(df)} rows × {len(df.columns)} cols")
    
    # Strategy A: Full table as markdown
    table_markdown = df.to_markdown(index=False)
    documents_pandas.append({
        "content": table_markdown,
        "metadata": {
            "source": str(excel_path),
            "sheet": sheet_name,
            "type": "full_table",
            "rows": len(df),
            "columns": list(df.columns),
            "parser": "pandas",
        }
    })
    
    # Strategy B: Row-level chunks (each row as natural language)
    for idx, row in df.iterrows():
        row_text = " | ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
        documents_pandas.append({
            "content": f"[Sheet: {sheet_name}, Row {idx+1}] {row_text}",
            "metadata": {
                "source": str(excel_path),
                "sheet": sheet_name,
                "type": "row",
                "row_index": idx,
                "parser": "pandas",
            }
        })
    
    # Strategy C: Column-level statistics summary
    summary_parts = [f"Table '{sheet_name}' has {len(df)} records with columns: {', '.join(df.columns)}."]
    for col in df.select_dtypes(include='number').columns[:5]:
        summary_parts.append(
            f"{col}: min={df[col].min()}, max={df[col].max()}, "
            f"mean={df[col].mean():.2f}, sum={df[col].sum():.2f}"
        )
    
    documents_pandas.append({
        "content": " ".join(summary_parts),
        "metadata": {
            "source": str(excel_path),
            "sheet": sheet_name,
            "type": "table_summary",
            "parser": "pandas",
        }
    })

print(f"\n[Pandas] Total documents: {len(documents_pandas)}")
```

### Implementation: `01c_excel_multi_file.py`

```python
"""
Batch Excel processing — handles a directory of Excel files.
This is what your real project will need: process many Excels at once.
"""
from docling.document_converter import DocumentConverter
from pathlib import Path
from collections import Counter
import time

# --- Configure ---
data_dir = Path("data/")
excel_files = list(data_dir.glob("*.xlsx")) + list(data_dir.glob("*.xls"))
print(f"Found {len(excel_files)} Excel files to process")

# --- Initialize Docling once (reuse for all files) ---
converter = DocumentConverter()

# --- Batch processing pipeline ---
all_documents = []
processing_stats = []

for excel_path in excel_files:
    start_time = time.time()
    print(f"\nProcessing: {excel_path.name}...", end=" ")
    
    try:
        result = converter.convert(str(excel_path))
        doc = result.document
        
        # Extract elements
        file_docs = []
        for item, level in doc.iterate_items():
            element_type = item.__class__.__name__
            
            if hasattr(item, 'export_to_markdown'):
                content = item.export_to_markdown()
            elif hasattr(item, 'text') and item.text:
                content = item.text
            else:
                continue
            
            if not content or len(content.strip()) < 5:
                continue
            
            file_docs.append({
                "content": content,
                "metadata": {
                    "source": str(excel_path),
                    "filename": excel_path.name,
                    "element_type": element_type.lower(),
                    "hierarchy_level": level,
                    "parser": "docling",
                    "file_type": "excel",
                }
            })
        
        elapsed = time.time() - start_time
        processing_stats.append({
            "file": excel_path.name,
            "elements": len(file_docs),
            "time": elapsed,
            "status": "✅",
        })
        all_documents.extend(file_docs)
        print(f"✅ {len(file_docs)} elements ({elapsed:.1f}s)")
        
    except Exception as e:
        elapsed = time.time() - start_time
        processing_stats.append({
            "file": excel_path.name,
            "elements": 0,
            "time": elapsed,
            "status": f"❌ {str(e)[:50]}",
        })
        print(f"❌ Error: {e}")

# --- Summary ---
print(f"\n{'='*60}")
print(f"BATCH PROCESSING SUMMARY")
print(f"{'='*60}")
print(f"Files processed: {len(excel_files)}")
print(f"Total documents: {len(all_documents)}")
print(f"Total time: {sum(s['time'] for s in processing_stats):.1f}s")
print(f"\nPer file:")
for stat in processing_stats:
    print(f"  {stat['status']} {stat['file']:<30} {stat['elements']:>4} elements  ({stat['time']:.1f}s)")

# --- Element type distribution across all files ---
print(f"\nElement types (all files):")
type_counts = Counter(d["metadata"]["element_type"] for d in all_documents)
for t, count in type_counts.most_common():
    print(f"  {t}: {count}")

# --- Build chunks from all files ---
print(f"\n{'='*60}")
print("BUILDING SEARCHABLE CHUNKS FROM ALL EXCELS")
print(f"{'='*60}")

all_chunks = []
for doc_item in all_documents:
    if doc_item["metadata"]["element_type"] == "table":
        content = doc_item["content"]
        # Full table chunk (or split if too large)
        if len(content) <= 1500:
            all_chunks.append({
                "content": content,
                "metadata": {**doc_item["metadata"], "chunk_strategy": "full_table"}
            })
        else:
            lines = content.split("\n")
            header = "\n".join(lines[:2])
            data_lines = lines[2:]
            for i in range(0, len(data_lines), 15):
                batch = data_lines[i:i+15]
                all_chunks.append({
                    "content": header + "\n" + "\n".join(batch),
                    "metadata": {
                        **doc_item["metadata"],
                        "chunk_strategy": "table_row_batch",
                        "row_start": i,
                        "row_end": i + len(batch),
                    }
                })
    else:
        all_chunks.append({
            "content": doc_item["content"],
            "metadata": {**doc_item["metadata"], "chunk_strategy": "text_element"}
        })

print(f"Total searchable chunks: {len(all_chunks)}")
print(f"Across {len(excel_files)} files")
print(f"\nChunk strategy breakdown:")
strat_counts = Counter(c["metadata"]["chunk_strategy"] for c in all_chunks)
for s, count in strat_counts.most_common():
    print(f"  {s}: {count}")
```

### Docling vs Pandas for Excel — When to Use Which

| Scenario | Use Docling | Use Pandas |
|----------|------------|------------|
| Structure-aware parsing (headers, merged cells) | ✅ | ⚠️ Needs manual handling |
| Consistent API with PDF parsing | ✅ Same `DocumentConverter` | ❌ Different API |
| Multi-file batch processing | ✅ | ✅ |
| Row-level numerical analysis | ⚠️ Parse markdown back | ✅ Native DataFrame |
| Column statistics (min/max/sum) | ❌ | ✅ Native |
| Complex formulas/computed values | ⚠️ | ✅ openpyxl `data_only=True` |
| Multi-sheet relationships | ✅ (hierarchy) | ⚠️ Manual |
| Markdown output for LLM | ✅ Direct | ⚠️ `df.to_markdown()` |
| Large files (100K+ rows) | 🐢 Slower | ⚡ Fast |

### Recommended Enterprise Strategy

```
Excel Ingestion Pipeline:
┌─────────────────────────────────────────────────────┐
│  Excel File                                         │
│       │                                             │
│       ├── Docling (PRIMARY)                         │
│       │    → Structure-aware table extraction       │
│       │    → Markdown output for chunking/LLM       │
│       │    → Consistent with PDF pipeline           │
│       │                                             │
│       └── Pandas (SECONDARY — enrichment)           │
│            → Column statistics for summaries        │
│            → Row-level filtering/search             │
│            → Numerical aggregation queries          │
│                                                     │
│  Output: Metadata-rich chunks with:                 │
│    • source filename                                │
│    • sheet name                                     │
│    • table/row identification                       │
│    • column headers                                 │
│    • numerical ranges                               │
└─────────────────────────────────────────────────────┘
```

### Observations to Note
- How does Docling handle multi-sheet workbooks vs pandas?
- Does Docling preserve merged cell content correctly?
- Which gives better markdown tables for LLM input?
- How does batch processing scale with 10, 50, 100 files?
- Which approach produces better retrieval results downstream?

---

## Block 3A: PDF Table Extraction — pdfplumber (Baseline) (30 min)

### Goal
Extract tables from a structured PDF using pdfplumber. This is our **baseline** to compare against Docling and Unstructured.

### Key Concepts to Learn
- pdfplumber table extraction
- Table-to-markdown conversion
- Handling merged cells, multi-line headers
- Page-level metadata

### Implementation: `02a_pdf_pdfplumber.py`

```python
import pdfplumber
from pathlib import Path

pdf_path = "data/sample_auction_notice.pdf"
documents = []

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        # --- Step 1: Extract tables ---
        tables = page.extract_tables()
        
        for table_idx, table in enumerate(tables):
            if not table or len(table) < 2:
                continue
            
            # Convert to markdown preserving structure
            headers = table[0]
            rows = table[1:]
            
            # Build markdown table
            md_lines = ["| " + " | ".join(str(h) for h in headers) + " |"]
            md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for row in rows:
                md_lines.append("| " + " | ".join(str(cell or "") for cell in row) + " |")
            
            table_md = "\n".join(md_lines)
            
            documents.append({
                "content": table_md,
                "metadata": {
                    "source": pdf_path,
                    "page": page_num,
                    "type": "table",
                    "table_index": table_idx,
                    "headers": headers,
                    "row_count": len(rows),
                    "parser": "pdfplumber",
                }
            })
        
        # --- Step 2: Extract non-table text ---
        text = page.extract_text()
        if text:
            documents.append({
                "content": text,
                "metadata": {
                    "source": pdf_path,
                    "page": page_num,
                    "type": "narrative",
                    "parser": "pdfplumber",
                }
            })

print(f"[pdfplumber] Extracted {len(documents)} documents from PDF")
for doc in documents[:5]:
    print(f"\n--- [Page {doc['metadata']['page']} | {doc['metadata']['type']}] ---")
    print(doc['content'][:300])
```

### Limitations to Observe
- Struggles with complex merged cells
- Cannot detect document hierarchy (headings, sections)
- No element typing (doesn't know if text is a title, footnote, or body)
- Tables without visible borders may be missed

---

## Block 3B: PDF Parsing — Docling (Structure-Aware) (45 min)

### Goal
Use IBM's Docling to parse the same PDF. Docling understands document **structure** — it identifies titles, paragraphs, tables, lists, and their hierarchy. This is the modern approach.

### Why Docling is Exciting
- Produces **typed elements** (Title, SectionHeader, Paragraph, Table, List, Caption, Footnote)
- Understands **document hierarchy** (which paragraphs belong to which section)
- Outputs **clean Markdown** with structure preserved
- Table extraction is structure-aware (understands row/column spans)
- Open-source (MIT license), by IBM Research
- Works offline, no API calls needed

### Key Resources
- GitHub: https://github.com/DS4SD/docling
- Documentation: https://ds4sd.github.io/docling/
- Paper: https://arxiv.org/abs/2408.09869

### Implementation: `02b_pdf_docling.py`

```python
"""
Docling-based PDF parsing — structure-aware document understanding.
Docling outputs typed, hierarchical document elements.
"""
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from pathlib import Path

pdf_path = "data/sample_auction_notice.pdf"

# --- Step 1: Initialize Docling converter ---
converter = DocumentConverter()

# --- Step 2: Convert document ---
print(f"Parsing with Docling: {pdf_path}")
result = converter.convert(pdf_path)

# --- Step 3: Get the structured document ---
doc = result.document

# --- Step 4: Export as Markdown (Docling's strength) ---
markdown_output = doc.export_to_markdown()
print(f"\n--- Docling Markdown Output (first 1000 chars) ---")
print(markdown_output[:1000])

# --- Step 5: Iterate over document elements (typed!) ---
documents_docling = []

for item, level in doc.iterate_items():
    # Each item has a type: Title, SectionHeader, Paragraph, Table, List, etc.
    element_type = item.__class__.__name__
    
    if hasattr(item, 'text') and item.text:
        content = item.text
    elif hasattr(item, 'export_to_markdown'):
        content = item.export_to_markdown()
    else:
        continue
    
    if not content or len(content.strip()) < 10:
        continue
    
    documents_docling.append({
        "content": content,
        "metadata": {
            "source": pdf_path,
            "type": element_type.lower(),  # "table", "paragraph", "sectionheader", "title"
            "level": level,
            "parser": "docling",
        }
    })

print(f"\n[Docling] Extracted {len(documents_docling)} typed elements")
print(f"\nElement type breakdown:")
from collections import Counter
type_counts = Counter(d["metadata"]["type"] for d in documents_docling)
for t, count in type_counts.most_common():
    print(f"  {t}: {count}")

# --- Step 6: Show sample elements ---
print(f"\n--- Sample Elements ---")
for doc in documents_docling[:8]:
    print(f"\n[{doc['metadata']['type'].upper()}] (level={doc['metadata']['level']})")
    print(f"  {doc['content'][:150]}")

# --- Step 7: Extract tables specifically ---
tables_docling = [d for d in documents_docling if d["metadata"]["type"] == "table"]
print(f"\n--- Tables found: {len(tables_docling)} ---")
for t in tables_docling[:2]:
    print(t["content"][:400])
```

### What to Observe
- **Element typing**: Docling tells you exactly WHAT each piece of text is (title, section header, paragraph, table)
- **Hierarchy**: Level information tells you the nesting depth
- **Table quality**: Compare Docling's table output vs pdfplumber's — which preserves structure better?
- **Markdown export**: One-shot clean markdown of entire document — extremely useful

### Docling Advanced Features (try if time permits)

```python
# --- Advanced: Get document structure as a tree ---
# Docling preserves parent-child relationships
print("\n--- Document Structure Tree ---")
for item, level in doc.iterate_items():
    indent = "  " * level
    element_type = item.__class__.__name__
    preview = ""
    if hasattr(item, 'text'):
        preview = item.text[:50] if item.text else ""
    print(f"{indent}[{element_type}] {preview}")

# --- Advanced: Export as JSON (for programmatic access) ---
import json
json_output = doc.export_to_dict()
# This gives you the full structured representation
print(f"\nJSON keys: {list(json_output.keys())}")
```

---

## Block 3C: PDF Parsing — Unstructured.io (Element-Based) (45 min)

### Goal
Use Unstructured.io to parse the same PDF. Unstructured focuses on **element-based partitioning** — it breaks documents into categorized elements with rich metadata.

### Why Unstructured.io is Exciting
- **25+ file formats** supported (PDF, DOCX, PPTX, HTML, Email, etc.)
- **Element categorization**: Title, NarrativeText, Table, ListItem, Header, Footer, Image, etc.
- **Chunking built-in**: Can chunk by title/section automatically
- **Metadata-rich**: Each element carries coordinates, page number, category, parent info
- **hi_res strategy**: Uses a layout model (like YOLO) for complex documents
- **Cloud API available**: For production, or run locally
- Has a strong enterprise offering

### Key Resources
- GitHub: https://github.com/Unstructured-IO/unstructured
- Documentation: https://docs.unstructured.io/
- Open-source Python library: https://github.com/Unstructured-IO/unstructured
- API (free tier): https://unstructured.io/api-key-hosted

### Implementation: `02c_pdf_unstructured.py`

```python
"""
Unstructured.io-based PDF parsing — element-based document partitioning.
Produces categorized elements with rich metadata.
"""
from unstructured.partition.pdf import partition_pdf
from unstructured.chunking.title import chunk_by_title
from collections import Counter

pdf_path = "data/sample_auction_notice.pdf"

# --- Step 1: Partition the PDF into elements ---
# strategy options: "fast" (text only), "hi_res" (layout model), "ocr_only"
print(f"Parsing with Unstructured: {pdf_path}")
print("(Using 'fast' strategy — switch to 'hi_res' for layout-aware parsing)")

elements = partition_pdf(
    filename=pdf_path,
    strategy="fast",          # Use "hi_res" for layout model (slower, better tables)
    # strategy="hi_res",      # Uncomment for better table detection (needs extra deps)
    include_metadata=True,
)

print(f"\n[Unstructured] Extracted {len(elements)} elements")

# --- Step 2: Examine element types ---
print(f"\nElement type breakdown:")
type_counts = Counter(type(el).__name__ for el in elements)
for t, count in type_counts.most_common():
    print(f"  {t}: {count}")

# --- Step 3: Convert to our document format ---
documents_unstructured = []

for el in elements:
    content = str(el)
    if len(content.strip()) < 10:
        continue
    
    # Rich metadata from Unstructured
    metadata = {
        "source": pdf_path,
        "type": type(el).__name__.lower(),  # "narrativetext", "table", "title", "listitem"
        "parser": "unstructured",
        "page": el.metadata.page_number if hasattr(el.metadata, 'page_number') else None,
    }
    
    # Additional metadata if available
    if hasattr(el.metadata, 'coordinates') and el.metadata.coordinates:
        metadata["has_coordinates"] = True
    if hasattr(el.metadata, 'parent_id') and el.metadata.parent_id:
        metadata["parent_id"] = el.metadata.parent_id
    
    documents_unstructured.append({
        "content": content,
        "metadata": metadata,
    })

print(f"\nDocuments created: {len(documents_unstructured)}")

# --- Step 4: Show sample elements ---
print(f"\n--- Sample Elements ---")
for doc in documents_unstructured[:10]:
    print(f"\n[{doc['metadata']['type'].upper()}] (page={doc['metadata'].get('page')})")
    print(f"  {doc['content'][:150]}")

# --- Step 5: Unstructured's built-in chunking (by title/section) ---
print(f"\n{'='*50}")
print("CHUNKING BY TITLE (Unstructured built-in)")
print(f"{'='*50}")

chunks = chunk_by_title(
    elements,
    max_characters=1000,       # Max chunk size
    combine_text_under_n_chars=200,  # Merge small elements
    new_after_n_chars=800,     # Start new chunk after this
)

print(f"\nChunks created: {len(chunks)}")
for i, chunk in enumerate(chunks[:5]):
    print(f"\n--- Chunk {i+1} ({type(chunk).__name__}) ---")
    print(f"  {str(chunk)[:200]}")
    if hasattr(chunk.metadata, 'orig_elements'):
        print(f"  (Merged from {len(chunk.metadata.orig_elements)} original elements)")

# --- Step 6: Tables specifically ---
from unstructured.documents.elements import Table
tables_unstructured = [el for el in elements if isinstance(el, Table)]
print(f"\n--- Tables found: {len(tables_unstructured)} ---")
for t in tables_unstructured[:2]:
    print(f"\n[Table on page {t.metadata.page_number}]")
    print(str(t)[:400])
    # Unstructured can also give you table as HTML
    if hasattr(t.metadata, 'text_as_html') and t.metadata.text_as_html:
        print(f"\n  HTML representation available: {t.metadata.text_as_html[:200]}...")
```

### What to Observe
- **Element granularity**: Unstructured produces fine-grained elements (every paragraph separate)
- **Built-in chunking**: `chunk_by_title` groups elements under their section heading — very powerful
- **Metadata richness**: coordinates, page numbers, parent-child relationships
- **Table quality**: Compare vs pdfplumber and Docling
- **Speed**: `fast` strategy is quick but misses layout; `hi_res` is slow but better

### Unstructured Advanced: Hi-Res Strategy (if time permits)

```python
# Hi-res uses a layout detection model — much better for complex PDFs
# Requires: pip install "unstructured[pdf]" and detectron2 or yolox
elements_hires = partition_pdf(
    filename=pdf_path,
    strategy="hi_res",
    hi_res_model_name="yolox",  # Layout detection model
    include_metadata=True,
)
print(f"Hi-res extracted {len(elements_hires)} elements")
# Compare element types and table quality vs "fast" strategy
```

---

## Block 3D: Compare All Three Parsers (15 min)

### Implementation: `02d_compare_parsers.py`

```python
"""
Side-by-side comparison of pdfplumber vs Docling vs Unstructured.io
on the SAME PDF document.
"""
from rich.console import Console
from rich.table import Table as RichTable

console = Console()

# Assuming you've run 02a, 02b, 02c and have:
# - documents (from pdfplumber)
# - documents_docling (from Docling)  
# - documents_unstructured (from Unstructured)

# --- Comparison Table ---
table = RichTable(title="Parser Comparison")
table.add_column("Metric", style="cyan")
table.add_column("pdfplumber", style="green")
table.add_column("Docling", style="yellow")
table.add_column("Unstructured", style="magenta")

# Total elements
table.add_row(
    "Total elements extracted",
    str(len(documents)),
    str(len(documents_docling)),
    str(len(documents_unstructured)),
)

# Tables found
tables_plumber = len([d for d in documents if d["metadata"]["type"] == "table"])
tables_docling_count = len([d for d in documents_docling if d["metadata"]["type"] == "table"])
tables_unstructured_count = len([d for d in documents_unstructured if d["metadata"]["type"] == "table"])
table.add_row("Tables found", str(tables_plumber), str(tables_docling_count), str(tables_unstructured_count))

# Element types
types_plumber = set(d["metadata"]["type"] for d in documents)
types_docling = set(d["metadata"]["type"] for d in documents_docling)
types_unstructured = set(d["metadata"]["type"] for d in documents_unstructured)
table.add_row("Element types", str(types_plumber), str(types_docling), str(types_unstructured))

# Hierarchy support
table.add_row("Hierarchy/Levels", "❌ No", "✅ Yes", "⚠️ Partial (parent_id)")

# Built-in chunking
table.add_row("Built-in chunking", "❌ No", "❌ No (manual)", "✅ Yes (chunk_by_title)")

# Table format
table.add_row("Table output format", "List of lists", "Markdown", "Text/HTML")

console.print(table)

# --- Quality comparison: Same table extracted by all three ---
print(f"\n{'='*60}")
print("SAME TABLE — THREE PARSERS")
print(f"{'='*60}")

# Show first table from each parser
if tables_plumber > 0:
    t = [d for d in documents if d["metadata"]["type"] == "table"][0]
    print(f"\n[PDFPLUMBER TABLE]")
    print(t["content"][:300])

if tables_docling_count > 0:
    t = [d for d in documents_docling if d["metadata"]["type"] == "table"][0]
    print(f"\n[DOCLING TABLE]")
    print(t["content"][:300])

if tables_unstructured_count > 0:
    t = [d for d in documents_unstructured if d["metadata"]["type"] == "table"][0]
    print(f"\n[UNSTRUCTURED TABLE]")
    print(t["content"][:300])

# --- Decision Matrix ---
print(f"\n{'='*60}")
print("DECISION: Which parser for enterprise?")
print(f"{'='*60}")
print("""
┌─────────────────────┬──────────────────────────────────────────────┐
│ Use Case            │ Best Parser                                  │
├─────────────────────┼──────────────────────────────────────────────┤
│ Simple table PDFs   │ pdfplumber (fastest, good enough)            │
│ Structured docs     │ Docling (hierarchy + typed elements)         │
│ Mixed/messy docs    │ Unstructured hi_res (layout model)           │
│ Multi-format ingest │ Unstructured (25+ formats)                   │
│ Document hierarchy  │ Docling (best structure understanding)       │
│ Table-heavy docs    │ Docling > pdfplumber > Unstructured          │
│ Scanned/OCR docs    │ Unstructured hi_res or Docling with OCR      │
│ Production pipeline │ Unstructured (API + enterprise support)      │
└─────────────────────┴──────────────────────────────────────────────┘

For the enterprise Financial RAG platform:
→ Use Docling as PRIMARY parser (best structure understanding)
→ Use Unstructured as SECONDARY for format coverage
→ Use pdfplumber as FALLBACK for simple table extraction
""")
```

---

## Block 3 — Key Takeaways

| Feature | pdfplumber | Docling | Unstructured.io |
|---------|-----------|---------|-----------------|
| Speed | ⚡ Fast | 🐢 Moderate | 🐢 Moderate (hi_res slow) |
| Table quality | ✅ Good | ✅✅ Excellent | ⚠️ Depends on strategy |
| Structure awareness | ❌ None | ✅✅ Excellent | ✅ Good |
| Element typing | ❌ None | ✅ Title/Para/Table/List | ✅ NarrativeText/Title/Table |
| Hierarchy | ❌ None | ✅ Levels + nesting | ⚠️ Parent-child IDs |
| Built-in chunking | ❌ | ❌ | ✅ chunk_by_title |
| Format support | PDF only | PDF, DOCX, PPTX, HTML | 25+ formats |
| OCR support | ❌ | ✅ Built-in | ✅ Built-in |
| Enterprise ready | ⚠️ Library only | ✅ Open source | ✅✅ API + Enterprise |
| Install complexity | Easy | Easy | Medium (hi_res needs extras) |

---

## Block 4: Chunking + Embedding + Indexing (60 min)

### Goal
Embed all extracted documents and store in Qdrant with metadata.

### Key Concepts to Learn
- Embedding models (BGE-small for speed)
- Qdrant collection creation with metadata payload
- Hybrid storage (content + metadata)
- Filtering capability setup

### Implementation: `03_chunking_and_indexing.py`

```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer
import uuid
import json

# --- Step 1: Initialize embedding model ---
# Using BGE-small for speed in POC (384 dimensions)
# Enterprise would use BGE-large or fine-tuned model
model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# --- Step 2: Initialize Qdrant (in-memory for POC) ---
client = QdrantClient(":memory:")  # Use "localhost" for persistent Qdrant

collection_name = "structured_financial_docs"
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

# --- Step 3: Load documents from previous steps ---
# In real POC, import from 01 and 02. Here we'll combine:
# documents = excel_documents + pdf_documents
# For now, assume `documents` list exists from previous scripts

# --- Step 4: Embed and index ---
points = []
for i, doc in enumerate(documents):
    # Prefix for better retrieval (BGE recommendation)
    text_to_embed = f"Represent this financial document for retrieval: {doc['content'][:512]}"
    embedding = model.encode(text_to_embed).tolist()
    
    point = PointStruct(
        id=str(uuid.uuid4()),
        vector=embedding,
        payload={
            "content": doc["content"],
            "metadata": doc["metadata"],
            "source": doc["metadata"].get("source", ""),
            "type": doc["metadata"].get("type", ""),
            "page": doc["metadata"].get("page", 0),
            "sheet": doc["metadata"].get("sheet", ""),
        }
    )
    points.append(point)

# Batch upsert
client.upsert(collection_name=collection_name, points=points)
print(f"Indexed {len(points)} documents in Qdrant")

# --- Step 5: Test metadata filtering ---
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Search only in tables
results = client.search(
    collection_name=collection_name,
    query_vector=model.encode("total outstanding loan amount").tolist(),
    query_filter=Filter(
        must=[FieldCondition(key="type", match=MatchValue(value="table"))]
    ),
    limit=3,
)

print("\n--- Filtered Search (tables only) ---")
for r in results:
    print(f"Score: {r.score:.3f} | Type: {r.payload['type']}")
    print(f"Content: {r.payload['content'][:150]}\n")
```

### Key Learning Points
- Observe how metadata filtering narrows results (type=table vs type=narrative)
- Notice embedding dimension trade-offs (384 vs 768 vs 1024)
- In-memory Qdrant is fast for POC but not persistent

---

## Block 5: Retrieval + QA Pipeline (60 min)

### Goal
Build a complete question-answering pipeline with retrieval + LLM generation.

### Key Concepts to Learn
- Query embedding + vector search
- Context construction from retrieved chunks
- Prompt engineering for financial QA
- Structured answer generation

### Implementation: `04_retrieval_qa.py`

```python
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

# --- Setup ---
embed_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
qdrant = QdrantClient(":memory:")  # or localhost
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

collection_name = "structured_financial_docs"

def retrieve(query: str, top_k: int = 5, doc_type: str = None):
    """Retrieve relevant chunks with optional type filtering."""
    query_embedding = embed_model.encode(f"Represent this query for retrieval: {query}").tolist()
    
    search_filter = None
    if doc_type:
        search_filter = Filter(
            must=[FieldCondition(key="type", match=MatchValue(value=doc_type))]
        )
    
    results = qdrant.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        query_filter=search_filter,
        limit=top_k,
    )
    return results

def build_context(results):
    """Construct context from retrieved documents with citations."""
    context_parts = []
    for i, r in enumerate(results, 1):
        source = r.payload.get("source", "unknown")
        page = r.payload.get("page", "N/A")
        doc_type = r.payload.get("type", "unknown")
        content = r.payload["content"]
        
        context_parts.append(
            f"[Source {i}] (File: {source}, Page: {page}, Type: {doc_type})\n{content}"
        )
    return "\n\n---\n\n".join(context_parts)

def answer_query(query: str, doc_type: str = None):
    """End-to-end RAG: retrieve + generate."""
    # Step 1: Retrieve
    results = retrieve(query, top_k=5, doc_type=doc_type)
    
    if not results:
        return "No relevant documents found."
    
    # Step 2: Build context
    context = build_context(results)
    
    # Step 3: Generate answer with citation
    system_prompt = """You are a financial document analyst. Answer questions based ONLY on the provided context.
    
Rules:
- If the answer is in a table, present it clearly
- Always cite which source [Source N] contains the evidence
- If you cannot find the answer in the context, say "Not found in available documents"
- For numerical answers, show the exact figure from the source
- Never make up financial figures"""

    user_prompt = f"""Context:
{context}

Question: {query}

Provide a clear, cited answer:"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",  # Use gpt-4o for better table understanding
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )
    
    return {
        "answer": response.choices[0].message.content,
        "sources": [{"score": r.score, "type": r.payload["type"], "page": r.payload.get("page")} for r in results],
        "context_used": context[:500] + "...",
    }

# --- Test Queries ---
test_queries = [
    ("What is the total outstanding amount?", None),
    ("List all properties with their reserve prices", "table"),
    ("What are the terms and conditions of the auction?", "narrative"),
]

for query, dtype in test_queries:
    print(f"\n{'='*60}")
    print(f"Q: {query}")
    print(f"Filter: type={dtype}")
    result = answer_query(query, doc_type=dtype)
    print(f"A: {result['answer']}")
    print(f"Sources: {result['sources']}")
```

---

## Block 6: Evaluation + Observations (30-60 min)

### Goal
Measure retrieval quality and document learnings.

### Implementation: `05_evaluation.py`

```python
"""
Simple evaluation — no need for RAGAS in POC.
Just measure: does the system retrieve the right chunk?
"""

# Define test cases: (query, expected_source_type, expected_keyword_in_result)
test_cases = [
    {
        "query": "What is the reserve price of property in Lot 1?",
        "expected_type": "table",
        "expected_keyword": "reserve",  # Should appear in retrieved content
    },
    {
        "query": "What are the borrower details?",
        "expected_type": "row",
        "expected_keyword": "borrower",
    },
    {
        "query": "Summarize the loan portfolio",
        "expected_type": "table_summary",
        "expected_keyword": "records",
    },
]

def evaluate(test_cases):
    results = []
    for tc in test_cases:
        retrieved = retrieve(tc["query"], top_k=3)
        
        # Check if expected type appears in top results
        types_found = [r.payload["type"] for r in retrieved]
        type_hit = tc["expected_type"] in types_found
        
        # Check if keyword appears in retrieved content
        all_content = " ".join([r.payload["content"].lower() for r in retrieved])
        keyword_hit = tc["expected_keyword"].lower() in all_content
        
        results.append({
            "query": tc["query"],
            "type_hit": type_hit,
            "keyword_hit": keyword_hit,
            "top_score": retrieved[0].score if retrieved else 0,
        })
    
    # Summary
    type_accuracy = sum(r["type_hit"] for r in results) / len(results)
    keyword_accuracy = sum(r["keyword_hit"] for r in results) / len(results)
    avg_score = sum(r["top_score"] for r in results) / len(results)
    
    print(f"Type Retrieval Accuracy: {type_accuracy:.0%}")
    print(f"Keyword Hit Rate: {keyword_accuracy:.0%}")
    print(f"Average Top Score: {avg_score:.3f}")
    
    return results

evaluate(test_cases)
```

---

## Key Observations Template

After completing the POC, fill this in:

### What Worked
- [ ] Excel row-level chunking retrieval quality
- [ ] PDF table extraction accuracy
- [ ] Metadata filtering effectiveness
- [ ] Answer citation quality

### What Didn't Work
- [ ] Complex merged-cell tables in PDF
- [ ] Ambiguous column names in embeddings
- [ ] Large tables exceeding embedding token limit
- [ ] Numerical comparison queries

### Enterprise Implications
- [ ] Need for table-specific embedding strategy
- [ ] Need for hybrid (keyword + semantic) search
- [ ] Need for structured output from LLM
- [ ] Need for domain-specific embedding fine-tuning

---

## Resources & Links

| Resource | Link | Why |
|----------|------|-----|
| **Docling (IBM)** | https://github.com/DS4SD/docling | Structure-aware document understanding — best hierarchy + table extraction |
| Docling Documentation | https://ds4sd.github.io/docling/ | Setup guides, API reference |
| Docling Paper | https://arxiv.org/abs/2408.09869 | Research behind Docling's approach |
| **Unstructured.io** | https://github.com/Unstructured-IO/unstructured | Element-based parsing, 25+ formats |
| Unstructured Docs | https://docs.unstructured.io/ | Full API documentation |
| Unstructured API Key (free) | https://unstructured.io/api-key-hosted | Cloud API for hi_res processing |
| **pdfplumber** | https://github.com/jsvine/pdfplumber | Baseline PDF table extraction |
| BGE Embedding Models | https://huggingface.co/BAAI/bge-small-en-v1.5 | Fast, quality embeddings |
| Qdrant Documentation | https://qdrant.tech/documentation/ | Vector DB with metadata filtering |
| Qdrant Python Client | https://github.com/qdrant/qdrant-client | Client library |
| Sentence Transformers | https://www.sbert.net/ | Embedding library |
| OpenAI API | https://platform.openai.com/docs | LLM generation |
| LlamaIndex Docs | https://docs.llamaindex.ai/en/stable/ | Retrieval framework (next step) |
| Pandas to_markdown | https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_markdown.html | Table formatting |
| Docling vs Unstructured Blog | https://ds4sd.github.io/docling/examples/ | Comparison examples |

---

## Next Steps (After POC)

1. → Use **Docling** as primary parser in enterprise pipeline (best structure + hierarchy)
2. → Use **Unstructured.io** for multi-format ingestion (Excel, DOCX, HTML, Email)
3. → Add **SPLADE sparse vectors** for hybrid search
4. → Try **ColBERT** for table retrieval
5. → Add **reranking** (cross-encoder) layer
6. → Integrate Unstructured's `chunk_by_title` with Qdrant metadata filtering
7. → Explore Docling's hierarchy for parent-child retrieval
8. → Connect to enterprise architecture Layers B, C, D, E

