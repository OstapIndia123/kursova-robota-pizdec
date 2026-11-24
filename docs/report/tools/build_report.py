#!/usr/bin/env python3
"""Build editable DOCX and paginated PDF from coursework.md without network access."""
from __future__ import annotations

import math
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageFont
from PIL import ImageDraw
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parents[1]
SOURCE = REPORT / "coursework.md"
OUT_DOCX = REPORT / "coursework.docx"
FONT_REG = font_manager.findfont("Liberation Serif")


@dataclass
class Block:
    kind: str
    text: str = ""
    rows: list[list[str]] = field(default_factory=list)
    image: Path | None = None
    level: int = 0


@dataclass
class Page:
    blocks: list[Block]
    section: str
    kind: str = "normal"


def latex_plain(text: str) -> str:
    text = text.replace(r"\cdot", "·").replace(r"\times", "×")
    text = text.replace(r"\pi", "π").replace(r"\sqrt", "√")
    text = text.replace(r"\overrightarrow", "")
    text = text.replace(r"\|", "||")
    for spacing in (r"\qquad", r"\quad", r"\,", r"\;", r"\!"):
        text = text.replace(spacing, " ")
    text = text.replace(r"\left", "").replace(r"\right", "")
    text = text.replace(r"\le", "≤").replace(r"\ge", "≥")
    text = text.replace(r"\neq", "≠").replace(r"\infty", "∞")
    text = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", text)
    text = re.sub(r"\\sqrt\{([^{}]+)\}", r"√(\1)", text)
    text = re.sub(r"\\text\{([^{}]+)\}", r"\1", text)
    text = text.replace(r"\{", "{").replace(r"\}", "}")
    return text.replace("{", "").replace("}", "")


def plain(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = text.replace("**", "").replace("__", "")
    text = text.replace("`", "").replace("*", "")
    text = text.replace(r"\(", "").replace(r"\)", "")
    text = text.replace(r"\[", "").replace(r"\]", "")
    return latex_plain(text.strip())


def parse_source() -> list[Page]:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    pages: list[Page] = []
    blocks: list[Block] = []
    section = "unframed"
    pending_section: str | None = None
    kind = "normal"
    i = 0

    def finish_page() -> None:
        nonlocal blocks, kind
        if blocks:
            pages.append(Page(blocks, section, kind))
        blocks = []
        kind = "normal"

    while i < len(lines):
        line = lines[i]
        if line.startswith("<!-- PAGE:"):
            kind = line.split(":", 1)[1].split("-->")[0].strip()
            i += 1
            continue
        if line.startswith("<!-- SECTION:"):
            if "appendix" in line:
                pending_section = "appendix"
            elif "framed" in line:
                pending_section = "framed"
            i += 1
            continue
        if line.strip() == "<!-- NEXT_PAGE -->":
            finish_page()
            if pending_section:
                section = pending_section
                pending_section = None
            i += 1
            continue
        if line.startswith("<!--") or not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            language = line[3:].strip()
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            blocks.append(Block("code", "\n".join(code), level=1 if language else 0))
            i += 1
            continue
        if line.startswith("|"):
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[-: ]+", c or "-") for c in cells):
                    rows.append(cells)
                i += 1
            blocks.append(Block("table", rows=rows))
            continue
        image_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if image_match:
            image_path = (REPORT / image_match.group(2)).resolve()
            if image_path.suffix.lower() == ".svg" and "PLACEHOLDER" in image_path.name:
                image_path = image_path.with_suffix(".png")
                make_screenshot_placeholder(image_path)
            caption = ""
            if i + 1 < len(lines) and lines[i + 1].startswith("**Рисунок"):
                caption = plain(lines[i + 1].strip("* "))
                i += 1
            blocks.append(Block("image", caption, image=image_path))
            i += 1
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            blocks.append(Block("heading", plain(line[level:].strip()), level=level))
            i += 1
            continue
        if line.startswith(r"\["):
            math_lines = []
            while i < len(lines) and not lines[i].startswith(r"\]"):
                math_lines.append(lines[i])
                i += 1
            blocks.append(Block("equation", plain(" ".join(math_lines))))
            i += 1
            continue
        is_ordered_list = bool(re.match(r"^\s*\d+\.\s", line)) and not re.search(r"\.{3,}", line)
        if line.startswith("- ") or is_ordered_list:
            blocks.append(Block("list", plain(line)))
            i += 1
            continue
        para = [line.strip()]
        hard_break = line.endswith("  ")
        i += 1
        while i < len(lines):
            nxt = lines[i]
            is_next_ordered_list = bool(re.match(r"^\s*\d+\.\s", nxt)) and not re.search(r"\.{3,}", nxt)
            if (hard_break or not nxt.strip() or nxt.startswith(("#", "```", "|", "<!--", "![", "- "))
                    or is_next_ordered_list or nxt.startswith(r"\[")):
                break
            para.append(nxt.strip())
            hard_break = nxt.endswith("  ")
            i += 1
        blocks.append(Block("paragraph", plain(" ".join(para))))
    finish_page()
    return pages


def make_screenshot_placeholder(path: Path) -> None:
    """Rasterize a clearly labeled non-screenshot card for document placement."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1200, 675), "#f8fafc")
    draw = ImageDraw.Draw(image)
    draw.rectangle((4, 4, 1196, 671), outline="#475569", width=5)
    font = ImageFont.truetype(FONT_REG, 36)
    small = ImageFont.truetype(FONT_REG, 25)
    for text, y, f in (("ЗАМІНИТИ РЕАЛЬНИМ СКРИНШОТОМ", 280, font),
                       ("ЦЕЙ ЗАПОВНЮВАЧ НЕ Є ДОКАЗОМ ЗАПУСКУ", 350, small)):
        box = draw.textbbox((0, 0), text, font=f)
        draw.text(((1200 - (box[2] - box[0])) / 2, y), text, fill="#0f172a", font=f)
    image.save(path)


def xml_el(parent: ET.Element, tag: str, attrs: dict[str, str] | None = None,
           text: str | None = None) -> ET.Element:
    node = ET.SubElement(parent, tag, attrs or {})
    if text is not None:
        node.text = text
    return node


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
ET.register_namespace("w", W)
ET.register_namespace("r", R)
ET.register_namespace("wp", WP)
ET.register_namespace("a", A)
ET.register_namespace("pic", PIC)


def wtag(name: str) -> str:
    return f"{{{W}}}{name}"


def package_xml(root: ET.Element, namespace: str) -> bytes:
    """Serialize an OPC package part with its required namespace as the default."""
    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    prefix = b"ns0:"
    data = data.replace(b"<" + prefix, b"<").replace(b"</" + prefix, b"</")
    declaration = f'xmlns:ns0="{namespace}"'.encode()
    data = data.replace(declaration, f'xmlns="{namespace}"'.encode())
    return data


def add_run(p: ET.Element, text: str, *, bold: bool = False,
            font: str = "Times New Roman", size: int = 28, italic: bool = False) -> None:
    run = xml_el(p, wtag("r"))
    rpr = xml_el(run, wtag("rPr"))
    xml_el(rpr, wtag("rFonts"), {wtag("ascii"): font, wtag("hAnsi"): font, wtag("cs"): font})
    if bold:
        xml_el(rpr, wtag("b"))
    if italic:
        xml_el(rpr, wtag("i"))
    xml_el(rpr, wtag("sz"), {wtag("val"): str(size)})
    xml_el(rpr, wtag("szCs"), {wtag("val"): str(size)})
    t = xml_el(run, wtag("t"), text=text)
    if text.startswith(" ") or text.endswith(" "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def add_paragraph(parent: ET.Element, text: str = "", *, style: str = "Normal",
                  align: str | None = None, first_line: bool = True,
                  before: int = 0, after: int = 100, line: int = 420,
                  bold: bool = False, size: int = 28, font: str = "Times New Roman") -> ET.Element:
    p = xml_el(parent, wtag("p"))
    ppr = xml_el(p, wtag("pPr"))
    if style != "Normal":
        xml_el(ppr, wtag("pStyle"), {wtag("val"): style})
    if align:
        xml_el(ppr, wtag("jc"), {wtag("val"): align})
    ind = {wtag("firstLine"): "567"} if first_line else {}
    if ind:
        xml_el(ppr, wtag("ind"), ind)
    xml_el(ppr, wtag("spacing"), {wtag("before"): str(before), wtag("after"): str(after),
                                    wtag("line"): str(line), wtag("lineRule"): "auto"})
    if text:
        add_run(p, text, bold=bold, font=font, size=size)
    return p


def add_toc_field(parent: ET.Element) -> None:
    p = add_paragraph(parent, first_line=False, after=0, line=240, size=22)
    field = xml_el(p, wtag("fldSimple"),
                   {wtag("instr"): ' TOC \\o "1-2" \\h \\z \\u '})
    add_run(field, "Оновіть поле змісту в редакторі документів.", size=22)


def add_image(parent: ET.Element, image: Path, rel_id: str, caption: str = "") -> None:
    figure = xml_el(parent, wtag("tbl"))
    tblpr = xml_el(figure, wtag("tblPr"))
    xml_el(tblpr, wtag("tblW"), {wtag("w"): "0", wtag("type"): "auto"})
    borders = xml_el(tblpr, wtag("tblBorders"))
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        xml_el(borders, wtag(edge), {wtag("val"): "nil"})
    row = xml_el(figure, wtag("tr"))
    xml_el(xml_el(row, wtag("trPr")), wtag("cantSplit"))
    cell = xml_el(row, wtag("tc"))
    xml_el(xml_el(cell, wtag("tcPr")), wtag("tcW"), {wtag("w"): "9000", wtag("type"): "dxa"})
    p = xml_el(cell, wtag("p"))
    ppr = xml_el(p, wtag("pPr"))
    xml_el(ppr, wtag("jc"), {wtag("val"): "center"})
    run = xml_el(p, wtag("r"))
    drawing = xml_el(run, wtag("drawing"))
    inline = xml_el(drawing, f"{{{WP}}}inline", {"distT": "0", "distB": "0", "distL": "0", "distR": "0"})
    with Image.open(image) as im:
        width_px, height_px = im.size
    width_in = 6.0
    if image.name == "class-diagram.png":
        width_in = 4.8
    elif image.name == "sequence-diagram.png":
        width_in = 4.9
    elif image.name == "use-case.png":
        width_in = 4.8
    elif image.name.startswith("processing-flowchart"):
        width_in = 5.2
    elif "PLACEHOLDER" in image.name:
        width_in = 4.5
    cx = round(width_in * 914400)
    cy = round(cx * height_px / width_px)
    xml_el(inline, f"{{{WP}}}extent", {"cx": str(cx), "cy": str(cy)})
    xml_el(inline, f"{{{WP}}}docPr", {"id": "1", "name": image.name})
    graphic = xml_el(inline, f"{{{A}}}graphic")
    gd = xml_el(graphic, f"{{{A}}}graphicData", {"uri": PIC})
    pic = xml_el(gd, f"{{{PIC}}}pic")
    nv = xml_el(pic, f"{{{PIC}}}nvPicPr")
    xml_el(nv, f"{{{PIC}}}cNvPr", {"id": "0", "name": image.name})
    xml_el(nv, f"{{{PIC}}}cNvPicPr")
    blip_fill = xml_el(pic, f"{{{PIC}}}blipFill")
    xml_el(blip_fill, f"{{{A}}}blip", {f"{{{R}}}embed": rel_id})
    stretch = xml_el(blip_fill, f"{{{A}}}stretch")
    xml_el(stretch, f"{{{A}}}fillRect")
    sp = xml_el(pic, f"{{{PIC}}}spPr")
    xfrm = xml_el(sp, f"{{{A}}}xfrm")
    xml_el(xfrm, f"{{{A}}}off", {"x": "0", "y": "0"})
    xml_el(xfrm, f"{{{A}}}ext", {"cx": str(cx), "cy": str(cy)})
    geom = xml_el(sp, f"{{{A}}}prstGeom", {"prst": "rect"})
    xml_el(geom, f"{{{A}}}avLst")
    if caption:
        break_run = xml_el(p, wtag("r"))
        xml_el(break_run, wtag("br"))
        add_run(p, caption, size=24)
    xml_el(cell, wtag("p"))


def build_docx(pages: list[Page]) -> None:
    doc = ET.Element(wtag("document"))
    body = xml_el(doc, wtag("body"))
    image_rels: dict[Path, str] = {}
    for page in pages:
        for block in page.blocks:
            if block.kind == "image" and block.image and block.image.exists():
                image_rels.setdefault(block.image, f"rIdImg{len(image_rels)+1}")
    rels = ET.Element("{http://schemas.openxmlformats.org/package/2006/relationships}Relationships")
    pkg_rel = "http://schemas.openxmlformats.org/package/2006/relationships"
    xml_el(rels, f"{{{pkg_rel}}}Relationship", {"Id": "rIdStyles", "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles", "Target": "styles.xml"})
    for path, rid in image_rels.items():
        xml_el(rels, f"{{{pkg_rel}}}Relationship", {"Id": rid, "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image", "Target": f"media/{path.stem}.png"})
    content_types = ET.Element("{http://schemas.openxmlformats.org/package/2006/content-types}Types")
    ct = "http://schemas.openxmlformats.org/package/2006/content-types"
    xml_el(content_types, f"{{{ct}}}Default", {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
    xml_el(content_types, f"{{{ct}}}Default", {"Extension": "xml", "ContentType": "application/xml"})
    xml_el(content_types, f"{{{ct}}}Default", {"Extension": "png", "ContentType": "image/png"})
    xml_el(content_types, f"{{{ct}}}Override", {"PartName": "/word/document.xml", "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"})
    xml_el(content_types, f"{{{ct}}}Override", {"PartName": "/word/styles.xml", "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"})
    xml_el(content_types, f"{{{ct}}}Override", {"PartName": "/word/settings.xml", "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"})
    framed_page = 0
    toc_scope = False
    for page_no, page in enumerate(pages, 1):
        h = next((b.text for b in page.blocks if b.kind == "heading"), "")
        if h.startswith("1 "):
            toc_scope = True
        if page.section == "framed":
            framed_page += 1
        for b in page.blocks:
            if b.kind == "heading":
                if b.text == "ЗМІСТ":
                    toc_scope = False
                heading_style = ("Heading1" if b.level == 1 else "Heading2") if toc_scope else "Normal"
                p = add_paragraph(body, b.text.upper() if b.level == 1 else b.text,
                                  style=heading_style,
                                  align="center" if b.level == 1 else "left",
                                  first_line=False, before=0, after=0, bold=True, size=28)
            elif b.kind in ("paragraph", "list", "equation"):
                text = b.text
                if b.kind == "list":
                    text = "• " + text.lstrip("- ")
                body_size = 24 if page.kind == "abstracts" else 28
                body_line = 300 if page.kind == "abstracts" else 420
                add_paragraph(body, text, align="center" if b.kind == "equation" else "both",
                              first_line=b.kind == "paragraph", after=0,
                              line=body_line, size=body_size)
            elif b.kind == "code":
                for line in b.text.splitlines():
                    add_paragraph(body, line, first_line=False, after=0, line=240,
                                  size=19, font="Liberation Mono")
            elif b.kind == "table":
                if h == "ЗМІСТ":
                    add_toc_field(body)
                    continue
                tbl = xml_el(body, wtag("tbl"))
                tblpr = xml_el(tbl, wtag("tblPr"))
                xml_el(tblpr, wtag("tblW"), {wtag("w"): "0", wtag("type"): "auto"})
                borders = xml_el(tblpr, wtag("tblBorders"))
                for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
                    xml_el(borders, wtag(edge), {wtag("val"): "single", wtag("sz"): "4", wtag("color"): "808080"})
                for ri, row in enumerate(b.rows):
                    tr = xml_el(tbl, wtag("tr"))
                    for val in row:
                        tc = xml_el(tr, wtag("tc"))
                        p = add_paragraph(tc, plain(val), first_line=False, after=30, line=250,
                                          bold=ri == 0, size=22)
            elif b.kind == "image" and b.image and b.image.exists():
                add_image(body, b.image, image_rels[b.image], b.text)
        break_p = xml_el(body, wtag("p"))
        ppr = xml_el(break_p, wtag("pPr"))
        sect = xml_el(ppr, wtag("sectPr"))
        footer_id = f"rIdFooter{page_no}"
        footer_path = f"word/footer{page_no}.xml"
        xml_el(sect, wtag("footerReference"), {wtag("type"): "default", f"{{{R}}}id": footer_id})
        xml_el(sect, wtag("type"), {wtag("val"): "nextPage"})
        xml_el(sect, wtag("pgSz"), {wtag("w"): "11906", wtag("h"): "16838"})
        xml_el(sect, wtag("pgMar"), {wtag("top"): "1134", wtag("right"): "850", wtag("bottom"): "1417", wtag("left"): "1417", wtag("header"): "360", wtag("footer"): "360", wtag("gutter"): "0"})
        if page.section == "framed":
            borders = xml_el(sect, wtag("pgBorders"), {wtag("offsetFrom"): "page"})
            for edge, space in (("top", "14"), ("left", "57"), ("bottom", "14"), ("right", "14")):
                xml_el(borders, wtag(edge), {wtag("val"): "single", wtag("sz"): "8", wtag("space"): space, wtag("color"): "000000"})
        xml_el(content_types, f"{{{ct}}}Override", {"PartName": f"/{footer_path}", "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"})
        f_rel = xml_el(rels, f"{{{pkg_rel}}}Relationship", {"Id": footer_id, "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer", "Target": f"footer{page_no}.xml"})
        froot = ET.Element(wtag("ftr"))
        if page.section == "framed":
            tbl = xml_el(froot, wtag("tbl"))
            tblpr = xml_el(tbl, wtag("tblPr"))
            xml_el(tblpr, wtag("tblW"), {wtag("w"): "10488", wtag("type"): "dxa"})
            xml_el(tblpr, wtag("tblInd"), {wtag("w"): "-283", wtag("type"): "dxa"})
            borders = xml_el(tblpr, wtag("tblBorders"))
            for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
                xml_el(borders, wtag(edge), {wtag("val"): "single", wtag("sz"): "6", wtag("color"): "000000"})
            grid = xml_el(tbl, wtag("tblGrid"))
            xml_el(grid, wtag("gridCol"), {wtag("w"): "7650"})
            xml_el(grid, wtag("gridCol"), {wtag("w"): "2838"})
            for row_idx in range(2):
                row = xml_el(tbl, wtag("tr"))
                trpr = xml_el(row, wtag("trPr"))
                xml_el(trpr, wtag("trHeight"), {wtag("val"): "850" if row_idx == 0 else "2268", wtag("hRule"): "exact"})
                for col_idx, width in enumerate(("7650", "2838")):
                    cell = xml_el(row, wtag("tc"))
                    tcpr = xml_el(cell, wtag("tcPr"))
                    xml_el(tcpr, wtag("tcW"), {wtag("w"): width, wtag("type"): "dxa"})
                    if row_idx == 0 and col_idx == 0:
                        add_paragraph(cell, "Розрахунок відношення об’єму фігури до її площі: конус, тетраедр, циліндр", first_line=False, after=30, line=210, size=16)
                        add_paragraph(cell, "Позначення документа: [КР.КІ–[№].00.000.ПЗ]", first_line=False, after=0, line=210, size=16)
                    elif row_idx == 0:
                        add_paragraph(cell, f"Літера Н · {'Г1' if framed_page == 1 else 'Г2'}", first_line=False, align="center", after=30, line=210, size=16)
                        sheet = add_paragraph(cell, align="center", first_line=False, after=0, line=210, size=16)
                        add_run(sheet, "Аркуш ", size=16)
                        page_field = xml_el(sheet, wtag("fldSimple"), {wtag("instr"): " PAGE "})
                        add_run(page_field, str(page_no), size=16)
                        add_run(sheet, " / ", size=16)
                        count_field = xml_el(sheet, wtag("fldSimple"), {wtag("instr"): " NUMPAGES "})
                        add_run(count_field, str(len(pages)), size=16)
                    elif col_idx == 0:
                        add_paragraph(cell, "Розробив: [ПІБ]     Перевірив: [керівник]", first_line=False, after=70, line=210, size=16)
                        add_paragraph(cell, "Н. контр.: [заповнити]     Затвердив: [заповнити]", first_line=False, after=70, line=210, size=16)
                        add_paragraph(cell, "ІФНТУНГ · [група] · [ПІБ студента]", first_line=False, after=0, line=210, size=16)
                    else:
                        add_paragraph(cell, "Підписи й дати: [заповнюють відповідальні особи]", first_line=False, after=0, line=210, size=16)
        elif page.section == "framed":
            p = xml_el(froot, wtag("p"))
            xml_el(xml_el(p, wtag("pPr")), wtag("jc"), {wtag("val"): "center"})
            add_run(p, str(page_no), size=20)
        else:
            xml_el(froot, wtag("p"))
        footer_xml = ET.tostring(froot, encoding="utf-8", xml_declaration=True)
        page._footer_xml = footer_xml  # type: ignore[attr-defined]
    last_break_p = body[-1]
    last_sect = last_break_p.find(f"./{wtag('pPr')}/{wtag('sectPr')}")
    if last_sect is not None:
        last_break_p.remove(last_break_p.find(wtag("pPr")))
        body.remove(last_break_p)
        body.append(last_sect)
    styles = ET.Element(wtag("styles"))
    normal = xml_el(styles, wtag("style"), {wtag("type"): "paragraph", wtag("default"): "1", wtag("styleId"): "Normal"})
    nrpr = xml_el(normal, wtag("rPr")); xml_el(nrpr, wtag("rFonts"), {wtag("ascii"): "Times New Roman", wtag("hAnsi"): "Times New Roman"}); xml_el(nrpr, wtag("sz"), {wtag("val"): "28"})
    for sid, name, outline in (("Heading1", "heading 1", "0"), ("Heading2", "heading 2", "1")):
        st = xml_el(styles, wtag("style"), {wtag("type"): "paragraph", wtag("styleId"): sid})
        xml_el(st, wtag("name"), {wtag("val"): name})
        xml_el(st, wtag("basedOn"), {wtag("val"): "Normal"})
        xml_el(st, wtag("qFormat"))
        pr = xml_el(st, wtag("pPr")); xml_el(pr, wtag("keepNext"))
        xml_el(pr, wtag("outlineLvl"), {wtag("val"): outline})
        rr = xml_el(st, wtag("rPr")); xml_el(rr, wtag("rFonts"), {wtag("ascii"): "Times New Roman", wtag("hAnsi"): "Times New Roman"}); xml_el(rr, wtag("b")); xml_el(rr, wtag("sz"), {wtag("val"): "28"})
    rootrels = ET.Element("{http://schemas.openxmlformats.org/package/2006/relationships}Relationships")
    xml_el(rootrels, f"{{{pkg_rel}}}Relationship", {"Id": "rId1", "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument", "Target": "word/document.xml"})
    xml_el(rels, f"{{{pkg_rel}}}Relationship", {"Id": "rIdSettings", "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings", "Target": "settings.xml"})
    settings = ET.Element(wtag("settings"))
    xml_el(settings, wtag("updateFields"), {wtag("val"): "true"})
    OUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT_DOCX, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", package_xml(content_types, ct))
        zf.writestr("_rels/.rels", package_xml(rootrels, pkg_rel))
        zf.writestr("word/document.xml", ET.tostring(doc, encoding="utf-8", xml_declaration=True))
        zf.writestr("word/styles.xml", ET.tostring(styles, encoding="utf-8", xml_declaration=True))
        zf.writestr("word/settings.xml", ET.tostring(settings, encoding="utf-8", xml_declaration=True))
        zf.writestr("word/_rels/document.xml.rels", package_xml(rels, pkg_rel))
        for page_no, page in enumerate(pages, 1):
            zf.writestr(f"word/footer{page_no}.xml", page._footer_xml)  # type: ignore[attr-defined]
        for path in image_rels:
            zf.write(path, f"word/media/{path.stem}.png")


def main() -> int:
    source_dir = REPORT / "diagrams" / "source"
    rendered_dir = REPORT / "diagrams" / "rendered"
    rendered_dir.mkdir(parents=True, exist_ok=True)
    for dot_source in source_dir.glob("*.dot"):
        if dot_source.stem == "sequence-diagram":
            continue
        for fmt in ("png", "svg"):
            subprocess.run(["dot", f"-T{fmt}", str(dot_source), "-o",
                            str(rendered_dir / f"{dot_source.stem}.{fmt}")], check=True)
    subprocess.run([sys.executable, str(source_dir / "render_sequence.py")], check=True)
    pages = parse_source()
    build_docx(pages)
    print(f"DOCX source sections: {len(pages)}")
    subprocess.run([sys.executable, str(REPORT / "tools" / "finalize_docx.py")], check=True)
    print(f"DOCX: {OUT_DOCX}")
    print(f"PDF exported from DOCX: {REPORT / 'coursework.pdf'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
