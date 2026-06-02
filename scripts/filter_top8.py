import sqlite3

DB = 'ncaa_history.db'

with sqlite3.connect(DB) as conn:
    total = conn.execute('SELECT COUNT(*) FROM results').fetchone()[0]
    conn.execute('DELETE FROM results WHERE place IS NULL OR place > 8 OR is_dq = 1')
    conn.commit()
    remaining = conn.execute('SELECT COUNT(*) FROM results').fetchone()[0]
    print(f'Kept {remaining} of {total} rows ({total - remaining} removed)')
