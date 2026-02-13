import pandas as pd
import json
import os

INPUT_DIR = 'Output'
OUTPUT_DIR = 'Output'


def generate_frontend_data(adj_path, group_path, edge_path, metrics_path):
    # --- 1. 載入資料 ---
    adj_matrix = pd.read_csv(adj_path, index_col=0)
    group_report = pd.read_csv(group_path)
    edge_list = pd.read_csv(edge_path)
    metrics_report = pd.read_csv(metrics_path)

    # --- 2. 建立派系與配色對照表 ---
    # 設定派系顏色方案 (HEX)
    group_colors = {
        "主要派系 1": "#E41A1C", "主要派系 2": "#377EB8", "主要派系 3": "#4DAF4A",
        "主要派系 4": "#984EA3", "主要派系 5": "#FF7F00", "主要派系 6": "#FFFF33"
    }
    
    name_to_group = {}
    for _, row in group_report.iterrows():
        group_name = row['派系名稱']
        members = [m.strip() for m in row['所有成員'].split('|')]
        for m in members:
            name_to_group[m] = group_name

    # --- 3. 處理 Nodes (節點) 數據 ---
    nodes = []
    for _, row in metrics_report.iterrows():
        name = row['Person_Name']
        group = name_to_group.get(name, "其他")
        nodes.append({
            "id": name,
            "name": name,
            "group": group,
            "color": group_colors.get(group, "#94a3b8"),
            "val": (row['In_Degree (被追蹤數)'] + row['Out_Degree (主動追蹤數)']) / 2 + 5, # 決定球體大小
            "metrics": {
                "in_degree": int(row['In_Degree (被追蹤數)']),
                "out_degree": int(row['Out_Degree (主動追蹤數)']),
                "mutual": int(row['Mutual_Follow (互粉數)'])
            }
        })

    # --- 4. 處理 Links (連線) 數據 ---
    # 建立一個集合用來快速判斷是否存在反向連線（互粉）
    edges_set = set(zip(edge_list['source'], edge_list['target']))
    links = []
    processed_pairs = set()

    for _, row in edge_list.iterrows():
        u, v = row['source'], row['target']
        pair = tuple(sorted((u, v)))
        
        # 如果 A 追蹤 B 且 B 追蹤 A
        if (v, u) in edges_set:
            if pair not in processed_pairs:
                links.append({"source": u, "target": v, "type": "mutual"})
                processed_pairs.add(pair)
        else:
            links.append({"source": u, "target": v, "type": "single"})
    
    NODE_JSON = os.path.join(OUTPUT_DIR, 'nodes_edges.json')

    # 儲存 nodes_edges.json
    with open(NODE_JSON, 'w', encoding='utf-8') as f:
        json.dump({"nodes": nodes, "links": links}, f, ensure_ascii=False, indent=2)

    # --- 5. 處理 Heatmap Matrix (矩陣) 數據 ---
    # 為了讓熱力圖呈現「區塊化」，必須依照派系重新排序網紅名單
    sorted_names = sorted(adj_matrix.index.tolist(), key=lambda x: name_to_group.get(x, "其他"))
    sorted_adj = adj_matrix.loc[sorted_names, sorted_names]

    matrix_json = {
        "z": sorted_adj.values.tolist(),
        "x": sorted_names,
        "y": sorted_names
    }

    MATRIX_JSON = os.path.join(OUTPUT_DIR, 'matrix.json')

    # 儲存 matrix.json
    with open(MATRIX_JSON, 'w', encoding='utf-8') as f:
        json.dump(matrix_json, f, ensure_ascii=False, indent=2)

    print("Successfully generated nodes_edges.json and matrix.json")


ADJ_MATRIX_PATH = os.path.join(INPUT_DIR, 'influencer_adjacency_matrix.csv')
GROUP_PATH = os.path.join(INPUT_DIR, 'community_grouping_report_final.csv')
EDGE_PATH = os.path.join(INPUT_DIR, 'username_edge_list.csv')
NETWORK_METRICS_PATH = os.path.join(INPUT_DIR, 'network_metrics_report.csv')

# 執行轉換
generate_frontend_data(
    ADJ_MATRIX_PATH,
    GROUP_PATH,
    EDGE_PATH,
    NETWORK_METRICS_PATH
)