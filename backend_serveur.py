from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
from datetime import datetime

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

# ============================================================
# DATABASE
# ============================================================

DB_PATH = "catalogue.db"

def init_db():
    """Initialiser la base de données"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# 🚀 NOUVEL ENDPOINT BATCH - SYNCHRONISATION RAPIDE
# ============================================================

@app.post("/api/products/batch")
async def batch_products(products: List[Product]):
    """
    Synchronisation en masse de produits
    Crée les nouveaux produits et met à jour les existants
    """
    created = 0
    updated = 0
    failed = 0
    errors = []
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for product in products:
            try:
                # Vérifier si le produit existe
                cursor.execute("SELECT reference FROM products WHERE reference = ?", (product.reference,))
                exists = cursor.fetchone()
                
                if exists:
                    # MISE À JOUR
                    cursor.execute(
                        """UPDATE products 
                           SET designation = ?, price = ?, unit = ?, family = ?, icon = ?, updated_at = ?
                           WHERE reference = ?""",
                        (product.designation, product.price, product.unit, product.family, 
                         product.icon, datetime.now().isoformat(), product.reference)
                    )
                    updated += 1
                else:
                    # CRÉATION
                    cursor.execute(
                        """INSERT INTO products (reference, designation, price, unit, family, icon)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (product.reference, product.designation, product.price, 
                         product.unit, product.family, product.icon)
                    )
                    created += 1
                    
            except Exception as e:
                failed += 1
                errors.append({
                    "reference": product.reference,
                    "error": str(e)
                })
        
        # Commit une seule fois à la fin
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "created": created,
            "updated": updated,
            "failed": failed,
            "errors": errors,
            "total": len(products)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# STARTUP
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
