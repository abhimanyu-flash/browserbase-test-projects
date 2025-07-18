#!/usr/bin/env python3
import os
import stripe
import sys
import datetime
from dotenv import load_dotenv
import time

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

def get_card_details(card_id):
    """Get basic details about the card"""
    try:
        card = stripe.issuing.Card.retrieve(card_id)
        print(f"Card: {card.id}")
        print(f"Last 4: {card.last4}")
        print(f"Brand: {card.brand}")
        print(f"Status: {card.status}")
        return card
    except stripe.error.StripeError as e:
        print(f"❌ Error retrieving card: {e}")
        return None

def check_card_authorizations(card_id):
    """Check for authorizations on the card"""
    try:
        authorizations = stripe.issuing.Authorization.list(
            card=card_id,
            limit=5
        )
        
        if not authorizations.data:
            print("No authorizations found for this card")
            return []
        
        print(f"Found {len(authorizations.data)} authorization(s):")
        
        for i, auth in enumerate(authorizations.data):
            print(f"\nAuthorization #{i+1}:")
            print(f"  ID: {auth.id}")
            print(f"  Created: {datetime.datetime.fromtimestamp(auth.created)}")
            print(f"  Merchant: {auth.merchant_data.name}")
            print(f"  Amount: ${auth.amount/100:.2f} {auth.currency.upper()}")
            print(f"  Status: {auth.status}")
            print(f"  Approved: {auth.approved}")
            
        return authorizations.data
    except stripe.error.StripeError as e:
        print(f"❌ Error checking authorizations: {e}")
        return []

def check_card_transactions(card_id):
    """Check for transactions on the card"""
    try:
        transactions = stripe.issuing.Transaction.list(
            card=card_id,
            limit=5
        )
        
        if not transactions.data:
            print("No transactions found for this card")
            return []
        
        print(f"Found {len(transactions.data)} transaction(s):")
        
        for i, tx in enumerate(transactions.data):
            print(f"\nTransaction #{i+1}:")
            print(f"  ID: {tx.id}")
            print(f"  Created: {datetime.datetime.fromtimestamp(tx.created)}")
            print(f"  Type: {tx.type}")
            print(f"  Amount: ${tx.amount/100:.2f} {tx.currency.upper()}")
            
            if hasattr(tx, 'purchase_details') and tx.purchase_details:
                if hasattr(tx.purchase_details, 'merchant') and tx.purchase_details.merchant:
                    print(f"  Merchant: {tx.purchase_details.merchant.name}")
            
        return transactions.data
    except stripe.error.StripeError as e:
        print(f"❌ Error checking transactions: {e}")
        return []

def monitor_card_activity(card_id, interval=10, duration=60):
    """
    Monitor card activity for a specified duration
    
    Args:
        card_id: The Stripe issuing card ID
        interval: Check interval in seconds
        duration: Total monitoring duration in seconds
    """
    print(f"Starting to monitor activity for card {card_id}")
    print(f"Will check every {interval} seconds for {duration} seconds total")
    print("Press Ctrl+C to stop monitoring\n")
    
    card = get_card_details(card_id)
    if not card:
        return
    
    print("\n=== Initial Card State ===")
    print("Checking for existing authorizations...")
    initial_auths = check_card_authorizations(card_id)
    initial_auth_ids = set(auth.id for auth in initial_auths)
    
    print("\nChecking for existing transactions...")
    initial_txs = check_card_transactions(card_id)
    initial_tx_ids = set(tx.id for tx in initial_txs)
    
    print("\n=== Starting Monitoring ===")
    print("Run the Red Cross donation script in another terminal.")
    print("This script will detect any new activity on the card.")
    
    start_time = time.time()
    try:
        while time.time() - start_time < duration:
            time.sleep(interval)
            
            print(f"\n=== Checking at {datetime.datetime.now().strftime('%H:%M:%S')} ===")
            
            # Check for new authorizations
            print("Checking for new authorizations...")
            current_auths = check_card_authorizations(card_id)
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
            else:
                print("No new authorizations detected")
            
            # Check for new transactions
            print("\nChecking for new transactions...")
            current_txs = check_card_transactions(card_id)
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
            else:
                print("No new transactions detected")
            
            remaining = duration - (time.time() - start_time)
            print(f"\nMonitoring will continue for approximately {int(remaining)} more seconds")
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    
    print("\n=== Monitoring Complete ===")
    print("Summary:")
    
    new_auth_count = len(current_auth_ids) - len(initial_auth_ids)
    new_tx_count = len(current_tx_ids) - len(initial_tx_ids)
    
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
    if len(sys.argv) < 2:
        print("Usage: python3 monitor_card_activity.py <card_id> [duration_seconds] [interval_seconds]")
        print("Example: python3 monitor_card_activity.py ic_1RffUCLP54m13jvUESeDqzHz 120 5")
        sys.exit(1)
    
    card_id = sys.argv[1]
    
    duration = 120  # Default: monitor for 2 minutes
    if len(sys.argv) >= 3:
        duration = int(sys.argv[2])
    
    interval = 10  # Default: check every 10 seconds
    if len(sys.argv) >= 4:
        interval = int(sys.argv[3])
    
    monitor_card_activity(card_id, interval, duration)
