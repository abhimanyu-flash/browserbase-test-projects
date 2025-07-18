import express from "express";
import { config } from "dotenv";
import { Browserbase } from "@browserbasehq/sdk";
import fs from "fs";
import fetch from "node-fetch";
import path from "path";
import { fileURLToPath } from "url";
import { cancelAmazonOrder, checkContextStatus } from "./amazoncancel.js";
import { chromium } from "playwright";

config();
const app = express();
const port = 3000;

app.use(express.json());

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
app.use(express.static(__dirname));

const CONTEXT_FILE = ".bb-context-id";
const bb = new Browserbase({ apiKey: process.env.BROWSERBASE_API_KEY });

let cachedSession = null;
let cachedPage = null;
let cachedBrowser = null;

async function getOrCreateContext() {
  if (fs.existsSync(CONTEXT_FILE)) {
    const saved = fs.readFileSync(CONTEXT_FILE, "utf-8").trim();
    console.log(" Reusing context:", saved);
    return saved;
  }

  const context = await bb.contexts.create({
    projectId: process.env.BROWSERBASE_PROJECT_ID,
    advancedStealth: true,
    persist: true,
  });

  fs.writeFileSync(CONTEXT_FILE, context.id);
  console.log(" Created new context:", context.id);
  return context.id;
}

app.get("/login", async (req, res) => {
  try {
    const contextId = await getOrCreateContext();

    cachedSession = await bb.sessions.create({
      projectId: process.env.BROWSERBASE_PROJECT_ID,
      browserSettings: {
        context: { id: contextId, persist: true },
        advancedStealth: true,
        fingerprint: {
          devices: ["mobile"],
          locales: ["en-US"],
          operatingSystems: ["android"],
        },
        viewport: {
          width: 360,
          height: 800,
        },
      },
    });

    cachedBrowser = await chromium.connectOverCDP(cachedSession.connectUrl);
    const context = cachedBrowser.contexts()[0];
    cachedPage = context.pages()[0] || await context.newPage();

    await cachedPage.goto("https://www.amazon.in", { waitUntil: "load", timeout: 60000 });

    const debugRes = await fetch(`https://www.browserbase.com/v1/sessions/${cachedSession.id}/debug`, {
      headers: { "X-BB-API-Key": process.env.BROWSERBASE_API_KEY },
    });
    const debugData = await debugRes.json();
    if (!debugData.debuggerFullscreenUrl) throw new Error("No Live View URL found");

    setTimeout(() => {
      const interval = setInterval(async () => {
        try {
          const isLoggedIn = await cachedPage.evaluate(() => {
            return !document.body.innerText.toLowerCase().includes("sign in");
          });

          console.log(" Login status:", isLoggedIn);
          if (isLoggedIn) {
            console.log(" Login detected. Stopping poll.");
            clearInterval(interval);
            await cachedBrowser.close();
            cachedBrowser = null;
            cachedSession = null;
            cachedPage = null;
          }
        } catch (e) {
          console.error("Polling error:", e.message);
        }
      }, 3000);
    }, 20000);

    return res.json({
      success: true,
      liveViewUrl: debugData.debuggerFullscreenUrl,
      sessionId: cachedSession.id,
      contextId,
    });
  } catch (err) {
    console.error(" Login error:", err);
    res.status(500).json({ success: false, error: err.message });
  }
});

app.get("/login-status", async (req, res) => {
  try {
    if (!cachedPage) throw new Error("No active session or page available");

    const isLoggedIn = await cachedPage.evaluate(() => {
      return !document.body.innerText.toLowerCase().includes("sign in");
    });

    // Get contextId from file
    let contextId = null;
    if (fs.existsSync(CONTEXT_FILE)) {
      contextId = fs.readFileSync(CONTEXT_FILE, "utf-8").trim();
    }

    res.json({ success: true, loggedIn: isLoggedIn, contextId });
  } catch (err) {
    console.error(" Login-status error:", err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

// Keep the old endpoint for backward compatibility
app.get("/check-login", async (req, res) => {
  try {
    if (!cachedPage) throw new Error("No active session or page available");

    const isLoggedIn = await cachedPage.evaluate(() => {
      return !document.body.innerText.toLowerCase().includes("sign in");
    });

    res.json({ success: true, loggedIn: isLoggedIn });
  } catch (err) {
    console.error(" Check-login error:", err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

// New endpoint to check if context exists
app.post("/check-context", async (req, res) => {
  try {
    const { contextId } = req.body;
    if (!contextId) {
      return res.json({ exists: false, error: "Missing contextId" });
    }

    // Check if the context file actually exists on the server
    if (fs.existsSync(CONTEXT_FILE)) {
      const savedContextId = fs.readFileSync(CONTEXT_FILE, "utf-8").trim();
      if (savedContextId !== contextId) {
        console.log(` Context ID mismatch: requested=${contextId}, saved=${savedContextId}`);
        return res.json({ exists: false, error: "Context ID does not match server" });
      }
    } else {
      console.log(` Context file does not exist on server`);
      return res.json({ exists: false, error: "Context file not found" });
    }

    // Still verify with Browserbase if needed
    const result = await checkContextStatus(contextId);
    return res.json(result);
  } catch (err) {
    console.error(" Check-context error:", err.message);
    return res.status(500).json({ exists: false, error: err.message });
  }
});

app.post("/cancel-order", async (req, res) => {
  const { orderId, contextId } = req.body;
  if (!orderId) return res.status(400).json({ success: false, error: "Missing orderId" });

  try {
    // Use provided contextId if available, otherwise get or create one
    const useContextId = contextId || await getOrCreateContext();
    const result = await cancelAmazonOrder(orderId, useContextId);
    
    // Return the result as-is without overriding the success property
    return res.json(result);
  } catch (err) {
    console.error(" Cancel error:", err);
    return res.status(500).json({ success: false, error: err.message });
  }
});

app.listen(port, () => {
  console.log(` Server ready at http://localhost:${port}`);
});
