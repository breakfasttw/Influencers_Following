# 產製：社群網絡圖、分群表、網頁所需json (使用 Louvain 演算法)
# input = 02-2 的所有產物 (Output/*.csv)
# output = Output/Louvain/*

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
import networkx as nx
from networkx.algorithms import community
import os
import json
from adjustText import adjust_text

# ==========================================
# 0. 全域設定
# ==========================================
plt.rcParams['font.sans-serif'] = ['Iansui', 'Microsoft JhengHei', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False 

# 輸入維持原始路徑
INPUT_DIR = 'Output'
# 輸出改為 Output/Louvain
OUTPUT_DIR = os.path.join('Output', 'Louvain')

# 確保輸出資料夾存在
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

ADJ_MATRIX_PATH = os.path.join(INPUT_DIR, 'influencer_adjacency_matrix.csv')
RECIP_MATRIX_PATH = os.path.join(INPUT_DIR, 'influencer_reciprocity_matrix.csv')
METRICS_PATH = os.path.join(INPUT_DIR, 'network_metrics_report.csv')

CUSTOM_COLORS = ['#45B7D1', '#FFA07A', '#F7DC6F', "#58E751",'#BB8FCE',   '#FF6B6B' , "#5968EE", "#78724F"]

# ==========================================
# 1. 網路圖模組 (Louvain 版本)
# ==========================================
def generate_louvain_network_analysis(adj_df, recip_df, metrics_df):
    print("正在執行：產生有向網路勢力圖 (演算法: Louvain)...")
    
    G_full = nx.from_pandas_adjacency(adj_df, create_using=nx.DiGraph)
    
    # 嚴格區分核心與孤島
    core_nodes = [n for n, d in G_full.degree() if d > 0]
    isolated_nodes = [n for n in G_full.nodes() if n not in core_nodes]
    
    # --- 匯出 zero_degree.json ---
    # 雖然孤島名單與演算法無關，但為了讓 Output/Louvain 資料夾完整獨立，此處仍進行輸出
    with open(os.path.join(OUTPUT_DIR, 'zero_degree_lv.json'), 'w', encoding='utf-8') as f:
        json.dump(isolated_nodes, f, ensure_ascii=False, indent=2)
    print(f"成功：已匯出 {len(isolated_nodes)} 位零關聯網紅至 zero_degree_lv.json")

    G_core = G_full.subgraph(core_nodes)
    metrics_lookup = metrics_df.set_index('Person_Name').to_dict('index')

    # 分群運算 (使用 Louvain 演算法)
    # Louvain 需要無向圖來計算模組度
    G_undirected = G_core.to_undirected()
    
    # --- [核心修改] 使用 Louvain 演算法 ---
    # seed=42 確保每次執行顏色分群結果一致
    print("正在計算 Louvain 社群分群...")
    try:
        # NetworkX 2.7+ 支援此語法
        raw_comm = sorted(community.louvain_communities(G_undirected, seed=42), key=len, reverse=True)
    except AttributeError:
        # 若 networkx 版本較舊，提示使用者
        print("錯誤：您的 NetworkX 版本可能不支援 louvain_communities。請更新 networkx 或確認環境。")
        return

    MAX_COMM = 8
    final_comm = list(raw_comm[:MAX_COMM-1])
    if len(raw_comm) >= MAX_COMM:
        others = set()
        for c in raw_comm[MAX_COMM-1:]: others.update(c)
        final_comm.append(others)
    else:
        final_comm = raw_comm

    community_map = {name: i for i, c in enumerate(final_comm) for name in c}
    my_cmap = ListedColormap(CUSTOM_COLORS[:len(final_comm)])

    # --- 繪圖邏輯 (與原版保持一致，僅標題修改) ---
    fig, ax = plt.subplots(figsize=(34, 34))
    pos = nx.spring_layout(G_core, k=0.35, iterations=120, seed=42)
    
    # 連線分類
    mutual_edges = [e for e in G_core.edges() if recip_df.at[e[0], e[1]] == 2]
    single_edges = [e for e in G_core.edges() if recip_df.at[e[0], e[1]] != 2]

    # 繪製連線
    nx.draw_networkx_edges(G_core, pos, edgelist=single_edges, alpha=0.15, width=0.8, 
                           edge_color='#AAAAAA', ax=ax, arrows=True, arrowstyle='-|>', arrowsize=15)
    nx.draw_networkx_edges(G_core, pos, edgelist=mutual_edges, alpha=0.5, width=2.8, 
                           edge_color='#222222', ax=ax, arrows=True, arrowstyle='-|>', arrowsize=20,
                           connectionstyle='arc3,rad=0.1')
    
    # 繪製節點
    node_sizes = [200 + metrics_lookup.get(n, {}).get('In_Degree (被追蹤數)', 0) * 450 for n in G_core.nodes()]
    node_colors = [community_map.get(n, 0) for n in G_core.nodes()]
    nx.draw_networkx_nodes(G_core, pos, node_size=node_sizes, node_color=node_colors, 
                           cmap=my_cmap, vmin=0, vmax=len(final_comm)-1, alpha=0.9, ax=ax)
    
    # 標籤
    texts = [ax.text(pos[n][0], pos[n][1], n, fontsize=12, weight='bold') for n in G_core.nodes() 
             if metrics_lookup.get(n, {}).get('Mutual_Follow (互粉數)', 0) > 0 or metrics_lookup.get(n, {}).get('In_Degree (被追蹤數)', 0) > 2]
    if texts: adjust_text(texts, arrowprops=dict(arrowstyle='->', color='red', lw=0.5, alpha=0.4))

    # 更新標題以反映演算法
    ax.set_title(f"網紅社群勢力圖 (Louvain 分群 | 已移除 {len(isolated_nodes)} 位孤島)", fontsize=36, pad=50, weight='bold', loc='center')
    plt.gcf().text(0.9, 0.92, "節點大小：被追蹤數 | 位置：社交親疏 | 演算法：Louvain Community Detection", ha='right', fontsize=18, color='#444444')

    # 圖例
    legend_handles = []
    group_leaders = []  # 儲存每個群體的領袖，供 CSV 使用
    for i, comm in enumerate(final_comm):
        # 找出該群體中 In_Degree 最高者作為領袖
        leader = max(list(comm), key=lambda m: metrics_lookup.get(m, {}).get('In_Degree (被追蹤數)', 0))
        group_leaders.append(leader)
        lbl = f"群 {i+1}：{leader}" if i < MAX_COMM - 1 else f"群 8 (混合)：{leader}"
        legend_handles.append(mpatches.Patch(color=CUSTOM_COLORS[i], label=lbl))
        
    ax.legend(handles=legend_handles, title="社群領袖 (Louvain - 依圈內影響力)", loc='upper right', fontsize=16)

    plt.axis('off')
    plt.savefig(os.path.join(OUTPUT_DIR, 'social_network_graph_optimized_lv.png'), bbox_inches='tight', dpi=300)
    plt.close()

    # --- 產出 CSV 報告 ---
    comm_rows = []
    for i, comm in enumerate(final_comm):
        comm_rows.append({
            '派系名稱': f"主要派系 {i+1}", 
            '成員總數': len(comm), 
            '核心領袖': group_leaders[i], 
            '所有成員': " | ".join(list(comm))
        })
    if isolated_nodes:
        comm_rows.append({
            '派系名稱': '0-Degree', 
            '成員總數': len(isolated_nodes), 
            '核心領袖': isolated_nodes[0], 
            '所有成員': " | ".join(isolated_nodes)
        })
    pd.DataFrame(comm_rows).to_csv(os.path.join(OUTPUT_DIR, 'community_grouping_report_final_lv.csv'), index=False, encoding='utf-8-sig')

    # --- 產出 nodes_edges.json ---
    nodes_json = []
    for node in G_core.nodes():
        g_idx = community_map.get(node, 0)
        m = metrics_lookup.get(node, {})
        nodes_json.append({
            "id": node, "name": node, "group": f"主要派系 {g_idx+1}", 
            "color": CUSTOM_COLORS[g_idx], 
            "val": 1 + m.get('In_Degree (被追蹤數)', 0) / 4,
            "metrics": {
                "in_degree": int(m.get('In_Degree (被追蹤數)', 0)), 
                "out_degree": int(m.get('Out_Degree (主動追蹤數)', 0)),
                "mutual": int(m.get('Mutual_Follow (互粉數)', 0)),
                "distinct_following": int(m.get('distinct_following', 0))}
        })
    links_json = [{"source": u, "target": v, "type": "mutual" if recip_df.at[u, v] == 2 else "single"} for u, v in G_core.edges()]
    
    with open(os.path.join(OUTPUT_DIR, 'nodes_edges_lv.json'), 'w', encoding='utf-8') as f:
        json.dump({"nodes": nodes_json, "links": links_json}, f, ensure_ascii=False, indent=2)

    print(f"Louvain 分析完畢。結果已存於：{OUTPUT_DIR}")

# ==========================================
# 執行
# ==========================================
if __name__ == "__main__":
    if not os.path.exists(INPUT_DIR):
        print(f"錯誤：找不到輸入資料夾 '{INPUT_DIR}'")
    else:
        adj_df = pd.read_csv(ADJ_MATRIX_PATH, index_col=0)
        recip_df = pd.read_csv(RECIP_MATRIX_PATH, index_col=0)
        m_df = pd.read_csv(METRICS_PATH)
        
        # 僅執行 Graph 相關分析，略過 Heatmap
        generate_louvain_network_analysis(adj_df, recip_df, m_df)