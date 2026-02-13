# 02-2_create_follow_matrix_v2.py
# 產製2種矩陣 (Adjacency 0/1)、(Reciprocity 0/1/2)、入出度摘要報告 network_metrics
# 新增 Betweenness_Centrality 計算

import pandas as pd
import numpy as np
import os
import networkx as nx

# ==========================================
# 參數與路徑設定
# ==========================================
MASTER_LIST_PATH = 'Aisa100_ig.csv'
EDGE_LIST_PATH = 'Output/username_edge_list.csv' 
OUTPUT_DIR = 'Output'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def run_phase_2_updated():
    print("--- 開始執行第二階段：矩陣生成與指標計算 ---")
    
    # 1. 讀取母體與邊清單
    if not os.path.exists(MASTER_LIST_PATH):
        print(f"錯誤：找不到母體名單檔案 {MASTER_LIST_PATH}")
        return
    master_df = pd.read_csv(MASTER_LIST_PATH)
    
    # 確保名稱一致性 (處理空格與字串)
    master_df['clean_person_name'] = master_df['person_name'].astype(str).str.strip().str.replace(r'[ ,，]+', '-', regex=True)
    ordered_influencers = master_df['person_name'].tolist()
    unique_master = master_df.drop_duplicates(subset=['clean_person_name'], keep='first')
    url_map = dict(zip(unique_master['clean_person_name'], unique_master['ig_url']))
    rank_map = dict(zip(unique_master['clean_person_name'], unique_master['order']))

    if not os.path.exists(EDGE_LIST_PATH):
        print(f"錯誤：找不到邊清單 {EDGE_LIST_PATH}")
        return
    df_edges = pd.read_csv(EDGE_LIST_PATH)
    
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
    
    # 3. 建立矩陣 (為了後續計算 In-Degree 與 Mutual)
    node_count = len(ordered_influencers)
    adj_matrix = pd.DataFrame(0, index=ordered_influencers, columns=ordered_influencers)
    for _, row in df_edges.iterrows():
        if row['source'] in adj_matrix.index and row['target'] in adj_matrix.columns:
            adj_matrix.at[row['source'], row['target']] = 1
            
    recip_matrix = adj_matrix.copy()
    for i in range(node_count):
        for j in range(i + 1, node_count):
            if adj_matrix.iloc[i, j] == 1 and adj_matrix.iloc[j, i] == 1:
                recip_matrix.iloc[i, j] = 2
                recip_matrix.iloc[j, i] = 2

    # 4. 產製報告 DataFrame
    in_degree = adj_matrix.sum(axis=0)
    out_degree = adj_matrix.sum(axis=1)
    mutual_count = (recip_matrix == 2).sum(axis=1)
    
    metrics_report = pd.DataFrame({
        'Original_Rank': [rank_map.get(name, 999) for name in ordered_influencers],
        'Person_Name': ordered_influencers,
        'In_Degree (被追蹤數)': in_degree.values,
        'Out_Degree (主動追蹤數)': out_degree.values,
        'Mutual_Follow (互粉數)': mutual_count.values,
        'Network_Influence_Score': (in_degree.values / (node_count - 1) * 100).round(2),
        'Betweenness_Centrality': [round(betweenness.get(name, 0), 6) for name in ordered_influencers],
        'ig_url': [url_map.get(name, '') for name in ordered_influencers]
    })

    # 5. 輸出結果
    adj_matrix.to_csv(os.path.join(OUTPUT_DIR, 'test_influencer_adjacency_matrix.csv'), encoding='utf-8-sig')
    recip_matrix.to_csv(os.path.join(OUTPUT_DIR, 'test_influencer_reciprocity_matrix.csv'), encoding='utf-8-sig')
    metrics_report.to_csv(os.path.join(OUTPUT_DIR, 'test_network_metrics_report.csv'), index=False, encoding='utf-8-sig')
    print("02-2 執行完畢，Betweenness_Centrality 已加入 report。")

if __name__ == "__main__":
    run_phase_2_updated()