import csv
from pymongo import MongoClient
import argparse
import time

CSV_FILE = "SFPL_DataSF_library-usage_Jan_2023.csv"

def parse_bool(value):
    if value is None:
        return None
    v = value.strip().lower()
    if v == "true":
        return True
    elif v == "false":
        return False
    return None

parser = argparse.ArgumentParser(description="Load CSV into MongoDB")
parser.add_argument("--file", "-f", default=CSV_FILE)
parser.add_argument("--schema", default="sfpl", help="MongoDB database name")
args = parser.parse_args()

CSV_FILE = args.file
DB_SCHEMA = args.schema

client = MongoClient("mongodb://localhost:27017/")
db = client[DB_SCHEMA]
collection = db["patrons"]

print("Connected to MongoDB")

start_time = time.time()

documents = []

with open(CSV_FILE, newline='', encoding='utf-8') as f:
    reader = csv.reader(f)

    next(reader, None)
    header = next(reader, None)

    for data in reader:
        if not data or not any(cell.strip() for cell in data):
            continue

        def g(i):
            return data[i].strip() if i < len(data) and data[i] is not None else ""

        patron_type_code = g(0)
        patron_type_def  = g(1)

        try:
            total_checkouts = int(g(2)) if g(2) else None
        except:
            total_checkouts = None

        try:
            total_renewals = int(g(3)) if g(3) else None
        except:
            total_renewals = None

        doc_id = len(documents) + 1
        doc = {
            "_id": doc_id,
            "Patron_ID": doc_id,
            "Patron_Type_Code": patron_type_code,
            "Patron_Type_Definition": patron_type_def,
            "Total_Checkouts": total_checkouts,
            "Total_Renewals": total_renewals,
            "Age_Range": g(4),
            "Home_Library_Code": g(5),
            "Home_Library_Definition": g(6),
            "Circulation_Active_Month": g(7),
            "Circulation_Active_Year": g(8),
            "Notification_Preference_Code": g(9),
            "Notice_Preference_Definition": g(10),
            "Provided_Email_Address": parse_bool(g(11)),
            "Within_San_Francisco_County": parse_bool(g(12)),
            "Year_Patron_Registered": g(13)
        }
        documents.append(doc)

collection.insert_many(documents)

end_time = time.time()
print(f"MongoDB insert complete in {end_time - start_time:.3f} seconds")
