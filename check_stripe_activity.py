#!/usr/bin/env python3
import os
import stripe
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

def check_payment_intents():
    """Check recent payment intents"""
    try:
        payment_intents = stripe.PaymentIntent.list(limit=5)
        
        if not payment_intents.data:
            print("No payment intents found")
            return
        
        print(f"\n=== Recent Payment Intents ({len(payment_intents.data)}) ===")
        for pi in payment_intents.data:
            print(f"ID: {pi.id}")
            print(f"Amount: ${pi.amount/100:.2f} {pi.currency.upper()}")
            print(f"Status: {pi.status}")
            print(f"Created: {pi.created}")
            print(f"Description: {pi.description}")
            print("-" * 40)
            
    except stripe.error.StripeError as e:
        print(f"❌ Error checking payment intents: {e}")

def check_charges():
    """Check recent charges"""
    try:
        charges = stripe.Charge.list(limit=5)
        
        if not charges.data:
            print("No charges found")
            return
        
        print(f"\n=== Recent Charges ({len(charges.data)}) ===")
        for charge in charges.data:
            print(f"ID: {charge.id}")
            print(f"Amount: ${charge.amount/100:.2f} {charge.currency.upper()}")
            print(f"Status: {charge.status}")
            print(f"Created: {charge.created}")
            if charge.description:
                print(f"Description: {charge.description}")
            print("-" * 40)
            
    except stripe.error.StripeError as e:
        print(f"❌ Error checking charges: {e}")

def check_payouts():
    """Check recent payouts"""
    try:
        payouts = stripe.Payout.list(limit=5)
        
        if not payouts.data:
            print("No payouts found")
            return
        
        print(f"\n=== Recent Payouts ({len(payouts.data)}) ===")
        for payout in payouts.data:
            print(f"ID: {payout.id}")
            print(f"Amount: ${payout.amount/100:.2f} {payout.currency.upper()}")
            print(f"Status: {payout.status}")
            print(f"Created: {payout.created}")
            print(f"Arrival Date: {payout.arrival_date}")
            print("-" * 40)
            
    except stripe.error.StripeError as e:
        print(f"❌ Error checking payouts: {e}")

def check_balance():
    """Check current balance"""
    try:
        balance = stripe.Balance.retrieve()
        
        print("\n=== Current Balance ===")
        for balance_item in balance.available:
            print(f"Available: ${balance_item.amount/100:.2f} {balance_item.currency.upper()}")
        
        for balance_item in balance.pending:
            print(f"Pending: ${balance_item.amount/100:.2f} {balance_item.currency.upper()}")
            
    except stripe.error.StripeError as e:
        print(f"❌ Error checking balance: {e}")

def check_card_authorizations(card_id):
    """Check for authorizations on the card"""
    if not card_id:
        print("No card ID provided, skipping card authorizations check")
        return
        
    try:
        authorizations = stripe.issuing.Authorization.list(
            card=card_id,
            limit=5
        )
        
        if not authorizations.data:
            print("No card authorizations found")
            return
        
        print(f"\n=== Recent Card Authorizations ({len(authorizations.data)}) ===")
        for auth in authorizations.data:
            print(f"ID: {auth.id}")
            print(f"Amount: ${auth.amount/100:.2f} {auth.currency.upper()}")
            print(f"Status: {auth.status}")
            print(f"Created: {auth.created}")
            if hasattr(auth, 'merchant_data') and auth.merchant_data:
                print(f"Merchant: {auth.merchant_data.name}")
            print("-" * 40)
            
    except stripe.error.StripeError as e:
        print(f"❌ Error checking card authorizations: {e}")

if __name__ == "__main__":
    print("Checking recent Stripe activity in TEST mode...")
    
    check_payment_intents()
    check_charges()
    check_payouts()
    check_balance()
    
    # If you want to check a specific card, uncomment and provide the card ID
    # check_card_authorizations("ic_1RffUCLP54m13jvUESeDqzHz")
    
    print("\nIf you don't see your transactions, make sure:")
    print("1. You're using the correct Stripe account")
    print("2. You're viewing the test mode dashboard at https://dashboard.stripe.com/test/payments")
    print("3. The transactions were created with the same API key you're using now")
