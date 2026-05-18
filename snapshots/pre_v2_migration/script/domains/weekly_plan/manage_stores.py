import os
import json
import argparse
import sys
from datetime import datetime

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MASTER_JSON_PATH = os.path.join(BASE_DIR, "data", "master_schedule.json")
NSO_SCHEDULE_PATH = os.path.join(BASE_DIR, "data", "nso", "nso_schedule.json")
NSO_STORES_PATH = os.path.join(BASE_DIR, "data", "nso", "nso_stores.json")

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {} if "nso_schedule" in path else []

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def update_master(code, name, schedule_ve, shift):
    master_data = load_json(MASTER_JSON_PATH)
    stores = master_data.get("stores", [])
    
    found = False
    for s in stores:
        if s["code"] == code:
            if name: s["name"] = name
            if schedule_ve: s["schedule_ve"] = schedule_ve
            if shift: s["shift"] = shift
            found = True
            break
            
    if not found:
        if not name or not schedule_ve or not shift:
            print(f"❌ Cannot add new store {code} to master_schedule: missing --name, --ve, or --shift")
            return
        stores.append({
            "code": code,
            "short": code,
            "name": name,
            "schedule_ve": schedule_ve,
            "shift": shift
        })
        
    master_data["stores"] = stores
    save_json(MASTER_JSON_PATH, master_data)
    print(f"Updated {code} in master_schedule.json")

def update_nso_schedule(code, name_full, schedule_chia, schedule_ve, shift):
    nso_data = load_json(NSO_SCHEDULE_PATH)
    
    if code not in nso_data:
        nso_data[code] = {}
        
    if name_full: nso_data[code]["name_full"] = name_full
    if schedule_chia: nso_data[code]["schedule_chia"] = schedule_chia
    if schedule_ve: nso_data[code]["schedule_ve"] = schedule_ve
    if shift: nso_data[code]["shift"] = shift
        
    save_json(NSO_SCHEDULE_PATH, nso_data)
    print(f"Updated {code} in nso_schedule.json")

def update_nso_stores(code, name_full, name_system, opening_date, version):
    nso_stores = load_json(NSO_STORES_PATH)
    
    found = False
    for s in nso_stores:
        if s["code"] == code:
            if name_full: s["name_full"] = name_full
            if name_system: s["name_system"] = name_system
            if opening_date: s["opening_date"] = opening_date
            if version: s["version"] = version
            found = True
            break
            
    if not found:
        nso_stores.append({
            "code": code,
            "name_system": name_system or "",
            "name_full": name_full or "",
            "name_mail": name_full or "",
            "opening_date": opening_date or "",
            "version": version or 1000,
            "original_date": None
        })
        
    save_json(NSO_STORES_PATH, nso_stores)
    print(f"Updated {code} in nso_stores.json")

def interactive_mode():
    print("=== TÌM SIÊU THỊ NSO CHƯA CÓ LỊCH ===")
    master_data = load_json(MASTER_JSON_PATH)
    nso_stores = load_json(NSO_STORES_PATH)
    
    master_codes = {s["code"] for s in master_data.get("stores", [])}
    pending = [s for s in nso_stores if s.get("code") and s["code"] not in master_codes]
    
    if pending:
        print(f"Found {len(pending)} pending NSO stores:")
        for s in pending:
            code = s["code"]
            print(f"\n👉 Siêu thị: {code} - {s.get('name_full', '')}")
            ans = input(f"Bạn có muốn cập nhật lịch cho {code} không? (y/n) [y]: ").strip().lower()
            if ans == 'n': continue
            
            ve = input("Nhập Lịch về (VD: Thứ 2-4-6, Ngày chẵn...): ").strip()
            shift = input("Nhập Ca giao (Ngày/Đêm) [Đêm]: ").strip() or "Đêm"
            chia = input("Nhập Lịch chia (VD: Thứ 3-5-7) [Enter để bỏ qua]: ").strip()
            
            if ve and shift:
                update_master(code, s.get('name_full', ''), ve, shift)
                update_nso_schedule(code, s.get('name_full', ''), chia, ve, shift)
    else:
        print("All NSO stores are scheduled.")
        
    print("\n=== CẬP NHẬT THỦ CÔNG ===")
    while True:
        code = input("Nhập Mã Code siêu thị cần update (hoặc Enter để thoát): ").strip().upper()
        if not code: break
        
        name = input("Tên siêu thị (Enter để giữ nguyên nếu đã có): ").strip()
        ve = input("Lịch về (VD: Thứ 2-4-6): ").strip()
        shift = input("Ca giao (Ngày/Đêm): ").strip()
        is_nso = input("Đây có phải siêu thị NSO không? (y/n) [n]: ").strip().lower() == 'y'
        
        update_master(code, name if name else None, ve if ve else None, shift if shift else None)
        if is_nso:
            chia = input("Lịch chia NSO (VD: Thứ 3-5-7): ").strip()
            update_nso_schedule(code, name if name else None, chia if chia else None, ve if ve else None, shift if shift else None)

def main():
    if len(sys.argv) == 1:
        interactive_mode()
        return

    parser = argparse.ArgumentParser(description="CLI tool to add or update store schedules")
    parser.add_argument("--code", help="Store Code (e.g. A186)")
    parser.add_argument("--name", help="Full name for master_schedule (e.g. KFM_HCM_TPH - H.38...)")
    parser.add_argument("--ve", help="Lịch về (e.g. Thứ 3-5-7)")
    parser.add_argument("--chia", help="Lịch chia (e.g. Thứ 2-4-6)")
    parser.add_argument("--shift", choices=["Ngày", "Đêm"], help="Ca giao hàng (Ngày/Đêm)")
    
    # NSO specific args
    parser.add_argument("--is-nso", action="store_true", help="Also add/update to NSO configs")
    parser.add_argument("--nso-name-sys", help="NSO name_system (e.g. KFM_HCM_TPH)")
    parser.add_argument("--nso-name-full", help="NSO name_full (e.g. H.38 Melody Residences...)")
    parser.add_argument("--opening-date", help="NSO opening date (dd/mm/yyyy)")
    parser.add_argument("--version", type=int, help="NSO version (default: 1000)")
    
    args = parser.parse_args()

    print(f"Managing store: {args.code}")
    
    # Update master schedule
    if args.name or args.ve or args.shift:
        update_master(args.code, args.name, args.ve, args.shift)
        
    # Update NSO configs if requested
    if args.is_nso:
        update_nso_schedule(args.code, args.nso_name_full or args.name, args.chia, args.ve, args.shift)
        if args.opening_date or args.nso_name_sys or args.nso_name_full:
            update_nso_stores(args.code, args.nso_name_full or args.name, args.nso_name_sys, args.opening_date, args.version)

if __name__ == "__main__":
    main()
