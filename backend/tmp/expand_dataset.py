import pandas as pd
import random

# Existing data
file_path = 'datasets/house_owner_data.tsv'
df = pd.read_csv(file_path, sep='\t')

# Current values
cities = df['city'].unique().tolist()
existing_ids = set(df['consumer_id'].astype(str).tolist())

# Generate more data
new_rows = []
total_needed = 1050 # A bit over 1000

# Start ID for new entries
# Assuming current IDs are around 100000-100159
current_max = 100159
next_id = current_max + 1

names = ["Arjun", "Deepak", "Sneha", "Priya", "Rahul", "Anjali", "Vikram", "Kavita", "Suresh", "Meera", 
         "Amit", "Pooja", "Rohan", "Sunita", "Vijay", "Anita", "Sanjay", "Neeta", "Manoj", "Rekha"]
surnames = ["Sharma", "Verma", "Patel", "Gupta", "Iyer", "Nair", "Reddy", "Singh", "Yadav", "Kumar"]

while len(df) + len(new_rows) < total_needed:
    consumer_id = str(next_id)
    if consumer_id not in existing_ids:
        name = f"{random.choice(names)} {random.choice(surnames)}"
        city = random.choice(cities)
        new_rows.append({
            'consumer_id': consumer_id,
            'owner_name': name,
            'city': city
        })
        existing_ids.add(consumer_id)
    next_id += 1

# Combine and save
df_expanded = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
df_expanded.to_csv(file_path, sep='\t', index=False)
print(f"Dataset expanded to {len(df_expanded)} rows.")
