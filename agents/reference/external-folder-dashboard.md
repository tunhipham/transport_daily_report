# Tích hợp folder bên ngoài vào Dashboard

> Ngày ghi nhận: 23/04/2026  
> Cập nhật: 24/04/2026  
> Trạng thái: **Chờ xác nhận path + nội dung tab** — kiến trúc đã rõ

## Bối cảnh

- Có 1 người khác làm việc trên **Google Drive folder riêng** (`Report nhap.xuat/`)
- Họ tự code, tự update data trong folder đó
- Mục tiêu: đưa output của họ lên thành **1 tab mới** ("Nhập Xuất") trong dashboard KFM Logistics

## Nguyên tắc thiết kế (QUAN TRỌNG)

1. **Isolation hoàn toàn** — Folder ngoài lỗi → chỉ tab đó fallback, KHÔNG ảnh hưởng dashboard
2. **Không đọc trực tiếp** — Dashboard KHÔNG đọc raw folder của họ, luôn đi qua adapter
3. **Theo convention hệ thống** — Tạo domain `nhap_xuat` như daily, inventory, nso...
4. **Fail-safe** — Adapter lỗi → không overwrite JSON cũ, tab hiển thị data cũ hoặc fallback

## Cấu trúc folder bên ngoài (tham khảo)

```
Report nhap.xuat/
├── Data/
│   ├── Xuat/transfer_*.xlsx
│   └── MSDT.xlsx
├── Output/
│   ├── {dd.mm}/              ← Output theo ngày
│   │   ├── bang1.png / bang1.html
│   │   └── bang2.png / bang2.html
│   ├── dulieuxuat/*.xlsx     ← Data đã xử lý
│   └── san_luong_xuat_T04.html
└── Workflow/huong_dan_chay_lenh.md
```

> **Lưu ý**: Cấu trúc này có thể thay đổi bất cứ lúc nào. Adapter phải handle gracefully.

## Kiến trúc tích hợp

### Flow

```
Bên ngoài (Drive riêng)                    Hệ thống (repo này)
┌───────────────────────┐                  ┌──────────────────────────────┐
│ Report nhap.xuat/     │                  │ script/domains/nhap_xuat/    │
│   Output/             │───adapter───────▶│   generate.py                │
│     {dd.mm}/bang*.png │                  │                              │
│     dulieuxuat/*.xlsx │                  │ output/state/                │
└───────────────────────┘                  │   nhap_xuat.json             │
                                           │                              │
                                           │ export_data.py               │
                                           │   → docs/data/nhap_xuat.json │
                                           │                              │
                                           │ docs/index.html              │
                                           │   → Tab "Nhập Xuất"         │
                                           └──────────────────────────────┘
```

### Isolation mechanism

Dashboard hiện tại đã có cơ chế isolate sẵn:

```python
# export_data.py — mỗi domain export độc lập
for name, fn in exporters.items():
    try:
        results[name] = fn()
    except Exception as e:
        results[name] = False  # ← fail domain này, domain khác vẫn chạy
```

Client-side cũng load từng JSON riêng → `nhap_xuat.json` fail thì chỉ tab đó fallback.

### Files cần tạo/sửa

| Action | File | Mô tả |
|--------|------|-------|
| **NEW** | `script/domains/nhap_xuat/generate.py` | Adapter: đọc folder ngoài → `output/state/nhap_xuat.json` |
| **MODIFY** | `script/dashboard/export_data.py` | Thêm `export_nhap_xuat()` |
| **MODIFY** | `script/dashboard/deploy.py` | Thêm `"nhap_xuat"` vào domain choices |
| **MODIFY** | `docs/index.html` | Thêm tab "Nhập Xuất" |
| **MODIFY** | `agents/reference/architecture.md` | Cập nhật diagram |

## TODO trước khi triển khai

- [ ] **Xác nhận path mount** — Folder `Report nhap.xuat/` mount ở đâu? (`G:\...`)
- [ ] **Xác nhận nội dung tab** — Show ảnh bang1/bang2? Parse Excel? Cả hai?
- [ ] Bạn kia share folder read access
- [ ] Code adapter `generate.py`
- [ ] Tích hợp vào `export_data.py` + `deploy.py`
- [ ] Thêm tab mới vào `index.html`
- [ ] Test end-to-end + test fallback khi folder không có
