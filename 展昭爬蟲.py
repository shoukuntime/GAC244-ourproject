import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

path=r'chromedriver-win64\chromedriver.exe' #chromedriver的位置
service=Service(path)
chrome_options = Options()
chrome_options.add_argument("--headless")  # 無頭模式
chrome_options.add_argument("--disable-gpu")  # 避免一些 GPU 渲染問題
chrome_options.add_argument("--no-sandbox")  # 適用於 Linux 環境，避免權限問題
chrome = webdriver.Chrome(service=service,options=chrome_options)

list=['展覽介紹','展覽平面圖','參展商列表','參展商產品','參展商新聞稿','參展商影音','交通資訊'] #關鍵字

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

def find_text_url(url,soup,target_text): #找關鍵詞連結 
    for tag in soup.find_all(string=True):
        if target_text in tag:
            # print("找到目標文本！")
            # print(f"所在標籤: {tag.parent}")
            # print(f"完整内容: {tag.strip()}")
            try:
                href=url+tag.parent.get('href')
                return href
            except:
                continue
    return ''
    
def get_more_info(chrome,url,list): #展覽詳細資訊
    chrome.get(url)
    html=chrome.page_source
    soup=BeautifulSoup(html,'lxml')
    data=[]
    for tag in list:
        data.append(find_text_url(url,soup,tag))
    return data

def page_data(chrome,page,list): #整頁展覽資訊
    url=f"https://www.chanchao.com.tw/expo.asp?page={page}&t=C&country=TW"
    chrome.get(url)
    html=chrome.page_source
    soup=BeautifulSoup(html,'lxml')
    expo=soup.find('ul',class_='expo')
    lis=expo.find_all('li')
    data=[]
    for li in lis:
        href=li.find('h4').find('a').get('href')
        title=li.find('h4').text
        id=href.split('?')[-1]
        detail_url='https://www.chanchao.com.tw/expoDetail.asp?'+id
        try:
            website=li.find('a',class_='website').get('href')
        except:
            website=''
        ps=li.find_all('p')
        date=ps[1].text
        place=ps[2].text
        type=ps[4].text.strip('臺灣 / ')
        if website!='':
            more_urls=get_more_info(chrome,website,list)
        else:
            more_urls=['' for i in list]
        print(title)
        data.append([title,date,place,type,detail_url,website]+more_urls)
    return data

start_total_time=time.time()

datas=[]
for i in [1,2]:
    data=page_data(chrome,i,list)
    datas.extend(data)

end_total_time=time.time()
total_time=end_total_time-start_total_time
print(f'全部執行完畢，總共花費{round(total_time)}秒')

df=pd.DataFrame(datas,columns=['展覽名稱','日期/狀態','地點','類別','詳細資訊','展覽網址']+list)
df.to_csv("展昭資料.csv",encoding="utf-8-sig")
    