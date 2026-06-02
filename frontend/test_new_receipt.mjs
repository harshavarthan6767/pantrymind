import Tesseract from 'tesseract.js';
import fs from 'fs';
import path from 'path';

function cleanAndParseReceiptLine(rawLine) {
    let currentLine = rawLine.trim();

    if (!currentLine || /SUBTOTAL|TOTAL|TAX|DEBIT|AUTH|ITEMS SOLD/i.test(currentLine)) {
        return null;
    }

    const metadataRegex = /(Groceries|Produce|Dairy|Meat|Bakery|Frozen|Grains).*/i;
    currentLine = currentLine.replace(metadataRegex, "").trim();

    if (currentLine.length === 0) return null;

    const alphanumericCount = (currentLine.match(/[a-zA-Z0-9]/g) || []).length;
    const symbolCount = (currentLine.match(/[^a-zA-Z0-9\s]/g) || []).length;

    if (alphanumericCount < 3) return null;
    if (currentLine.length > 0 && (symbolCount / currentLine.length) > 0.35) {
        return null;
    }

    const priceRegex = /\d+\.\d{2}/g;
    const priceMatches = currentLine.match(priceRegex);
    let finalPrice = null;

    if (priceMatches) {
        const parsedPrices = priceMatches.map(p => parseFloat(p));
        finalPrice = parsedPrices[parsedPrices.length - 1];
        currentLine = currentLine.replace(priceRegex, "");
    }

    const weightRegex = /(\d+(?:\.\d+)?)\s*(lbs|lb|kg|g|oz)/i;
    const weightMatch = currentLine.match(weightRegex);
    let amount = 1;
    let unit = "unit";

    if (weightMatch) {
        amount = parseFloat(weightMatch[1]);
        unit = weightMatch[2].toLowerCase();
        currentLine = currentLine.replace(weightRegex, "");
    }

    currentLine = currentLine.replace(/\b[F|T]\b\s*$/i, "");
    currentLine = currentLine.replace(/^\(\d+\)/, "");
    currentLine = currentLine.replace(/\b\d+\b/g, "");

    let pristineItemName = currentLine
        .replace(/[^a-zA-Z0-9\s]/g, "") 
        .replace(/\s+/g, " ")
        .trim();

    if (pristineItemName.length > 2) {
        return {
            name: pristineItemName,
            quantity: amount,
            unit: unit,
            price: finalPrice
        };
    }

    return null;
}

async function run() {
  console.log("Starting Tesseract...");
  const imgPath = path.resolve("C:/Users/harsh/.gemini/antigravity/brain/da36519a-8108-4eec-85f6-5c8d998f7676/media__1780417494011.jpg");
  
  const worker = await Tesseract.createWorker('eng', 1, {
      logger: m => {} // silences progress logs
  });

  const { data } = await worker.recognize(imgPath);
  
  if (!data || !data.text) {
    console.log("No text found");
    return;
  }
  
  const lines = data.text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
  console.log("Raw Tesseract Output:");
  lines.forEach(l => console.log(l));
  
  console.log("\nParsed Items:");
  lines.forEach(line => {
      const parsed = cleanAndParseReceiptLine(line);
      if (parsed) {
          console.log(parsed);
      }
  });
  
  await worker.terminate();
}

run().catch(console.error);
