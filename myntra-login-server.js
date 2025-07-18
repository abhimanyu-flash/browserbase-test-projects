/*
const fs = require("fs");
const path = require("path");
const express = require("express");
const { chromium } = require("playwright");
const { Browserbase } = require("@browserbasehq/sdk");

const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));


require("dotenv").config(); // Defaults to .env in the same dir
console.log("✅ API Key:", process.env.BROWSERBASE_API_KEY);
console.log("✅ Project ID:", process.env.BROWSERBASE_PROJECT_ID);


const app = express();
const PORT = 3000;

const bb = new Browserbase({ apiKey: process.env.BROWSERBASE_API_KEY });
const CONTEXT_FILE = ".bb-context-id";

// Serve frontend from public/
app.use(express.static(path.join(__dirname, "public")));

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

async function getLiveViewUrl(sessionId) {
  const res = await fetch(`https://www.browserbase.com/v1/sessions/${sessionId}/debug`, {
    headers: { "X-BB-API-Key": process.env.BROWSERBASE_API_KEY },
  });
  const data = await res.json();
  return data.debuggerFullscreenUrl;
}

app.get("/start", async (req, res) => {
  try {
    const contextId = await getOrCreateContext();
    const session = await createSession(contextId);
    const liveUrl = await getLiveViewUrl(session.id);

    const browser = await chromium.connectOverCDP(session.connectUrl);
    const context = browser.contexts()[0];
    const page = context.pages()[0] || await context.newPage();

    await page.goto("https://www.myntra.com/login", { waitUntil: "load" });
    console.log("🟢 Myntra login page opened.");

    res.json({ liveUrl });
  } catch (err) {
    console.error("❌ Error:", err.message);
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Server running at http://localhost:${PORT}`);
});
*/

// server.js
const fs = require("fs");
const path = require("path");
const express = require("express");
const { chromium } = require("playwright");
const { Browserbase } = require("@browserbasehq/sdk");
const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));

require("dotenv").config();

const app = express();
const PORT = 3000;

const bb = new Browserbase({ apiKey: process.env.BROWSERBASE_API_KEY });
const CONTEXT_FILE = ".bb-context-id";

app.use(express.static(path.join(__dirname, "public")));
app.use(express.json());

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

async function getLiveViewUrl(sessionId) {
  const res = await fetch(`https://www.browserbase.com/v1/sessions/${sessionId}/debug`, {
    headers: { "X-BB-API-Key": process.env.BROWSERBASE_API_KEY },
  });
  const data = await res.json();
  return data.debuggerFullscreenUrl;
}

app.get("/start", async (req, res) => {
  try {
    const contextId = await getOrCreateContext();
    const session = await createSession(contextId);
    const liveUrl = await getLiveViewUrl(session.id);

    const browser = await chromium.connectOverCDP(session.connectUrl);
    const context = browser.contexts()[0];
    const page = context.pages()[0] || await context.newPage();

    await page.goto("https://www.myntra.com/login", { waitUntil: "load" });
    console.log("🟢 Myntra login page opened.");

    res.json({ liveUrl });
  } catch (err) {
    console.error("❌ Error:", err.message);
    res.status(500).json({ error: err.message });
  }
});

app.post("/cancel-order", async (req, res) => {
  try {
    const contextId = await getOrCreateContext();
    const session = await createSession(contextId);
    const browser = await chromium.connectOverCDP(session.connectUrl);

    const context = browser.contexts()[0];
    const page = context.pages()[0] || await context.newPage();

    await page.goto("https://www.myntra.com/my/orders", { waitUntil: "load" });
    console.log("📦 Navigated to orders page.");

    await page.screenshot({ path: `myntra-orders.png`, fullPage: true });
    await browser.close();

    res.json({ success: true, message: "Visited Myntra orders page" });
  } catch (err) {
    console.error("❌ Error:", err.message);
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Server running at http://localhost:${PORT}`);
});
