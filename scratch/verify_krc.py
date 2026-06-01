import json
d = json.load(open(r'g:\My Drive\DOCS\transport_daily_report\docs\data\capacity_forecast.json', encoding='utf-8'))
krc = d['krc']['data']
print(f"KRC: {len(krc)} days")
print("First 5:")
for x in krc[:5]:
    print(f"  {x['date']} -> {x['tons']} tan")
print("Last 5:")
for x in krc[-5:]:
    print(f"  {x['date']} -> {x['tons']} tan")
