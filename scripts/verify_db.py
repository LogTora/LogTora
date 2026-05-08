import os
import sys

from dotenv import load_dotenv
import psycopg2

load_dotenv()


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()

        cur.execute("SELECT version();")
        pg_version = cur.fetchone()[0].split(",")[0]
        print(pg_version)

        cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
        row = cur.fetchone()
        if row is None:
            print("ERROR: pgvector extension not installed", file=sys.stderr)
            sys.exit(1)
        print(f"pgvector {row[0]}")

        cur.execute("SELECT COUNT(*) FROM facts;")
        count = cur.fetchone()[0]
        print(f"facts table: {count} rows")

        print("OK")
        cur.close()
        conn.close()

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
