require("dotenv").config();
const express = require("express");
const fs = require("fs");
const path = require("path");
const bodyParser = require("body-parser");
const { chromium } = require("playwright");
const { Browserbase } = require("@browserbasehq/sdk");

const app = express();
const PORT = 3000;
const CONTEXT_FILE = ".amazon-context-id";
const bb = new Browserbase({ apiKey: process.env.BROWSERBASE_API_KEY });

app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json()); // <-- Add this line to support JSON
app.use(express.static("public"));

// Serve the login page
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

async function getOrCreateContext() {
  if (fs.existsSync(CONTEXT_FILE)) {
    const savedId = fs.readFileSync(CONTEXT_FILE, "utf-8").trim();
    console.log("🔁 Reusing context:", savedId);
    return savedId;
  }

  const context = await bb.contexts.create({
    projectId: process.env.BROWSERBASE_PROJECT_ID,
    stealth: true,
  });

  fs.writeFileSync(CONTEXT_FILE, context.id);
  console.log("✅ New context created:", context.id);
  return context.id;
}

async function createSession(contextId) {
  return await bb.sessions.create({
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
}

app.post("/login", async (req, res) => {
  const { email, password, productUrl } = req.body;

  try {
    const contextId = await getOrCreateContext();
    const session = await createSession(contextId);

    const browser = await chromium.connectOverCDP(session.connectUrl);
    const context = browser.contexts()[0] || await browser.newContext();
    const page = context.pages()[0] || await context.newPage();

    if (!fs.existsSync(CONTEXT_FILE)) {
      // Fresh login if no context saved (this block won't run in reuse mode)
      await page.goto("https://www.amazon.com");
      await page.click("#nav-link-accountList a.nav-a");
      await page.waitForLoadState("networkidle");

      await page.fill("#ap_email_login", email);
      await page.click("input.a-button-input");

      await page.waitForSelector("#ap_password", { timeout: 10000 });
      await page.fill("#ap_password", password);
      await page.click("input#signInSubmit");
      await page.waitForLoadState("networkidle");

      const storageStatePath = path.join(__dirname, "context.json");
      await context.storageState({ path: storageStatePath });
    }

    // Navigate to product page and continue order
    await page.goto(productUrl);
    await page.waitForLoadState("networkidle");

    await page.waitForSelector("input#buy-now-button", { timeout: 10000 });
    await page.click("input#buy-now-button");

    await page.waitForSelector("a.pmts-add-cc-default-trigger-link", { timeout: 10000 });
    await page.click("a.pmts-add-cc-default-trigger-link");
    await page.fill("a-input-text a-form-normal pmts-account-Number", "123456789012");
    await page.fill("a-input-text a-form-normal apx-add-credit-card-account-holder-name-input mcx-input-fields", "Abhimanyu Vasudev");
    await page.fill("a-button-text a-declarative", "02");
    await page.fill("a-input-text a-form-normal a-width-small", "012")
    res.send("✅ Using saved session. Buy Now clicked and Add Card page opened.");
  } catch (err) {
    console.error(err);
    res.status(500).send("❌ Login or automation failed: " + err.message);
  }
});
app.get("/context", (req, res) => {
  const hasContext = fs.existsSync(CONTEXT_FILE);
  res.json({ hasContext });
});

app.listen(PORT, () => {
  console.log(`🚀 Server running at http://localhost:${PORT}`);
});
