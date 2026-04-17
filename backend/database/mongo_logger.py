from pymongo import MongoClient  # type: ignore
from pymongo.errors import ServerSelectionTimeoutError  # type: ignore

try:
    # Set a short timeout to check if the server is running
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    # Attempt to ping the server to verify connection
    client.admin.command('ping')
    db = client["microgrid_drl"]
    collection = db["training_results"]
    print("[OK] Connected to MongoDB.")
except (ServerSelectionTimeoutError, Exception) as e:
    print("[WARN] MongoDB not running or not accessible. Database logging disabled.")
    collection = None

def log_episode(ep, reward):
    if collection is not None:
        try:
            collection.insert_one({
                "episode": ep,
                "total_reward": reward
            })
        except Exception:
            pass
