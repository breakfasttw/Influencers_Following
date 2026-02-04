import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
import seaborn as sns
import networkx as nx
from networkx.algorithms import community
import os
from adjustText import adjust_text

# ==========================================
# 0. 全域設定
# ==========================================
plt.rcParams['font.sans-serif'] = ['Iansui', 'Microsoft JhengHei', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False 

INPUT_DIR = 'Output'
OUTPUT_DIR = 'Output'
# 繪圖時我們需要有向關係 (0/1 矩陣)
ADJ_MATRIX_PATH = os.path.join(INPUT_DIR, 'influencer_adjacency_matrix.csv')
RECIP_MATRIX_PATH = os.path.join(INPUT_DIR, 'influencer_reciprocity_matrix.csv')
METRICS_PATH = os.path.join(INPUT_DIR, 'network_metrics_report.csv')

CUSTOM_COLORS = ['#45B7D1', '#FFA07A', '#F7DC6F', '#FF6B6B', '#98D8C8', '#BB8FCE', '#4ECDC4', '#85929E']

# ==========================================
# 1. 關聯熱圖模組 (維持原樣)
# ==========================================
def generate_clustered_heatmap(recip_df):
    print("正在執行：產生熱圖 (強化網格標註)...")
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
    font_size = 10 if len(clean_df) < 100 else 7
    plt.setp(g.ax_heatmap.get_xticklabels(), rotation=90, fontsize=font_size)
    plt.setp(g.ax_heatmap.get_yticklabels(), rotation=0, fontsize=font_size)
    g.fig.suptitle(f"網紅關聯強度矩陣 (已移除 {isolated_count} 位無連結網紅)", fontsize=30, y=1.03, weight='bold')
    plt.gcf().text(0.5, 0.99, "關係強度指標 (0: 無關係, 1: 單向關注, 2: 雙向互粉)", ha='center', fontsize=18, color='gray', style='italic')
    g.savefig(os.path.join(OUTPUT_DIR, 'influencer_clustered_heatmap.png'), dpi=300, bbox_inches='tight')
    plt.close()

# ==========================================
# 2. 網路圖模組 (核心修改：Directed Graph)
# ==========================================
def generate_social_network_analysis(adj_df, recip_df, metrics_df):
    print("正在執行：產生有向網路勢力圖 (含箭頭與雙向連線)...")
    
    # 1. 建立有向圖 (DiGraph)
    G_full = nx.from_pandas_adjacency(adj_df, create_using=nx.DiGraph)
    
    # 找出核心節點
    core_nodes = [n for n, d in G_full.degree() if d > 0]
    isolated_nodes = [n for n in G_full.nodes() if n not in core_nodes]
    G_core = G_full.subgraph(core_nodes)
    
    metrics_lookup = metrics_df.set_index('Person_Name').to_dict('index')

    # 2. 社群偵測 (仍使用無向連線進行分群，穩定性較高)
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
    
    # 3. 分離連線：互粉 vs 單向
    mutual_edges = []
    single_edges = []
    for u, v in G_core.edges():
        # 利用 recip_df (互惠矩陣) 來判斷是否為雙向
        if recip_df.loc[u, v] == 2:
            mutual_edges.append((u, v))
        else:
            single_edges.append((u, v))

    # 4. 繪製連線
    # 單向連線：直箭頭，細淡線
    nx.draw_networkx_edges(
        G_core, pos, edgelist=single_edges, 
        alpha=0.15, width=0.8, edge_color='#AAAAAA', 
        ax=ax, arrows=True, arrowstyle='-|>', arrowsize=15
    )
    
    # 互粉連線：帶弧度的雙向箭頭，粗黑線
    # connectionstyle='arc3,rad=0.1' 讓兩條線產生弧度避免重疊
    nx.draw_networkx_edges(
        G_core, pos, edgelist=mutual_edges, 
        alpha=0.5, width=2.5, edge_color='#222222', 
        ax=ax, arrows=True, arrowstyle='-|>', arrowsize=20,
        connectionstyle='arc3,rad=0.1' 
    )
    
    # 5. 繪製節點
    node_sizes = [200 + metrics_lookup.get(n, {}).get('In_Degree (被追蹤數)', 0) * 450 for n in G_core.nodes()]
    node_colors = [community_map.get(n, 0) for n in G_core.nodes()]
    nx.draw_networkx_nodes(G_core, pos, node_size=node_sizes, node_color=node_colors, 
                           cmap=my_cmap, vmin=0, vmax=len(final_comm)-1, alpha=0.9, ax=ax)
    
    # 6. 文字避讓標籤
    texts = []
    for node, (x, y) in pos.items():
        m_info = metrics_lookup.get(node, {})
        if m_info.get('Mutual_Follow (互粉數)', 0) > 0 or m_info.get('In_Degree (被追蹤數)', 0) > 2:
            texts.append(ax.text(x, y, node, fontsize=12, weight='bold'))
    if texts:
        adjust_text(texts, arrowprops=dict(arrowstyle='->', color='red', lw=0.5, alpha=0.4))

    # 標題與 Subtitle 置右
    ax.set_title(f"網紅社群勢力圖 (已移除 {len(isolated_nodes)} 位無連結網紅)", fontsize=36, pad=50, weight='bold', loc='center')
    plt.gcf().text(0.9, 0.92, "節點大小：被追蹤數 | 位置：社交親疏 | 連線：追蹤方向(箭頭)", ha='right', fontsize=18, color='#444444')

    # 圖例
    legend_handles = []
    group_leaders = []
    for i, comm in enumerate(final_comm):
        leader = max(list(comm), key=lambda m: metrics_lookup.get(m, {}).get('In_Degree (被追蹤數)', 0))
        group_leaders.append(leader)
        lbl = f"群 {i+1}：{leader}" if i < MAX_COMM - 1 else f"群 8 (混合)：{leader}"
        legend_handles.append(mpatches.Patch(color=CUSTOM_COLORS[i], label=lbl))
    ax.legend(handles=legend_handles, title="社群領袖 (依圈內影響力)", loc='upper right', fontsize=16)

    plt.axis('off')
    plt.savefig(os.path.join(OUTPUT_DIR, 'social_network_graph_optimized.png'), bbox_inches='tight', dpi=300)
    plt.close()

    # 7. 報告產出
    comm_rows = []
    for i, comm in enumerate(final_comm):
        comm_rows.append({'派系名稱': f"主要派系 {i+1}", '成員總數': len(comm), '核心領袖': group_leaders[i], '所有成員': " | ".join(list(comm))})
    if isolated_nodes:
        comm_rows.append({'派系名稱': '未與他人關聯 (Degree = 0)', '成員總數': len(isolated_nodes), '核心領袖': isolated_nodes[0], '所有成員': " | ".join(isolated_nodes)})
    pd.DataFrame(comm_rows).to_csv(os.path.join(OUTPUT_DIR, 'community_grouping_report_final.csv'), index=False, encoding='utf-8-sig')

# ==========================================
# 執行
# ==========================================
if __name__ == "__main__":
    try:
        adj_df = pd.read_csv(ADJ_MATRIX_PATH, index_col=0)
        recip_df = pd.read_csv(RECIP_MATRIX_PATH, index_col=0)
        m_df = pd.read_csv(METRICS_PATH)
        
        generate_clustered_heatmap(recip_df)
        generate_social_network_analysis(adj_df, recip_df, m_df)
        print("所有分析與圖表已更新完成！")
    except Exception as e:
        print(f"執行出錯: {e}")