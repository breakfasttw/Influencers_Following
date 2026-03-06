(async () => {
    // ================= 配置區 =================
    const queryHash = "58712303d941c6855d4e888c5f0cd22f";

    // 請在此貼入妳的清單 (確保兩者長度相同)
    const targetUserId_list = ["7958155041", "255612709"];
    const username_list = ["milasky_love", "peeta.gege"];

    // 延遲參數 (秒)
    const smallSleep = { min: 8, max: 12 }; // 內層：翻頁休息
    const bigSleep = { min: 60, max: 120 }; // 外層：換人休息
    // ==========================================

    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    const getRandom = (min, max) =>
        Math.floor(Math.random() * (max - min + 1) + min);
    const getTime = () => new Date().toLocaleTimeString();

    console.log(
        `%c🚀 批次抓取任務啟動，預計處理 ${targetUserId_list.length} 個目標`,
        "color: #2e89ff; font-weight: bold; font-size: 14px;",
    );

    for (let i = 0; i < targetUserId_list.length; i++) {
        const targetUserId = targetUserId_list[i];
        const username = username_list[i];

        console.log(
            `%c\n[${getTime()}] >>> 開始處理第 ${i + 1} 位：${username} (${targetUserId})`,
            "color: #f7b928; font-weight: bold;",
        );

        let allUsers = [];
        let endCursor = "";
        let hasNextPage = true;
        let loopCount = 1;
        const seenIds = new Set();

        while (hasNextPage) {
            const variables = JSON.stringify({
                id: targetUserId,
                first: 50,
                after: endCursor,
            });

            const url = `https://www.instagram.com/graphql/query/?query_hash=${queryHash}&variables=${encodeURIComponent(variables)}`;

            try {
                const res = await fetch(url, {
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "X-IG-App-ID": "936619743392459",
                    },
                });
                const json = await res.json();

                if (json.errors || !json.data?.user?.edge_follow) {
                    console.error(
                        `%c[${username}] 抓取異常:`,
                        "color: #f02849;",
                        json.errors?.[0]?.message || "格式錯誤",
                    );
                    break;
                }

                const data = json.data.user.edge_follow;
                const edges = data.edges;

                edges.forEach((edge) => {
                    const node = edge.node;
                    if (!seenIds.has(node.id)) {
                        seenIds.add(node.id);
                        allUsers.push({
                            strong_id__: node.id,
                            username: node.username,
                            full_name: node.full_name,
                            is_verified: node.is_verified ?? "FieldMissing",
                            is_private: node.is_private ?? "FieldMissing",
                        });
                    }
                });

                console.log(
                    `%c[${username}] 第 ${loopCount} 輪完成 | 累計唯一人數: ${allUsers.length}`,
                    "color: #45bd62;",
                );

                hasNextPage = data.page_info.has_next_page;
                endCursor = data.page_info.end_cursor;
                loopCount++;

                if (hasNextPage) {
                    const delaySec = getRandom(smallSleep.min, smallSleep.max);
                    console.log(`⏳ 分頁等待中... ${delaySec} 秒後繼續`);
                    await sleep(delaySec * 1000);
                }
            } catch (e) {
                console.error(
                    `%c[${username}] 執行失敗:`,
                    "color: #f02849;",
                    e,
                );
                break;
            }
        }

        // 單一目標結束，下載檔案
        if (allUsers.length > 0) {
            const jsonString = JSON.stringify(allUsers, null, 2);
            const blob = new Blob([jsonString], { type: "application/json" });
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = `${username}.json`;
            a.click();
            console.log(
                `%c✅ [${username}] 抓取完成！檔案已自動下載。`,
                "color: #2e89ff; font-weight: bold;",
            );
        }

        // 判斷是否需要大休息 (最後一位不用等)
        if (i < targetUserId_list.length - 1) {
            const restSec = getRandom(bigSleep.min, bigSleep.max);
            console.log(
                `%c💤 觸發大休息：為保護帳號安全，等待 ${restSec} 秒後再處理下一位...`,
                "color: #b0b3b8; font-style: italic;",
            );
            await sleep(restSec * 1000);
        }
    }

    console.log(
        `%c\n[${getTime()}] 🏁 所有的批次任務已執行完畢！`,
        "color: #45bd62; font-weight: bold; font-size: 14px;",
    );
})();
