# 產出：可開始分析的個人追蹤清單
# input = 網頁下載的 har 檔案

import json
import base64
import os
import pandas as pd
from datetime import datetime

# 1. 設定輸出路徑與環境

influencer_name = "test_hook" # ⭐⭐ 改這
input_dir = r"D:\Code\Task\Influencers_Following\ignore\har"
input_filename = f"{influencer_name}.har"
input_path = os.path.join(input_dir, input_filename) 


def process_manual_har_to_csv_fixed(har_file_path, influencer_name):
    print(f"開始執行轉換.....")
    
    output_dir = "ignore/following_list/manual"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d-%H-%M")
    output_filename = f"{influencer_name}-Following-{timestamp}_m.csv"
    output_path = os.path.join(output_dir, output_filename)

    with open(har_file_path, 'r', encoding='utf-8') as f:
        har_data = json.load(f)

    all_users = []
    
    for entry in har_data['log']['entries']:
        url = entry['request']['url']
        if '/friendships/' in url and '/following/' in url:
            content = entry['response']['content']
            if 'text' in content:
                raw_text = content['text']
                try:
                    # 處理 Base64 或原始 JSON
                    if content.get('encoding') == 'base64':
                        decoded_text = base64.b64decode(raw_text).decode('utf-8')
                        data = json.loads(decoded_text)
                    else:
                        data = json.loads(raw_text)
                    
                    if 'users' in data:
                        all_users.extend(data['users'])
                except Exception as e:
                    print(f"解析單筆請求失敗: {e}")

    if not all_users:
        print("❌ 找不到資料。")
        return

    # 轉為 DataFrame
    raw_df = pd.DataFrame(all_users)
    
    # 關鍵修正：去重後立即重設索引 (Reset Index)
    clean_df = raw_df.drop_duplicates(subset=['pk']).reset_index(drop=True)
    
    # 建立最終結果
    result_df = pd.DataFrame()
    result_df['number'] = range(1, len(clean_df) + 1)
    result_df['ig_user_id'] = clean_df['pk']
    result_df['full_name'] = clean_df['full_name']
    result_df['username'] = clean_df['username']
    result_df['is_verified'] = clean_df['is_verified']
    result_df['total_following'] = len(clean_df)

    result_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ 轉換成功。")
    print(f"📊 獨特追蹤人數: {len(result_df)} (原始抓取人數: {len(raw_df)})")
    print(f"📁 檔案存於: {output_path}")

# 執行
process_manual_har_to_csv_fixed(input_path, influencer_name)