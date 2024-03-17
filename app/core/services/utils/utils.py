import string
import random
import qrcode
from io import BytesIO
from bson import ObjectId

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