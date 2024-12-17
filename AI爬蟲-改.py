import google.generativeai as genai
import configparser
from bs4 import BeautifulSoup
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import csv
import time

start_total_time=time.time()
# Config Parser
config = configparser.ConfigParser()
config.read('config.ini')

# 設定 Google Generative AI
genai.configure(api_key=config.get('Google', 'GEMINI_API_KEY'))
model = genai.GenerativeModel(
    model_name='gemini-2.0-flash-exp',
    generation_config={
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
    },)

url='https://www.tainex.com.tw/'
path=r'chromedriver-win64\chromedriver.exe' #chromedriver的位置
service=Service(path)
chrome_options = Options()
chrome_options.add_argument("--headless")  # 無頭模式
chrome_options.add_argument("--disable-gpu")  # 避免一些 GPU 渲染問題
chrome_options.add_argument("--no-sandbox")  # 適用於 Linux 環境，避免權限問題
chrome = webdriver.Chrome(service=service,options=chrome_options)
chrome.get(url)
html=chrome.page_source
soup=BeautifulSoup(html,'lxml')

def promt_to_json(prompt):
    response = model.generate_content(prompt, generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ))
    result = response._result.candidates[0].content.parts[0].text
    result=json.loads(result)
    return result

prompt=f"""
    以下是展覽網站的HTML，請提取以下資訊：
    1. 展覽名稱
    2. 展覽日期
    3. 展覽地點
    4. 展覽網址

    如果無法找到某項資訊，請用正確相關網址代替(若是相對網址請加上{url})，若都沒有請回傳空字串。
    請去除所有分號';'，並將結果以 JSON 格式輸出，請依照以下格式輸出：
    {{'exhibitions': [
        {{
            "name": "展覽名稱",
            "date": "展覽日期",
            "location": "展覽地點",
            "url": "展覽網址"
        }},
        ...
    ]}}

    HTML：
    {soup}
    """

result=promt_to_json(prompt)

prompt1=f"""
    {result}
    請你為此json檔中的所有url相似度做評分，0為完全不相似，1為完全相似，
    並將評分結果以json格式輸出，請依照以下格式輸出：
    {{
        "score": 0.9
    }}
    評分標準:
    1. ["https://www.kje.com.tw/exhibition/ins.php?index_id=236",
        "https://www.kje.com.tw/exhibition/ins.php?index_id=234",
        "https://www.kje.com.tw/exhibition/ins.php?index_id=243",...]時的相似度大約為0.95
    2. ["https://www.chanchao.com.tw/petsshow/kaohsiung/",
        "https://www.tibs.org.tw/",
        "https://www.chanchao.com.tw/ATLife/",...]時的相似度大約為0.5
    3. ["https://www.tigax.com.tw/zh-tw/index.html",
        "http://www.energytaiwan.com.tw",
        "http://ohstudy.net",...]時的相似度大約為0.05
    """
r=promt_to_json(prompt1)
print(r)
score=float(r['score'])
print(f'相似度評分為{score}')
if score>0.75:
    print('爬找第二層')
    exhibitions=result['exhibitions']
    data=[]
    for exhibition in exhibitions:
        name=exhibition['name']
        link=exhibition['url']
        chrome.get(link)
        html=chrome.page_source
        soup=BeautifulSoup(html,'lxml')
        prompt2=f"""
        {soup}是展覽網站的HTML，網站名稱為{name}，請找到官網連結(請不要選擇與{url}過於相似的網站，優先選擇關鍵字'官方網站'相關連結)，
        並將結果以json格式輸出，例如：
        {{'name': '2024 桃園聖誕婚禮市集 11/30-12/01',
        'url': 'https://www.kje.com.tw/exhibition/ins.php?index_id=236'}}
        """
        data.append([promt_to_json(prompt2)])

    prompt3=f"""
        將{result}更新url為{data}，但格式依然與原本相同，
        並將結果以json格式輸出，例如：
        {{'exhibitions': [
            {{
                "name": "展覽名稱",
                "date": "展覽日期",
                "location": "展覽地點",
                "url": "展覽網址"
            }},
            ...
        ]}}
        """
    result=promt_to_json(prompt3)


with open("exhibitions.csv", mode='w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=['name', 'date', 'location', 'url'])
    # 寫入表頭
    writer.writeheader()
    # 寫入每個展覽的資料
    writer.writerows(result['exhibitions'])

end_total_time=time.time()
total_time=end_total_time-start_total_time
print(f'全部執行完畢，總共花費{round(total_time)}秒')
print(result)