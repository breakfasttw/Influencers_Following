# 執行演算法、參數設定 (模組化重構版：12+1 合併邏輯 + 中觀指標擴充)
# input: EDGE_LIST_PATH, RECIP_MATRIX_PATH, zero_degree.json
# output: community_master.json (各演算法結果與 Q 度、中觀層次 SNA 指標)

import pandas as pd
import numpy as np
import networkx as nx
from networkx.algorithms import community
import igraph as ig
import json
import os
from config import *

# ==========================================
# 0. SNA 中觀指標運算分流設定檔 (Configuration)
# N: 不剔除 0-Degree (將孤立節點納入群體分母或均值計算)
# Y: 剔除 0-Degree 後才計算 (孤立節點不參與群體指標，其個人指標直接補 0)
# ==========================================
SNA_METRICS_CONFIG = {
    "Meso": {
        "Within_module_Degree": "Y",
        "Participation_Coefficient": "Y",
        "Cluster_Density": "Y",
        "Inter_cluster_Edge_Density": "Y"
    }
}

# ==========================================
# 1. 共同設定與資料載入函式 (源頭過濾 0-Degree)
# ==========================================
def load_and_prepare_graphs():
    """
    載入邊清單、互惠矩陣與 0-Degree 黑名單，產製已剔除孤島的 NetworkX 與 igraph 物件。
    """
    zero_degree_path = os.path.join(INPUT_DIR, 'zero_degree.json')
    if not os.path.exists(EDGE_LIST_PATH) or not os.path.exists(RECIP_MATRIX_PATH) or not os.path.exists(zero_degree_path):
        raise FileNotFoundError("錯誤：找不到邊清單、互惠矩陣或 zero_degree.json 檔案。")
        
    df_edges = pd.read_csv(EDGE_LIST_PATH)
    recip_df = pd.read_csv(RECIP_MATRIX_PATH, index_col=0)
    
    with open(zero_degree_path, 'r', encoding='utf-8') as f:
        zero_degree_nodes = json.load(f)
    
    # --- NetworkX 準備 (先建立全體，再剔除) ---
    G_full_dir = nx.from_pandas_edgelist(df_edges, source='source', target='target', create_using=nx.DiGraph())
    ordered_influencers = list(recip_df.index)
    G_full_dir.add_nodes_from(ordered_influencers)
    
    # 產製乾淨的去孤島網路圖
    G_filtered_dir = G_full_dir.copy()
    G_filtered_dir.remove_nodes_from(zero_degree_nodes)
    G_filtered_undir = G_filtered_dir.to_undirected()
    
    # --- igraph 準備 (Walktrap 加權專用) ---
    # 注意：這裡的 node_names 只會包含活躍的網紅，沒有 0-Degree
    node_names = list(G_filtered_undir.nodes())
    node_map = {name: i for i, name in enumerate(node_names)}
    
    edges = []
    weights = []
    processed_pairs = set()
    
    for u, v in G_filtered_undir.edges():
        pair = tuple(sorted((u, v)))
        if pair not in processed_pairs:
            # 依據互惠矩陣給予權重：2.0 (互粉) or 1.0 (單向)
            w = 2.0 if recip_df.at[u, v] == 2 else 1.0
            edges.append((node_map[u], node_map[v]))
            weights.append(w)
            processed_pairs.add(pair)
            
    g_ig = ig.Graph(n=len(node_names), edges=edges, directed=False)
    g_ig.es['weight'] = weights
    
    return G_filtered_dir, G_filtered_undir, g_ig, node_names, zero_degree_nodes

# ==========================================
# 2. 分群上限設定 (12+1 合併邏輯)
# ==========================================
def apply_community_limit(communities):
    """
    將分群結果按人數排序，保留前 12 大群，其餘合併為第 13 群 (Index 12)。
    """
    # 依人數由大到小排序
    sorted_comm = sorted(communities, key=len, reverse=True)
    
    if len(sorted_comm) <= 12:
        return sorted_comm
        
    # 保留前 12 名
    top_12 = sorted_comm[:12]
    
    # 第 13 名之後的所有節點合併
    others = []
    for extra_comm in sorted_comm[12:]:
        others.extend(extra_comm)
    
    if others:
        top_12.append(others)
    return top_12

# ==========================================
# 3. 中觀層次指標計算核心 (Meso Metrics Engine)
# ==========================================
def compute_meso_metrics(G_filtered_dir, membership, zero_degree_nodes):
    """
    依據純淨的分群結果，計算中觀層次 (Cluster-level) 的 SNA 指標。
    """
    meso_results = {
        "Cluster_Density": {},
        "Inter_cluster_Edge_Density": {},
        "Node_Metrics": {}
    }
    
    # 建立 反查字典 (Node -> Cluster ID)
    node_to_cluster = {}
    for cid, members in enumerate(membership):
        for node in members:
            node_to_cluster[node] = cid

    # --- A. 群體指標 (Cluster-wide Metrics) ---
    for cid, members in enumerate(membership):
        group_name = f"Group_{cid}"
        
        # 1. Cluster Density (群內密度)
        if len(members) > 1:
            meso_results["Cluster_Density"][group_name] = nx.density(G_filtered_dir.subgraph(members))
        else:
            meso_results["Cluster_Density"][group_name] = 0.0

    # 2. Inter-cluster Edge Density (群間邊密度)
    for cid1, members1 in enumerate(membership):
        g1_name = f"Group_{cid1}"
        meso_results["Inter_cluster_Edge_Density"][g1_name] = {}
        
        for cid2, members2 in enumerate(membership):
            if cid1 == cid2: continue
            g2_name = f"Group_{cid2}"
            
            if len(members1) == 0 or len(members2) == 0:
                meso_results["Inter_cluster_Edge_Density"][g1_name][g2_name] = 0.0
            else:
                # 計算從 Group A 連向 Group B 的實際邊數
                edges_between = len(list(nx.edge_boundary(G_filtered_dir, members1, members2)))
                possible_edges = len(members1) * len(members2)
                meso_results["Inter_cluster_Edge_Density"][g1_name][g2_name] = edges_between / possible_edges

    # --- B. 個人在群內的指標 (Node-specific Cluster Metrics) ---
    for cid, members in enumerate(membership):
        # 3. Within-module Degree (計算 Z-score)
        in_cluster_degrees = {}
        if len(members) > 0:
            subg = G_filtered_dir.subgraph(members).to_undirected()
            for n in members:
                in_cluster_degrees[n] = subg.degree(n)
                
            mean_k = np.mean(list(in_cluster_degrees.values()))
            std_k = np.std(list(in_cluster_degrees.values()))
        else:
            mean_k, std_k = 0, 0

        for node in members:
            if node not in meso_results["Node_Metrics"]:
                meso_results["Node_Metrics"][node] = {}
                
            # 若標準差為 0 (大家都一樣)，Z-score 設為 0
            if std_k > 0 and node in in_cluster_degrees:
                z_score = (in_cluster_degrees[node] - mean_k) / std_k
            else:
                z_score = 0.0
            meso_results["Node_Metrics"][node]["Within_module_Degree"] = round(z_score, 4)

    # 4. Participation Coefficient (參與係數 P)
    for node in G_filtered_dir.nodes():
        total_degree = G_filtered_dir.degree(node)
        if total_degree == 0:
            meso_results["Node_Metrics"][node]["Participation_Coefficient"] = 0.0
            continue
            
        cluster_links = {}
        for neighbor in nx.all_neighbors(G_filtered_dir, node):
            if neighbor in node_to_cluster:
                n_cid = node_to_cluster[neighbor]
                cluster_links[n_cid] = cluster_links.get(n_cid, 0) + 1
                
        sum_sq = sum((links / total_degree) ** 2 for links in cluster_links.values())
        p_coef = 1.0 - sum_sq
        meso_results["Node_Metrics"][node]["Participation_Coefficient"] = round(p_coef, 4)

    # --- C. 為 0-Degree 網紅補齊 0.0 的紀錄 ---
    for node in zero_degree_nodes:
        meso_results["Node_Metrics"][node] = {
            "Within_module_Degree": 0.0,
            "Participation_Coefficient": 0.0
        }

    return meso_results

# ==========================================
# 4. WalkTrap 演算法函式
# ==========================================
def compute_walktrap_algorithm(G_filtered_dir, g_ig, node_names, zero_degree_nodes):
    print("正在執行 Walktrap 演算法...")
    wt_dendrogram = g_ig.community_walktrap(weights='weight', steps=4)
    comm_result = wt_dendrogram.as_clustering()
    
    membership = comm_result.membership
    groups = {}
    for idx, group_id in enumerate(membership):
        name = node_names[idx]
        if group_id not in groups: groups[group_id] = []
        groups[group_id].append(name)
    
    raw_communities = list(groups.values())
    final_communities = apply_community_limit(raw_communities)
    
    meso_metrics = compute_meso_metrics(G_filtered_dir, final_communities, zero_degree_nodes)
    
    return {
        "modularity": comm_result.modularity,
        "Cluster_Density": meso_metrics["Cluster_Density"],
        "Inter_cluster_Edge_Density": meso_metrics["Inter_cluster_Edge_Density"],
        "membership": final_communities,
        "node_metrics": meso_metrics["Node_Metrics"],
        "params": {"steps": 4}
    }

# ==========================================
# 5. Louvain 演算法函式
# ==========================================
def compute_louvain_algorithm(G_filtered_dir, G_filtered_undir, zero_degree_nodes):
    print("正在執行 Louvain 演算法...")
    comm_set = community.louvain_communities(G_filtered_undir, weight=None, resolution=1.0)
    communities = [list(c) for c in comm_set]
    mod = community.modularity(G_filtered_undir, comm_set)
    
    final_communities = apply_community_limit(communities)
    meso_metrics = compute_meso_metrics(G_filtered_dir, final_communities, zero_degree_nodes)
    
    return {
        "modularity": mod,
        "Cluster_Density": meso_metrics["Cluster_Density"],
        "Inter_cluster_Edge_Density": meso_metrics["Inter_cluster_Edge_Density"],
        "membership": final_communities,
        "node_metrics": meso_metrics["Node_Metrics"],
        "params": {"resolution": 1.0}
    }

# ==========================================
# 6. Greedy Modularity 演算法函式
# ==========================================
def compute_greedy_algorithm(G_filtered_dir, G_filtered_undir, zero_degree_nodes):
    print("正在執行 Greedy Modularity 演算法...")
    comm_set = list(community.greedy_modularity_communities(G_filtered_undir, weight=None))
    communities = [list(c) for c in comm_set]
    mod = community.modularity(G_filtered_undir, comm_set)
    
    final_communities = apply_community_limit(communities)
    meso_metrics = compute_meso_metrics(G_filtered_dir, final_communities, zero_degree_nodes)
    
    return {
        "modularity": mod,
        "Cluster_Density": meso_metrics["Cluster_Density"],
        "Inter_cluster_Edge_Density": meso_metrics["Inter_cluster_Edge_Density"],
        "membership": final_communities,
        "node_metrics": meso_metrics["Node_Metrics"],
        "params": {}
    }

# ==========================================
# 7. 儲存與輸出函式
# ==========================================
def export_community_results(all_results):
    save_path = os.path.join(INPUT_DIR, 'community_master.json')
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n--- 分群與中觀指標結果已成功儲存至 {save_path} ---")

# ==========================================
# 8. 主執行函式 (Main Function)
# ==========================================
def run_community_compute():
    print("--- 執行 05-3：統一計算社群分群與中觀指標 (源頭去孤島重構版) ---")
    
    try:
        # A. 資料載入與準備 (此處取得的圖形已無 0-Degree)
        G_filtered_dir, G_filtered_undir, g_ig, node_names, zero_degree_nodes = load_and_prepare_graphs()
        
        # B. 執行各演算法
        final_results = {}
        
        # 1. Walktrap
        final_results['Walktrap'] = compute_walktrap_algorithm(G_filtered_dir, g_ig, node_names, zero_degree_nodes)
        
        # 2. Louvain
        final_results['Louvain'] = compute_louvain_algorithm(G_filtered_dir, G_filtered_undir, zero_degree_nodes)
        
        # 3. Greedy Modularity
        final_results['Greedy'] = compute_greedy_algorithm(G_filtered_dir, G_filtered_undir, zero_degree_nodes)
        
        # C. 儲存結果
        export_community_results(final_results)
        
        # 輸出預覽 (Q度)
        print("\n[演算法效能 Q 度摘要]")
        for alg, data in final_results.items():
            print(f"- {alg}: {data['modularity']:.4f} (分群數: {len(data['membership'])})")

    except Exception as e:
        print(f"執行過程中發生錯誤：{e}")

if __name__ == "__main__":
    run_community_compute()