# 鎮均的程式

### 展昭爬蟲.py
針對展昭的所有展覽，將詳細資料存成csv

### 檔期爬蟲.py
針對世貿的所有展覽，將詳細資料存成csv

### AI爬蟲-母.py
針對所有母展覽集，將子展覽主要資訊(名稱、日期、地點、網址)存成csv

### AI爬蟲-子.py
針對所有子展覽，將子展覽主要資訊(參展廠商列表(name,logo,id,type,info,url)、展覽平面圖)存成json、csv

### AI_first.py
AI爬蟲-母的延伸，存入MongoDB

### AI_second.py
AI爬蟲-子的延伸，存入MongoDB

### clear_database.py
將database資料清除

### export_database.py
將database資料所有collection存成json

### click.py
依照使用者點擊多少次展覽來進行協同演算的測試檔

### myfavorite.py
依照使用者設定我的最愛來進行協同演算的測試檔(1:表示加入最愛，0:未加入最愛，-1:系統推薦且不喜歡)