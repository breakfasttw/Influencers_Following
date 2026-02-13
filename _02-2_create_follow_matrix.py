# 產製2種矩陣 (Adjacency 0/1)、(Reciprocity 0/1/2)、入出度與中介摘要報告 network_metrics_reports
# input = 02-1 的edge 表格

import pandas as pd
import numpy as np
import os
import networkx as nx

# ==========================================
# 參數與路徑設定
# ==========================================
MASTER_LIST_PATH = 'Aisa100_ig.csv'
# 讀取第一階段產出的邊清單，請確保檔案位於 Output 資料夾或根目錄
EDGE_LIST_PATH = 'Output/username_edge_list.csv' 
TOTAL_FOLLOWING_PATH = 'Output/username_total_following.csv'
OUTPUT_DIR = 'Output'

if not os.path.exists(EDGE_LIST_PATH):
    EDGE_LIST_PATH = 'username_edge_list.csv'



# 確保輸出目錄存在
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def run_phase_2_updated():
    print("--- 開始執行第二階段：矩陣生成與指標計算 ---")
    
    # ==========================================
    # 1. 讀取母體清單以決定固定順序 (Rank Order)
    # ==========================================

    # 1. 讀取母體清單
    if not os.path.exists(MASTER_LIST_PATH):
        print(f"錯誤：找不到母體名單檔案 {MASTER_LIST_PATH}")
        return
        
    master_df = pd.read_csv(MASTER_LIST_PATH)
    # 清除欄位名稱可能存在的空格
    master_df.columns = master_df.columns.str.strip()
    
    # 確保名稱一致性 (處理空格與字串) "-"
    master_df['clean_person_name'] = master_df['person_name'].astype(str).str.strip().str.replace(r'[ ,，]+', '-', regex=True)

    # 使用 dict.fromkeys 維持原始排序並去重
    # 這裡改用剛剛產生的 clean_person_name 確保後續矩陣 key 值一致
    ordered_influencers = list(dict.fromkeys(master_df['clean_person_name'].tolist()))
    
    # --- [修正後的去重邏輯] ---
    # 現在欄位已經存在了，可以安全執行 drop_duplicates
    unique_master = master_df.drop_duplicates(subset=['clean_person_name'], keep='first')
    
    # 建立 Mapping 字典 (從去重後的資料中提取)
    url_map = dict(zip(unique_master['clean_person_name'], unique_master['ig_url']))
    rank_map = dict(zip(unique_master['clean_person_name'], unique_master['order']))

    # 讀取 Edge List
    if not os.path.exists(EDGE_LIST_PATH):
        print(f"錯誤：找不到邊清單檔案 {EDGE_LIST_PATH}")
        return

    df_edges = pd.read_csv(EDGE_LIST_PATH)


    # 建立排名映射表 (1 為排行榜第一名)
    rank_map = {name: i + 1 for i, name in enumerate(ordered_influencers)}
    
    # ==========================================
    # 2. 初始化鄰接矩陣 (Adjacency Matrix 0/1)
    # ==========================================
    # Row 代表發起追蹤者，Column 代表被追蹤者

    # 2. 建立圖形並計算個人影響力指標 (中介中心性)
    # 建立 NetworkX 有向圖
    G = nx.from_pandas_edgelist(df_edges, source='source', target='target', create_using=nx.DiGraph())
    
    # 確保 100 位網紅都在圖中 (含沒有連線的孤立者)
    for person in ordered_influencers:
        if person not in G:
            G.add_node(person)
            
    # [關鍵計算] 中介中心性 (Betweenness Centrality)
    # 代表該網紅在多少條「最短路徑」上，數值越高轉運能力越強
    betweenness = nx.betweenness_centrality(G, normalized=True)

    # 2. 建立矩陣
    node_count = len(ordered_influencers)
    print(f"成功加載 {node_count} 位網紅，矩陣將依照原始熱搜排行榜順序排列。")
    adj_matrix = pd.DataFrame(0, index=ordered_influencers, columns=ordered_influencers)
    
    # 將追蹤關係填入矩陣
    for _, row in df_edges.iterrows():
        src, tgt = str(row['source']), str(row['target'])
        if src in adj_matrix.index and tgt in adj_matrix.columns:
            adj_matrix.at[src, tgt] = 1

    # ==========================================
    # 3. 建立互惠矩陣 (Reciprocity Matrix 0/1/2)
    # ==========================================
    # 邏輯：矩陣與其轉置矩陣相加
    # 1 (A->B) + 1 (B->A) = 2 (互粉)
    # 1 (A->B) + 0 (B->A) = 1 (單向)
    recip_values = adj_matrix.values + adj_matrix.values.T
    recip_matrix = pd.DataFrame(recip_values, index=ordered_influencers, columns=ordered_influencers)

    # ==========================================
    # 4. 計算網路分析指標
    # ==========================================
    # 入度：被多少人追蹤
    in_degree = adj_matrix.sum(axis=0)    
    # 出度：主動追蹤多少人
    out_degree = adj_matrix.sum(axis=1)   
    # 互粉數：在互惠矩陣中數值等於 2 的次數
    mutual_count = (recip_matrix == 2).sum(axis=1)
    
    # 1. 建立名稱與 URL 的映射字典
    # 先對 master_df 進行去重，只保留每位網紅的第一筆資料 (預設 keep='first' 就會依據 order 順序取第一個)
    unique_master = master_df.drop_duplicates(subset=['clean_person_name'], keep='first')

    # 2. 建立 Mapping 字典
    url_map = dict(zip(unique_master['clean_person_name'], unique_master['ig_url']))
    rank_map = dict(zip(unique_master['clean_person_name'], unique_master['order']))

    # 3. 彙整摘要報告 (這時長度就會完全對齊 ordered_influencers 的 100 筆)
    metrics_report = pd.DataFrame({
        'Original_Rank': [rank_map.get(name, 999) for name in ordered_influencers],
        'Person_Name': ordered_influencers,
        'In_Degree (被追蹤數)': in_degree.values,
        'Out_Degree (主動追蹤數)': out_degree.values,
        'Mutual_Follow (互粉數)': mutual_count.values,
        'Network_Influence_Score': (in_degree.values / (node_count - 1) * 100).round(2),
        'Betweenness_Centrality': [round(betweenness.get(name, 0), 6) for name in ordered_influencers],
        # 根據去重後的字典抓取 URL
        'ig_url': [url_map.get(name, '') for name in ordered_influencers]
    })

    # ==========================================
    # 4-1. 整合 distinct_following 欄位
    # ==========================================
    if os.path.exists(TOTAL_FOLLOWING_PATH):
        total_df = pd.read_csv(TOTAL_FOLLOWING_PATH)
        # 建立 source -> distinct_following 的映射字典，注意這裡也要處理空格換成 "-" 的一致性
        total_df['source'] = total_df['source'].str.strip().str.replace(' ', '-')
        follow_map = dict(zip(total_df['source'], total_df['distinct_following']))
        
        # 新增欄位，使用 map 對應 Person_Name
        metrics_report['distinct_following'] = metrics_report['Person_Name'].map(follow_map).fillna(0).astype(int)

    # ==========================================
    # 5. 輸出結果檔案
    # ==========================================
    adj_out_path = os.path.join(OUTPUT_DIR, 'influencer_adjacency_matrix.csv') # 單向關注矩陣
    recip_out_path = os.path.join(OUTPUT_DIR, 'influencer_reciprocity_matrix.csv') # 雙向互惠矩陣
    report_out_path = os.path.join(OUTPUT_DIR, 'network_metrics_report.csv')
    
    # 使用 utf-8-sig 確保 Excel 開啟中文不亂碼
    adj_matrix.to_csv(adj_out_path, encoding='utf-8-sig')
    recip_matrix.to_csv(recip_out_path, encoding='utf-8-sig')
    metrics_report.to_csv(report_out_path, index=False, encoding='utf-8-sig')

    print("-" * 30)
    print(f"第二階段執行完畢！")
    print(f"1. 鄰接矩陣 (0/1): {adj_out_path}")
    print(f"2. 互惠矩陣 (0/1/2): {recip_out_path}")
    print(f"3. 網路指標報告: {report_out_path}")
    print("\n[數據提示]：您可以查看 network_metrics_report.csv 來比對排行榜排名與實際社交影響力的差異。")

if __name__ == "__main__":
    run_phase_2_updated()