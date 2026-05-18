# -*- coding: utf-8 -*-
"""
Base extractor interface.
All extractors inherit from this and implement extract().
"""
import os
import json
from abc import ABC, abstractmethod
from datetime import datetime


class BaseExtractor(ABC):
    """Base class for all data extractors."""

    name: str = "base"  # Override in subclass

    def __init__(self, date_tag: str, bronze_dir: str):
        """
        Args:
            date_tag: DDMMYYYY format
            bronze_dir: path to bronze/{date_tag}/
        """
        self.date_tag = date_tag
        self.bronze_dir = bronze_dir

    @abstractmethod
    def extract(self) -> dict:
        """
        Extract data from source.
        Returns dict with:
            - rows: list of row dicts
            - row_count: int
            - source: str (db name or file path)
            - extracted_at: ISO timestamp
        """
        raise NotImplementedError

    def save_bronze(self, data: dict) -> str:
        """Save extracted data to bronze directory as JSON."""
        output_path = os.path.join(self.bronze_dir, f"{self.name}.json")
        payload = {
            "extractor": self.name,
            "date_tag": self.date_tag,
            "extracted_at": datetime.now().isoformat(),
            "source": data.get("source", "unknown"),
            "row_count": data.get("row_count", len(data.get("rows", []))),
            "rows": data.get("rows", []),
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"  💾 Bronze: {self.name}.json ({payload['row_count']} rows)")
        return output_path

    def run(self) -> str:
        """Extract + save to bronze. Returns bronze file path."""
        print(f"  ▶ Extracting: {self.name}...")
        data = self.extract()
        return self.save_bronze(data)
