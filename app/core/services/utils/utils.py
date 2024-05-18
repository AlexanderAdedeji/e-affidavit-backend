import string
import random
from typing import Any, Dict, List
import qrcode
from io import BytesIO
from bson import ObjectId
from loguru import logger
from base64 import b64encode


def generate_document_name(length: int = 10) -> str:
    """Generate a random document name."""
    return ''.join(random.choices(string.ascii_uppercase, k=length))




def generate_qr_code_base64(url: str, version: int = 1, box_size: int = 10, border: int = 5) -> str:
    """Generate a QR code for a given URL and return it as a base64 encoded string."""
    qr = qrcode.QRCode(version=version, box_size=box_size, border=border)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    with BytesIO() as buffered:
        img.save(buffered)
        img_base64 = b64encode(buffered.getvalue()).decode('utf-8')
    return img_base64



def is_valid_objectid(objectid: str) -> bool:
    try:
        ObjectId(objectid)
        return True
    except (TypeError, ValueError):
        return False
    

def extract_preview_text_from_document(document: Dict[str, Any]) -> str:
    """
    Recursively extract text from children nodes within the given document.
    """
    text = ""
    children = []

    # Retrieve template data and find content area
    template_data = document.get("document_data", {}).get("template_data", [])
    content_area = next(
        (item for item in template_data if item.get("id") == "content-area"), None
    )

    if content_area:
        logger.info(f"Content Area found: {content_area}")
        children = content_area.get("children", [])
    else:
        logger.info("No content area found.")
        return ""

    def extract_preview_text_from_document(children: List[Dict[str, Any]]) -> str:
        nonlocal text
        for child in children:
            logger.info(f"Processing child: {child}")
            if "text" in child:
                text += child["text"]
            elif "type" in child and child["type"] == "field":
                # Use content if available, otherwise use label
                field_content = child.get("content", "").strip()
                text += field_content if field_content else child.get("label", "")
            elif "children" in child:
                # Recursively process nested children
                extract_preview_text_from_document(child["children"])
            # Limit to 100 characters
            if len(text) >= 100:
                text = text[:100]
                return text
        return text

    # Start the recursive extraction
    extract_preview_text_from_document(children)

    if not text:
        logger.info("No text extracted or content area not found.")

    logger.info(f"Final extracted text: {text}")
    return text