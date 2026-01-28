import instaloader
from instaloader.exceptions import ConnectionException, BadResponseException
import time
import random
import os
import csv
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# --- 設定區 ---
INPUT_CSV = "Top200_ig_20260126.csv"   # 輸入名單
SESSION_USER = os.getenv("SESSION_USER")      # IG 帳號名稱
timestamp_suffix = datetime.now().strftime("%Y%m%d%H%M")
OUTPUT_FILE = f"ig_network_analysis_{timestamp_suffix}.csv"
CHECKPOINT_FILE = "finished_list.txt"
LOG_FILE = "scraper_log.txt"

# CSV 欄位定義
CSV_COLUMNS = [
    "source_influencer", "total_following", "f_user_order", 
    "f_user_serial", "f_user_id", "f_user_name", "scraped_at"
]

def write_log(start_time, username, count, status, error="N/A"):
    """記錄執行日誌到文字檔"""
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        log_content = (
            f"起始時間: {start_time}\n"
            f"正在爬取: @{username}\n"
            f"成功人數: {count}\n"
            f"狀態: {status}\n"
            f"失敗原因/備註: {error}\n"
            f"結束時間: {end_time}\n\n"
        )
        f.write(log_content)

def main_scraper():
    # 1. 讀取網紅名單
    try:
        df_targets = pd.read_csv(INPUT_CSV)
        target_list = df_targets['ig_id'].tolist()
        print(f"成功載入名單，共 {len(target_list)} 位網紅。")
    except Exception as e:
        print(f"無法讀取輸入檔 {INPUT_CSV}: {e}")
        return

    # 2. 初始化 Instaloader
    L = instaloader.Instaloader()
    try:
        L.load_session_from_file(SESSION_USER)
        print(f"成功載入 Session: {SESSION_USER}")
    except FileNotFoundError:
        print(f"錯誤：找不到 Session 檔案。請先執行 instaloader --login {SESSION_USER}")
        return

    # 3. 初始化輸出 CSV
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()

    # 4. 檢查已完成進度 (斷點續傳)
    done_users = set()
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            done_users = set(f.read().splitlines())

    # 5. 主迴圈
    for target in target_list:
        target = str(target)
        if target in done_users:
            continue
        
        start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_influencer_data = []
        
        retry_count = 0
        max_retries = 3
        is_success = False

        while retry_count < max_retries:
            try:
                print(f"\n{'='*50}")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 檢查帳號狀態: @{target}")
                
                profile = instaloader.Profile.from_username(L.context, target)
                
                # --- 新增機制：私人帳號跳過判斷 ---
                if profile.is_private:
                    print(f"跳過：@{target} 為私人帳號，無法獲取名單。")
                    write_log(start_time_str, target, 0, "跳過", "此帳號不公開")
                    
                    # 標記為已完成，避免下次重跑
                    with open(CHECKPOINT_FILE, "a") as f:
                        f.write(target + "\n")
                    
                    is_success = False # 設定為 False 以免觸發長休眠
                    break # 跳出 retry 迴圈處理下一個網紅
                
                # --- 若為公開帳號，執行原定抓取邏輯 ---
                total_followees = profile.followees
                print(f"開始抓取公開帳號 (@{target})，總追蹤數: {total_followees}")
                
                with open(OUTPUT_FILE, "a", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                    
                    order = 1
                    for followee in profile.get_followees():
                        row = {
                            "source_influencer": target,
                            "total_following": total_followees,
                            "f_user_order": order,
                            "f_user_serial": followee.userid,
                            "f_user_id": followee.username,
                            "f_user_name": followee.full_name,
                            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        writer.writerow(row)
                        current_influencer_data.append(row)
                        
                        if order % 100 == 0:
                            f.flush()
                            delay = random.uniform(15, 30) # 15-30秒微休眠
                            print(f"  - 已抓取 {order} 人，微休眠 {delay:.1f} 秒...")
                            time.sleep(delay)
                        order += 1

                print(f">>> @{target} 完成，共抓取 {len(current_influencer_data)} 筆。")
                
                # 數據抽查監控
                if len(current_influencer_data) >= 10:
                    print("\n[前 10 筆]")
                    for r in current_influencer_data[:10]:
                        print(f"#{r['f_user_order']} | ID: {r['f_user_id']} | Serial: {r['f_user_serial']}")
                    print("\n[最後 10 筆]")
                    for r in current_influencer_data[-10:]:
                        print(f"#{r['f_user_order']} | ID: {r['f_user_id']} | Serial: {r['f_user_serial']}")

                with open(CHECKPOINT_FILE, "a") as f:
                    f.write(target + "\n")
                
                write_log(start_time_str, target, len(current_influencer_data), "成功")
                is_success = True
                break

            except (ConnectionException, BadResponseException) as e:
                if "401" in str(e) or "Please wait" in str(e):
                    retry_count += 1
                    wait_time = 1800 * retry_count 
                    print(f"⚠ 觸發 IG 限制。強制休眠 {wait_time/60} 分鐘...")
                    write_log(start_time_str, target, len(current_influencer_data), "暫時封鎖", str(e))
                    time.sleep(wait_time)
                else:
                    print(f"× 連線異常: {e}")
                    write_log(start_time_str, target, len(current_influencer_data), "連線異常", str(e))
                    break

            except Exception as e:
                print(f"× 系統異常: {e}")
                write_log(start_time_str, target, len(current_influencer_data), "失敗", str(e))
                break

        # 網紅間的大休息 (僅針對成功抓取完畢者)
        if is_success:
            long_wait = random.uniform(300, 480)
            print(f"\n隨機休眠 {int(long_wait)} 秒後處理下一個網紅...")
            time.sleep(long_wait)
        else:
            # 如果是私密帳號或是失敗跳過，只休眠較短時間便繼續下一位
            time.sleep(5)

if __name__ == "__main__":
    main_scraper()