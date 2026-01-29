import sys
# 針對 Python 3.12+ 移除 distutils 的相容性補丁
try:
    import distutils.version
except ImportError:
    import types
    d = types.ModuleType("distutils")
    v = types.ModuleType("distutils.version")
    class LooseVersion:
        def __init__(self, vstring): self.vstring = vstring
        def __str__(self): return self.vstring
    v.LooseVersion = LooseVersion
    d.version = v
    sys.modules["distutils"] = d
    sys.modules["distutils.version"] = v

import os
import time
import random
import pandas as pd
from datetime import datetime
import undetected_chromedriver as uc
# --- 補齊缺失的 Selenium 引用 ---
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ================= 配置設定 =================
CSV_FILE = "Top200_ig_20260126.csv"
SAVE_FOLDER = os.path.join(os.getcwd(), "ExportTool")
LOG_FILE = "extent_log.txt"
PROCESSED_LIST_FILE = "processed_list.txt"
EXTENSION_ID = "iindafjcdjddenmiacdelomccfblfllm"

# ===========================================

if not os.path.exists(SAVE_FOLDER): os.makedirs(SAVE_FOLDER)

def write_log(message):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def get_processed_list():
    if os.path.exists(PROCESSED_LIST_FILE):
        with open(PROCESSED_LIST_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    return set()

def mark_as_processed(username):
    with open(PROCESSED_LIST_FILE, "a", encoding="utf-8") as f:
        f.write(username + "\n")

def setup_driver():
    options = uc.ChromeOptions()
    
    # 這裡只寫到 User Data 為止，不要寫到 Profile
    user_data_path = r"C:/Users/Tiffany/AppData/Local/Google/Chrome/User Data"
    # 這裡指定資料夾名稱 (例如 "Profile 2" 或 "Default")
    profile_name = "Profile 2" 
    
    options.add_argument(f"--user-data-dir={user_data_path}")
    options.add_argument(f"--profile-directory={profile_name}")

    # 加入這個參數可以避免很多啟動時的權限錯誤
    options.add_argument("--disable-dev-shm-usage") 
    options.add_argument("--no-sandbox")

    driver = uc.Chrome(options=options, use_subprocess=True) 
    return driver

def run_scraper():
    df = pd.read_csv(CSV_FILE)
    all_targets = df['ig_id'].tolist()
    processed_targets = get_processed_list()
    
    targets_to_run = [t for t in all_targets if t not in processed_targets]
    print(f"總計: {len(all_targets)} 筆, 已完成: {len(processed_targets)} 筆, 剩餘: {len(targets_to_run)} 筆")

    driver = None

    for username in targets_to_run:
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"起始執行時間: {start_time}\n網紅帳號: {username}\n"
        
        try:
            if driver is None:
                driver = setup_driver()
                if driver is None: raise Exception("無法初始化瀏覽器")
            
            target_url = f"chrome-extension://{EXTENSION_ID}/tabs/Export.html?username={username}&type=Following"
            driver.get(target_url)
            print(f"[{username}] 正在抓取名單...")
            
            # 1. 等待名單載入 (3分鐘)
            time.sleep(180) 
            
            # 2. 點擊 DOWNLOAD ALL
            download_trigger_xpath = "//button[contains(., 'DOWNLOAD ALL')]"
            WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, download_trigger_xpath))).click()
            
            # 3. 點擊 DOWNLOAD ALL TO CSV
            csv_option_xpath = "//span[contains(text(), 'DOWNLOAD ALL TO CSV')]"
            WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, csv_option_xpath))).click()
            
            time.sleep(15) # 等待下載
            
            log_entry += "檔案下載成功: YES\n"
            mark_as_processed(username)
            print(f"[{username}] 完成！")

        except Exception as e:
            error_msg = str(e).replace('\n', ' ')
            log_entry += f"檔案下載成功: NO\n錯誤訊息: {error_msg}\n"
            print(f"[{username}] 發生錯誤: {e}")
            if driver:
                try: driver.quit()
                except: pass
                driver = None

        finally:
            write_log(log_entry + "\n")
            rest_time = random.randint(300, 480)
            if username != targets_to_run[-1]:
                print(f"防封鎖機制：隨機休息 {rest_time} 秒...")
                time.sleep(rest_time)

    if driver: driver.quit()
    print("所有任務執行完畢。")

if __name__ == "__main__":
    run_scraper()