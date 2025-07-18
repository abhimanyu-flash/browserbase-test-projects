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
    print("    Get a test API key from https://dashboard.stripe.com/test/apikeys")
    exit(1)
elif not stripe_api_key.startswith("sk_test_"):
    print("\n❌ ERROR: You must use a Stripe TEST API key (starts with sk_test_)")
    print("    This program is designed to run in test mode only.")
    print("    Get a test API key from https://dashboard.stripe.com/test/apikeys")
    exit(1)

stripe.api_key = stripe_api_key
print("✅ Using Stripe TEST mode")


def create_card(cardholder_id):
    """
    Create a virtual card for the given cardholder.
    
    Args:
        cardholder_id (str): The ID of the cardholder to create a card for
        
    Returns:
        The created card object
    """
    try:
        card = stripe.issuing.Card.create(
            cardholder=cardholder_id,
            currency='usd',
            type='virtual',
            spending_controls={
                "allowed_categories": ['charitable_and_social_service_organizations_fundraising'],
                # Choose to block certain categories instead of allowing them
                # "blocked_categories": ['automated_cash_disburse'],
                "spending_limits": [
                    {
                        "amount": 100,  # $1.00 measured in cents
                        "interval": "daily",  # all_time, daily, weekly, monthly, yearly, per_authorization
                    }
                ]
            },
        )
        print("Card created:", card.id)
        return card
    except Exception as e:
        print(f"Error creating virtual card: {e}")
        return None

if __name__ == "__main__":
    # Get cardholder ID from command line or input
    import sys
    if len(sys.argv) > 1:
        cardholder_id = sys.argv[1]
    else:
        cardholder_id = input("Enter cardholder ID: ")
    
    virtual_card = create_card(cardholder_id)
    if virtual_card:
        print(f"Successfully created virtual card with ID: {virtual_card.id}")
        print("Save this ID for retrieving card details.")
    else:
        print("Failed to create virtual card. Check your Stripe API key and cardholder ID.")
