# 公開資料驗證管線

這個目錄負責在真實資料接入前檢查環境部 CWMS（重大點源放流水自動連續監測）資料。管線目前只讀取本機 JSON，不會在沒有明確授權與金鑰時自動抓取官方 API。

官方候選端點：

`https://data.moenv.gov.tw/api/v2/wqx_p_50`

環境部端點需要 `MOENV_API_KEY`。金鑰只可放在本機環境變數或 GitHub Actions Secrets，不可寫入程式、測試資料、前端快照或日誌。本階段尚未在程式中自動使用金鑰，避免誤抓與洩漏。

## 驗證本機檔案

```powershell
python -m pipeline.validate --input .\path\to\rows.json --output .\artifacts\validation-report.json
```

沒有測項對照時，命令會建立報告並回傳狀態碼 2；這是預期的資料關卡結果，不是程式崩潰。只有確認 `m_val` 對應到哪一個測項後，才可加入：

```powershell
python -m pipeline.validate `
  --input .\path\to\rows.json `
  --output .\artifacts\validation-report.json `
  --metric-id cod `
  --metric-name '化學需氧量（COD）'
```

報告只包含列數、缺少欄位、錯誤列索引、單位、狀態與測項對照狀態，不包含 `m_val` 原始值或 API 金鑰。即使加入 mapping，也必須另行核對官方測項定義、資料時間、缺值與發布延遲；通過報告不等同於模型可用。
