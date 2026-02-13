import cv2
import pytesseract

# 如果 Tesseract 沒有在系統路徑，指定其安裝路徑
# Windows 上可能需要以下設置：
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 讀取圖像文件
image = cv2.imread('page_1.png')

# 使用 Tesseract 辨識圖像中的文字
text = pytesseract.image_to_string(image, lang='chi_tra')  # 'chi_tra' 是繁體中文的語言代碼

# 打印辨識出的文字
print(text)
