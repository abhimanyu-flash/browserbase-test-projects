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


def create_cardholder():
    """
    Create a new cardholder in Stripe.
    A cardholder must be created before issuing virtual cards.
    """
    try:
        cardholder = stripe.issuing.Cardholder.create(
            name="Browserbase User",
            email="hello@browserbase.com",
            phone_number="+15555555555",
            status='active',
            type='individual',
            billing={
                "address": {
                    "line1": "123 Main Street",
                    "city": "San Francisco",
                    "state": "CA",
                    "country": "US",
                    "postal_code": "94111",
                }
            },
        )
        print("Cardholder created:", cardholder.id)
        return cardholder
    except Exception as e:
        print(f"Error creating cardholder: {e}")
        return None

if __name__ == "__main__":
    card_holder = create_cardholder()
    if card_holder:
        print(f"Successfully created cardholder with ID: {card_holder.id}")
        print("Save this ID for creating virtual cards.")
    else:
        print("Failed to create cardholder. Check your Stripe API key and try again.")
