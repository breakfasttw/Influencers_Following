from pdf2image import convert_from_path
import os

# 設定 PDF 路徑
pdf_path = r'2025百大網紅排行榜.pdf'

# 電腦中 poppler bin 資料夾的實際路徑
POPPLER_PATH = r'D:\tools\poppler\Library\bin'

# 輸出目錄
# 路徑不存在就新增
OUTPUT_DIR = 'Output'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


try:
    # 3. 高品質轉換
    # 加入 poppler_path 參數
    images = convert_from_path(
        pdf_path, 
        dpi=600, 
        fmt='png', 
        poppler_path=POPPLER_PATH
    )

    # 4. 儲存圖片
    for i, image in enumerate(images):
        # 修正：直接在 OUTPUT_DIR 下存檔
        save_path = os.path.join(OUTPUT_DIR, f'page_{i+1}.png')
        image.save(save_path, 'PNG')
        print(f'Page {i+1} saved at {save_path}')

except Exception as e:
    print(f"轉換失敗：{e}")


