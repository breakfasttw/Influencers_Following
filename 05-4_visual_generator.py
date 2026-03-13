import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import os
import json
from adjustText import adjust_text
from config import *

# ==========================================
# 1. 資料載入與前處理函式
# ==========================================
def load_analysis_data():
    """載入 05-1 與 05-3 產出的所有必要數據 (包含擴充的全域指標)"""
    metrics_path = os.path.join(INPUT_DIR, 'network_metrics_report.csv')
    recip_path = os.path.join(INPUT_DIR, 'influencer_reciprocity_matrix.csv')
    comm_path = os.path.join(INPUT_DIR, 'community_master.json')
    global_stats_path = os.path.join(INPUT_DIR, 'global_stats_temp.json')
    
    if not all(os.path.exists(p) for p in [metrics_path, recip_path, comm_path, global_stats_path]):
        raise FileNotFoundError("錯誤：找不到 05-1 或 05-3 產出的必要檔案。")
        
    metrics_df = pd.read_csv(metrics_path)
    recip_df = pd.read_csv(recip_path, index_col=0)
    
    with open(comm_path, 'r', encoding='utf-8') as f:
        comm_data = json.load(f)
        
    with open(global_stats_path, 'r', encoding='utf-8') as f:
        global_stats = json.load(f)
        
    return metrics_df, recip_df, comm_data, global_stats

def get_algorithm_config(alg_name):
    """依照演算法對應 Suffix 與建立子目錄"""
    mapping = {
        'Walktrap': '_wt',
        'Louvain': '_lv',
        'Greedy': '_gd'
    }
    suffix = mapping.get(alg_name, f'_{alg_name.lower()}')
    
    output_dir = os.path.join(INPUT_DIR, alg_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    return suffix, output_dir

# ==========================================
# 2. 報表產製函式 (CSV 欄位與孤島處理)
# ==========================================
def export_grouping_csv(alg_name, communities, metrics_lookup, zero_nodes, output_dir, suffix):
    """產製包含孤島的派系報表，並返回核心領袖映射表"""
    report_data = []
    in_col = 'In_Degree (被追蹤數)'
    leader_map = {}
    
    # A. 處理主體社群 (A-M)
    for i, comm in enumerate(communities):
        group_label = chr(i + 65)
        # 核心領袖：該群內被追蹤數最高者
        leader = max(comm, key=lambda n: metrics_lookup.get(n, {}).get(in_col, 0))
        leader_map[i] = leader
        
        display_name = f"{group_label} (其他小群)" if i == 12 else group_label
        
        report_data.append({
            '派系名稱': display_name,
            '成員總數': len(comm),
            '核心領袖': leader,
            '所有成員': ' | '.join(map(str, comm)) # map(str) 避免 TypeError
        })
    
    # B. 處理 0-Degree (孤島) - 僅出現在 CSV 中
    if zero_nodes:
        report_data.append({
            '派系名稱': '0-Degree (孤島)',
            '成員總數': len(zero_nodes),
            '核心領袖': 'N/A',
            '所有成員': ' | '.join(map(str, zero_nodes))
        })
    
    df_report = pd.DataFrame(report_data)
    save_path = os.path.join(output_dir, f'community_grouping_report_final{suffix}.csv')
    df_report.to_csv(save_path, index=False, encoding='utf-8-sig')
    return leader_map

# ==========================================
# 3. 圖像繪製核心函式 (樣式嚴格復刻)
# ==========================================
def draw_network_map(G_draw, G_layout, communities, metrics_lookup, leader_map, alg_name, q_score, zero_count, output_dir, suffix):
    """執行視覺化繪圖與圖片儲存"""
    plt.figure(figsize=(24, 24))
    plt.rcParams['font.sans-serif'] = FONT_SETTING # 解決中文亂碼
    plt.rcParams['axes.unicode_minus'] = False
    
    # --- [可調參數說明]：重力佈局設定 ---
    # k (最佳距離)： 調大（如 0.55 或 0.6）可讓 200 個節點的圖面較鬆散。
    # iterations (運算次數)： 增加次數（如 100）讓佈局趨於穩定。
    pos = nx.spring_layout(G_layout, k=0.7, iterations=500, seed=42, weight='weight')
    
    # A. 建立圖例 (格式: A (成員數): 領袖)
    legend_handles = []
    for i, leader in leader_map.items():
        group_label = chr(i + 65)
        member_count = len(communities[i])
        label = f"{group_label} ({member_count}): {leader}"
        if i == 12: label += " (其他小群)"
        
        legend_handles.append(mpatches.Patch(color=CUSTOM_COLORS[i % len(CUSTOM_COLORS)], label=label))

    # B. 繪圖屬性設定
    in_col = 'In_Degree (被追蹤數)'
    node_sizes = [metrics_lookup.get(n, {}).get(in_col, 0) * 45 + 250 for n in G_draw.nodes()]
    
    node_to_group = {n: i for i, comm in enumerate(communities) for n in comm}
    node_colors = [CUSTOM_COLORS[node_to_group.get(n, 12) % len(CUSTOM_COLORS)] for n in G_draw.nodes()]
    
    weights = [d['weight'] for u, v, d in G_draw.edges(data=True)]
    max_w = max(weights) if weights else 1
    edge_widths = [(w / max_w) * 3 + 0.2 for w in weights]

    # C. 執行繪圖 (有向實心箭頭)
    nx.draw_networkx_edges(G_draw, pos, width=edge_widths, alpha=0.45, edge_color="#3E3D3D",
                           arrows=True, arrowsize=8, arrowstyle='-|>') 
    
    nx.draw_networkx_nodes(G_draw, pos, node_size=node_sizes, node_color=node_colors, alpha=0.75, edgecolors='white')

    # D. 文字標籤與 adjust_text
    texts = [plt.text(pos[n][0], pos[n][1], n, fontsize=8, fontweight='bold') 
             for n in G_draw.nodes() if metrics_lookup.get(n, {}).get(in_col, 0) > 3]

    if texts:
        adjust_text(texts, arrowprops=dict(arrowstyle='-', linestyle='--', color="#395182", lw=0.4))

    # E. 標題與圖例樣式 (嚴格遵守指示)
    plt.title(f"台灣網紅社群追蹤互動網路分析 - {alg_name}", fontsize=36, pad=120)
    plt.suptitle(f"演算法: {alg_name} | Q 度: {q_score:.4f} | 已排除 {zero_count} 位孤島網紅", 
                 fontsize=21, y=0.93)
    
    plt.legend(
        handles=legend_handles, 
        title="社群分群核心領袖", 
        loc='upper left', 
        bbox_to_anchor=(1.01, 1), 
        prop={'size': 14}, 
        title_fontsize=16, 
        frameon=True, 
        shadow=True, 
        borderpad=1
    )

    # F. 移除邊框
    ax = plt.gca()
    for spine in ['top', 'bottom', 'left', 'right']:
        ax.spines[spine].set_visible(False)

    save_path = os.path.join(output_dir, f'social_network_graph_weighted{suffix}.png')
    plt.savefig(save_path, bbox_inches='tight',dpi=300)
    plt.close()
    print(f"   - 圖片已儲存: {save_path}")

# ==========================================
# 4. JSON 產製函式 (與擴充 SNA 指標對齊)
# ==========================================
def export_web_json(G_draw, communities, metrics_lookup, alg_result, output_dir, suffix):
    """產製網頁使用的 nodes_edges.json (巢狀結構擴充版)"""
    nodes_json = []
    node_to_group = {n: i for i, comm in enumerate(communities) for n in comm}
    
    # 取出 05-3 算好的中觀指標
    node_cluster_metrics = alg_result.get('node_metrics', {})
    
    for node in G_draw.nodes():
        g_idx = node_to_group.get(node, 12)
        m = metrics_lookup.get(node, {})
        m_cluster = node_cluster_metrics.get(node, {})
        
        nodes_json.append({
            "id": node, 
            "name": node, 
            "group": chr(g_idx + 65), 
            "color": CUSTOM_COLORS[g_idx % len(CUSTOM_COLORS)], 
            "val": 1 + m.get('In_Degree (被追蹤數)', 0) / 4,
            "metrics": {
                "in_degree": int(m.get('In_Degree (被追蹤數)', 0)), 
                "out_degree": int(m.get('Out_Degree (主 ক্যামের主動追蹤數)', 0)) if pd.notna(m.get('Out_Degree (主動追蹤數)')) else 0, # 防呆
                "mutual": int(m.get('Mutual_Follow (互粉數)', 0)),
                "between_centrality": float(m.get('Betweenness_Centrality', 0.0)),
                "Eigenvector Centrality": float(m.get('Eigenvector_Centrality', 0.0)),
                "Local Clustering Coefficient": float(m.get('Local_Clustering_Coefficient', 0.0)),
                "Core-periphery Coreness": int(m.get('Core-periphery_Coreness', 0))
            },
            "metrics_cluster": {
                "Within-module Degree": float(m_cluster.get('Within_module_Degree', 0.0)),
                "Participation Coefficient": float(m_cluster.get('Participation_Coefficient', 0.0))
            },
            "Following": int(m.get('Following', 0)) if pd.notna(m.get('Following')) else 0,
            "Followers": int(m.get('Followers', 0)) if pd.notna(m.get('Followers')) else 0,
            "posts": int(m.get('posts', 0)) if pd.notna(m.get('posts')) else 0,
            "category": str(m.get('category', 'unknown'))
        })

    links_json = [{"source": u, "target": v, "type": d['type'], "value": d['weight']} 
                  for u, v, d in G_draw.edges(data=True)]

    json_path = os.path.join(output_dir, f'nodes_edges{suffix}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({"nodes": nodes_json, "links": links_json}, f, ensure_ascii=False, indent=2)

# ==========================================
# 5. 打包最終宏觀報表 (整合原 05-5 邏輯)
# ==========================================
def generate_network_summary(global_stats, comm_data):
    """將 05-1 的總體指標與 05-3 的群體中觀指標打包"""
    print("\n--- 整合演算法數據報表 (network_summary.json) ---")
    summary = global_stats.copy()
    
    for algo in ['Greedy', 'Louvain', 'Walktrap']:
        if algo in comm_data:
            summary[algo] = {
                "Group_Count": len(comm_data[algo]['membership']),
                "Group_Size": [len(c) for c in comm_data[algo]['membership']],
                "Modularity_Score_Q": round(comm_data[algo]['modularity'], 6),
                "Cluster Density": comm_data[algo].get("Cluster_Density", {}),
                "Inter-cluster Edge Density": comm_data[algo].get("Inter_cluster_Edge_Density", {})
            }
        
    output_path = os.path.join(INPUT_DIR, 'network_summary.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=4)
    print(f"最終摘要已儲存至: {output_path}")

# ==========================================
# 6. 主執行函式 (Main Function)
# ==========================================
def run_visual_generator():
    print("--- 執行 05-4：Following 視覺化產製與總表整合 (正式擴充版) ---")
    
    try:
        metrics_df, recip_df, comm_data, global_stats = load_analysis_data()
        metrics_lookup = metrics_df.set_index('Person_Name').to_dict('index')
        
        # [關鍵修正]：正確取得使用者名稱字串集，避免 RangeIndex (int) 造成 join 錯誤
        all_users = set(metrics_df['Person_Name'].astype(str))
        
        for alg_name, result in comm_data.items():
            print(f"\n>> 處理演算法：{alg_name}")
            
            suffix, output_dir = get_algorithm_config(alg_name)
            communities = result['membership']
            q_score = result['modularity']
            
            # 識別孤島 (0-Degree)
            active_nodes = [n for g in communities for n in g]
            zero_nodes = sorted(list(all_users - set(active_nodes)))
            zero_count = len(zero_nodes)
            
            # 1. 產製 CSV 報表並取得 Leader Map
            leader_map = export_grouping_csv(alg_name, communities, metrics_lookup, zero_nodes, output_dir, suffix)
            
            # 2. 建立圖形
            G_draw = nx.DiGraph()
            G_layout = nx.Graph()
            G_draw.add_nodes_from(active_nodes)
            G_layout.add_nodes_from(active_nodes)
            
            # 建立邊 (互粉=2, 單向=1)
            for i, u in enumerate(active_nodes):
                for v in active_nodes[i+1:]:
                    rel = recip_df.at[u, v]
                    if rel == 2:
                        G_draw.add_edge(u, v, weight=2, type="mutual")
                        G_draw.add_edge(v, u, weight=2, type="mutual")
                        G_layout.add_edge(u, v, weight=2)
                    elif rel == 1:
                        G_draw.add_edge(u, v, weight=1, type="single")
                        G_layout.add_edge(u, v, weight=1)

            # 3. 繪製圖片
            draw_network_map(G_draw, G_layout, communities, metrics_lookup, leader_map, alg_name, q_score, zero_count, output_dir, suffix)
            
            # 4. 產製 JSON (傳入 result 以獲取中觀指標)
            export_web_json(G_draw, communities, metrics_lookup, result, output_dir, suffix)

        # 5. 打包總表
        generate_network_summary(global_stats, comm_data)

    except Exception as e:
        print(f"執行出錯：{e}")

if __name__ == "__main__":
    run_visual_generator()