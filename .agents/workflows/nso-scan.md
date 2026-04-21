# /nso-scan — NSO Mail Scanner

> Quét email NSO trên Haraworks, merge dữ liệu vào master, deploy dashboard.

## Khi nào chạy
- **Tự động**: Task Scheduler chạy Thứ 2 + Thứ 3 lúc 09:00
- **Thứ 3**: Tự động gửi **Telegram notification** (calendar screenshot + dashboard HTML + tóm tắt TUẦN NÀY/TUẦN SAU)
- **Thủ công**: `--force` để chạy bất kỳ ngày nào
- **Dedup**: Tự skip mail đã đọc (track bằng `data/nso/.last_mail_url`)

## Prerequisites
- `data/dsst_cache.json` — DSST store metadata (refresh bằng `_save_dsst.py`)
- Edge browser profile đã login Haraworks

---

## Steps

### Step 1: Run scanner
```powershell
# Auto mode (Thứ 2+3, skip mail cũ)
python -u script/domains/nso/fetch_nso_mail.py

# Force mode (bypass weekday + dedup)
python -u script/domains/nso/fetch_nso_mail.py --force

# Dry run (xem trước, không ghi)
python -u script/domains/nso/fetch_nso_mail.py --force --dry-run
```

> **Dedup**: Nếu mail URL giống lần trước → tự skip.
> `--force` sẽ re-process mail đã đọc.

### Step 2: Review output
- `output/nso/scan_summary.txt` — Tóm tắt kết quả scan
- `output/nso/nso_master.xlsx` — Copy master Excel (Stores + History)
- `output/nso/nso.json` — Dashboard JSON data

### Step 3: Check master
- `data/nso/nso_master.xlsx` — Sheet "Stores": danh sách 30+ stores
- `data/nso/nso_master.xlsx` — Sheet "History": log mọi thay đổi

### Step 4: Verify dashboard
- https://tunhipham.github.io/transport_daily_report/ → Tab NSO
- Ctrl+Shift+R để hard refresh

### Step 5: Telegram notification (Thứ 3 only)
> Tự động chạy qua `auto_nso_watch.bat` — không cần thao tác thủ công.

Batch file detect `DayOfWeek == Tuesday` → chạy `generate.py --send-telegram`:
1. Xóa tin nhắn NSO cũ trên Telegram
2. Screenshot calendar section → gửi ảnh
3. Build tin nhắn tóm tắt (TUẦN NÀY + TUẦN SAU + tổng active)
4. Gửi `nso_dashboard.html` kèm caption vào group (`nso` config)

**Gửi thủ công** (bất kỳ ngày nào):
```powershell
python -u script/domains/nso/generate.py --send-telegram
```

---

## Manual Operations

### Update store date manually
```python
# Trong Python hoặc qua script
from nso_master import NsoMaster
master = NsoMaster()
master.load()
master.update_store("A185", opening_date="25/04/2026", source="Manual")
master.save()
```

### Refresh DSST cache
Khi DSST Google Sheet có thay đổi (thêm store mới, đổi version):
1. Mở DSST sheet trên browser
2. Chạy:
```powershell
python -u script/domains/nso/_save_dsst.py
```

### Re-deploy dashboard only
```powershell
python -u script/dashboard/deploy.py --domain nso
```

---

## Data Flow

```
_save_dsst.py ──→ data/dsst_cache.json (181 stores)
                        ↓
fetch_nso_mail.py ──→ Haraworks mail → parse stores
                        ↓
                  NsoMaster.merge_mail()
                        ↓
              data/nso/nso_master.xlsx (Stores + History)
                        ↓
              output/nso/ (nso.json, nso_master.xlsx, scan_summary.txt)
                        ↓
              export_data.py → docs/data/nso.json
                        ↓
              deploy.py → GitHub Pages
```

## Telegram Notification

- **Khi nào**: Tự động mỗi **Thứ 3 sáng** (09:00) qua Task Scheduler
- **Gửi đến**: Telegram group `nso` (config: `config/telegram.json` → `nso.chat_id`)
- **Nội dung**:
  1. 📸 Calendar screenshot (`nso_calendar.png`)
  2. 📄 Dashboard HTML file (`nso_dashboard.html`) kèm caption:
     - Tổng active stores
     - TUẦN NÀY: danh sách store khai trương tuần hiện tại
     - TUẦN SAU: danh sách store khai trương tuần kế tiếp
- **Logic xóa/gửi mới**: Xóa tin cũ trước khi gửi (track msg_ids trong `output/state/nso/sent_messages.json`)
- **Batch trigger**: `auto_nso_watch.bat` kiểm tra `DayOfWeek == Tuesday` → thêm `--send-telegram`

## Troubleshooting

| Vấn đề | Giải pháp |
|---------|-----------|
| Parsed 0 stores | Email format mới? Check selector + date regex |
| DSST cache empty | Chạy `_save_dsst.py` với DSST sheet mở |
| NSO tab trống | Check JS console cho null code errors |
| Date sai format | Check `22\n/05` pattern → text normalization |
| Telegram không gửi | Check `config/telegram.json` → `nso` domain |

## Task Scheduler

Import XML:
```powershell
schtasks /create /tn "NSO_MailScan" /xml "G:\My Drive\DOCS\transport_daily_report\script\domains\nso\NsoScan_TaskScheduler.xml"
```
- Trigger: Thứ 2 + Thứ 3 lúc 09:00
- Action: `auto_nso_watch.bat` → scan mail + generate dashboard
- **Thứ 2**: Scan mail + generate (không Telegram)
- **Thứ 3**: Scan mail + generate + **gửi Telegram notification**
- Timeout: 10 phút
- StartWhenAvailable: true (chạy bù nếu máy tắt lúc 09:00)
