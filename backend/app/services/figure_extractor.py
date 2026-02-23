"""Figure & Table Extractor — extract images and tables from PDF using PyMuPDF."""

from __future__ import annotations

import base64
import logging
from pathlib import Path

import fitz

logger = logging.getLogger(__name__)

MIN_IMAGE_SIZE = 5000  # bytes — skip tiny icons/logos
MIN_DIMENSION = 80     # pixels — skip tiny decorations


def extract_figures(pdf_bytes: bytes, output_dir: str | None = None) -> list[dict]:
    """Extract figures/images from a PDF. Returns list of {index, page, width, height, ext, data_b64, path}."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    figures = []
    seen_digests = set()
    try:
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                if xref in seen_digests:
                    continue
                seen_digests.add(xref)
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.width < MIN_DIMENSION or pix.height < MIN_DIMENSION:
                        continue
                    # Convert CMYK to RGB
                    if pix.n > 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    img_bytes = pix.tobytes("png")
                    if len(img_bytes) < MIN_IMAGE_SIZE:
                        continue
                    entry = {
                        "index": len(figures),
                        "page": page_num + 1,
                        "width": pix.width,
                        "height": pix.height,
                        "ext": "png",
                        "data_b64": base64.b64encode(img_bytes).decode(),
                    }
                    if output_dir:
                        out = Path(output_dir)
                        out.mkdir(parents=True, exist_ok=True)
                        fname = f"fig_{len(figures):03d}_p{page_num+1}.png"
                        (out / fname).write_bytes(img_bytes)
                        entry["path"] = str(out / fname)
                    figures.append(entry)
                except Exception:
                    logger.debug("Skip image xref=%d on page %d", xref, page_num + 1)
    finally:
        page_count = doc.page_count
        doc.close()
    logger.info("Extracted %d figures from PDF (%d pages)", len(figures), page_count)
    return figures


def extract_tables_text(pdf_bytes: bytes) -> list[dict]:
    """Extract table-like text blocks from PDF using PyMuPDF layout analysis."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    tables = []
    try:
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            # Use find_tables if available (PyMuPDF >= 1.23.0)
            if hasattr(page, "find_tables"):
                try:
                    tab_finder = page.find_tables()
                    for i, tab in enumerate(tab_finder.tables):
                        rows = tab.extract()
                        if len(rows) >= 2:  # at least header + 1 data row
                            tables.append({
                                "index": len(tables),
                                "page": page_num + 1,
                                "headers": rows[0] if rows else [],
                                "rows": rows[1:],
                                "row_count": len(rows) - 1,
                                "col_count": len(rows[0]) if rows else 0,
                            })
                except Exception:
                    pass
    finally:
        doc.close()
    logger.info("Extracted %d tables from PDF", len(tables))
    return tables
