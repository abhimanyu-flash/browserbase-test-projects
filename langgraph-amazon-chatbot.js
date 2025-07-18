// langgraph-amazon-chatbot.js
// Main orchestrator for chatbot with order/cancel tools
require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const { spawn } = require('child_process');
const fetch = require('node-fetch');
const { createAgent, Tool } = require('langgraph');

const app = express();
const PORT = 4000;

app.use(bodyParser.json());
app.use(express.static('public'));

// --- TOOL WRAPPERS --- //

// Order tool: calls /login endpoint from amazonorder.js
async function orderProduct({ email, password, url }) {
  const res = await fetch('http://localhost:3000/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, productUrl: url })
  });
  const text = await res.text();
  return text;
}

// Cancel tool: spawns amazoncancel.js with product name
async function cancelProduct({ product }) {
  return new Promise((resolve, reject) => {
    const proc = spawn('node', ['amazoncancel.js', product], { cwd: __dirname });
    let output = '';
    proc.stdout.on('data', (data) => { output += data.toString(); });
    proc.stderr.on('data', (data) => { output += data.toString(); });
    proc.on('close', (code) => {
      if (code === 0) resolve(output);
      else reject(new Error(`Cancel script exited with code ${code}: ${output}`));
    });
  });
}

// LangGraph tools
const orderTool = new Tool({
  name: 'OrderProduct',
  description: 'Order an Amazon product given a URL',
  func: orderProduct
});

const cancelTool = new Tool({
  name: 'CancelProduct',
  description: 'Cancel an Amazon order by product name',
  func: cancelProduct
});

// --- INTENT DETECTION --- //
function detectIntent(message) {
  // Order intent: Amazon URL
  const urlMatch = message.match(/https?:\/\/(www\.)?amazon\.[a-z.]+\/[\w\-?=&#%]+/i);
  if (urlMatch) {
    return { intent: 'order', url: urlMatch[0] };
  }
  // Cancel intent: contains 'cancel' and a product name
  if (/cancel/i.test(message)) {
    // Extract product name after 'cancel'
    const prodMatch = message.match(/cancel\s+(my\s+order\s+for\s+)?(.+)/i);
    if (prodMatch && prodMatch[2]) {
      return { intent: 'cancel', product: prodMatch[2].trim() };
    }
    return { intent: 'cancel', product: '' };
  }
  return { intent: 'chat' };
}

// --- LANGGRAPH AGENT --- //
const agent = createAgent({
  tools: [orderTool, cancelTool],
  async handle({ input, context }) {
    const { intent, url, product } = detectIntent(input);
    if (intent === 'order') {
      // For demo: use hardcoded email/password, or prompt for them in production
      const email = process.env.AMAZON_EMAIL;
      const password = process.env.AMAZON_PASSWORD;
      const result = await orderTool.func({ email, password, url });
      return result;
    } else if (intent === 'cancel') {
      if (!product) return 'Please specify the product you want to cancel.';
      const result = await cancelTool.func({ product });
      return result;
    }
    // Default: small talk
    return "I'm your Amazon assistant. Send me a product link to order, or ask to cancel an order.";
  }
});

// --- API ENDPOINT --- //
app.post('/chat', async (req, res) => {
  const { message } = req.body;
  try {
    const response = await agent.run({ input: message });
    res.json({ response });
  } catch (err) {
    res.status(500).json({ response: 'Error: ' + err.message });
  }
});

app.listen(PORT, () => {
  console.log(`LangGraph Amazon Chatbot running at http://localhost:${PORT}`);
});
