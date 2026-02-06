(async () => {
    const targetUserId = '在此輸入測試對象的數字ID';  // ⭐⭐ 改這
    const getCookie = (name) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    };

    let allUsers = [];
    let nextMaxId = "";
    let loopCount = 1;

    console.log(`🚀 壓力測試開始！目標 ID: ${targetUserId}`);

    while (true) {
        // IG 預設一頁約 12-50 人，500 人帳號預計會跑 10-20 次迴圈
        const url = `https://www.instagram.com/api/v1/friendships/${targetUserId}/following/?count=50&max_id=${nextMaxId}`;
        
        try {
            const res = await fetch(url, {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "X-Csrftoken": getCookie('csrftoken'),
                    "X-IG-App-ID": "936619743392459"
                }
            });

            if (res.status !== 200) {
                console.error(`🛑 異常中斷！狀態碼: ${res.status}`);
                break;
            }

            const data = await res.json();
            allUsers = [...allUsers, ...data.users];

            console.log(`--- 第 ${loopCount} 次請求 ---`);
            console.log(`📦 本次拿到: ${data.users.length} 人`);
            console.log(`🔗 下一頁 Token: ${data.next_max_id || '無 (已到底)'}`);
            console.log(`📊 目前總計: ${allUsers.length} 人`);

            if (!data.next_max_id) {
                console.log("🏁 測試順利結束，資料已完整。");
                break;
            }

            nextMaxId = data.next_max_id;
            loopCount++;

            // 安全間隔：500 人規模建議每次休息 7 秒，模擬真實閱讀
            const delay = 7000 + Math.random() * 3000;
            console.log(`⏳ 等待 ${Math.round(delay/1000)} 秒後繼續...`);
            await new Promise(r => setTimeout(r, delay));

        } catch (e) {
            console.error("💥 執行時出錯:", e);
            break;
        }
    }
    // 輸出 JSON 到 Console 供複製
    console.log("💾 最終資料對象:", allUsers);
})();

// 輸出成功後，對著物件點右鍵選擇「Store as global variable」(儲存為全域變數)，
// 接著在 Console 輸入 copy(temp1) 並按 Enter (類似 ctrl + c 的效果)