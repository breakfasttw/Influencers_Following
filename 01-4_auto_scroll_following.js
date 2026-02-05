// 需另開 f12 視窗，不要遮蓋到容器
// 每滾一次休息 n 秒鐘，確保請求正確載入
// 即使瀏覽器端卡住，可以再貼腳本繼續滾


(async () => {

    const container = document.querySelector('div.x6nl9eh.x1a5l9x9');

    if (!container) {
        console.error('找不到追蹤清單容器，請確認 modal 已開');
        return;
    }

    const log = console.log;

    console.log('已鎖定追蹤名單容器');

    let lastHeight = 0;
    let same = 0;
    let watchdog = 0;

    const sleep = ms => new Promise(resolve => {
        const start = performance.now();
        function check(t) {
        if (t - start >= ms) resolve();
        else requestAnimationFrame(check);
        }
        requestAnimationFrame(check);
    });


    while (same < 5) { // 設定連續 10 次高度不變才停止滾動並結束腳本，避免路塞車導致轉圈圈很久的情形

        watchdog++;
        if (watchdog > 300) {
            log('⛔ watchdog 強制中止');
            break;
        }

        // 產生隨機毫秒數
        const min = 6000; // 1 秒 = 1000毫秒
        const max = 10000;
        const randomTime = Math.floor(Math.random() * (max - min + 1)) + min;

        log(`等待 ${Math.round(randomTime/1000)} 秒後，繼續嘗試捲動.....`)
        // 防止有時 loading 轉圈圈較久才生成資料

        container.scrollTo({
            top: container.scrollHeight,
            behavior: 'smooth'
        });

        await sleep(randomTime);

        let h = container.scrollHeight;

        // 判斷是否到底
        if (h === lastHeight) {
            // nudging trick 如果高度沒變，幫它輕推一下，再等一次
            container.scrollTop -= 200;
            await new Promise(r => setTimeout(r, 1000));
            container.scrollTop += 400;
            await new Promise(r => setTimeout(r, 2000));

            h = container.scrollHeight;

            if (h === lastHeight) {
                same++;
                log(`疑似到底，第 ${same} 次`);
            } else {
                same = 0;
                lastHeight = h;
                log('nudging 輕推成功，繼續載入');
            }
        } else {
            same = 0;
            lastHeight = h;
        }

        log('目前高度:', h);
    }

    log('✅ 追蹤名單已全部載入');

})();
