import os
import cv2
import requests
from configparser import ConfigParser
import numpy as np
import json
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
import pytesseract
import networkx as nx
from scipy.spatial import distance
from scipy.ndimage import distance_transform_edt
import matplotlib.pyplot as plt
import random
import google.generativeai as genai
import configparser
import json
import re

config = ConfigParser()
config.read("config.ini")

# Azure Computer Vision 設定
CV_KEY = config.get('Azure', 'CV_KEY')
CV_ENDPOINT = config.get('Azure', 'CV_ENDPOINT')

# Create an Image Analysis client
client = ImageAnalysisClient(
    endpoint=CV_ENDPOINT,
    credential=AzureKeyCredential(CV_KEY)
)

# 圖片路徑
EXHIBITION_MAP = 'test4.jpg'
with open(EXHIBITION_MAP, "rb") as f:
        image_data = f.read()

# client.analyze_from_url
result = client.analyze(
    image_data=image_data,
    visual_features=[VisualFeatures.READ]
)

def calculate_center(boundingPolygon):
    """
    計算給定四邊形的中心點。

    Args:
        boundingPolygon (list): 四個頂點的座標 [{'x': x1, 'y': y1}, {'x': x2, 'y': y2}, ...]

    Returns:
        dict: 中心點的座標 {'x': cx, 'y': cy'}
    """
    # 計算中心點
    x_coords = [point['x'] for point in boundingPolygon]
    y_coords = [point['y'] for point in boundingPolygon]
    center_x = round(sum(x_coords) / len(x_coords))
    center_y = round(sum(y_coords) / len(y_coords))
    return {'x': center_x, 'y': center_y}

def extract_centers(data):
    """
    從給定資料中提取每個詞語的中心點並整理為 JSON 格式。

    Args:
        data (dict): JSON 格式的資料，包含 'blocks' -> 'lines' -> 'boundingPolygon'.

    Returns:
        list: 包含詞語和中心點的 JSON 資料 [{'text': '詞語', 'center': {'x': cx, 'y': cy}}]
    """
    result = []
    for block in data.get('blocks', []):
        for line in block.get('lines', []):
            text = line['text']
            boundingPolygon = line['boundingPolygon']
            center = calculate_center(boundingPolygon)
            result.append({'text': text, 'center': center})
    return result



#處理展覽地圖，生成攤位框和道路遮罩
def process_map_with_mask(image_path, output_path_mask, output_path_boxes):
    """
    處理展覽地圖，生成攤位框和道路遮罩。

    Args:
        image_path (str): 輸入圖片路徑。
        output_path_mask (str): 保存道路遮罩的路徑。
        output_path_boxes (str): 保存攤位框的路徑。
    """
    # 讀取圖像
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"無法讀取圖像: {image_path}")

    # 轉換為灰度圖像
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 邊緣檢測
    edges = cv2.Canny(gray_image, 30, 100, apertureSize=3)

    # 霍夫直線檢測（調整效率！）
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=30, maxLineGap=20)

    # 創建一個空白遮罩圖像
    mask = np.ones_like(gray_image) * 255  # 初始為全白（道路）
    boxes_image = image.copy()  # 用於顯示攤位框的圖像

    vertical_lines = []
    horizontal_lines = []

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # 判斷是垂直線還是水平線
            if abs(x1 - x2) < 10:  # 垂直線
                vertical_lines.append((x1, y1, x2, y2))
            elif abs(y1 - y2) < 10:  # 水平線
                horizontal_lines.append((x1, y1, x2, y2))

    # 確定網格的交點
    vertical_lines = sorted(vertical_lines, key=lambda x: x[0])  # 按 x 坐標排序
    horizontal_lines = sorted(horizontal_lines, key=lambda x: x[1])  # 按 y 坐標排序

    # 遍歷網格框
    for i in range(len(vertical_lines) - 1):
        for j in range(len(horizontal_lines) - 1):
            # 確定網格邊界
            x1 = vertical_lines[i][0]
            x2 = vertical_lines[i + 1][0]
            y1 = horizontal_lines[j][1]
            y2 = horizontal_lines[j + 1][1]

            # 提取網格內部的區域
            grid_region = gray_image[y1:y2, x1:x2]
            avg_intensity = np.mean(grid_region)  # 計算網格內像素的平均亮度

            # 判斷是否為攤位（根據亮度）
            if avg_intensity < 200:  # 假設暗區域是攤位
                # 填充攤位區域為黑色（遮罩）
                mask[y1:y2, x1:x2] = 0
                # 在框圖上標記攤位框
                cv2.rectangle(boxes_image, (x1, y1), (x2, y2), (0, 255, 0), 2)  # 綠色框標記攤位

    # 再次檢測封閉區域，處理非矩形區域（如梯形）
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        # 計算輪廓的面積，過濾過小的區域
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)

        # 檢查是否為接近整張圖的外框
        if (x <= 5 or y <= 5 or x + w >= gray_image.shape[1] - 5 or y + h >= gray_image.shape[0] - 5) and area > 0.9 * gray_image.shape[0] * gray_image.shape[1]:
            continue  # 忽略接近整張圖大小的外框

        if area > 500:  # 可根據需求調整面積閾值
            # 判斷輪廓是否為封閉區域
            perimeter = cv2.arcLength(contour, True)
            if cv2.isContourConvex(contour) or (perimeter > 0 and area / perimeter > 5):
                # 填充封閉區域為黑色
                cv2.fillPoly(mask, [contour], 0)

    # 保存遮罩圖像
    cv2.imwrite(output_path_mask, mask)

    # 保存攤位框圖像
    cv2.imwrite(output_path_boxes, boxes_image)

# process_map_with_mask(EXHIBITION_MAP, "road_mask.jpg", "booth_boxes.png")


#*********粗的路線
def find_connected_region(mask, start_point):
    """
    找到遮罩圖中指定起始點所屬的黑色區域。

    Args:
        mask (numpy.ndarray): 遮罩圖像。
        start_point (tuple): 起始點座標 (x, y)。

    Returns:
        list: 黑色區域中的所有像素座標列表。
    """
    h, w = mask.shape
    visited = np.zeros((h, w), dtype=bool)
    region = []
    stack = [start_point]

    while stack:
        x, y = stack.pop()
        if visited[y, x]:
            continue
        visited[y, x] = True
        region.append((x, y))
        # 檢查四周像素
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx_, ny_ = x + dx, y + dy
            if 0 <= nx_ < w and 0 <= ny_ < h and mask[ny_, nx_] == 0 and not visited[ny_, nx_]:
                stack.append((nx_, ny_))
    return region

def find_boundary_point(mask, region):
    """
    找到黑色區域中與白色道路鄰接的第一個像素。

    Args:
        mask (numpy.ndarray): 遮罩圖像。
        region (list): 黑色區域中的所有像素座標。

    Returns:
        tuple: 與道路鄰接的第一個白色像素座標。
    """
    h, w = mask.shape
    for x, y in region:
        # 檢查四周像素
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx_, ny_ = x + dx, y + dy
            if 0 <= nx_ < w and 0 <= ny_ < h and mask[ny_, nx_] == 255:
                return (nx_, ny_)
    return None

def update_point_to_boundary(mask, point):
    """
    將給定點更新到攤位區域與道路的鄰接點。

    Args:
        mask (numpy.ndarray): 遮罩圖像。
        point (tuple): 原始點座標 (x, y)。

    Returns:
        tuple: 更新後的點座標（鄰接白色道路的點）。
    """
    # 檢查點是否在黑色區域
    if mask[point[1], point[0]] != 0:
        raise ValueError(f"點 {point} 不在黑色區域內。")

    # 找到該點所屬的黑色區域
    region = find_connected_region(mask, point)

    # 找到與道路鄰接的第一個點
    boundary_point = find_boundary_point(mask, region)
    if boundary_point is None:
        raise ValueError(f"無法找到攤位區域與道路鄰接的點。")
    
    return boundary_point

def smooth_path(path):
    """
    對路徑進行平滑處理。

    Args:
        path (list): 路徑點列表。

    Returns:
        list: 平滑後的路徑。
    """
    smoothed_path = []
    for i in range(1, len(path) - 1):
        x_prev, y_prev = path[i - 1]
        x_curr, y_curr = path[i]
        x_next, y_next = path[i + 1]
        smoothed_x = (x_prev + x_curr + x_next) // 3
        smoothed_y = (y_prev + y_curr + y_next) // 3
        smoothed_path.append((smoothed_x, smoothed_y))
    return [path[0]] + smoothed_path + [path[-1]]

def calculate_shortest_path(img_path, mask_path, start_point, end_point, output_path):
    """
    根據展覽地圖遮罩圖計算兩點之間的最短路徑。

    Args:
        mask_path (str): 遮罩圖的路徑。
        start_point (tuple): 起點座標 (x, y)。
        end_point (tuple): 終點座標 (x, y)。
        output_path (str): 保存結果圖像的路徑。
    """
    # mask_path = "road_mask.png"
    start_point = start_point
    end_point = end_point
    # output_path = "shortest_path.png"
    # 讀取遮罩圖
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise FileNotFoundError(f"無法讀取遮罩圖: {mask_path}")
    original_img = cv2.imread(img_path)
    if original_img is None:
        raise FileNotFoundError(f"無法讀取原始圖像: {img_path}")

    # 計算距離轉換
    dist_transform = cv2.distanceTransform((mask == 255).astype(np.uint8), cv2.DIST_L2, 5)
    max_dist = np.max(dist_transform)  # 獲取距離轉換的最大值

    # 更新起點和終點到鄰接道路的白色像素
    start_point = update_point_to_boundary(mask, start_point)
    end_point = update_point_to_boundary(mask, end_point)

    # 構建圖
    graph = nx.Graph()
    rows, cols = mask.shape
    for y in range(rows):
        for x in range(cols):
            if mask[y, x] == 255:  # 僅將白色像素視為道路
                neighbors = [(y + dy, x + dx) for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]]
                for ny, nx_ in neighbors:
                    if 0 <= ny < rows and 0 <= nx_ < cols and mask[ny, nx_] == 255:
                        weight = max_dist - dist_transform[ny, nx_]  # 轉為正值權重
                        graph.add_edge((x, y), (nx_, ny), weight=weight)

    # 計算最短路徑
    try:
        path = nx.shortest_path(graph, source=start_point, target=end_point, weight='weight')
    except nx.NetworkXNoPath:
        raise ValueError("無法找到兩點之間的路徑。")

    # 平滑路徑
    path = smooth_path(path)

    # 在遮罩圖上繪製路徑
    result_image = original_img.copy()
    for i in range(len(path) - 1):
        start = path[i]
        end = path[i + 1]
        cv2.line(result_image, start, end, (0, 0, 255), thickness=5)  # 繪製紅線，線條加粗

    # 保存結果圖像
    cv2.imwrite(output_path, result_image)
    print(f"結果保存至 {output_path}")

process_map_with_mask(EXHIBITION_MAP, "road_mask.png", "booth_boxes.png")
word_location = extract_centers(result.read)

# 繪製路線圖
mask_path = "road_mask.png"

# 設定 Google Generative AI
api_keys = config.get('Google', 'GEMINI_API_KEY').replace('\n', '').split(',')

prompt=f"""
整理{result.read}的所有攤位的名稱、攤位號碼及攤位名稱在圖片的中心座標，請輸出json格式，必須使用utf-8編碼輸出中文，並使用以下格式：
{{
  "booths": [
    {{
      "name": "攤位名稱",
      "number": "攤位號碼",
      "location": {{
        "x": 123,
        "y": 456
      }}
    }},
    ...
  ]
}}
"""
genai.configure(api_key=random.choice(api_keys))
model = genai.GenerativeModel('gemini-1.5-flash',
    generation_config={
    "temperature": 0,
    "max_output_tokens": 8192,  # 設定輸出的最大字元數
    "response_mime_type":"application/json"
    })

chat_session = model.start_chat(
  history=[
    {
      "role": "user",
      "parts": [genai.upload_file(EXHIBITION_MAP, mime_type='image/jpg'),],
    },
  ]
)

response = chat_session.send_message(prompt)
print(response.text)
start = input('請輸入起點：')
end = input('請輸入終點：')

prompt1=f"""
    {response.text}是展覽廠商在展覽地圖上的位置，
    請提取起點{start}及終點{end}的座標，若沒有資料請回傳空字串，
    請依照以下格式輸出：
    {{
        "start": ['123','456'],
        "end": ['789','101']
    }}
"""

response = model.generate_content(prompt1, generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            ))
result=response.text
result=json.loads(re.sub(r'[\x00-\x1F\x7F]', '', result.replace('\n', '\\n').replace('\r', '\\r'))) or json.loads(result)
# print(result)
try:
    start_point = (int(result['start'][0]), int(result['start'][1]))
    end_point = (int(result['end'][0]), int(result['end'][1]))
    print(start_point, end_point)

    output_path = "shortest_path.png"
    original_img = EXHIBITION_MAP
    calculate_shortest_path(original_img, mask_path, start_point, end_point, output_path)

    # # 讀取遮罩圖
    mask_path = "road_mask.png"  # 替換為你的遮罩圖路徑
    mask = cv2.imread(mask_path, cv2.IMREAD_UNCHANGED)
    if mask is None:
        raise FileNotFoundError(f"無法讀取遮罩圖: {mask_path}")
except Exception as e:
    print(e)
    print('請重新輸入起點及終點')