# database.py
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from bson import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# ✅ Configuration MongoDB avec résilience améliorée
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB", "llm_tests")

# ✅ Options de connexion pour meilleure résilience
client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,  # Timeout de 5s pour détecter rapidement les problèmes
    connectTimeoutMS=10000,         # Timeout de connexion de 10s
    socketTimeoutMS=30000,          # Timeout de socket de 30s
    maxPoolSize=50,                 # Pool de connexions max
    minPoolSize=10,                 # Pool de connexions min
    retryWrites=True,               # Réessayer automatiquement les écritures échouées
    retryReads=True                 # Réessayer automatiquement les lectures échouées
)

db = client[MONGO_DB_NAME]
collection = db["test_cases"]

def _to_dict(doc):
    if not doc: return {}
    out = dict(doc)
    if isinstance(out.get("_id"), ObjectId):
        out["_id"] = str(out["_id"])
    if isinstance(out.get("created_at"), datetime):
        out["created_at"] = out["created_at"].isoformat()
    return out

def save_test_case(code, result, test_type, language=None):
    collection.insert_one({
        "code": code,
        "generated_test": result,
        "test_type": test_type,
        "language": language,
        "created_at": datetime.utcnow()
    })

def list_test_cases(limit: int = 50):
    """
    ✅ Liste les test cases avec gestion d'erreur MongoDB
    """
    try:
        cur = collection.find().sort("created_at", -1).limit(int(limit))
        return [_to_dict(doc) for doc in cur]
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        print(f"❌ Erreur MongoDB: {e}")
        return []  # Retourne une liste vide au lieu de crasher
