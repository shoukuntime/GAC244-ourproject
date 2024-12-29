from pymongo import MongoClient
from bson.json_util import dumps
import os

# 配置
DB_NAME = "myDatabase"
OUTPUT_DIR = "./exports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 连接 MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client[DB_NAME]

# 导出所有集合
for collection_name in db.list_collection_names():
    print(f"Exporting collection: {collection_name}")
    collection = db[collection_name]
    data = list(collection.find({}))
    
    # 写入 JSON 文件，保持中文输出
    with open(os.path.join(OUTPUT_DIR, f"{collection_name}.json"), "w", encoding="utf-8") as file:
        file.write(dumps(data, indent=4, ensure_ascii=False))  # 添加 ensure_ascii=False

print("Export complete. Files are saved in", OUTPUT_DIR)