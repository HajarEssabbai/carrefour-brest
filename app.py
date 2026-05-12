from flask import Flask, render_template, request, redirect, url_for, flash, session
import difflib
import unicodedata
import psycopg2
import os
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from functools import wraps
from psycopg2.extras import execute_values

app = Flask(__name__)
app.secret_key = "secret123"

def get_db_connection():

    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        return psycopg2.connect(database_url)

    return psycopg2.connect(
        host="localhost",
        database="carrefour_brest",
        user="postgres",
        password="postgresql123",
        port="5432"
    )


def login_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        if "admin" not in session:
            return redirect("/login")

        return f(*args, **kwargs)

    return decorated

@app.route("/create-tables")
def create_tables():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rayons (
            id SERIAL PRIMARY KEY,
            nom TEXT NOT NULL,
            numero_allee INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produits (
            id SERIAL PRIMARY KEY,
            nom TEXT NOT NULL,
            rayon_id INTEGER,
            date_ajout TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id SERIAL PRIMARY KEY,
            nom TEXT NOT NULL,
            rayon_id INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS service_alias (
            id SERIAL PRIMARY KEY,
            service_id INTEGER,
            alias TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recherches_introuvables (
            id SERIAL PRIMARY KEY,
            recherche TEXT NOT NULL,
            date_recherche TEXT
        )
    """)

    conn.commit()
    conn.close()

    return "Tables créées ✅"

@app.route("/migrate-produits")
def migrate_produits():

    try:

        import sqlite3
        from psycopg2.extras import execute_values

        sqlite_conn = sqlite3.connect("database.db")
        sqlite_cursor = sqlite_conn.cursor()

        pg_conn = get_db_connection()
        pg_cursor = pg_conn.cursor()

        sqlite_cursor.execute("""
            SELECT id, nom, rayon_id, date_ajout
            FROM produits
        """)

        rows = sqlite_cursor.fetchall()

        execute_values(
            pg_cursor,
            """
            INSERT INTO produits (id, nom, rayon_id, date_ajout)
            VALUES %s
            """,
            rows
        )

        pg_conn.commit()

        sqlite_conn.close()
        pg_conn.close()

        return f"{len(rows)} produits migrés ✅"

    except Exception as e:
        return str(e)

@app.route("/")
@login_required
def accueil():
    return render_template("accueil.html")


@app.route("/login", methods=["GET","POST"])
def login():
    if "admin" in session:
        return redirect("/")

    if request.method=="POST":

        username=request.form["username"]
        password=request.form["password"]

        conn = get_db_connection()
        cursor=conn.cursor()

        cursor.execute(
        """
        SELECT password
        FROM users
        WHERE username=%s
        """,
        (username,)
        )

        user=cursor.fetchone()

        conn.close()


        if user and check_password_hash(
            user[0],
            password
        ):

            session["admin"]=username

            return redirect("/")


        return "Identifiants incorrects"


    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/ajouter-rayon", methods=["GET", "POST"])
@login_required
def ajouter_rayon():
    
    if request.method == "POST":
        nom = request.form["nom"].strip().capitalize()

        # Vérification
        if not nom:
            return "Le nom du rayon ne peut pas être vide !"
        
        # Connexion à la base
        conn = get_db_connection()
        cursor = conn.cursor()

        # Vérifier si le rayon existe déjà
        cursor.execute("SELECT * FROM rayons WHERE LOWER(nom) = LOWER(%s)", (nom,))
        existe = cursor.fetchone()

        if existe:
            conn.close()
            return f"Le rayon '{nom}' existe déjà !"

        # Sinon on ajoute
        cursor.execute("SELECT MAX(numero_allee) FROM rayons") 
        result = cursor.fetchone()

        if result[0] is None:
            numero = 1
        else:
            numero = result[0] + 1
        
        # Insérer le rayon
        cursor.execute(
            "INSERT INTO rayons (nom, numero_allee) VALUES (%s, %s)",
            (nom, numero)
        )

        conn.commit()
        conn.close()

        #return f"Rayon ajouté : {nom} (Allée {numero})"
        flash("Rayon ajouté avec succès ✅")
        return redirect(url_for("afficher_rayons"))
    
    return render_template("ajouter_rayon.html")



@app.route("/rayons")
@login_required
def afficher_rayons():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nom, numero_allee FROM rayons")
    rayons = cursor.fetchall()

    conn.close()

    return render_template("rayons.html", rayons=rayons)

@app.route("/supprimer-rayon/<int:id>")
@login_required
def supprimer_rayon(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM rayons WHERE id = %s", (id,))

    conn.commit()
    conn.close()

    #return "Rayon supprimé !"
    flash("Rayon supprimé 🗑️")
    return redirect(url_for("afficher_rayons"))

@app.route("/modifier-rayon/<int:id>", methods=["GET", "POST"])
@login_required
def modifier_rayon(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        nom = request.form["nom"].strip().capitalize()

        if not nom:
            conn.close()
            return "Le nom ne peut pas être vide !"

        # Vérifier doublon (sauf lui-même)
        cursor.execute("""
            SELECT * FROM rayons 
            WHERE LOWER(nom) = LOWER(%s) AND id != %s
        """, (nom, id))
        existe = cursor.fetchone()

        if existe:
            conn.close()
            return f"Le rayon '{nom}' existe déjà !"

        # Update
        cursor.execute(
            "UPDATE rayons SET nom = %s WHERE id = %s",
            (nom, id)
        )

        conn.commit()
        conn.close()

        flash("Rayon modifié ✏️")
        return redirect(url_for("afficher_rayons"))

    # GET → récupérer les infos
    cursor.execute("SELECT nom FROM rayons WHERE id = %s", (id,))
    rayon = cursor.fetchone()

    conn.close()

    return render_template("modifier_rayon.html", rayon=rayon)

@app.route("/ajouter-produit", methods=["GET", "POST"])
@login_required
def ajouter_produit():

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        nom = request.form["nom"].strip()
        rayon_id = request.form["rayon_id"]

        # Validation nom
        if not nom:
            conn.close()
            flash("Le nom du produit est obligatoire ❌")
            return redirect(url_for("ajouter_produit"))
        

       
        
        # Vérification doublons
        cursor.execute("""
            SELECT * FROM produits 
            WHERE LOWER(nom) = LOWER(%s) AND rayon_id = %s
        """, (nom, rayon_id))

        existe = cursor.fetchone()

        if existe:
            conn.close()
            flash("Ce produit existe déjà dans ce rayon ❌")
            return redirect(url_for("ajouter_produit"))

        # Date (simple)
        from datetime import datetime
        date_ajout = datetime.now().strftime("%Y-%m-%d")

        # Insertion
        cursor.execute("""
            INSERT INTO produits (nom, rayon_id, date_ajout)
            VALUES ( %s, %s, %s)
        """, (nom, rayon_id, date_ajout))

        conn.commit()
        conn.close()

        flash("Produit ajouté avec succès ✅")
        return redirect(url_for("afficher_rayons"))  # temporaire

    # GET → récupérer les rayons
    nom_pre_rempli = request.args.get("nom", "")

    cursor.execute("SELECT id, nom FROM rayons")
    rayons = cursor.fetchall()

    conn.close()

    return render_template(
    "ajouter_produit.html",
    rayons=rayons,
    nom_pre_rempli=nom_pre_rempli
)

@app.route("/produits", methods=["GET", "POST"])
@login_required
def afficher_produits():

    conn = get_db_connection()
    cursor = conn.cursor()

    # récupérer tous les rayons (pour dropdown)
    cursor.execute("SELECT id, nom FROM rayons")
    rayons = cursor.fetchall()

    produits = []
    rayon_selectionne = None

    if request.method == "POST":
        rayon_id = request.form["rayon_id"]
        rayon_selectionne = rayon_id
    
    elif "rayon_id" in request.args:
        rayon_id = request.args.get("rayon_id")
        rayon_selectionne = rayon_id
    else:
        rayon_id = None

    if rayon_id:
        cursor.execute("""
            SELECT id, nom,  date_ajout 
            FROM produits 
            WHERE rayon_id = %s 
            ORDER BY LOWER(nom) ASC
        """ , (rayon_id,))
        produits = cursor.fetchall()

    conn.close()

    return render_template(
        "produits.html",
        rayons=rayons,
        produits=produits,
        rayon_selectionne = rayon_selectionne
    )

@app.route("/supprimer-produit/<int:id>/<int:rayon_id>")
@login_required
def supprimer_produit(id, rayon_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM produits WHERE id = %s", (id,))

    conn.commit()
    conn.close()

    flash("Produit supprimé 🗑️")
    return redirect(url_for("afficher_produits", rayon_id= rayon_id))

def enlever_accents(texte):

    return ''.join(
        c for c in unicodedata.normalize(
            'NFD',
            texte
        )
        if unicodedata.category(c) != 'Mn'
    )

@app.route("/recherche", methods=["GET", "POST"])
def recherche():

    conn = get_db_connection()
    cursor = conn.cursor()

    rayons = {}
    services = {}
    if request.method == "POST":

        nom = request.form["nom"].strip().lower()
        nom = enlever_accents(nom)

        mots_recherche = nom.split()


        cursor.execute("""
            SELECT p.nom, r.id, r.nom
            FROM produits p
            JOIN rayons r ON p.rayon_id = r.id
        """)

        produits = cursor.fetchall()


        for p in produits:

            nom_db = enlever_accents(p[0].lower())
            rayon_id = p[1]
            rayon_nom = p[2]
            if all(mot.rstrip("s") in nom_db for mot in mots_recherche):
                if rayon_id not in rayons:
                    rayons[rayon_id] = {
                         "nom": rayon_nom,
                         "produits": []
                           }

                if p[0] not in rayons[rayon_id]["produits"]:
                    rayons[rayon_id]["produits"].append(p[0])

        cursor.execute("""
                       SELECT s.id, s.nom, r.id, r.nom, a.alias
                       FROM services s
                       JOIN rayons r ON s.rayon_id = r.id
                       LEFT JOIN service_alias a ON s.id = a.service_id
                       """)
        services_db = cursor.fetchall()
        for s in services_db:
            service_id = s[0]
            service_nom = s[1]
            rayon_id = s[2]
            rayon_nom = s[3]
            alias = s[4] or ""

            texte = enlever_accents((service_nom + " " + alias).lower())

            if all(mot.rstrip("s") in texte for mot in mots_recherche):
                if service_id not in services:
                    services[service_id] = {
                    "nom": service_nom,
                    "rayon_id": rayon_id,
                    "rayon_nom": rayon_nom
            }
                    

    if not rayons and not services and request.method == "POST":
        cursor.execute("""
                       INSERT INTO recherches_introuvables
                       (recherche, date_recherche)
                       VALUES (%s, NOW())
                       """, (nom,))
        conn.commit()   

    conn.close()

    if "admin" in session:
        template = "recherche_admin.html"
    else:
        template = "recherche_client.html"


    from datetime import datetime

    mois = datetime.now().month

    if mois in [12, 1, 2]:
        saison = "hiver"
    elif mois in [3, 4, 5]:
        saison = "printemps"
    elif mois in [6, 7, 8]:
        saison = "ete"
    else:
        saison = "automne"

    return render_template(
        template,
        rayons=rayons,
        services=services,
        nb_rayons=len(rayons),
        saison= saison
    )

@app.route("/modifier-produit/<int:id>", methods=["GET", "POST"])
@login_required
def modifier_produit(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        nom = request.form["nom"].strip()
        rayon_id = request.form["rayon_id"]

        # Validation nom
        if not nom:
            conn.close()
            flash("Nom obligatoire ❌")
            return redirect(url_for("modifier_produit", id=id))
       

        # Doublon (sauf lui-même)
        cursor.execute("""
            SELECT * FROM produits
            WHERE LOWER(nom) = LOWER(%s) AND rayon_id = %s AND id != %s
        """, (nom, rayon_id, id))

        existe = cursor.fetchone()

        if existe:
            conn.close()
            flash("Produit déjà existant ❌")
            return redirect(url_for("modifier_produit", id=id))

        # UPDATE
        cursor.execute("""
            UPDATE produits
            SET nom = %s, rayon_id = %s
            WHERE id = %s
        """, (nom, rayon_id, id))

        conn.commit()
        conn.close()

        flash("Produit modifié ✏️")
        return redirect(url_for("afficher_produits"))

    # GET → récupérer produit
    cursor.execute("SELECT nom,  rayon_id FROM produits WHERE id = %s", (id,))
    produit = cursor.fetchone()

    # récupérer rayons
    cursor.execute("SELECT id, nom FROM rayons")
    rayons = cursor.fetchall()

    conn.close()

    return render_template("modifier_produit.html", produit=produit, rayons=rayons, id=id)

@app.route("/plan/<int:rayon_id>")
def plan(rayon_id):

    gif = f"rayon_{rayon_id}.gif"

    if "admin" in session:
        template = "plan_admin.html"
    else:
        template = "plan_client.html"

    return render_template(
        template,
        gif=gif
    )

@app.route("/loading/<int:rayon_id>")
def loading(rayon_id):

    return render_template(
        "loading.html",
        url_plan=f"/plan/{rayon_id}"
    )

@app.route("/recherches")
@login_required
def recherches_introuvables():
    
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
                   MIN(id),
                   recherche, 
                   COUNT(*) as total,
                   TO_CHAR(
                   MAX(date_recherche::timestamp),
                   'YYYY-MM-DD HH24:MI:SS'
                   )
                   FROM recherches_introuvables
                   GROUP BY recherche
                   ORDER BY total DESC
                   """)
    
    recherches= cursor.fetchall()

    conn.close()

    return render_template(
        "recherches_introuvables.html",
        recherches=recherches
    )

@app.route("/supprimer-recherche/<recherche>")
@login_required
def supprimer_recherche(recherche):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM recherches_introuvables WHERE recherche = %s",
        (recherche,)
    )

    conn.commit()
    conn.close()

    flash("Recherche supprimée 🗑️")

    return redirect(url_for("recherches_introuvables"))

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )