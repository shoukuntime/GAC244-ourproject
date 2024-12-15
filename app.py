import google.generativeai as genai
import configparser
from bs4 import BeautifulSoup
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Config Parser
config = configparser.ConfigParser()
config.read('config.ini')

# 設定 Google Generative AI
genai.configure(api_key=config.get('Google', 'GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

#利用geminai的模型寫一個自動抓取展覽資訊的爬蟲程式

url = "https://www.tigax.com.tw/zh-tw/exhibitor/show-area-data/index.html"

path=r'chromedriver-win64\chromedriver.exe' #chromedriver的位置
service=Service(path)
chrome_options = Options()
chrome_options.add_argument("--headless")  # 無頭模式
chrome_options.add_argument("--disable-gpu")  # 避免一些 GPU 渲染問題
chrome_options.add_argument("--no-sandbox")  # 適用於 Linux 環境，避免權限問題
chrome = webdriver.Chrome(service=service,options=chrome_options)

def fetch_html_content(url):
    chrome.get(url)
    html=chrome.page_source
    soup=BeautifulSoup(html,'lxml')
    return soup

def analyze_html_with_ai(url):
    html_content = fetch_html_content(url)
    prompt = f"""
    以下是展覽網站的 HTML，請提取以下資訊：
    1. 展覽名稱
    2. 展覽日期
    3. 展覽地點
    4. 展覽簡介
    5. 展覽平面圖
    6. 參展商列表
    7. 參展商產品
    8. 參展商新聞稿
    9. 參展商影音
    10. 交通資訊

    如果無法找到某項資訊，請用正確相關網址代替(若是相對網址請加上{url})，若都沒有請回傳空字串。
    請將結果以 JSON 格式輸出，例如：
    {{
        "name": "展覽名稱",
        "date": "展覽日期",
        "location": "展覽地點",
        "description": "展覽簡介"
        "floor_plan": "展覽平面圖",
        "exhibitors_list": "參展商列表",
        "exhibitors_products": "參展商產品",
        "exhibitors_press_release": "參展商新聞稿",
        "exhibitors_videos": "參展商影音",
        "transportation_info": "交通資訊"
    }}

    HTML：
    {html_content}  # 截取前 4000 字符
    """
    
    try:
        parameters = {
        "max_tokens": 100,
        "temperature": 0.5,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "stop": "\n"
    }
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ))
        print(response)
        # result = response.text.strip()
        result = response._result.candidates[0].content.parts[0].text
        print(result)
        parsed_response = json.loads(result)
        print(parsed_response)
        # corrected_data = {key: unicodedata.normalize("NFKC", value) for key, value in parsed_response.items()}
    
        # 輸出結果
        # print(json.dumps(parsed_response, ensure_ascii=False, indent=2))
        return parsed_response
    except Exception as e:
        print(f"Error during AI analysis: {e}")
        return {
            "name": "N/A",
            "date": "N/A",
            "location": "N/A",
            "description": "N/A"
        }

def save_to_csv(data, filename="exhibition_info.csv"):
    import csv
    with open(filename, mode="w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        writer.writeheader()
        writer.writerow(data)

def main():
    print("正在使用生成式 AI 分析 HTML 並提取資訊...")
    exhibition_info = analyze_html_with_ai(url)
    
    print("提取結果：")
    for key, value in exhibition_info.items():
        print(f"{key}: {value}")
    
    print("保存結果到 CSV...")
    save_to_csv(exhibition_info)
    print("完成！")

if __name__ == "__main__":
    main()      