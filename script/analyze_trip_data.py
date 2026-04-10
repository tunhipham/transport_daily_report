import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import os
from datetime import datetime

path = r'G:\My Drive\DOCS\DAILY\DS chi tiet chuyen xe\T03.26'
dfs = []
for f in sorted(os.listdir(path)):
    if f.endswith('.xlsx'):
        df = pd.read_excel(os.path.join(path, f), sheet_name='Sheet 1')
        dfs.append(df)

df_all = pd.concat(dfs, ignore_index=True)

# Focus on unique trip-destination level (deduplicate box type rows)
trip_dest = df_all.groupby(['Mã chuyến xe', 'Nơi nhận (Tên viết tắt)']).agg({
    'Trạng thái chuyến xe': 'first',
    'Trạng thái nơi nhận': 'first',
    'Nơi chuyển': 'first',
    'Nơi nhận (Tên)': 'first',
    'Ngày xuất phát': 'first',
    'Giờ xuất phát': 'first',
    'Thời gian đến cửa hàng': 'first',
    'Thời gian nhận': 'first',
    'Số xe': 'first',
    'Tên tài xế': 'first',
}).reset_index()

print(f"Total trip-destination rows: {len(trip_dest)}")
print(f"Completed (not cancelled): {(trip_dest['Trạng thái chuyến xe'] == 'Hoàn thành').sum()}")

# For "đúng tuyến" analysis, let's check what info we have
# Option 1: The "Nơi nhận (Tên)" has prefix like "KFM_HCM_GVA" which maps to an area/route
# Let's extract the route/area from destination name
trip_dest['area'] = trip_dest['Nơi nhận (Tên)'].str.extract(r'KFM_(\w+_\w+)')
print(f"\n=== Areas ===")
print(trip_dest['area'].value_counts())

# Let's look deeper into multi-stop trips - are stops within same area?
print("\n=== Multi-stop trips: are all stops in same area? ===")
completed = trip_dest[trip_dest['Trạng thái chuyến xe'] == 'Hoàn thành'].copy()
trip_areas = completed.groupby('Mã chuyến xe')['area'].agg(lambda x: list(x.dropna().unique()))

# Count trips where all stops are same area vs mixed
same_area = 0
mixed_area = 0
for trip_id, areas in trip_areas.items():
    if len(areas) <= 1:
        same_area += 1
    else:
        mixed_area += 1
print(f"Same area trips: {same_area}")
print(f"Mixed area trips: {mixed_area}")

# Show examples of mixed area trips
mixed_trips = [tid for tid, areas in trip_areas.items() if len(areas) > 1]
if mixed_trips:
    print("\nExamples of mixed-area trips:")
    for tid in mixed_trips[:5]:
        stops = completed[completed['Mã chuyến xe'] == tid].sort_values('Thời gian đến cửa hàng')
        print(f"\n  Trip {tid} ({stops.iloc[0]['Nơi chuyển']}):")
        for _, row in stops.iterrows():
            print(f"    -> {row['Nơi nhận (Tên viết tắt)']} ({row['area']})")

# === ON-TIME analysis ===
print("\n\n=== ON-TIME analysis ===")
# Parse departure date+time and arrival time
def parse_dt(date_str, time_str):
    try:
        return datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
    except:
        return None

def parse_arrival(ts):
    try:
        return datetime.strptime(str(ts), "%d/%m/%Y %H:%M")
    except:
        return None

completed_with_time = completed[completed['Thời gian đến cửa hàng'].notna()].copy()
completed_with_time['depart_dt'] = completed_with_time.apply(
    lambda r: parse_dt(str(r['Ngày xuất phát']), str(r['Giờ xuất phát'])), axis=1)
completed_with_time['arrival_dt'] = completed_with_time['Thời gian đến cửa hàng'].apply(parse_arrival)

valid = completed_with_time.dropna(subset=['depart_dt', 'arrival_dt'])
valid = valid.copy()
valid['travel_hours'] = (valid['arrival_dt'] - valid['depart_dt']).dt.total_seconds() / 3600

print(f"Valid timing records: {len(valid)}")
print(f"\nTravel time statistics (hours):")
print(valid['travel_hours'].describe())

# By origin
print("\nTravel time by origin (Nơi chuyển):")
for origin, group in valid.groupby('Nơi chuyển'):
    print(f"\n  {origin}:")
    print(f"    Mean: {group['travel_hours'].mean():.1f}h")
    print(f"    Median: {group['travel_hours'].median():.1f}h")
    print(f"    P90: {group['travel_hours'].quantile(0.9):.1f}h")

# By departure time slot
print("\nTravel time by departure hour:")
valid['depart_hour'] = valid['depart_dt'].dt.hour
for hour, group in valid.groupby('depart_hour'):
    print(f"  {hour:02d}h: n={len(group)}, mean={group['travel_hours'].mean():.1f}h, "
          f"median={group['travel_hours'].median():.1f}h")

# === Hoàn thành analysis ===
print("\n\n=== HOÀN THÀNH analysis ===")
# Trip level
trip_status = df_all.groupby('Mã chuyến xe')['Trạng thái chuyến xe'].first()
print(f"Total trips: {len(trip_status)}")
print(f"Hoàn thành: {(trip_status == 'Hoàn thành').sum()}")
print(f"Đã Hủy: {(trip_status == 'Đã Hủy').sum()}")
print(f"Rate: {(trip_status == 'Hoàn thành').sum()/len(trip_status)*100:.1f}%")

# Destination level
print(f"\nDestination level:")
print(f"Total: {len(trip_dest)}")
print(f"Hoàn thành: {(trip_dest['Trạng thái nơi nhận'] == 'Hoàn thành').sum()}")
print(f"Đã Hủy: {(trip_dest['Trạng thái nơi nhận'] == 'Đã Hủy').sum()}")
print(f"Rate: {(trip_dest['Trạng thái nơi nhận'] == 'Hoàn thành').sum()/len(trip_dest)*100:.1f}%")

# By day
print(f"\nBy day (trip level):")
trip_date = df_all.groupby('Mã chuyến xe').agg({
    'Ngày xuất phát': 'first',
    'Trạng thái chuyến xe': 'first'
})
for date, group in trip_date.groupby('Ngày xuất phát'):
    total = len(group)
    complete = (group['Trạng thái chuyến xe'] == 'Hoàn thành').sum()
    print(f"  {date}: {complete}/{total} = {complete/total*100:.0f}%")
