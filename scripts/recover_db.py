import sqlite3
import os
import sys
import shutil
from pathlib import Path

# Ensure project root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

db_path = Path("storage/cricketiq.db")
bak_path = Path("storage/cricketiq.db.corrupt_bak")
recovered_path = Path("storage/cricketiq.db.new")

if db_path.exists():
    shutil.move(db_path, bak_path)

# Initialize clean schema in new db using session_repository logic
from backend.app.repositories.session_repository import SessionRepository
new_repo = SessionRepository(db_path=recovered_path)

# Open corrupt db in read-only mode and copy rows
src_conn = sqlite3.connect(f"file:{bak_path}?mode=ro", uri=True)
src_cur = src_conn.cursor()

dst_conn = sqlite3.connect(recovered_path)
dst_cur = dst_conn.cursor()

# Enable WAL mode for better concurrency in SQLite!
dst_conn.execute("PRAGMA journal_mode = WAL;")
dst_conn.execute("PRAGMA synchronous = NORMAL;")

tables = ["sessions", "analysis_results", "coaching_feedback", "comparison_sessions"]
for t in tables:
    print(f"Recovering table {t}...")
    try:
        src_cur.execute(f"SELECT * FROM {t}")
        # Fetch columns
        col_names = [desc[0] for desc in src_cur.description]
        placeholders = ", ".join(["?"] * len(col_names))
        cols_str = ", ".join(col_names)
        
        recovered_count = 0
        error_count = 0
        while True:
            try:
                row = src_cur.fetchone()
                if row is None:
                    break
                dst_cur.execute(f"INSERT OR REPLACE INTO {t} ({cols_str}) VALUES ({placeholders})", row)
                recovered_count += 1
            except Exception as row_err:
                error_count += 1
                
        dst_conn.commit()
        print(f"  Table {t}: recovered {recovered_count} rows (skipped {error_count} damaged)")
    except Exception as t_err:
        print(f"  Table {t} error: {t_err}")

src_conn.close()
dst_conn.close()

# Verify integrity
check_conn = sqlite3.connect(recovered_path)
cur = check_conn.cursor()
cur.execute("PRAGMA integrity_check;")
res = cur.fetchall()
print("Integrity check on recovered DB:", res)
check_conn.close()

if res == [("ok",)]:
    shutil.copy2(recovered_path, db_path)
    print("Clean database installed at storage/cricketiq.db!")
else:
    print("Integrity check failed!")
