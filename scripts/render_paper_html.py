from __future__ import annotations

import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "paper" / "semantic-state-prices.md"
HTML_PATH = ROOT / "paper" / "semantic-state-prices.html"


def render_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def render_table(lines: list[str]) -> str:
    rows = []
    for idx, line in enumerate(lines):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if idx == 1 and all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        tag = "th" if idx == 0 else "td"
        rows.append("<tr>" + "".join(f"<{tag}>{render_inline(cell)}</{tag}>" for cell in cells) + "</tr>")
    return "<table>" + "".join(rows) + "</table>"


def markdown_to_html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    list_tag = "ul"
    code_lines: list[str] = []
    table_lines: list[str] = []
    in_code = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            out.append("<p>" + render_inline(" ".join(paragraph).strip()) + "</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items, list_tag
        if list_items:
            out.append(f"<{list_tag}>" + "".join(f"<li>{item}</li>" for item in list_items) + f"</{list_tag}>")
            list_items = []
            list_tag = "ul"

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            out.append(render_table(table_lines))
            table_lines = []

    for line in lines:
        stripped = line.strip()
        if in_code:
            if stripped.startswith("```"):
                out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code = False
            else:
                code_lines.append(line)
            continue

        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            flush_table()
            in_code = True
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            flush_list()
            table_lines.append(stripped)
            continue
        else:
            flush_table()

        image = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if image:
            flush_paragraph()
            flush_list()
            alt, src = image.groups()
            class_name = "operator-figure" if "semantic_operator" in src else "data-figure"
            out.append(
                f'<figure class="{class_name}"><img src="{html.escape(src)}" alt="{html.escape(alt)}">'
                f"<figcaption>{render_inline(alt)}</figcaption></figure>"
            )
            continue

        if not stripped:
            flush_paragraph()
            flush_list()
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            flush_list()
            level = min(len(heading.group(1)), 4)
            out.append(f"<h{level}>{render_inline(heading.group(2))}</h{level}>")
            continue

        if stripped.startswith("- "):
            flush_paragraph()
            if list_tag != "ul":
                flush_list()
            list_tag = "ul"
            list_items.append(render_inline(stripped[2:].strip()))
            continue

        ordered = re.match(r"^\d+\.\s+(.*)$", stripped)
        if ordered:
            flush_paragraph()
            if list_tag != "ol":
                flush_list()
            list_tag = "ol"
            list_items.append(render_inline(ordered.group(1).strip()))
            continue

        paragraph.append(stripped)

    flush_paragraph()
    flush_list()
    flush_table()
    return "\n".join(out)


def main() -> None:
    body = markdown_to_html(MD_PATH.read_text(encoding="utf-8"))
    body = body.replace(
        "<p><strong>Ojas Shukla</strong> Sybilian ojas@sybilian.com May 8, 2026</p>",
        '<div class="author-block"><div>Ojas Shukla</div><div>Sybilian</div><div>ojas@sybilian.com</div><div>May 8, 2026</div></div>',
    )
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Semantic State Prices</title>
<style>
  @page {{ size: letter; margin: 0.75in 0.78in 0.78in 0.78in; }}
  html, body {{ margin: 0; padding: 0; background: #fff; color: #111; }}
  body {{ font-family: "Times New Roman", Times, serif; font-size: 10.6pt; line-height: 1.42; }}
  main {{ max-width: 6.95in; margin: 0 auto; }}
  h1, h2, h3, h4 {{ color: #111; page-break-after: avoid; break-after: avoid; }}
  h1 {{ font-size: 19pt; line-height: 1.12; margin: 0 0 8pt; text-align: center; font-weight: 700; }}
  .author-block {{ text-align: center; font-size: 10.6pt; line-height: 1.25; margin: 0 0 18pt; }}
  h2 {{ font-size: 13pt; margin: 18pt 0 6pt; font-weight: 700; }}
  h3 {{ font-size: 11pt; margin: 13pt 0 4pt; font-style: italic; font-weight: 700; }}
  h4 {{ font-size: 10.6pt; margin: 10pt 0 4pt; font-weight: 700; }}
  p {{ margin: 0 0 7.2pt; color: #111; }}
  strong {{ font-weight: 700; }}
  code {{ font-family: "Courier New", Courier, monospace; font-size: 8.6pt; color: #111; background: transparent; padding: 0; }}
  pre {{ break-inside: avoid; margin: 8pt 0 10pt; padding: 7pt 9pt; border: 0.6pt solid #d8d8d8; background: #fff; white-space: pre-wrap; }}
  pre code {{ background: transparent; padding: 0; font-size: 8.15pt; line-height: 1.35; }}
  ul, ol {{ margin: 0 0 8pt 18pt; padding: 0; }}
  li {{ margin: 0 0 3.2pt; }}
  table {{ width: 100%; border-collapse: collapse; margin: 8pt 0 12pt; break-inside: avoid; font-size: 8.7pt; font-variant-numeric: tabular-nums; }}
  th {{ font-weight: 700; text-align: left; border-bottom: 0.8pt solid #333; padding: 0 5pt 4pt 0; }}
  td {{ border-bottom: 0.5pt solid #d7d7d7; padding: 4.5pt 5pt 4.5pt 0; vertical-align: top; }}
  figure {{ margin: 10pt 0 13pt; break-inside: avoid; page-break-inside: avoid; text-align: center; }}
  figure img {{ max-width: 100%; display: block; margin: 0 auto; border: 0; }}
  .operator-figure {{ margin: 11pt 0 14pt; }}
  .operator-figure img {{ width: 100%; }}
  .data-figure img {{ max-height: 3.35in; object-fit: contain; }}
  figcaption {{ font-size: 8.2pt; color: #333; margin-top: 4pt; text-align: left; }}
  a {{ color: #111; text-decoration: none; }}
  @media print {{ html, body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }} }}
</style>
</head>
<body><main>{body}</main></body>
</html>
"""
    HTML_PATH.write_text(html_doc, encoding="utf-8")
    print(f"wrote {HTML_PATH}")


if __name__ == "__main__":
    main()
