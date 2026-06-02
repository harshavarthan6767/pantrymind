"""
Google Cloud Document AI OCR Service.

Uses the pre-trained Expense Parser for receipts and Invoice Parser for
formal documents. Extracts line items, prices, dates, and merchant info.
"""

import os
import logging
from typing import Literal

from google.cloud import documentai_v1 as documentai

logger = logging.getLogger("pantrymind.ocr")


class OCRService:
    """Wrapper around Google Cloud Document AI processors."""

    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us")
        self.expense_processor_id = os.getenv("DOC_AI_EXPENSE_PROCESSOR_ID")
        self.invoice_processor_id = os.getenv("DOC_AI_INVOICE_PROCESSOR_ID")

        opts = {"api_endpoint": f"{self.location}-documentai.googleapis.com"}
        self.client = documentai.DocumentProcessorServiceClient(client_options=opts)

    def _get_processor_path(
        self, doc_type: Literal["receipt", "invoice"]
    ) -> str:
        """Get the full processor resource path."""
        processor_id = (
            self.expense_processor_id
            if doc_type == "receipt"
            else self.invoice_processor_id
        )
        return self.client.processor_path(
            self.project_id, self.location, processor_id
        )

    def parse_document(
        self,
        file_content: bytes,
        mime_type: str,
        doc_type: Literal["receipt", "invoice"] = "receipt",
    ) -> dict:
        """
        Send a document image to Document AI and extract structured data.

        Returns:
            {
                "receipt_date": "2026-06-01",
                "merchant_name": "Big Bazaar",
                "total_amount": "1234.50",
                "currency": "INR",
                "line_items": [
                    {"description": "Apples 1kg", "amount": "120.00", "quantity": "1"},
                    ...
                ],
                "confidence": 0.95,
                "raw_text": "full OCR text..."
            }
        """
        name = self._get_processor_path(doc_type)

        raw_document = documentai.RawDocument(
            content=file_content,
            mime_type=mime_type,
        )
        request = documentai.ProcessRequest(
            name=name,
            raw_document=raw_document,
        )

        logger.info(f"Sending {doc_type} to Document AI (processor: {name})")
        result = self.client.process_document(request=request)
        document = result.document

        return self._extract_entities(document)

    def _extract_entities(self, document) -> dict:
        """Extract structured entities from Document AI response."""
        extracted = {
            "receipt_date": None,
            "merchant_name": None,
            "total_amount": None,
            "currency": None,
            "line_items": [],
            "confidence": 0.0,
            "raw_text": document.text,
        }

        confidence_scores = []

        for entity in document.entities:
            conf = entity.confidence
            confidence_scores.append(conf)

            # Top-level fields
            if entity.type_ == "receipt_date":
                extracted["receipt_date"] = (
                    entity.normalized_value.text
                    if entity.normalized_value
                    else entity.mention_text
                )
            elif entity.type_ == "supplier_name":
                extracted["merchant_name"] = entity.mention_text
            elif entity.type_ in ("total_amount", "net_amount"):
                extracted["total_amount"] = (
                    entity.normalized_value.text
                    if entity.normalized_value
                    else entity.mention_text
                )
            elif entity.type_ == "currency":
                extracted["currency"] = entity.mention_text

            # Line items (nested entities)
            elif entity.type_ == "line_item":
                item = {
                    "description": None,
                    "amount": None,
                    "quantity": None,
                    "unit_price": None,
                }
                for prop in entity.properties:
                    if prop.type_ == "line_item/description":
                        item["description"] = prop.mention_text
                    elif prop.type_ == "line_item/amount":
                        item["amount"] = (
                            prop.normalized_value.text
                            if prop.normalized_value
                            else prop.mention_text
                        )
                    elif prop.type_ == "line_item/quantity":
                        item["quantity"] = prop.mention_text
                    elif prop.type_ == "line_item/unit_price":
                        item["unit_price"] = prop.mention_text

                if item["description"]:
                    extracted["line_items"].append(item)

        # Average confidence
        if confidence_scores:
            extracted["confidence"] = sum(confidence_scores) / len(confidence_scores)

        logger.info(
            f"Extracted {len(extracted['line_items'])} line items, "
            f"confidence: {extracted['confidence']:.2f}"
        )
        return extracted
