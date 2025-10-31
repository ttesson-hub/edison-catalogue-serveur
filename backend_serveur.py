from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import sqlite3
from datetime import datetime
import os
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

app = FastAPI(title="Edison Catalogue API")

# CORS pour permettre les appels depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# MODELS
# ============================================================

class Product(BaseModel):
    reference: str
    designation: str
    price: float
    unit: str = "U"
    family: str = "Divers"
    icon: str = "📦"

class ProductUpdate(BaseModel):
    designation: str
    price: float
    unit: str = "U"
    family: str = "Divers"

class BatchResult(BaseModel):
    created: int
    updated: int
    failed: int
    errors: List[dict]

class EmailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    body: str
    da_number: Optional[str] = None
    attachment_path: Optional[str] = None

class DAArticle(BaseModel):
    reference: str
    designation: str
    quantity: int
    unit: str
    price: float

class DARequest(BaseModel):
    user_email: str
    user_name: str
    site: str
    articles: List[DAArticle]
    attachment_filename: Optional[str] = None
    comments: Optional[str] = None

# ============================================================
# CONFIGURATION
# ============================================================

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Configuration email (à personnaliser)
EMAIL_CONFIG = {
    "SMTP_SERVER": "smtp.gmail.com",
    "SMTP_PORT": 587,
    "SENDER_EMAIL": "votre-email@gmail.com",  # À configurer
    "SENDER_PASSWORD": "votre-mot-de-passe-app",  # À configurer
    "ENABLED": False  # Mettre True quand configuré
}

# ============================================================
# DATABASE
# ============================================================

DB_PATH = "catalogue.db"

def init_db():
    """Initialiser la base de données"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table produits
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            reference TEXT PRIMARY KEY,
            designation TEXT NOT NULL,
            price REAL NOT NULL,
            unit TEXT DEFAULT 'U',
            family TEXT DEFAULT 'Divers',
            icon TEXT DEFAULT '📦',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table demandes d'achat
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchase_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            da_number TEXT UNIQUE NOT NULL,
            user_email TEXT NOT NULL,
            user_name TEXT NOT NULL,
            site TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            attachment_filename TEXT,
            comments TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table articles des DA
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS da_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            da_number TEXT NOT NULL,
            reference TEXT NOT NULL,
            designation TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit TEXT NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (da_number) REFERENCES purchase_requests(da_number)
        )
    """)
    
    # Table fichiers uploadés
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            original_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            mime_type TEXT,
            uploaded_by TEXT,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# Initialiser la DB au démarrage
init_db()

# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "OK"}

@app.get("/api/products")
async def get_products():
    """Récupérer tous les produits"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT reference, designation, price, unit, family, icon FROM products")
        rows = cursor.fetchall()
        
        products = [
            {
                "reference": row[0],
                "designation": row[1],
                "price": row[2],
                "unit": row[3],
                "family": row[4],
                "icon": row[5]
            }
            for row in rows
        ]
        
        conn.close()
        
        return {
            "success": True,
            "products": products
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/products")
async def create_product(product: Product):
    """Créer un nouveau produit"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Vérifier si le produit existe déjà
        cursor.execute("SELECT reference FROM products WHERE reference = ?", (product.reference,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Cette référence existe déjà")
        
        # Insérer le produit
        cursor.execute(
            """INSERT INTO products (reference, designation, price, unit, family, icon)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (product.reference, product.designation, product.price, product.unit, product.family, product.icon)
        )
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Produit créé"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/products/{reference}")
async def update_product(reference: str, product: ProductUpdate):
    """Mettre à jour un produit existant"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Vérifier si le produit existe
        cursor.execute("SELECT reference FROM products WHERE reference = ?", (reference,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        
        # Mettre à jour le produit
        cursor.execute(
            """UPDATE products 
               SET designation = ?, price = ?, unit = ?, family = ?, updated_at = ?
               WHERE reference = ?""",
            (product.designation, product.price, product.unit, product.family, 
             datetime.now().isoformat(), reference)
        )
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Produit mis à jour"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/products/{reference}")
async def delete_product(reference: str):
    """Supprimer un produit"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM products WHERE reference = ?", (reference,))
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Produit supprimé"}
    except HTTPException:
        raise
    except Excepti
