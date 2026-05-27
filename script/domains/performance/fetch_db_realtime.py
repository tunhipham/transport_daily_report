# -*- coding: utf-8 -*-
"""
fetch_db_realtime.py — Load trip data from ClickHouse for realtime performance
===============================================================================
Replaces load_trip_data() (xlsx-based) with DB query for realtime pipeline.

Returns list of row dicts in SAME format as _load_single_file() so
calc_metrics() and all downstream code works unchanged.

Usage:
    from fetch_db_realtime import load_trip_data_from_db
    rows = load_trip_data_from_db(month=5, year=2026)
"""
import os, sys, json, re
from datetime import datetime, timedelta, time as dtime
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ── DB Config ──
CH_CONFIG_PATH = os.path.join(BASE, "config", "mcp_clickhouse.json")


def _load_ch_config():
    with open(CH_CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg["base_url"], cfg["params"]


def _parse_arrival(s):
    """Parse arrival datetime string → (time, datetime) or (None, None)."""
    if not s or s in ("", "0001-01-01T00:00:00Z", "0001-01-01 00:00:00"):
        return None, None
    s = str(s).strip()
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2}):?(\d{2})?', s)
    if m:
        dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                       int(m.group(4)), int(m.group(5)), int(m.group(6) or 0))
        return dtime(dt.hour, dt.minute), dt
    return None, None


def _parse_departure_date(s):
    """Parse departure datetime → date object."""
    if not s:
        return None
    s = str(s).strip()
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
    return None


def _parse_depart_time(s):
    """Parse departure datetime → time object (for KSL session logic)."""
    if not s:
        return None
    s = str(s).strip()
    m = re.search(r'(\d{1,2}):(\d{2})', s)
    if m:
        return dtime(int(m.group(1)), int(m.group(2)))
    return None


# ── NOI_CHUYEN_MAP (same as generate.py) ──
NOI_CHUYEN_MAP = {
    "KSL": "DRY",
    "SLKT": "KSL-Tối",
    "KRC": "KRC",
    "QCABA": "ĐÔNG MÁT",
}


def _get_kho_session(noi_chuyen, arrival_time, depart_time=None):
    """Map warehouse + time to kho name (with KSL session split)."""
    kho = NOI_CHUYEN_MAP.get(noi_chuyen, noi_chuyen)
    if kho == "DRY":
        ref_time = arrival_time or depart_time
        if ref_time:
            if ref_time.hour < 15:
                return "KSL-Sáng"
            else:
                return "KSL-Tối"
        return "KSL-Sáng"
    return kho


def load_trip_data_from_db(month, year):
    """Load trip data from ClickHouse for a given month.
    
    Returns list of row dicts matching _load_single_file() format:
    {trip_id, dest, kho, sub_kho, noi_chuyen, driver, vehicle_number,
     phone, date, trip_status, dest_status, arrival_time, arrival_dt,
     arrival_raw, container_type}
    """
    import requests

    base_url, params = _load_ch_config()
    
    from calendar import monthrange
    _, days = monthrange(year, month)
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-{days:02d} 23:59:59"

    sql = f"""
    SELECT
        t.t_code,
        t.t_status,
        t.t_license_number,
        t.t_driver_name,
        t.t_driver_phone,
        t.t_departure,
        arrayJoin(t.t_from_location_name_abbreviates) AS noi_chuyen,
        b.branch_name_abbreviate AS dest,
        t.tl_arrival,
        t.barrel_basket_name
    FROM kdb.kf_trip_locations_items t
    LEFT JOIN kdb.kf_branch_location b ON t.tl_branch_id = b.id
    WHERE t.t_departure >= '{start}' AND t.t_departure <= '{end}'
    FORMAT JSONEachRow
    """

    print(f"  → ClickHouse: trips for {year}-{month:02d}...")
    r = requests.get(base_url, params={**params, "query": sql}, timeout=120)
    r.raise_for_status()

    # Dedup by (trip_id, dest, sub_kho) — same as _load_single_file
    seen = {}
    total_raw = 0

    for line in r.text.strip().split("\n"):
        if not line.strip():
            continue
        total_raw += 1
        obj = json.loads(line)

        t_code = str(obj.get("t_code", "")).strip()
        dest = str(obj.get("dest", "")).strip()
        noi_chuyen = str(obj.get("noi_chuyen", "")).strip()
        barrel = str(obj.get("barrel_basket_name", "")).strip()
        t_status = obj.get("t_status", 0)

        if not t_code or not dest:
            continue

        # Parse times
        arrival_raw = str(obj.get("tl_arrival", "")).strip()
        arrival_time, arrival_dt = _parse_arrival(arrival_raw)
        dep_date = _parse_departure_date(obj.get("t_departure", ""))
        depart_time = _parse_depart_time(obj.get("t_departure", ""))

        if not dep_date:
            continue

        # Kho + session
        kho = _get_kho_session(noi_chuyen, arrival_time, depart_time)

        # Sub-kho for ĐÔNG MÁT
        sub_kho = ""
        if kho == "ĐÔNG MÁT":
            if "tote" in barrel.lower():
                sub_kho = "ĐÔNG"
            else:
                sub_kho = "MÁT"

        # Dedup key
        key = (t_code, dest, sub_kho)
        if key in seen:
            continue

        # Map status
        trip_status = "Hoàn thành" if t_status == 3 else "Đang giao"
        # Dest status: derive from arrival — if arrived, consider completed
        dest_status = "Hoàn thành" if arrival_time is not None else ""

        seen[key] = {
            "trip_id": t_code,
            "dest": dest,
            "kho": kho,
            "sub_kho": sub_kho,
            "noi_chuyen": noi_chuyen,
            "driver": str(obj.get("t_driver_name", "")).strip(),
            "vehicle_number": str(obj.get("t_license_number", "")).strip(),
            "phone": str(obj.get("t_driver_phone", "")).strip(),
            "date": dep_date,
            "trip_status": trip_status,
            "dest_status": dest_status,
            "arrival_time": arrival_time,
            "arrival_dt": arrival_dt,
            "arrival_raw": arrival_raw,
            "container_type": barrel,
        }

    rows = list(seen.values())
    with_time = sum(1 for r in rows if r["arrival_time"] is not None)
    no_time = len(rows) - with_time

    print(f"    {total_raw:,} raw → {len(rows)} deduped")
    print(f"    🕐 {with_time} with arrival, {no_time} without")

    return rows


# ── Container classification ──
TOTE_KEYWORDS = ["tote", "rổ", "ro "]
CARTON_KEYWORDS = ["carton", "kiện", "kien", "bịch", "bich", "pallet"]


def _classify_container(barrel_name):
    """Classify barrel_basket_name → 'tote' or 'carton'."""
    low = barrel_name.lower()
    for kw in CARTON_KEYWORDS:
        if kw in low:
            return "carton"
    return "tote"  # Default = rổ/tote


def load_tracking_data(start_date_iso, end_date_iso=None):
    """Load tracking data for a date range with container breakdown.
    
    Returns dict keyed by date_iso → kho → list of row dicts:
    { "YYYY-MM-DD": { "KHO": [ {trip_id, dest, arrival...} ] } }
    """
    import requests

    if not end_date_iso:
        end_date_iso = start_date_iso

    base_url, params = _load_ch_config()

    sql = f"""
    SELECT
        t.t_code,
        t.t_status,
        t.t_license_number,
        t.t_driver_name,
        t.t_driver_phone,
        t.t_departure,
        arrayJoin(t.t_from_location_name_abbreviates) AS noi_chuyen,
        b.branch_name_abbreviate AS dest,
        t.tl_arrival,
        t.barrel_basket_name,
        t.tli_transfer_qty,
        t.tli_received_qty
    FROM kdb.kf_trip_locations_items t
    LEFT JOIN kdb.kf_branch_location b ON t.tl_branch_id = b.id
    WHERE toDate(t.t_departure) >= '{start_date_iso}' 
      AND toDate(t.t_departure) <= '{end_date_iso}'
    FORMAT JSONEachRow
    """

    print(f"  → Tracking data for {start_date_iso} to {end_date_iso}...")
    r = requests.get(base_url, params={**params, "query": sql}, timeout=60)
    r.raise_for_status()

    # Aggregate containers per (date, trip_id, dest, kho)
    agg = {}  # key → {meta, tote_t, tote_r, carton_t, carton_r}

    for line in r.text.strip().split("\n"):
        if not line.strip():
            continue
        obj = json.loads(line)

        t_code = str(obj.get("t_code", "")).strip()
        dest = str(obj.get("dest", "")).strip()
        noi_chuyen = str(obj.get("noi_chuyen", "")).strip()
        barrel = str(obj.get("barrel_basket_name", "")).strip()
        dep_date = _parse_departure_date(obj.get("t_departure", ""))

        if not t_code or not dest or not dep_date:
            continue

        date_iso = dep_date.strftime("%Y-%m-%d")
        arrival_raw = str(obj.get("tl_arrival", "")).strip()
        arrival_time, _ = _parse_arrival(arrival_raw)
        depart_time = _parse_depart_time(obj.get("t_departure", ""))
        kho = _get_kho_session(noi_chuyen, arrival_time, depart_time)

        # Sub-kho
        sub_kho = ""
        if kho == "ĐÔNG MÁT":
            sub_kho = "ĐÔNG" if "tote" in barrel.lower() else "MÁT"

        # Use sub_kho as display kho for tracking
        display_kho = sub_kho if sub_kho else kho

        key = (date_iso, t_code, dest, display_kho)
        transfer = int(obj.get("tli_transfer_qty", 0) or 0)
        received = int(obj.get("tli_received_qty", 0) or 0)
        ctype = _classify_container(barrel)

        if key not in agg:
            agg[key] = {
                "date_iso": date_iso,
                "trip": t_code,
                "plate": str(obj.get("t_license_number", "")).strip(),
                "driver": str(obj.get("t_driver_name", "")).strip(),
                "phone": str(obj.get("t_driver_phone", "")).strip(),
                "dest": dest,
                "kho": display_kho,
                "arrival": arrival_time.strftime("%H:%M") if arrival_time else "",
                "tote_t": 0, "tote_r": 0,
                "carton_t": 0, "carton_r": 0,
            }

        if ctype == "tote":
            agg[key]["tote_t"] += transfer
            agg[key]["tote_r"] += received
        else:
            agg[key]["carton_t"] += transfer
            agg[key]["carton_r"] += received

    # Group by date -> kho
    by_date = defaultdict(lambda: defaultdict(list))
    for row in agg.values():
        date_iso = row.pop("date_iso")
        by_date[date_iso][row["kho"]].append(row)

    # Sort each kho by trip → dest
    for d in by_date:
        for kho in by_date[d]:
            by_date[d][kho].sort(key=lambda r: (r["trip"], r["dest"]))

    # Convert defaultdict to normal dict for JSON
    res = {d: dict(khos) for d, khos in by_date.items()}
    
    total = sum(len(v) for dates in res.values() for v in dates.values())
    print(f"    📋 {total} tracking rows across {len(res)} dates")

    return res


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", type=int, default=datetime.now().month)
    parser.add_argument("--year", type=int, default=datetime.now().year)
    parser.add_argument("--tracking-date", default=None, help="YYYY-MM-DD for tracking")
    args = parser.parse_args()

    if args.tracking_date:
        data = load_tracking_data(args.tracking_date)
        for kho, rows in data.items():
            print(f"\n  {kho}: {len(rows)} rows")
            for r in rows[:3]:
                print(f"    {r['trip']} → {r['dest']} | arr={r['arrival']} | tote={r['tote_t']}/{r['tote_r']} carton={r['carton_t']}/{r['carton_r']}")
    else:
        rows = load_trip_data_from_db(args.month, args.year)
        print(f"\n✅ Total: {len(rows)} rows for T{args.month:02d}/{args.year}")

