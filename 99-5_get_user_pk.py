import requests
import re
import pandas as pd
import time
import random
import os

# === 配置區 ===
COOKIES = os.getenv("ig_ck")
INPUT_CSV = "influencer_list.csv" # 包含 username 欄位
OUTPUT_CSV = "influencer_results.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "cookie": COOKIES,
    "X-IG-App-ID": "936619743392459", # 這是 IG 網頁版的專屬 ID，必須填寫
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.instagram.com/",
}

def get_ig_id_v2(username):
    # 改用官方 Web API 端點
    api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    
    try:
        response = requests.get(api_url, headers=HEADERS, timeout=10)
        
        # 如果噴 403/404，代表 Cookie 過期或被擋
        if response.status_code == 200:
            data = response.json()
            # 資料結構在 data -> data -> user -> id
            user_id = data.get('data', {}).get('user', {}).get('id')
            if user_id:
                return user_id
            else:
                print(f"[-] {username}: JSON 中找不到 ID 欄位")
        else:
            print(f"[-] {username}: API 請求失敗，狀態碼: {response.status_code}")
            
    except Exception as e:
        print(f"[-] {username}: 發生錯誤: {e}")
    
    return None

def main():
    # 讀取 CSV
    try:
        df = pd.read_csv(INPUT_CSV)
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {INPUT_CSV}")
        return

    ids = []
    for i, row in df.iterrows():
        username = row['username']
        print(f"[{i+1}/{len(df)}] 查詢中: {username}...", end="\r")
        
        user_id = get_ig_id_v2(username)
        ids.append(user_id)
        
        # 為了保護你的小帳，請務必維持延遲
        time.sleep(random.uniform(60, 120))
        
    # 寫回 CSV
    df['ig_strong_id'] = ids
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"\n查詢結束！成功取得的 ID 數量: {df['ig_strong_id'].notnull().sum()}")

if __name__ == "__main__":
    main()