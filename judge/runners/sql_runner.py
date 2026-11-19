import json
import sqlite3

payload = json.loads(open("/source/input.json", encoding="utf-8").read())
query = open("/source/solution.sql", encoding="utf-8").read().strip()
database = sqlite3.connect(":memory:")
for table_name, table in payload["tables"].items():
    if not table_name.replace("_", "").isalnum():
        raise ValueError("Invalid table name")
    definitions = []
    for name, data_type in table["columns"]:
        if not name.replace("_", "").isalnum() or data_type not in {"TEXT", "INTEGER", "REAL"}:
            raise ValueError("Invalid schema")
        definitions.append(f'"{name}" {data_type}')
    database.execute(f'CREATE TABLE "{table_name}" ({", ".join(definitions)})')
    placeholders = ",".join("?" for _ in table["columns"])
    database.executemany(f'INSERT INTO "{table_name}" VALUES ({placeholders})', table["rows"])

denied = {
    sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_CREATE_INDEX,
    sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_CREATE_TRIGGER, sqlite3.SQLITE_CREATE_VIEW,
    sqlite3.SQLITE_DELETE, sqlite3.SQLITE_DROP_INDEX, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_DROP_TRIGGER,
    sqlite3.SQLITE_DROP_VIEW, sqlite3.SQLITE_INSERT, sqlite3.SQLITE_PRAGMA, sqlite3.SQLITE_REINDEX,
    sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_UPDATE,
}
database.set_authorizer(lambda action, *_: sqlite3.SQLITE_DENY if action in denied else sqlite3.SQLITE_OK)
cursor = database.execute(query)
rows = cursor.fetchmany(1001)
if len(rows) > 1000:
    raise ValueError("Result exceeds 1000 rows")
print("__EKLAVYA_RESULT__" + json.dumps({"columns": [item[0] for item in cursor.description], "rows": rows}, separators=(",", ":")))
