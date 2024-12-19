from pymongo import MongoClient

# 连接到 MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client['myDatabase']
collection = db['myCollection']

# 插入数据
collection.insert_one({"name": "Alice", "age": 25})
collection.insert_many([
    {"name": "Bob", "age": 30},
    {"name": "Charlie", "age": 35}
])

# 查询数据
for doc in collection.find():
    print(doc)

# 更新数据
collection.update_one({"name": "Alice"}, {"$set": {"age": 26}})

# 删除数据
collection.delete_one({"name": "Bob"})

# 查看索引
print(collection.index_information())