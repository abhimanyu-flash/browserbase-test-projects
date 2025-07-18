# Stripe Virtual Card Generator and Form Filler

**IMPORTANT: This project runs in TEST MODE ONLY and will not make any real charges.**

This project allows you to create virtual cards using Stripe's Issuing API and automatically fill payment forms with the virtual card details.

## Features

- Create Stripe cardholders
- Generate virtual cards with customizable spending limits
- Retrieve virtual card details (card number, expiry, CVV)
- Automatically fill payment forms using virtual card information
- AI-powered form field detection and filling

## Prerequisites

- Python 3.7+
- Stripe API key
- BrowserBase API key (for advanced form filling)
- OpenAI API key (for AI-powered form detection)

## Setup

1. Make sure you have all required API keys in your `.env` file:

```
STRIPE_API_KEY=your_stripe_api_key
BROWSERBASE_API_KEY=your_browserbase_api_key
BROWSERBASE_PROJECT_ID=your_browserbase_project_id
OPENAI_API_KEY=your_openai_api_key
```

2. Install required dependencies:

```bash
python -m pip install stripe python-dotenv playwright langchain-openai
```

3. Install Playwright browsers:

```bash
python -m playwright install
```

## Usage

### Creating a Cardholder

To create a new cardholder in Stripe:

```bash
python formfiller.py --create-cardholder
```

The URL parameter is now optional when creating a cardholder.

This will output a cardholder ID that you'll need for the next step.

### Creating a Virtual Card

To create a virtual card for a cardholder:

```bash
python formfiller.py --create-card ic_cardholder_id
```

Replace `ic_cardholder_id` with the actual cardholder ID from the previous step. The URL parameter is optional when creating a virtual card.

### Filling a Form with Virtual Card

To fill a form using a virtual card:

```bash
python formfiller.py --use-card ic_card_id https://example.com/payment-form
```

Replace `ic_card_id` with the actual card ID from the previous step and provide the URL of the payment form you want to fill.

### Making a Red Cross Donation (BrowserBase Example)

To make a donation to Red Cross using a virtual card and BrowserBase:

```bash
python3 redcross_donation.py ic_card_id
```

Replace `ic_card_id` with the actual card ID from the virtual card creation step. This script follows the BrowserBase documentation example and will:

1. Retrieve the virtual card details from Stripe
2. Open a BrowserBase session with the Red Cross donation page
3. Select a $75 donation amount
4. Fill in all billing and payment information using the virtual card
5. Wait 10 seconds before submitting (giving you time to review)
6. Submit the donation form

**Note:** Since this uses Stripe's test mode, no actual donation will be made.

### Using Default Payment Information

To fill a form with the default payment information (without creating a virtual card):

```bash
python formfiller.py https://example.com/payment-form
```

## Important Notes

- Virtual cards have a default spending limit of $75.00 USD per day
- The form filler will wait for 30 seconds after filling the form to allow manual review before submission
- You need a valid Stripe API key with access to the Issuing API
- This implementation is based on the BrowserBase documentation for Stripe integration

## Files

- `formfiller.py` - Main script with all functionality
- `create_cardholder.py` - Standalone script for creating cardholders
- `create_virtual_card.py` - Standalone script for creating virtual cards
- `get_card_details.py` - Standalone script for retrieving card details

## Test Mode

This application is designed to work **ONLY** with Stripe's test mode. The code includes validation to ensure that:

1. You're using a test API key (starts with `sk_test_`)
2. No real charges will ever be made
3. All virtual cards created are test cards

To get a Stripe test API key:
1. Sign up for a Stripe account if you don't have one
2. Go to the [Stripe Dashboard](https://dashboard.stripe.com/test/apikeys)
3. Make sure you're in test mode (indicated by the "Test Mode" badge)
4. Copy your test secret key (starts with `sk_test_`)
5. Add it to your `.env` file

## Security

- Card details are masked when displayed in the console
- API keys should be kept secure in the `.env` file
- Virtual cards have spending controls to limit potential fraud
- The application will refuse to run with production API keys
# browserbase-test-projects
