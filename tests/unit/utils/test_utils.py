# tests/unit/utils/test_utils.py

import base64
import re
from datetime import datetime

import pytest

from commonLib.utils.utils import (extract_preview_text_from_document,
                                   generate_document_name,
                                   generate_qr_code_base64, is_valid_objectid)

# -------------------------------
# Test for generate_document_name
# -------------------------------

def test_generate_document_name_default_length():
    """Test that the default generated document name has 10 uppercase letters."""
    name = generate_document_name()
    assert isinstance(name, str)
    assert len(name) == 10
    assert re.fullmatch(r"[A-Z]{10}", name), "Name should consist of 10 uppercase letters"

def test_generate_document_name_custom_length():
    """Test that generating a name with a custom length returns the correct length."""
    custom_length = 15
    name = generate_document_name(length=custom_length)
    assert isinstance(name, str)
    assert len(name) == custom_length
    assert re.fullmatch(r"[A-Z]{" + str(custom_length) + r"}", name), "Name should consist of uppercase letters"



def test_generate_qr_code_base64_returns_valid_base64():
    """Test that the QR code generator returns a valid base64 string."""
    url = "http://example.com"
    qr_code_str = generate_qr_code_base64(url)
    assert isinstance(qr_code_str, str)
    assert len(qr_code_str) > 0
    try:
        decoded = base64.b64decode(qr_code_str, validate=True)
    except Exception as e:
        pytest.fail(f"QR code string is not valid base64: {e}")



def test_is_valid_objectid_valid():
    """Test that a valid ObjectId string returns True."""
    valid_id = "507f1f77bcf86cd799439011"
    assert is_valid_objectid(valid_id) is True

def test_is_valid_objectid_invalid():
    """Test that an invalid ObjectId string returns False."""
    invalid_id = "invalid_objectid"
    assert is_valid_objectid(invalid_id) is False

def test_is_valid_objectid_empty():
    """Test that an empty string is not considered a valid ObjectId."""
    assert is_valid_objectid("") is False



def test_extract_preview_text_with_content():
    """Test that preview text is extracted correctly from a document that has a content-area."""
    document = {
        "document_data": {
            "template_data": [
                {
                    "id": "content-area",
                    "children": [
                        {"text": "Hello "},
                        {"type": "field", "content": "World", "label": "Fallback"},
                        {"children": [
                            {"text": " Nested text."}
                        ]}
                    ]
                }
            ]
        }
    }

    preview = extract_preview_text_from_document(document)
    expected = "Hello World Nested text."
    assert preview == expected, f"Expected preview text '{expected}', got '{preview}'"

def test_extract_preview_text_without_content_area():
    """Test that if no content-area exists, an empty string is returned."""
    document = {
        "document_data": {
            "template_data": [
                {"id": "other-area", "children": [{"text": "No content-area here"}]}
            ]
        }
    }
    preview = extract_preview_text_from_document(document)
    assert preview == "", "Expected empty preview text when no content-area exists."

def test_extract_preview_text_truncation():
    """Test that the extracted preview text is truncated to 100 characters if it exceeds that length."""
    # Create a content-area with repeated text so that the concatenated string is longer than 100 characters.
    long_text = "A" * 150  # 150 characters
    document = {
        "document_data": {
            "template_data": [
                {
                    "id": "content-area",
                    "children": [
                        {"text": long_text},
                    ]
                }
            ]
        }
    }
    preview = extract_preview_text_from_document(document)
    assert len(preview) == 100, "Preview text should be truncated to 100 characters."



def test_extract_preview_text_empty_document():
    """Test that an empty document returns an empty string."""
    document = {}
    preview = extract_preview_text_from_document(document)
    assert preview == "", "Expected empty preview text for an empty document."
