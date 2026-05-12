import sqlite3
import psycopg2

# SQLITE
sqlite_conn = sqlite3.connect("database.db")
sqlite_cursor = sqlite_conn.cursor()

# POSTGRESQL
pg_conn = psycopg2.connect(
    host="localhost",
    database="carrefour_brest",
    user="postgres",
    password="postgresql123",
    port="5432"
)

pg_cursor = pg_conn.cursor()


# -------------------
# RAYONS
# -------------------

sqlite_cursor.execute("SELECT * FROM rayons")
rayons = sqlite_cursor.fetchall()

for rayon in rayons:
    pg_cursor.execute("""
        INSERT INTO rayons (id, nom, numero_allee)
        VALUES (%s, %s, %s)
    """, rayon)

print("Rayons migrés ✅")


# -------------------
# PRODUITS
# -------------------

sqlite_cursor.execute("SELECT * FROM produits")
produits = sqlite_cursor.fetchall()

for produit in produits:
    pg_cursor.execute("""
        INSERT INTO produits (id, nom, rayon_id, date_ajout)
        VALUES (%s, %s, %s, %s)
    """, produit)

print("Produits migrés ✅")


# -------------------
# SERVICES
# -------------------

sqlite_cursor.execute("SELECT * FROM services")
services = sqlite_cursor.fetchall()

for service in services:
    pg_cursor.execute("""
        INSERT INTO services (id, nom, rayon_id)
        VALUES (%s, %s, %s)
    """, service)

print("Services migrés ✅")


# -------------------
# SERVICE ALIAS
# -------------------

sqlite_cursor.execute("SELECT * FROM service_alias")
alias = sqlite_cursor.fetchall()

for a in alias:
    pg_cursor.execute("""
        INSERT INTO service_alias (id, service_id, alias)
        VALUES (%s, %s, %s)
    """, a)

print("Alias migrés ✅")


# -------------------
# RECHERCHES INTROUVABLES
# -------------------

sqlite_cursor.execute("SELECT * FROM recherches_introuvables")
recherches = sqlite_cursor.fetchall()

for recherche in recherches:
    pg_cursor.execute("""
        INSERT INTO recherches_introuvables (id, recherche, date_recherche)
        VALUES (%s, %s, %s)
    """, recherche)

print("Recherches migrées ✅")


# -------------------
# USERS
# -------------------

sqlite_cursor.execute("SELECT * FROM users")
users = sqlite_cursor.fetchall()

for user in users:
    pg_cursor.execute("""
        INSERT INTO users (id, username, password)
        VALUES (%s, %s, %s)
    """, user)

print("Users migrés ✅")


# SAVE
pg_conn.commit()

# CLOSE
sqlite_conn.close()
pg_conn.close()

print("Migration terminée 🚀")