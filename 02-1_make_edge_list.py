import pandas as pd
import os
import re

# ==========================================
# 1. 參數設定
# ==========================================
MASTER_LIST_PATH = 'Top200_ig_20260126.csv'
INPUT_DIR = 'ignore/following_list'
OUTPUT_DIR = 'Output'
OUTPUT_FILENAME = 'username_edge_list.csv'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def solve_phase_1():
    # ==========================================
    # 2. 讀取母體名單並建立映射 (Mapping)
    # ==========================================
    if not os.path.exists(MASTER_LIST_PATH):
        print(f"錯誤：找不到檔案 {MASTER_LIST_PATH}")
        return

    # 讀取檔案
    master_df = pd.read_csv(MASTER_LIST_PATH)
    
    # [關鍵防錯]：去除欄位名稱的前後空格 (例如將 "ig_id " 轉為 "ig_id")
    master_df.columns = master_df.columns.str.strip()
    
    # 檢查必要欄位是否存在
    required_cols = ['person_name', 'ig_id']
    for col in required_cols:
        if col not in master_df.columns:
            print(f"錯誤：母體檔案中找不到 '{col}' 欄位。目前的欄位有: {master_df.columns.tolist()}")
            return

    # [關鍵清理]：
    # 1. 將 ig_id 內容去空格並轉小寫
    # 2. 將 person_name 空格換成 "-"
    master_df['clean_ig_id'] = master_df['ig_id'].astype(str).str.strip().str.lower()
    master_df['clean_person_name'] = master_df['person_name'].astype(str).str.replace(' ', '-', regex=False)
    
    # 建立映射表：{ '帳號': '清理後的姓名' }
    id_to_person_map = dict(zip(master_df['clean_ig_id'], master_df['clean_person_name']))
    valid_ids = set(id_to_person_map.keys())

    # ==========================================
    # 3. 掃描 Following 資料夾
    # ==========================================
    all_edges = []
    
    if not os.path.exists(INPUT_DIR):
        print(f"錯誤：找不到資料夾 {INPUT_DIR}")
        return

    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.csv')]
    print(f"預計處理 {len(files)} 個檔案...")

    for filename in files:
        # 提取檔名第一個橫槓前的字串作為 source_id
        source_id = filename.split('-')[0].strip().lower()
        
        # 驗證此帳號是否在母體內
        if source_id not in valid_ids:
            # 除錯資訊：如果還是失敗，印出此 ID 讓使用者確認
            print(f"跳過：{filename} (提取到的 ID '{source_id}' 不在母體清單中)")
            continue
            
        source_name = id_to_person_map[source_id]
        
        try:
            # 讀取該網紅追蹤的人，只取 username 欄位
            following_df = pd.read_csv(os.path.join(INPUT_DIR, filename), usecols=['username'])
            
            # 清理追蹤清單中的帳號
            following_df['username'] = following_df['username'].astype(str).str.strip().str.lower()
            
            # 過濾：只保留追蹤對象也在母體名單內的紀錄 (圈內互動)
            in_circle = following_df[following_df['username'].isin(valid_ids)].copy()
            
            for target_id in in_circle['username']:
                target_name = id_to_person_map[target_id]
                
                # 排除自己追蹤自己（若有分帳則會保留）
                if source_name != target_name:
                    all_edges.append({
                        'source': source_name,
                        'target': target_name
                    })
                    
        except Exception as e:
            print(f"讀取檔案 {filename} 時發生錯誤: {e}")

    # ==========================================
    # 4. 去重並產出 CSV
    # ==========================================
    edge_df = pd.DataFrame(all_edges).drop_duplicates() # 處理多個小帳追蹤同一主帳
    
    save_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    edge_df.to_csv(save_path, index=False, encoding='utf-8-sig')
    
    print("-" * 30)
    print(f"執行完畢！")
    print(f"成功處理的檔案數: {len(files)}")
    print(f"產生的關係總數 (Edge count): {len(edge_df)}")
    print(f"結果已存至: {save_path}")

if __name__ == "__main__":
    solve_phase_1()