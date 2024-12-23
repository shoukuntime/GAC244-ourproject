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

url='https://www.touchtaiwan.com/'
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
    try:
        genai.configure(api_key=random.choice(api_keys))
        model = genai.GenerativeModel('gemini-1.5-flash',
            generation_config={
                "temperature": 0,
                "top_p": 0.01,
                "top_k": 1,
            },)
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            ))
        result = response._result.candidates[0].content.parts[0].text
        result=re.sub(r'[\x00-\x1F\x7F]', '', result.replace('\n', '\\n').replace('\r', '\\r'))
        result=json.loads(result)
        return result
    except Exception as e:
        print(e,'等待十秒')
        time.sleep(10)
        return promt_to_json(prompt)

prompt=f"""
    以下是展覽網站的HTML{soup}，請提取以下資訊的連結(若是相對網址請加上{url})，若都沒有請回傳空字串：
    1. 參展的廠商列表(參展品牌/參展商列表)
    2. 展覽平面圖(非google地圖)(若連結有'map'優先選擇)

    請去除所有分號';'，並將結果以 JSON 格式輸出，例如：
    {{'companys': '參展廠商列表連結',
    'map': '展覽平面圖連結'}}

    HTML：
    {soup}
    """

result=promt_to_json(prompt)
print(result)
if result['companys']!='':
    #抓取廠商列表
    companys=result['companys']
    chrome.get(companys)
    html=chrome.page_source
    soup=BeautifulSoup(html,'lxml')
    print('抓取廠商列表')
    prompt1=f"""
        {soup}
        是廠商列表的HTML，請找到各個廠商名稱、廠商logo圖片、攤位號碼、廠商類別、基本資訊(排除其他資訊)、廠商官方連結(若是相對網址請加上{url})，若沒有請回傳空字串，
        請找到關鍵字'上一頁'與'下一頁'的連結(若是相對網址請加上{url})，若沒有請回傳空字串，
        並將結果以json格式輸出，請以以下格式輸出：
        {{'companys': [
        {{'name': '廠商名稱',
        'logo': '廠商logo',
        'id': '攤位號碼',
        'type': '廠商類別',
        'info': '基本資訊',
        'url': '廠商官方連結'}},
        {{'name': '廠商名稱',
        'logo': '廠商logo',
        'id': '攤位號碼',
        'type': '廠商類別',
        'info': '基本資訊',
        'url': '廠商官方連結'}},
        ...
        ],'back': '上一頁連結',
        'next': '下一頁連結'}}
        """
    r=promt_to_json(prompt1)
    print(r['next'])
    result1=r['companys']
    while r['next']!='':
        next_page=r['next']
        chrome.get(next_page)
        html=chrome.page_source
        soup=BeautifulSoup(html,'lxml')
        prompt1=f"""
        {soup}
        是廠商列表的HTML，請找到各個廠商名稱、廠商logo圖片、攤位號碼、廠商類別、基本資訊(排除其他資訊)、廠商官方連結(若是相對網址請加上{url})，若沒有請回傳空字串，
        請找到關鍵字'上一頁'與'下一頁'的連結(若是相對網址請加上{url})，若沒有請回傳空字串，
        並將結果以json格式輸出，請以以下格式輸出：
        {{'companys': [
        {{'name': '廠商名稱',
        'logo': '廠商logo',
        'id': '攤位號碼',
        'type': '廠商類別',
        'info': '基本資訊',
        'url': '廠商官方連結'}},
        {{'name': '廠商名稱',
        'logo': '廠商logo',
        'id': '攤位號碼',
        'type': '廠商類別',
        'info': '基本資訊',
        'url': '廠商官方連結'}},
        ...
        ],'back': '上一頁連結',
        'next': '下一頁連結'}}
        """
        r=promt_to_json(prompt1)
        print(r['next'])
        result1.extend(r['companys'])
    prompt2=f"""
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
    r=promt_to_json(prompt2)
    score=float(r['score'])
    print(f'相似度評分為{score}')
    if score>0.75:
        print('爬找第二層')
        new_result1=[]
        for company in result1:
            try:
                name=company['name']
                link=company['url']
                chrome.get(link)
                html=chrome.page_source
                soup=BeautifulSoup(html,'lxml')
                prompt2=f"""
                {soup}是展覽網站的HTML，網站名稱為{name}，請找到官網連結(請不要選擇與{url}過於相似的網站，優先選擇關鍵字'官方網站'相關連結)，
                若無連結請回傳空字串，將結果以json格式輸出，例如：
                {{'name': '2024 桃園聖誕婚禮市集 11/30-12/01',
                'url': 'https://www.kje.com.tw/exhibition/ins.php?index_id=236'}}
                """
                new_link=promt_to_json(prompt2)['url']
                new_result1.append({'name':name,'id':company['id'],'type':company['type'],'info':company['info'],'url':new_link})
            except:
                new_result1.append(company)
        result1=new_result1

else:
    result1={'companys':''}

# print(result1) #廠商列表list
if result['map']!='':
    prompt_test=f"""
        檢查此連結{result['map']}是否為展覽平面圖連結(.jpg/.png/.jpeg/.gif/.bmp/.svg/.webp/.pdf)，
        若是請回傳'T'，若不是請回傳'F'，並將結果以json格式輸出，例如：
        {{'result': 'T'}}
        """
    test=promt_to_json(prompt_test)['result']
    print(test)
    print(result['map'])
    if test=='F':
        #抓取展覽平面圖
        map=result['map']
        chrome.get(map)
        html=chrome.page_source
        soup=BeautifulSoup(html,'lxml')
        print('抓取展覽平面圖')
        prompt2=f"""
            {soup}
            是展覽平面圖的HTML，請找到展覽平面圖的連結，若沒有請回傳空字串，並將結果以json格式輸出，例如：
            {{'map': '展覽平面圖連結'}}
            """
        try:
            result2=promt_to_json(prompt2)
        except:
            result2={'map':''}
    else:
        result2={'map':result['map']}
else:
    result2={'map':''}

end_total_time=time.time()
total_time=end_total_time-start_total_time
print(f'全部執行完畢，總共花費{round(total_time)}秒')
result={'companys':result1,'map':[result2['map'],result['map']]}
# 關閉瀏覽器
chrome.quit()

#將結果寫入json
with open('result.json','w',encoding='utf-8') as f:
    json.dump(result,f,ensure_ascii=False,indent=4)

result_map=result['companys']
with open("companys.csv", mode='w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=['name', 'id','logo', 'type', 'info', 'url'])
    # 寫入表頭
    writer.writeheader()
    # 寫入每個展覽的資料
    writer.writerows(result_map)