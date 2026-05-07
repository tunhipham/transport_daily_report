import sys, os, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
f = open(r'G:\My Drive\DOCS\transport_daily_report\docs\data\performance.json', 'r', encoding='utf-8')
d = json.load(f)
f.close()
html = d['weekly_tables_html']
# Split by table sections
sections = re.split(r'<div class="chart-box"', html)
for s in sections:
    if not s.strip():
        continue
    title_match = re.search(r'<h3>.*?([\w\s]+)\s*—', s)
    title = title_match.group(1).strip() if title_match else "?"
    metrics = re.findall(r'wt-metric-cell">(.*?)</td>', s)
    print(f"\n=== {title} ===")
    print(f"  Metrics: {metrics}")
