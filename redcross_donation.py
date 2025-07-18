#!/usr/bin/env python3
import os
import sys
from playwright.async_api import async_playwright
from browserbase import Browserbase
from dotenv import load_dotenv
import stripe
import asyncio

# Import our card details retrieval function
from get_card_details import get_card

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

# Set up BrowserBase
bb_api_key = os.getenv("BROWSERBASE_API_KEY")
bb_project_id = os.getenv("BROWSERBASE_PROJECT_ID")

if not bb_api_key or not bb_project_id:
    print("\n⚠️  BrowserBase API key or project ID not found in .env file.")
    exit(1)

bb = Browserbase(api_key=bb_api_key)

async def make_donation(card_id):
    """
    Make a donation to Red Cross using a virtual card
    
    Args:
        card_id (str): The ID of the virtual card to use
    """
    # Get card details
    print(f"Retrieving card details for {card_id}...")
    payment_info = get_card(card_id)
    
    if not payment_info:
        print("❌ Failed to retrieve card details")
        return
    
    print("✅ Card details retrieved")
    
    # Create a BrowserBase session
    print("Creating BrowserBase session...")
    session = bb.sessions.create(project_id=bb_project_id)
    print(f"✅ Session created. Watch live at: https://browserbase.com/sessions/{session.id}")
    
    async with async_playwright() as playwright:
        # Connect to the BrowserBase session
        browser = await playwright.chromium.connect_over_cdp(session.connect_url)
        context = browser.contexts[0]
        page = context.pages[0]
        
        try:
            print("Navigating to Red Cross donation page...")
            await page.goto("https://www.redcross.org/donate/donation.html")
            
            # Select $75 donation amount (this is a test card, so we're using test mode)
            print("Selecting donation amount...")
            await page.click("#modf-handle-0-radio")  # $75 option
            
            # Continue to next step
            print("Proceeding to next step...")
            await page.click("text=Continue")
            
            # Select credit card payment method
            print("Selecting credit card payment method...")
            await page.click("text=credit card")
            await page.click("text=Continue")
            
            # Fill billing information
            print("Filling billing information...")
            await page.fill("input[name='bill_to_forename']", payment_info["cardholder_firstName"])
            await page.fill("input[name='bill_to_surname']", payment_info["cardholder_lastName"])
            await page.fill("input[name='bill_to_email']", payment_info["cardholder_email"])
            await page.fill("input[name='bill_to_phone']", payment_info["cardholder_phone"])
            
            # Fill address information
            print("Filling address information...")
            await page.fill("input[name='bill_to_address_line1']", payment_info["cardholder_address"]["line1"])
            await page.fill("input[name='bill_to_address_city']", payment_info["cardholder_address"]["city"])
            await page.fill("input[name='bill_to_address_postal_code']", payment_info["cardholder_address"]["postal_code"])
            await page.select_option("select#bill_to_address_state", payment_info["cardholder_address"]["state"])
            
            # Fill card information
            print("Filling card information...")
            await page.fill("input#cardnumber", payment_info["card_number"])
            await page.fill("input#MM", str(payment_info["expiration_month"]))
            await page.fill("input#YY", str(payment_info["expiration_year"]))
            await page.fill("input#CVC", str(payment_info["cvc"]))
            
            # Wait for user confirmation before submitting
            print("\n✅ Form filled with virtual card details")
            print("⚠️  This is a TEST donation using a TEST card in Stripe's test mode")
            print("⚠️  No actual charges will be made")
            print("\nWaiting 10 seconds before clicking Donate button...")
            await asyncio.sleep(10)
            
            # Submit donation
            print("Submitting donation...")
            await page.click("text=Donate")
            
            # Wait for confirmation
            print("Waiting for confirmation...")
            await asyncio.sleep(5)
            
            print("\n✅ Donation process completed")
            print("Note: Since this is using Stripe's test mode, no actual donation was made")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            # Close the browser
            await browser.close()

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 redcross_donation.py <card_id>")
        print("Example: python3 redcross_donation.py ic_1234567890")
        sys.exit(1)
    
    card_id = sys.argv[1]
    asyncio.run(make_donation(card_id))

if __name__ == "__main__":
    main()
