# Tích hợp folder bên ngoài vào Dashboard

> Ngày ghi nhận: 23/04/2026  
> Trạng thái: **Chưa xử lý** — chờ bạn kia ready

## Bối cảnh

- Có 1 người khác làm việc trên **Google Drive folder riêng** của họ
- Họ tự code, tự update data trong folder đó
- Mục tiêu: đưa output của họ lên thành **1 tab mới** trong dashboard KFM Logistics

## Kiến trúc hiện tại

Dashboard dùng mô hình **JSON → static HTML tabs**, deploy GitHub Pages:

```
docs/
├── index.html          ← Dashboard HTML (all tabs)
└── data/
    ├── daily.json       ← Tab "Daily"
    ├── performance.json ← Tab "Performance"
    ├── inventory.json   ← Tab "Tồn Kho"
    ├── nso.json         ← Tab "NSO"
    └── weekly_plan.json ← Tab "Lịch Tuần"
```

Mỗi tab chỉ cần **1 file JSON** trong `docs/data/`.

## Giải pháp

### Flow

```
Bạn kia (Drive riêng)                 Dashboard (repo này)
┌─────────────────────┐               ┌──────────────────────┐
│  Code + chạy script │               │  docs/data/          │
│  → output JSON      │──── copy ────▶│    domain_moi.json   │
│  (folder Drive kia) │               │  → deploy GitHub     │
└─────────────────────┘               └──────────────────────┘
```

### Điều kiện

1. **Access**: Bạn kia share folder Drive (hoặc mount Shared Drive) để mình đọc được
2. **Output format**: 1 file JSON duy nhất, có field `_updated` (timestamp)
3. **Không cần folder tổng**: Chỉ cần 1 file JSON output là đủ

### Tự động hóa

Thêm 1 step trong `deploy.py` hoặc `export_data.py`:

```python
# Copy JSON từ folder Drive bạn kia → docs/data/
EXTERNAL_JSON = "G:/Shared drives/BanKia/output/data.json"  # path thật
if os.path.exists(EXTERNAL_JSON):
    shutil.copy(EXTERNAL_JSON, os.path.join(DOCS_DATA, "domain_moi.json"))
```

## TODO khi triển khai

- [ ] Xác nhận path folder Drive của bạn kia
- [ ] Thống nhất JSON format (fields, structure)
- [ ] Thêm tab mới trong `docs/index.html`
- [ ] Thêm export step trong `deploy.py`
- [ ] Test end-to-end
