from app.api.dependencies.db import get_db
from app.models.payment_model import Payment
from fastapi import FastAPI, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.settings.configurations import settings
import requests
import hmac
import hashlib

app = FastAPI()

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY

@app.post('/api/verify-payment')
async def verify_payment(data: dict, db: Session = Depends(get_db)):
    print("hello world")
    reference = data.get('reference')
    user_id = data.get('user_id')
    document_id = data.get('document_id')
    print(reference, user_id, document_id)
    headers = {
        'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }
    response = requests.get(f'{settings.PAYSTACK_VERIFY_PAYMENT_URL}{reference}', headers=headers)

    if response.status_code == 200:
        result = response.json()
        status = 'success' if result['data']['status'] == 'success' else 'failed'
        payment = Payment(
            user_id=user_id,
            document_id=document_id,
            amount=result['data']['amount'] / 100,  # Convert to the original currency unit
            status=status,
            payment_method=result['data']['channel'],
            paystack_reference=reference
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        if status == 'success':
            return {'status': 'success', 'message': 'Payment verified successfully'}
        else:
            raise HTTPException(status_code=400, detail='Payment verification failed')
    else:
        raise HTTPException(status_code=500, detail='Error verifying payment')


# @app.post('/api/webhook')
# async def webhook(request: Request, db: Session = Depends(get_db)):
#     json_data = await request.json()
#     event = json_data.get('event')

#     signature = request.headers.get('x-paystack-signature')
#     secret = bytes(PAYSTACK_SECRET_KEY, 'utf-8')
#     hashed = hmac.new(secret, await request.body(), hashlib.sha512).hexdigest()

#     if hashed == signature:
#         if event == 'charge.success':
#             data = json_data.get('data')
#             reference = data.get('reference')
#             headers = {
#                 'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
#                 'Content-Type': 'application/json',
#             }
#             response = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)

#             if response.status_code == 200 and response.json()['data']['status'] == 'success':
#                 payment = Payment(
#                     user_id=data['metadata']['user_id'],
#                     document_id=data['metadata']['document_id'],
#                     amount=data['amount'] / 100,
#                     status='success',
#                     payment_method=data['channel'],
#                     paystack_reference=reference
#                 )
#                 db.add(payment)
#                 db.commit()
#                 db.refresh(payment)
#                 return {'status': 'success'}, 200
#             else:
#                 return {'status': 'failed'}, 400

#     return {'status': 'ignored'}, 200
