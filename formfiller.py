import os
import json
import asyncio
import stripe
import argparse
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from langchain_openai import ChatOpenAI

load_dotenv()
gpt4 = ChatOpenAI(model="gpt-4", temperature=0)

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


# Default form data (will be overridden if using a virtual card)
form_data = {
    "name": "Abhimanyu",
    "email": "abhimanyu@example.com",
    "phone": "9876543210",
    "address": "123 Flash Street",
    "city": "Mumbai",
    "state": "MH",
    "zipcode": "400001",
    "card": "4111111111111111",
    "expiry": "12/26",
    "cvv": "123"
}

def create_cardholder():
    """Create a new cardholder in Stripe."""
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
        print("✅ Cardholder created:", cardholder.id)
        return cardholder
    except Exception as e:
        print(f"❌ Error creating cardholder: {e}")
        return None

def create_virtual_card(cardholder_id):
    """Create a virtual card for the given cardholder."""
    try:
        card = stripe.issuing.Card.create(
            cardholder=cardholder_id,
            currency='usd',
            type='virtual',
            spending_controls={
                "allowed_categories": ['charitable_and_social_service_organizations_fundraising'],
                "spending_limits": [
                    {
                        "amount": 7500,  # $75.00 measured in cents
                        "interval": "daily",
                    }
                ]
            },
        )
        print("✅ Virtual card created:", card.id)
        return card
    except Exception as e:
        print(f"❌ Error creating virtual card: {e}")
        return None

def get_card_details(card_id):
    """Retrieve the details of a virtual card."""
    try:
        card = stripe.issuing.Card.retrieve(card_id, expand=['number', 'cvc'])
        
        card_info = {
            'name': card.cardholder.name,
            'email': card.cardholder.email,
            'phone': card.cardholder.phone_number,
            'address': card.cardholder.billing.address.line1,
            'city': card.cardholder.billing.address.city,
            'state': card.cardholder.billing.address.state,
            'zipcode': card.cardholder.billing.address.postal_code,
            'card': card.number,
            'expiry': f"{card.exp_month:02d}/{str(card.exp_year)[-2:]}",
            'cvv': card.cvc,
        }
        
        # Print card info (with masked card number for security)
        masked_info = card_info.copy()
        if masked_info.get('card'):
            masked_info['card'] = f"****-****-****-{masked_info['card'][-4:]}"
        if masked_info.get('cvv'):
            masked_info['cvv'] = "***"
        
        print('💳 Card info:', masked_info)
        return card_info
    except Exception as e:
        print(f"❌ Error retrieving card details: {e}")
        return None

async def autofill_smart(url, use_virtual_card=False, card_id=None):
    # If using a virtual card, get its details
    if use_virtual_card and card_id:
        print(f"💳 Using virtual card with ID: {card_id}")
        card_details = get_card_details(card_id)
        if card_details:
            # Update form_data with virtual card details
            global form_data
            form_data = card_details
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print(f"🌐 Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Wait for forms to appear
        try:
            await page.wait_for_selector("input", timeout=15000)
        except:
            print("⚠️ No input fields detected after waiting.")
            return

        print("🔍 Extracting visible input fields...")
        inputs = await page.query_selector_all("input")
        input_snippets = []

        for input_elem in inputs:
            try:
                visible = await input_elem.is_visible()
                disabled = await input_elem.is_disabled()
                if visible and not disabled:
                    outer = await input_elem.evaluate("el => el.outerHTML")
                    name = await input_elem.get_attribute("name") or ""
                    input_snippets.append({"html": outer, "name": name})
            except:
                continue

        if not input_snippets:
            print("❌ No usable input fields found.")
            return

        prompt = f"""
You are given a list of HTML <input> elements. For each, return a list of dictionaries with:
- 'type': what it expects (name, email, phone, address, card, expiry, cvv, etc.)
- 'selector': a Playwright-compatible selector that can be used to fill it (e.g. 'input[name="email"]')

Respond ONLY in JSON format like:
[{{"type": "email", "selector": "input[name='email']"}}, ...]

Inputs:
{json.dumps([i["html"] for i in input_snippets])}
        """

        print("🤖 Asking GPT-4 to map fields...")
        try:
            response = await gpt4.ainvoke(prompt)
            mappings = json.loads(response.content)
        except Exception as e:
            print("❌ Failed to parse LLM response:", e)
            print("LLM raw output:", response.content)
            return

        print("✍️ Filling form fields...\n")
        for field in mappings:
            selector = field.get("selector")
            field_type = field.get("type")
            value = form_data.get(field_type)
            if selector and value:
                try:
                    await page.fill(selector, value)
                    print(f"✅ Filled '{field_type}' → {selector}")
                except Exception as e:
                    print(f"⚠️ Couldn't fill '{field_type}' → {selector}: {e}")

        print("\n💡 Form filled with payment information. Review before submitting.")
        print("⏳ Waiting for 30 seconds to allow manual review...")
        await asyncio.sleep(30)
        await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Form filler with Stripe virtual card support")
    parser.add_argument("url", nargs='?', default=None, help="URL of the form to fill")
    parser.add_argument("--create-cardholder", action="store_true", help="Create a new cardholder")
    parser.add_argument("--create-card", metavar="CARDHOLDER_ID", help="Create a virtual card for the given cardholder ID")
    parser.add_argument("--use-card", metavar="CARD_ID", help="Use the specified virtual card ID for form filling")
    
    args = parser.parse_args()
    
    if args.create_cardholder:
        # Create a new cardholder
        cardholder = create_cardholder()
        if cardholder:
            print(f"\n✅ Successfully created cardholder with ID: {cardholder.id}")
            print("Use this ID to create a virtual card with --create-card option")
    
    elif args.create_card:
        # Create a virtual card for the given cardholder
        card = create_virtual_card(args.create_card)
        if card:
            print(f"\n✅ Successfully created virtual card with ID: {card.id}")
            print("Use this ID to fill forms with --use-card option")
    
    else:
        # Fill the form
        if not args.url:
            parser.error("URL is required when filling forms")
        
        use_virtual_card = args.use_card is not None
        asyncio.run(autofill_smart(args.url, use_virtual_card, args.use_card))
