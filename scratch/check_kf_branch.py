import requests
import json
import codecs

url = 'http://103.140.248.114:32015/'
auth = ('scm_lam', 'xukco1-roghaB-fuqfum')

q = 'SELECT id, branch_code, branch_name FROM kdb.kf_branch_location LIMIT 3'
res = requests.post(url, auth=auth, params={'database': 'kdb', 'query': q + " FORMAT JSON"})

with codecs.open('scratch/kf_branch_sample.json', 'w', 'utf-8') as f:
    json.dump(res.json()['data'], f, ensure_ascii=False, indent=2)
