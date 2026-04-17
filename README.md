# 🚛 Transport Daily Report

**Hệ thống báo cáo & tự động vận hành logistic hàng ngày — SCM Team**

---

## Tổng Quan

Dự án gồm 4 module, chạy **hàng ngày** trên máy local sync Google Drive:

| Module | Slash Command | Output |
|--------|---------------|--------|
| **Daily Report** | `/daily-report` | HTML dashboard + 5 PNG → Telegram |
| **Performance Report** | `/performance-report` | HTML dashboard + Excel raw data |
| **Compose Mail** | `/compose-mail` | HTML email → Haraworks draft |
| **Backup Inject** | `/backup-inject` | Inject thủ công sau cutoff |

### Các kho vận hành

| Kho | Lịch giao | Ghi chú |
|-----|-----------|---------| 
| **KRC** | 7/7 | — |
| **THỊT CÁ** | 7/7 | — |
| **ĐÔNG MÁT** | 6/7 | Không giao Thứ 2 |
| **KSL (DRY)** | 6/7 | Không giao CN (ngoại lệ khai trương) |

---

## Quick Commands

### 1. Daily Report `/daily-report`
```powershell
python -u script/domains/daily/generate.py --send
python -u script/domains/daily/generate.py --date DD/MM/YYYY --send
```

### 2. Compose Mail `/compose-mail`
```powershell
python -u script/compose/auto_compose.py --watch
python -u script/compose/auto_compose.py --status
```

### 3. Performance Report `/performance-report`
```powershell
python -u script/domains/performance/fetch_monthly.py --month 04 --year 2026
python -u script/domains/performance/generate.py --months 3,4 --year 2026
```

### 4. Backup Inject `/backup-inject`
```powershell
python -u script/compose/auto_compose.py --status
python -u script/compose/compose_mail.py --kho KRC --date DD/MM/YYYY
python -u script/compose/inject_haraworks.py --kho KRC --date DD/MM/YYYY --week W16
```

---

## 🌐 Live Dashboard (GitHub Pages)

**URL: https://tunhipham.github.io/transport_daily_report/**

Dashboard web thống nhất 4 tab, team bookmark link này xem report mới nhất.

### Kiến trúc

```
Domain Scripts (daily/perf/inv/nso)
    ↓  generate reports
    ├──→ Telegram (HTML/PNG) ← giữ nguyên
    └──→ export JSON → docs/data/*.json
                            ↓  git push
                     GitHub Pages (live web)
                            ↓
                     Team mở link xem 🎯
```

### 4 Tabs

| Tab | Nội dung | Update khi nào |
|-----|----------|----------------|
| 📦 **Daily** | Tấn/Xe/ST/Items, table theo kho, trend charts, donut | Sau daily report |
| 🚛 **Performance** | SLA/Plan/Route/KH, 5 charts + filters, weekly tables | Sau perf report |
| 📋 **Inventory** | Item/SKU/KG accuracy, trend charts, pie | Sau inventory report |
| 🏪 **NSO** | Store stats, calendar, replenishment schedule | Thứ 3 sau NSO task |

### Cách update dashboard

```powershell
# Sau daily report
python script/dashboard/deploy.py --domain daily

# Sau performance report
python script/dashboard/deploy.py --domain performance

# Sau inventory report
python script/dashboard/deploy.py --domain inventory

# Sau NSO task (thứ 3)
python script/dashboard/deploy.py --domain nso

# Update tất cả
python script/dashboard/deploy.py --domain all
```

Mỗi lệnh sẽ: **Export JSON** → `git add docs/` → `git commit` → `git push` → GitHub Pages tự deploy (~1-2 phút).

### Dashboard Files

| File | Mục đích |
|------|----------|
| `docs/index.html` | SPA dashboard (4 tabs, Chart.js, dark theme) |
| `docs/data/*.json` | Data files cho mỗi domain |
| `script/dashboard/export_data.py` | Export JSON từ state/cache files |
| `script/dashboard/deploy.py` | Export + git push tự động |

> 💡 **Lưu ý**: Máy không cần bật 24/7. Chỉ cần chạy `deploy.py` sau mỗi report. GitHub lo hosting.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3 |
| Data | `openpyxl`, `requests` |
| Browser fetch | `playwright` |
| Email inject | `selenium` + Edge WebDriver |
| Charts | Chart.js (client) |
| Notifications | Telegram Bot API |
| Scheduling | Windows Task Scheduler |
| Storage | Google Drive sync |
| Dashboard | GitHub Pages (static, `docs/` folder) |
| VCS | Git → GitHub (`tunhipham/transport_daily_report`) |

### Prerequisites
```powershell
pip install openpyxl requests playwright selenium
playwright install chromium
```
- **Working directory**: `G:\My Drive\DOCS\transport_daily_report`
- **Edge profile**: `.edge_automail/` (auto-created)
- **Haraworks login**: SC012433

---

## Cấu Trúc Thư Mục (Tổng Quan)

```
transport_daily_report/
├── .agents/workflows/       ← Slash commands (entry point)
├── agents/prompts/          ← 🧠 AI context (architecture, domain knowledge)
├── script/
│   ├── domains/             ← ⚙️ Domain scripts (daily, perf, inv, nso, compose)
│   ├── dashboard/           ← 📊 Export + deploy dashboard
│   ├── lib/                 ← 🔧 Shared modules (telegram, sources)
│   └── orchestrator/        ← 🎛️ Cross-domain (future)
├── docs/                    ← 🌐 GitHub Pages (index.html + data/*.json)
├── data/                    ← 📥 Input data (gitignored)
├── output/                  ← 📤 Output (gitignored)
│   ├── artifacts/           ←   HTML/PNG reports per domain
│   └── state/               ←   ⭐ JSON state files (cầu nối)
├── config/                  ← ⚙️ Telegram, mail schedule, task scheduler
└── README.md
```

> 📖 **Chi tiết kiến trúc**: xem [`agents/prompts/architecture.md`](agents/prompts/architecture.md)
