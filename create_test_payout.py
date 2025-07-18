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

def create_test_payout():
    """
    Create a test payout to trigger the payout.paid event
    """
    try:
        # Create a test payout
        payout = stripe.Payout.create(
            amount=4000,  # $40.00 (less than the $50 we charged)
            currency="usd",
        )
        
        print(f"✅ Created test payout: {payout.id}")
        print(f"Payout status: {payout.status}")
        print(f"Payout amount: ${payout.amount/100:.2f}")
        
        return payout
            
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return None

if __name__ == "__main__":
    print("Creating a test payout...")
    print("This should trigger the following events:")
    print("1. payout.paid")
    print("\nCheck the Stripe CLI listener for these events.")
    
    payout = create_test_payout()
    
    if payout:
        print("\n✅ Test payout created successfully!")
        print("The Stripe CLI listener should show the payout.paid event.")
        print("\nNext steps:")
        print("1. Check your Stripe Dashboard (in test mode) to see the payout")
        print("2. You have now verified the full payment lifecycle in test mode!")
    else:
        print("\n❌ Failed to create test payout")
