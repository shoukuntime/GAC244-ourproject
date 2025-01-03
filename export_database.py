from pymongo import MongoClient
from bson.json_util import dumps
import os

# 配置
DB_NAME = "myDatabase"
OUTPUT_DIR = "./exports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

client = MongoClient("mongodb://localhost:27017/")
db = client[DB_NAME]

for collection_name in db.list_collection_names():
    print(f"Exporting collection: {collection_name}")
    collection = db[collection_name]
    data = list(collection.find({}))
    
    with open(os.path.join(OUTPUT_DIR, f"{collection_name}.json"), "w", encoding="utf-8") as file:
        file.write(dumps(data, indent=4, ensure_ascii=False))

print("Export complete. Files are saved in", OUTPUT_DIR)