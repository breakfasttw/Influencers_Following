# 執行演算法、參數設定 (模組化重構版：12+1 合併邏輯)
# input: EDGE_LIST_PATH, RECIP_MATRIX_PATH
# output: community_master.json (各演算法結果與 Q 度)

import pandas as pd
import networkx as nx
from networkx.algorithms import community
import igraph as ig
import json
import os
from config import *

# ==========================================
# 0. 共同設定與資料載入函式
# ==========================================
def load_and_prepare_graphs():
    """
    載入邊清單與互惠矩陣，產製 NetworkX 與 igraph 物件。
    注意：此處沿用 following 原有的互惠矩陣權重邏輯。
    """
    if not os.path.exists(EDGE_LIST_PATH) or not os.path.exists(RECIP_MATRIX_PATH):
        raise FileNotFoundError("錯誤：找不到邊清單或互惠矩陣檔案。")
        
    df_edges = pd.read_csv(EDGE_LIST_PATH)
    recip_df = pd.read_csv(RECIP_MATRIX_PATH, index_col=0)
    
    # --- NetworkX 準備 ---
    G_nx = nx.from_pandas_edgelist(df_edges, source='source', target='target', create_using=nx.DiGraph())
    G_undir = G_nx.to_undirected()
    
    # --- igraph 準備 (Walktrap 加權專用) ---
    node_names = list(G_undir.nodes())
    node_map = {name: i for i, name in enumerate(node_names)}
    
    edges = []
    weights = []
    processed_pairs = set()
    
    for u, v in G_undir.edges():
        pair = tuple(sorted((u, v)))
        if pair not in processed_pairs:
            # 依據互惠矩陣給予權重：2.0 (互粉) or 1.0 (單向)
            # following 版本不使用 count 權重
            w = 2.0 if recip_df.at[u, v] == 2 else 1.0
            edges.append((node_map[u], node_map[v]))
            weights.append(w)
            processed_pairs.add(pair)
            
    g_ig = ig.Graph(n=len(node_names), edges=edges, directed=False)
    g_ig.es['weight'] = weights
    
    return G_undir, g_ig, node_names

# ==========================================
# 1. 分群上限設定 (12+1 合併邏輯)
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
    
    top_12.append(others)
    return top_12

# ==========================================
# 2. WalkTrap 演算法函式
# ==========================================
def compute_walktrap_algorithm(g_ig, node_names):
    """
    執行 Walktrap 演算法。
    [可調參數說明]
    - steps: 隨機遊走步數，通常設為 3-5，越高則分群越粗略。
    """
    print("正在執行 Walktrap 演算法...")
    # 執行 igraph Walktrap
    wt_dendrogram = g_ig.community_walktrap(weights='weight', steps=4)
    comm_result = wt_dendrogram.as_clustering()
    
    # 轉換格式
    membership = comm_result.membership
    groups = {}
    for idx, group_id in enumerate(membership):
        name = node_names[idx]
        if group_id not in groups: groups[group_id] = []
        groups[group_id].append(name)
    
    raw_communities = list(groups.values())
    final_communities = apply_community_limit(raw_communities)
    
    return {
        "modularity": comm_result.modularity,
        "membership": final_communities,
        "params": {"steps": 4}
    }

# ==========================================
# 3. Louvain 演算法函式
# ==========================================
def compute_louvain_algorithm(G_undir):
    """
    執行 Louvain 演算法。
    [可調參數說明]
    - resolution: 分辨率，>1 得到較多小群，<1 得到較少大群。
    """
    print("正在執行 Louvain 演算法...")
    # Louvain 在 following 原始邏輯中不使用權重 (weight=None)
    comm_set = community.louvain_communities(G_undir, weight=None, resolution=1.0)
    communities = [list(c) for c in comm_set]
    
    # 計算 Q 度 (Modularity)
    mod = community.modularity(G_undir, comm_set)
    
    final_communities = apply_community_limit(communities)
    
    return {
        "modularity": mod,
        "membership": final_communities,
        "params": {"resolution": 1.0}
    }

# ==========================================
# 4. Greedy Modularity 演算法函式
# ==========================================
def compute_greedy_algorithm(G_undir):
    """
    執行 Greedy Modularity 演算法。
    適合處理大型網路。
    """
    print("正在執行 Greedy Modularity 演算法...")
    # Greedy 在 following 原始邏輯中不使用權重
    comm_set = list(community.greedy_modularity_communities(G_undir, weight=None))
    communities = [list(c) for c in comm_set]
    
    # 計算 Q 度
    mod = community.modularity(G_undir, comm_set)
    
    final_communities = apply_community_limit(communities)
    
    return {
        "modularity": mod,
        "membership": final_communities,
        "params": {}
    }

# ==========================================
# 5. 儲存與輸出函式
# ==========================================
def export_community_results(all_results):
    """
    將結果整合存為 JSON，供後續視覺化程式 (05-4) 使用。
    """
    save_path = os.path.join(INPUT_DIR, 'community_master.json')
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n--- 分群結果已成功儲存至 {save_path} ---")

# ==========================================
# 6. 主執行函式 (Main Function)
# ==========================================
def run_community_compute():
    print("--- 執行 05-3：統一計算社群分群 (重構版) ---")
    
    try:
        # A. 資料載入與準備
        G_undir, g_ig, node_names = load_and_prepare_graphs()
        
        # B. 執行各演算法
        final_results = {}
        
        # 1. Walktrap
        final_results['Walktrap'] = compute_walktrap_algorithm(g_ig, node_names)
        
        # 2. Louvain
        final_results['Louvain'] = compute_louvain_algorithm(G_undir)
        
        # 3. Greedy Modularity
        final_results['Greedy'] = compute_greedy_algorithm(G_undir)
        
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