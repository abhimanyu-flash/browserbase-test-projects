import { config } from "dotenv";
import fs from "fs";
import path from "path";
import { Browserbase } from "@browserbasehq/sdk";
import { chromium } from "playwright";

config();

const SCREENSHOTS_DIR = "screenshots";
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR);
}

export async function cancelAmazonOrder(orderId, contextId) {
  let browser;
  const bb = new Browserbase({ apiKey: process.env.BROWSERBASE_API_KEY });

  try {
    // Check if we have a valid contextId before creating a new session
    if (!contextId) {
      throw new Error("No contextId provided. User needs to login first.");
    }

    const session = await bb.sessions.create({
      projectId: process.env.BROWSERBASE_PROJECT_ID,
      browserSettings: {
        context: { id: contextId, persist: true },
        advancedStealth: true,
        fingerprint: {
          devices: ["desktop"],
          locales: ["en-US"],
          operatingSystems: ["windows"]
        },
        viewport: {
          width: 1280,
          height: 720
        }
      }
    });

    browser = await chromium.connectOverCDP(session.connectUrl);
    const page = (await browser.contexts())[0].pages()[0] || await (await browser.contexts())[0].newPage();

    const orderUrl = `https://www.amazon.in/gp/your-account/order-details?orderID=${orderId}`;
    console.log(`[${new Date().toISOString()}] Navigating to order page: ${orderUrl}`);
    await page.goto(orderUrl, { waitUntil: "load", timeout: 60000 });

    const screenshotPath = path.join(SCREENSHOTS_DIR, `order-${orderId}-loaded.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`[${new Date().toISOString()}] 📸 Screenshot saved: ${screenshotPath}`);

    // Check if the page indicates that the order doesn't exist
    const orderNotFound = await page.evaluate(() => {
      const pageText = document.body.innerText || '';
      return pageText.includes("We couldn't find that order") || 
             pageText.includes("Order not found") ||
             pageText.includes("Hmm, we couldn't find that order") ||
             pageText.includes("Sorry, we couldn't find an order matching") ||
             pageText.includes("Sorry, we couldn't find an order") ||
             pageText.includes("No order found") ||
             pageText.includes("Looking for something?") || 
             pageText.includes("check the spelling of your search term");
    });

    console.log(`[${new Date().toISOString()}] Order not found check result: ${orderNotFound}`);
    
    // Take a screenshot of what we're seeing for debugging
    const orderValidationScreenshot = path.join(SCREENSHOTS_DIR, `order-${orderId}-validation.png`);
    await page.screenshot({ path: orderValidationScreenshot });
    
    if (orderNotFound) {
      console.log(`[${new Date().toISOString()}] ❌ Order not found: ${orderId}`);
      return {
        success: false,
        status: 'order_not_found',
        statusMessage: 'Order ID is invalid or could not be found',
        screenshot: screenshotPath,
        contextId,
        timestamp: new Date().toISOString(),
      };
    }
    
    // Additional check: Look for recognizable Amazon order elements
    const isValidOrderPage = await page.evaluate(() => {
      // Check for order details elements that should be present on a valid order page
      const orderDetailsElement = document.querySelector('.order-date-invoice-item') || 
                                  document.querySelector('.order-details') ||
                                  document.querySelector('.order-header') ||
                                  document.querySelector('.order-summary');
      
      return !!orderDetailsElement;
    });
    
    console.log(`[${new Date().toISOString()}] Valid order page check result: ${isValidOrderPage}`);
    
    if (!isValidOrderPage) {
      console.log(`[${new Date().toISOString()}] ❌ Not a valid order page for: ${orderId}`);
      return {
        success: false,
        status: 'invalid_order',
        statusMessage: 'This does not appear to be a valid Amazon order',
        screenshot: screenshotPath,
        contextId,
        timestamp: new Date().toISOString(),
      };
    }

    let status = "unknown";
    let statusMessage = "Status not determined";

    const cancelledText = await page.evaluate(() => {
      const alertElement = document.querySelector('div.a-alert-container h4.a-alert-heading');
      return alertElement?.textContent?.toLowerCase().includes('cancelled') ? 'cancelled' : null;
    });

    if (cancelledText) {
      status = 'already_cancelled';
      statusMessage = 'Order is already cancelled';
      return {
        success: false,
        status,
        statusMessage,
        screenshot: screenshotPath,
        contextId,
        timestamp: new Date().toISOString(),
      };
    } else {
      const cancelButton = await page.locator(
        'a:has-text("Cancel items"), a:has-text("Cancel Order"), input[name="cancelItemButton"]'
      ).first();

      if (await cancelButton.count() > 0) {
        console.log(`[${new Date().toISOString()}] Found cancel button. Clicking...`);
        await cancelButton.click({ timeout: 10000 });

        try {
          // Wait for the confirmation button to appear
          const requestButton = page.locator('input[name="cq.submit"]');
          const hasRequestButton = await requestButton.waitFor({ timeout: 15000 })
            .then(() => true)
            .catch(() => false);
            
          if (!hasRequestButton) {
            return {
              success: false,
              status: 'no_confirmation_button',
              statusMessage: 'Could not find the confirmation button for cancellation',
              screenshot: screenshotPath,
              contextId,
              timestamp: new Date().toISOString(),
            };
          }
          
          console.log(`[${new Date().toISOString()}] 🔘 Found 'Request Cancellation' button`);

          await page.screenshot({ path: path.join(SCREENSHOTS_DIR, `order-${orderId}-request-cancel.png`), fullPage: true });
          await requestButton.scrollIntoViewIfNeeded();
          await requestButton.click({ timeout: 10000, force: true });
          console.log(`[${new Date().toISOString()}] ✅ Clicked 'Request Cancellation'`);

          // Wait for success confirmation
          const successConfirmation = await page.waitForSelector('div.a-alert-success, h4:has-text("cancelled"), span:has-text("cancelled"), .success-message, .a-alert-success', { 
            timeout: 10000 
          }).catch(() => null);
          
          if (!successConfirmation) {
            // Take screenshot for debugging
            await page.screenshot({ path: path.join(SCREENSHOTS_DIR, `order-${orderId}-no-confirmation.png`), fullPage: true });
            
            // Do an additional text check 
            const successText = await page.evaluate(() =>
              document.body.innerText.includes('cancellation was successful') ||
              document.body.innerText.includes('cancelled successfully') ||
              document.body.innerText.includes('order has been cancelled')
            );
            
            if (!successText) {
              return {
                success: false,
                status: 'confirmation_not_found',
                statusMessage: 'Cancellation was submitted but no confirmation was detected',
                screenshot: path.join(SCREENSHOTS_DIR, `order-${orderId}-no-confirmation.png`),
                contextId,
                timestamp: new Date().toISOString(),
              };
            }
          }
          
          // Success confirmed
          status = 'cancelled';
          statusMessage = 'Order successfully cancelled';
        } catch (e) {
          console.warn(`[${new Date().toISOString()}] ⚠️ Could not confirm cancellation step 2:`, e);
          return {
            success: false,
            status: 'cancellation_failed',
            statusMessage: 'Failed to confirm cancellation',
            screenshot: screenshotPath,
            contextId,
            timestamp: new Date().toISOString(),
          };
        }
      } else {
        status = 'not_cancellable';
        statusMessage = 'Order is not eligible for cancellation';
        
        return {
          success: false,
          status,
          statusMessage,
          screenshot: screenshotPath,
          contextId,
          timestamp: new Date().toISOString(),
        };
      }
    }

    console.log(`[${new Date().toISOString()}] Final status: ${status}, message: ${statusMessage}`);
    
    // Only return success: true if we got explicit cancellation confirmation
    return {
      success: status === 'cancelled',
      status,
      statusMessage,
      screenshot: screenshotPath,
      contextId,
      timestamp: new Date().toISOString(),
    };

  } catch (error) {
    console.error(`[${new Date().toISOString()}] ❌ Fatal error:`, error);
    return {
      success: false,
      status: 'error',
      error: error.message,
    };
  } finally {
    try {
      if (browser) await browser.close();
    } catch (closeError) {
      console.error("Failed to close browser:", closeError);
    }
  }
}

export async function checkContextStatus(contextId) {
  if (!contextId) {
    return { exists: false };
  }
  
  try {
    const bb = new Browserbase({ apiKey: process.env.BROWSERBASE_API_KEY });
    
    // Try to create a session with the existing contextId
    const session = await bb.sessions.create({
      projectId: process.env.BROWSERBASE_PROJECT_ID,
      browserSettings: {
        context: { id: contextId, persist: true },
        advancedStealth: true
      }
    });
    
    // If we get here, the context exists
    return { 
      exists: true, 
      contextId 
    };
  } catch (error) {
    console.log("Context check failed:", error.message);
    return { 
      exists: false,
      error: error.message
    };
  }
}
