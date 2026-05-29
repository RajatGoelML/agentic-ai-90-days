# Unstructured RAG POC — 1 Day (4-6 Hours)

## Objective

Build an end-to-end RAG pipeline over **unstructured financial documents** (narrative PDFs, scanned documents, auction notices with mixed layouts) to gain hands-on familiarity with:

- **Docling** (IBM) — structure-aware parsing that auto-detects headings, paragraphs, sections
- **Unstructured.io** — element-based partitioning with built-in OCR and chunking
- **pdfplumber / PyMuPDF** — baseline text extraction
- **Tesseract OCR** — handling scanned documents
- Semantic chunking strategies (compare 4 approaches)
- Dense embedding + retrieval
- Context engineering for long-form documents
- Grounded answer generation with citations

This POC directly maps to Layers A, B, C, D, E, F, G of the enterprise architecture.

---

## What You'll Build

A system that can:
1. Ingest a multi-page narrative PDF (auction notice / valuation report)
2. Handle scanned PDF pages via OCR
3. Parse document structure (sections, paragraphs, headings)
4. Chunk intelligently (not breaking mid-sentence or mid-section)
5. Embed + index in vector store
6. Answer questions with page-level citations like:
   - "What are the terms of sale for this auction?"
   - "Describe the property mentioned in the notice"
   - "What is the inspection date and time?"
   - "Who is the authorized officer?"

---

## Timeline

| Time Block | Activity | Duration |
|-----------|----------|----------|
| Block 1 | Setup + Data Preparation | 30 min |
| Block 2A | PDF Text Extraction + OCR (pdfplumber, PyMuPDF, Tesseract) | 45 min |
| Block 2B | Document Parsing with Docling (structure-aware) | 45 min |
| Block 2C | Document Parsing with Unstructured.io (element-based) | 45 min |
| Block 3 | Chunking Strategies (4 approaches compared) | 45 min |
| Block 4 | Embedding + Retrieval + QA | 45 min |
| Block 5 | Compare All Approaches + Evaluation | 30 min |

> Total: ~5-6 hours. Blocks 2A/2B/2C are the core parser comparison for unstructured docs.

---

## Block 1: Setup + Data Preparation (30 min)

### Environment Setup

```bash
# Core dependencies
pip install pdfplumber pymupdf pytesseract Pillow pdf2image
pip install sentence-transformers qdrant-client openai python-dotenv rich
pip install langchain-text-splitters tiktoken

# Docling (IBM) — structure-aware document understanding
pip install docling

# Unstructured.io — element-based document parsing
pip install "unstructured[pdf]" unstructured-client
# For full OCR + layout detection:
# pip install "unstructured[all-docs]"

# Optional: PaddleOCR
# pip install paddleocr paddlepaddle
```

> **Why Docling + Unstructured for unstructured docs?**
> - **Docling** auto-detects document structure (headings, paragraphs, lists, tables) even in narrative PDFs where there are NO explicit markers. It replaces our manual regex-based section detection heuristics with ML-based structure understanding.
> - **Unstructured.io** excels at partitioning messy, real-world documents into typed elements. Its `hi_res` strategy uses a layout model that works great on mixed-layout financial notices. It also has built-in OCR for scanned pages.

**System dependency for OCR:**
- Install [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — [Windows installer](https://github.com/UB-Mannheim/tesseract/wiki)
- Install [Poppler](https://github.com/osber/poppler-for-windows) for `pdf2image` (Windows: extract and add to PATH)

### Sample Data to Use

Use freely available financial/legal PDFs:

1. **Text-native PDF (multi-page narrative)**:
   - [SARFAESI Act Notice samples](https://ibapi.in/) — download any sample auction notice
   - [RBI Circular PDFs](https://www.rbi.org.in/Scripts/NotificationUser.aspx) — regulatory text
   - OR any 5-10 page text-heavy financial PDF you have

2. **Scanned PDF (for OCR testing)**:
   - Scan any printed page using your phone (CamScanner / native)
   - OR use [this sample](https://github.com/tesseract-ocr/tesseract/wiki/ImproveQuality) scanned document

3. **Mixed PDF (text + images + tables)**:
   - Any real-world bank auction notice (these are typically mixed)

### Project Structure

```
rag_Poc_Unstructured/
├── RAG_POC_UNSTRUCTURED_PLAN.md
├── data/
│   ├── narrative_document.pdf        (text-native PDF)
│   └── scanned_document.pdf          (scanned/OCR PDF)
├── 01_pdf_extraction_baseline.py     (pdfplumber + PyMuPDF)
├── 02_ocr_pipeline.py                (Tesseract OCR)
├── 03_docling_parsing.py             (Docling structure-aware)
├── 04_unstructured_parsing.py        (Unstructured.io element-based)
├── 05_compare_parsers.py             (head-to-head comparison)
├── 06_chunking_comparison.py         (4 strategies)
├── 07_retrieval_qa.py                (embedding + RAG)
├── 08_evaluation.py
└── requirements.txt
```

---

## Block 2A: PDF Text Extraction + OCR — Baseline (45 min)

### Goal
Handle both text-native and scanned PDFs. Learn when OCR is needed and how to detect it.

### Key Concepts to Learn
- Text extraction from native PDFs (pdfplumber, PyMuPDF)
- Detecting scanned pages (no extractable text = needs OCR)
- OCR pipeline (pdf → images → text)
- Quality assessment of extracted text

### Implementation: `01_pdf_extraction.py`

```python
import pdfplumber
import fitz  # PyMuPDF
from pathlib import Path

def extract_with_pdfplumber(pdf_path: str) -> list[dict]:
    """Extract text using pdfplumber — good for layout preservation."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            pages.append({
                "page_num": i,
                "text": text,
                "char_count": len(text),
                "has_text": len(text.strip()) > 50,
                "method": "pdfplumber",
            })
    return pages

def extract_with_pymupdf(pdf_path: str) -> list[dict]:
    """Extract text using PyMuPDF — faster, good for large PDFs."""
    pages = []
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc, 1):
        text = page.get_text()
        pages.append({
            "page_num": i,
            "text": text,
            "char_count": len(text),
            "has_text": len(text.strip()) > 50,
            "method": "pymupdf",
        })
    doc.close()
    return pages

def detect_scanned_pages(pages: list[dict]) -> list[int]:
    """Detect pages that need OCR (very little or no extractable text)."""
    scanned = []
    for p in pages:
        if not p["has_text"]:
            scanned.append(p["page_num"])
            print(f"  ⚠️  Page {p['page_num']}: Only {p['char_count']} chars — likely scanned")
    return scanned

# --- Run extraction ---
pdf_path = "data/narrative_document.pdf"
print(f"\n{'='*50}")
print(f"Extracting: {pdf_path}")
print(f"{'='*50}")

# Method 1: pdfplumber
pages_plumber = extract_with_pdfplumber(pdf_path)
print(f"\n[pdfplumber] Extracted {len(pages_plumber)} pages")
for p in pages_plumber:
    print(f"  Page {p['page_num']}: {p['char_count']} chars")

# Method 2: PyMuPDF
pages_mupdf = extract_with_pymupdf(pdf_path)
print(f"\n[PyMuPDF] Extracted {len(pages_mupdf)} pages")

# Detect scanned pages
print("\n--- Scanned Page Detection ---")
scanned_pages = detect_scanned_pages(pages_plumber)
if scanned_pages:
    print(f"Pages needing OCR: {scanned_pages}")
else:
    print("All pages have extractable text ✓")

# Compare quality
print("\n--- Quality Comparison (Page 1) ---")
print(f"pdfplumber chars: {pages_plumber[0]['char_count']}")
print(f"PyMuPDF chars: {pages_mupdf[0]['char_count']}")
print(f"\nFirst 300 chars (pdfplumber):\n{pages_plumber[0]['text'][:300]}")
```

### Implementation: `02_ocr_pipeline.py`

```python
"""OCR pipeline for scanned PDFs."""
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter
from pathlib import Path

# Configure Tesseract path (Windows)
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def pdf_to_images(pdf_path: str, dpi: int = 300) -> list[Image.Image]:
    """Convert PDF pages to images for OCR."""
    images = convert_from_path(pdf_path, dpi=dpi)
    print(f"Converted {len(images)} pages to images at {dpi} DPI")
    return images

def preprocess_image(image: Image.Image) -> Image.Image:
    """Preprocess image for better OCR quality."""
    # Convert to grayscale
    img = image.convert("L")
    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)
    # Sharpen
    img = img.filter(ImageFilter.SHARPEN)
    # Binarize (threshold)
    img = img.point(lambda x: 0 if x < 128 else 255, "1")
    return img

def ocr_page(image: Image.Image, preprocess: bool = True) -> dict:
    """Run OCR on a single page image."""
    if preprocess:
        image = preprocess_image(image)
    
    # Get text
    text = pytesseract.image_to_string(image)
    
    # Get confidence data
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    confidences = [int(c) for c in data["conf"] if int(c) > 0]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    return {
        "text": text,
        "confidence": avg_confidence,
        "word_count": len(text.split()),
    }

def ocr_pipeline(pdf_path: str) -> list[dict]:
    """Full OCR pipeline for a scanned PDF."""
    images = pdf_to_images(pdf_path)
    results = []
    
    for i, img in enumerate(images, 1):
        print(f"  OCR processing page {i}...", end=" ")
        
        # Try without preprocessing first
        result_raw = ocr_page(img, preprocess=False)
        # Try with preprocessing
        result_processed = ocr_page(img, preprocess=True)
        
        # Pick the better result
        if result_processed["confidence"] > result_raw["confidence"]:
            result = result_processed
            result["preprocessing"] = True
        else:
            result = result_raw
            result["preprocessing"] = False
        
        result["page_num"] = i
        results.append(result)
        print(f"✓ ({result['word_count']} words, {result['confidence']:.0f}% confidence)")
    
    return results

# --- Run OCR pipeline ---
scanned_pdf = "data/scanned_document.pdf"
print(f"\nRunning OCR on: {scanned_pdf}")
ocr_results = ocr_pipeline(scanned_pdf)

# Quality report
print(f"\n--- OCR Quality Report ---")
for r in ocr_results:
    quality = "🟢" if r["confidence"] > 80 else "🟡" if r["confidence"] > 60 else "🔴"
    print(f"  Page {r['page_num']}: {quality} {r['confidence']:.0f}% confidence | {r['word_count']} words | Preprocessed: {r['preprocessing']}")

print(f"\nSample output (Page 1):\n{ocr_results[0]['text'][:500]}")
```

### Key Learnings
- Native PDFs: pdfplumber/PyMuPDF extract perfectly → no OCR needed
- Scanned PDFs: text extraction returns empty → OCR required
- OCR quality varies wildly — preprocessing helps
- DPI matters: 300 DPI is the sweet spot for OCR accuracy
- **Limitation**: None of these tools understand document STRUCTURE (what's a heading, what's body text, what's a footnote)

---

## Block 2B: Document Parsing with Docling — Structure-Aware (45 min)

### Goal
Use IBM's Docling to parse the SAME narrative PDF. Unlike pdfplumber/PyMuPDF which just dump text, Docling **understands document structure** — it identifies headings, paragraphs, lists, tables, footnotes, and their hierarchy automatically using ML models.

### Why This Matters for Unstructured Documents
- Narrative financial documents (valuation reports, legal notices, circulars) have implicit structure
- In Block 3 we built a regex-based section detector — Docling replaces that with ML
- Docling produces typed elements → directly usable for section-aware chunking without manual heuristics

### Key Resources
- GitHub: https://github.com/DS4SD/docling
- Documentation: https://ds4sd.github.io/docling/
- Paper: https://arxiv.org/abs/2408.09869
- Supported formats: PDF, DOCX, PPTX, HTML, Images

### Implementation: `03_docling_parsing.py`

```python
"""
Docling-based parsing for unstructured narrative documents.
Key value: automatic structure detection without regex heuristics.
"""
from docling.document_converter import DocumentConverter
from pathlib import Path
from collections import Counter

pdf_path = "data/narrative_document.pdf"

# --- Step 1: Initialize and convert ---
print(f"Parsing with Docling: {pdf_path}")
converter = DocumentConverter()
result = converter.convert(pdf_path)
doc = result.document

# --- Step 2: Get full Markdown output (Docling's killer feature for narrative docs) ---
markdown_output = doc.export_to_markdown()
print(f"\n{'='*50}")
print("DOCLING MARKDOWN OUTPUT (preserves headings, paragraphs, lists)")
print(f"{'='*50}")
print(markdown_output[:1500])
print(f"\n... (total {len(markdown_output)} chars)")

# --- Step 3: Iterate typed elements ---
documents_docling = []
for item, level in doc.iterate_items():
    element_type = item.__class__.__name__
    
    # Get text content
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
            "source": str(pdf_path),
            "element_type": element_type.lower(),
            "hierarchy_level": level,
            "parser": "docling",
        }
    })

# --- Step 4: Analyze what Docling found ---
print(f"\n[Docling] Total elements: {len(documents_docling)}")
print(f"\nElement type breakdown:")
type_counts = Counter(d["metadata"]["element_type"] for d in documents_docling)
for t, count in type_counts.most_common():
    print(f"  {t}: {count}")

# --- Step 5: Show document structure (what regex heuristics tried to do) ---
print(f"\n{'='*50}")
print("DOCUMENT STRUCTURE (auto-detected by Docling)")
print(f"{'='*50}")
for doc_item in documents_docling[:15]:
    indent = "  " * doc_item["metadata"]["hierarchy_level"]
    etype = doc_item["metadata"]["element_type"]
    preview = doc_item["content"][:80].replace("\n", " ")
    print(f"{indent}[{etype}] {preview}")

# --- Step 6: Extract sections naturally (no regex needed!) ---
print(f"\n{'='*50}")
print("SECTIONS DETECTED (compare with manual regex approach)")
print(f"{'='*50}")
headings = [d for d in documents_docling if d["metadata"]["element_type"] in 
            ("sectionheader", "title", "heading")]
for h in headings:
    level = h["metadata"]["hierarchy_level"]
    print(f"  {'  ' * level}• {h['content'][:60]}")

# --- Step 7: Group content by sections (for section-aware chunking) ---
sections_docling = []
current_section = {"title": "Document Start", "content": [], "level": 0}

for d in documents_docling:
    if d["metadata"]["element_type"] in ("sectionheader", "title", "heading"):
        # Save previous section
        if current_section["content"]:
            sections_docling.append({
                "title": current_section["title"],
                "content": "\n".join(current_section["content"]),
                "level": current_section["level"],
            })
        # Start new section
        current_section = {
            "title": d["content"],
            "content": [],
            "level": d["metadata"]["hierarchy_level"],
        }
    else:
        current_section["content"].append(d["content"])

# Don't forget last section
if current_section["content"]:
    sections_docling.append({
        "title": current_section["title"],
        "content": "\n".join(current_section["content"]),
        "level": current_section["level"],
    })

print(f"\n\nSections identified: {len(sections_docling)}")
for s in sections_docling[:5]:
    print(f"  [{s['level']}] {s['title'][:50]} ({len(s['content'])} chars)")
```

### What to Observe (vs Baseline)
| Aspect | pdfplumber/PyMuPDF | Docling |
|--------|-------------------|---------|
| Output | Raw text dump | Typed elements with hierarchy |
| Structure detection | None (you build regex) | Automatic (ML-based) |
| Section boundaries | Manual heuristics | Auto-detected headings |
| Heading identification | Guessing from CAPS/formatting | Confident classification |
| Markdown output | None | Clean, structured |
| Effort for chunking | High (build section detector) | Low (sections pre-identified) |

### Key Insight
> Docling eliminates the need for the entire "heuristic section detection" code in Block 3.
> It turns unstructured text → structured elements automatically.

---

## Block 2C: Document Parsing with Unstructured.io — Element-Based (45 min)

### Goal
Use Unstructured.io to parse the same PDF. Unstructured excels at **element-based partitioning** — it produces fine-grained, categorized elements and has built-in chunking that groups elements under their parent heading.

### Why Unstructured.io for Unstructured Documents
- Built-in OCR handling (auto-detects scanned pages and runs OCR)
- `hi_res` strategy uses layout models for complex financial notices
- `chunk_by_title` auto-groups paragraphs under their heading → instant section-aware chunks
- Handles 25+ formats (PDF, DOCX, HTML, email, images) with same API
- Production-ready with cloud API option

### Key Resources
- GitHub: https://github.com/Unstructured-IO/unstructured
- Documentation: https://docs.unstructured.io/
- Free API Key: https://unstructured.io/api-key-hosted
- Element types reference: https://docs.unstructured.io/open-source/concepts/document-elements

### Implementation: `04_unstructured_parsing.py`

```python
"""
Unstructured.io parsing for narrative financial documents.
Key value: element-based partitioning + built-in chunking by title.
"""
from unstructured.partition.pdf import partition_pdf
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import (
    Title, NarrativeText, ListItem, Table, Header, Footer
)
from collections import Counter

pdf_path = "data/narrative_document.pdf"

# --- Step 1: Partition document into elements ---
print(f"Parsing with Unstructured.io: {pdf_path}")
print("Strategy: 'fast' (switch to 'hi_res' for layout model)")

elements = partition_pdf(
    filename=pdf_path,
    strategy="fast",              # "fast" = text extraction, "hi_res" = layout model
    include_metadata=True,
    include_page_breaks=True,
)

print(f"\n[Unstructured] Total elements: {len(elements)}")

# --- Step 2: Element type analysis ---
print(f"\nElement type breakdown:")
type_counts = Counter(type(el).__name__ for el in elements)
for t, count in type_counts.most_common():
    print(f"  {t}: {count}")

# --- Step 3: Show elements with their types ---
print(f"\n{'='*50}")
print("ELEMENT STREAM (first 15 elements)")
print(f"{'='*50}")
for i, el in enumerate(elements[:15]):
    el_type = type(el).__name__
    page = el.metadata.page_number if hasattr(el.metadata, 'page_number') else "?"
    content_preview = str(el)[:80].replace("\n", " ")
    print(f"  [{el_type:<15}] (p.{page}) {content_preview}")

# --- Step 4: Unstructured's KILLER FEATURE — chunk_by_title ---
# This automatically groups elements under their heading/title
# Basically does what our manual section detection did, but better
print(f"\n{'='*50}")
print("CHUNK BY TITLE (Unstructured built-in section-aware chunking)")
print(f"{'='*50}")

chunks = chunk_by_title(
    elements,
    max_characters=1000,              # Max chunk size
    new_after_n_chars=800,            # Soft limit to start new chunk
    combine_text_under_n_chars=200,   # Merge tiny elements together
)

print(f"\nChunks created: {len(chunks)}")
for i, chunk in enumerate(chunks[:8]):
    chunk_type = type(chunk).__name__
    content = str(chunk)
    print(f"\n--- Chunk {i+1} ({chunk_type}, {len(content)} chars) ---")
    print(f"  {content[:200]}")
    
    # Show how many original elements were merged
    if hasattr(chunk.metadata, 'orig_elements') and chunk.metadata.orig_elements:
        orig_types = [type(e).__name__ for e in chunk.metadata.orig_elements]
        print(f"  (Merged from: {Counter(orig_types)})")

# --- Step 5: Convert to our standard document format ---
documents_unstructured = []
for el in elements:
    content = str(el)
    if len(content.strip()) < 10:
        continue
    
    documents_unstructured.append({
        "content": content,
        "metadata": {
            "source": str(pdf_path),
            "element_type": type(el).__name__.lower(),
            "page": el.metadata.page_number if hasattr(el.metadata, 'page_number') else None,
            "parser": "unstructured",
        }
    })

# --- Step 6: Compare element detection ---
print(f"\n{'='*50}")
print("TITLES/HEADINGS DETECTED")
print(f"{'='*50}")
titles = [el for el in elements if isinstance(el, Title)]
for t in titles:
    print(f"  • {str(t)[:60]} (page {t.metadata.page_number})")

# --- Step 7: Try with hi_res for better results (optional, slower) ---
# Uncomment below if you have detectron2/yolox installed
"""
print(f"\n{'='*50}")
print("HI-RES STRATEGY (layout model)")
print(f"{'='*50}")

elements_hires = partition_pdf(
    filename=pdf_path,
    strategy="hi_res",
    hi_res_model_name="yolox",
    include_metadata=True,
)
print(f"Hi-res elements: {len(elements_hires)}")
print(f"Type breakdown: {Counter(type(el).__name__ for el in elements_hires)}")
"""

# --- Step 8: Scanned PDF handling (built-in OCR) ---
print(f"\n{'='*50}")
print("SCANNED PDF — Unstructured auto-OCR")
print(f"{'='*50}")

scanned_pdf = "data/scanned_document.pdf"
try:
    elements_scanned = partition_pdf(
        filename=scanned_pdf,
        strategy="ocr_only",      # Force OCR on all pages
        include_metadata=True,
    )
    print(f"Scanned PDF elements: {len(elements_scanned)}")
    for el in elements_scanned[:5]:
        print(f"  [{type(el).__name__}] {str(el)[:100]}")
except Exception as e:
    print(f"  OCR strategy requires tesseract/paddleocr. Error: {e}")
```

### What to Observe (vs Baseline & Docling)
| Aspect | pdfplumber | Docling | Unstructured.io |
|--------|-----------|---------|-----------------|
| Structure detection | ❌ None | ✅ ML-based | ✅ Rule + ML based |
| Built-in OCR | ❌ | ✅ | ✅ (auto-detects) |
| Built-in chunking | ❌ | ❌ | ✅ `chunk_by_title` |
| Element granularity | Page-level text | Typed elements | Fine-grained elements |
| Multi-format | PDF only | PDF, DOCX, PPTX | 25+ formats |
| Speed | ⚡ Fast | 🐢 Moderate | ⚡ Fast / 🐢 hi_res |
| Best for | Simple text extraction | Hierarchy understanding | Real-world messy docs |

### Key Insight
> Unstructured's `chunk_by_title` is incredibly powerful — it basically gives you section-aware chunking for FREE without any custom code. Combined with its auto-OCR, it handles the majority of unstructured financial document scenarios.

---

## Block 2D: Head-to-Head Parser Comparison (15 min)

### Implementation: `05_compare_parsers.py`

```python
"""
Compare all parsing approaches on the same document.
Which gives best results for unstructured narrative financial docs?
"""
from rich.console import Console
from rich.table import Table as RichTable

console = Console()

# --- Comparison matrix ---
table = RichTable(title="Parser Comparison — Unstructured Narrative PDFs")
table.add_column("Metric", style="cyan")
table.add_column("pdfplumber", style="green")
table.add_column("Docling", style="yellow")  
table.add_column("Unstructured.io", style="magenta")

table.add_row("Total elements", 
    f"{len(pages_plumber)} pages (raw text)",
    f"{len(documents_docling)} typed elements",
    f"{len(documents_unstructured)} typed elements")

table.add_row("Auto structure detection", "❌ No", "✅ Yes (ML)", "✅ Yes (rules+ML)")
table.add_row("Headings identified", "❌ Manual regex", 
    f"✅ {len([d for d in documents_docling if 'header' in d['metadata']['element_type'] or 'title' in d['metadata']['element_type']])}",
    f"✅ {len([d for d in documents_unstructured if d['metadata']['element_type'] == 'title'])}")
table.add_row("Built-in OCR", "❌", "✅", "✅")
table.add_row("Built-in chunking", "❌", "❌", "✅ chunk_by_title")
table.add_row("Hierarchy/nesting", "❌", "✅ Levels", "⚠️ Parent IDs")
table.add_row("Markdown export", "❌", "✅ Excellent", "❌")
table.add_row("Setup complexity", "Easy", "Easy (pip)", "Easy (pip)")

console.print(table)

# --- Recommendation for unstructured docs ---
print("""
┌─────────────────────────────────────────────────────────────────┐
│  RECOMMENDATION FOR UNSTRUCTURED FINANCIAL DOCUMENTS            │
├─────────────────────────���───────────────────────────────────────┤
│                                                                 │
│  1. Use DOCLING when you need:                                  │
│     • Clean document hierarchy                                  │
│     • Accurate heading/section detection                        │
│     • Markdown output for LLM context                           │
│     • Best: long narrative reports (valuation, legal)           │
│                                                                 │
│  2. Use UNSTRUCTURED.IO when you need:                          │
│     • Built-in chunking (chunk_by_title)                        │
│     • Auto-OCR for mixed scanned+native docs                   │
│     • Multi-format pipeline (PDF + DOCX + Email)               │
│     • Best: messy real-world auction notices                    │
│                                                                 │
│  3. Use PDFPLUMBER/PYMUPDF when you need:                       │
│     • Fast text extraction (preprocessing step)                 │
│     • Scanned page detection (before routing to OCR)            │
│     • Simple documents where structure doesn't matter           │
│                                                                 │
│  Enterprise Strategy:                                           │
│  → Docling as primary (best structure) + Unstructured for       │
│    multi-format coverage + pdfplumber as fast fallback          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
""")
```

---

## Block 3: Chunking Strategies — 4 Approaches Compared (45 min)

### Goal
Compare chunking strategies including Unstructured's built-in `chunk_by_title` and Docling's section-based output. This is where we see the payoff of better parsing.

### Key Concepts to Learn
- Naive chunking (baseline — demonstrates why it's bad)
- Recursive character splitting (LangChain — industry standard)
- Section-aware chunking (custom heuristics — from Block 2A)
- **Unstructured chunk_by_title** (zero-code section chunking — from Block 2C)
- **Docling section-based** (ML-detected sections — from Block 2B)

### Implementation: `06_chunking_comparison.py`

```python
"""
Four chunking strategies compared:
1. Naive fixed-size chunking
2. Recursive character splitting (LangChain)
3. Section-aware semantic chunking (manual heuristics)
4. Docling/Unstructured auto-section chunking (ML-based — NEW)
"""
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
import tiktoken

# --- Load extracted text (from Block 2) ---
# Assume full_text is the complete document text
# full_text = "\n\n".join([p["text"] for p in pages_plumber])

# For demo, use a sample:
full_text = """[Paste or load your extracted text here]"""

# ============================================================
# STRATEGY 1: Naive Fixed-Size Chunking
# ============================================================
def naive_chunk(text: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """Simple character-based chunking. Breaks mid-word, mid-sentence."""
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size]
        chunks.append({
            "content": chunk,
            "method": "naive",
            "char_start": i,
            "char_end": i + len(chunk),
        })
    return chunks

# ============================================================
# STRATEGY 2: Recursive Character Splitting (Industry Standard)
# ============================================================
def recursive_chunk(text: str, chunk_size: int = 500, overlap: int = 100) -> list[dict]:
    """LangChain recursive splitter — respects paragraphs, sentences, words."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],  # Priority order
        length_function=len,
    )
    splits = splitter.split_text(text)
    return [{"content": s, "method": "recursive", "index": i} for i, s in enumerate(splits)]

# ============================================================
# STRATEGY 3: Section-Aware Chunking (Custom Financial)
# ============================================================
def detect_sections(text: str) -> list[dict]:
    """Detect section boundaries using heuristics common in financial docs."""
    sections = []
    current_section = {"title": "Introduction", "content": "", "level": 0}
    
    # Patterns common in financial documents
    heading_patterns = [
        (r"^[A-Z][A-Z\s]{5,}$", 1),              # ALL CAPS LINE = Level 1
        (r"^\d+\.\s+[A-Z]", 2),                    # "1. Title" = Level 2
        (r"^[a-z]\)\s+", 3),                        # "a) Subpoint" = Level 3
        (r"^(?:SCHEDULE|ANNEXURE|APPENDIX)\s", 1),  # Document sections
        (r"^(?:Note|NOTE|Terms|TERMS)", 2),         # Common financial headings
    ]
    
    lines = text.split("\n")
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            current_section["content"] += "\n"
            continue
        
        # Check if line is a heading
        is_heading = False
        for pattern, level in heading_patterns:
            if re.match(pattern, stripped):
                # Save current section
                if current_section["content"].strip():
                    sections.append(current_section.copy())
                # Start new section
                current_section = {
                    "title": stripped,
                    "content": "",
                    "level": level,
                }
                is_heading = True
                break
        
        if not is_heading:
            current_section["content"] += line + "\n"
    
    # Don't forget last section
    if current_section["content"].strip():
        sections.append(current_section)
    
    return sections

def section_aware_chunk(text: str, max_chunk_size: int = 800) -> list[dict]:
    """Chunk by sections, splitting large sections with recursive splitter."""
    sections = detect_sections(text)
    chunks = []
    
    for section in sections:
        content = f"[Section: {section['title']}]\n{section['content'].strip()}"
        
        if len(content) <= max_chunk_size:
            # Section fits in one chunk
            chunks.append({
                "content": content,
                "method": "section_aware",
                "section_title": section["title"],
                "section_level": section["level"],
            })
        else:
            # Section too large — split with recursive but preserve section context
            sub_splitter = RecursiveCharacterTextSplitter(
                chunk_size=max_chunk_size,
                chunk_overlap=100,
            )
            sub_chunks = sub_splitter.split_text(content)
            for i, sc in enumerate(sub_chunks):
                chunks.append({
                    "content": sc,
                    "method": "section_aware",
                    "section_title": section["title"],
                    "section_level": section["level"],
                    "sub_chunk": i,
                })
    
    return chunks

# ============================================================
# COMPARE ALL THREE
# ============================================================
chunks_naive = naive_chunk(full_text)
chunks_recursive = recursive_chunk(full_text)
chunks_section = section_aware_chunk(full_text)

# ============================================================
# STRATEGY 4: Docling/Unstructured Auto-Section Chunking (ML-based)
# ============================================================
# Option A: Use Docling sections (from Block 2B)
chunks_docling = []
for section in sections_docling:  # sections_docling from 03_docling_parsing.py
    content = f"[{section['title']}]\n{section['content']}"
    if len(content) > 1000:
        # Split large sections
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        for i, sub in enumerate(splitter.split_text(content)):
            chunks_docling.append({
                "content": sub,
                "method": "docling_section",
                "section_title": section["title"],
                "section_level": section["level"],
            })
    else:
        chunks_docling.append({
            "content": content,
            "method": "docling_section",
            "section_title": section["title"],
            "section_level": section["level"],
        })

# Option B: Use Unstructured chunk_by_title (from Block 2C)
chunks_unstructured = [
    {
        "content": str(chunk),
        "method": "unstructured_title",
        "section_title": str(chunk)[:50],  # First line as title proxy
    }
    for chunk in chunks  # chunks from chunk_by_title in 04_unstructured_parsing.py
    if len(str(chunk).strip()) > 20
]

print(f"{'='*50}")
print(f"Chunking Strategy Comparison")
print(f"{'='*50}")
print(f"Document length: {len(full_text)} chars")
print(f"")
print(f"{'Strategy':<20} {'Chunks':<10} {'Avg Size':<12} {'Min':<8} {'Max':<8}")
print(f"{'-'*58}")

for name, chunks in [("Naive", chunks_naive), ("Recursive", chunks_recursive), ("Section-Aware", chunks_section), ("Docling Sections", chunks_docling), ("Unstructured Title", chunks_unstructured)]:
    sizes = [len(c["content"]) for c in chunks]
    print(f"{name:<20} {len(chunks):<10} {sum(sizes)/len(sizes):<12.0f} {min(sizes):<8} {max(sizes):<8}")

# Show sample chunks from each
print(f"\n--- Sample: Naive Chunk ---")
print(chunks_naive[0]["content"][:200])
print(f"\n--- Sample: Recursive Chunk ---")
print(chunks_recursive[0]["content"][:200])
print(f"\n--- Sample: Section-Aware Chunk (manual heuristics) ---")
print(chunks_section[0]["content"][:200])
print(f"\n--- Sample: Docling Section Chunk (ML-detected) ---")
print(chunks_docling[0]["content"][:200])
print(f"\n--- Sample: Unstructured chunk_by_title ---")
print(chunks_unstructured[0]["content"][:200])
```

---

## Block 4: Embedding + Retrieval + QA Pipeline (45 min)

### Goal
Index all chunking strategies (including Docling and Unstructured-based) and compare retrieval quality side-by-side.

### Implementation: `07_retrieval_qa.py`

```python
"""
End-to-end RAG with comparison across chunking strategies.
"""
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import os, uuid
from dotenv import load_dotenv

load_dotenv()

# --- Setup ---
embed_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
qdrant = QdrantClient(":memory:")
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Create separate collections for each strategy ---
strategies = {
    "naive": chunks_naive,
    "recursive": chunks_recursive,
    "section_aware": chunks_section,
    "docling_section": chunks_docling,
    "unstructured_title": chunks_unstructured,
}

for strategy_name, chunks in strategies.items():
    collection_name = f"unstructured_{strategy_name}"
    
    qdrant.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    
    points = []
    for chunk in chunks:
        embedding = embed_model.encode(chunk["content"][:512]).tolist()
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "content": chunk["content"],
                "method": chunk["method"],
                "section_title": chunk.get("section_title", ""),
            }
        ))
    
    qdrant.upsert(collection_name=collection_name, points=points)
    print(f"Indexed {len(points)} chunks in '{collection_name}'")

# --- Retrieval function ---
def retrieve_from_strategy(query: str, strategy: str, top_k: int = 3):
    collection_name = f"unstructured_{strategy}"
    query_vec = embed_model.encode(query).tolist()
    
    results = qdrant.search(
        collection_name=collection_name,
        query_vector=query_vec,
        limit=top_k,
    )
    return results

# --- Compare retrieval across strategies ---
def compare_retrieval(query: str):
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}")
    
    for strategy in ["naive", "recursive", "section_aware", "docling_section", "unstructured_title"]:
        results = retrieve_from_strategy(query, strategy, top_k=3)
        print(f"\n  [{strategy.upper()}] Top score: {results[0].score:.4f}")
        print(f"  Top chunk preview: {results[0].payload['content'][:150]}...")
        if results[0].payload.get("section_title"):
            print(f"  Section: {results[0].payload['section_title']}")
    
    return results

# --- Full QA with best strategy ---
def answer_with_rag(query: str, strategy: str = "section_aware"):
    results = retrieve_from_strategy(query, strategy, top_k=5)
    
    context = "\n\n---\n\n".join([
        f"[Chunk {i+1}] {r.payload.get('section_title', 'General')}\n{r.payload['content']}"
        for i, r in enumerate(results)
    ])
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """You are a financial document analyst.
Answer based ONLY on the provided context. Cite [Chunk N] for evidence.
If the answer is not in the context, say so explicitly."""},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ],
        temperature=0,
    )
    
    return {
        "answer": response.choices[0].message.content,
        "chunks_used": len(results),
        "top_score": results[0].score,
    }

# --- Test queries ---
test_queries = [
    "What are the terms and conditions of the auction?",
    "Who is the authorized officer?",
    "What is the date of inspection?",
    "Describe the property details",
    "What is the earnest money deposit amount?",
]

print("\n\n" + "="*60)
print("RETRIEVAL COMPARISON ACROSS STRATEGIES")
print("="*60)

for q in test_queries:
    compare_retrieval(q)

print("\n\n" + "="*60)
print("FULL QA ANSWERS (Section-Aware Strategy)")
print("="*60)

for q in test_queries[:3]:
    result = answer_with_rag(q)
    print(f"\nQ: {q}")
    print(f"A: {result['answer']}")
    print(f"   (Top score: {result['top_score']:.3f})")
```

---

## Block 5: Compare All Approaches + Evaluation (30 min)

### Implementation: `08_evaluation.py`

```python
"""
Compare chunking strategies on retrieval quality.
Key question: Which strategy retrieves the most relevant chunk for each query?
"""

# Manual relevance judgments (you fill these after seeing the data)
evaluation_set = [
    {
        "query": "What are the terms and conditions?",
        "relevant_section": "TERMS AND CONDITIONS",  # Expected section
        "relevant_keywords": ["terms", "conditions", "deposit", "payment"],
    },
    {
        "query": "Property description and location",
        "relevant_section": "PROPERTY",
        "relevant_keywords": ["property", "situated", "area", "sq"],
    },
    {
        "query": "Who issued this notice?",
        "relevant_section": "AUTHORIZED",
        "relevant_keywords": ["authorized", "officer", "bank", "branch"],
    },
]

def evaluate_strategy(strategy: str, eval_set: list) -> dict:
    scores = {"section_hit": 0, "keyword_hit": 0, "avg_score": 0}
    
    for case in eval_set:
        results = retrieve_from_strategy(case["query"], strategy, top_k=3)
        
        # Check section hit (for section_aware strategy)
        top_sections = [r.payload.get("section_title", "").upper() for r in results]
        if any(case["relevant_section"] in s for s in top_sections):
            scores["section_hit"] += 1
        
        # Check keyword hit
        top_content = " ".join([r.payload["content"].lower() for r in results])
        keyword_hits = sum(1 for kw in case["relevant_keywords"] if kw in top_content)
        if keyword_hits >= 2:
            scores["keyword_hit"] += 1
        
        scores["avg_score"] += results[0].score
    
    n = len(eval_set)
    return {
        "section_accuracy": scores["section_hit"] / n,
        "keyword_accuracy": scores["keyword_hit"] / n,
        "avg_top_score": scores["avg_score"] / n,
    }

# --- Run evaluation ---
print(f"\n{'='*60}")
print("CHUNKING STRATEGY EVALUATION")
print(f"{'='*60}\n")
print(f"{'Strategy':<15} {'Section Hit':<15} {'Keyword Hit':<15} {'Avg Score':<12}")
print(f"{'-'*57}")

for strategy in ["naive", "recursive", "section_aware", "docling_section", "unstructured_title"]:
    result = evaluate_strategy(strategy, evaluation_set)
    print(f"{strategy:<15} {result['section_accuracy']:<15.0%} {result['keyword_accuracy']:<15.0%} {result['avg_top_score']:<12.3f}")
```

---

## Key Observations Template

### Fill after completing the POC:

| Aspect | Naive | Recursive | Section-Aware (regex) | Docling Sections | Unstructured chunk_by_title |
|--------|-------|-----------|----------------------|------------------|---------------------------|
| Retrieval relevance | | | | | |
| Chunk coherence | | | | | |
| Section boundary respect | | | | | |
| Answer quality | | | | | |
| Implementation complexity | Low | Low | Medium | Low (ML does it) | Low (built-in) |

### What Worked
- [ ] OCR detection heuristic (char count < 50)
- [ ] Recursive chunking for general text
- [ ] Section-aware chunking for structured narratives
- [ ] **Docling auto-structure detection (replaces regex heuristics)**
- [ ] **Unstructured chunk_by_title (zero-code section chunking)**
- [ ] Page-level metadata for citations
- [ ] BGE embeddings quality for financial text

### What Didn't Work
- [ ] Naive chunking breaks mid-sentence
- [ ] OCR on low-quality scans
- [ ] Manual regex section detection on irregular documents
- [ ] Short queries retrieving long irrelevant chunks
- [ ] Any parser struggling with specific document layouts?

### Enterprise Implications
- [ ] **Docling eliminates manual section detection — use as primary parser**
- [ ] **Unstructured's chunk_by_title = instant production-ready chunking**
- [ ] Recursive chunking is a solid baseline — start here for unknown docs
- [ ] Hybrid retrieval needed for keyword-heavy financial queries
- [ ] Context window management critical for long documents
- [ ] Multi-parser strategy: Docling for quality, Unstructured for coverage

---

## Resources & Links

| Resource | Link | Why |
|----------|------|-----|
| **Docling (IBM)** | https://github.com/DS4SD/docling | Structure-aware parsing — auto-detects sections/headings |
| Docling Documentation | https://ds4sd.github.io/docling/ | Setup, examples, API reference |
| Docling Research Paper | https://arxiv.org/abs/2408.09869 | Understand the ML approach |
| **Unstructured.io** | https://github.com/Unstructured-IO/unstructured | Element-based parsing + built-in chunking |
| Unstructured Docs | https://docs.unstructured.io/ | Full documentation |
| Unstructured API (free tier) | https://unstructured.io/api-key-hosted | Cloud API for hi_res |
| Unstructured Element Types | https://docs.unstructured.io/open-source/concepts/document-elements | Reference for element categories |
| pdfplumber | https://github.com/jsvine/pdfplumber | Text + table extraction from PDFs |
| PyMuPDF (fitz) | https://pymupdf.readthedocs.io/en/latest/ | Fast PDF text extraction |
| Tesseract OCR | https://github.com/tesseract-ocr/tesseract | Open-source OCR engine |
| pytesseract | https://github.com/madmaze/pytesseract | Python wrapper for Tesseract |
| pdf2image | https://github.com/Belval/pdf2image | PDF → image conversion for OCR |
| Poppler (Windows) | https://github.com/osber/poppler-for-windows | Required by pdf2image on Windows |
| LangChain Text Splitters | https://python.langchain.com/docs/modules/data_connection/document_transformers/ | Recursive and character splitters |
| Sentence Transformers | https://www.sbert.net/ | Embedding models |
| BGE Models | https://huggingface.co/BAAI/bge-small-en-v1.5 | Retrieval-optimized embeddings |
| Qdrant | https://qdrant.tech/documentation/ | Vector database |
| OpenAI API | https://platform.openai.com/docs/api-reference | LLM for generation |
| Chunking Research (Pinecone) | https://www.pinecone.io/learn/chunking-strategies/ | Comparison of strategies |
| RAG Best Practices | https://docs.llamaindex.ai/en/stable/optimizing/production_rag/ | Production RAG optimization |
| Marker (PDF→Markdown) | https://github.com/VikParuchuri/marker | Alternative PDF extraction |
| Surya (Layout OCR) | https://github.com/VikParuchuri/surya | Layout-aware OCR for enterprise |

---

## Next Steps (After POC)

1. → Use **Docling** as primary parser in enterprise pipeline (replaces manual heuristics entirely)
2. → Use **Unstructured.io chunk_by_title** as default chunking for production
3. → Add **hybrid retrieval** (BM25 + dense) — important for financial keyword queries
4. → Add **reranking** with cross-encoder (e.g., `BAAI/bge-reranker-base`)
5. → Try **contextual chunking** — prepend document summary to each chunk before embedding
6. → Experiment with **parent-child retrieval** (retrieve child chunk, expand to parent section via Docling hierarchy)
7. → Try Unstructured's `hi_res` strategy with layout model for complex auction notices
8. → Connect to enterprise architecture Layers A, B, C, D, E

---

## Quick Reference: When to Use What

| Document Type | Best Parser | Best Chunking | Notes |
|--------------|------------|---------------|-------|
| Text-native PDF (narrative) | **Docling** | Docling sections / chunk_by_title | Auto-detects structure |
| Scanned PDF | **Unstructured** (`ocr_only` or `hi_res`) | Recursive (structure lost) | Built-in OCR handling |
| Mixed PDF (text + scans) | **Unstructured** (`hi_res`) | chunk_by_title | Auto-detects + OCRs scanned pages |
| Long narrative (50+ pages) | **Docling** | Docling sections + recursive | Hierarchy enables parent-child retrieval |
| Short notice (1-3 pages) | pdfplumber or Docling | Full-page or recursive | Simple docs don't need complex parsing |
| Multi-format (PDF + DOCX + Email) | **Unstructured** | chunk_by_title | Same API for all formats |
| Complex layout (multi-column) | **Unstructured** (`hi_res`) | chunk_by_title | Layout model handles columns |

