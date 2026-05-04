# /update-external — Update & Deploy External Dashboard Data

> **Dành cho:** ThanhPhammm111 (external collaborator)
> **Mục đích:** Update dữ liệu Nhập/Xuất ĐM hoặc Claim ABA → auto deploy lên KFM Dashboard

## Tổng quan

Workflow này giúp update dữ liệu cho 2 tab external trên dashboard:
- 📊 **Nhập/Xuất ĐM** → `docs/external/nhap_xuat_dm.html`
- 📋 **Claim ABA** → `docs/external/claim_aba.html`

Sau khi update xong, script tự động tạo PR → GitHub Actions auto-approve + auto-merge → dashboard cập nhật trong ~2 phút.

## ⚠ Quy tắc

- ✅ **CHỈ ĐƯỢC** sửa 2 file trên → auto-deploy
- ❌ **KHÔNG ĐƯỢC** thêm file mới hoặc sửa `docs/index.html` → sẽ bị BLOCK
- ❌ **KHÔNG ĐƯỢC** sửa bất kỳ file nào ngoài `docs/external/` → sẽ bị BLOCK
- 💡 Nếu muốn thêm tab mới → liên hệ @tunhipham

## Steps

### Step 1: Update dữ liệu

Tùy thuộc vào yêu cầu của user, update data trong file HTML tương ứng:

**Nhập/Xuất ĐM** (`docs/external/nhap_xuat_dm.html`):
- Thêm dòng mới vào mảng `D[]` (dữ liệu xuất hàng theo ngày)
- Thêm vào `CT{}` (chi tiết SKU pick rớt)
- Thêm vào `NH{}` (dữ liệu nhập hàng)
- Thêm vào `DA[]` (tỷ lệ đáp ứng)
- Update title nếu chuyển tháng mới

**Claim ABA** (`docs/external/claim_aba.html`):
- Thêm dòng mới vào mảng `daily[]`
- Thêm tuần mới vào `CL_WEEKS[]` nếu cần
- Update title/subtitle cho tháng mới

### Step 2: Deploy lên dashboard

Sau khi update xong data, chạy deploy script:

```bash
python script/external/deploy.py
```

Hoặc với commit message tùy chỉnh:

```bash
python script/external/deploy.py -m "Update data T05 ngày 04/05"
```

Script sẽ tự động:
1. ✅ Kiểm tra chỉ có file whitelist thay đổi
2. 🌿 Tạo branch mới
3. 📤 Push + tạo PR
4. 🤖 GitHub Actions auto-approve + auto-merge
5. 🌐 Dashboard cập nhật trong ~2 phút

### Step 3: Xác nhận

Sau khi script chạy xong, kiểm tra:
- PR link được in ra → mở xem status
- Chờ ~1-2 phút → vào https://tunhipham.github.io/transport_daily_report/ → chọn tab tương ứng để verify

## Troubleshooting

| Lỗi | Giải pháp |
|-----|-----------|
| `gh: command not found` | Cài GitHub CLI: https://cli.github.com/ |
| `gh auth` lỗi | Chạy `gh auth login` |
| BLOCK — file ngoài whitelist | Chỉ sửa 2 file trong whitelist, không thêm file mới |
| PR conflict | `git checkout main && git pull origin main` rồi thử lại |
