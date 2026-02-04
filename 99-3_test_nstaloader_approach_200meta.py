# 請求過程中，加入人為雜訊(開自己的帳號、閱讀別人帳號等)的腳本
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

# 1. 初始化與環境設定
load_dotenv()
SESSION_USER = os.getenv("SESSION_USER2")
INPUT_FILE = "Top200_ig_20260126.csv"
OUTPUT_FILE = "person_meta_baseline.csv"
CHECKPOINT_FILE = "meta_finished.txt"

CSV_COLUMNS = ["ig_id", "strong_id__", "post_count", "follower_count", "following_count", "is_private", "scraped_at"]

def check_instagram_in_browser():
    """檢查是否有任何視窗標題包含 Instagram，避免 429 衝突"""
    print("正在進行環境安全性檢查...")
    all_windows = gw.getAllTitles()
    # 檢查所有視窗標題中是否含有 'Instagram' (不限大小寫)
    ig_windows = [t for t in all_windows if "instagram" in t.lower()]
    
    if ig_windows:
        print("\n" + "!"*50)
        print("⚠ 警示：偵測到瀏覽器可能正開啟 Instagram！")
        print(f"偵測到的視窗：{ig_windows}")
        print("為了避免觸發 429 Too Many Requests，程式已終止。")
        print("請關閉所有 Instagram 分頁後再重新執行。")
        print("!"*50 + "\n")
        sys.exit() # 強制退出程式
    else:
        print("√ 環境檢查通過：未偵測到 Instagram 瀏覽器視窗。")

def trigger_human_noise(L, session_user):
    # (此部分邏輯維持不變，包含擬人化雜訊)
    noise_types = ["SELF_CHECK", "CELEBRITY_CHECK", "LONG_READ"]
    choice = random.choice(noise_types)
    print(f"\n   [🤖 擬人化雜訊觸發] >>> ", end="")
    try:
        if choice == "SELF_CHECK":
            print(f"正在模擬『查看自己 (@{session_user}) 的個人檔案』...")
            instaloader.Profile.from_username(L.context, session_user)
            time.sleep(random.uniform(16, 33))
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
        print("雜訊執行微故障，略過...")
    print(f"   [雜訊結束，準備執行下一個正式目標]\n")

def fetch_metadata_master():
    # 在啟動前執行瀏覽器檢查
    check_instagram_in_browser()

    try:
        df_targets = pd.read_csv(INPUT_FILE)
        target_list = df_targets['ig_id'].tolist()
        done_users = set()
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, "r") as f:
                done_users = set(f.read().splitlines())
    except Exception as e:
        print(f"初始化失敗: {e}"); return

    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=CSV_COLUMNS).writeheader()

    L = instaloader.Instaloader()
    L.load_session_from_file(SESSION_USER)

    for index, target in enumerate(target_list, 1):
        target = str(target).strip()
        if target in done_users: continue
        
        if random.random() < 0.25:
            trigger_human_noise(L, SESSION_USER)

        print(f"[{index}/{len(target_list)}] 正式抓取目標: @{target}...", end=" ", flush=True)
        
        try:
            profile = instaloader.Profile.from_username(L.context, target)
            row = {
                "ig_id": target, "strong_id__": profile.userid,
                "post_count": profile.mediacount, "follower_count": profile.followers,
                "following_count": profile.followees, "is_private": profile.is_private,
                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(OUTPUT_FILE, "a", newline="", encoding="utf-8-sig") as f:
                csv.DictWriter(f, fieldnames=CSV_COLUMNS).writerow(row)
                f.flush()
            with open(CHECKPOINT_FILE, "a") as f:
                f.write(target + "\n")
            print(f"√ 成功")
            
            small_wait = random.uniform(61, 80)
            print(f"   - 休息 {small_wait:.1f} 秒...")
            time.sleep(small_wait)

            if index % 3 == 0:
                deep_wait = random.uniform(300, 480) 
                print(f"\n[!] 已處理 3 人，進入『深度冷卻』: {deep_wait/60:.1f} 分鐘...")
                time.sleep(deep_wait)

        except Exception as e:
            if "429" in str(e) or "401" in str(e):
                print(f"\n× 觸發速率限制或封鎖 ({e})。請務必切換飛航模式獲取新 IP 並關閉所有瀏覽器後再重試。")
                break
            print(f"× 錯誤: {e}"); time.sleep(60)

if __name__ == "__main__":
    fetch_metadata_master()