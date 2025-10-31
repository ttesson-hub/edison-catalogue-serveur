# ================================================================
# EDISON CATALOGUE - BACKEND SERVEUR V2
# Version complète avec base de données SQLite
# ================================================================

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import sqlite3
import json
from datetime import datetime
import hashlib

# ===== CRÉATION DE L'APPLICATION =====
app = FastAPI(
    title="Edison Catalogue API v2",
    description="API complète avec base de données pour le catalogue électrique",
    version="2.0.0"
)

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================================
# BASE DE DONNÉES SQLITE
# ================================================================

DB_NAME = "edison_catalogue.db"

def get_db():
    """Connexion à la base de données"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialise la base de données avec les tables nécessaires"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Table des produits
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            reference TEXT PRIMARY KEY,
            designation TEXT NOT NULL,
            price REAL NOT NULL,
            unit TEXT NOT NULL,
            family TEXT NOT NULL,
            icon TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table des familles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS families (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            icon TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table des utilisateurs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        )
    ''')
    
    conn.commit()
    
    # Insérer des données par défaut si les tables sont vides
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        default_products = [
            ("CAB001", "CÂBLE U1000 R2V 3G2.5", 2.45, "M", "Câbles", "🔌"),
            ("DIS001", "DISJONCTEUR 16A COURBE C", 8.90, "U", "Protection", "⚡"),
            ("INT001", "INTERRUPTEUR VA-ET-VIENT BLANC", 3.20, "U", "Appareillage", "💡"),
        ]
        cursor.executemany(
            "INSERT INTO products (reference, designation, price, unit, family, icon) VALUES (?, ?, ?, ?, ?, ?)",
            default_products
        )
    
    cursor.execute("SELECT COUNT(*) FROM families")
    if cursor.fetchone()[0] == 0:
        default_families = [
            ("Câbles", "🔌"),
            ("Protection", "⚡"),
            ("Appareillage", "💡"),
            ("Tableaux", "📋"),
            ("Gaines", "🔧"),
            ("Éclairage", "💡"),
        ]
        cursor.executemany(
            "INSERT INTO families (name, icon) VALUES (?, ?)",
            default_families
        )
    
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        # Utilisateur par défaut (mot de passe: demo123)
        hashed_pw = hashlib.sha256("demo123".encode()).hexdigest()
        cursor.execute(
            "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, ?)",
            ("t.tesson@edison-energies.com", "Thomas Tesson", hashed_pw, "superadmin")
        )
    
    conn.commit()
    conn.close()

# ================================================================
# MODÈLES DE DONNÉES
# ================================================================

class Product(BaseModel):
    reference: str
    designation: str
    price: float
    unit: str
    family: str
    icon: Optional[str] = "📦"

class ProductUpdate(BaseModel):
    designation: Optional[str] = None
    price: Optional[float] = None
    unit: Optional[str] = None
    family: Optional[str] = None
    icon: Optional[str] = None

class Family(BaseModel):
    name: str
    icon: Optional[str] = "📁"

class User(BaseModel):
    email: str
    name: str
    password: str
    role: Optional[str] = "user"

class LoginRequest(BaseModel):
    email: str
    password: str

# ================================================================
# ROUTES DE L'API
# ================================================================

@app.on_event("startup")
async def startup_event():
    """Initialise la DB au démarrage"""
    init_db()
    print("✅ Base de données initialisée")

@app.get("/")
def home():
    """Page d'accueil"""
    return {
        "message": "🎉 Edison Catalogue API v2 - Avec base de données !",
        "version": "2.0.0",
        "status": "✅ Serveur opérationnel",
        "database": "SQLite",
        "creator": "Thomas Tesson - MINERVE GROUP"
    }

@app.get("/health")
def health_check():
    """Vérification de santé du serveur"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM products")
    products_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM families")
    families_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "status": "OK",
        "database": "Connected",
        "products_count": products_count,
        "families_count": families_count,
        "users_count": users_count
    }

# ===== GESTION DES PRODUITS =====

@app.get("/api/products")
def get_products(family: Optional[str] = None, search: Optional[str] = None):
    """Récupère tous les produits avec filtres optionnels"""
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    
    if family:
        query += " AND family = ?"
        params.append(family)
    
    if search:
        query += " AND (reference LIKE ? OR designation LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])
    
    cursor.execute(query, params)
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "success": True,
        "count": len(products),
        "products": products
    }

@app.get("/api/products/{reference}")
def get_product(reference: str):
    """Récupère un produit spécifique"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM products WHERE reference = ?", (reference,))
    product = cursor.fetchone()
    conn.close()
    
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    return {
        "success": True,
        "product": dict(product)
    }

@app.post("/api/products")
def add_product(product: Product):
    """Ajoute un nouveau produit"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO products (reference, designation, price, unit, family, icon) VALUES (?, ?, ?, ?, ?, ?)",
            (product.reference, product.designation, product.price, product.unit, product.family, product.icon)
        )
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Produit ajouté avec succès",
            "product": product.dict()
        }
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Cette référence existe déjà")

@app.put("/api/products/{reference}")
def update_product(reference: str, product: ProductUpdate):
    """Met à jour un produit"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Vérifier que le produit existe
    cursor.execute("SELECT * FROM products WHERE reference = ?", (reference,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    # Construire la requête de mise à jour
    updates = []
    params = []
    
    if product.designation is not None:
        updates.append("designation = ?")
        params.append(product.designation)
    if product.price is not None:
        updates.append("price = ?")
        params.append(product.price)
    if product.unit is not None:
        updates.append("unit = ?")
        params.append(product.unit)
    if product.family is not None:
        updates.append("family = ?")
        params.append(product.family)
    if product.icon is not None:
        updates.append("icon = ?")
        params.append(product.icon)
    
    if updates:
        params.append(reference)
        query = f"UPDATE products SET {', '.join(updates)} WHERE reference = ?"
        cursor.execute(query, params)
        conn.commit()
    
    # Récupérer le produit mis à jour
    cursor.execute("SELECT * FROM products WHERE reference = ?", (reference,))
    updated_product = dict(cursor.fetchone())
    conn.close()
    
    return {
        "success": True,
        "message": "Produit mis à jour",
        "product": updated_product
    }

@app.delete("/api/products/{reference}")
def delete_product(reference: str):
    """Supprime un produit"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM products WHERE reference = ?", (reference,))
    product = cursor.fetchone()
    
    if not product:
        conn.close()
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    cursor.execute("DELETE FROM products WHERE reference = ?", (reference,))
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "message": "Produit supprimé",
        "product": dict(product)
    }

# ===== GESTION DES FAMILLES =====

@app.get("/api/families")
def get_families():
    """Récupère toutes les familles"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM families ORDER BY name")
    families = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "success": True,
        "count": len(families),
        "families": families
    }

@app.post("/api/families")
def add_family(family: Family):
    """Ajoute une nouvelle famille"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO families (name, icon) VALUES (?, ?)",
            (family.name, family.icon)
        )
        conn.commit()
        
        cursor.execute("SELECT * FROM families WHERE name = ?", (family.name,))
        new_family = dict(cursor.fetchone())
        conn.close()
        
        return {
            "success": True,
            "message": "Famille ajoutée",
            "family": new_family
        }
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Cette famille existe déjà")

@app.delete("/api/families/{family_id}")
def delete_family(family_id: int):
    """Supprime une famille"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM families WHERE id = ?", (family_id,))
    family = cursor.fetchone()
    
    if not family:
        conn.close()
        raise HTTPException(status_code=404, detail="Famille non trouvée")
    
    cursor.execute("DELETE FROM families WHERE id = ?", (family_id,))
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "message": "Famille supprimée"
    }

# ===== GESTION DES UTILISATEURS =====

@app.post("/api/login")
def login(login_req: LoginRequest):
    """Connexion utilisateur"""
    conn = get_db()
    cursor = conn.cursor()
    
    hashed_pw = hashlib.sha256(login_req.password.encode()).hexdigest()
    
    cursor.execute(
        "SELECT * FROM users WHERE email = ? AND password = ?",
        (login_req.email, hashed_pw)
    )
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    # Mettre à jour la date de dernière connexion
    cursor.execute(
        "UPDATE users SET last_login = ? WHERE email = ?",
        (datetime.now().isoformat(), login_req.email)
    )
    conn.commit()
    conn.close()
    
    user_dict = dict(user)
    # Ne pas renvoyer le mot de passe
    user_dict.pop('password', None)
    
    return {
        "success": True,
        "message": "Connexion réussie",
        "user": user_dict
    }

@app.get("/api/users")
def get_users():
    """Récupère tous les utilisateurs (sans les mots de passe)"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT email, name, role, created_at, last_login FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "success": True,
        "count": len(users),
        "users": users
    }

@app.post("/api/users")
def create_user(user: User):
    """Crée un nouvel utilisateur"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Hasher le mot de passe
    hashed_pw = hashlib.sha256(user.password.encode()).hexdigest()
    
    try:
        cursor.execute(
            "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, ?)",
            (user.email, user.name, hashed_pw, user.role)
        )
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Utilisateur créé avec succès"
        }
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Cet utilisateur existe déjà")

# ===== STATISTIQUES =====

@app.get("/api/stats")
def get_stats():
    """Récupère les statistiques"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Total produits
    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]
    
    # Total utilisateurs
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    # Produits par famille
    cursor.execute("""
        SELECT family, COUNT(*) as count 
        FROM products 
        GROUP BY family 
        ORDER BY count DESC
    """)
    families = {}
    for row in cursor.fetchall():
        families[row[0]] = row[1]
    
    # Prix moyen
    cursor.execute("SELECT AVG(price) FROM products")
    avg_price = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        "success": True,
        "total_products": total_products,
        "total_users": total_users,
        "families": families,
        "avg_price": round(avg_price, 2)
    }

# ================================================================
# LANCEMENT DU SERVEUR
# ================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 EDISON CATALOGUE V2 - SERVEUR EN DÉMARRAGE")
    print("=" * 60)
    print("📍 Adresse locale : http://localhost:8000")
    print("📚 Documentation : http://localhost:8000/docs")
    print("💾 Base de données : SQLite (edison_catalogue.db)")
    print("🔧 Par Thomas Tesson - MINERVE GROUP")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
