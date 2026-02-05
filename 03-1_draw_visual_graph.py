# 產製：階層關聯 heatmap 圖、社群網絡圖、分群表、網頁所需json
# input = 02-2 的所有產物

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
import seaborn as sns
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

INPUT_DIR = 'Output'
OUTPUT_DIR = 'Output'
ADJ_MATRIX_PATH = os.path.join(INPUT_DIR, 'influencer_adjacency_matrix.csv')
RECIP_MATRIX_PATH = os.path.join(INPUT_DIR, 'influencer_reciprocity_matrix.csv')
METRICS_PATH = os.path.join(INPUT_DIR, 'network_metrics_report.csv')

CUSTOM_COLORS = ['#45B7D1', '#FFA07A', '#F7DC6F', '#FF6B6B', '#98D8C8', '#BB8FCE', '#4ECDC4', '#85929E']

# ==========================================
# 1. 關聯熱圖模組 (過濾孤島 + 聚類 JSON)
# ==========================================
def generate_clustered_heatmap_and_json(recip_df):
    print("正在執行：產生熱圖並捕捉聚類排序...")
    
    # 過濾 Degree = 0 的孤島
    adj_temp = (recip_df.fillna(0) > 0).astype(int)
    nodes_with_edges = adj_temp.index[(adj_temp.sum(axis=1) > 0) | (adj_temp.sum(axis=0) > 0)]
    clean_df = recip_df.loc[nodes_with_edges, nodes_with_edges].fillna(0)
    isolated_count = len(recip_df) - len(clean_df)
    
    sns.set_theme(font='Iansui')
    g = sns.clustermap(
        clean_df, cmap="YlOrRd", linewidths=.3, linecolor='lightgray',
        figsize=(25, 25), xticklabels=True, yticklabels=True,
        cbar_kws={'label': '關係強度'}, dendrogram_ratio=(0.08, 0.08),
        cbar_pos=(0.02, 0.8, 0.03, 0.15) 
    )
    
    # 捕捉聚類順序
    reordered_labels = [clean_df.index[i] for i in g.dendrogram_row.reordered_ind]
    reordered_matrix = clean_df.loc[reordered_labels, reordered_labels]
    
    matrix_data = {"z": reordered_matrix.values.tolist(), "x": reordered_labels, "y": reordered_labels}
    with open(os.path.join(OUTPUT_DIR, 'matrix.json'), 'w', encoding='utf-8') as f:
        json.dump(matrix_data, f, ensure_ascii=False, indent=2)

    g.fig.suptitle(f"網紅關聯強度矩陣 (已移除 {isolated_count} 位無連結網紅)", fontsize=30, y=1.03, weight='bold')
    plt.gcf().text(0.5, 0.99, "關係強度指標 (0: 無關係, 1: 單向關注, 2: 雙向互粉)", ha='center', fontsize=18, color='gray', style='italic')
    g.savefig(os.path.join(OUTPUT_DIR, 'influencer_clustered_heatmap.png'), dpi=300, bbox_inches='tight')
    plt.close()

# ==========================================
# 2. 網路圖模組 (過濾孤島 + 分離 zero_degree.json)
# ==========================================
def generate_social_network_analysis_and_json(adj_df, recip_df, metrics_df):
    print("正在執行：產生有向網路勢力圖並分離零關聯清單...")
    
    G_full = nx.from_pandas_adjacency(adj_df, create_using=nx.DiGraph)
    
    # 嚴格區分核心與孤島
    core_nodes = [n for n, d in G_full.degree() if d > 0]
    isolated_nodes = [n for n in G_full.nodes() if n not in core_nodes]
    
    # --- [關鍵修改] 輸出 zero_degree.json ---
    with open(os.path.join(OUTPUT_DIR, 'zero_degree.json'), 'w', encoding='utf-8') as f:
        json.dump(isolated_nodes, f, ensure_ascii=False, indent=2)
    print(f"成功：已匯出 {len(isolated_nodes)} 位零關聯網紅至 zero_degree.json")

    G_core = G_full.subgraph(core_nodes)
    metrics_lookup = metrics_df.set_index('Person_Name').to_dict('index')

    # 分群運算 (使用無向投影以獲得穩定社群)
    G_undirected = G_core.to_undirected()
    raw_comm = sorted(community.greedy_modularity_communities(G_undirected), key=len, reverse=True)
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

    fig, ax = plt.subplots(figsize=(34, 34))
    pos = nx.spring_layout(G_core, k=0.35, iterations=120, seed=42)
    
    # 連線分類
    mutual_edges = [e for e in G_core.edges() if recip_df.at[e[0], e[1]] == 2]
    single_edges = [e for e in G_core.edges() if recip_df.at[e[0], e[1]] != 2]

    # 繪製靜態圖連線 (箭頭 + 弧線)
    nx.draw_networkx_edges(G_core, pos, edgelist=single_edges, alpha=0.15, width=0.8, 
                           edge_color='#AAAAAA', ax=ax, arrows=True, arrowstyle='-|>', arrowsize=15)
    nx.draw_networkx_edges(G_core, pos, edgelist=mutual_edges, alpha=0.5, width=2.8, 
                           edge_color='#222222', ax=ax, arrows=True, arrowstyle='-|>', arrowsize=20,
                           connectionstyle='arc3,rad=0.1')
    
    # 繪製靜態圖節點
    node_sizes = [200 + metrics_lookup.get(n, {}).get('In_Degree (被追蹤數)', 0) * 450 for n in G_core.nodes()]
    node_colors = [community_map.get(n, 0) for n in G_core.nodes()]
    nx.draw_networkx_nodes(G_core, pos, node_size=node_sizes, node_color=node_colors, 
                           cmap=my_cmap, vmin=0, vmax=len(final_comm)-1, alpha=0.9, ax=ax)
    
    # 標籤與 Subtitle
    texts = [ax.text(pos[n][0], pos[n][1], n, fontsize=12, weight='bold') for n in G_core.nodes() 
             if metrics_lookup.get(n, {}).get('Mutual_Follow (互粉數)', 0) > 0 or metrics_lookup.get(n, {}).get('In_Degree (被追蹤數)', 0) > 2]
    if texts: adjust_text(texts, arrowprops=dict(arrowstyle='->', color='red', lw=0.5, alpha=0.4))

    ax.set_title(f"網紅社群勢力圖 (已移除 {len(isolated_nodes)} 位無連結網紅)", fontsize=36, pad=50, weight='bold', loc='center')
    plt.gcf().text(0.9, 0.92, "節點大小：被追蹤數 | 位置：社交親疏 | 連線：追蹤方向(箭頭)", ha='right', fontsize=18, color='#444444')

    # 圖例
    legend_handles = [mpatches.Patch(color=CUSTOM_COLORS[i], label=f"群 {i+1}：{max(list(c), key=lambda m: metrics_lookup.get(m, {}).get('In_Degree (被追蹤數)', 0))}") 
                      for i, c in enumerate(final_comm)]
    ax.legend(handles=legend_handles, title="社群領袖 (依圈內影響力)", loc='upper right', fontsize=16)

    plt.axis('off')
    plt.savefig(os.path.join(OUTPUT_DIR, 'social_network_graph_optimized.png'), bbox_inches='tight', dpi=300)
    plt.close()

    # --- [關鍵修改] 產出 nodes_edges.json (僅含核心) ---
    nodes_json = []
    for node in G_core.nodes():
        g_idx = community_map.get(node, 0)
        m = metrics_lookup.get(node, {})
        nodes_json.append({
            "id": node, "name": node, "group": f"主要派系 {g_idx+1}", 
            "color": CUSTOM_COLORS[g_idx], 
            "val": 1 + m.get('In_Degree (被追蹤數)', 0) / 4, # 網頁版節點大小
            "metrics": {"in_degree": int(m.get('In_Degree (被追蹤數)', 0)), "mutual": int(m.get('Mutual_Follow (互粉數)', 0))}
        })
    links_json = [{"source": u, "target": v, "type": "mutual" if recip_df.at[u, v] == 2 else "single"} for u, v in G_core.edges()]
    
    with open(os.path.join(OUTPUT_DIR, 'nodes_edges.json'), 'w', encoding='utf-8') as f:
        json.dump({"nodes": nodes_json, "links": links_json}, f, ensure_ascii=False, indent=2)

# ==========================================
# 執行
# ==========================================
if __name__ == "__main__":
    adj_df = pd.read_csv(ADJ_MATRIX_PATH, index_col=0)
    recip_df = pd.read_csv(RECIP_MATRIX_PATH, index_col=0)
    m_df = pd.read_csv(METRICS_PATH)
    generate_clustered_heatmap_and_json(recip_df)
    generate_social_network_analysis_and_json(adj_df, recip_df, m_df)
    print("V5.1 執行完畢：已分離 0 關聯名單至 zero_degree.json，且 nodes_edges.json 已過濾。")