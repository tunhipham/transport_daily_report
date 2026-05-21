import openpyxl, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

wb = openpyxl.load_workbook(r"output\artifacts\weekly transport plan\Lịch đi hàng ST W22.xlsx", data_only=True)
ws = wb.active

nso_check = ["A159", "A199", "A181", "A193", "A154", "A196", "A203", "A107"]
print("=== Excel W22 - NSO stores ===")
found = []
for row in ws.iter_rows(min_row=2, values_only=False):
    code = row[0].value  # col A = code
    if code and str(code).strip() in nso_check:
        vals = [str(c.value or "").strip() for c in row[:10]]
        found.append(str(code).strip())
        print(f"  {vals}")

print(f"\nFound: {found}")
missing = [c for c in nso_check if c not in found]
print(f"Missing: {missing}")
