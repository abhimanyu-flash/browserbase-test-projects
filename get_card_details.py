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


def get_card(card_id):
    """
    Retrieve the details of a virtual card.
    
    Args:
        card_id (str): The ID of the card to retrieve
        
    Returns:
        A dictionary containing the card details
    """
    try:
        card = stripe.issuing.Card.retrieve(card_id, expand=['number', 'cvc'])
        
        card_info = {
            'cardholder_firstName': card.cardholder.name.split(' ')[0],
            'cardholder_lastName': card.cardholder.name.split(' ')[1] if len(card.cardholder.name.split(' ')) > 1 else '',
            'cardholder_email': card.cardholder.email,
            'cardholder_phone': card.cardholder.phone_number,
            'cardholder_address': card.cardholder.billing.address,
            'card_number': card.number,
            'expiration_month': card.exp_month,
            'expiration_year': str(card.exp_year)[-2:],  # 2028 -> 28
            'cvc': card.cvc,
            'brand': card.brand,
            'currency': card.currency,
        }
        
        # Print card info (with masked card number for security)
        masked_info = card_info.copy()
        if masked_info.get('card_number'):
            masked_info['card_number'] = f"****-****-****-{masked_info['card_number'][-4:]}"
        if masked_info.get('cvc'):
            masked_info['cvc'] = "***"
        
        print('Card info:', masked_info)
        return card_info
    except Exception as e:
        print(f"Error retrieving card details: {e}")
        return None

if __name__ == "__main__":
    # Get card ID from command line or input
    import sys
    if len(sys.argv) > 1:
        card_id = sys.argv[1]
    else:
        card_id = input("Enter card ID: ")
    
    card_info = get_card(card_id)
    if card_info:
        print("Successfully retrieved card details.")
    else:
        print("Failed to retrieve card details. Check your Stripe API key and card ID.")
