import json
import os
import pandas as pd
from datetime import datetime

# ================= 配置區域 =================
# 1. 手動輸入要轉換的 username_list 
username_list = ['xiucao.han', 'three_muggles', 'uni_catto', 'emmy_on_earth', 'logandbeck', '1_shiuan_0', 'japanuts', 'campfire_tw', 'blairechen', 'mengj215', 'itsberrym', 'afunnywii', 'huzihuang1989', 'tinana_master', 'weisway18', 'neneko.n', 'wia627', 'jam_steak', 'getwie__', 'wufeili', 'zxsdexz', 'kellyshen40', 'mypink0911', 'oldwangstock', 'walkerdad1228', 'boyplaymj', 'b2btramy888888', 'cindyhhh32', 'mr.joehobby', 'sunnie_cat0111', 'goris.sky', 'byleway', 'nowyouon', 'momanddad_band', 'maygobla', 'kai_makeup_', 'ninggoose', 'anjouclever', 'linzin.yt', 'thechef_fred', 'hsin0126']

# 2. 路徑設定 (使用 raw string 避免斜線轉義問題)
input_dir = r"ignore\graphQL"
output_dir = r"ignore\following_list\graphQL"

# ================= 執行邏輯 =================

def convert_json_to_csv(username_list, input_dir, output_dir):
    for username in username_list:
        print(f"正在執行 {username}")
        input_path = os.path.join(input_dir, f"{username}.json")
        
        # 檢查輸入檔案是否存在
        if not os.path.exists(input_path):
            print(f"❌ 找不到檔案：{input_path}")
            continue

        # 讀取 JSON 資料
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 建立輸出目錄
        os.makedirs(output_dir, exist_ok=True)

        # 處理時間戳記
        timestamp = datetime.now().strftime("%Y%m%d-%H-%M")
        output_filename = f"{username}-Following-{timestamp}_g.csv"
        output_path = os.path.join(output_dir, output_filename)

        # 解析資料
        parsed_list = []
        for index, item in enumerate(data, start=1):
            parsed_list.append({
                "number": index,
                "ig_user_id": item.get("strong_id__"),
                "full_name": item.get("full_name"),
                "username": item.get("username"),
                "is_verified": item.get("is_verified"),
                "is_private": item.get("is_private")
            })

        # 轉為 DataFrame 並儲存
        df = pd.DataFrame(parsed_list)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")

        print(f"✅ 轉換成功！")
        print(f"📊 總筆數：{len(df)}")
        print(f"📁 檔案存於：{output_path}")
    
    print(f"✅ 全部轉換完成，共轉了 {len(username_list)} 筆")

if __name__ == "__main__":
    convert_json_to_csv(username_list, input_dir, output_dir)