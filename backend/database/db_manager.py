import hashlib
import datetime
import json
import os
import uuid
import threading
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from bson import ObjectId

class JsonDB:
    """Simple JSON-based database fallback."""
    def __init__(self, filename="local_db.json"):
        self.filename = filename
        self.lock = threading.Lock()
        self.data = {"users": [], "simulations": []}
        self.load()

    def load(self):
        with self.lock:
            if os.path.exists(self.filename):
                try:
                    with open(self.filename, 'r') as f:
                        self.data = json.load(f)
                except Exception as e:
                    print(f"Error loading local DB: {e}")
    
    def save(self):
        try:
            # Custom encoder for datetime
            def default(o):
                if isinstance(o, (datetime.date, datetime.datetime)):
                    return o.isoformat()
                return str(o)
            
            with self.lock:
                with open(self.filename, 'w') as f:
                    json.dump(self.data, f, indent=4, default=default)
        except Exception as e:
            print(f"Error saving local DB: {e}")

    def add_user(self, user_doc):
        self.data["users"].append(user_doc)
        self.save()

    def find_user(self, email):
        for user in self.data["users"]:
            if user["email"] == email:
                return user
        return None

    def add_simulation(self, sim_doc):
        # Convert objects to strings for JSON safety
        if "_id" not in sim_doc:
            sim_doc["_id"] = str(uuid.uuid4())
        else:
            sim_doc["_id"] = str(sim_doc["_id"])
             
        self.data["simulations"].append(sim_doc)
        self.save()

    def get_simulations(self, email):
        return [s for s in self.data["simulations"] if s["user_email"] == email]

    def get_simulation_by_id(self, sim_id):
        for s in self.data["simulations"]:
            if str(s.get("_id")) == str(sim_id):
                return s
        return None
    
    def delete_simulation(self, email, sim_id):
        initial_len = len(self.data["simulations"])
        self.data["simulations"] = [s for s in self.data["simulations"] 
                                    if not (str(s.get("_id")) == str(sim_id) and s["user_email"] == email)]
        
        if len(self.data["simulations"]) < initial_len:
            self.save()
            return True
        return False

class DatabaseManager:
    def __init__(self, db_name=None, connection_string=None):
        # Prioritize arguments, then env vars
        db_name = db_name or os.getenv("DATABASE_NAME", "microgrid_drl")
        connection_string = connection_string or os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        
        self.use_mongo = False
        self.client = None
        self.db = None
        self.users = None
        self.simulations = None
        self.json_db = None
        
        try:
            # print("CONNECTING TO MONGO...", connection_string) # Reduced noise
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=2000)
            # Ping to check connection
            self.client.admin.command('ping')
            
            self.db = self.client[db_name]
            self.users = self.db["users"]
            self.simulations = self.db["simulations"]
            self.use_mongo = True
            print("Database Connected (MongoDB)")
        except (ServerSelectionTimeoutError, Exception):
            # Suppress full error to avoid scaring user
            print("MongoDB not detected. Switching to Local JSON Database (local_db.json).")
            self.json_db = JsonDB()
            self.use_mongo = False

    def _hash_password(self, password):
        """Hashes password using SHA-256. Safely handles None."""
        if password is None:
            return ""
        return hashlib.sha256(str(password).encode()).hexdigest()

    def register_user(self, email=None, password=None, mobile=None):
        if not (email and password) and not (mobile):
            return False, "Email/Password or Mobile Number is required"

        email = email.strip().lower() if email else None
        mobile = mobile.strip() if mobile else None
        password_hash = self._hash_password(password) if password else None
        created_at = datetime.datetime.now()
        
        user_data = {
            "email": email,
            "mobile": mobile,
            "password": password_hash,
            "created_at": created_at,
            "otp": None,
            "otp_expiry": None
        }
        
        if self.use_mongo:
            query = {}
            if email: query["email"] = email
            if mobile: query["mobile"] = mobile
            
            existing_user = self.users.find_one({ "$or": [ {"email": email}, {"mobile": mobile} ] } if email and mobile else query)
            if existing_user:
                # If we are trying to sign up (with email/password) 
                # and the existing user only has a mobile, we should UPDATE it.
                if email and password and not existing_user.get("email"):
                    self.users.update_one(
                        {"_id": existing_user["_id"]},
                        {"$set": {"email": email, "password": password_hash, "created_at": created_at}}
                    )
                    return True, "Registration completed successfully"
                return False, "User already exists"
                
            self.users.insert_one(user_data)
            return True, "Registration successful"
        else:
            existing_by_email = self.find_user(email)
            existing_by_mobile = self.find_user_by_mobile(mobile)
            
            if existing_by_email or existing_by_mobile:
                user = existing_by_email or existing_by_mobile
                # Logic for Local JSON fallback - allow upgrade if no email/password
                if email and password and not user.get("email"):
                    user["email"] = email
                    user["password"] = password_hash
                    user["created_at"] = created_at.isoformat() if isinstance(created_at, datetime.datetime) else created_at
                    self.json_db.save()
                    return True, "Registration completed successfully (Local Mode)"
                    
                return False, "User already exists"
            self.json_db.add_user(user_data)
            return True, "Registration successful (Local Mode)"


    def find_user(self, email):
        """Finds a user by email."""
        if not email: return None
        email = email.lower().strip()
        if self.use_mongo:
            return self.users.find_one({"email": email})
        else:
            return self.json_db.find_user(email)

    def authenticate_user(self, email, password):
        """Authenticates a user. Returns True if valid."""
        if not email or not password:
            return False

        email = email.strip().lower()
        password_hash = self._hash_password(password)
        
        if self.use_mongo:
            user = self.users.find_one({"email": email})
        else:
            user = self.json_db.find_user(email)
            
        if not user:
            return False
        
        # Consistent check even if record has missing password field
        return user.get("password") == password_hash

    def find_user_by_mobile(self, mobile):
        """Finds a user by mobile number."""
        if not mobile: return None
        mobile = mobile.strip()
        
        if self.use_mongo:
            return self.users.find_one({"mobile": mobile})
        else:
            for user in self.json_db.data["users"]:
                if user.get("mobile") == mobile:
                    return user
            return None

    def store_otp(self, mobile, otp):
        """Stores a generated OTP for a mobile number with expiry."""
        if not mobile or not otp: return False
        
        expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        
        if self.use_mongo:
            result = self.users.update_one(
                {"mobile": mobile},
                {"$set": {"otp": otp, "otp_expiry": expiry}}
            )
            # If user doesn't exist, we might want to register them or return False
            return result.matched_count > 0
        else:
            for user in self.json_db.data["users"]:
                if user.get("mobile") == mobile:
                    user["otp"] = otp
                    user["otp_expiry"] = expiry.isoformat()
                    self.json_db.save()
                    return True
            return False

    def verify_otp(self, mobile, otp):
        """Verifies if the provided OTP is valid and not expired."""
        if not mobile or not otp: return False
        
        user = self.find_user_by_mobile(mobile)
        if not user: return False
        
        stored_otp = user.get("otp")
        expiry = user.get("otp_expiry")
        
        if stored_otp != otp: return False
        
        if isinstance(expiry, str):
            expiry = datetime.datetime.fromisoformat(expiry)
            
        if datetime.datetime.utcnow() > expiry:
            return False
            
        return True

    def update_user_settings(self, email, settings):
        """Updates user specific settings such as email credentials."""
        if not settings:
            return False
            
        if self.use_mongo:
            result = self.users.update_one({"email": email}, {"$set": {"settings": settings}})
            return result.modified_count > 0
        else:
            for user in self.json_db.data["users"]:
                if user["email"] == email:
                    if "settings" not in user:
                        user["settings"] = {}
                    user["settings"].update(settings)
                    self.json_db.save()
                    return True
            return False
            
    def get_user_settings(self, email):
        """Retrieves user settings."""
        if self.use_mongo:
            user = self.users.find_one({"email": email})
            return user.get("settings", {}) if user else {}
        else:
            user = self.json_db.find_user(email)
            return user.get("settings", {}) if user else {}

    def link_meter(self, email, consumer_id):
        """Permanently links a consumer meter ID to a specific user email."""
        if not email or not consumer_id:
            return False
            
        if self.use_mongo:
            result = self.users.update_one(
                {"email": email},
                {"$set": {"linked_meter": str(consumer_id)}}
            )
            return result.modified_count > 0
        else:
            for user in self.json_db.data["users"]:
                if user.get("email") == email:
                    user["linked_meter"] = str(consumer_id)
                    self.json_db.save()
                    return True
            return False

    def check_meter_ownership(self, email, consumer_id):
        """Checks if the given meter ID is linked to the user email."""
        if not email or not consumer_id:
            return False
            
        if self.use_mongo:
            user = self.users.find_one({"email": email})
        else:
            user = self.json_db.find_user(email)
            
        if not user:
            return False
            
        return user.get("linked_meter") == str(consumer_id)

    def record_payment(self, email, consumer_id, amount, bill_month):
        """Records a successful bill payment."""
        payment_doc = {
            "amount": amount,
            "bill_month": bill_month,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        if self.use_mongo:
            result = self.users.update_one(
                {"email": email, "linked_meter": str(consumer_id)},
                {"$push": {"payment_history": payment_doc}, "$set": {"last_payment_status": "PAID"}}
            )
            return result.modified_count > 0
        else:
            for user in self.json_db.data["users"]:
                if user.get("email") == email and user.get("linked_meter") == str(consumer_id):
                    if "payment_history" not in user:
                        user["payment_history"] = []
                    user["payment_history"].append(payment_doc)
                    user["last_payment_status"] = "PAID"
                    self.json_db.save()
                    return True
            return False

    def upsert_house_data(self, consumer_id, data):
        """Inserts or updates a house owner's data in the database."""
        if not consumer_id: return False
        
        doc = {**data, "consumer_id": str(consumer_id)}
        
        if self.use_mongo:
            # Create a dedicated collection for house data for scalability
            houses = self.db.house_data
            houses.create_index("consumer_id", unique=True)
            result = houses.replace_one({"consumer_id": str(consumer_id)}, doc, upsert=True)
            return True
        else:
            if "house_data" not in self.json_db.data:
                self.json_db.data["house_data"] = []
            
            # Update existing or append
            found = False
            for i, h in enumerate(self.json_db.data["house_data"]):
                if h.get("consumer_id") == str(consumer_id):
                    self.json_db.data["house_data"][i] = doc
                    found = True
                    break
            if not found:
                self.json_db.data["house_data"].append(doc)
            
            self.json_db.save()
            return True

    def get_house_data(self, consumer_id):
        """Retrieves a house owner's record by consumer_id."""
        if not consumer_id: return None
        
        if self.use_mongo:
            return self.db.house_data.find_one({"consumer_id": str(consumer_id)})
        else:
            if "house_data" not in self.json_db.data:
                return None
            for h in self.json_db.data["house_data"]:
                if h.get("consumer_id") == str(consumer_id):
                    return h
            return None

    def save_simulation(self, email, simulation_data):
        """Saves a simulation result for a user."""
        doc = {
            "user_email": email,
            "timestamp": datetime.datetime.now(),
            "data": simulation_data,
            "summary": {
                "savings_pct": simulation_data.get("savings_pct", 0),
                "net_profit": simulation_data.get("net_profit", 0),
                "suggestions": simulation_data.get("suggestions", []),
                "efficiency": simulation_data.get("efficiency", 0.0)
            }
        }
        
        if self.use_mongo:
            self.simulations.insert_one(doc)
        else:
            self.json_db.add_simulation(doc)
             
        return True, "Simulation saved successfully"

    def get_user_history(self, email):
        """Retrieves simulation history for a user."""
        if self.use_mongo:
            # Exclude 'data.sim_results' from the list view to improve performance
            cursor = self.simulations.find(
                {"user_email": email}, 
                {"data.sim_results": 0} 
            ).sort("timestamp", -1)
            return list(cursor)
        else:
            # Get all and manually exclude big data if needed, or just return basic info
            data = self.json_db.get_simulations(email)
            # Sort by timestamp desc
            # Note: in JSON, timestamps are strings or datetime objects depending on load state
            # Simple reverse assuming append order is chronological might be enough, or sort
            return sorted(data, key=lambda x: str(x["timestamp"]), reverse=True)

    def get_simulation(self, simulation_id):
        """Retrieves a single full simulation document by ID."""
        if self.use_mongo:
            try:
                return self.simulations.find_one({"_id": ObjectId(simulation_id)})
            except Exception as e:
                print(f"MongoDB Lookup Error for ID {simulation_id}: {e}")
                return None
        else:
            return self.json_db.get_simulation_by_id(simulation_id)

    def delete_simulation(self, email, simulation_id):
        """Deletes a simulation by ID."""
        if self.use_mongo:
            try:
                result = self.simulations.delete_one({
                    "_id": ObjectId(simulation_id),
                    "user_email": email
                })
                if result.deleted_count > 0:
                    return True, "Simulation deleted successfully"
                else:
                    return False, "Simulation not found or unauthorized"
            except Exception as e:
                return False, f"Error deleting simulation: {e}"
        else:
            success = self.json_db.delete_simulation(email, simulation_id)
            if success:
                return True, "Simulation deleted successfully"
            else:
                return False, "Simulation not found or unauthorized"
