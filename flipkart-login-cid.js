const fs = require("fs");
const path = require("path");
const express = require("express");
const { chromium } = require("playwright");
const { Browserbase } = require("@browserbasehq/sdk");
const fetch = (...args) => import("node-fetch").then(({ default: fetch }) => fetch(...args));
require("dotenv").config();

const app = express();
const PORT = 3000;

const CONTEXT_FILE = ".bb-flipkart-context-id";
const bb = new Browserbase({ apiKey: process.env.BROWSERBASE_API_KEY });
let session = null;

app.use(express.static(path.join(__dirname, "public")));

async function getOrCreateContext() {
  if (fs.existsSync(CONTEXT_FILE)) {
    const saved = fs.readFileSync(CONTEXT_FILE, "utf-8").trim();
    console.log("♻️ Reusing Flipkart context:", saved);
    return saved;
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
        locales: ["en-IN"],
        operatingSystems: ["windows"],
      },
      viewport: { width: 1366, height: 768 },
    },
    proxies: [
      {
        type: "browserbase",
        geolocation: { country: "IN", city: "DELHI" },
      },
    ],
  });
}

app.get("/start", async (req, res) => {
  try {
    const contextId = await getOrCreateContext();
    session = await createSession(contextId);

    const debugRes = await fetch(`https://www.browserbase.com/v1/sessions/${session.id}/debug`, {
      headers: { "X-BB-API-Key": process.env.BROWSERBASE_API_KEY },
    });
    const debugData = await debugRes.json();
    const liveUrl = debugData.debuggerFullscreenUrl;

    const browser = await chromium.connectOverCDP(session.connectUrl);
    const context = browser.contexts()[0];
    const page = context.pages()[0] || await context.newPage();
    await page.goto("https://www.flipkart.com/account/login", { waitUntil: "load" });

    console.log("🟢 Flipkart login page opened.");
    res.json({ liveUrl });
  } catch (err) {
    console.error("❌ Error:", err.message);
    res.status(500).json({ error: err.message });
  }
});

app.get("/continue", async (req, res) => {
  try {
    const browser = await chromium.connectOverCDP(session.connectUrl);
    const context = browser.contexts()[0];
    const page = context.pages()[0] || await context.newPage();

    await page.goto("https://www.flipkart.com/account/orders", { waitUntil: "load" });
    console.log("📦 Flipkart orders page opened (headless)");

    await page.screenshot({ path: "flipkart-orders.png", fullPage: true });
    console.log("📸 Screenshot saved: flipkart-orders.png");

    await browser.close();
    res.send("✅ Continued to Flipkart orders.");
  } catch (err) {
    console.error("❌ Continue error:", err.message);
    res.status(500).send("Error continuing.");
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Flipkart LiveView server running at http://localhost:${PORT}`);
});
