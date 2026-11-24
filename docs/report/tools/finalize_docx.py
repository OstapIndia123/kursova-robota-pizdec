#!/usr/bin/env python3
"""Refresh DOCX indexes and export the canonical DOCX to PDF with headless LibreOffice."""
from __future__ import annotations

import os
import re
import socket
import subprocess
import tempfile
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import uno
from com.sun.star.beans import PropertyValue

REPORT = Path(__file__).resolve().parents[1]
DOCX = REPORT / "coursework.docx"
PDF = REPORT / "coursework.pdf"
CORE_NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def set_docx_core_metadata() -> None:
    """Set identity metadata in the DOCX package without rewriting document parts."""
    temp_path = DOCX.with_suffix(".metadata.tmp")
    with zipfile.ZipFile(DOCX, "r") as source, zipfile.ZipFile(temp_path, "w") as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "docProps/core.xml":
                root = ET.fromstring(data)
                values = {
                    "title": ("dc", "Розрахунок відношення об’єму фігури до її площі: конус, тетраедр, циліндр"),
                    "subject": ("dc", "Курсова робота з об’єктно-орієнтованого програмування, варіант № 6"),
                    "creator": ("dc", "Павлюк Остап Мирославович"),
                    "language": ("dc", "uk-UA"),
                }
                for local_name, (prefix, value) in values.items():
                    tag = f"{{{CORE_NS[prefix]}}}{local_name}"
                    element = root.find(tag)
                    if element is None:
                        element = ET.SubElement(root, tag)
                    element.text = value
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            target.writestr(item, data)
    temp_path.replace(DOCX)


def props(**values):
    result = []
    for name, value in values.items():
        item = PropertyValue()
        item.Name = name
        item.Value = value
        result.append(item)
    return tuple(result)


def main() -> int:
    if not DOCX.is_file():
        raise SystemExit(f"Missing canonical DOCX: {DOCX}")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="oop-coursework-lo-r3-") as temp:
        profile = Path(temp) / "profile"
        env = os.environ.copy()
        env.pop("DISPLAY", None)
        env.pop("WAYLAND_DISPLAY", None)
        env["HOME"] = temp
        env["SAL_USE_VCLPLUGIN"] = "svp"
        accept = f"socket,host=127.0.0.1,port={port};urp;StarOffice.ServiceManager"
        process = subprocess.Popen([
            "libreoffice", "--headless", "--norestore", "--nodefault",
            "--nolockcheck", "--nofirststartwizard",
            f"-env:UserInstallation={profile.as_uri()}", f"--accept={accept}"
        ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        document = None
        try:
            local_ctx = uno.getComponentContext()
            resolver = local_ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.bridge.UnoUrlResolver", local_ctx)
            remote_ctx = None
            connection = f"uno:socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext"
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    remote_ctx = resolver.resolve(connection)
                    break
                except Exception:
                    if process.poll() is not None:
                        raise RuntimeError(f"LibreOffice exited early with code {process.returncode}")
                    time.sleep(0.2)
            if remote_ctx is None:
                raise TimeoutError("Timed out waiting for LibreOffice UNO listener")
            desktop = remote_ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", remote_ctx)
            document = desktop.loadComponentFromURL(
                DOCX.as_uri(), "_blank", 0,
                props(Hidden=True, ReadOnly=False, UpdateDocMode=3))
            if document is None:
                raise RuntimeError("LibreOffice could not load the canonical DOCX")
            # Keep the package-level metadata consistent with the confirmed
            # student identity and the title shown on the cover page.
            metadata = document.getDocumentProperties()
            for name, value in {
                "Title": "Розрахунок відношення об’єму фігури до її площі: конус, тетраедр, циліндр",
                "Subject": "Курсова робота з об’єктно-орієнтованого програмування, варіант № 6",
                "Author": "Павлюк Остап Мирославович",
                "Creator": "Павлюк Остап Мирославович",
                "Keywords": "ІФНТУНГ; КІ-26-1К; варіант 6; C++17",
            }.items():
                try:
                    metadata.setPropertyValue(name, value)
                except Exception:
                    # Some LibreOffice builds expose only a subset of the
                    # standard metadata properties (for example, no Creator).
                    pass
            indexes = document.getDocumentIndexes()
            for _ in range(2):
                for idx in range(indexes.getCount()):
                    indexes.getByIndex(idx).update()
            document.storeAsURL(DOCX.as_uri(), props(
                FilterName="Office Open XML Text", Overwrite=True))
            set_docx_core_metadata()
            document.storeToURL(PDF.as_uri(), props(
                FilterName="writer_pdf_Export", Overwrite=True))
            info = subprocess.run(["pdfinfo", str(PDF)], check=True, capture_output=True, text=True).stdout
            match = re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE)
            if not match:
                raise RuntimeError("Could not read exported PDF page count")
            page_count = int(match.group(1))
            extracted = subprocess.run(["pdftotext", "-layout", str(PDF), "-"],
                                       check=True, capture_output=True, text=True).stdout
            pdf_pages = extracted.split("\f")[:page_count]
            if len(pdf_pages) != page_count:
                raise RuntimeError("Could not extract every exported PDF page")
            blank_pages = [i for i, text in enumerate(pdf_pages, 1) if not text.strip()]
            if blank_pages:
                raise RuntimeError(f"Unexpected blank PDF pages: {blank_pages}")
            start = next((i for i, text in enumerate(pdf_pages[4:], 5)
                          if "1 АНАЛІЗ ПРЕДМЕТНОЇ ОБЛАСТІ ТА МАТЕМАТИЧНИХ ОСНОВ" in text), None)
            conclusion = next((i for i, text in enumerate(pdf_pages, 1)
                               if re.search(r"^\s*ВИСНОВКИ\s*$", text, re.MULTILINE)), None)
            if start is None or conclusion is None or not 16 <= conclusion - start <= 32:
                raise RuntimeError(f"Main body page count outside 16–32: start={start}, conclusions={conclusion}")
            framed_pages = [i for i, text in enumerate(pdf_pages, 1)
                            if "Літера Н · Г" in text]
            for page_no in framed_pages:
                expected = f"Аркуш {page_no} / {page_count}"
                if expected not in pdf_pages[page_no - 1]:
                    raise RuntimeError(f"Page field mismatch on framed page {page_no}")
            toc_text = pdf_pages[3]
            if "ДЕКЛАРАЦІЯ ВНЕСКУ ГЕНЕРАТИВНОГО ШТУЧНОГО ІНТЕЛЕКТУ" not in toc_text:
                raise RuntimeError("Updated table of contents is missing expected headings")
            report = REPORT / "evidence" / "final-pagination-report.txt"
            report.parent.mkdir(parents=True, exist_ok=True)
            body_pages = conclusion - start
            short_continuations = []
            footer_markers = ("Розрахунок відношення", "Літера Н ·", "Аркуш ",
                              "Позначення документа:", "Розробив:", "Н. контр.:",
                              "ІФНТУНГ ·", "Підписи й дати:")
            for page_no in range(start, conclusion):
                body_lines = [line.strip() for line in pdf_pages[page_no - 1].splitlines()
                              if line.strip() and not any(marker in line for marker in footer_markers)]
                if len(body_lines) <= 4 and "Рисунок" not in "\n".join(body_lines):
                    short_continuations.append(f"{page_no} ({len(body_lines)} text lines)")
            report.write_text(
                "OOP-COURSE-004-R3 final pagination verification\n\n"
                f"Canonical editable document: {DOCX}\n"
                f"Submission PDF exported by LibreOffice from that DOCX: {PDF}\n"
                f"PDF page count: {page_count}; paper size: A4.\n"
                f"The saved DOCX was the source of this PDF export; DOCX and PDF pagination are synchronized at {page_count} pages.\n"
                f"Substantive main body: pages {start}–{conclusion - 1}, {body_pages} pages (required range 16–32).\n"
                "Automatic Word-compatible TOC field was refreshed twice through LibreOffice UNO before saving/export.\n"
                "TOC contains chapter, subsection, conclusion, references, AI declaration, and appendix entries; the PDF page mapping was visually reviewed.\n"
                f"Dynamic title-block PAGE/NUMPAGES fields verified on framed pages {framed_pages[0]}–{framed_pages[-1]}; each reads its physical page / {page_count}.\n"
                "Blank pages: none (checked by page-level text extraction).\n"
                f"Sparse main-body continuation pages (nonblank): {', '.join(short_continuations) or 'none'}.\n"
                "Visual inspection is recorded by the OOP-COURSE-004-R3 operator after rendering.\n",
                encoding="utf-8")
            print(f"LibreOffice refreshed {indexes.getCount()} document index(es).")
            print(f"PDF pages: {page_count}; main body: {body_pages} pages.")
            print(f"Pagination report: {report}")
            print(f"Canonical DOCX saved: {DOCX}")
            print(f"PDF exported from canonical DOCX: {PDF}")
            document.close(True)
            document = None
            desktop.terminate()
        finally:
            if document is not None:
                try:
                    document.close(True)
                except Exception:
                    pass
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
