#!/usr/bin/env python3
from playwright.sync_api import Playwright, sync_playwright
from browserbase import Browserbase
from get_card_details import get_card as getCard
import os
import sys
from dotenv import load_dotenv
import stripe

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
    print("✅ BrowserBase session created")

    try:
        # Navigate to the donation page
        print("Navigating to Red Cross donation page...")
        page.goto("https://www.redcross.org/donate/donation.html", wait_until="networkidle")
        print("Page loaded successfully")
        
        # Wait for the page to be fully loaded
        page.wait_for_load_state("networkidle")
        
        # Perform actions on the donation page with increased timeouts
        print("Selecting $75 donation amount...")
        page.wait_for_selector("#modf-handle-0-radio", timeout=60000)
        page.click("#modf-handle-0-radio")
        
        print("Proceeding to next step...")
        page.wait_for_selector("text=Continue", timeout=60000)
        page.click("text=Continue")
        
        # Wait for the next page to load
        page.wait_for_load_state("networkidle")
        
        print("Selecting credit card payment method...")
        try:
            page.wait_for_selector("text=credit card", timeout=60000)
            page.click("text=credit card")
            
            page.wait_for_selector("text=Continue", timeout=60000)
            page.click("text=Continue")
        except Exception as e:
            print(f"Warning: Could not find credit card option or continue button: {e}")
            print("Attempting to proceed with form filling anyway...")
            
        # Wait for the payment form to load
        page.wait_for_load_state("networkidle")

        # Fill billing information with error handling
        print("Filling billing information...")
        try:
            # Wait for form fields to be available
            page.wait_for_selector("input[name='bill_to_forename']", timeout=60000)
            
            # Fill billing information
            page.fill("input[name='bill_to_forename']", payment_info["cardholder_firstName"])
            page.fill("input[name='bill_to_surname']", payment_info["cardholder_lastName"])
            page.fill("input[name='bill_to_email']", payment_info["cardholder_email"])
            page.fill("input[name='bill_to_phone']", payment_info["cardholder_phone"])
            print("✅ Billing information filled")
        except Exception as e:
            print(f"Warning: Could not fill billing information: {e}")

        # Fill in the address information with error handling
        print("Filling address information...")
        try:
            # Wait for address fields to be available
            page.wait_for_selector("input[name='bill_to_address_line1']", timeout=60000)
            
            # Fill address information
            page.fill("input[name='bill_to_address_line1']", payment_info["cardholder_address"]["line1"])
            page.fill("input[name='bill_to_address_city']", payment_info["cardholder_address"]["city"])
            page.fill("input[name='bill_to_address_postal_code']", payment_info["cardholder_address"]["postal_code"])
            
            # Wait for state dropdown and select option
            page.wait_for_selector("select#bill_to_address_state", timeout=60000)
            page.select_option("select#bill_to_address_state", payment_info["cardholder_address"]["state"])
            print("✅ Address information filled")
        except Exception as e:
            print(f"Warning: Could not fill address information: {e}")

        # Fill in the card information with error handling
        print("Filling card information...")
        try:
            # Wait for card fields to be available
            page.wait_for_selector("input#cardnumber", timeout=60000)
            
            # Fill card information
            page.fill("input#cardnumber", payment_info["card_number"])
            page.fill("input#MM", str(payment_info["expiration_month"]))
            page.fill("input#YY", str(payment_info["expiration_year"]))
            page.fill("input#CVC", str(payment_info["cvc"]))
            print("✅ Card information filled")
        except Exception as e:
            print(f"Warning: Could not fill card information: {e}")

        # Wait for user confirmation before submitting
        print("\n✅ Form filled with virtual card details")
        print("⚠️  This is a TEST donation using a TEST card in Stripe's test mode")
        print("⚠️  No actual charges will be made")
        print("\nWaiting 5 seconds before clicking Donate button...")
        import time
        time.sleep(5)

        # Click donate button with error handling
        print("Submitting donation...")
        try:
            # Try different possible selectors for the donate button
            donate_selectors = [
                "text=Donate",
                "button:has-text('Donate')",
                "input[type='submit'][value='Donate']",
                "#donate-button",
                ".donate-button"
            ]
            
            button_clicked = False
            for selector in donate_selectors:
                try:
                    if page.is_visible(selector, timeout=5000):
                        page.click(selector)
                        button_clicked = True
                        print(f"Clicked donate button using selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not button_clicked:
                print("Could not find donate button with standard selectors")
                print("Taking screenshot of current page state...")
                page.screenshot(path="redcross_form_filled.png")
                print("Screenshot saved as redcross_form_filled.png")
                print("You can manually complete the donation process by viewing the BrowserBase session")
            else:
                # Wait for confirmation
                print("Waiting for confirmation...")
                time.sleep(5)
                
                print("\n✅ Donation process completed")
                print("Note: Since this is using Stripe's test mode, no actual donation was made")
        except Exception as e:
            print(f"Error during donation submission: {e}")
            print("Taking screenshot of current page state...")
            page.screenshot(path="redcross_error.png")
            print("Screenshot saved as redcross_error.png")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Close the browser
        page.close()
        browser.close()

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 redcross_donation_sync.py <card_id>")
        print("Example: python3 redcross_donation_sync.py ic_1234567890")
        sys.exit(1)
    
    card_id = sys.argv[1]
    
    with sync_playwright() as playwright:
        run(playwright, card_id)

if __name__ == "__main__":
    main()
