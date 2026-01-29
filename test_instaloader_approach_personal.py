# 最低限度測試抓取 meta data，不抓取迭帶清單

import instaloader
import os
from dotenv import load_dotenv
from datetime import datetime

# 載入環境變數
load_dotenv()
SESSION_USER = os.getenv("SESSION_USER") # 預期為 morning_ana2026

def run_low_risk_test():
    L = instaloader.Instaloader()
    
    # 1. 嘗試載入 Session
    try:
        L.load_session_from_file(SESSION_USER)
        print(f"[{datetime.now()}] √ 成功載入 Session 檔案: {SESSION_USER}")
    except FileNotFoundError:
        print(f"× 錯誤：找不到 Session 檔案，請確認 .env 設定與路徑。")
        return

    try:
        # 2. 測試 A：存取「自己」的帳號 (風險最低)
        print(f"\n--- 測試 A：存取帳號本身資訊 ---")
        my_profile = instaloader.Profile.from_username(L.context, SESSION_USER)
        print(f"帳號 ID: {my_profile.userid}")
        print(f"目前貼文數: {my_profile.mediacount}")
        print(f"目前關注中人數: {my_profile.followees}")
        print(f"√ 狀態：可以成功讀取自身帳號資料。")

        # 3. 測試 B：存取單一網紅的「公開後設資料」 (不讀取清單)
        # 以你名單中的第一個網紅為例
        test_target = "yga0721" 
        print(f"\n--- 測試 B：存取公開網紅後設資料 (@{test_target}) ---")
        
        target_profile = instaloader.Profile.from_username(L.context, test_target)
        print(f"目標 ID: {target_profile.userid}")
        print(f"目標簡介: {target_profile.biography[:20]}...")
        print(f"目標粉絲數: {target_profile.followers}")
        print(f"√ 狀態：成功讀取公開帳號基礎資訊。")
        
        print(f"\n{'='*30}")
        print("恭喜！你的 Session 目前運作正常，且帳號權限已放行基本查詢。")
        print("{'='*30}")

    except Exception as e:
        print(f"\n× 測試中斷：{str(e)}")
        if "401" in str(e):
            print("提示：Session 可能已過期，或 IP 仍被標記中。")

if __name__ == "__main__":
    run_low_risk_test()