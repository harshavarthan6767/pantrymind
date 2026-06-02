import Tesseract from 'tesseract.js';

export async function processReceiptFile(file) {
  // 1. Convert File to Image Element
  const imageUrl = URL.createObjectURL(file);
  const img = new Image();
  img.src = imageUrl;
  
  await new Promise((resolve, reject) => {
    img.onload = resolve;
    img.onerror = reject;
  });

  // 2. Preprocess with HTML5 Canvas
  const processedImageUrl = preprocessImage(img);
  URL.revokeObjectURL(imageUrl); // clean up

  // 3. Extract Text via Tesseract.js
  const ocrLines = await extractTextLightweight(processedImageUrl);

  // 4. Parse Layout
  const receiptData = parseReceiptLayoutJS(ocrLines);
  
  return receiptData;
}

function preprocessImage(imageElement) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    // Scale down massive 4K phone photos to save CPU during OCR
    const scale = Math.min(1, 1000 / imageElement.width);
    canvas.width = imageElement.width * scale;
    canvas.height = imageElement.height * scale;
    
    // Draw and apply simple contrast/grayscale filter natively
    ctx.filter = 'grayscale(100%) contrast(150%)';
    ctx.drawImage(imageElement, 0, 0, canvas.width, canvas.height);
    
    return canvas.toDataURL('image/png'); // Ready for Tesseract
}

async function extractTextLightweight(processedImageUrl) {
    // Tesseract.js automatically uses Web Workers (background threads)
    // so the UI / CSS animations will not freeze!
    
    const worker = await Tesseract.createWorker("eng", 1, {
        logger: m => {
            // Can be used to hook progress updates
            // console.log(m);
        }
    });

    // Run the extraction
    const { data } = await worker.recognize(processedImageUrl);
    
    // Clean up to free memory immediately
    await worker.terminate();

    // THE FIX: Check if 'data.text' actually exists
    if (!data || !data.text) {
        console.warn("Tesseract could not find any text in this image.");
        return []; // Return an empty array safely instead of crashing
    }

    // Tesseract v5 returns a raw text string, so we split it by newlines
    const ocrLines = data.text.split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);
        
    return ocrLines;
}

function parseReceiptLayoutJS(ocrLines) {
    const receiptData = {
        store: "Scanned Receipt",
        items: [],
        taxes: {},
        subtotal: null,
        total: null
    };

    if (ocrLines.length > 0) {
        receiptData.store = ocrLines[0].substring(0, 40);
    }

    const priceRegex = /(?:[\$£€₹R])?\s*(\d+\.\d{2})/;
    const weightQtyRegex = /(\d+(?:\.\d+)?)\s*(kg|g|l|ml|oz|lb|unit|ea)/i;
    const metadataAnchors = ["TAX", "SGST", "CGST", "IGST", "VAT", "SUBTOTAL", "TOTAL"];

    // 1. Extract Totals and Taxes (Sliding Window)
    for (let i = 0; i < ocrLines.length; i++) {
        let upperLine = ocrLines[i].toUpperCase();

        if (upperLine.includes("TOTAL") && !upperLine.includes("SUB")) {
            let match = upperLine.match(priceRegex);
            if (match) {
                receiptData.total = parseFloat(match[1]);
            } else {
                // Sliding window: Look at the next 2 lines
                for (let j = 1; j <= 2; j++) {
                    if (i + j < ocrLines.length) {
                        let lookaheadMatch = ocrLines[i+j].match(priceRegex);
                        if (lookaheadMatch) {
                            receiptData.total = parseFloat(lookaheadMatch[1]);
                            break;
                        }
                    }
                }
            }
        }
    }

    // 2. Extract Items
    ocrLines.forEach(line => {
        let currentLine = line.trim();

        // --- 1. THE BOUNCER: Instantly Reject Known Metadata & Empty Lines ---
        if (!currentLine || /SUBTOTAL|TOTAL|TAX|DEBIT|AUTH|ITEMS SOLD/i.test(currentLine)) {
            return;
        }

        // --- 2. THE CHOPPER: Remove Appended Category Metadata ---
        const metadataRegex = /(Groceries|Produce|Dairy|Meat|Bakery|Frozen|Grains).*/i;
        currentLine = currentLine.replace(metadataRegex, "").trim();

        // --- 3. THE JUNK FILTER: Reject OCR Hallucinations ---
        if (currentLine.length === 0) return;

        const alphanumericCount = (currentLine.match(/[a-zA-Z0-9]/g) || []).length;
        const symbolCount = (currentLine.match(/[^a-zA-Z0-9\s]/g) || []).length;

        if (alphanumericCount < 3) return;
        if (currentLine.length > 0 && (symbolCount / currentLine.length) > 0.35) {
            return;
        }

        // --- 4. EXTRACTION: Price ---
        const priceRegex = /\d+\.\d{2}/g;
        const priceMatches = currentLine.match(priceRegex);
        let finalPrice = null;

        if (priceMatches) {
            const parsedPrices = priceMatches.map(p => parseFloat(p));
            finalPrice = parsedPrices[parsedPrices.length - 1]; // Take the total
            currentLine = currentLine.replace(priceRegex, "");
        }

        // --- 5. EXTRACTION: Weight or Quantity ---
        const weightRegex = /(\d+(?:\.\d+)?)\s*(lbs|lb|kg|g|oz)/i;
        const weightMatch = currentLine.match(weightRegex);
        let amount = 1;
        let unit = "unit";

        if (weightMatch) {
            amount = parseFloat(weightMatch[1]);
            unit = weightMatch[2].toLowerCase();
            currentLine = currentLine.replace(weightRegex, "");
        }

        // --- 6. CLEANUP: Final Polish ---
        currentLine = currentLine.replace(/\b[F|T]\b\s*$/i, "");
        currentLine = currentLine.replace(/^\(\d+\)/, "");
        currentLine = currentLine.replace(/\b\d+\b/g, "");

        let pristineItemName = currentLine
            .replace(/[^a-zA-Z0-9\s]/g, "") 
            .replace(/\s+/g, " ")
            .trim();

        // --- 7. FINAL SANITY CHECK ---
        // Need a product name AND a price to map to the backend schema properly
        if (pristineItemName.length > 2 && finalPrice !== null) {
            receiptData.items.push({
                name: pristineItemName.substring(0, 30),
                category: "Groceries",
                quantity: amount,
                unit: unit,
                cost_per_unit: amount > 0 ? parseFloat((finalPrice / amount).toFixed(2)) : finalPrice,
                total_price: finalPrice
            });
        }
    });

    // Validation fallback
    let calculatedTotal = receiptData.items.reduce((sum, item) => sum + item.total_price, 0);
    if (!receiptData.total || receiptData.total === 0 || receiptData.total < calculatedTotal * 0.8) {
        receiptData.total = calculatedTotal;
    }

    return receiptData;
}
