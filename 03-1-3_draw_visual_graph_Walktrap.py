# 03-1-2_draw_visual_graph_Walktrap.py
# 產製：社群網絡圖、分群表、網頁所需json (使用 Walktrap 演算法)
# input = 02-2 的所有產物 (Output/*.csv)
# output = Output/Walktrap/*_wt.*

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
import networkx as nx
import os
import json
from adjustText import adjust_text

# 嘗試匯入 igraph，若無則提示安裝
try:
    import igraph as ig
except ImportError:
    raise ImportError("錯誤：請先安裝 python-igraph 套件。指令：pip install python-igraph")

# ==========================================
# 0. 全域設定
# ==========================================
plt.rcParams['font.sans-serif'] = ['Iansui', 'Microsoft JhengHei', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False 

INPUT_DIR = 'Output'
OUTPUT_DIR = os.path.join('Output', 'Walktrap')

# 確保輸出資料夾存在
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

ADJ_MATRIX_PATH = os.path.join(INPUT_DIR, 'influencer_adjacency_matrix.csv')
RECIP_MATRIX_PATH = os.path.join(INPUT_DIR, 'influencer_reciprocity_matrix.csv')
METRICS_PATH = os.path.join(INPUT_DIR, 'network_metrics_report.csv')

CUSTOM_COLORS = ['#45B7D1', '#FFA07A', '#F7DC6F', "#58E751",'#BB8FCE', '#FF6B6B' , "#5968EE", "#78724F", "#A9A9A9", "#000000"]

# ==========================================
# 1. 網路圖模組 (Walktrap 版本)
# ==========================================
def generate_walktrap_network_analysis(adj_df, recip_df, metrics_df):
    print("正在執行：產生有向網路勢力圖 (演算法: Walktrap)...")
    
    # 建立 NetworkX 圖 (用於資料處理與繪圖)
    G_full = nx.from_pandas_adjacency(adj_df, create_using=nx.DiGraph)
    
    # 嚴格區分核心與孤島
    core_nodes = [n for n, d in G_full.degree() if d > 0]
    isolated_nodes = [n for n in G_full.nodes() if n not in core_nodes]
    
    # --- 匯出 zero_degree_wt.json ---
    with open(os.path.join(OUTPUT_DIR, 'zero_degree_wt.json'), 'w', encoding='utf-8') as f:
        json.dump(isolated_nodes, f, ensure_ascii=False, indent=2)
    print(f"成功：已匯出 {len(isolated_nodes)} 位零關聯網紅至 zero_degree_wt.json")

    G_core = G_full.subgraph(core_nodes)
    metrics_lookup = metrics_df.set_index('Person_Name').to_dict('index')

    # ==========================================
    # 核心演算法：Walktrap (需轉換至 igraph)
    # ==========================================
    print("正在轉換資料結構並執行 Walktrap 分群...")
    
    # 1. 建立節點映射 (NetworkX 名稱 -> igraph 索引)
    node_names = list(G_core.nodes())
    node_map = {name: i for i, name in enumerate(node_names)}
    
    # 2. 準備邊與權重 (轉換為無向圖邏輯，互粉權重加倍)
    # Walktrap 在處理這種社交親密度時，通常視為無向連結 (關係強弱)
    edges = []
    weights = []
    
    # 為了避免重複計算無向邊，我們使用一個 set 來追蹤已處理的 pair
    processed_pairs = set()
    
    for u, v in G_core.edges():
        if u > v: # 確保 pair 順序一致，避免 (A,B) 和 (B,A) 重複算
            pair = (v, u)
        else:
            pair = (u, v)
            
        if pair not in processed_pairs:
            # 決定權重：如果是互粉(2)則權重為 2，單向(1)則權重為 1
            # 這裡直接查詢 recip_df，它已經包含了雙向資訊
            w = 2.0 if recip_df.at[u, v] == 2 else 1.0
            
            edges.append((node_map[u], node_map[v]))
            weights.append(w)
            processed_pairs.add(pair)
            
    # 3. 建立 igraph 物件
    g_ig = ig.Graph(n=len(node_names), edges=edges, directed=False)
    g_ig.es['weight'] = weights # 設定邊的權重
    
    # 4. 執行 Walktrap
    # -----------------------------------------------------------
    # [參數說明]
    # steps (步數): 隨機遊走的長度。
    #   - 預設建議值: 4
    #   - 調小 (e.g., 2-3): 會分出非常破碎、微小的群體 (過度敏感)。
    #   - 調大 (e.g., 6-8): 容易把不相關的大群體合併 (解析度過低)。
    # weights: 使用我們剛剛設定的互粉權重，讓互粉的人更容易被歸為同一群。
    # -----------------------------------------------------------
    wt_dendrogram = g_ig.community_walktrap(weights='weight', steps=4)
    
    # 5. 切割分群 (使用最大模組度自動決定最佳群數)
    # as_clustering() 會自動在樹狀圖中找到模組度(Modularity)最高的那一層切下去
    comm_result = wt_dendrogram.as_clustering()
    print(f"Walktrap 分群完成：自動劃分為 {len(comm_result)} 個群體 (Modularity: {comm_result.modularity:.4f})")
    
    # 6. 將結果映射回 NetworkX
    # comm_result.membership 給出每個 node index 所屬的群組 ID
    membership = comm_result.membership
    
    # 整理分群結果： list of sets
    # 先建立一個 dict: group_id -> list of names
    groups = {}
    for idx, group_id in enumerate(membership):
        name = node_names[idx]
        if group_id not in groups:
            groups[group_id] = []
        groups[group_id].append(name)
        
    # 轉為 list 並依群體大小排序
    final_comm = sorted(groups.values(), key=len, reverse=True)
    
    # 限制主要顏色顯示數量 (前 8 群給獨立色，剩下的歸類為混合)
    MAX_COMM = 8
    
    # 建立顏色映射 map
    community_map = {}
    for i, members in enumerate(final_comm):
        # 如果超過最大顏色數，就全部歸為同一類 (最後一個顏色)
        color_idx = i if i < MAX_COMM - 1 else MAX_COMM - 1
        for name in members:
            community_map[name] = color_idx

    # ==========================================
    # 繪圖模組
    # ==========================================
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
    my_cmap = ListedColormap(CUSTOM_COLORS[:min(len(final_comm), MAX_COMM)])
    node_sizes = [200 + metrics_lookup.get(n, {}).get('In_Degree (被追蹤數)', 0) * 450 for n in G_core.nodes()]
    node_colors = [community_map.get(n, 0) for n in G_core.nodes()]
    
    nx.draw_networkx_nodes(G_core, pos, node_size=node_sizes, node_color=node_colors, 
                           cmap=my_cmap, vmin=0, vmax=min(len(final_comm), MAX_COMM)-1, alpha=0.9, ax=ax)
    
    # 標籤
    texts = [ax.text(pos[n][0], pos[n][1], n, fontsize=12, weight='bold') for n in G_core.nodes() 
             if metrics_lookup.get(n, {}).get('Mutual_Follow (互粉數)', 0) > 0 or metrics_lookup.get(n, {}).get('In_Degree (被追蹤數)', 0) > 2]
    if texts: adjust_text(texts, arrowprops=dict(arrowstyle='->', color='red', lw=0.5, alpha=0.4))

    ax.set_title(f"網紅社群勢力圖 (Walktrap 分群 | steps=4 | 已移除孤島)", fontsize=36, pad=50, weight='bold', loc='center')
    plt.gcf().text(0.9, 0.92, f"演算法：Walktrap (Auto-Cut) | 分群數：{len(final_comm)}", ha='right', fontsize=18, color='#444444')

    # 圖例
    legend_handles = []
    group_leaders = []
    
    # 只顯示前 MAX_COMM 個圖例
    display_count = min(len(final_comm), MAX_COMM)
    
    for i in range(display_count):
        comm_members = final_comm[i]
        # 若是最後一組且還有更多群體，標示為混合
        is_mixed = (i == MAX_COMM - 1) and (len(final_comm) > MAX_COMM)
        
        # 找出領袖 (In_Degree 最高)
        leader = max(comm_members, key=lambda m: metrics_lookup.get(m, {}).get('In_Degree (被追蹤數)', 0))
        group_leaders.append(leader) # 注意：如果是混合組，這裡只存了最大的那個領袖，報告中需要處理
        
        if is_mixed:
            lbl = f"其他小型群體 (混和)：{leader} 等"
        else:
            lbl = f"群 {i+1}：{leader} ({len(comm_members)}人)"
            
        legend_handles.append(mpatches.Patch(color=CUSTOM_COLORS[i], label=lbl))
        
    ax.legend(handles=legend_handles, title="Walktrap 社群領袖", loc='upper right', fontsize=16)

    plt.axis('off')
    plt.savefig(os.path.join(OUTPUT_DIR, 'social_network_graph_optimized_wt.png'), bbox_inches='tight', dpi=300)
    plt.close()

    # ==========================================
    # 產出報告 CSV
    # ==========================================
    comm_rows = []
    for i, comm in enumerate(final_comm):
        # 重新計算每個群的領袖 (為了寫入 CSV)
        leader = max(comm, key=lambda m: metrics_lookup.get(m, {}).get('In_Degree (被追蹤數)', 0))
        comm_rows.append({
            '派系名稱': f"Walktrap Group {i+1}", 
            '成員總數': len(comm), 
            '核心領袖': leader, 
            '所有成員': " | ".join(comm)
        })
    if isolated_nodes:
        comm_rows.append({
            '派系名稱': '0-Degree', 
            '成員總數': len(isolated_nodes), 
            '核心領袖': isolated_nodes[0], 
            '所有成員': " | ".join(isolated_nodes)
        })
    pd.DataFrame(comm_rows).to_csv(os.path.join(OUTPUT_DIR, 'community_grouping_report_final_wt.csv'), index=False, encoding='utf-8-sig')

    # ==========================================
    # 產出 nodes_edges_wt.json
    # ==========================================
    nodes_json = []
    for node in G_core.nodes():
        # 取得顏色 index
        # 需反查該 node 在 final_comm 的哪一群
        found_idx = -1
        for idx, comm in enumerate(final_comm):
            if node in comm:
                found_idx = idx
                break
        
        color_idx = found_idx if found_idx < MAX_COMM - 1 else MAX_COMM - 1
        m = metrics_lookup.get(node, {})
        
        nodes_json.append({
            "id": node, 
            "name": node, 
            "group": f"Walktrap Group {found_idx+1}", 
            "color": CUSTOM_COLORS[color_idx], 
            "val": 1 + m.get('In_Degree (被追蹤數)', 0) / 4,
            "metrics": {
                "in_degree": int(m.get('In_Degree (被追蹤數)', 0)), 
                "out_degree": int(m.get('Out_Degree (主動追蹤數)', 0)),
                "mutual": int(m.get('Mutual_Follow (互粉數)', 0)),
                "distinct_following": int(m.get('distinct_following', 0))}
        })
    
    links_json = [{"source": u, "target": v, "type": "mutual" if recip_df.at[u, v] == 2 else "single"} for u, v in G_core.edges()]
    
    with open(os.path.join(OUTPUT_DIR, 'nodes_edges_wt.json'), 'w', encoding='utf-8') as f:
        json.dump({"nodes": nodes_json, "links": links_json}, f, ensure_ascii=False, indent=2)

    print(f"Walktrap 分析完畢。結果已存於：{OUTPUT_DIR}")

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
        
        generate_walktrap_network_analysis(adj_df, recip_df, m_df)