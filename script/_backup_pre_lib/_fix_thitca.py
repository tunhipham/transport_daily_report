import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'output\monthly_plan_T03.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# THIT CA: derive plan from external actual data (since ABA sheet only has 2025)
tc_ext = data.get('thitca_actual', [])
tc_plan = []
for r in tc_ext:
    tc_plan.append({
        'date': r['date'],
        'store': r['store'],
        'planned_time': r['planned_time'],
        'tuyen': r['tuyen'],
        'kho': 'THỊT CÁ'
    })
# Replace empty plan with derived plan
data['plan']['THỊT CÁ'] = tc_plan
tuyens = sorted(set(r['tuyen'] for r in tc_plan if r['tuyen']))
print(f"THỊT CÁ plan: {len(tc_plan)} rows")
print(f"Unique tuyến: {tuyens[:15]}")

with open(r'output\monthly_plan_T03.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("Saved OK")

# Summary all kho
for kho, rows in data['plan'].items():
    print(f"  {kho}: {len(rows)} plan rows")
