# VYRA War Room — Live Market Scanner

繁體中文 / English (US) · Emerald Black · Bitunix 公開行情 · 不需要 AI API 金鑰

## 上傳 GitHub

此資料夾可直接作為 GitHub repository 的根目錄。請解壓縮後上傳裡面的檔案，保留 `tests/` 子資料夾；不要只上傳 ZIP。

完整操作見 [GITHUB_UPLOAD.md](GITHUB_UPLOAD.md)。專案不包含本機日誌、程序 ID、持倉、交易日誌或 API 金鑰。手動資料保存在各自瀏覽器內，未包含在原始碼中。

**上傳 GitHub 是分享原始碼，不等於線上部署。** GitHub Pages 只能託管靜態內容，無法執行本專案的 Python 行情服務。朋友下載專案後可在自己電腦啟動；若希望直接用公開網址取得完整即時行情，需要另外部署網頁與後端。

## 專案結構

```text
index.html                 網頁與掃描器介面
server.py                  Bitunix 公開行情服務
Start-VYRA.command         macOS 背景啟動檔
requirements.txt           Python 依賴說明（僅使用標準函式庫）
.gitignore                 排除本機執行檔案、暫存檔與金鑰
.gitattributes             統一文字檔換行
GITHUB_UPLOAD.md           上傳 GitHub 操作說明
tests/test-scanner.cjs      掃描規則測試
tests/test_market.py        行情服務與快取測試
```


## 開啟方式

1. 需要 Python 3 與網路連線，不需要 API 金鑰。
2. 在 Mac 雙擊 `Start-VYRA.command`，服務會在背景執行，啟動成功後可關閉終端機視窗。若提示舊版服務正在執行，請先關閉舊版服務的終端機視窗再重開啟動檔。若從 GitHub 網頁下載後無法直接執行啟動檔，可在終端機切換到此資料夾後執行 `chmod +x Start-VYRA.command`，或直接執行 `python3 server.py`。
3. 啟動檔會開啟 `http://127.0.0.1:8765/`，可將此網址貼到 Chrome。請透過這個網址使用，以避開本機 HTML 連線到服務的瀏覽器限制。
4. 頁面顯示「已連線 Bitunix」後開始自動更新與掃描。可按「暫停更新」或切換掃描週期。

目前 HTML 會使用此行情服務取得行情；單獨下載 HTML 並不包含服務。請下載完整專案。

原有手動持倉、交易計畫與日誌仍保存在原瀏覽器的本機儲存空間。請在相同瀏覽器開啟相同位置的 HTML，以保留原有資料；不同瀏覽器、檔案位置或改用 localhost 網址可能使用不同儲存空間。

## 更新與掃描

- 每 10 秒讀取 Bitunix 全市場價格、24 小時漲跌與成交量。
- 從官方交易對清單自動取得 `OPEN` 的 USDT 期貨合約；清單每小時刷新。這包含交易所提供的其他資產合約。
- 目前選擇的價格圖表每 15 秒讀取已收盤 OHLC K 線；保留 K 線／折線與 1H／4H／1D 切換。
- 掃描器依 24 小時成交額排序，輪流讀取所有合約最近 100 根 K 線，計算 EMA20、EMA50、Wilder RSI14 與成交量比。掃描週期可選 15m／1H／4H／1D。
- 做多規則：收盤價 > EMA20 > EMA50；RSI14 為 55–70；成交量至少為前 20 根均量的 1.2 倍。
- 做空規則：收盤價 < EMA20 < EMA50；RSI14 為 30–45；成交量條件相同。
- 使用已收盤 K 線，不使用尚未完成的 K 線；不是逐筆或即時盤中突破掃描。
- 如果資料來源的開盤價超出該根高低範圍，但收盤價、成交量與時間仍有效，指標會使用原始收盤價與成交量；K 線圖會跳過該根不一致的蠟燭並顯示數量，不會修改 OHLC 數值。
- 只顯示符合規則的結果，沒有符合時維持空白，不產生任意信心分數。
- 每輪完成後等待至少 60 秒再開始下一輪；數百個合約需要數分鐘，依連線情況可能更久。畫面會顯示進度和個別掃描時間，不保證所有合約同時更新。
- 本機服務將所有上游請求限制為最多約 4 次／秒，並快取相同請求。遇到上游限流會暫緩請求。
- 快取到期使用實際日期時間計算，電腦休眠後也會正確刷新。不同合約請求使用分開的鎖，單一慢回應不會阻塞所有行情。
- 價格與交易對清單分開更新。清單刷新失敗時保留價格顯示，暫停新掃描並自動重試；清單恢復後掃描會繼續。
- 斷線提示區分本機服務未回應、Bitunix 暫時無資料、請求限流、服務忙碌與過期資料。返回分頁或網路恢復時也會重新讀取。
- 行情超過 45 秒未更新、斷線或暫停時，停止顯示有效交易訊號。個別掃描結果 10 分鐘後失效。
- 資料缺少、K 線不足或不連續時顯示待掃描／資料不足；不以其他交易所或模擬數值替代。

## 圖表與訊號版面

- Price Action 圖表橫跨完整內容寬度，訊號區位於圖表下方。訊號沿用 Market Pulse 的黑綠卡片樣式，桌面每列四張、平板兩張、手機一張；不再使用側欄捲動清單。
- 價格圖表下方顯示真實 K 線成交量，以及最新價格、24 小時漲跌、成交額、RSI14、EMA20 與 EMA50。技術指標依目前圖表週期計算。
- 點擊訊號可檢視該交易對的圖表，保留目前圖表週期。
- 手機使用單欄排列，行情摘要改為兩欄。

## 其他面板

- BTC 市占率維持 TradingView `CRYPTOCAP:BTC.D` 嵌入圖表，需要連網。
- 資金費率每 60 秒更新（戰情室開啟時），顯示 Bitunix `fundingRate` 原始值並清楚標記；因官方文件未明確定義回傳單位，不自行換算百分比。
- OI、CVD 與清算沒有接入可驗證的資料來源，維持無資料，不再顯示合成圖表。
- 區間高低點為掃描週期最近 20 根已收盤 K 線的最高與最低價。
- 手動持倉／計畫／檢討仍為瀏覽器本機記錄，不會同步交易所或送出訂單。

## 運行範圍與成本

行情更新與規則掃描都由程式執行，不會呼叫 OpenAI 或其他 AI 模型，因此不消耗 AI Token。資料來源本身的使用條款與限制另計。

這是本機版本：必須保持頁面與背景行情服務運行、電腦保持喚醒並連網。背景服務不會因關閉啟動檔的終端機視窗而停止，但重新開機後仍需再執行啟動檔。瀏覽器背景分頁可能限制計時器；關閉頁面、停止背景服務或電腦休眠就不會繼續掃描。不包含雲端常駐、推播通知或自動交易。

## 資料來源

- [Bitunix Tickers](https://www.bitunix.com/api-docs/futures/market/get_tickers.html)
- [Bitunix Trading Pairs](https://www.bitunix.com/api-docs/futures/market/get_trading_pairs.html)
- [Bitunix Kline](https://www.bitunix.com/api-docs/futures/market/get_kline.html)
- [Bitunix Funding Rate](https://www.bitunix.com/api-docs/futures/market/get_funding_rate.html)
- [TradingView BTC.D](https://www.tradingview.com/symbols/BTC.D/)

## Windows / Linux

安裝 Python 3，在專案資料夾執行 `python server.py`（Windows）或 `python3 server.py`（Linux），再開啟 `http://127.0.0.1:8765/`。使用此方式需保持啟動服務的終端機開啟。

## English quick start

Install Python 3, double-click `Start-VYRA.command` on macOS (or run `python3 server.py`), and open `http://127.0.0.1:8765/` in Chrome. The launcher starts the service in the background; closing its terminal window will not stop it. Keep the page and service running. Relaunch after restarting the computer. The UI supports English (US) and Traditional Chinese. Live prices poll every 10 seconds; closed-candle charts every 15 seconds. All open USDT futures are scanned in rotation using the documented EMA/RSI/volume rules. No AI calls, account keys, or orders are involved. Closing the page or sleeping the computer stops scans.

This repository shares source code. GitHub Pages cannot run the Python market relay. Download and run locally, or deploy the frontend and backend to a suitable server. No third-party Python packages are required.

## Verification

- Real Bitunix endpoint discovery, price polling, OHLC charts and computed scan results.
- Bilingual controls, pause/resume, stale/disconnected state and missing derivatives.
- Scanner unit tests: `node tests/test-scanner.cjs` (Node.js only needed for this test).
- Relay unit tests: `python3 -m unittest discover -s tests -p 'test_*.py'`.
