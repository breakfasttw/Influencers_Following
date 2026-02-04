```mermaid
graph TD
    subgraph Data_Source [輸入資料與預處理]
        A[Master List CSV<br/>Top200_ig] --> A1[清理姓名: 空格轉為 '-']
        A1 --> A2[建立映射表: ig_id ➔ person_name]
        B[Following CSVs Folder] --> B1[提取檔名前綴: Source Account]
    end

    subgraph Phase_1 [第一階段：邊清單生成]
        B1 --> C{發起者帳號<br/>在母體名單內?}
        C -- Yes --> D[讀取追蹤清單 username 欄位]
        D --> E{目標帳號<br/>在母體名單內?}
        E -- Yes --> F[轉換 ID 為 person_name]
        F --> G[產出 Edge List<br/>username_edge_list.csv]
    end

    subgraph Phase_2 [第二階段：模型建置與矩陣運算]
        G --> H[建立 200x200 鄰接矩陣<br/>Adjacency Matrix]
        H --> I[偵測互惠關係<br/>Mutual Following Check]
        I --> J[計算網路指標<br/>Centrality Metrics]
    end

    subgraph Phase_3 [第三階段：視覺化呈現]
        J --> K1[力導向圖: 觀察社交圈中心]
        J --> K2[熱圖: 觀察小團體 Cliques]
        J --> K3[互動排行: 影響力報表]
    end

    style G fill:#0e6699,stroke:#333,stroke-width:2px
    style J fill:#4109ba,stroke:#333,stroke-width:2px

    ```