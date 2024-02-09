
def test_json1():
    import sqlite3

    conn = sqlite3.connect(':memory:')
    try:
        conn.execute('SELECT json(\'{"key": "value"}\')')
        print('JSON1-Erweiterung ist verfügbar.')
    except sqlite3.OperationalError:
        print('JSON1-Erweiterung ist nicht verfügbar.')
    finally:
        conn.close()

if __name__ == '__main__':
    test_json1()