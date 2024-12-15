import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options

def get_soup(url): 
    soup=None 
    try:
        resp=requests.get(url)          
        if resp.status_code==200:
            soup=BeautifulSoup(resp.text,'lxml')
        else:
            print('網頁取得失敗',resp.status_code)
    except Exception as e:
        print('網址不正確!',e)
    return soup

def data_of_page(year,month_index):
    year_element = chrome.find_element(By.ID, "body_ddlYear")
    year_select = Select(year_element)
    year_select.select_by_value(year)
    time.sleep(0.5)
    month_element = chrome.find_element(By.ID, "body_ddlMoth")
    month_select = Select(month_element)
    month_select.select_by_index(month_index)
    time.sleep(0.5)
    html=chrome.page_source
    soup=BeautifulSoup(html,'lxml')
    tables=soup.find_all('table',class_='table table-striped fixed date_table')
    datas=[]
    for table in [tables[0]]:
        trs=table.find('tbody').find_all('tr')
        data=[]
        for tr in trs:
            tds=tr.find_all('td')
            date=tds[0].text
            name=tds[1].text.strip().strip(' \nmore')
            as_name=tds[1].find_all('a')
            if len(as_name)==1:
                name_href=''
                more_href='https://www.twtc.com.tw/'+as_name[0].get('href')
            else:
                name_href=as_name[0].get('href')
                more_href='https://www.twtc.com.tw/'+as_name[1].get('href')
            organizer=[text.strip() for text in tds[2].strings]
            try:
                organizer_href=tds[2].find('a').get('href')
            except:
                organizer_href=''
            if organizer_href=='http:// ':
                organizer_href=''
            phone=tds[3].text
            try:
                place=tds[4].text
            except:
                place=''
            data.append([year,date,name,organizer,phone,place,name_href,more_href,organizer_href])
        datas.extend(data)
    return datas
url="https://www.twtc.com.tw/exhibition"
path=r'chromedriver-win64\chromedriver.exe' #chromedriver的位置!
service=Service(path)
# 設置 Chrome 無頭模式
chrome_options = Options()
chrome_options.add_argument("--headless")  # 無頭模式
chrome_options.add_argument("--disable-gpu")  # 避免一些 GPU 渲染問題
chrome_options.add_argument("--no-sandbox")  # 適用於 Linux 環境，避免權限問題
chrome = webdriver.Chrome(service=service,options=chrome_options)
chrome.get(url)
datas=[]
for y in ['2023','2024','2025']:
    for i in range(4):
        datas.extend(data_of_page(y,i))
df=pd.DataFrame(datas,columns=['年份','展出日期', '展覽名稱', '主辦單位', '電話號碼', '展覽館別','展覽連結','更多資訊連結','主辦單位連結'])
df.to_csv("展覽資料.csv",encoding="utf-8-sig")