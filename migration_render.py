import psycopg2
import os

# LOCAL
local_conn = psycopg2.connect(
    host="localhost",
    database="carrefour_brest",
    user="postgres",
    password="postgresql123",
    port="5432"
)

# RENDER
render_conn = psycopg2.connect(
    "postgresql://carrefour_brest_user:hSPG02cXnekLY4kndBl9D35BrxLnG4e7@dpg-d81jepl0lvsc7392grug-a.frankfurt-postgres.render.com/carrefour_brest?sslmode=require"
)

local_cursor = local_conn.cursor()
render_cursor = render_conn.cursor()

tables = [
    "users",
    "rayons",
    "produits",
    "services",
    "service_alias",
    "recherches_introuvables"
]

for table in tables:

    local_cursor.execute(f"SELECT * FROM {table}")
    rows = local_cursor.fetchall()

    if not rows:
        continue

    placeholders = ",".join(["%s"] * len(rows[0]))

    for row in rows:
        render_cursor.execute(
            f"INSERT INTO {table} VALUES ({placeholders})",
            row
        )

    print(f"{table} migrée")

render_conn.commit()

local_conn.close()
render_conn.close()

print("Migration terminée ✅")