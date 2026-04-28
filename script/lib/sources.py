# -*- coding: utf-8 -*-
"""
Shared data source URLs & paths used by multiple domains.
Centralized here to avoid duplication and sync issues.
"""

# ── Google Sheets (export as XLSX) ──
KRC_SHEET_URL = "https://docs.google.com/spreadsheets/d/1tWamqjpOI2j2MrYW3Ah6ptmT524CAlQvEP8fCkxfuII/export?format=xlsx"
KFM_SHEET_URL = "https://docs.google.com/spreadsheets/d/1LkJFJhOQ8F2WEB3uCk7kA2Phvu8IskVi3YBfVr7pBx0/export?format=xlsx"
MASTER_SHEET_URL = "https://docs.google.com/spreadsheets/d/1TG9m1xf1Yhgui-KzXo5l67689bAwcifY/export?format=xlsx"

# ── Inventory schedule (kiểm kê) ──
INVENTORY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1KIXDqGDW60sKNXuHOriT8utPTyhV-pCy11jlf18Zz-0/export?format=xlsx"

# ── Google Drive folders (Drive API) ──
KH_MEAT_FOLDER_URL = "https://drive.google.com/drive/folders/1GIzH8nmCbLhWfpdmxFIn9cHTvQNbnwWr"
TRANSFER_FOLDER_URL = "https://drive.google.com/drive/folders/17Z_UPMDywWFplcg0fx3XSG87vSsG8LHb"
YECAU_FOLDER_URL = "https://drive.google.com/drive/folders/1DpDon0QHhDRoX7_ZnEygwKlXsbcPGp-t"

# ── Local Google Drive sync paths ──
KH_DONG_LOCAL = r"G:\My Drive\DOCS\DAILY\KH HÀNG ĐÔNG"
KH_MAT_LOCAL = r"G:\My Drive\DOCS\DAILY\KH HÀNG MÁT"
KH_MEAT_LOCAL = r"G:\My Drive\DOCS\DAILY\KH MEAT"
TRANSFER_LOCAL = r"G:\My Drive\DOCS\DAILY\transfer"

# ── Inventory (ton_aba) local data ──
DOI_SOAT_DIR = r"G:\My Drive\DOCS\DAILY\ton_aba\data\doi_soat"
MASTER_DATA_FILE = r"G:\My Drive\DOCS\DAILY\ton_aba\data\master_data\Master Data.xlsx"
WEIGHT_DATA_FILE = r"G:\My Drive\DOCS\DAILY\Sản phẩm thường - Thông tin cơ bản.xlsx"

# ── NSO ──
NSO_DATA_DIR = r"G:\My Drive\DOCS\DAILY\LICH DI HANG DC"

# ── DSST (Danh sách siêu thị — store lookup for NSO) ──
DSST_SHEET_URL = "https://docs.google.com/spreadsheets/d/1byEE8KterdcRr10IydIjbPcJcQwhX2HtGBzd0VZ5N1k/export?format=xlsx"
DSST_GID = 1655867479  # Sheet gid chứa danh sách ST
