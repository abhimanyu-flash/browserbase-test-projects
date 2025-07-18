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

def create_payment_intent():
    """
    Create a payment intent using the bypass pending test card
    This will make funds immediately available
    """
    try:
        # Use a pre-defined test token for the bypass pending card
        # This avoids sending raw card data to the API
        payment_method = stripe.PaymentMethod.create(
            type="card",
            card={
                "token": "tok_bypassPending",  # Special token for bypass pending test card
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
            return_url="https://example.com/return",  # Required for redirect-based payment methods
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
        )
        
        print(f"✅ Created payment intent: {payment_intent.id}")
        print(f"Payment intent status: {payment_intent.status}")
        
        if payment_intent.status == "succeeded":
            print("✅ Payment intent succeeded")
            
            # Get the charge ID
            if payment_intent.latest_charge:
                charge = stripe.Charge.retrieve(payment_intent.latest_charge)
                print(f"✅ Charge created: {charge.id}")
                print(f"Charge status: {charge.status}")
                print(f"Charge amount: ${charge.amount/100:.2f}")
            
            return payment_intent
        else:
            print(f"❌ Payment intent status is not succeeded: {payment_intent.status}")
            return None
            
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return None

if __name__ == "__main__":
    print("Creating a test payment with the bypass pending card...")
    print("This should trigger the following events in order:")
    print("1. payment_intent.succeeded")
    print("2. charge.succeeded")
    print("3. balance.available")
    print("\nCheck the Stripe CLI listener for these events.")
    
    payment_intent = create_payment_intent()
    
    if payment_intent:
        print("\n✅ Test payment created successfully!")
        print("The Stripe CLI listener should show the events being triggered.")
        print("\nNext steps:")
        print("1. Create a test payout to see the payout.paid event")
        print("2. Check your Stripe Dashboard (in test mode) to see the payment")
    else:
        print("\n❌ Failed to create test payment")
