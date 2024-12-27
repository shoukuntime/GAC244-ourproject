import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# 模擬的使用者-展覽點擊矩陣
data = {
    'User': ['Alice', 'Alice', 'Alice', 'Bob', 'Bob', 'Charlie', 'Charlie', 'Charlie'],
    'Exhibition': ['Exhibition1', 'Exhibition2', 'Exhibition3', 'Exhibition1', 'Exhibition4', 'Exhibition2', 'Exhibition3', 'Exhibition4'],
    'Rating': [5, 3, 4, 4, 5, 3, 4, 5]
}

# 將數據轉換為 DataFrame
df = pd.DataFrame(data)

# 建立使用者-展覽矩陣
user_exhibition_matrix = df.pivot_table(index='User', columns='Exhibition', values='Rating', fill_value=0)

# 計算物品之間的相似度（餘弦相似度）
exhibition_similarity = cosine_similarity(user_exhibition_matrix.T)
exhibition_similarity_df = pd.DataFrame(exhibition_similarity, index=user_exhibition_matrix.columns, columns=user_exhibition_matrix.columns)

# 顯示展覽相似度矩陣
print("Item Similarity Matrix:")
print(exhibition_similarity_df)

# 定義推薦函數
def recommend_items(user, user_exhibition_matrix, exhibition_similarity_df, top_n=2):
    """
    給定使用者，根據物品相似度進行推薦
    """
    user_ratings = user_exhibition_matrix.loc[user]
    scores = exhibition_similarity_df.dot(user_ratings).div(exhibition_similarity_df.sum(axis=1))
    
    # 過濾掉已經點擊過的展覽
    recommendations = scores[user_ratings == 0].sort_values(ascending=False).head(top_n)
    return recommendations

# 測試推薦函數
user_to_recommend = "Alice"
recommendations = recommend_items(user_to_recommend, user_exhibition_matrix, exhibition_similarity_df)

print(f"\nRecommendations for {user_to_recommend}:")
print(recommendations)
