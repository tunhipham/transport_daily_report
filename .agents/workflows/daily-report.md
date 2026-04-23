---
description: Daily report automation - download data and generate summary report
---

# Daily Report Workflow

// turbo-all

## ⚠ Required

Read `agents/prompts/daily-report.md` trước khi chạy.

## Run

```
python -u script/domains/daily/generate.py --send
```
Hoặc chỉ định ngày:
```
python -u script/domains/daily/generate.py --date DD/MM/YYYY --send
```

## Expected Output

- Summary cards: Tổng Tấn, Xe, Siêu thị, Items
- KPI table per kho (5 kho)
- Charts: 5 PNG → Telegram (gửi tới **tất cả groups** trong `daily.chat_ids[]`)
- Telegram: tin nhắn thông báo + dashboard link (multi-group)
- Auto-deploy dashboard lên GitHub Pages

## Validation

- THỊT CÁ, KRC: always present (7/7)
- ĐÔNG MÁT: no Monday
- KSL: no Sunday (except small trips)
- Missing data = warning → check source

## Deploy (nếu auto-deploy lỗi)

```
python -u script/dashboard/deploy.py --domain daily
```

## Troubleshooting

Script lỗi? → Đọc `agents/reference/daily-report-detail.md` trước khi sửa code.
