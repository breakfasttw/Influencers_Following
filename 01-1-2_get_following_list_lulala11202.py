import instaloader
import pandas as pd
import time
import random
import os
import csv
import sys
import pygetwindow as gw
from datetime import datetime
from dotenv import load_dotenv

# 1. 初始化與環境設定
load_dotenv()
# 請在 .env 中將 SESSION_USER 更新為你的老帳號名稱
SESSION_USER = os.getenv("SESSION_USER2")  # lulala11202
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
# --- 2. User-Agent 隨機池：針對主機黑歷史進行設備偽裝 ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Instagram 219.0.0.12.117 Android (29/10; 420dpi; 1080x1920; samsung; SM-G960F; starlte; exynos9810; en_US; 340011804)"
]

# --- 3. 官方推薦：自定義速率控制器 (針對 429 強化) ---
class SafeRateController(instaloader.RateController):
    def sleep(self, secs):
        # 老帳號雖然耐操，但因主機被封過，我們主動增加 30% 隨機緩衝
        total_sleep = secs + (secs * random.uniform(0.3, 0.5))
        print(f"\n   [⚖️ 內部控管] 檢測到高頻風險，建議休眠 {secs:.1f}s，實際執行 {total_sleep:.1f}s...")
        super().sleep(total_sleep)

    def query_waittime(self, query_type, current_time, untracked_queries=False):
        # 墊高基礎延遲，使行為更像人類
        base_time = super().query_waittime(query_type, current_time, untracked_queries)
        return base_time + random.uniform(15, 35)

# --- 4. 穩健性檢查功能 ---
def check_environment():
    """確認瀏覽器未開啟且 IP 已切換"""
    all_windows = gw.getAllTitles()
    if any("instagram" in t.lower() for t in all_windows):
        print("\n⚠ 偵測到瀏覽器開啟 IG，請關閉後再執行，以免與 RateController 衝突。")
        sys.exit()

def trigger_human_noise(L, session_user):
    """擬人化行為雜訊"""
    choice = random.choice(["SELF", "CELEB", "READ"])
    print(f"\n   [🤖 擬人雜訊] >>> ", end="")
    try:
        if choice == "SELF":
            print(f"查看自己 (@{session_user})..."); instaloader.Profile.from_username(L.context, session_user)
        elif choice == "CELEB":
            celeb = random.choice(["instagram", "natgeo", "cristiano"])
            print(f"瀏覽大帳號 (@{celeb})..."); instaloader.Profile.from_username(L.context, celeb)
        elif choice == "READ":
            wait = random.uniform(45, 90)
            print(f"模擬頁面停留閱讀 {wait:.1f} 秒..."); time.sleep(wait)
    except: pass
    print("   [雜訊結束]\n")

# --- 5. 主執行邏輯 ---
def main():
    check_environment() # 啟動前置環境檢查

    try:
        df_targets = pd.read_csv(INPUT_CSV)
        target_list = df_targets['ig_id'].tolist()
    except Exception as e: print(f"讀取 CSV 失敗: {e}"); return

    # 實例化 Instaloader 並注入自定義控制器
    L = instaloader.Instaloader(
        rate_controller=lambda ctx: SafeRateController(ctx),
        max_connection_attempts=10
    )
    
    # 隨機選擇 User-Agent 偽裝
    chosen_ua = random.choice(USER_AGENTS)
    L.context._session.headers.update({'User-Agent': chosen_ua})
    print(f"√ 已選定設備指紋: {chosen_ua[:50]}...")

    try:
        L.load_session_from_file(SESSION_USER)
        print(f"√ 成功載入老帳號 Session: {SESSION_USER}")
    except: print(f"× 找不到 Session 檔案。請先手動執行 instaloader --login {SESSION_USER}"); return

    done_users = set()
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f: done_users = set(f.read().splitlines())

    for target in target_list:
        target = str(target).strip()
        if target in done_users: continue
        
        # 10% 機率觸發雜訊 (老帳號雜訊不宜過多，以免消耗額度)
        if random.random() < 0.10: trigger_human_noise(L, SESSION_USER)

        # 動態生成檔名
        target_output = os.path.join(OUTPUT_DIR, f"{target}-Following-{datetime.now().strftime('%Y%m%d-%H-%M')}.csv")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 抓取目標: @{target}...", end=" ", flush=True)
        
        try:
            profile = instaloader.Profile.from_username(L.context, target)
            if profile.is_private:
                print("跳過 (私密)"); open(CHECKPOINT_FILE, "a").write(target + "\n"); continue

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
                    if order % 49 == 0:
                        f.flush(); delay = random.uniform(40, 70)
                        print(f"  - 抓取 {order} 人，冷卻 {delay:.1f}s..."); time.sleep(delay)
                    order += 1

            open(CHECKPOINT_FILE, "a").write(target + "\n")
            print(f"√ 成功 ({order-1} 筆)")
            
            # 成功抓取一個網紅後的長休息
            long_wait = random.uniform(900, 1800) # 15-30 分鐘，對於老帳號與被標記主機是必要的
            print(f">>> 深度休眠 {long_wait/60:.1f} 分鐘後處理下一位...")
            time.sleep(long_wait)

        except Exception as e:
            if "429" in str(e):
                print(f"\n× 觸發速率限制 (429)。老帳號風險警報，請立即切換 IP 並停機 2 小時。")
                break
            print(f"× 錯誤: {e}"); time.sleep(120)

if __name__ == "__main__":
    main()