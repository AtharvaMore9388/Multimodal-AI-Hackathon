import io
import re
from typing import Any

FIGURE_CAPTION_PATTERN = re.compile(
    r"(?:Fig(?:ure)?|Diagram|Chart|Table|Graph)\s*\.?\s*\d*[:\.\-]?\s*([^\n]{4,180})",
    re.IGNORECASE,
)


def _try_pytesseract(img_bytes: bytes, lang: str = "eng") -> str:
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes))
        text = pytesseract.image_to_string(img, lang=lang)
        return text.strip()
    except Exception:
        return ""


def extract_figure_captions(page_text: str) -> list[str]:
    return [m.group(1).strip().rstrip(".") for m in FIGURE_CAPTION_PATTERN.finditer(page_text or "")]


def ocr_image_bytes(img_bytes: bytes, fallback_caption_hint: str = "") -> tuple[str, list[str]]:
    ocr_text = _try_pytesseract(img_bytes)
    keywords = []
    if ocr_text:
        words = re.findall(r"[A-Za-z0-9_]{3,}", ocr_text)
        keywords = sorted(set(w.lower() for w in words))[:20]
    elif fallback_caption_hint:
        words = re.findall(r"[A-Za-z0-9_]{3,}", fallback_caption_hint)
        keywords = sorted(set(w.lower() for w in words))[:20]
    return ocr_text, keywords


def scan_pdf_images(page_obj: Any, page_text: str) -> dict[str, Any]:
    figures = 0
    ocr_texts = []
    all_keywords: set[str] = set()
    try:
        images = getattr(page_obj, "images", []) or []
        for img_info in images:
            figures += 1
            raw = img_info.get("stream") or b""
            if raw:
                try:
                    if hasattr(raw, "get_data"):
                        data = raw.get_data()
                    else:
                        data = bytes(raw) if not isinstance(raw, (bytes, bytearray)) else raw
                except Exception:
                    data = b""
            else:
                data = b""
            hint = page_text[:500]
            t, kws = ocr_image_bytes(data, hint)
            if t:
                ocr_texts.append(t)
            all_keywords.update(kws)
    except Exception:
        pass
    captions = extract_figure_captions(page_text)
    for cap in captions:
        words = re.findall(r"[A-Za-z0-9_]{3,}", cap)
        all_keywords.update(w.lower() for w in words)
    return {
        "figures_count": figures + len(captions),
        "ocr_appended": "\n".join(ocr_texts + captions),
        "figure_keywords": ",".join(sorted(all_keywords))[:400] or None,
    }


def scan_pptx_picture(shape: Any, slide_text: str) -> dict[str, Any]:
    ocr_text = ""
    keywords: set[str] = set()
    try:
        shape_type = getattr(shape, "shape_type", None)
        is_picture = str(shape_type) == "13" or "PICTURE" in str(shape_type).upper()
        if is_picture:
            try:
                image_bytes = shape.image.blob
                t, kws = ocr_image_bytes(image_bytes, slide_text)
                ocr_text = t
                keywords.update(kws)
            except Exception:
                pass
    except Exception:
        pass
    captions = extract_figure_captions(slide_text)
    for cap in captions:
        words = re.findall(r"[A-Za-z0-9_]{3,}", cap)
        keywords.update(w.lower() for w in words)
    return {
        "figures_count": (1 if ocr_text or (str(getattr(shape, "shape_type", "")) == "13") else 0) + len(captions),
        "ocr_appended": ocr_text + ("\n" if ocr_text else "") + "\n".join(captions),
        "figure_keywords": ",".join(sorted(keywords))[:400] or None,
    }
