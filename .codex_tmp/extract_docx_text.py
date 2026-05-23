from pathlib import Path

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


DOCS = [
    ("ch3", Path(r"C:\Users\Clark\Desktop\毕业设计\新第3章草稿_3.4.3表题已处理.docx")),
    ("ch4", Path(r"C:\Users\Clark\Desktop\毕业设计\新第4章草稿_表述修改版.docx")),
    ("ch5", Path(r"C:\Users\Clark\Desktop\毕业设计\新第5章草稿.docx")),
]


def iter_blocks(document):
    body = document.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def table_text(table):
    rows = []
    for row in table.rows:
        cells = [" ".join(cell.text.split()) for cell in row.cells]
        rows.append(" | ".join(cells))
    return "\n".join(rows)


def main():
    outdir = Path(".codex_tmp/doc_review")
    outdir.mkdir(parents=True, exist_ok=True)

    for label, path in DOCS:
        document = Document(path)
        lines = []
        for block in iter_blocks(document):
            if isinstance(block, Paragraph):
                text = " ".join(block.text.split())
                if text:
                    style = block.style.name if block.style is not None else ""
                    lines.append(f"[P:{style}] {text}")
            else:
                text = table_text(block)
                if text:
                    lines.append(f"[TABLE]\n{text}")

        (outdir / f"{label}.txt").write_text("\n\n".join(lines), encoding="utf-8")
        print(f"{label}: {len(lines)} blocks -> {outdir / (label + '.txt')}")


if __name__ == "__main__":
    main()
