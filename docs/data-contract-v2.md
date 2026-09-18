# UCI 四輸入模型資料契約 v2.0

網站讀取 `frontend/public/data/uci-model.json`。此檔由 `python -m pipeline.train_uci` 產生，不手動修改。

## 來源與範圍

- 來源：UCI Water Treatment Plant。
- 資料：527 筆都市污水廠每日紀錄；原始檔另含空白行，解析時忽略。
- 輸入：`PH-E`、`COND-E`、`SS-E`、`DQO-E`。
- 目標：`RD-SS-P`，初沉池 SS 去除效率。
- 模式：`historical-research`。這不是即時工業現場資料。

## 根層欄位

| 欄位 | 說明 |
|---|---|
| `schema_version` | 固定為 `2.0` |
| `generated_at` | UTC 產生時間 |
| `mode` | 固定為 `historical-research` |
| `source` | 來源名稱、網址與適用範圍 |
| `features` | 四項輸入的欄名、標籤、單位與開發資料範圍 |
| `target` | 目標欄位、單位與研究門檻 |
| `split` | 時間序列的訓練、驗證與測試筆數 |
| `data_report` | 原始列數、可用列數與缺值統計 |
| `model` | Ridge 模型的補值中位數、平均、尺度、係數與截距 |
| `metrics` | 保留測試集的 MAE、RMSE、R² 與基準比較 |
| `test_cases` | 測試期日期、四項輸入、實際效率及模型估計 |

## 瀏覽器推論

對每個輸入欄位先計算 `(值 - mean) / scale`，乘上相應 coefficient，四項加總後加上 intercept。缺值不可由表單送出；模型內的訓練中位數只供資料管線與程式契約保底使用。超出 `features[].min/max` 的值可以計算，但介面必須標示為外推。

`target.warning_threshold` 是研究門檻，不是法規限值。低於門檻只觸發人工複測與製程檢查提醒，不能轉換成自動加藥量或合規判定。
