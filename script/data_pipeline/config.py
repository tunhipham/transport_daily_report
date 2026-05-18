# -*- coding: utf-8 -*-
"""
DB config loader — reads config/mcp_*.json files.
"""
import os
import json

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(BASE, "config")


def load_starrocks_config():
    """Load StarRocks connection config."""
    path = os.path.join(CONFIG_DIR, "mcp_starrocks.json")
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return {
        "host": cfg["host"],
        "port": cfg["port"],
        "user": cfg["user"],
        "password": cfg["password"],
        "database": cfg["database"],
    }


def load_clickhouse_config():
    """Load ClickHouse connection config."""
    path = os.path.join(CONFIG_DIR, "mcp_clickhouse.json")
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return {
        "base_url": cfg["base_url"],
        "user": cfg["params"]["user"],
        "password": cfg["params"]["password"],
        "database": cfg["params"]["database"],
    }


def get_storage_dir():
    """Get storage root (bronze/silver). Currently output/storage/, will move to runtime/storage/."""
    storage = os.path.join(BASE, "output", "storage")
    os.makedirs(storage, exist_ok=True)
    return storage


def get_bronze_dir(date_tag: str):
    """Get bronze directory for a date. date_tag format: DDMMYYYY"""
    d = os.path.join(get_storage_dir(), "bronze", date_tag)
    os.makedirs(d, exist_ok=True)
    return d


def get_silver_dir(date_tag: str):
    """Get silver directory for a date. date_tag format: DDMMYYYY"""
    d = os.path.join(get_storage_dir(), "silver", date_tag)
    os.makedirs(d, exist_ok=True)
    return d
