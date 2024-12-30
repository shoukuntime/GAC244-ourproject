import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# 構建數據
data = {
    'User': ['A', 'A', 'B', 'B', 'C', 'C','D', 'D'],
    'Item': ['Item1', 'Item2', 'Item1', 'Item3', 'Item2', 'Item3', 'Item1', 'Item3'],
    'Rating': [1, -1, 1, 1, 1, -1, -1, 1]
}

# 轉換為 DataFrame
df = pd.DataFrame(data)

# 創建使用者-物品矩陣
user_item_matrix = df.pivot_table(index='User', columns='Item', values='Rating', fill_value=0)

print("User-Item Matrix:")
print(user_item_matrix)

# 計算使用者之間的餘弦相似度
user_similarity = pd.DataFrame(
    np.round(cosine_similarity(user_item_matrix), 2),
    index=user_item_matrix.index,
    columns=user_item_matrix.index
)

print("\nUser Similarity Matrix:")
print(user_similarity)

# 為 user 推薦物品
def recommend_items(user, user_item_matrix, user_similarity):
    # 找到該使用者的相似使用者
    similar_users = user_similarity[user].sort_values(ascending=False).drop(user)
    
    # 取出相似使用者的物品偏好，考慮負評（-1）和正評（1）的影響
    recommendations = pd.Series(dtype=float)
    for similar_user, similarity in similar_users.items():
        # 加權物品評分
        recommendations = recommendations.add(user_item_matrix.loc[similar_user] * similarity, fill_value=0)
    
    # 排除該使用者已經明確表態（1 或 -1）的物品
    already_rated = user_item_matrix.loc[user]
    recommendations = recommendations[already_rated == 0].sort_values(ascending=False)
    return recommendations

# 推薦給 user
user='A'
user_recommendations = recommend_items(user, user_item_matrix, user_similarity)

print(f"\nRecommendations for {user}:")
print(user_recommendations)