# input
# Aisa100_ig.csv、EDGE_LIST_PATH、TOTAL_FOLLOWING_PATH
# output
# zero_degree.json
# influencer_adjacency_matrix.csv、influencer_reciprocity_matrix.csv (雙矩陣)
# network_metrics_report.csv (網紅為物件的各項統計、類別，包含微觀 SNA 指標)
# global_stats_temp.json (母體統計結果，包含宏觀 SNA 指標)

import pandas as pd
import numpy as np
import os
import json
import networkx as nx
from config import *

# ==========================================
# 0. SNA 指標運算分流設定檔 (Configuration)
# N: 不剔除 0-Degree (使用全體網路 G_full 計算)
# Y: 剔除 0-Degree 後才計算 (使用去孤島網路 G_filtered 計算，被剔除者於報表中補 0)
# ==========================================
SNA_METRICS_CONFIG = {
    # 微觀層次
    "Micro": {
        "In_Degree": "N",
        "Out_Degree": "N",
        "Mutual_Follow": "N",
        "Network_Influence_Score": "N",
        "Betweenness_Centrality": "Y",
        "Eigenvector_Centrality": "Y",
        "Local_Clustering_Coefficient": "Y",
        "Core-periphery_Coreness": "Y"
    },
    # 宏觀層次
    "Macro": {
        "Density": "N",
        "Density_0": "Y",
        "Reciprocity": "Y",
        "Transitivity": "Y",
        "Avg_Clustering": "Y",
        "Assortativity": "Y",
        "Core-periphery_Structure_Fit": "Y"
    }
}

# ==========================================
# Step 1. 載入母體與基本屬性
# ==========================================
def step1_load_and_clean_data(master_list_path):
    if not os.path.exists(master_list_path):
        print(f"錯誤：找不到母體名單檔案 {master_list_path}")
        return None, None, None
        
    master_df = pd.read_csv(master_list_path)
    master_df.columns = master_df.columns.str.strip()
    master_df['clean_person_name'] = master_df['person_name'].astype(str).str.strip().str.replace(' ', '-')
    
    # 剔除清洗後重複的網紅名單，保留第一筆資料，確保 nodelist 絕對唯一
    master_df = master_df.drop_duplicates(subset=['clean_person_name'], keep='first').reset_index(drop=True)
    
    # 建立順序清單
    ordered_influencers = master_df['clean_person_name'].tolist()
    
    # 建立欄位 Mapping 字典
    attr_maps = {
        'url': dict(zip(master_df['clean_person_name'], master_df['ig_url'])),
        'posts': dict(zip(master_df['clean_person_name'], master_df['posts'])),
        'followers': dict(zip(master_df['clean_person_name'], master_df['Followers'])),
        'following': dict(zip(master_df['clean_person_name'], master_df['Following'])),
        'category': dict(zip(master_df['clean_person_name'], master_df['category']))
    }
    
    return master_df, ordered_influencers, attr_maps

# ==========================================
# Step 2. 建立雙軌網路圖 (G_full & G_filtered)
# ==========================================
def step2_build_dual_networks(edge_list_path, ordered_influencers):
    df_edges = pd.read_csv(edge_list_path)
    
    # 1. 建立 G_full (包含所有人的全體網路)
    G_full_dir = nx.from_pandas_edgelist(df_edges, source='source', target='target', create_using=nx.DiGraph())
    G_full_dir.add_nodes_from(ordered_influencers) # 補齊 0-Degree 的孤立節點
    G_full_undir = G_full_dir.to_undirected()
    
    # 2. 找出 0-Degree 節點
    zero_degree_nodes = [n for n in G_full_dir.nodes() if G_full_dir.degree(n) == 0]
    
    # 3. 建立 G_filtered (剔除 0-Degree 後的去孤島網路)
    G_filtered_dir = G_full_dir.copy()
    G_filtered_dir.remove_nodes_from(zero_degree_nodes)
    G_filtered_undir = G_filtered_dir.to_undirected()
    
    return G_full_dir, G_full_undir, G_filtered_dir, G_filtered_undir, zero_degree_nodes

# ==========================================
# Step 3. 指標分流運算引擎 (微觀與宏觀)
# ==========================================
def step3_compute_metrics(G_full_dir, G_full_undir, G_filtered_dir, G_filtered_undir, ordered_influencers, zero_degree_nodes):
    node_count = len(ordered_influencers)
    
    # --- A. 微觀指標 (Micro Metrics) ---
    micro_metrics = {node: {} for node in ordered_influencers}
    
    # [N：不剔除 0-Degree]
    in_degree_dict = dict(G_full_dir.in_degree())
    out_degree_dict = dict(G_full_dir.out_degree())
    
    mutual_dict = {node: 0 for node in ordered_influencers}
    for u, v in G_full_dir.edges():
        if G_full_dir.has_edge(v, u):
            mutual_dict[u] += 1
            
    for n in ordered_influencers:
        micro_metrics[n]['in_degree'] = in_degree_dict.get(n, 0)
        micro_metrics[n]['out_degree'] = out_degree_dict.get(n, 0)
        micro_metrics[n]['mutual'] = mutual_dict.get(n, 0)
        micro_metrics[n]['network_influence_score'] = round((in_degree_dict.get(n, 0) / (node_count - 1)) * 100, 2)
        
    # [Y：剔除 0-Degree] (針對 G_filtered 計算，0-Degree 者預設補 0)
    betweenness_dict = nx.betweenness_centrality(G_filtered_dir)
    local_clustering_dict = nx.clustering(G_filtered_dir)
    coreness_dict = nx.core_number(G_filtered_undir)
    
    # [Y：Eigenvector 獨立處理] 解決 disconnected graphs 問題
    eigenvector_dict = {}
    for component in nx.weakly_connected_components(G_filtered_dir):
        subgraph = G_filtered_dir.subgraph(component)
        if len(subgraph) > 1:
            try:
                sub_ev = nx.eigenvector_centrality_numpy(subgraph)
                eigenvector_dict.update(sub_ev)
            except Exception:
                try:
                    sub_ev = nx.eigenvector_centrality(subgraph, max_iter=2000)
                    eigenvector_dict.update(sub_ev)
                except Exception as e:
                    print(f"警告：某個子圖 Eigenvector 計算失敗，該區塊節點標記為 0。原因: {e}")

    for n in ordered_influencers:
        if n in zero_degree_nodes:
            micro_metrics[n]['betweenness'] = 0.0
            micro_metrics[n]['eigenvector'] = 0.0
            micro_metrics[n]['local_clustering'] = 0.0
            micro_metrics[n]['coreness'] = 0
        else:
            micro_metrics[n]['betweenness'] = betweenness_dict.get(n, 0.0)
            micro_metrics[n]['eigenvector'] = eigenvector_dict.get(n, 0.0)
            micro_metrics[n]['local_clustering'] = local_clustering_dict.get(n, 0.0)
            micro_metrics[n]['coreness'] = coreness_dict.get(n, 0)


    # --- B. 宏觀指標 (Macro Metrics) ---
    macro_metrics = {"母體數": node_count, "0-Degree": len(zero_degree_nodes)}
    
    # [N：不剔除 0-Degree]
    macro_metrics["密度(Density)"] = nx.density(G_full_dir)
    
    # [Y：剔除 0-Degree]
    if len(G_filtered_dir) > 0:
        macro_metrics["密度去0(Density_0)"] = nx.density(G_filtered_dir)
        macro_metrics["互惠率(Reciprocity)"] = nx.reciprocity(G_filtered_dir)
        macro_metrics["傳遞性(Transitivity)"] = nx.transitivity(G_filtered_dir)
        macro_metrics["團體凝聚力(Avg Clustering)"] = nx.average_clustering(G_filtered_dir)
        
        # 同質性係數
        try:
            macro_metrics["同質性係數(Assortativity)"] = nx.degree_assortativity_coefficient(G_filtered_dir)
        except:
            macro_metrics["同質性係數(Assortativity)"] = 0.0
            
        # 核心邊陲結構適配度 (Core-periphery Structure Fit)
        c_nums = nx.core_number(G_filtered_undir)
        max_core_val = max(c_nums.values()) if c_nums else 0
        core_nodes = [n for n, c in c_nums.items() if c == max_core_val]
        if len(core_nodes) > 1:
            macro_metrics["核心邊陲結構適配度(Core-periphery Structure Fit)"] = nx.density(G_filtered_dir.subgraph(core_nodes))
        else:
            macro_metrics["核心邊陲結構適配度(Core-periphery Structure Fit)"] = 0.0
    else:
        # 防呆：如果全都是 0-Degree
        macro_metrics.update({"密度去0(Density_0)": 0, "互惠率(Reciprocity)": 0, "傳遞性(Transitivity)": 0, 
                              "團體凝聚力(Avg Clustering)": 0, "同質性係數(Assortativity)": 0, 
                              "核心邊陲結構適配度(Core-periphery Structure Fit)": 0})

    return micro_metrics, macro_metrics

# ==========================================
# Step 4. 組裝微觀報表與外部追蹤數
# ==========================================
def step4_assemble_dataframe(master_df, ordered_influencers, micro_metrics, attr_maps):
    # 嚴格依照指定順序組裝表頭
    metrics_report = pd.DataFrame({
        'Original_Rank': master_df['order'] if 'order' in master_df.columns else range(1, len(ordered_influencers) + 1),
        'Person_Name': ordered_influencers,
        'In_Degree (被追蹤數)': [micro_metrics[n]['in_degree'] for n in ordered_influencers],
        'Out_Degree (主動追蹤數)': [micro_metrics[n]['out_degree'] for n in ordered_influencers],
        'Mutual_Follow (互粉數)': [micro_metrics[n]['mutual'] for n in ordered_influencers],
        'Network_Influence_Score': [micro_metrics[n]['network_influence_score'] for n in ordered_influencers],
        'Betweenness_Centrality': [round(micro_metrics[n]['betweenness'], 6) for n in ordered_influencers],
        'Eigenvector_Centrality': [round(micro_metrics[n]['eigenvector'], 6) for n in ordered_influencers],
        'Local_Clustering_Coefficient': [round(micro_metrics[n]['local_clustering'], 6) for n in ordered_influencers],
        'Core-periphery_Coreness': [micro_metrics[n]['coreness'] for n in ordered_influencers],
        'ig_url': [attr_maps['url'].get(n, '') for n in ordered_influencers],
        'posts': [attr_maps['posts'].get(n, '') for n in ordered_influencers],
        'Followers': [attr_maps['followers'].get(n, '') for n in ordered_influencers],
        'Following': [attr_maps['following'].get(n, '') for n in ordered_influencers],
        'category': [attr_maps['category'].get(n, '') for n in ordered_influencers]
    })

    # 整合外部追蹤數 (distinct_following)
    if os.path.exists(TOTAL_FOLLOWING_PATH):
        total_df = pd.read_csv(TOTAL_FOLLOWING_PATH)
        total_df['source'] = total_df['source'].str.strip().str.replace(' ', '-')
        follow_map = dict(zip(total_df['source'], total_df['distinct_following']))
        metrics_report['distinct_following'] = metrics_report['Person_Name'].map(follow_map).fillna(0).astype(int)
    else:
        metrics_report['distinct_following'] = 0
        
    return metrics_report

# ==========================================
# Step 5. 輸出所有結果與暫存檔案
# ==========================================
def step5_export_files(G_full_dir, ordered_influencers, metrics_report, zero_degree_nodes, macro_metrics):
    os.makedirs(INPUT_DIR, exist_ok=True)
    
    # 產製鄰接與互惠矩陣 (以 G_full 為基礎，包含所有人)
    adj_matrix = nx.to_pandas_adjacency(G_full_dir, nodelist=ordered_influencers, weight=1)
    recip_matrix = pd.DataFrame(0, index=ordered_influencers, columns=ordered_influencers)
    for u in ordered_influencers:
        for v in ordered_influencers:
            if u != v:
                has_uv = G_full_dir.has_edge(u, v)
                has_vu = G_full_dir.has_edge(v, u)
                if has_uv and has_vu:
                    recip_matrix.loc[u, v] = 2
                elif has_uv:
                    recip_matrix.loc[u, v] = 1

    # 輸出矩陣
    adj_matrix.to_csv(os.path.join(INPUT_DIR, 'influencer_adjacency_matrix.csv'), encoding='utf-8-sig')
    recip_matrix.to_csv(os.path.join(INPUT_DIR, 'influencer_reciprocity_matrix.csv'), encoding='utf-8-sig')
    
    # 輸出微觀節點指標報表
    metrics_report.to_csv(os.path.join(INPUT_DIR, 'network_metrics_report.csv'), index=False, encoding='utf-8-sig')
    
    # 輸出孤立節點暫存檔
    with open(os.path.join(INPUT_DIR, 'zero_degree.json'), 'w', encoding='utf-8') as f:
        json.dump(zero_degree_nodes, f, ensure_ascii=False, indent=2)

    # 輸出宏觀網路指標暫存檔
    with open(os.path.join(INPUT_DIR, 'global_stats_temp.json'), 'w', encoding='utf-8') as f:
        json.dump(macro_metrics, f, ensure_ascii=False, indent=4)

    print("=> 成功產出：influencer_adjacency_matrix.csv")
    print("=> 成功產出：influencer_reciprocity_matrix.csv")
    print("=> 成功產出：network_metrics_report.csv")
    print("=> 成功產出：global_stats_temp.json")

# ==========================================
# 核心執行器 (Main Routine)
# ==========================================
def run_matrix_engine():
    print("--- 開始執行 05-1：產製矩陣、微觀與宏觀全域指標 (5步架構重構版) ---")
    
    # Step 1
    master_df, ordered_influencers, attr_maps = step1_load_and_clean_data(MASTER_LIST_PATH)
    if master_df is None: return
    
    # Step 2
    G_full_dir, G_full_undir, G_filtered_dir, G_filtered_undir, zero_degree_nodes = step2_build_dual_networks(EDGE_LIST_PATH, ordered_influencers)
    
    # Step 3
    micro_metrics, macro_metrics = step3_compute_metrics(G_full_dir, G_full_undir, G_filtered_dir, G_filtered_undir, ordered_influencers, zero_degree_nodes)
    
    # Step 4
    metrics_report = step4_assemble_dataframe(master_df, ordered_influencers, micro_metrics, attr_maps)
    
    # Step 5
    step5_export_files(G_full_dir, ordered_influencers, metrics_report, zero_degree_nodes, macro_metrics)
    
    print("=> 05-1 執行完畢。\n")

if __name__ == "__main__":
    run_matrix_engine()