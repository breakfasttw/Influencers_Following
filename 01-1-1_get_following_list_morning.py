import instaloader
import pandas as pd
import time
import random
import os
import csv
import sys
import pygetwindow as gw # 用於檢查視窗標題
from datetime import datetime
from dotenv import load_dotenv

# 1. 初始化環境變數
load_dotenv()
SESSION_USER = os.getenv("SESSION_USER1")
INPUT_CSV = "600_todo.csv"

OUTPUT_DIR = 'Output'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
CHECKPOINT_FILE = os.path.join(OUTPUT_DIR, 'finished_list.txt')
LOG_FILE = os.path.join(OUTPUT_DIR, 'scraper_log.txt') 



# CSV 欄位定義
CSV_COLUMNS = [
    "source_influencer", "total_following", "f_user_order", 
    "ig_user", "username", "full_name", "scraped_at"
]

# --- 2. 官方推薦：自定義速率控制器 ---
class SafeRateController(instaloader.RateController):
    def sleep(self, secs):
        # 額外增加 15-25% 的隨機時間，稀釋自動化特徵
        extra_buffer = secs * random.uniform(0.15, 0.25)
        total_sleep = secs + extra_buffer
        print(f"\n   [⚖️ 內部控管] 接近速率限制，建議休眠 {secs:.1f}s，實際執行 {total_sleep:.1f}s...")
        super().sleep(total_sleep)

    def query_waittime(self, query_type, current_time, untracked_queries=False):
        # 墊高基礎延遲時間
        base_time = super().query_waittime(query_type, current_time, untracked_queries)
        return base_time + random.uniform(10, 20)

# --- 3. 穩健性檢查功能 ---
def check_instagram_in_browser():
    """確保執行時未開啟瀏覽器 IG，避免速率計數器失準"""
    all_windows = gw.getAllTitles()
    ig_windows = [t for t in all_windows if "instagram" in t.lower()]
    if ig_windows:
        print(f"\n⚠ 警示：偵測到瀏覽器視窗：{ig_windows}。")
        print("為保護帳號並確保 RateController 準確性，請關閉瀏覽器分頁後再執行。")
        sys.exit()

def trigger_human_noise(L, session_user):
    """擬人化雜訊觸發，不寫入檔案"""
    noise_types = ["SELF_CHECK", "CELEBRITY_CHECK", "LONG_READ"]
    choice = random.choice(noise_types)
    print(f"\n   [🤖 擬人化雜訊觸發] >>> ", end="")
    try:
        if choice == "SELF_CHECK":
            print(f"模擬查看自己 (@{session_user}) 的 Profile...")
            instaloader.Profile.from_username(L.context, session_user)
        elif choice == "CELEBRITY_CHECK":
            target = random.choice(["instagram", "cristiano", "natgeo"])
            print(f"隨機瀏覽大帳號 (@{target})...")
            instaloader.Profile.from_username(L.context, target)
        elif choice == "LONG_READ":
            wait = random.uniform(60, 100)
            print(f"模擬閱讀貼文內容，停留 {wait:.1f} 秒...")
            time.sleep(wait)
    except:
        pass
    print("   [雜訊結束]\n")

def write_log(start_time, username, count, status, error="N/A"):
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"時間: {start_time} | 目標: @{username} | 成功: {count} | 狀態: {status} | 備註: {error}\n")

# --- 4. 主執行邏輯 ---
def main_scraper():
    check_instagram_in_browser() # 啟動前置檢查

    try:
        df_targets = pd.read_csv(INPUT_CSV)
        target_list = df_targets['ig_id'].tolist()
        print(f"成功載入名單，共 {len(target_list)} 位網紅。")
    except Exception as e:
        print(f"讀取檔失敗: {e}"); return

    # 初始化 Instaloader 並帶入自定義控制器
    L = instaloader.Instaloader(
        rate_controller=lambda ctx: SafeRateController(ctx),
        max_connection_attempts=5
    )
    
    # 設備指紋偽裝 (Mobile Headers)
    L.context._session.headers.update({
        'User-Agent': 'Instagram 219.0.0.12.117 Android (29/10; 420dpi; 1080x1920; samsung; SM-G960F; starlte; exynos9810; en_US; 340011804)'
    })

    try:
        L.load_session_from_file(SESSION_USER)
        print(f"成功載入 Session: {SESSION_USER}")
    except FileNotFoundError:
        print("請先執行 instaloader --login 生成 session。"); return

    done_users = set()
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            done_users = set(f.read().splitlines())

    for target in target_list:
        target = str(target).strip()
        if target in done_users: continue
        
        # 動態生成檔案名稱
        target_output = os.path.join(OUTPUT_DIR, f"{target}-Following-{datetime.now().strftime('%Y%m%d-%H-%M')}.csv")
        start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 20% 機率觸發雜訊
        if random.random() < 0.20:
            trigger_human_noise(L, SESSION_USER)

        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 正式請求: @{target}")
            profile = instaloader.Profile.from_username(L.context, target)
            
            if profile.is_private:
                print(f"跳過：@{target} 為私人帳號。")
                with open(CHECKPOINT_FILE, "a") as f: f.write(target + "\n")
                continue

            with open(target_output, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                
                order = 1
                for followee in profile.get_followees():
                    writer.writerow({
                        "source_influencer": target,
                        "total_following": profile.followees,
                        "f_user_order": order,
                        "ig_user": followee.userid,
                        "username": followee.username,
                        "full_namee": followee.full_name,
                        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    if order % 100 == 0:
                        f.flush()
                        delay = random.uniform(30, 60)
                        print(f"  - 已抓取 {order} 人，冷卻休眠 {delay:.1f} 秒...")
                        time.sleep(delay)
                    order += 1

            with open(CHECKPOINT_FILE, "a") as f: f.write(target + "\n")
            write_log(start_time_str, target, order-1, "成功")
            
            # 成功抓取完一個網紅後的「大冷卻」
            deep_wait = random.uniform(600, 1200) # 10-20 分鐘
            print(f">>> @{target} 完成，深度休眠 {deep_wait/60:.1f} 分鐘...")
            time.sleep(deep_wait)

        except Exception as e:
            if "429" in str(e):
                print(f"\n× 觸發 429 速率限制。請更換手機 IP 並等待至少 2 小時。")
                break
            print(f"× 異常: {e}"); time.sleep(120)

if __name__ == "__main__":
    main_scraper()