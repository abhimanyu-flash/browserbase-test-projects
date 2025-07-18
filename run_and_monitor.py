#!/usr/bin/env python3
import os
import sys
import time
import threading
import stripe
import subprocess
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

# Global variables
card_id = None
monitoring_active = True
initial_auth_ids = set()
initial_tx_ids = set()

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

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 run_and_monitor.py <card_id>")
        print("Example: python3 run_and_monitor.py ic_1RffUCLP54m13jvUESeDqzHz")
        sys.exit(1)
    
    global card_id, monitoring_active
    card_id = sys.argv[1]
    
    # Start monitoring thread
    monitor_thread = threading.Thread(target=monitor_card_activity)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Run the existing Red Cross donation script
    print("\n=== Running Red Cross Donation Script ===")
    try:
        subprocess.run([sys.executable, "browserbase_redcross.py", card_id], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running donation script: {e}")
    
    # Keep monitoring for a bit longer to catch any delayed transactions
    print("\n=== Continuing to monitor for 30 more seconds ===")
    time.sleep(30)
    
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
