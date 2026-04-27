---
description: Generate or update the weekly transport plan (Lịch về hàng siêu thị)
---

# Weekly Transport Plan Workflow

> Tạo và cập nhật Lịch Tuần giao hàng siêu thị.
> **Thứ 5 hàng tuần**: 12h check data → 13h generate + send review → user confirm → gửi team
> Dashboard tab: 📅 Lịch Tuần
> Context: [agents/prompts/weekly-plan.md](../../../agents/prompts/weekly-plan.md)

## ⚠ MANDATORY: Read roles & prompts FIRST
Before doing ANYTHING:
1. Read `agents/role.md` — nguyên tắc chung, phạm vi, quy ước output
2. Read `agents/prompts/weekly-plan.md` — NSO logic, Excel format, master schedule rules

## Rules

1. **Lịch cố định**: Lịch về/shift cố định trong `data/master_schedule.json`. Chỉ thay đổi khi user confirm
2. **NSO châm hàng**: D→D+3 châm hàng, D+4 skip nếu trùng delivery day, sau đó daily bình thường
3. **Kiểm kê**: Fetch từ Google Sheets, đánh dấu D và D-1 unconditionally
4. **Excel format**: 10 cột (A-J), không xuất Lịch chia/Lịch về/Khai trương/Kiểm kê columns
5. **Không viết tắt**: Tất cả label trên dashboard và report phải viết đầy đủ

## Workflow

### 1. Generate file Excel tuần mới

// turbo
```powershell
python script/domains/weekly_plan/generate_excel.py --week {nn}
```

Output: `output/artifacts/weekly transport plan/Lịch đi hàng ST W{nn}.xlsx`

### 2. Cập nhật NSO stores (nếu có khai trương mới)

Thêm store mới vào **3 nơi**:

| Nơi | File | Thêm gì |
|-----|------|---------|
| NSO STORES | `script/domains/nso/generate.py` | `code`, `name_system`, `name_full`, `opening_date` |
| NSO_SCHEDULE | `script/dashboard/export_weekly_plan.py` | `schedule_ve`, `shift`, `name_full` |
| Master schedule | `data/master_schedule.json` | `code`, `name`, `schedule_ve`, `shift` |

> [!NOTE]
> A112 Cô Giang: `schedule_ve: "Ngày chẵn"` — script tự tính dynamic. Shift mặc định = Đêm.

### 3. Export data + Deploy

// turbo
```powershell
python script/dashboard/export_weekly_plan.py
python script/dashboard/deploy.py --domain weekly_plan
```

### 4. Verify trên dashboard

- Mở https://tunhipham.github.io/transport_daily_report/ → Tab "📅 Lịch Tuần"
- Check: NSO châm hàng, kiểm kê, stores đủ, nút "Xuất Excel"

---

## Thursday Finalize Automation

Script: `script/domains/weekly_plan/finalize.py`

### Flow

```
12:00 Thu (auto)   →  --check     Check data readiness → Telegram reminder
13:00 Thu (auto)   →  --send      Generate Excel → Telegram review
User confirm       →  --deliver   Gửi Excel → group SCM - NCP
```

### Commands

| Lệnh | Mô tả |
|-------|-------|
| `python script/domains/weekly_plan/finalize.py --check` | Check readiness + gửi reminder (auto Thu 12h) |
| `python script/domains/weekly_plan/finalize.py --send` | Generate Excel + gửi review (auto Thu 13h) |
| `python script/domains/weekly_plan/finalize.py --deliver` | Gửi lên group SCM - NCP (**MANUAL** — user confirm) |
| `python script/domains/weekly_plan/finalize.py --deliver --week 18` | Gửi tuần cụ thể |
| `python script/domains/weekly_plan/finalize.py --test` | Test gửi file mới nhất qua Telegram cá nhân |

### Task Scheduler

| Task Name | Schedule |
|-----------|----------|
| `WeeklyPlan_12h_Check` | Thu 12:00 |
| `WeeklyPlan_13h_Send` | Thu 13:00 |

> [!IMPORTANT]
> `--deliver` KHÔNG tự động. Chỉ chạy thủ công sau khi user confirm file review.

---

## Monday Kiểm Kê Refresh (Thứ 2)

Script: `script/dashboard/auto_inventory_watch.py`

```
Task Scheduler (thứ 2 07:00) → --watch
  ├─ 07:00-11:00: Monitor kiểm kê (fetch + log only, no deploy)
  ├─ 12:00 cutoff: Re-generate Excel → export JSON → deploy → send summary + file
  └─ User confirm → --deliver: gửi group SCM-NCP
```

### Commands

| Lệnh | Mô tả |
|-------|-------|
| `auto_inventory_watch.py --watch` | Watch mode: monitor → cutoff 12h full pipeline |
| `auto_inventory_watch.py --backup` | One-shot full pipeline (bất kỳ ngày) |
| `auto_inventory_watch.py --deliver` | Gửi Excel cập nhật vào group SCM-NCP |
| `auto_inventory_watch.py --backup --dry-run` | Xem thay đổi, không deploy |
| `auto_inventory_watch.py --force` | 1 shot full pipeline, bỏ qua check thứ 2 |

### Monday Flow

1. **07:00→11:00**: Fetch kiểm kê mỗi 1h, log thay đổi (không deploy)
2. **12:00 Cutoff**: Re-generate Excel tuần hiện tại → re-export JSON → deploy dashboard
3. **Diff vs thứ 5**: So sánh toàn bộ store data (shift, kiểm kê, lịch giao) v/s Thursday baseline
4. **Telegram**: Gửi summary thay đổi + file Excel + **draft caption** gửi group
5. **User confirm**: Reply 'OK' → chạy `--deliver` gửi vào group SCM-NCP với caption đã duyệt

> [!IMPORTANT]
> `finalize.py --send` (thứ 5) lưu **Thursday baseline** (`output/state/thursday_baseline_W{nn}.json`).
> Monday diff so với baseline này để phát hiện mọi thay đổi: shift (Đêm→Ngày), kiểm kê (thêm/bớt/dời), lịch giao (246/357). 

### State Files

| File | Nội dung |
|------|-----------|
| `output/state/inventory_watch_state.json` | `last_telegram_msg_id`, `monday_diff`, `group_caption` |
| `output/state/thursday_baseline_W{nn}.json` | Snapshot stores từ thứ 5 (shift, kiểm kê, days) |
| `output/state/inventory_watch.lock` | Lock chống chạy trùng |
| `output/logs/inventory_watch.log` | Log chi tiết |

---

## Troubleshooting

| Vấn đề | Giải pháp |
|--------|-----------|
| NSO không hiện châm hàng | Check 3 nơi: NSO STORES + NSO_SCHEDULE + master_schedule.json |
| NSO skip D+4 sai | Check skip-first-day: `generate_excel.py` và `export_weekly_plan.py` |
| Kiểm kê sai/thiếu | Re-export (fetch mới). Check date normalization |
| Dashboard data cũ | Hard refresh — JSON có cache-bust `?t=timestamp` |
| Finalize không chạy | `schtasks /query /tn "WeeklyPlan_12h_Check"` |
| Watch không chạy | Xóa lock file `output/state/inventory_watch.lock` |
| Telegram không gửi | Check `config/telegram.json` key `weekly_plan` |
| Deliver không gửi | Chạy `--backup` trước để tạo diff, sau đó `--deliver` |

