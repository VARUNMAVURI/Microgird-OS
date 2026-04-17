import pandas as pd
import os
import sys

# Add paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, 'backend')
for p in [BASE_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.append(p)

from database.db_manager import DatabaseManager

def migrate():
    print("Starting Dataset Migration to Database...")
    
    # Initialize DB
    db = DatabaseManager(
        db_name=os.getenv("DATABASE_NAME", "microgrid_drl"),
        connection_string=os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    )
    
    db_type = "MongoDB" if db.use_mongo else "Local JSON"
    print(f"Using Database: {db_type}")
    
    file_path = os.path.join(BACKEND_DIR, "datasets", "house_owner_data.tsv")
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    # Load data from file
    try:
        df = pd.read_csv(file_path, sep='\t')
        print(f"Parsed {len(df)} records from {file_path}.")
    except Exception as e:
        print(f"Error parsing file: {e}")
        return

    count = 0
    for _, row in df.iterrows():
        consumer_id = str(row['consumer_id'])
        
        # Map 'city' to 'house_location' as used in current logic
        data = row.to_dict()
        if 'city' in data:
            data['house_location'] = data.pop('city')
            
        success = db.upsert_house_data(consumer_id, data)
        if success:
            count += 1
            
    print(f"Migration Complete! {count} residents imported into the database.")

if __name__ == "__main__":
    migrate()
