from docling.document_converter import DocumentConverter
from pathlib import Path
from collections import Counter
import pandas as pd

# ============================================================
# ACTUAL DATA FILES IN THIS PROJECT
# ============================================================
DATA_DIR = Path(__file__).parent / "data"

# Your real Excel files
EXCEL_FILES = [
    DATA_DIR / "LoanDataset.xlsx",
    DATA_DIR / "govData.xlsx",
]

# --- Quick pandas peek BEFORE Docling (to understand what we're dealing with) ---
def peek_excel(path: Path):
    """Show a quick summary of the Excel file using pandas before Docling processes it."""
    print(f"\n{'='*60}")
    print(f"PEEK (pandas): {path.name}")
    print(f"{'='*60}")
    try:
        xl = pd.ExcelFile(path)
        print(f"  Sheets: {xl.sheet_names}")
        for sheet in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=sheet, nrows=3)
            print(f"\n  [Sheet: '{sheet}']  {df.shape[0]}+ rows × {len(df.columns)} cols")
            print(f"  Columns: {list(df.columns)}")
            if len(df) > 0:
                print(f"  Sample row 1: {df.iloc[0].to_dict()}")
    except Exception as e:
        print(f"  ❌ peek failed: {e}")

# Peek at both files first
for f in EXCEL_FILES:
    if f.exists():
        peek_excel(f)
    else:
        print(f"⚠️  File not found: {f}")

# ============================================================
# DOCLING INGESTION
# ============================================================
converter = DocumentConverter()

def ingest_excel_with_docling(excel_path: Path) -> tuple[list[dict], list[dict]]:
    """
    Ingest a single Excel file via Docling.
    Returns (raw_elements, chunks)
    """
    print(f"\n{'='*60}")
    print(f"DOCLING INGESTION: {excel_path.name}")
    print(f"{'='*60}")

    # --- Convert ---
    result = converter.convert(str(excel_path))
    doc    = result.document   # keep doc reference — needed for export_to_markdown(doc=doc)

    # --- Markdown export of full document ---
    markdown_output = doc.export_to_markdown()
    print(f"\n--- Docling Markdown Output (first 2000 chars) ---")
    print(markdown_output[:2000])
    print(f"... (total {len(markdown_output)} chars)\n")

    # --- Extract typed elements ---
    # NOTE: In Docling v2.x the element class name is "TableItem" (not "Table")
    #       We match on .lower() == "tableitem"
    documents = []
    for item, level in doc.iterate_items():
        element_type = item.__class__.__name__   # e.g. "TableItem", "TextItem", "SectionHeaderItem"

        # Pass `doc` to suppress deprecation warning and get correct markdown
        if hasattr(item, 'export_to_markdown'):
            try:
                content = item.export_to_markdown(doc=doc)
            except TypeError:
                content = item.export_to_markdown()          # older API fallback
        elif hasattr(item, 'text') and item.text:
            content = item.text
        else:
            continue

        if not content or len(content.strip()) < 5:
            continue

        documents.append({
            "content": content,
            "metadata": {
                "source":          str(excel_path),
                "filename":        excel_path.name,
                "element_type":    element_type.lower(),   # "tableitem", "textitem", …
                "hierarchy_level": level,
                "parser":          "docling",
                "file_type":       "excel",
            }
        })

    print(f"[Docling] Extracted {len(documents)} elements")
    print("Element types:")
    for t, count in Counter(d["metadata"]["element_type"] for d in documents).most_common():
        print(f"  {t}: {count}")

    # --- Show table elements (class name ends with "tableitem") ---
    tables = [d for d in documents if "table" in d["metadata"]["element_type"]]
    print(f"\n--- Tables Found: {len(tables)} ---")
    for i, t in enumerate(tables[:3]):
        print(f"\n[Table {i+1}]")
        print(t["content"][:800])

    # --- Build chunks ---
    chunks = []
    for doc_item in documents:
        is_table = "table" in doc_item["metadata"]["element_type"]
        table_content = doc_item["content"]

        if is_table:
            # Strategy A: full table (small ≤ 1500 chars)
            if len(table_content) <= 1500:
                chunks.append({
                    "content": table_content,
                    "metadata": {**doc_item["metadata"], "chunk_strategy": "full_table"}
                })
            else:
                # Strategy B: row-batched — always include markdown header row
                lines        = table_content.split("\n")
                header_lines = lines[:2]    # header row + separator row
                data_lines   = lines[2:]
                chunk_size   = 15           # rows per chunk

                for i in range(0, len(data_lines), chunk_size):
                    batch = data_lines[i:i + chunk_size]
                    chunks.append({
                        "content": "\n".join(header_lines + batch),
                        "metadata": {
                            **doc_item["metadata"],
                            "chunk_strategy": "table_row_batch",
                            "row_start":       i,
                            "row_end":         i + len(batch),
                        }
                    })

            # Strategy C: NL summary (always generated for every table)
            row_count = max(table_content.count("\n") - 2, 0)
            if "|" in table_content:
                cols    = [c.strip() for c in table_content.split("\n")[0].split("|") if c.strip()]
                summary = (f"File '{excel_path.name}' table with {row_count} rows. "
                           f"Columns: {', '.join(cols)}.")
            else:
                summary = f"File '{excel_path.name}' table with ~{row_count} data rows."

            chunks.append({
                "content": summary,
                "metadata": {**doc_item["metadata"], "chunk_strategy": "table_summary"}
            })
        else:
            chunks.append({
                "content": table_content,
                "metadata": {**doc_item["metadata"], "chunk_strategy": "text_element"}
            })

    print(f"\n--- Chunk summary: {excel_path.name} ---")
    print(f"  Total chunks: {len(chunks)}")
    for s, cnt in Counter(c["metadata"]["chunk_strategy"] for c in chunks).most_common():
        print(f"    {s}: {cnt}")

    return documents, chunks


# ============================================================
# RUN ON ALL REAL DATA FILES
# ============================================================
all_documents, all_chunks = [], []

for excel_file in EXCEL_FILES:
    if not excel_file.exists():
        print(f"\n⚠️  Skipping (not found): {excel_file}")
        continue
    try:
        docs, chunks = ingest_excel_with_docling(excel_file)
        all_documents.extend(docs)
        all_chunks.extend(chunks)
    except Exception as e:
        import traceback
        print(f"\n❌ Failed to process {excel_file.name}: {e}")
        traceback.print_exc()

# ============================================================
# FINAL SUMMARY
# ============================================================
print(f"\n{'='*60}")
print("OVERALL SUMMARY")
print(f"{'='*60}")
print(f"Files processed : {len([f for f in EXCEL_FILES if f.exists()])}")
print(f"Total elements  : {len(all_documents)}")
print(f"Total chunks    : {len(all_chunks)}")

print(f"\nAll chunk strategies:")
for s, cnt in Counter(c["metadata"]["chunk_strategy"] for c in all_chunks).most_common():
    print(f"  {s}: {cnt}")

print(f"\nChunks by file:")
for f in EXCEL_FILES:
    fc = [c for c in all_chunks if c["metadata"]["filename"] == f.name]
    if fc:
        print(f"  {f.name}: {len(fc)} chunks")

print("\n✅ Ingestion complete — chunks ready for embedding & indexing")
