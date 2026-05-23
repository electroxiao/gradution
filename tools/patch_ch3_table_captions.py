from __future__ import annotations

import copy
import zipfile
from pathlib import Path

from lxml import etree


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
WQ = f"{{{W}}}"


SOURCE = Path(r"C:\Users\Clark\Desktop\毕业设计\新第3章草稿.docx")
OUTPUT = Path(r"C:\dev\gradution\新第3章草稿_3.4.3表题已处理.docx")


CAPTIONS = [
    "表3-1 用户表",
    "表3-2 聊天会话表",
    "表3-3 聊天消息表",
    "表3-4 问答知识点记录表",
    "表3-5 用户薄弱点表",
    "表3-6 用户知识状态表",
    "表3-7 作业表",
    "表3-8 作业题目表",
    "表3-9 作业测试用例表",
    "表3-10 作业分配表",
    "表3-11 作业提交表",
    "表3-12 题库表",
    "表3-13 知识点表",
    "表3-14 题目知识点绑定表",
]


def qn(local: str) -> str:
    return f"{WQ}{local}"


def paragraph_text(p: etree._Element) -> str:
    return "".join(p.xpath(".//w:t/text()", namespaces=NS)).strip()


def paragraph_style(p: etree._Element) -> str | None:
    styles = p.xpath("./w:pPr/w:pStyle/@w:val", namespaces=NS)
    return styles[0] if styles else None


def set_paragraph_text(p: etree._Element, text: str) -> None:
    runs = p.xpath("./w:r", namespaces=NS)
    first_run = runs[0] if runs else etree.SubElement(p, qn("r"))

    texts = first_run.xpath("./w:t", namespaces=NS)
    first_text = texts[0] if texts else etree.SubElement(first_run, qn("t"))
    first_text.text = text

    for t in p.xpath(".//w:t", namespaces=NS):
        if t is not first_text:
            t.text = ""


def caption_paragraph(template: etree._Element, text: str) -> etree._Element:
    p = copy.deepcopy(template)
    set_paragraph_text(p, text)
    return p


def set_before_half_line(p: etree._Element) -> None:
    ppr = p.find(qn("pPr"))
    if ppr is None:
        ppr = etree.Element(qn("pPr"))
        p.insert(0, ppr)

    spacing = ppr.find(qn("spacing"))
    if spacing is None:
        spacing = etree.SubElement(ppr, qn("spacing"))

    spacing.set(qn("beforeLines"), "50")
    spacing.attrib.pop(qn("before"), None)


def main() -> None:
    parser = etree.XMLParser(remove_blank_text=False)
    with zipfile.ZipFile(SOURCE, "r") as zin:
        doc_xml = zin.read("word/document.xml")
        root = etree.fromstring(doc_xml, parser)
        body = root.find("w:body", NS)
        if body is None:
            raise RuntimeError("Cannot find document body")

        children = list(body)

        start = None
        for idx, child in enumerate(children):
            if etree.QName(child).localname == "p" and paragraph_text(child).startswith("3.4.3"):
                start = idx
                break
        if start is None:
            raise RuntimeError("Cannot find section 3.4.3")

        end = len(children)
        for idx in range(start + 1, len(children)):
            child = children[idx]
            if etree.QName(child).localname == "p":
                style = paragraph_style(child)
                text = paragraph_text(child)
                if idx > start and style in {"3", "4"} and text.startswith("3."):
                    end = idx
                    break

        caption_template = None
        for idx in range(start + 1, end):
            child = children[idx]
            if etree.QName(child).localname == "p" and paragraph_style(child) == "12":
                caption_template = child
                break
        if caption_template is None:
            for child in children:
                if etree.QName(child).localname == "p" and paragraph_style(child) == "12":
                    caption_template = child
                    break
        if caption_template is None:
            raise RuntimeError("Cannot find a caption-style paragraph to copy")

        caption_idx = 0
        idx = start + 1
        while idx < len(body) and caption_idx < len(CAPTIONS):
            child = body[idx]
            if etree.QName(child).localname != "tbl":
                idx += 1
                continue

            caption_text = CAPTIONS[caption_idx]
            prev = body[idx - 1] if idx > 0 else None
            if (
                prev is not None
                and etree.QName(prev).localname == "p"
                and paragraph_style(prev) == "12"
                and paragraph_text(prev) in {"表", ""}
            ):
                set_paragraph_text(prev, caption_text)
            else:
                body.insert(idx, caption_paragraph(caption_template, caption_text))
                idx += 1

            following = body[idx + 1] if idx + 1 < len(body) else None
            if following is not None and etree.QName(following).localname == "p":
                set_before_half_line(following)

            caption_idx += 1
            idx += 1

        if caption_idx != len(CAPTIONS):
            raise RuntimeError(f"Expected {len(CAPTIONS)} tables, updated {caption_idx}")

        new_doc_xml = etree.tostring(
            root, xml_declaration=True, encoding="UTF-8", standalone=True
        )

        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = new_doc_xml if item.filename == "word/document.xml" else zin.read(item.filename)
                zout.writestr(item, data)

    print(OUTPUT)


if __name__ == "__main__":
    main()
