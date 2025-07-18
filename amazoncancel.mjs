import stagehandModule from "@browserbasehq/stagehand";
import dotenv from "dotenv";
import StagehandConfig from "./stagehand.config.mjs";
import fs from "fs";
import { Browserbase } from "@browserbasehq/sdk";
import { chromium } from "playwright";

dotenv.config();
const { Stagehand } = stagehandModule;
const bb = new Browserbase({ apiKey: process.env.BROWSERBASE_API_KEY });

async function main() {
  const args = process.argv.slice(2);
  const productName = args.join(" ").trim();

  if (!productName) {
    console.error("❌ No product name provided. Exiting.");
    process.exit(1);
  }
  console.log(`✅ Product name received: ${productName}`);

  // Try to load context ID from .amazon-context-id
  let contextId = null;
  const contextPath = ".amazon-context-id";
  if (fs.existsSync(contextPath)) {
    contextId = fs.readFileSync(contextPath, "utf-8").trim();
    console.log(`🔁 Using saved context ID: ${contextId}`);
  }

  // Launch Browserbase session with contextId and advanced stealth
  let session;
  if (contextId) {
    session = await bb.sessions.create({
      projectId: process.env.BROWSERBASE_PROJECT_ID,
      browserSettings: {
        context: { id: contextId, persist: true },
        advancedStealth: true,
        fingerprint: {
          devices: ["desktop"],
          locales: ["en-US"],
          operatingSystems: ["windows"],
        },
        viewport: { width: 1366, height: 768 },
      },
    });
    console.log("✅ Browserbase session created with context ID.");
  } else {
    // fallback: create new session without context (should rarely happen)
    session = await bb.sessions.create({
      projectId: process.env.BROWSERBASE_PROJECT_ID,
      browserSettings: {
        advancedStealth: true,
        fingerprint: {
          devices: ["desktop"],
          locales: ["en-US"],
          operatingSystems: ["windows"],
        },
        viewport: { width: 1366, height: 768 },
      },
    });
    console.log("✅ Browserbase session created without context ID.");
  }

  // Connect Playwright to Browserbase session
  const browser = await chromium.connectOverCDP(session.connectUrl);
  const context = browser.contexts()[0] || await browser.newContext();
  const page = context.pages()[0] || await context.newPage();

  // Pass Playwright page to Stagehand
  const stagehand = new Stagehand({ ...StagehandConfig, page });
  await stagehand.init();
  const agent = stagehand.agent();

  // Only login if contextId is not available
  if (!contextId) {
    console.log("\n===== OPENING AMAZON.IN =====");
    await page.goto("https://www.amazon.in");

    console.log("\n===== LOGGING IN =====");
    await agent.execute(`Find and click on the 'Sign in' link.`);
    await page.waitForSelector('input[name="email"]', { timeout: 10000 });
    await page.fill('input[name="email"]', 'abhimanyu.vasudev@gmail.com');
    await page.press('input[name="email"]', 'Enter');
    await page.waitForSelector('input[name="password"]', { timeout: 10000 });
    await page.fill('input[name="password"]', 'abhi@123');
    await page.press('input[name="password"]', 'Enter');

    const otpFieldSelector = 'input[name="otpCode"], input[name="otp"]';
    let otpFieldPresent = false;
    try {
      await page.waitForSelector(otpFieldSelector, { timeout: 8000 });
      otpFieldPresent = true;
      console.log("🔔 OTP field detected. Prompting for OTP...");
    } catch (e) {
      console.log("✅ No OTP field detected. Skipping OTP step.");
    }

    if (otpFieldPresent) {
      const readline = await import('readline');
      const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
      const otp = await new Promise((resolve) => rl.question("Enter the OTP: ", resolve));
      await page.fill(otpFieldSelector, otp);
      await page.press(otpFieldSelector, 'Enter');
      rl.close();
    }
  } else {
    // If context is reused, go directly to orders page
    console.log("\n===== REUSED CONTEXT: SKIPPING LOGIN =====");
    await page.goto("https://www.amazon.in/gp/your-account/order-history");
  }

  console.log("\n===== GOING TO ORDERS PAGE =====");
  await page.goto("https://www.amazon.in/gp/your-account/order-history");
  await page.waitForTimeout(5000);
  await page.waitForSelector('div.a-box-group.a-spacing-base', { timeout: 30000 });
  console.log("✅ Orders page loaded.");

  const orders = await page.$$('div.a-box-group.a-spacing-base');
  console.log(`✅ Found ${orders.length} orders.`);

  const searchTerm = productName.toLowerCase().replace(/[^a-z0-9 ]/g, '').split(' ').filter(Boolean);
  let targetOrder = null;

  for (let i = 0; i < orders.length; i++) {
    const order = orders[i];
    console.log(`\n🔍 Checking order ${i + 1}/${orders.length}...`);

    const productLink = await order.$('div.yohtmlc-product-title a.a-link-normal');
    const statusSpan = await order.$('div.yohtmlc-shipment-status-primaryText h3 span.delivery-box__primary-text');
    const orderIDSpan = await order.$('div.yohtmlc-order-id span.a-color-secondary[dir="ltr"]');

    let productText = productLink ? (await productLink.textContent()).trim().toLowerCase().replace(/[^a-z0-9 ]/g, '') : "";
    let statusText = statusSpan ? (await statusSpan.textContent()).trim().toLowerCase() : "";
    let orderID = orderIDSpan ? (await orderIDSpan.textContent()).trim() : "";

    console.log(`📦 Product: ${productText}`);
    console.log(`📦 Status: ${statusText}`);
    console.log(`📦 Order ID: ${orderID}`);

    const productWords = productText.split(' ').filter(Boolean);
    const commonWords = searchTerm.filter(word => productWords.includes(word));
    const matchScore = commonWords.length;

    if (matchScore >= 3 && orderID) {
      targetOrder = order;
      console.log(`✅ Matched order for '${productName}'`);

      if (statusText.includes("cancelled")) {
        console.log(`ℹ️ The order for '${productName}' is already cancelled.`);
      } else {
        const orderURL = `https://www.amazon.in/gp/your-account/order-details?orderID=${orderID}`;
        console.log(`➡️ Navigating directly to: ${orderURL}`);
        await page.goto(orderURL);
        await page.waitForTimeout(5000);
        console.log("✅ Order details page loaded.");

        console.log("✅ Attempting cancellation...");
        await agent.execute(`Click Cancel Items or Cancel Order, then confirm.`);
        console.log(`✅ The order for '${productName}' has been cancelled.`);
      }

      break;
    }
  }

  if (!targetOrder) {
    console.log(`❌ No order found for '${productName}'.`);
  }

  await stagehand.close();
}

main().catch((err) => {
  console.error("❌ Error in main:", err);
});
