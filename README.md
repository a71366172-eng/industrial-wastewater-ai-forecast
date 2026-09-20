# 工業廢水放流水 AI 預報

本專案以臺灣化工業放流水法規限值為核心，利用進水 pH、導電度、SS 與 COD 預測放流水 SS、COD，並顯示相對於適用限值的餘裕及預警狀態。

目前成果屬研究原型。正式合規仍須依工廠所在地、排放去向、地方加嚴、環評、總量管制及有效水污染防治許可內容判定，並以合格採樣檢測結果為準。

## 目前版本

- 主站：法規導向 v4。
- 預設法規設定：化工業直接排放至地面水體之中央附表四基準。
- pH：6.0–9.0。
- SS：30 mg/L。
- COD：100 mg/L。
- SS-S 模型：尚未優於中位數基準，不可部署。
- DQO-S／COD-S 模型：小幅優於中位數基準，仍須臺灣化工廠外部驗證。
- pH：尚未建立可信的放流水模型。

正式計畫請參閱 [專案計畫書 v3：法規限值導向](專案計畫書-v3-法規限值導向.md)。

## 本機位置與預覽

主要工作目錄：

~~~text
D:\AI\化工\工業廢水放流水AI預報
~~~

啟動網站：

~~~powershell
py -3 -m http.server 4173 --directory frontend
~~~

開啟 <http://127.0.0.1:4173/>。

## 測試與產物驗證

~~~powershell
npm test
py -3 -m pipeline.verify_effluent_v4
py -3 validate_real_data.py data/templates/chemical_plant_training_template.csv
~~~

重新訓練公開資料原型：

~~~powershell
py -3 train_effluent_v4.py
~~~

模型產物位於 frontend/public/data/effluent-model-v4.json。訓練採時間順序前 80%／後 20% 切分，並與訓練資料中位數基準比較。

## 真實資料

實廠 CSV 範本位於 data/templates/chemical_plant_training_template.csv。

欄位包含進出水 pH、導電度、SS、COD、流量、投藥、曝氣、污泥濃度、時間與品質旗標。正式提前預報需要逐時資料及正確的水力停留時間；環境部 EMS_S_03 申報資料可作為臺灣濃度分布與外部檢查資料，但時間粒度不足以單獨支撐逐時預報。

## 目錄

- frontend/：GitHub Pages 靜態網站。
- frontend/src/effluent.js：瀏覽器濃度預測與限值判讀。
- frontend/public/data/legal-profiles.json：版本化法規設定檔。
- frontend/public/data/effluent-model-v4.json：SS-S／COD-S 模型產物。
- pipeline/compliance.py：Python 法規判讀核心。
- pipeline/real_data.py：實廠與環境部申報資料驗證。
- pipeline/verify_effluent_v4.py：部署前產物重現檢查。
- .github/workflows/：CI 與 GitHub Pages 部署。

## GitHub Pages

deploy.yml 會在發布前：

1. 安裝 requirements.txt。
2. 執行前端與 Python 測試。
3. 驗證既有效率模型。
4. 重算並核對 SS-S／COD-S 模型。
5. 檢查化工業 pH、SS、COD 法規設定與官方來源。
6. 將 frontend/ 發布至 GitHub Pages。

GitHub 儲存庫建立後，將 Pages 的 Source 設為 GitHub Actions。本專案不會把 API key、.env、私有資料、虛擬環境或快取提交至 Git。

## 雲端同步

Windows 排程「化工AI專案雲端同步」每 10 分鐘將 D: 工作目錄的新增或變更檔案備份至 Google Drive 原專案位置。同步不傳播刪除，以避免本機誤刪同步到雲端。

## 環境部 EMS_S_03 真實申報資料

官方資料頁：<https://data.moenv.gov.tw/dataset/detail/EMS_S_03>

目前可直接使用官方資料頁的公開預覽端點，免 API Key 擷取最新批次。預設會在沒有金鑰時使用此模式：

~~~powershell
py -3 fetch_moenv_ems.py --mode public-preview --page-size 1000 --max-pages 5
~~~

目前網站使用最新 5,000 筆明細產生匿名摘要，呈現 COD、SS、pH 的樣本數、中位數與 P90。這是依官方預覽排序取得的最新批次，不是 191 萬筆全資料母體，也不是化工業專屬樣本，因此不直接拿來訓練逐時預報模型。網站同時提供依申報截止日聚合的 COD、SS、pH 中位數趨勢圖，以及化工業中央基準情境比較；兩者都只供資料探索，不代表個別事業合規判定。

若已在環境部平臺註冊取得 API Key，可改用會員 API。金鑰只透過環境變數傳入：

~~~powershell
$env:MOENV_API_KEY = '你的金鑰'
py -3 fetch_moenv_ems.py --mode api-key
~~~

也可以從官方頁面手動下載 CSV 後匯入：

~~~powershell
py -3 import_moenv_csv.py .\path\to\EMS_S_03.csv
~~~

兩種模式都會：

- 將含事業識別資訊的正規化原始資料寫入被 Git 排除的 data/raw/moenv/。
- 只將 COD、SS、pH 的筆數、最小值、中位數、P90 與最大值寫入前端公開摘要。
- 明確標記資料時間粒度為 reporting_period，不把申報資料當成逐時感測資料。
- 不公開事業名稱、地址、統編、許可證號或管制編號。
