import json, pathlib, pymysql
root=pathlib.Path(__file__).resolve().parents[1]
try:
 c=pymysql.connect(host='127.0.0.1',port=3307,user='root',password=json.loads((root/'.local-config.json').read_text())['rootPassword'])
 with c.cursor() as q:q.execute('SHUTDOWN')
 print('Project MySQL stopped gracefully')
except pymysql.err.OperationalError as e:
 if e.args[0] != 2003: raise
