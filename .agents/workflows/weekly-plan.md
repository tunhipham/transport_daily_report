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

## Auto-Watch Kiểm Kê (Thứ 2)

Script: `script/dashboard/auto_inventory_watch.py`

```
Task Scheduler (thứ 2 07:00) → --watch
  └─ Mỗi 1h (07:00 → 17:30): fetch kiểm kê → diff → deploy → Telegram notify
```

### Commands

| Lệnh | Mô tả |
|-------|-------|
| `auto_inventory_watch.py --backup` | Fetch thủ công bất kỳ ngày |
| `auto_inventory_watch.py --backup --dry-run` | Xem thay đổi, không deploy |
| `auto_inventory_watch.py --watch` | Watch mode (chỉ thứ 2) |
| `auto_inventory_watch.py --force` | 1 shot, bỏ qua check thứ 2 |

### State Files

| File | Nội dung |
|------|----------|
| `output/state/inventory_watch_state.json` | `last_telegram_msg_id` |
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
