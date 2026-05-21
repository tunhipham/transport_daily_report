"""Quick script to regenerate capacity PNGs for today."""
import os, sys, json
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "script"))
sys.path.insert(0, os.path.join(BASE, "script", "domains", "daily"))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

output_dir = os.path.join(BASE, "output", "artifacts", "daily")
cap_json_path = os.path.join(BASE, "docs", "data", "capacity_forecast.json")

with open(cap_json_path, "r", encoding="utf-8") as f:
    cap_data = json.load(f)

print(f"KRC data points: {len(cap_data['krc']['data'])}")
print(f"KSL data points: {len(cap_data['ksl']['data'])}")

from generate import _generate_capacity_pngs
paths = _generate_capacity_pngs(cap_data, output_dir, "21052026")
print(f"\nGenerated {len(paths)} PNGs:")
for p in paths:
    print(f"  {os.path.basename(p)}")
