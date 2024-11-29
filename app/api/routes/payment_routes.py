from app.api.dependencies.db import get_db
from app.models.payment_model import Payment
from sqlalchemy.orm import Session
from app.core.settings.configurations import settings
import requests
import hmac
import hashlib
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks

from app.core.settings.configurations import settings
from app.schemas.payment_schema import PaymentCreate
import logging
from typing import Dict, Any

router = APIRouter(prefix="/api/payments", tags=["Payments"])
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY

@router.post("/verify-payment", response_model=Dict[str, Any])
async def verify_payment(data: PaymentCreate, db: Session = Depends(get_db)):
    """
    Endpoint to verify payment using Paystack.
    """
    logger.info(f"Verifying payment for reference: {data.reference}")
    

    if not data.reference:
        logger.error("Payment reference is required.")
        raise HTTPException(status_code=400, detail="Payment reference is required.")
    
    # Set headers and make a request to Paystack to verify payment
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(f"{settings.PAYSTACK_VERIFY_PAYMENT_URL}{data.reference}", headers=headers)
        response.raise_for_status()  
        result = response.json()

        if result["data"]["status"] == "success":
         
            payment = Payment(
                user_id=data.user_id,
                document_id=data.document_id,
                amount=result["data"]["amount"] / 100,  # Convert to the original currency unit
                status="success",
                payment_method=result["data"]["channel"],
                paystack_reference=data.reference,
            )
            db.add(payment)
            db.commit()
            db.refresh(payment)

            logger.info(f"Payment verified successfully for reference: {data.reference}")
            return {"status": "success", "message": "Payment verified successfully"}
        else:
            logger.warning(f"Payment verification failed for reference: {data.reference}")
            raise HTTPException(status_code=400, detail="Payment verification failed")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error while verifying payment with reference {data.reference}: {e}")
        raise HTTPException(status_code=500, detail="Error verifying payment with Paystack")


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint to handle Paystack webhooks.
    """
    logger.info("Webhook triggered.")
    try:
        json_data = await request.json()
        event = json_data.get("event")
        signature = request.headers.get("x-paystack-signature")

        # Verify the signature for security purposes
        secret = bytes(PAYSTACK_SECRET_KEY, "utf-8")
        body = await request.body()
        hashed = hmac.new(secret, body, hashlib.sha512).hexdigest()

        if hashed != signature:
            logger.warning("Signature verification failed.")
            return {"status": "ignored"}, 400

        if event == "charge.success":
            data = json_data.get("data")
            reference = data.get("reference")
            logger.info(f"Charge successful for reference: {reference}")

            # Store payment data in the database
            payment = Payment(
                user_id=data["metadata"]["user_id"],
                document_id=data["metadata"]["document_id"],
                amount=data["amount"] / 100,  # Convert to the original currency unit
                status="success",
                payment_method=data["channel"],
                paystack_reference=reference,
            )
            db.add(payment)
            db.commit()
            db.refresh(payment)

            logger.info(f"Payment recorded successfully for reference: {reference}")
            return {"status": "success"}, 200

    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    logger.info("Webhook event ignored.")
    return {"status": "ignored"}, 200
