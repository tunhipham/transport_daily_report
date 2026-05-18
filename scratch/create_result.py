import json
with open('output/state/history.json', 'r', encoding='utf-8') as f:
    history = json.load(f)
entry = [h for h in history if h['date'] == '18/05/2026']
if entry:
    result = entry[0]
    with open('output/state/last_daily_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    tons = result["total_tons"]
    xe = result["total_xe"]
    st = result["total_sthi"]
    print(f"Created: {tons:.2f}T, {xe}xe, {st}ST")
else:
    print("No entry for 18/05/2026!")
