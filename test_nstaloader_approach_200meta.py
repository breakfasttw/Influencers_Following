# 請求過程中，加入人為雜訊(開自己的帳號、閱讀別人帳號等)的腳本
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
OUTPUT_FILE = "person_meta_baseline.csv"
CHECKPOINT_FILE = "meta_finished.txt"

CSV_COLUMNS = ["ig_id", "strong_id__", "post_count", "follower_count", "following_count", "is_private", "scraped_at"]

def trigger_human_noise(L, session_user):
    """
    隨機觸發擬人化行為，僅在終端機列印，不影響資料寫入。
    """
    # 模擬人類行為：1.看自己的Profile, 2.看一個超級大帳號, 3.模擬長時間閱讀(長休眠)
    noise_types = ["SELF_CHECK", "CELEBRITY_CHECK", "LONG_READ"]
    choice = random.choice(noise_types)
    
    print(f"\n   [🤖 擬人化雜訊觸發] >>> ", end="")
    
    try:
        if choice == "SELF_CHECK":
            print(f"正在模擬『查看自己 (@{session_user}) 的個人檔案』...")
            instaloader.Profile.from_username(L.context, session_user)
            time.sleep(random.uniform(5, 10))
            
        elif choice == "CELEBRITY_CHECK":
            celebs = ["instagram", "cristiano", "leomessi", "natgeo"]
            target_celeb = random.choice(celebs)
            print(f"正在模擬『隨機瀏覽大帳號 (@{target_celeb})』...")
            instaloader.Profile.from_username(L.context, target_celeb)
            time.sleep(random.uniform(21, 33))
            
        elif choice == "LONG_READ":
            wait = random.uniform(62, 94)
            print(f"正在模擬『假裝停留在頁面閱讀內容』，預計停留 {wait:.1f} 秒...")
            time.sleep(wait)
            
    except Exception:
        print("雜訊執行微故障 (通常是網路波動)，略過...")
    print(f"   [雜訊結束，準備執行下一個正式目標]\n")

def fetch_metadata_master():
    # 2. 載入名單與檢查進度
    try:
        df_targets = pd.read_csv(INPUT_FILE)
        target_list = df_targets['ig_id'].tolist()
        done_users = set()
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, "r") as f:
                done_users = set(f.read().splitlines())
    except Exception as e:
        print(f"初始化失敗: {e}"); return

    # 3. 初始化輸出檔案 (Append 模式)
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=CSV_COLUMNS).writeheader()

    L = instaloader.Instaloader()
    L.load_session_from_file(SESSION_USER) #

    # 4. 主迴圈：遍歷 200 位網紅
    for index, target in enumerate(target_list, 1):
        target = str(target).strip()
        if target in done_users: continue
        
        # --- 隨機雜訊觸發邏輯 ---
        # 每處理一個網紅前，有 20% 的機率觸發雜訊行為
        if random.random() < 0.25:
            trigger_human_noise(L, SESSION_USER)

        print(f"[{index}/{len(target_list)}] 正式抓取目標: @{target}...", end=" ", flush=True)
        
        try:
            profile = instaloader.Profile.from_username(L.context, target)
            
            # 準備數據並寫入 CSV
            row = {
                "ig_id": target,
                "strong_id__": profile.userid,
                "post_count": profile.mediacount,
                "follower_count": profile.followers,
                "following_count": profile.followees,
                "is_private": profile.is_private,
                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            with open(OUTPUT_FILE, "a", newline="", encoding="utf-8-sig") as f:
                csv.DictWriter(f, fieldnames=CSV_COLUMNS).writerow(row)
                f.flush()

            with open(CHECKPOINT_FILE, "a") as f:
                f.write(target + "\n")
            
            print(f"√ 成功")
            
            # --- 極保守休息策略 ---
            # 每成功一位，強制休息
            small_wait = random.uniform(61, 80)
            print(f"   - 休息 {small_wait:.1f} 秒...")
            time.sleep(small_wait)

            # 每成功 3 位，進入深度大休息
            if index % 3 == 0:
                deep_wait = random.uniform(300, 480) 
                print(f"\n[!] 已處理 3 人，為保護帳號進入『深度冷卻』: {deep_wait/60:.1f} 分鐘...")
                time.sleep(deep_wait)

        except Exception as e:
            if "401" in str(e):
                print(f"\n× 嚴重封鎖 (401)。請務必切換手機飛航模式獲取新 IP 後再重試。")
                break
            print(f"× 錯誤: {e}"); time.sleep(60)

if __name__ == "__main__":
    fetch_metadata_master()