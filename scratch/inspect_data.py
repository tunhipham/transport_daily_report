import pymysql
import json
import codecs

def get_data(query):
    try:
        conn = pymysql.connect(
            host="103.147.122.56",
            port=9030,
            user="kfm_scm_lam_nguyen",
            password="QPYZfjWWhJcHNi5ab5Au",
            database="kfm_scm"
        )
        data = []
        with conn.cursor() as cursor:
            cursor.execute(query)
            res = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            for row in res:
                row_dict = dict(zip(cols, row))
                # Convert any non-serializable objects (like datetime) to string
                for k, v in row_dict.items():
                    if v.__class__.__name__ == 'datetime':
                        row_dict[k] = str(v)
                data.append(row_dict)
        conn.close()
        return data
    except Exception as e:
        return f"Error: {e}"

out = {
    "tickets": get_data("SELECT _id, vendor_code, vendor_name, code, hrw_id FROM __cdc_kfm_kf_inventories_kf_hrw_quality_tickets LIMIT 3"),
    "tickets_items": get_data("SELECT _parent_id, item_code, item_name, quantity, original_quantity, total_sample_quantity, support_rate, min_sample_percent, max_sample_percent FROM __cdc_kfm_kf_inventories_kf_hrw_quality_tickets___items LIMIT 3"),
    "claim_txn_details": get_data("SELECT _id, barcode, object_code, transaction_quantity, claim_quantity, ratio, claim_stock, transaction_stock FROM __cdc_kfm_kf_inventories_kf_claim_transaction_details LIMIT 3"),
    "claim_stock_summaries": get_data("SELECT _id, base_variant_id, on_hand, claim_quantity, ratio FROM __cdc_kfm_kf_inventories_kf_claim_stock_summaries LIMIT 3"),
    "claim_tickets": get_data("SELECT _id, code, barcode, product_name, requested_qty, claim_pt_qty, inventory_transfer__code FROM __cdc_kfm_kf_inventories_kf_claim_tickets LIMIT 3")
}

with codecs.open('scratch/data_sample.json', 'w', 'utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
