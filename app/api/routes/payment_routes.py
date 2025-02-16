import hashlib
import hmac
import logging
from typing import Any, Dict

import httpx  # Use httpx for async HTTP requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.db import get_db
from app.core.settings.configurations import settings
from app.models.payment_model import Payment
from app.schemas.payment_schema import PaymentCreate
from commonLib.response.response_schema import create_response

router = APIRouter(prefix="/api/payments", tags=["Payments"])
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY

# --- Helper function for making async HTTP calls ---
async def fetch_paystack_verification(reference: str) -> Dict[str, Any]:
    url = f"{settings.PAYSTACK_VERIFY_PAYMENT_URL}{reference}"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

@router.post("/verify-payment", response_model=Dict[str, Any])
async def verify_payment(data: PaymentCreate, db: Session = Depends(get_db)):
    """
    Verify a payment using Paystack.

    This endpoint performs the following:
      - Validates the incoming payment reference.
      - Calls the Paystack API using an asynchronous HTTP client.
      - Checks that the response has the expected structure and that the payment was successful.
      - Creates a Payment record in the database.
      - Returns a success response.
    """
    logger.info(f"Verifying payment for reference: {data.reference}")

    if not data.reference:
        logger.error("Payment reference is missing.")
        raise HTTPException(status_code=400, detail="Payment reference is required.")

    try:
        result = await fetch_paystack_verification(data.reference)
    except httpx.HTTPError as http_err:
        logger.error(f"HTTP error while verifying payment for {data.reference}: {http_err}")
        raise HTTPException(status_code=500, detail="Error communicating with Paystack API")
    except Exception as e:
        logger.error(f"Unexpected error during payment verification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error during payment verification")

    # Validate that the response structure contains the necessary keys
    try:
        paystack_data = result.get("data")
        if not paystack_data or paystack_data.get("status") != "success":
            logger.warning(f"Payment verification failed for reference: {data.reference}")
            raise HTTPException(status_code=400, detail="Payment verification failed")
    except Exception as e:
        logger.error(f"Error processing Paystack response: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Invalid response from Paystack API")

    try:
        # Create a new Payment record in the database
        payment = Payment(
            user_id=data.user_id,
            document_id=data.document_id,
            amount=paystack_data.get("amount", 0) / 100,  # Convert amount to original currency
            status="success",
            payment_method=paystack_data.get("channel", ""),
            paystack_reference=data.reference,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        logger.info(f"Payment recorded successfully for reference: {data.reference}")
    except Exception as e:
        logger.error(f"Database error recording payment for reference {data.reference}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to record payment")

    return {"status": "success", "message": "Payment verified successfully"}


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Paystack webhook notifications.

    This endpoint:
      - Extracts and verifies the webhook signature.
      - Processes only the 'charge.success' events.
      - Validates that required metadata (user_id, document_id) exists.
      - Creates a Payment record in the database.
    """
    logger.info("Webhook triggered.")
    try:
        json_data = await request.json()
        event = json_data.get("event")
        signature = request.headers.get("x-paystack-signature")
        if not signature:
            logger.error("Missing x-paystack-signature header.")
            raise HTTPException(status_code=400, detail="Missing signature header.")

        # Verify the signature securely
        secret = bytes(PAYSTACK_SECRET_KEY, "utf-8")
        body = await request.body()
        computed_signature = hmac.new(secret, body, hashlib.sha512).hexdigest()
        if not hmac.compare_digest(computed_signature, signature):
            logger.warning("Signature verification failed.")
            return {"status": "ignored"}, 400

        if event != "charge.success":
            logger.info(f"Ignoring event: {event}")
            return {"status": "ignored"}, 200

        data = json_data.get("data", {})
        reference = data.get("reference")
        metadata = data.get("metadata", {})

        if not metadata.get("user_id") or not metadata.get("document_id"):
            logger.error("Missing metadata: user_id or document_id not provided.")
            raise HTTPException(status_code=400, detail="Missing payment metadata.")

        logger.info(f"Charge successful for reference: {reference}")

        # Create payment record if not already recorded
        payment = Payment(
            user_id=metadata["user_id"],
            document_id=metadata["document_id"],
            amount=data.get("amount", 0) / 100,  # Convert amount
            status="success",
            payment_method=data.get("channel", ""),
            paystack_reference=reference,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        logger.info(f"Payment recorded successfully for reference: {reference}")
        return {"status": "success"}, 200

    except HTTPException as http_exc:
        logger.error(f"Webhook HTTPException: {http_exc.detail}", exc_info=True)
        raise http_exc
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

    logger.info("Webhook event ignored.")
    return {"status": "ignored"}, 200
