# ================================================================
# EDISON CATALOGUE - BACKEND SERVEUR
# Version débutant - Ultra simple pour apprendre
# ================================================================

# ===== IMPORTS (les outils dont on a besoin) =====
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# ===== CRÉATION DE L'APPLICATION =====
app = FastAPI(
    title="Edison Catalogue API",
    description="API pour gérer le catalogue électrique",
    version="1.0.0"
)

# ===== CORS : Permet au navigateur de communiquer avec le serveur =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Accepte toutes les origines (pour le test)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================================
# MODÈLES DE DONNÉES (comment sont structurées les infos)
# ================================================================

class Product(BaseModel):
    """Un produit électrique"""
    reference: str
    designation: str
    price: float
    unit: str
    family: str
    icon: Optional[str] = "📦"

class User(BaseModel):
    """Un utilisateur"""
    email: str
    name: str
    password: str

# ================================================================
# BASE DE DONNÉES TEMPORAIRE (en mémoire pour l'instant)
# ================================================================

# Liste des produits (pour l'instant stockés ici, plus tard en vrai DB)
products_db = [
    {
        "reference": "CAB001",
        "designation": "CÂBLE U1000 R2V 3G2.5",
        "price": 2.45,
        "unit": "M",
        "family": "Câbles",
        "icon": "🔌"
    },
    {
        "reference": "DIS001", 
        "designation": "DISJONCTEUR 16A COURBE C",
        "price": 8.90,
        "unit": "U",
        "family": "Protection",
        "icon": "⚡"
    },
    {
        "reference": "INT001",
        "designation": "INTERRUPTEUR VA-ET-VIENT BLANC",
        "price": 3.20,
        "unit": "U", 
        "family": "Appareillage",
        "icon": "💡"
    }
]

# Liste des utilisateurs (version simple)
users_db = [
    {
        "email": "t.tesson@edison-energies.com",
        "name": "Thomas Tesson",
        "password": "demo123"  # ⚠️ En production, JAMAIS en clair !
    }
]

# ================================================================
# ROUTES DE L'API (les actions possibles)
# ================================================================

@app.get("/")
def home():
    """Page d'accueil - Pour vérifier que le serveur fonctionne"""
    return {
        "message": "🎉 Bienvenue sur Edison Catalogue API !",
        "version": "1.0.0",
        "status": "✅ Serveur opérationnel",
        "creator": "Thomas Tesson - MINERVE GROUP"
    }

@app.get("/health")
def health_check():
    """Vérification de santé du serveur"""
    return {
        "status": "OK",
        "products_count": len(products_db),
        "users_count": len(users_db)
    }

# ===== GESTION DES PRODUITS =====

@app.get("/api/products")
def get_products():
    """Récupère tous les produits"""
    return {
        "success": True,
        "count": len(products_db),
        "products": products_db
    }

@app.get("/api/products/{reference}")
def get_product(reference: str):
    """Récupère un produit spécifique par sa référence"""
    for product in products_db:
        if product["reference"] == reference:
            return {
                "success": True,
                "product": product
            }
    
    # Si produit non trouvé
    raise HTTPException(status_code=404, detail="Produit non trouvé")

@app.post("/api/products")
def add_product(product: Product):
    """Ajoute un nouveau produit"""
    
    # Vérifie si la référence existe déjà
    for p in products_db:
        if p["reference"] == product.reference:
            raise HTTPException(status_code=400, detail="Cette référence existe déjà")
    
    # Ajoute le produit
    new_product = product.dict()
    products_db.append(new_product)
    
    return {
        "success": True,
        "message": "Produit ajouté avec succès",
        "product": new_product
    }

@app.delete("/api/products/{reference}")
def delete_product(reference: str):
    """Supprime un produit"""
    for i, product in enumerate(products_db):
        if product["reference"] == reference:
            deleted = products_db.pop(i)
            return {
                "success": True,
                "message": "Produit supprimé",
                "product": deleted
            }
    
    raise HTTPException(status_code=404, detail="Produit non trouvé")

# ===== GESTION DES UTILISATEURS =====

@app.post("/api/login")
def login(user: User):
    """Connexion utilisateur"""
    for u in users_db:
        if u["email"] == user.email and u["password"] == user.password:
            return {
                "success": True,
                "message": "Connexion réussie",
                "user": {
                    "email": u["email"],
                    "name": u["name"]
                }
            }
    
    raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

@app.get("/api/users")
def get_users():
    """Récupère tous les utilisateurs (sans les mots de passe)"""
    users_safe = []
    for u in users_db:
        users_safe.append({
            "email": u["email"],
            "name": u["name"]
        })
    return {
        "success": True,
        "count": len(users_safe),
        "users": users_safe
    }

# ===== STATISTIQUES =====

@app.get("/api/stats")
def get_stats():
    """Récupère les statistiques"""
    
    # Compte par famille
    families = {}
    for product in products_db:
        family = product["family"]
        if family in families:
            families[family] += 1
        else:
            families[family] = 1
    
    return {
        "success": True,
        "total_products": len(products_db),
        "total_users": len(users_db),
        "families": families
    }

# ================================================================
# LANCEMENT DU SERVEUR
# ================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 EDISON CATALOGUE - SERVEUR EN DÉMARRAGE")
    print("=" * 60)
    print("📍 Adresse locale : http://localhost:8000")
    print("📚 Documentation : http://localhost:8000/docs")
    print("🔧 Par Thomas Tesson - MINERVE GROUP")
    print("=" * 60)
    
    # Démarre le serveur
    uvicorn.run(app, host="0.0.0.0", port=8000)
