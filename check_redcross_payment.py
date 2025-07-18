#!/usr/bin/env python3
import os
import time
import stripe
import sys
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up Stripe API key
stripe_api_key = os.getenv("STRIPE_API_KEY")

# Validate that we're using a test API key
if not stripe_api_key:
    print("\n⚠️  No Stripe API key found in .env file. Please add your test API key.")
    exit(1)
elif not stripe_api_key.startswith("sk_test_"):
    print("\n❌ ERROR: You must use a Stripe TEST API key (starts with sk_test_)")
    exit(1)

stripe.api_key = stripe_api_key
print("✅ Using Stripe TEST mode")

def check_card_authorizations(card_id):
    """
    Check for recent authorizations on the virtual card
    """
    try:
        # Get the card details
        card = stripe.issuing.Card.retrieve(card_id)
        print(f"Card: {card.id} (Last 4: {card.last4})")
        
        # Get recent authorizations for this card
        now = datetime.datetime.now()
        one_hour_ago = int((now - datetime.timedelta(hours=1)).timestamp())
        
        authorizations = stripe.issuing.Authorization.list(
            card=card_id,
            created={
                "gte": one_hour_ago
            },
            limit=5
        )
        
        if not authorizations.data:
            print("❌ No recent authorizations found for this card")
            return None
        
        print(f"✅ Found {len(authorizations.data)} recent authorization(s)")
        
        # Get the most recent authorization
        auth = authorizations.data[0]
        print(f"Authorization ID: {auth.id}")
        print(f"Merchant: {auth.merchant_data.name}")
        print(f"Amount: ${auth.amount/100:.2f} {auth.currency.upper()}")
        print(f"Status: {auth.status}")
        print(f"Approved: {auth.approved}")
        
        if "redcross" in auth.merchant_data.name.lower() or "red cross" in auth.merchant_data.name.lower():
            print("✅ Confirmed Red Cross merchant")
        else:
            print(f"⚠️  Merchant name doesn't contain 'Red Cross': {auth.merchant_data.name}")
        
        return auth
            
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return None

def check_card_transactions(card_id):
    """
    Check for recent transactions on the virtual card
    """
    try:
        # Get recent transactions for this card
        now = datetime.datetime.now()
        one_hour_ago = int((now - datetime.timedelta(hours=1)).timestamp())
        
        transactions = stripe.issuing.Transaction.list(
            card=card_id,
            created={
                "gte": one_hour_ago
            },
            limit=5
        )
        
        if not transactions.data:
            print("❌ No recent transactions found for this card")
            return None
        
        print(f"✅ Found {len(transactions.data)} recent transaction(s)")
        
        # Get the most recent transaction
        tx = transactions.data[0]
        print(f"Transaction ID: {tx.id}")
        print(f"Type: {tx.type}")
        print(f"Amount: ${tx.amount/100:.2f} {tx.currency.upper()}")
        
        if hasattr(tx, 'purchase_details') and tx.purchase_details:
            if hasattr(tx.purchase_details, 'merchant') and tx.purchase_details.merchant:
                print(f"Merchant: {tx.purchase_details.merchant.name}")
                
                if "redcross" in tx.purchase_details.merchant.name.lower() or "red cross" in tx.purchase_details.merchant.name.lower():
                    print("✅ Confirmed Red Cross merchant")
                else:
                    print(f"⚠️  Merchant name doesn't contain 'Red Cross': {tx.purchase_details.merchant.name}")
        
        return tx
            
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return None

def monitor_payment_flow(card_id):
    """
    Monitor the payment flow for the Red Cross donation
    """
    print("\n=== Checking for Card Authorizations ===")
    auth = check_card_authorizations(card_id)
    
    print("\n=== Checking for Card Transactions ===")
    tx = check_card_transactions(card_id)
    
    if auth and auth.approved:
        print("\n✅ The payment was authorized successfully")
        
        if tx:
            print("✅ The transaction was recorded")
            print("\nPayment flow verification:")
            print("1. Virtual card was used for payment")
            print("2. Authorization was approved")
            print("3. Transaction was recorded")
            print("\nThis confirms the payment process is working correctly in test mode.")
        else:
            print("\n⚠️  The payment was authorized but no transaction was recorded yet")
            print("This is normal if the authorization just happened. Transactions may take a few minutes to appear.")
            print("Try running this script again in a few minutes.")
    elif auth:
        print("\n❌ The payment was NOT approved")
        print(f"Authorization status: {auth.status}")
    else:
        print("\n❌ No authorization was found")
        print("This could mean:")
        print("1. The donation process didn't reach the payment stage")
        print("2. The card wasn't used correctly in the form")
        print("3. The merchant hasn't processed the payment yet")
    
    print("\nTo verify in Stripe Dashboard:")
    print("1. Go to https://dashboard.stripe.com/test/issuing")
    print("2. Make sure you're in 'Viewing test data' mode")
    print("3. Check the card details and transaction history")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 check_redcross_payment.py <card_id>")
        print("Example: python3 check_redcross_payment.py ic_1RffUCLP54m13jvUESeDqzHz")
        sys.exit(1)
    
    card_id = sys.argv[1]
    monitor_payment_flow(card_id)
