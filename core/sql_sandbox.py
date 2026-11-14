"""
DataSentinel QA - Interactive SQL Query Sandbox
Allows users to run arbitrary analytical SQL queries over active CSV datasets in memory.
"""

import sqlite3
import time
from typing import List, Dict, Any, Tuple

class SQLSandbox:
    @staticmethod
    def execute_query(rows: List[Dict], sql_query: str) -> Dict[str, Any]:
        """Loads row dictionaries into an in-memory SQLite table and runs user query."""
        if not rows:
            return {"error": "Dataset is empty", "columns": [], "rows": [], "duration": "0ms"}

        t0 = time.time()
        conn = sqlite3.connect(":memory:")
        cur = conn.cursor()

        # Create table dynamically from first row keys
        cols = list(rows[0].keys())
        col_defs = ", ".join([f'"{c}" TEXT' for c in cols])
        cur.execute(f"CREATE TABLE transactions ({col_defs})")

        # Insert rows
        placeholders = ", ".join(["?"] * len(cols))
        data_tuples = [[r.get(c, "") for c in cols] for r in rows]
        cur.executemany(f"INSERT INTO transactions VALUES ({placeholders})", data_tuples)

        try:
            cur.execute(sql_query)
            res_rows = cur.fetchall()
            col_names = [desc[0] for desc in cur.description] if cur.description else []
            duration = f"{round((time.time() - t0) * 1000, 2)}ms"

            # Limit to 100 rows for display
            display_rows = res_rows[:100]
            conn.close()

            return {
                "columns": col_names,
                "rows": display_rows,
                "total_returned": len(res_rows),
                "duration": duration,
                "error": None
            }
        except Exception as e:
            conn.close()
            return {
                "columns": [],
                "rows": [],
                "total_returned": 0,
                "duration": f"{round((time.time() - t0) * 1000, 2)}ms",
                "error": str(e)
            }
