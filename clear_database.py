from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
database_name = input("請輸入要刪除的資料庫名稱：")
client.drop_database(database_name)

print(f"資料庫 {database_name} 已删除。")