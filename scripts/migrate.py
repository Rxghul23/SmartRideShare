"""Additive, repeatable local migrations; existing rides and accounts are preserved."""
import json
from pathlib import Path
import pymysql

root = Path(__file__).resolve().parents[1]
config = json.loads((root / '.local-config.json').read_text())
connection = pymysql.connect(host='127.0.0.1', port=3307, user='root',
                             password=config['rootPassword'], database='smartride', autocommit=True)
try:
    with connection.cursor() as cursor:
        for path in sorted((root / 'database').glob('[0-9]*.sql')):
            for statement in path.read_text(encoding='utf-8-sig').split(';'):
                if statement.strip():
                    cursor.execute(statement)
            print('Database ready:', path.name)
finally:
    connection.close()
