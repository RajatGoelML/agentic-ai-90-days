"""
DEBUG FILE for 01a_excel_docling.py
=====================================
Purpose  : Deep-inspect every step of the Docling Excel ingestion pipeline.
           See exactly what Docling produces, what the chunks look like,
           and what the final retrieval-ready output contains.

Run      : python debug_01a_excel_docling.py
           python debug_01a_excel_docling.py --file LoanDataset.xlsx
           python debug_01a_excel_docling.py --file govData.xlsx

Sections :
  [1] Pandas peek          — raw shape, columns, sample rows
  [2] Docling raw output   — what the converter returns
  [3] Element inspector    — every element: type, level, content
  [4] Chunk inspector      — every chunk: strategy, size, preview
  [5] End-result viewer    — final chunks ready for embedding
  [6] Problem detector     — auto-flag issues (empty content, bad headers, etc.)
"""

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd
from docling.document_converter import DocumentConverter
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich.syntax import Syntax

console = Console()
DATA_DIR = Path(__file__).parent / "data"

# ── CLI args ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--file", default=None,
                    help="Single filename in data/ e.g. LoanDataset.xlsx. "
                         "Omit to run on both files.")
args = parser.parse_args()

if args.file:
    EXCEL_FILES = [DATA_DIR / args.file]
else:
    EXCEL_FILES = [DATA_DIR / "LoanDataset.xlsx", DATA_DIR / "govData.xlsx"]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — PANDAS PEEK
# ─────────────────────────────────────────────────────────────────────────────
def section1_pandas_peek(path: Path):
    console.print(Rule(f"[bold cyan]SECTION 1 · PANDAS PEEK — {path.name}[/bold cyan]"))

    xl = pd.ExcelFile(path)
    console.print(f"  📄 Sheets found : [yellow]{xl.sheet_names}[/yellow]")

    for sheet in xl.sheet_names:
        df_full = pd.read_excel(xl, sheet_name=sheet)
        df_peek = df_full.head(5)

        t = Table(title=f"Sheet: '{sheet}'  ({len(df_full)} rows × {len(df_full.columns)} cols)",
                  show_lines=True, header_style="bold magenta")

        for col in df_peek.columns[:10]:          # show max 10 cols for readability
            t.add_column(str(col), overflow="fold", max_width=18)

        for _, row in df_peek.iterrows():
            t.add_row(*[str(v)[:18] for v in row.values[:10]])

        console.print(t)

        if len(df_full.columns) > 10:
            console.print(f"  [dim](+ {len(df_full.columns)-10} more columns not shown)[/dim]")

        # Numeric stats
        num_cols = df_full.select_dtypes(include="number").columns.tolist()
        if num_cols:
            console.print(f"\n  [green]Numeric columns ({len(num_cols)}):[/green]")
            for c in num_cols[:6]:
                console.print(f"    {c:<30}  min={df_full[c].min():<12}  "
                               f"max={df_full[c].max():<12}  mean={df_full[c].mean():.2f}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — DOCLING RAW OUTPUT
# ─────────────────────────────────────────────────────────────────────────────
def section2_docling_raw(path: Path, doc):
    console.print(Rule(f"[bold cyan]SECTION 2 · DOCLING RAW OUTPUT — {path.name}[/bold cyan]"))

    md = doc.export_to_markdown()
    console.print(f"  Total markdown size : [yellow]{len(md):,} chars[/yellow]")
    console.print(f"  Total lines         : [yellow]{md.count(chr(10)):,}[/yellow]\n")

    # Show first 60 lines of markdown
    lines = md.split("\n")[:60]
    console.print(Panel(
        "\n".join(lines),
        title="[bold]Markdown (first 60 lines)[/bold]",
        subtitle="[dim]Docling's clean table output[/dim]",
        border_style="green",
    ))

    # JSON structure (limited)
    try:
        doc_dict = doc.export_to_dict()
        top_keys = list(doc_dict.keys())
        console.print(f"\n  [green]JSON export top-level keys:[/green] {top_keys}")
        # Show body count
        if "body" in doc_dict:
            console.print(f"  Body items: {len(doc_dict['body'])}")
    except Exception as e:
        console.print(f"  [dim]JSON export: {e}[/dim]")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — ELEMENT INSPECTOR
# ─────────────────────────────────────────────────────────────────────────────
def section3_elements(path: Path, doc) -> list[dict]:
    console.print(Rule(f"[bold cyan]SECTION 3 · ELEMENT INSPECTOR — {path.name}[/bold cyan]"))

    elements = []
    for item, level in doc.iterate_items():
        etype = item.__class__.__name__

        try:
            content = item.export_to_markdown(doc=doc)
        except TypeError:
            content = item.export_to_markdown()
        except Exception:
            content = getattr(item, "text", "") or ""

        elements.append({
            "element_type": etype,
            "level":        level,
            "content":      content,
            "char_count":   len(content),
        })

    # Summary table
    t = Table(title="Element Summary", show_lines=True, header_style="bold blue")
    t.add_column("Element Type", style="yellow")
    t.add_column("Count", justify="right")
    t.add_column("Total Chars", justify="right")
    t.add_column("Avg Chars", justify="right")

    type_groups: dict[str, list] = {}
    for el in elements:
        type_groups.setdefault(el["element_type"], []).append(el["char_count"])

    for etype, sizes in sorted(type_groups.items()):
        t.add_row(etype, str(len(sizes)),
                  f"{sum(sizes):,}", f"{sum(sizes)//len(sizes):,}")
    console.print(t)

    # Deep-dive: show each element with a number
    console.print(f"\n[bold]Individual elements ({len(elements)} total):[/bold]")
    for i, el in enumerate(elements):
        color = "yellow" if "Table" in el["element_type"] else "white"
        preview = el["content"][:200].replace("\n", "↵ ")
        console.print(
            f"  [dim]#{i+1:>3}[/dim]  "
            f"[{color}]{el['element_type']:<20}[/{color}]  "
            f"level={el['level']}  "
            f"chars={el['char_count']:>8,}  "
            f"preview: [dim]{preview[:80]}[/dim]"
        )

    return elements


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — CHUNK INSPECTOR
# ─────────────────────────────────────────────────────────────────────────────
def build_chunks(elements: list[dict], filename: str) -> list[dict]:
    chunks = []
    for el in elements:
        is_table  = "Table" in el["element_type"]
        content   = el["content"]

        if is_table:
            if len(content) <= 1500:
                chunks.append({
                    "content":  content,
                    "strategy": "full_table",
                    "filename": filename,
                    "el_type":  el["element_type"],
                })
            else:
                lines        = content.split("\n")
                header_lines = lines[:2]
                data_lines   = lines[2:]
                chunk_size   = 15

                for i in range(0, len(data_lines), chunk_size):
                    batch = data_lines[i:i + chunk_size]
                    chunks.append({
                        "content":   "\n".join(header_lines + batch),
                        "strategy":  "table_row_batch",
                        "filename":  filename,
                        "el_type":   el["element_type"],
                        "row_start": i,
                        "row_end":   i + len(batch),
                    })

            # NL summary
            row_count = max(content.count("\n") - 2, 0)
            if "|" in content:
                cols = [c.strip() for c in content.split("\n")[0].split("|") if c.strip()]
                summary = (f"File '{filename}' table with {row_count} rows. "
                           f"Columns: {', '.join(cols)}.")
            else:
                summary = f"File '{filename}' table with ~{row_count} data rows."

            chunks.append({
                "content":  summary,
                "strategy": "table_summary",
                "filename": filename,
                "el_type":  el["element_type"],
            })
        else:
            chunks.append({
                "content":  content,
                "strategy": "text_element",
                "filename": filename,
                "el_type":  el["element_type"],
            })

    return chunks


def section4_chunk_inspector(path: Path, elements: list[dict]) -> list[dict]:
    console.print(Rule(f"[bold cyan]SECTION 4 · CHUNK INSPECTOR — {path.name}[/bold cyan]"))

    chunks = build_chunks(elements, path.name)

    # ── Strategy distribution ──────────────────────────────────────
    t = Table(title="Chunk Strategy Distribution", show_lines=True, header_style="bold blue")
    t.add_column("Strategy",    style="yellow")
    t.add_column("Count",       justify="right")
    t.add_column("Min chars",   justify="right")
    t.add_column("Max chars",   justify="right")
    t.add_column("Avg chars",   justify="right")
    t.add_column("Total chars", justify="right")

    strat_groups: dict[str, list] = {}
    for c in chunks:
        strat_groups.setdefault(c["strategy"], []).append(len(c["content"]))

    for strat, sizes in sorted(strat_groups.items()):
        t.add_row(strat, str(len(sizes)),
                  f"{min(sizes):,}", f"{max(sizes):,}",
                  f"{sum(sizes)//len(sizes):,}", f"{sum(sizes):,}")
    console.print(t)

    # ── Show first 3 chunks of each strategy ──────────────────────
    shown: dict[str, int] = {}
    for i, chunk in enumerate(chunks):
        strat = chunk["strategy"]
        if shown.get(strat, 0) >= 3:
            continue
        shown[strat] = shown.get(strat, 0) + 1

        title = f"Chunk #{i+1} · strategy=[bold]{strat}[/bold] · {len(chunk['content']):,} chars"
        # Show metadata
        meta_lines = [f"  filename  : {chunk['filename']}",
                      f"  el_type   : {chunk['el_type']}",
                      f"  strategy  : {strat}"]
        if "row_start" in chunk:
            meta_lines.append(f"  rows      : {chunk['row_start']} → {chunk['row_end']}")
        meta_lines.append("")

        # Show content preview (first 15 lines)
        content_lines = chunk["content"].split("\n")[:15]
        body = "\n".join(meta_lines) + "\n".join(content_lines)
        if len(chunk["content"].split("\n")) > 15:
            body += f"\n[dim]... (+{len(chunk['content'].split(chr(10)))-15} more lines)[/dim]"

        console.print(Panel(body, title=title, border_style="green", expand=False))

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — END-RESULT VIEWER
# ─────────────────────────────────────────────────────────────────────────────
def section5_end_result(all_chunks: list[dict]):
    console.print(Rule("[bold cyan]SECTION 5 · END RESULT — WHAT GOES INTO THE VECTOR DB[/bold cyan]"))

    console.print(f"\n  Total chunks ready for embedding: [bold green]{len(all_chunks)}[/bold green]")

    # Show what a single embedding-ready record looks like
    if all_chunks:
        sample = all_chunks[0]
        record = {
            "id":       "<uuid-generated-at-index-time>",
            "vector":   "<384-dim float array from BGE embedding>",
            "payload": {
                "content":  sample["content"][:300] + ("..." if len(sample["content"]) > 300 else ""),
                "filename": sample["filename"],
                "strategy": sample["strategy"],
                "el_type":  sample["el_type"],
            }
        }
        console.print(Panel(
            Syntax(json.dumps(record, indent=2, default=str), "json", theme="monokai"),
            title="[bold]Sample Qdrant Point (what gets stored)[/bold]",
            border_style="yellow",
        ))

    # Distribution across files
    t = Table(title="Final Chunk Distribution", show_lines=True, header_style="bold blue")
    t.add_column("File",     style="cyan")
    t.add_column("Strategy", style="yellow")
    t.add_column("Chunks",   justify="right")
    t.add_column("Avg chars",justify="right")

    from collections import defaultdict
    groups: dict = defaultdict(list)
    for c in all_chunks:
        groups[(c["filename"], c["strategy"])].append(len(c["content"]))

    for (fname, strat), sizes in sorted(groups.items()):
        t.add_row(fname, strat, str(len(sizes)), f"{sum(sizes)//len(sizes):,}")
    console.print(t)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — PROBLEM DETECTOR
# ─────────────────────────────────────────────────────────────────────────────
def section6_problem_detector(all_chunks: list[dict]):
    console.print(Rule("[bold cyan]SECTION 6 · PROBLEM DETECTOR[/bold cyan]"))

    issues = []

    for i, c in enumerate(all_chunks):
        content = c["content"]

        # Empty or near-empty
        if len(content.strip()) < 20:
            issues.append((i, "EMPTY/TINY", f"Only {len(content)} chars"))

        # Repeated header problem (govData-style merged cells)
        if "|" in content:
            first_line = content.split("\n")[0]
            cells = [x.strip() for x in first_line.split("|") if x.strip()]
            if len(cells) >= 2 and len(set(cells)) == 1:
                issues.append((i, "REPEATED HEADER",
                                f"All {len(cells)} columns have same value: '{cells[0][:40]}'"))

        # Chunk too large for typical embedding models (512 token limit ≈ ~2000 chars)
        if len(content) > 2500:
            issues.append((i, "TOO LARGE",
                            f"{len(content):,} chars — may exceed embedding token limit"))

        # Chunk suspiciously small for a row batch
        if c["strategy"] == "table_row_batch" and len(content) < 100:
            issues.append((i, "TINY ROW BATCH", f"Only {len(content)} chars for a row batch"))

    if not issues:
        console.print("  [bold green]✅ No problems detected![/bold green]")
    else:
        t = Table(title=f"{len(issues)} Issues Found", show_lines=True,
                  header_style="bold red")
        t.add_column("Chunk #",  justify="right")
        t.add_column("Issue",    style="red")
        t.add_column("Detail")
        t.add_column("Strategy")
        t.add_column("File")

        for chunk_idx, issue_type, detail in issues[:30]:   # show max 30
            c = all_chunks[chunk_idx]
            t.add_row(str(chunk_idx), issue_type, detail, c["strategy"], c["filename"])

        if len(issues) > 30:
            t.add_row("...", f"(+{len(issues)-30} more issues)", "", "", "")
        console.print(t)

        # Fix hints
        console.print("\n[bold]Fix hints:[/bold]")
        issue_types = {i[1] for i in issues}
        if "REPEATED HEADER" in issue_types:
            console.print("  [yellow]REPEATED HEADER[/yellow] → govData.xlsx has merged cells. "
                          "Fix: post-process with pandas, read actual header row explicitly.")
        if "TOO LARGE" in issue_types:
            console.print("  [yellow]TOO LARGE[/yellow]      → Reduce chunk_size from 15 to 8-10 rows, "
                          "or use token-aware splitting.")
        if "EMPTY/TINY" in issue_types:
            console.print("  [yellow]EMPTY/TINY[/yellow]     → Filter out chunks with < 20 chars "
                          "before embedding.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
converter = DocumentConverter()
all_chunks: list[dict] = []

for excel_file in EXCEL_FILES:
    if not excel_file.exists():
        console.print(f"[red]⚠️  File not found: {excel_file}[/red]")
        continue

    console.print(Panel(f"[bold white]{excel_file.name}[/bold white]",
                        style="bold blue", expand=False))

    try:
        # Section 1: pandas peek
        section1_pandas_peek(excel_file)

        # Docling convert (done once, reused by sections 2 & 3)
        console.print(f"\n  [dim]Converting with Docling...[/dim]", end="")
        result = converter.convert(str(excel_file))
        doc    = result.document
        console.print(" [green]done[/green]")

        # Section 2: Docling raw output
        section2_docling_raw(excel_file, doc)

        # Section 3: Element inspector (returns list of dicts)
        elements = section3_elements(excel_file, doc)

        # Section 4: Chunk inspector (builds + inspects chunks)
        chunks = section4_chunk_inspector(excel_file, elements)
        all_chunks.extend(chunks)

    except Exception as e:
        import traceback
        console.print(f"[red]❌ Error processing {excel_file.name}: {e}[/red]")
        traceback.print_exc()

# Section 5: End result (across all files)
section5_end_result(all_chunks)

# Section 6: Problem detector
section6_problem_detector(all_chunks)

console.print(Rule("[bold green]DEBUG COMPLETE[/bold green]"))
console.print(f"  Total chunks produced: [bold green]{len(all_chunks)}[/bold green]")
console.print(f"  These chunks are ready to pass to [bold]03_chunking_and_indexing.py[/bold]\n")

