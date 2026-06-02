import Tesseract from 'tesseract.js';
import fs from 'fs';
import path from 'path';

async function run() {
  console.log("Starting Tesseract...");
  const imgPath = path.resolve("C:/Users/harsh/.gemini/antigravity/brain/da36519a-8108-4eec-85f6-5c8d998f7676/media__1780414919373.jpg");
  
  if (!fs.existsSync(imgPath)) {
    console.error("Image not found at", imgPath);
    return;
  }

  const worker = await Tesseract.createWorker('eng', 1, {
      logger: m => console.log(m)
  });

  console.log("Worker created. Recognizing...");
  const { data } = await worker.recognize(imgPath);
  
  console.log("Keys of data:", Object.keys(data));
  if (data.lines) {
    console.log(`Found ${data.lines.length} lines.`);
  } else {
    console.log("No lines found in data!");
  }
  
  await worker.terminate();
}

run().catch(console.error);
