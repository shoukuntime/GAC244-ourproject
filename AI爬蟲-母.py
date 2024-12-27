import google.generativeai as genai
import configparser
from bs4 import BeautifulSoup
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import csv
import time
import random
import re

start_total_time=time.time()
# Config Parser
config = configparser.ConfigParser()
config.read('config.ini')
# 設定 Google Generative AI
api_keys = config.get('Google', 'GEMINI_API_KEY').replace('\n', '').split(',')

url=input('請輸入展覽集網址：')
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

def prompt_to_json(prompt):
    try:
        genai.configure(api_key=random.choice(api_keys))
        model = genai.GenerativeModel('gemini-1.5-flash',
            generation_config={
            "temperature": 0,
            "top_p": 0.01,
            "top_k": 1,
            "max_output_tokens": 8192,  # 設定輸出的最大字元數
            "response_mime_type":"application/json"
            })
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            ))
        result = response._result.candidates[0].content.parts[0].text
        history=[{"role": "user",
                "parts": [prompt]},
                {"role": "model",
                "parts": [result]}]
        token_count=response._result.usage_metadata.candidates_token_count
        while token_count==8192:
            chat_session = model.start_chat(history=history)
            response = chat_session.send_message("請接續輸出")
            history.append({"role": "model","parts": [response._result.candidates[0].content.parts[0].text]})
            token_count=response._result.usage_metadata.candidates_token_count
            print(token_count)
            result+=response.text
        result=json.loads(re.sub(r'[\x00-\x1F\x7F]', '', result.replace('\n', '\\n').replace('\r', '\\r'))) or json.loads(result)
        return result
    except Exception as e:
        print(e,'等待十秒')
        time.sleep(10)
        return prompt_to_json(prompt)
    

prompt=f"""
    {soup}是展覽網站的HTML，請提取以下資訊：
    1. 展覽名稱
    2. 展覽logo圖片網址
    3. 展覽日期
    4. 展覽地點
    5. 展覽網址

    如果無法找到某項資訊，請用正確相關網址代替(若是相對網址請加上{url})，若都沒有請回傳空字串。請去除所有分號';'，
    請找到關鍵字'上一頁'與'下一頁'的連結(若是相對網址請加上{url})，若沒有請回傳空字串，
    並將結果以 JSON 格式輸出，請依照以下格式輸出：
    {{'exhibitions': [
        {{
            "name": "展覽名稱",
            "logo": "展覽logo圖片網址",
            "date": "展覽日期",
            "location": "展覽地點",
            "url": "展覽網址"
        }},
        ...],'back': '上一頁連結',
        'next': '下一頁連結'}}
    """

result=prompt_to_json(prompt)
print(result['next'])
result1=result['exhibitions']
while result['next']!='':
    next_page=result['next']
    chrome.get(next_page)
    html=chrome.page_source
    soup=BeautifulSoup(html,'lxml')
    prompt_next=f"""
    {soup}是展覽網站的HTML，請提取以下資訊：
    1. 展覽名稱
    2. 展覽logo圖片網址
    3. 展覽日期
    4. 展覽地點
    5. 展覽網址

    如果無法找到某項資訊，請用正確相關網址代替(若是相對網址請加上{url})，若都沒有請回傳空字串。請去除所有分號';'，
    請找到關鍵字'上一頁'與'下一頁'的連結(若是相對網址請加上{url})，若沒有請回傳空字串，
    並將結果以 JSON 格式輸出，請依照以下格式輸出：
    {{'exhibitions': [
        {{
            "name": "展覽名稱",
            "logo": "展覽logo圖片網址",
            "date": "展覽日期",
            "location": "展覽地點",
            "url": "展覽網址"
        }},
        ...],'back': '上一頁連結',
        'next': '下一頁連結'}}
    """
    result=prompt_to_json(prompt_next)
    print(result['back'],result['next'])
    result1.extend(result['exhibitions'])

result1={'exhibitions':result1}

prompt1=f"""
    {result1}
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
r=prompt_to_json(prompt1)
# print(r)
score=float(r['score'])
print(f'相似度評分為{score}')
if score>0.75:
    print('爬找第二層')
    exhibitions=result1['exhibitions']
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
        data.append([prompt_to_json(prompt2)])

    prompt3=f"""
        將{result1}更新url為{data}，但格式依然與原本相同，
        並將結果以json格式輸出，例如：
        {{'exhibitions': [
            {{
                "name": "展覽名稱",
                "logo": "展覽logo圖片網址",
                "date": "展覽日期",
                "location": "展覽地點",
                "url": "展覽網址"
            }},
            ...
        ]}}
        """
    result1=prompt_to_json(prompt3)
# 關閉瀏覽器
chrome.quit()

with open("exhibitions.csv", mode='w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=['name','logo', 'date', 'location', 'url'])
    # 寫入表頭
    writer.writeheader()
    # 寫入每個展覽的資料
    writer.writerows(result1['exhibitions'])

end_total_time=time.time()
total_time=end_total_time-start_total_time
print(f'全部執行完畢，總共花費{round(total_time)}秒')
# print(result)