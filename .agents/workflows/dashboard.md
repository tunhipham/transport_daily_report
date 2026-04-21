# /dashboard — Update Live Dashboard

> Cập nhật dashboard web sau khi chạy xong report.
> URL: https://tunhipham.github.io/transport_daily_report/

> [!NOTE]
> **Daily domain tự động deploy** khi chạy `generate.py --send`.
> Chỉ cần chạy manual deploy cho các domain khác (performance, inventory, nso, weekly_plan) hoặc khi cần re-deploy.

## Prerequisites
- Report domain tương ứng đã chạy xong (daily/performance/inventory/nso/weekly_plan)
- Git configured với push access

## Workflow

### Update 1 domain cụ thể
```powershell
# Sau daily report
python script/dashboard/deploy.py --domain daily

# Sau performance report  
python script/dashboard/deploy.py --domain performance

# Sau inventory report
python script/dashboard/deploy.py --domain inventory

# Sau NSO task (thứ 3)
python script/dashboard/deploy.py --domain nso

# Sau weekly transport plan (thứ 5)
python script/dashboard/deploy.py --domain weekly_plan
```

### Update tất cả domains
```powershell
python script/dashboard/deploy.py --domain all
```

### Chỉ export JSON (không push)
```powershell
python script/dashboard/export_data.py --domain all
python script/dashboard/export_data.py --domain daily

# Weekly plan export riêng (không qua export_data.py)
python script/dashboard/export_weekly_plan.py
```

## Luồng xử lý

```
deploy.py --domain {name}
  ↓
export_data.py → đọc output/state/ + domain scripts
  ↓ (nếu domain = all/weekly_plan)
export_weekly_plan.py → đọc Excel + kiểm kê + NSO
  ↓
Ghi JSON → docs/data/{name}.json
  ↓
git add docs/ → git commit → git push origin main
  ↓
GitHub Pages tự deploy (~1-2 phút)
  ↓
Live tại: https://tunhipham.github.io/transport_daily_report/
```

## Dashboard Tabs

| Tab | Data file | Mô tả |
|-----|-----------|--------|
| 📦 Daily Report | `docs/data/daily.json` | KPI + chi tiết kho theo ngày |
| 🚛 Performance | `docs/data/performance.json` | Biểu đồ hiệu suất vận chuyển |
| 📋 Inventory | `docs/data/inventory.json` | Đối soát tồn kho |
| 🏪 NSO | `docs/data/nso.json` | Lịch khai trương + châm hàng |
| 📅 Lịch Tuần | `docs/data/weekly_plan.json` | Lịch về hàng ST theo tuần |

## Files liên quan

| File | Vai trò |
|------|---------| 
| `docs/index.html` | Dashboard SPA (5 tabs, Chart.js, xlsx-js-style) |
| `docs/data/*.json` | Data files per domain |
| `script/dashboard/export_data.py` | Export JSON cho daily/performance/inventory/nso |
| `script/dashboard/export_weekly_plan.py` | Export JSON cho weekly_plan |
| `script/dashboard/deploy.py` | Export + git commit + push |

## Timing cập nhật

| Domain | Khi nào chạy | Auto? |
|--------|-------------|-------|
| Daily | Sau khi gửi daily report lên Telegram | ✅ Auto (via `--send`) |
| Performance | Sau khi chạy thêm báo cáo ngày mới | ❌ Manual |
| Inventory | Sau khi có report đối soát | ❌ Manual |
| NSO | Thứ 3 — sau task quét mail + làm lịch | ❌ Manual |
| Weekly Plan | Thứ 5 — sau khi tạo lịch W+1 | ❌ Manual |

## Troubleshooting

- **Push fail**: Kiểm tra `git status`, resolve conflicts nếu có
- **Data trống**: Chạy report domain trước rồi mới deploy
- **GitHub Pages chưa update**: Chờ 2-3 phút, check Actions tab trên GitHub
- **Weekly plan lỗi**: Xem chi tiết tại workflow `/weekly-plan`
- **NSO store quá D+3 vẫn hiện**: Dashboard JS tự filter client-side (auto-hide `delta > 3`). Nếu cần cập nhật JSON sạch: `python script/dashboard/deploy.py --domain nso`

## Notes

> **NSO tab**: Dashboard có **client-side D+3 filter** — JS tự ẩn store quá D+3 dựa trên `new Date()`, dù `nso.json` chưa re-generate. Không cần re-deploy mỗi ngày chỉ để ẩn store cũ.
