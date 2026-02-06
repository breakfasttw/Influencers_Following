(async () => {
    // ================= 配置區 =================
    const targetUserId = '請輸入user_strong_id(純數字)';  // user_strong_id
    const username = '請輸入username(英數)';  // username，最終輸出的檔名
    const queryHash = '58712303d941c6855d4e888c5f0cd22f';  // 去 payload找
    // ==========================================

    let allUsers = [];
    let endCursor = "";
    let hasNextPage = true;
    let loopCount = 1;
    const seenIds = new Set();

    console.log(`🚀 啟動 [${username}] 完整欄位抓取模式...`);

    while (hasNextPage) {
        const variables = JSON.stringify({
            "id": targetUserId,
            "first": 50,
            "after": endCursor
        });
        
        const url = `https://www.instagram.com/graphql/query/?query_hash=${queryHash}&variables=${encodeURIComponent(variables)}`;

        try {
            const res = await fetch(url, { 
                headers: { 
                    "X-Requested-With": "XMLHttpRequest",
                    "X-IG-App-ID": "936619743392459"
                } 
            });
            const json = await res.json();

            if (json.errors || !json.data?.user?.edge_follow) {
                console.error("🛑 抓取中斷:", json.errors?.[0]?.message || "格式錯誤");
                break;
            }

            const data = json.data.user.edge_follow;
            const edges = data.edges;

            edges.forEach(edge => {
                const node = edge.node;
                if (!seenIds.has(node.id)) {
                    seenIds.add(node.id);
                    
                    // 修正處：使用 ?? 確保 false 值不會被 NotFound 覆蓋
                    allUsers.push({
                        strong_id__: node.id,
                        username: node.username,
                        full_name: node.full_name,
                        is_verified: node.is_verified ?? "FieldMissing",
                        is_private: node.is_private ?? "FieldMissing"
                    });
                }
            });

            console.log(`第 ${loopCount} 輪 | 累計唯一人數: ${allUsers.length}`);

            // 偵錯小撇步：如果還是 NotFound，印出第一個 node 看看
            if (loopCount === 1 && edges.length > 0) {
                console.log("🔍 原始資料結構樣本:", edges[0].node);
            }

            hasNextPage = data.page_info.has_next_page;
            endCursor = data.page_info.end_cursor;
            loopCount++;

            const delay = 8000 + Math.random() * 4000; // 等待至少8秒
            console.log(`⏳ 等待 ${Math.round(delay/1000)} 秒後繼續...`);
            await new Promise(r => setTimeout(r, delay));

        } catch (e) {
            console.error("💥 執行失敗:", e);
            break;
        }
    }

    if (allUsers.length > 0) {
        window.temp_result = allUsers;
        const jsonString = JSON.stringify(allUsers, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `${username}.json`;
        a.click();
        console.log(`✅ 抓取完成！總計: ${allUsers.length}。`);
    }
})();