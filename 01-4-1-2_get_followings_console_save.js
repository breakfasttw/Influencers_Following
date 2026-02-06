(async () => {
    // ================= 手動輸入區 =================
    const targetUserId = '在此輸入目標ID';  // 例如蔡桃貴的 8047388429
    const username = 'aries_8248';        // 檔案名稱用的 username
    // =============================================

    const getCookie = (name) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    };

    let allUsers = [];
    let nextMaxId = "";
    let loopCount = 1;

    console.log(`🚀 開始抓取 [${username}]，目標 ID: ${targetUserId}`);

    while (true) {
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

            console.log(`第 ${loopCount} 次請求 | 本次: ${data.users.length} | 累計: ${allUsers.length}`);

            if (!data.next_max_id) {
                console.log("🏁 抓取結束。");
                break;
            }

            nextMaxId = data.next_max_id;
            loopCount++;

            // 隨機延遲 7-10 秒
            const delay = 7000 + Math.random() * 3000;
            console.log(`⏳ 等待 ${Math.round(delay/1000)} 秒後繼續...`);
            await new Promise(r => setTimeout(r, delay));

        } catch (e) {
            console.error("💥 錯誤:", e);
            break;
        }
    }

    // --- 自動化程序開始 ---

    // 1. 儲存為全域變數 (在 Console 輸入 temp_result 即可看到)
    window.temp_result = allUsers;
    console.log("✅ 已儲存至全域變數: temp_result");

    // 2. 嘗試複製到剪貼簿
    try {
        copy(allUsers); // 僅在 DevTools Console 環境有效
        console.log("✅ 已執行 copy() 指令");
    } catch (e) {
        console.log("💡 無法自動複製，請手動輸入 copy(temp_result)");
    }

    // 3. 自動觸發 JSON 下載
    const jsonString = JSON.stringify(allUsers, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `${username}.json`; // 設定下載檔名
    
    document.body.appendChild(link);
    link.click(); // 觸發下載
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    console.log(`💾 檔案 [${username}.json] 已嘗試存入下載資料夾`);
})();