#!/usr/bin/env python3
from playwright.sync_api import Playwright, sync_playwright
from browserbase import Browserbase
from get_card_details import get_card as getCard
import os
import sys
import time
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
    print("✅ BrowserBase session created")

    try:
        # Navigate to the Stripe test payment page
        print("Navigating to Stripe test payment page...")
        page.goto("https://checkout.stripe.dev/preview")
        page.wait_for_load_state("networkidle")
        print("✅ Page loaded successfully")

        # Select a payment method
        print("Selecting card payment method...")
        page.wait_for_selector("text=Card", timeout=60000)
        page.click("text=Card")

        # Fill in the card information
        print("Filling card information...")
        try:
            # Wait for card fields to be available
            page.wait_for_selector("input[placeholder='1234 1234 1234 1234']", timeout=60000)
            
            # Fill card information
            page.fill("input[placeholder='1234 1234 1234 1234']", payment_info["card_number"])
            page.fill("input[placeholder='MM / YY']", f"{payment_info['expiration_month']}/{payment_info['expiration_year']}")
            page.fill("input[placeholder='CVC']", payment_info["cvc"])
            
            # Fill name field if available
            try:
                name_field = page.query_selector("input[placeholder='Name on card']") or page.query_selector("input[placeholder='Full name']")
                if name_field:
                    name_field.fill(f"{payment_info['cardholder_firstName']} {payment_info['cardholder_lastName']}")
            except Exception as e:
                print(f"Note: Could not fill name field: {e}")
            
            print("✅ Card information filled")
        except Exception as e:
            print(f"❌ Error filling card information: {e}")
            page.screenshot(path="stripe_test_error.png")
            print("Screenshot saved as stripe_test_error.png")
            return

        # Submit the payment
        print("\n✅ Form filled with virtual card details")
        print("⚠️  This is a TEST payment using a TEST card in Stripe's test mode")
        print("⚠️  No actual charges will be made")
        print("\nSubmitting payment...")
        
        # Try different possible selectors for the pay button
        pay_selectors = [
            "text=Pay",
            "button:has-text('Pay')",
            "button:has-text('Submit')",
            "button[type='submit']"
        ]
        
        button_clicked = False
        for selector in pay_selectors:
            try:
                if page.is_visible(selector, timeout=5000):
                    page.click(selector)
                    button_clicked = True
                    print(f"Clicked pay button using selector: {selector}")
                    break
            except Exception:
                continue
        
        if not button_clicked:
            print("❌ Could not find pay button with standard selectors")
            page.screenshot(path="stripe_test_form.png")
            print("Screenshot saved as stripe_test_form.png")
            return
        
        # Wait for confirmation
        print("Waiting for confirmation...")
        time.sleep(5)
        
        # Check for success message
        success_selectors = [
            "text=Payment successful",
            "text=Success",
            "text=Thank you",
            ".success",
            "#success"
        ]
        
        success_found = False
        for selector in success_selectors:
            try:
                if page.is_visible(selector, timeout=5000):
                    print(f"✅ Payment success confirmed! Found: {selector}")
                    success_found = True
                    break
            except Exception:
                continue
        
        if not success_found:
            print("⚠️  Could not confirm payment success message")
            print("Taking screenshot of current page state...")
            page.screenshot(path="stripe_test_result.png")
            print("Screenshot saved as stripe_test_result.png")
        
        print("\n✅ Test payment process completed")
        print("Note: Since this is using Stripe's test mode, no actual payment was made")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        try:
            page.screenshot(path="stripe_test_error.png")
            print("Screenshot saved as stripe_test_error.png")
        except:
            pass
    finally:
        # Close the browser
        page.close()
        browser.close()

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 stripe_test_payment.py <card_id>")
        print("Example: python3 stripe_test_payment.py ic_1RffUCLP54m13jvUESeDqzHz")
        sys.exit(1)
    
    card_id = sys.argv[1]
    
    with sync_playwright() as playwright:
        run(playwright, card_id)

if __name__ == "__main__":
    main()
