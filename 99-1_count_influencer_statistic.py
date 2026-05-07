import pandas as pd
import os
import glob
import ast
import numpy as np

def generate_influencer_statistics(inputdir, outputdir):
    """
    讀取 inputdir 下的所有 csv 檔案，統計 2025 年影片數據，並輸出至 outputdir。
    """
    # 建立輸出資料夾（如果不存在）
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)
        
    output_filename = "influencer_videos_statistuc.csv"
    output_path = os.path.join(outputdir, output_filename)
    
    # 搜尋所有 csv 檔案
    csv_files = glob.glob(os.path.join(inputdir, "*.csv"))
    
    results = []
    
    for file_path in csv_files:
        try:
            # 讀取 CSV
            df = pd.read_csv(file_path)
            
            # 1. 轉換時間格式並篩選 2025 年影片
            # 欄位：creation_time_tw (格式如 2025-01-01 00:19:29+08:00)
            df['creation_time_tw'] = pd.to_datetime(df['creation_time_tw'], errors='coerce')
            df_2025 = df[df['creation_time_tw'].dt.year == 2025].copy()
            
            # 如果該網紅在 2025 沒有發布影片，仍需建立一列資料，數值皆為 0
            if df_2025.empty:
                # 嘗試從原始 df 拿 username，若 df 也空則從檔名拿
                ig_name = df['post_owner.username'].iloc[0] if not df.empty else os.path.basename(file_path).split('-')[0]
                results.append({
                    'ig_name': ig_name, 'total_vedios': 0,
                    'total_likes': 0, 'avg_like': 0, 'max_like': 0, 'min_like': 0,
                    'total_comments': 0, 'avg_coments': 0, 'max_comments': 0, 'min_comments': 0,
                    'total_tags': 0, 'avg_tags': 0, 'max_tags': 0, '_min_tags': 0,
                    'total_views': 0, 'avg_views': 0, 'max_views': 0, 'min_views': 0,
                    'total_duration': 0, 'max_duration': 0, 'avg_duration': 0, 'min_duration': 0
                })
                continue

            # 2. 準備 ig_name (取第一個 post_owner.username)
            ig_name = df_2025['post_owner.username'].iloc[0]
            
            # 3. 處理 Tags 統計 (計算字串字典的長度)
            def get_tag_count(tag_str):
                if pd.isna(tag_str) or tag_str == "" or str(tag_str).lower() == 'nan':
                    return 0
                try:
                    # 使用 ast.literal_eval 安全解析字串形式的字典/清單
                    tags = ast.literal_eval(str(tag_str))
                    return len(tags) if isinstance(tags, (dict, list)) else 0
                except:
                    return 0

            df_2025['tag_count'] = df_2025['tags'].apply(get_tag_count)
            
            # 4. 計算各項指標
            stats = {
                'ig_name': ig_name,
                'total_vedios': len(df_2025),
                
                # Likes (statistics.like_count)
                'total_likes': df_2025['statistics.like_count'].sum(),
                'avg_like': df_2025['statistics.like_count'].mean(),
                'max_like': df_2025['statistics.like_count'].max(),
                'min_like': df_2025['statistics.like_count'].min(),
                
                # Comments (statistics.comment_count)
                'total_comments': df_2025['statistics.comment_count'].sum(),
                'avg_coments': df_2025['statistics.comment_count'].mean(),
                'max_comments': df_2025['statistics.comment_count'].max(),
                'min_comments': df_2025['statistics.comment_count'].min(),
                
                # Tags (物件長度)
                'total_tags': df_2025['tag_count'].sum(),
                'avg_tags': df_2025['tag_count'].mean(),
                'max_tags': df_2025['tag_count'].max(),
                '_min_tags': df_2025['tag_count'].min(),
                
                # Views (statistics.views)
                'total_views': df_2025['statistics.views'].sum(),
                'avg_views': df_2025['statistics.views'].mean(),
                'max_views': df_2025['statistics.views'].max(),
                'min_views': df_2025['statistics.views'].min(),
                
                # Duration (duration)
                'total_duration': df_2025['duration'].sum(),
                'max_duration': df_2025['duration'].max(),
                'avg_duration': df_2025['duration'].mean(),
                'min_duration': df_2025['duration'].min(),
            }
            results.append(stats)
            
        except Exception as e:
            print(f"處理檔案 {file_path} 時發生錯誤: {e}")

    # 5. 整合結果並輸出 CSV
    summary_df = pd.DataFrame(results)
    
    # 依照要求排序欄位 (包含指定的拼字如 vedios, coments, _min_tags)
    ordered_cols = [
        'ig_name', 'total_vedios', 
        'total_likes', 'avg_like', 'max_like', 'min_like', 
        'total_comments', 'avg_coments', 'max_comments', 'min_comments', 
        'total_tags', 'avg_tags', 'max_tags', '_min_tags', 
        'total_views', 'avg_views', 'max_views', 'min_views', 
        'total_duration', 'max_duration', 'avg_duration', 'min_duration'
    ]
    
    summary_df = summary_df[ordered_cols]
    summary_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"統計完成！檔案已儲存至: {output_path}")

# --- 設定路徑並執行 ---
input_dir = r"T:\Code\Task\meta_vedio_download\Output\Top200_VideoInfo"  # 更改為你的輸入資料夾路徑
output_dir = r"T:\Code\Task\Influencers_Following\Output"     # 更改為你的輸出資料夾路徑

generate_influencer_statistics(input_dir, output_dir)