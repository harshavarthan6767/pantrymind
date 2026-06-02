import os
import io
import re
import cv2
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# Initialize PaddleOCR globally so the model stays in memory
try:
    from paddleocr import PaddleOCR
    # use_angle_cls=True helps with slightly rotated text
    ocr_engine = PaddleOCR(use_angle_cls=True, lang='en', enable_mkldnn=False)
except ImportError:
    ocr_engine = None
    logger.error("PaddleOCR not installed or failed to import.")

class OCRAgent:
    @staticmethod
    def preprocess_image(image_bytes: bytes) -> np.ndarray:
        """
        Agent Phase 1: Image Preprocessing (OpenCV)
        - Grayscale conversion
        - Adaptive thresholding (Binarization)
        """
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Failed to decode image bytes.")
            
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Adaptive thresholding to handle uneven lighting and shadows
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # PaddleOCR expects a 3-channel (H, W, C) image, so convert the 2D binary image back to BGR
        binary_3c = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        return binary_3c

    @staticmethod
    def extract_text_and_boxes(image_array) -> list:
        if ocr_engine is None:
            raise RuntimeError("PaddleOCR is not initialized.")
            
        result = ocr_engine.ocr(image_array)
        if not result or not result[0]:
            return []
            
        normalized = []
        res = result[0]
        
        # Check if PaddleX dict format
        if isinstance(res, dict):
            boxes = res.get('dt_polys', res.get('rec_polys', res.get('rec_boxes', [])))
            texts = res.get('rec_texts', [])
            scores = res.get('rec_scores', [])
            for i in range(len(texts)):
                box = boxes[i].tolist() if i < len(boxes) else []
                text = texts[i]
                score = scores[i] if i < len(scores) else 0.0
                normalized.append((box, text, score))
        else:
            # Old PaddleOCR format: [[[[x,y],...], ('text', conf)], ...]
            for line in res:
                if len(line) >= 2 and isinstance(line[1], (tuple, list)) and len(line[1]) >= 1:
                    box = line[0]
                    text = line[1][0]
                    score = line[1][1] if len(line[1]) > 1 else 0.0
                    normalized.append((box, text, score))
                    
        return normalized

    @staticmethod
    def parse_receipt_layout(ocr_results: list) -> dict:
        """
        Agent Phase 3 & 4: Layout & Parsing Agent (The "Brain")
        - Groups tokens by Y-axis to form rows
        - Uses Regex to identify weights and prices
        """
        if not ocr_results:
            return {"store": "Unknown", "total": 0.0, "items": []}
            
        # The first extracted text is often the store name
        first_line = ocr_results[0][1].strip() if ocr_results[0][1] else "Unknown Store"
        if len(first_line) < 3:
            first_line = "Local Market"
            
        store_name = first_line[:40]
        items = []
        total_amount = 0.0
        
        # Y-coordinate grouping (spatial layout)
        rows = []
        Y_TOLERANCE = 15  # Pixels tolerance for same line

        # Sort all boxes by their average Y coordinate
        def get_avg_y(box):
            return sum(point[1] for point in box) / 4

        # Clean and sort results
        sorted_results = sorted(ocr_results, key=lambda r: get_avg_y(r[0]))

        current_row = []
        current_y = -1

        for box, text, conf in sorted_results:
            avg_y = get_avg_y(box)
            avg_x = sum(point[0] for point in box) / 4
            
            if current_y == -1 or abs(avg_y - current_y) <= Y_TOLERANCE:
                current_row.append({"text": text, "x": avg_x})
                current_y = (current_y + avg_y) / 2 if current_y != -1 else avg_y
            else:
                current_row.sort(key=lambda item: item["x"])
                rows.append(current_row)
                current_row = [{"text": text, "x": avg_x}]
                current_y = avg_y
                
        if current_row:
            current_row.sort(key=lambda item: item["x"])
            rows.append(current_row)

        # 2. Entity Extraction & Spatial Reasoning
        weight_regex = re.compile(r'\b\d+(\.\d+)?\s*(kg|g|lb|oz|ml|l)\b', re.IGNORECASE)
        price_regex = re.compile(r'(\$|€|£|₹)?\s*\d+\.\d{2}\b')
        
        for row in rows:
            row_text = " ".join(item["text"] for item in row)
            
            # Find all prices in the row
            prices = []
            for token in row:
                if price_regex.search(token["text"]):
                    num_match = re.search(r'(\d+\.\d{2})', token["text"])
                    if num_match:
                        prices.append(float(num_match.group(1)))
            
            if not prices:
                continue

            max_price = max(prices)
            
            # Check if this row is the Total
            if "total" in row_text.lower() or "subtotal" in row_text.lower() or "tax" in row_text.lower():
                total_amount = max(total_amount, max_price)
                continue

            # Check for weight/quantity
            weight_match = weight_regex.search(row_text)
            quantity = 1
            unit = "unit"
            
            if weight_match:
                val_match = re.search(r'\d+(\.\d+)?', weight_match.group(0))
                unit_match = re.search(r'[a-zA-Z]+', weight_match.group(0))
                if val_match and unit_match:
                    quantity = float(val_match.group(0))
                    unit = unit_match.group(0).lower()
            else:
                qty_match = re.search(r'\b(\d+)\s*(x|ea|ct)\b', row_text, re.IGNORECASE)
                if qty_match:
                    quantity = float(qty_match.group(1))
                    unit = qty_match.group(2).lower()
            
            # Extract Item Name
            name = row_text
            for p in prices:
                name = name.replace(str(p), "")
            if weight_match:
                name = name.replace(weight_match.group(0), "")
                
            # Clean up name
            name = re.sub(r'[^\w\s-]', '', name).strip()
            name = re.sub(r'\b\d\b', '', name).strip()

            if len(name) > 3 and 0 < max_price < 5000:
                items.append({
                    "name": name[:30],
                    "category": "Groceries",
                    "quantity": quantity,
                    "unit": unit,
                    "cost_per_unit": round(max_price / quantity, 2) if quantity > 0 else max_price,
                    "total_price": max_price
                })

        # Validation Agent logic
        calculated_total = sum(i["total_price"] for i in items)
        if total_amount == 0 or total_amount < calculated_total * 0.8: 
            total_amount = calculated_total

        return {
            "store": store_name,
            "total": total_amount,
            "items": items
        }
