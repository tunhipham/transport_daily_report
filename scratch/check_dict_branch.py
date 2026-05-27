import requests
import json
import codecs

url = 'http://103.140.248.114:32015/'
auth = ('scm_lam', 'xukco1-roghaB-fuqfum')

q = 'SELECT id, branch_code, branch_name FROM kdb.dict_branch_location LIMIT 10'
res = requests.post(url, auth=auth, params={'database': 'kdb', 'query': q + " FORMAT JSON"})

if res.status_code == 200:
    data = res.json()
    with codecs.open('scratch/branch_sample.json', 'w', 'utf-8') as f:
        json.dump(data['data'], f, ensure_ascii=False, indent=2)
    print("Saved sample to branch_sample.json")
else:
    print(res.text)
