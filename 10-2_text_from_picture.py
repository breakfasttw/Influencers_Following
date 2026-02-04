import cv2
from paddleocr import PaddleOCR
import pandas as pd

# 1. 初始化 OCR 引擎 (支持繁體中文)
# lang='chinese_cht' 代表繁體中文
ocr = PaddleOCR(use_angle_cls=True, lang='chinese_cht')

def image_to_csv(image_path, output_csv):
    # 2. 執行 OCR 辨識
    result = ocr.ocr(image_path, cls=True)
    
    # 3. 提取文字與座標
    data_list = []
    for line in result[0]:
        coords = line[0]  # 文字方塊的四個角座標
        text = line[1][0] # 辨識出的文字
        
        # 取左上角的 y 座標與 x 座標作為排序依據
        x_top_left = coords[0][0]
        y_top_left = coords[0][1]
        
        data_list.append({
            'text': text,
            'x': x_top_left,
            'y': y_top_left
        })

    # 4. 邏輯處理：根據座標將文字分組到「行」
    # 由於表格掃描可能會有微小偏斜，我們對 y 座標進行些許模糊處理（例如差距 10 像素內視為同一行）
    df_raw = pd.DataFrame(data_list)
    df_raw = df_raw.sort_values(by=['y', 'x']) # 先排 y 再排 x

    # 簡單的行分組演算法
    rows = []
    if not df_raw.empty:
        current_row = [df_raw.iloc[0]['text']]
        last_y = df_raw.iloc[0]['y']
        
        for i in range(1, len(df_raw)):
            if df_raw.iloc[i]['y'] - last_y < 15:  # 容錯間距 15 像素
                current_row.append(df_raw.iloc[i]['text'])
            else:
                rows.append(",".join(current_row))
                current_row = [df_raw.iloc[i]['text']]
                last_y = df_raw.iloc[i]['y']
        rows.append(",".join(current_row))

    # 5. 儲存為 CSV
    with open(output_csv, 'w', encoding='utf-8-sig') as f:
        for row in rows:
            f.write(row + '\n')
            
    print(f"辨識完成！檔案已儲存至: {output_csv}")

# 使用範例
image_to_csv('page_1.png', 'social_media_ranking.csv')