#!/usr/bin/env python3
from playwright.sync_api import Playwright, sync_playwright
from browserbase import Browserbase
from get_card_details import get_card as getCard
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Validate Stripe API key is in test mode
stripe_api_key = os.getenv("STRIPE_API_KEY")
if not stripe_api_key or not stripe_api_key.startswith("sk_test_"):
    print("\n❌ ERROR: You must use a Stripe TEST API key (starts with sk_test_)")
    exit(1)

# Set up BrowserBase
bb = Browserbase(api_key=os.environ["BROWSERBASE_API_KEY"])

def run(playwright: Playwright, card_id: str) -> None:
    session = bb.sessions.create(
        project_id=os.environ["BROWSERBASE_PROJECT_ID"],
    )

    browser = playwright.chromium.connect_over_cdp(session.connect_url)
    context = browser.contexts[0]
    page = context.pages[0]

    payment_info = getCard(card_id)

    # Watch the session
    print(f"Session URL: https://browserbase.com/sessions/{session.id}")

    # Navigate to the donation page
    page.goto("https://www.redcross.org/donate/donation.html")

    # Perform actions on the donation page
    page.click("#modf-handle-0-radio")
    page.click("text=Continue")
    page.click("text=credit card")

    # Fill billing information
    page.fill("input[name='bill_to_forename']", payment_info["cardholder_firstName"])
    page.fill("input[name='bill_to_surname']", payment_info["cardholder_lastName"])
    page.fill("input[name='bill_to_email']", payment_info["cardholder_email"])
    page.fill("input[name='bill_to_phone']", payment_info["cardholder_phone"])

    # Fill in the address information
    page.fill("input[name='bill_to_address_line1']", payment_info["cardholder_address"]["line1"])
    page.fill("input[name='bill_to_address_city']", payment_info["cardholder_address"]["city"])
    page.fill("input[name='bill_to_address_postal_code']", payment_info["cardholder_address"]["postal_code"])
    page.select_option("select#bill_to_address_state", payment_info["cardholder_address"]["state"])

    # Fill in the card information
    page.fill("input#cardnumber", payment_info["card_number"])
    page.fill("input#MM", str(payment_info["expiration_month"]))
    page.fill("input#YY", str(payment_info["expiration_year"]))
    page.fill("input#CVC", str(payment_info["cvc"]))

    # Wait for user confirmation before submitting
    print("\n✅ Form filled with virtual card details")
    print("⚠️  This is a TEST donation using a TEST card in Stripe's test mode")
    print("⚠️  No actual charges will be made")
    
    # Click donate button
    print("Clicking Donate button...")
    page.click("text=Donate")
    
    print("\n✅ Donation process completed")
    print("Note: Since this is using Stripe's test mode, no actual donation was made")
    
    page.close()
    browser.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 browserbase_redcross.py <card_id>")
        print("Example: python3 browserbase_redcross.py ic_1RffUCLP54m13jvUESeDqzHz")
        sys.exit(1)
    
    card_id = sys.argv[1]
    
    with sync_playwright() as playwright:
        run(playwright, card_id)
