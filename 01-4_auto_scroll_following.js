// 需另開 f12 視窗，不要遮蓋到容器
// 每滾一次休息5秒鐘，確保請求正確載入

(async () => {

    const container = document.querySelector('div.x6nl9eh.x1a5l9x9');

    if (!container) {
        console.error('找不到追蹤清單容器，請確認 modal 已開');
        return;
    }

    console.log('已鎖定追蹤名單容器');

    let lastHeight = 0;
    let same = 0;

  // 產生隨機毫秒數
    const min = 10000;
    const max = 13000;
    const randomTime = Math.floor(Math.random() * (max - min + 1)) + min;

    while (same < 15) { // 設定連續 10 次高度不變才停止滾動並結束腳本，避免路塞車導致轉圈圈很久的情形
        container.scrollTo({
            top: container.scrollHeight,
            behavior: 'smooth'
        });

        await new Promise(r => setTimeout(r, randomTime));

        const h = container.scrollHeight;

        if (h === lastHeight) {
            same++;
            console.log(f`正在確認是否已到底，第${same}次`)
        } else {
            same = 0;
            lastHeight = h;
        }

        console.log('目前高度:', h);
    }

    console.log('✅ 追蹤名單已全部載入');

})();
