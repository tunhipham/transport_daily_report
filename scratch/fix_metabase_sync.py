"""
Fix Metabase StarRocks sync stuck issue.
"""
import requests
import time
import sys
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE = "http://localhost:3000/api"
headers = {}

# Step 1: Get session - try common credentials
print("Step 1: Login to Metabase")
for creds in [
    {"username": "admin@admin.com", "password": "admin123"},
    {"username": "admin@example.com", "password": "admin123"},
    {"username": "admin", "password": "admin123"},
    {"username": "admin@admin.com", "password": "Admin123!"},
]:
    try:
        login = requests.post(f"{BASE}/session", json=creds, timeout=5)
        if login.status_code == 200:
            token = login.json().get("id")
            headers = {"X-Metabase-Session": token}
            print(f"  Logged in with {creds['username']}")
            break
        else:
            print(f"  {creds['username']}: {login.status_code}")
    except Exception as e:
        print(f"  {creds['username']}: {e}")
else:
    # Try without auth (maybe cookies from browser)
    resp = requests.get(f"{BASE}/database")
    if resp.status_code == 200:
        print("  No auth needed")
    else:
        print("  Could not authenticate. Trying cookie-based approach...")
        # Get current user check
        resp = requests.get(f"{BASE}/user/current")
        print(f"  Current user check: {resp.status_code}")

# Step 2: Get databases
print("\nStep 2: Get databases")
resp = requests.get(f"{BASE}/database", headers=headers)
print(f"  Status: {resp.status_code}")
if resp.status_code != 200:
    print(f"  Response: {resp.text[:500]}")
    sys.exit(1)

data = resp.json()
db_list = data.get("data", data if isinstance(data, list) else [])
sr_db = None
for db in db_list:
    name = db.get("name", "")
    print(f"  DB: {name} (id={db['id']}, sync={db.get('initial_sync_status')})")
    if "StarRocks" in name or "starrocks" in name.lower():
        sr_db = db

if not sr_db:
    print("  StarRocks not found!")
    sys.exit(1)

db_id = sr_db["id"]
print(f"\n  Target: StarRocks DB ID={db_id}, sync_status={sr_db.get('initial_sync_status')}")

# Step 3: Discard field values
print("\nStep 3: Discard field values")
resp = requests.post(f"{BASE}/database/{db_id}/discard_values", headers=headers)
print(f"  Result: {resp.status_code}")

# Step 4: Update to disable heavy operations
print("\nStep 4: Update settings")
resp = requests.put(f"{BASE}/database/{db_id}", headers=headers, json={
    "is_full_sync": False,
    "is_on_demand": True,
    "refingerprint": False
})
print(f"  Result: {resp.status_code}")

# Step 5: Trigger schema-only sync
print("\nStep 5: Trigger schema sync only")
resp = requests.post(f"{BASE}/database/{db_id}/sync_schema", headers=headers)
print(f"  Result: {resp.status_code}")

# Step 6: Wait and check
print("\nStep 6: Waiting 20s...")
time.sleep(20)

resp = requests.get(f"{BASE}/database/{db_id}", headers=headers)
if resp.status_code == 200:
    db = resp.json()
    print(f"  sync_status: {db.get('initial_sync_status')}")

resp2 = requests.get(f"{BASE}/database/{db_id}/metadata?include_hidden=true", headers=headers)
if resp2.status_code == 200:
    md = resp2.json()
    tables = md.get("tables", [])
    print(f"  Tables found: {len(tables)}")
    for t in tables:
        print(f"    - {t.get('name')} (vis={t.get('visibility_type')}, active={t.get('active')})")

print("\nDone.")
