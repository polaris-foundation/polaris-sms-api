from typing import Any, Dict

import psycopg2
from environs import Env


def execute_query(query: str, params: Dict[str, Any]) -> None:
    env = Env()
    conn = psycopg2.connect(
        host=env.str("DATABASE_HOST"),
        database=env.str("DATABASE_NAME"),
        user=env.str("DATABASE_USER"),
        password=env.str("DATABASE_PASSWORD"),
        port=env.str("DATABASE_PORT", 5432),
    )
    cur = conn.cursor()
    cur.execute(query, params)
    cur.close()
    conn.commit()
    conn.close()
