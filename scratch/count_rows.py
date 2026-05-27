import sys, os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "script"))
from data_pipeline.config import load_clickhouse_config
import requests
import json

KRC_BRANCH_ID = '5fdc170ebd89c10006f15b7c'
cfg = load_clickhouse_config()

sql = f"""
SELECT
    formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date_vendor_confirm)), '%d/%m/%Y') AS del_date,
    count() as c
FROM kf_receipt_items ri
INNER JOIN kf_purchase_order po
    ON ri.purchase_code = po.code
    AND po.branch_id = '{KRC_BRANCH_ID}'
    AND po.deleted = 0
    AND NOT has(po.list_sub_status, 11)
WHERE ri.branch_id = '{KRC_BRANCH_ID}'
  AND formatDateTime(fromUnixTimestamp(toUInt32(po.delivery_date_vendor_confirm)), '%d/%m/%Y') IN ('25/05/2026', '26/05/2026', '27/05/2026', '28/05/2026')
GROUP BY del_date
ORDER BY del_date
FORMAT JSONEachRow
"""

r = requests.get(
    cfg['base_url'],
    params={
        'user': cfg['user'],
        'password': cfg['password'],
        'database': cfg['database'],
        'query': sql
    }
)
print(r.text)
