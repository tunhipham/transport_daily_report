---
description: Manual fetch + compose + inject after cutoff hours (backup procedure)
---

# Backup Inject Workflow

// turbo-all

> Chi tiết rules, troubleshooting → xem `agents/prompts/backup-inject.md`

## Prerequisites

- **Đọc `agents/role.md` trước** — nguyên tắc chung, phạm vi, quy ước output

## Khi nào dùng?

Khi **đã qua cutoff** mà cần inject lại (data trễ, lỗi inject...).

## 🚨 Pre-flight (BẮT BUỘC — trước khi chạy bất kỳ lệnh nào)

> [!CAUTION]
> Xác nhận ngày TRƯỚC KHI chạy. KHÔNG tự suy luận.

- **KRC / ĐÔNG MÁT / THỊT CÁ / DRY Sáng** → `--date` = **D+1** (ngày mai)
- **DRY Tối** → `--date` = D (cùng ngày)
- ⛔ Compose kho A → inject kho A → rồi mới compose kho B. KHÔNG compose nhiều kho rồi inject.

## Steps

### 1. Check status
```
python -u script/compose/auto_compose.py --status
```
Chỉ backup kho có status `composed` (chưa inject).

### 2. Fetch data mới nhất
```
python -u script/domains/performance/fetch_weekly.py --week W{week} --start DD/MM/YYYY
```

### 3. Compose + Inject tuần tự (từng kho)

> ⚠️ **Compose kho nào → inject ngay kho đó** trước khi compose kho tiếp.
> Generic `_mail_body.html` bị ghi đè mỗi lần compose → inject sau có thể dùng nhầm data.

> ℹ️ Inject dùng **JS base64 + setData()** — không phụ thuộc clipboard, hoạt động từ mọi session.

> ✅ **THỊT CÁ**: fetch = chốt → compose + inject luôn (data chính xác từ lần fetch đầu).
> ⚠️ **ĐÔNG MÁT**: phải đủ cả 2 file (KH HÀNG ĐÔNG + KH HÀNG MÁT) mới compose. Nếu chỉ có 1 → chờ.

**KRC:**
```
python -u script/compose/compose_mail.py --kho KRC --date DD/MM/YYYY
python -u script/compose/inject_haraworks.py --kho KRC --date DD/MM/YYYY --week W{week}
```

**ĐÔNG MÁT:**
```
python -u script/compose/compose_mail.py --kho "DONG MAT" --date DD/MM/YYYY
python -u script/compose/inject_haraworks.py --kho "DONG MAT" --date DD/MM/YYYY --week W{week}
```

**THỊT CÁ:**
```
python -u script/compose/compose_mail.py --kho "THIT CA" --date DD/MM/YYYY
python -u script/compose/inject_haraworks.py --kho "THIT CA" --date DD/MM/YYYY --week W{week}
```

**DRY Sáng:**
```
python -u script/compose/compose_mail.py --kho DRY --session sang --date DD/MM/YYYY
python -u script/compose/inject_haraworks.py --kho DRY --session sang --date DD/MM/YYYY --week W{week}
```

**DRY Tối:**
```
python -u script/compose/compose_mail.py --kho DRY --session toi --date DD/MM/YYYY
python -u script/compose/inject_haraworks.py --kho DRY --session toi --date DD/MM/YYYY --week W{week}
```

> ⚠️ **TUYỆT ĐỐI KHÔNG dùng `--new`** — tự dò thread → reply nếu có, tạo mới nếu chưa.

### 4. Review draft trên Haraworks → Gửi
