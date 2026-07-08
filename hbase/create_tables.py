import happybase

def create_tables():
    conn = happybase.Connection('localhost')

    tables = {
        'business': {
            'info':     {},
            'location': {},
            'meta':     {},
        },
        'review': {
            'info':    {},
            'content': {},
        },
        'user': {
            'info':  {},
            'stats': {},
        },
        'checkin': {
            'data': {},
        },
        'tip': {
            'info': {},
        },
    }

    existing = [t.decode() for t in conn.tables()]
    for name, families in tables.items():
        if name in existing:
            print(f"Table '{name}' already exists, skipping.")
        else:
            conn.create_table(name, families)
            print(f"Created table '{name}'")

    conn.close()
    conn2 = happybase.Connection('localhost')
    print("\nDone. Tables:", [t.decode() for t in conn2.tables()])
    conn2.close()

if __name__ == '__main__':
    create_tables()
