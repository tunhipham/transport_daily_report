# -*- coding: utf-8 -*-
"""
Validate bronze data against contracts (JSON schemas).
Promote valid data bronze → silver.
"""
import os
import json
import shutil

CONTRACTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contracts")


def load_schema(extractor_name: str) -> dict | None:
    """Load JSON schema for an extractor."""
    path = os.path.join(CONTRACTS_DIR, f"{extractor_name}.schema.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_bronze(bronze_path: str) -> tuple[bool, list[str]]:
    """
    Validate a bronze JSON file against its schema.
    Returns (is_valid, list_of_errors).
    """
    with open(bronze_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    extractor_name = data.get("extractor", "unknown")
    schema = load_schema(extractor_name)

    errors = []

    # Basic structural checks (no jsonschema dependency needed)
    if not isinstance(data.get("rows"), list):
        errors.append(f"'rows' must be a list, got {type(data.get('rows'))}")

    if not isinstance(data.get("row_count"), int):
        errors.append(f"'row_count' must be int, got {type(data.get('row_count'))}")

    if isinstance(data.get("rows"), list) and isinstance(data.get("row_count"), int):
        actual = len(data["rows"])
        declared = data["row_count"]
        if actual != declared:
            errors.append(f"row_count mismatch: declared={declared}, actual={actual}")

    if not data.get("date_tag"):
        errors.append("missing 'date_tag'")

    # Schema-based validation (if jsonschema is available)
    if schema:
        try:
            import jsonschema
            jsonschema.validate(data, schema)
        except ImportError:
            pass  # jsonschema not installed, skip deep validation
        except jsonschema.ValidationError as e:
            errors.append(f"Schema violation: {e.message}")

    is_valid = len(errors) == 0
    return is_valid, errors


def promote_to_silver(bronze_path: str, silver_dir: str) -> str:
    """Copy validated bronze file to silver directory."""
    fname = os.path.basename(bronze_path)
    silver_path = os.path.join(silver_dir, fname)
    shutil.copy2(bronze_path, silver_path)
    print(f"  ✅ Silver: {fname}")
    return silver_path


def validate_and_promote(bronze_dir: str, silver_dir: str) -> dict:
    """
    Validate all bronze files and promote valid ones to silver.
    Returns summary dict.
    """
    os.makedirs(silver_dir, exist_ok=True)
    results = {"promoted": [], "failed": [], "skipped": []}

    for fname in sorted(os.listdir(bronze_dir)):
        if not fname.endswith(".json"):
            continue

        bronze_path = os.path.join(bronze_dir, fname)
        is_valid, errors = validate_bronze(bronze_path)

        if is_valid:
            silver_path = promote_to_silver(bronze_path, silver_dir)
            results["promoted"].append(fname)
        else:
            print(f"  ❌ Validation failed: {fname}")
            for err in errors:
                print(f"     → {err}")
            results["failed"].append({"file": fname, "errors": errors})

    return results
