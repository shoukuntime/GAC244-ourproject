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
model = genai.GenerativeModel('gemini-1.5-flash')

url='https://www.chanchao.com.tw/petsshow/kaohsiung/'
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
        是廠商列表的HTML，請找到各個廠商名稱、攤位號碼、基本資訊、廠商官方連結(若是相對網址請加上{companys})，若沒有請回傳空字串，
        若有下一頁，請找到下一頁連結，若無下一頁連結請回傳空字串，並將結果以json格式輸出，例如：
        {{'companys': [
        {{'name': '廠商名稱',
        'id': '攤位號碼',
        'info': '基本資訊',
        'url': '廠商官方連結'}},
        {{'name': '廠商名稱',
        'id': '攤位號碼',
        'info': '基本資訊',
        'url': '廠商官方連結'}},
        ...
        ],'next': '下一頁連結'}}
        """
    r=promt_to_json(prompt1)
    result1=r['companys']
    while r['next']!='':
        print(r['next'])
        next_page=r['next']
        chrome.get(next_page)
        html=chrome.page_source
        soup=BeautifulSoup(html,'lxml') #(連結中page代表所在頁面，不要找到比當前頁面還前面的連結)
        prompt1=f"""
            {soup}
            是廠商列表的HTML，請找到各個廠商名稱、攤位號碼、基本資訊、廠商官方連結(若是相對網址請加上{companys})，若沒有請回傳空字串，
            若有下一頁，請找到下一頁連結，若無下一頁連結請回傳空字串，並將結果以json格式輸出，例如：
            {{'companys': [
            {{'name': '廠商名稱',
            'id': '攤位號碼',
            'info': '基本資訊',
            'url': '廠商官方連結'}},
            {{'name': '廠商名稱',
            'id': '攤位號碼',
            'info': '基本資訊',
            'url': '廠商官方連結'}},
            ...
            ],'next': '下一頁連結'}}
            """
        r=promt_to_json(prompt1)
        result1.extend(r['companys'])
else:
    result1={'companys':''}
print(result1) #廠商列表list
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
        result2=promt_to_json(prompt2)
    else:
        result2={'map':result['map']}
else:
    result2={'map':''}

end_total_time=time.time()
total_time=end_total_time-start_total_time
print(f'全部執行完畢，總共花費{round(total_time)}秒')
result={'companys':result1,'map':[result2['map'],result['map']]}

#將結果寫入json
with open('result.json','w',encoding='utf-8') as f:
    json.dump(result,f,ensure_ascii=False,indent=4)

result_map=result['companys']
with open("companys.csv", mode='w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=['name', 'id', 'info', 'url'])
    # 寫入表頭
    writer.writeheader()
    # 寫入每個展覽的資料
    writer.writerows(result_map)