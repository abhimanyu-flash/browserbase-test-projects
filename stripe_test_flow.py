#!/usr/bin/env python3
import os
import time
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

def create_payment_intent():
    """
    Create a payment intent using the bypass pending test card
    This will make funds immediately available
    """
    try:
        # Create a PaymentMethod using the bypass pending test card
        payment_method = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": "4000000000000077",  # This is the bypass pending test card
                "exp_month": 12,
                "exp_year": 2030,
                "cvc": "123",
            },
        )
        
        print(f"✅ Created test payment method: {payment_method.id}")
        
        # Create a Payment Intent and confirm it immediately
        payment_intent = stripe.PaymentIntent.create(
            amount=5000,  # $50.00
            currency="usd",
            payment_method=payment_method.id,
            confirm=True,
            description="Test payment with bypass pending card",
        )
        
        print(f"✅ Created payment intent: {payment_intent.id}")
        print(f"Payment intent status: {payment_intent.status}")
        
        if payment_intent.status == "succeeded":
            print("✅ Payment intent succeeded")
            return payment_intent
        else:
            print(f"❌ Payment intent status is not succeeded: {payment_intent.status}")
            return None
            
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return None

def check_charge(payment_intent_id):
    """
    Check if the charge was successful
    """
    try:
        # Retrieve the payment intent to get the charge ID
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if not payment_intent.latest_charge:
            print("❌ No charge found on payment intent")
            return None
        
        # Retrieve the charge
        charge = stripe.Charge.retrieve(payment_intent.latest_charge)
        
        print(f"Charge ID: {charge.id}")
        print(f"Charge status: {charge.status}")
        print(f"Charge amount: ${charge.amount/100:.2f}")
        
        if charge.status == "succeeded":
            print("✅ Charge succeeded")
            return charge
        else:
            print(f"❌ Charge status is not succeeded: {charge.status}")
            return None
            
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return None

def check_balance():
    """
    Check if the funds are available in the balance
    """
    try:
        # Get the current balance
        balance = stripe.Balance.retrieve()
        
        print("Available balance:")
        for available in balance.available:
            print(f"  {available.currency}: ${available.amount/100:.2f}")
        
        print("Pending balance:")
        for pending in balance.pending:
            print(f"  {pending.currency}: ${pending.amount/100:.2f}")
        
        # Check if there are available funds in USD
        available_usd = next((b for b in balance.available if b.currency == "usd"), None)
        
        if available_usd and available_usd.amount > 0:
            print("✅ Funds are available in the balance")
            return available_usd.amount
        else:
            print("❌ No available funds found in USD")
            return 0
            
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return 0

def create_test_bank_account():
    """
    Create a test external account (bank account) for payouts
    """
    try:
        # Check if there's already a bank account
        accounts = stripe.Account.list_external_accounts(
            stripe.Account.retrieve().id,
            object="bank_account",
            limit=1
        )
        
        if accounts.data:
            print(f"✅ Using existing bank account: {accounts.data[0].id}")
            return accounts.data[0].id
        
        # Create a new test bank account
        bank_account = stripe.Account.create_external_account(
            stripe.Account.retrieve().id,
            external_account={
                "object": "bank_account",
                "country": "US",
                "currency": "usd",
                "account_holder_name": "Test User",
                "account_holder_type": "individual",
                "routing_number": "110000000",  # Test routing number
                "account_number": "000123456789",  # Test account number
            },
        )
        
        print(f"✅ Created test bank account: {bank_account.id}")
        return bank_account.id
            
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return None

def create_payout(amount):
    """
    Create a test payout
    """
    try:
        # Create a payout
        payout = stripe.Payout.create(
            amount=amount,
            currency="usd",
        )
        
        print(f"✅ Created payout: {payout.id}")
        print(f"Payout status: {payout.status}")
        
        return payout.id
            
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return None

def check_payout_status(payout_id):
    """
    Check the status of a payout
    """
    try:
        # Poll the payout status until it's paid
        max_attempts = 5
        for attempt in range(max_attempts):
            payout = stripe.Payout.retrieve(payout_id)
            print(f"Payout status: {payout.status} (attempt {attempt+1}/{max_attempts})")
            
            if payout.status == "paid":
                print("✅ Payout is paid")
                return True
            
            if attempt < max_attempts - 1:
                print("Waiting 2 seconds before checking again...")
                time.sleep(2)
        
        print(f"❌ Payout did not reach 'paid' status after {max_attempts} attempts")
        return False
            
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return False

def run_test_flow():
    """
    Run the complete test flow
    """
    print("\n=== STEP 1: Create Payment Intent with Bypass Pending Card ===")
    payment_intent = create_payment_intent()
    if not payment_intent:
        return
    
    print("\n=== STEP 2: Check Charge Status ===")
    charge = check_charge(payment_intent.id)
    if not charge:
        return
    
    print("\n=== STEP 3: Check Balance for Available Funds ===")
    available_amount = check_balance()
    if not available_amount:
        return
    
    print("\n=== STEP 4: Create Test Bank Account ===")
    bank_account_id = create_test_bank_account()
    if not bank_account_id:
        return
    
    print("\n=== STEP 5: Create Test Payout ===")
    # Create a payout for the available amount (or a smaller amount)
    payout_amount = min(available_amount, 5000)  # Don't try to payout more than available
    payout_id = create_payout(int(payout_amount))
    if not payout_id:
        return
    
    print("\n=== STEP 6: Check Payout Status ===")
    success = check_payout_status(payout_id)
    
    if success:
        print("\n✅✅✅ TEST FLOW COMPLETE ✅✅✅")
        print("The entire payment flow has been verified in test mode:")
        print("1. Payment intent created and succeeded")
        print("2. Charge succeeded")
        print("3. Funds are available in the balance")
        print("4. Payout created and paid")
        print("\nYou can verify this in the Stripe Dashboard:")
        print("1. Switch to 'Viewing test data' in the top-left")
        print("2. Payments tab: Find your charge with status 'Succeeded'")
        print("3. Balance tab: Check the available balance")
        print("4. Payouts tab: Find your payout with status 'Paid'")
    else:
        print("\n❌ TEST FLOW INCOMPLETE")
        print("Some part of the payment flow did not complete successfully.")

if __name__ == "__main__":
    run_test_flow()
