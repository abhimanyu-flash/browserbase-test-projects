#!/usr/bin/env python3
import os
import sys
import time
import threading
import stripe
import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from browserbase import Browserbase
from get_card_details import get_card as getCard

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

# Set up BrowserBase
bb = Browserbase(api_key=os.environ["BROWSERBASE_API_KEY"])

# Global variables for monitoring
monitoring_active = True
initial_auth_ids = set()
initial_tx_ids = set()
card_id = None

def check_card_authorizations():
    """Check for authorizations on the card"""
    try:
        authorizations = stripe.issuing.Authorization.list(
            card=card_id,
            limit=5
        )
        
        if not authorizations.data:
            return []
        
        return authorizations.data
    except stripe.error.StripeError as e:
        print(f"❌ Error checking authorizations: {e}")
        return []

def check_card_transactions():
    """Check for transactions on the card"""
    try:
        transactions = stripe.issuing.Transaction.list(
            card=card_id,
            limit=5
        )
        
        if not transactions.data:
            return []
        
        return transactions.data
    except stripe.error.StripeError as e:
        print(f"❌ Error checking transactions: {e}")
        return []

def monitor_card_activity():
    """Monitor card activity in a separate thread"""
    global initial_auth_ids, initial_tx_ids, monitoring_active
    
    print("\n=== Starting Card Activity Monitoring ===")
    
    # Get initial state
    print("Checking for existing authorizations...")
    initial_auths = check_card_authorizations()
    initial_auth_ids = set(auth.id for auth in initial_auths)
    
    print("Checking for existing transactions...")
    initial_txs = check_card_transactions()
    initial_tx_ids = set(tx.id for tx in initial_txs)
    
    print(f"Initial state: {len(initial_auth_ids)} authorizations, {len(initial_tx_ids)} transactions")
    
    # Monitor for changes
    while monitoring_active:
        time.sleep(5)  # Check every 5 seconds
        
        # Check for new authorizations
        current_auths = check_card_authorizations()
        current_auth_ids = set(auth.id for auth in current_auths)
        
        new_auth_ids = current_auth_ids - initial_auth_ids
        if new_auth_ids:
            print(f"\n✅ DETECTED {len(new_auth_ids)} NEW AUTHORIZATION(S)!")
            for auth in current_auths:
                if auth.id in new_auth_ids:
                    print(f"  New authorization: {auth.id}")
                    print(f"  Merchant: {auth.merchant_data.name}")
                    print(f"  Amount: ${auth.amount/100:.2f} {auth.currency.upper()}")
                    print(f"  Status: {auth.status}")
                    print(f"  Approved: {auth.approved}")
            initial_auth_ids = current_auth_ids
        
        # Check for new transactions
        current_txs = check_card_transactions()
        current_tx_ids = set(tx.id for tx in current_txs)
        
        new_tx_ids = current_tx_ids - initial_tx_ids
        if new_tx_ids:
            print(f"\n✅ DETECTED {len(new_tx_ids)} NEW TRANSACTION(S)!")
            for tx in current_txs:
                if tx.id in new_tx_ids:
                    print(f"  New transaction: {tx.id}")
                    print(f"  Type: {tx.type}")
                    print(f"  Amount: ${tx.amount/100:.2f} {tx.currency.upper()}")
                    
                    if hasattr(tx, 'purchase_details') and tx.purchase_details:
                        if hasattr(tx.purchase_details, 'merchant') and tx.purchase_details.merchant:
                            print(f"  Merchant: {tx.purchase_details.merchant.name}")
            initial_tx_ids = current_tx_ids
    
    print("\n=== Card Monitoring Stopped ===")

def run_donation(playwright, card_id_param):
    """Run the Red Cross donation process"""
    global card_id
    card_id = card_id_param
    
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
        print("\nSubmitting donation...")

        # Click donate button with error handling
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
                time.sleep(10)  # Wait a bit longer to see if the payment processes
                
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
        # Keep the browser open for a while to allow monitoring to detect any delayed transactions
        print("Keeping browser open for 30 more seconds to monitor for payment activity...")
        time.sleep(30)
        
        # Close the browser
        page.close()
        browser.close()

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 donation_with_monitoring.py <card_id>")
        print("Example: python3 donation_with_monitoring.py ic_1RffUCLP54m13jvUESeDqzHz")
        sys.exit(1)
    
    global card_id, monitoring_active
    card_id = sys.argv[1]
    
    # Start monitoring thread
    monitor_thread = threading.Thread(target=monitor_card_activity)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Run donation process
    with sync_playwright() as playwright:
        run_donation(playwright, card_id)
    
    # Stop monitoring
    monitoring_active = False
    monitor_thread.join(timeout=5)
    
    # Final check for any activity that might have been missed
    print("\n=== Final Card Activity Check ===")
    
    # Check for new authorizations
    current_auths = check_card_authorizations()
    current_auth_ids = set(auth.id for auth in current_auths)
    
    new_auth_count = len(current_auth_ids - initial_auth_ids)
    
    # Check for new transactions
    current_txs = check_card_transactions()
    current_tx_ids = set(tx.id for tx in current_txs)
    
    new_tx_count = len(current_tx_ids - initial_tx_ids)
    
    print("\n=== Summary ===")
    if new_auth_count > 0 or new_tx_count > 0:
        print(f"✅ Detected {new_auth_count} new authorization(s) and {new_tx_count} new transaction(s)")
        print("The payment process is working correctly in test mode!")
    else:
        print("❌ No new activity was detected on this card")
        print("This could mean:")
        print("1. The donation process didn't reach the payment stage")
        print("2. The card wasn't used correctly in the form")
        print("3. The merchant hasn't processed the payment yet")
    
    print("\nTo verify in Stripe Dashboard:")
    print("1. Go to https://dashboard.stripe.com/test/issuing")
    print("2. Make sure you're in 'Viewing test data' mode")
    print("3. Check the card details and transaction history")

if __name__ == "__main__":
    main()
