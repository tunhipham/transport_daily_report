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
                for k, v in row_dict.items():
                    if v.__class__.__name__ == 'datetime':
                        row_dict[k] = str(v)
                data.append(row_dict)
        conn.close()
        return data
    except Exception as e:
        return f"Error: {e}"

out = {
    "tables_in_scm": get_data("SHOW TABLES")
}

with codecs.open('scratch/data_sample3.json', 'w', 'utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
