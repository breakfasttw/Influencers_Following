# 抓取200名網紅的純 meta (貼文數、粉絲數、追蹤數)
import instaloader
import pandas as pd
import time
import random
import os
import csv
from datetime import datetime
from dotenv import load_dotenv

# 1. 初始化與環境設定
load_dotenv()
SESSION_USER = os.getenv("SESSION_USER") # morning_ana2026
INPUT_FILE = "Top200_ig_20260126.csv"
OUTPUT_FILE = "person_meta_baseline.csv" # 建議固定檔名以便續傳
CHECKPOINT_FILE = "meta_finished.txt"

# CSV 欄位定義
CSV_COLUMNS = [
    "ig_id", "strong_id__", "post_count", "follower_count", 
    "following_count", "is_private", "scraped_at"
]

def fetch_metadata_with_checkpoint():
    # 2. 載入名單與檢查進度
    try:
        df_targets = pd.read_csv(INPUT_FILE)
        target_list = df_targets['ig_id'].tolist()
        
        done_users = set()
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, "r") as f:
                done_users = set(f.read().splitlines())
        
        print(f"名單總數: {len(target_list)}，已完成: {len(done_users)}，剩餘: {len(target_list) - len(done_users)}")
    except Exception as e:
        print(f"初始化失敗: {e}")
        return

    # 3. 初始化輸出檔案 (若不存在則寫入標頭)
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()

    # 4. 初始化 Instaloader
    L = instaloader.Instaloader()
    try:
        L.load_session_from_file(SESSION_USER)
    except Exception as e:
        print(f"Session 載入失敗: {e}")
        return

    # 5. 主迴圈
    success_count = 0
    for index, target in enumerate(target_list, 1):
        target = str(target).strip()
        if target in done_users:
            continue
        
        print(f"[{index}/{len(target_list)}] 正在獲取 @{target}...", end=" ", flush=True)
        
        try:
            profile = instaloader.Profile.from_username(L.context, target)
            
            # 準備數據
            row = {
                "ig_id": target,
                "strong_id__": profile.userid,
                "post_count": profile.mediacount,
                "follower_count": profile.followers,
                "following_count": profile.followees,
                "is_private": profile.is_private,
                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # --- 即時寫入 CSV ---
            with open(OUTPUT_FILE, "a", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writerow(row)
                f.flush() # 強制寫入硬碟

            # --- 即時更新斷點 ---
            with open(CHECKPOINT_FILE, "a") as f:
                f.write(target + "\n")
            
            print(f"√ 成功 ({profile.followers} 粉絲)")
            success_count += 1
            
            # --- 分層休息邏輯 (更加保守版) ---
            if index % 10 == 0:
                # 每 10 人大休息
                wait = random.uniform(85, 143)
                print(f"   >> 已達 10 人，大休息 {wait:.1f} 秒...")
                time.sleep(wait)
            else:
                # 每人小休息
                wait = random.uniform(61, 80)
                print(f"   >> 小休息 {wait:.1f} 秒...")
                time.sleep(wait)

        except Exception as e:
            if "401" in str(e):
                print(f"\n× 觸發限制 (401)。程式將自動停止。請更換 IP 或等待 1 小時後再跑。")
                break
            else:
                print(f"× 跳過 @{target}: {e}")
                time.sleep(45) # 遇到非 401 錯誤也多等一下

    print(f"\n本次執行完畢，成功抓取 {success_count} 筆。")

if __name__ == "__main__":
    fetch_metadata_with_checkpoint()

print('執行完成')