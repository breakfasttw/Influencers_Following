import json
import base64
import pandas as pd
from datetime import datetime

def extract_following_from_har(file_path, influencer_name):
    with open(file_path, 'r', encoding='utf-8') as f:
        har_data = json.load(f)

    all_users = []
    
    for entry in har_data['log']['entries']:
        url = entry['request']['url']
        
        # 篩選 Following API 請求
        if '/friendships/' in url and '/following/' in url:
            content = entry['response']['content']
            if 'text' in content:
                raw_text = content['text']
                
                # 處理 Base64 編碼或是原始 JSON
                try:
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
        print("找不到任何資料，請確認 HAR 檔案是否正確匯出。")
        return

    # 轉換成 DataFrame 並去重 (以 pk 為準)
    df = pd.DataFrame(all_users)
    df = df.drop_duplicates(subset=['pk'])
    
    # 整理格式
    result = pd.DataFrame({
        "source_influencer": influencer_name,
        "total_following": len(df),
        "username": df['username'],
        "ig_user_id": df['pk'],
        "full_name": df['full_name'],
        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    timestamp = datetime.now().strftime("%Y%m%d-%H-%M")
    output_filename = f"{influencer_name}-Following-{timestamp}_m.csv"
    result.to_csv(output_filename, index=False, encoding="utf-8-sig")
    print(f"✅ 提取成功！已從 HAR 檔中產出 {len(result)} 筆資料至 {output_filename}")

# 使用方式：請輸入你剛才手動滾動的網紅 ig_id
extract_following_from_har("www.instagram.com.har", "thedodomen")