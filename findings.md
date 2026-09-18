# 研究發現

查核日期：2026-09-17。

- 官方提供放流水自動連續監測與歷史查詢入口：https://water.moenv.gov.tw/Public/CHT/WaterEnv/wasteW_monitor.aspx
- 河川水質定期採樣資料不適合作為工業放流口小時預報的替代：https://data.gov.tw/dataset/6078
- 仍需確認歷史批次取得方式、測項辨識及實際時間間隔；資料集更新頻率不等於採樣頻率。

## 官方資料集查核

- 桃園：https://data.gov.tw/dataset/35108 及 https://data.moenv.gov.tw/dataset/detail/WQX_P_50 。官方提供 CSV、JSON、XML，更新頻率為不定期；政府資料開放授權條款第1版。未實際取得資料檔，不據此宣稱資料可直接建模。
- 高雄：https://data.moenv.gov.tw/dataset/detail/WQX_P_60 。候選即時資料，更新頻率為不定期。
- 公開欄位包含 CNO、ABBR、DP_NO、DESP、M_DATE、M_TIME、M_VAL、STATUS、UNIT、STD1、STD2、STD_S 及座標。缺少獨立測項代碼／名稱，DESP 定義為監測位置中文描述；不能僅依 mg/L 區分 COD 與 SS。
- 歷史查詢官方手冊：https://cwmspublic.moenv.gov.tw/images/資訊公開查詢系統操作手冊.pdf 。歷史日趨勢為正常操作且上傳紀錄的小時平均值，手冊描述自2015-01-01起查詢；不代表每廠各測項皆完整。手冊未證實歷史批次下載或 API，部分查詢含驗證碼。
- 河川資料為月採樣且通常隔月提供，不作本題小時預報訓練資料。

## 證據層級與設計結論

本次查核官方網頁與操作手冊，尚未取得完整訓練資料或實際監測樣本。主要未知為批次歷史取得、測項映射、狀態定義及真實發布延遲。計畫書把這些列為第2週關卡；1／3小時預測、90天、80%完整率及效能目標均為研究設計，不是官方保證。

使用者已回覆確認：預測水質與異常風險。規劃本機原型、12週、先1～3個工業對象。數值預報必要，預警成效驗證依獨立事件數調整。

## 追加研究：前端與GitHub部署（2026-09-17）

- Pages為靜態網站，不執行Python；前端採版本化JSON讀取，計算留在本機或Actions：https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- Pages免費方案與公开儲存庫資格，私人儲存庫不等於網站私人：https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
- Vite需設定正確base和Pages工作流程：https://vite.dev/guide/static-deploy.html
- Actions排程不保證準時，公開儲存庫60天無活動會停用排程：https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- 自訂Pages部署權限：https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- 設計決策：網站為必要成果；批次推論、完整快照與前端一併發布；常駐API列第二階段。時程調整為網站与模型並行，零新增預算為條件式目標。

## v2.0 資料方向查核（2026-09-17）

Kaggle 候選：https://www.kaggle.com/datasets/pamhohhgkgm/water-treatment-plant-data-set ，尚未核對下載檔。
UCI 原始說明：https://archive.ics.uci.edu/dataset/106/water+treatment+plant 。有 PH-E、COND-E、SS-E、DQO-E 四項進水欄位，及效率／出水欄位。此為每日都市污水資料，不能直接證明工業場域適用性或小時級提前量。

選擇效率目標時須區分初沉池 SS 與全廠 SS 去除；出水研究門檻不等於法律合規。無投藥資料，不建立具體劑量建議。每日同列進出水不代表相同水體配對；須確認檢測可用時間與停留時間才能聲稱提前預警。
