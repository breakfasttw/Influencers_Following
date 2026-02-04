import pandas as pd
import pytesseract
from PIL import Image

# 1. 設定 Tesseract 路徑
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def ocr_to_csv(image_path, output_csv):
    # 2. 讀取圖片
    img = Image.open(image_path)
    
    # 3. 使用 image_to_data 獲取詳細資訊 (包含座標)
    # config 參數 '--psm 6' 代表假設圖片為單一區塊的表格文字
    data = pytesseract.image_to_data(img, lang='chi_tra', output_type=pytesseract.Output.DATAFRAME)
    
    # 4. 過濾掉空白的辨識結果
    df = data[data['text'].notna() & (data['text'] != '')].copy()
    
    if df.empty:
        print("未辨識出任何文字")
        return

    # 5. 排序與分行邏輯
    # 表格處理的核心：將 y 座標相近的文字歸類為同一行
    # 我們將 y 座標除以一個「行高度閾值」（例如 20-30 像素），將其群組化
    line_threshold = 20 
    df['line_group'] = (df['top'] // line_threshold)
    
    # 先按行群組排序，再按水平座標 (left) 排序
    df = df.sort_values(by=['line_group', 'left'])
    
    # 6. 重組文字為逗號分隔格式
    rows = []
    for _, group in df.groupby('line_group'):
        # 將同一行的文字用逗號串接
        line_text = ",".join(group['text'].astype(str))
        rows.append(line_text)
    
    # 7. 寫入 CSV
    with open(output_csv, 'w', encoding='utf-8-sig') as f:
        for row in rows:
            f.write(row + '\n')
            
    print(f"辨識完成！CSV 檔案已儲存：{output_csv}")

# 使用範例
ocr_to_csv('page_1.png', 'output_ranking.csv')