# /dashboard — Update Live Dashboard

> Cập nhật dashboard web sau khi chạy xong report.
> URL: https://tunhipham.github.io/transport_daily_report/

> [!NOTE]
> **Daily domain tự động deploy** khi chạy `generate.py --send`.
> Chỉ cần chạy manual deploy cho các domain khác (performance, inventory, nso) hoặc khi cần re-deploy.

## Prerequisites
- Report domain tương ứng đã chạy xong (daily/performance/inventory/nso)
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
```

### Update tất cả domains
```powershell
python script/dashboard/deploy.py --domain all
```

### Chỉ export JSON (không push)
```powershell
python script/dashboard/export_data.py --domain all
python script/dashboard/export_data.py --domain daily
```

## Luồng xử lý

```
deploy.py --domain {name}
  ↓
export_data.py → đọc output/state/ + domain scripts
  ↓
Ghi JSON → docs/data/{name}.json
  ↓
git add docs/ → git commit → git push origin main
  ↓
GitHub Pages tự deploy (~1-2 phút)
  ↓
Live tại: https://tunhipham.github.io/transport_daily_report/
```

## Files liên quan

| File | Vai trò |
|------|---------|
| `docs/index.html` | Dashboard SPA (4 tabs, Chart.js) |
| `docs/data/*.json` | Data files per domain |
| `script/dashboard/export_data.py` | Export JSON từ state/cache |
| `script/dashboard/deploy.py` | Export + git commit + push |

## Timing cập nhật

| Domain | Khi nào chạy | Auto? |
|--------|-------------|-------|
| Daily | Sau khi gửi daily report lên Telegram | ✅ Auto (via `--send`) |
| Performance | Sau khi chạy thêm báo cáo ngày mới | ❌ Manual |
| Inventory | Sau khi có report đối soát | ❌ Manual |
| NSO | Thứ 3 — sau task quét mail + làm lịch | ❌ Manual |

## Troubleshooting

- **Push fail**: Kiểm tra `git status`, resolve conflicts nếu có
- **Data trống**: Chạy report domain trước rồi mới deploy
- **GitHub Pages chưa update**: Chờ 2-3 phút, check Actions tab trên GitHub
