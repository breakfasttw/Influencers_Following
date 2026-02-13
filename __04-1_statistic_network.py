# 04-1_statistic_network_v2.py
# 整合全域指標與演算法評分 (Modularity Score)

import pandas as pd
import networkx as nx
import os
import json
from networkx.algorithms import community

# --- 參數設定 ---
INPUT_DIR = 'Output'
EDGE_LIST_FILE = 'username_edge_list.csv'
OUTPUT_DIR = 'Output'
OUTPUT_JSON_PATH = 'network_summary.json'
TOTAL_INFLUENCERS = 100  # 手動設定總母體人數

def run_network_statistics():
    # 1. 載入資料
    edge_path = os.path.join(INPUT_DIR, EDGE_LIST_FILE)
    if not os.path.exists(edge_path):
        edge_path = EDGE_LIST_FILE
    
    df_edges = pd.read_csv(edge_path)
    G_dir = nx.from_pandas_edgelist(df_edges, source='source', target='target', create_using=nx.DiGraph())
    
    # 補足 100 位母體中的孤立點 (確保密度與聚類分母正確)
    current_nodes = G_dir.number_of_nodes()
    if current_nodes < TOTAL_INFLUENCERS:
        for i in range(TOTAL_INFLUENCERS - current_nodes):
            G_dir.add_node(f"__isolated_{i}__")

    # 2. 計算全域指標 (單一公式)
    density = nx.density(G_dir)
    reciprocity = nx.reciprocity(G_dir)
    transitivity = nx.transitivity(G_dir)
    avg_clustering = nx.average_clustering(G_dir)

    # 3. 計算演算法分群指標 (Modularity Q)
    # 通常 Modularity 在無向圖上更有定義意義
    G_undir = G_dir.to_undirected()
    
    # --- Algorithm 1: Greedy ---
    greedy_comm = list(community.greedy_modularity_communities(G_undir))
    greedy_q = community.modularity(G_undir, greedy_comm)
    
    # --- Algorithm 2: Louvain ---
    louvain_comm = list(community.louvain_communities(G_undir, seed=42))
    louvain_q = community.modularity(G_undir, louvain_comm)
    
    # --- Algorithm 3: Walktrap (讀取之前產出的 CSV) ---
    wt_csv = os.path.join(OUTPUT_DIR, 'community_grouping_report_final_wt.csv')
    if os.path.exists(wt_csv):
        df_wt = pd.read_csv(wt_csv)
        # 將 CSV 中的成員字串還原為 set 以計算 Q 值
        wt_comm = [set(m.split(' | ')) for m in df_wt['所有成員']]
        wt_q = community.modularity(G_undir, wt_comm)
        wt_count = len(wt_comm)
        wt_sizes = [len(c) for c in wt_comm]
    else:
        wt_count, wt_sizes, wt_q = 0, [], 0

    # 4. 整合為 JSON 格式
    result = {
        "母體數": TOTAL_INFLUENCERS,
        "密度(Density)": round(density, 6),
        "互惠率(Reciprocity)": round(reciprocity, 6),
        "傳遞性(Transitivity)": round(transitivity, 6),
        "團體凝聚力(Avg Clustering)": round(avg_clustering, 6),
        "Greedy": {
            "Group_Count": len(greedy_comm),
            "Group_Size": [len(c) for c in greedy_comm],
            "Modularity_Score_Q": round(greedy_q, 6)
        },
        "Louvain": {
            "Group_Count": len(louvain_comm),
            "Group_Size": [len(c) for c in louvain_comm],
            "Modularity_Score_Q": round(louvain_q, 6)
        },
        "Walktrap": {
            "Group_Count": wt_count,
            "Group_Size": wt_sizes,
            "Modularity_Score_Q": round(wt_q, 6)
        }
    }

    # 5. 輸出 JSON 檔案
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_JSON_PATH)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    
    print(f"分析完成！JSON 摘要已儲存至: {output_path}")

if __name__ == "__main__":
    run_network_statistics()