import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

url = "http://103.140.248.114:32015/"
auth = ("scm_lam", "xukco1-roghaB-fuqfum")

# Check branch_code format
q = "SELECT id, branch_code, branch_name FROM kdb.kf_branch_location WHERE branch_code LIKE 'A1%' LIMIT 10 FORMAT JSON"
r = requests.post(url, auth=auth, params={"database": "kdb", "query": q})
print("branch_code samples:")
for row in r.json()['data']:
    print(f"  {row['branch_code']} = {row['branch_name']}")

# Also check if there's a short name / abbreviation field
q2 = "DESCRIBE kdb.kf_branch_location FORMAT JSON"
r2 = requests.post(url, auth=auth, params={"database": "kdb", "query": q2})
print("\nkf_branch_location columns:")
for row in r2.json()['data']:
    print(f"  {row['name']} ({row['type']})")
