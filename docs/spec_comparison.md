# So Sánh: Production Spec vs Docs Hiện Tại

## Hiện tại có 2 files:
1. **`performance_report_workflow.md`** (73 dòng) — workflow ngắn gọn, chạy step-by-step
2. **`performance_report_implementation_plan.md`** (417 dòng) — business logic chi tiết, data contract, fallback chains

## So sánh từng section của Production Spec

| # | Section | Đã có? | Ở đâu? | Cần thêm? |
|---|---|---|---|---|
| 1 | Overview | ✅ | impl_plan §Tổng quan | Không |
| 2 | Source of Truth | ✅ | impl_plan §Data Loading | Gom lại thành bảng rõ hơn |
| 3 | Data Contract (Input) | ✅ | impl_plan §1.1, §1.2 | Đã chi tiết hơn spec |
| 4 | Data Contract (Output) | ❌ | — | **CẦN THÊM** |
| 5 | KPI Logic (Versioned) | ✅ | impl_plan §2-§5 | **Thêm version tag** |
| 6 | Config Management | ❌ | Hardcode trong script | **CẦN THÊM** |
| 7 | Workflow steps | ✅ | workflow.md | Không |
| 8 | Output Naming Convention | ❌ | Hardcode `RAW_DATA_{months}_{year}` | **CẦN THÊM** |
| 9 | Data Quality Checks | ⚠ Bán phần | Script verify cuối | **CẦN NÂNG CẤP** |
| 10 | Idempotency | ✅ | Script overwrite output | Chỉ cần ghi rõ |
| 11 | Logging | ❌ | print() ra console | **CẦN THÊM** |
| 12 | Failure Handling | ⚠ Bán phần | try/except per file | **CẦN NÂNG CẤP** |
| 13 | Data Lineage | ✅ | impl_plan §Kiến trúc | Đã có diagram |
| 14 | Verification Checklist | ✅ | workflow.md cuối | Không |
| 15 | Backup & Git | ✅ | workflow.md | Không |
| 16 | Storage Rules | ✅ | workflow.md | Không |
| 17 | Environment | ❌ | — | **CẦN THÊM** |
| 18 | Known Gotchas | ✅ | impl_plan | Bổ sung |

---

## Nhận xét

### ✅ Cái đang có TỐT HƠN spec:
- **Business logic** chi tiết hơn nhiều (fallback chains, sub_kho dedup, KSL session split...)
- **Data loading** ghi rõ từng cột, index, source file path
- Đã có **ĐÔNG/MÁT dedup** logic (spec chưa cover)

### ❌ Cái spec có mà mình THIẾU → cần thêm:

#### 1. **Config externalization** (quan trọng nhất!)
Hiện tại SLA windows, kho mapping, colors đều **hardcode** trong script. Mỗi lần sửa phải vô code.
→ Tách ra thành JSON config:
- `config/sla_rules.json` — SLA windows per kho
- `config/kho_mapping.json` — noi_chuyen → kho mapping

#### 2. **Data Quality Gates** (FAIL vs WARNING)
Script hiện chỉ print warning. Cần:
- `FAIL` = stop pipeline (planned_time null > 5%, unknown kho)  
- `WARNING` = continue nhưng log (KPI drop > 20%)

#### 3. **Logging to file**
Hiện chỉ `print()`. Nên tee vào file `logs/performance_report_{timestamp}.log`

#### 4. **Versioned output naming**
Hiện: `RAW_DATA_T03+T04_2026.xlsx` (overwrite)
Spec: `RAW_DATA_T03+T04_2026_v1_20260410.xlsx`
→ Giữ history, rollback dễ hơn

#### 5. **Output data contract**
Ghi rõ schema output Excel: cột nào, kiểu gì, giá trị hợp lệ

#### 6. **Environment / requirements.txt**
Chưa có file requirements → người mới không cài đc

### ⚠ Cái spec có nhưng CHƯA CẦN THIẾT ngay:
- **KPI version bumping** — hay nhưng workflow bạn chưa phức tạp đến mức cần
- **"No fallback to partial data"** — thực tế sếp vẫn muốn xem report dù thiếu vài ngày
- **pandas dependency** — script hiện **KHÔNG** dùng pandas (chỉ openpyxl + numpy) → spec sai

---

## Đề xuất: Merge docs

Hiện tại logic nằm rải rác 2 file. Nên **merge thành 1 production spec**:

```
docs/performance_report_spec.md     ← MỚI (merge tất cả)
docs/performance_report_workflow.md ← GIỮ (workflow ngắn cho agent chạy)
```

### Cấu trúc production spec mới:
1. Overview + Source of Truth
2. Data Contract (Input + Output)  
3. KPI Logic (v1) + Sub-kho + Dedup
4. Config (externalized files)
5. Data Quality Gates (FAIL/WARN)
6. Pipeline flow + Logging
7. Output naming + Storage
8. Verification + Known Gotchas
9. Environment + Git

---

## Ưu tiên implement

| Priority | Item | Effort | Impact |
|---|---|---|---|
| 🔴 P0 | Config externalization (SLA, kho mapping) | 2h | Giảm risk sửa code |
| 🔴 P0 | Data quality gates (FAIL/WARN) | 1h | Ngăn output sai |
| 🟡 P1 | Logging to file | 30min | Debug dễ hơn |
| 🟡 P1 | Merge docs thành 1 spec | 1h | Rõ ràng hơn |
| 🟢 P2 | Versioned output naming | 30min | History |
| 🟢 P2 | requirements.txt | 5min | Onboarding |
