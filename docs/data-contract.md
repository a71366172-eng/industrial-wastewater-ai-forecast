# 前端資料契約 v1.0

第一版網站使用一個快照目錄。`manifest.json` 描述快照，其餘 JSON 透過相對路徑載入。所有時間都必須是含時區的 ISO 8601 字串；缺值使用 `null`。

## manifest.json

必填欄位：

- `schema_version`：契約版本，例如 `1.0`。
- `snapshot_id`：不可變快照識別碼。
- `mode`：`demo`、`historical` 或 `live`；目前只使用 `demo`。
- `generated_at`：快照產生時間。
- `valid_until`：網站停止當前預報顯示的時間。
- `station_id`、`station_name`：監測對象識別與名稱。
- `metric_id`、`metric_name`、`unit`：測項識別、顯示名稱與單位。
- `threshold`：研究警戒值，不等同於法規限值。
- `source`：包含 `name` 與 `url` 的來源說明。
- `observations_path`、`forecasts_path`、`events_path`：同一快照中的相對檔案路徑。

## observations.json

陣列元素包含 `observed_at`、`value`、`unit` 與 `quality_status`。`quality_status` 必須保留來源品質狀態，不可把缺測改成零。

## forecasts.json

陣列元素包含 `issued_at`、`target_start`、`target_end`、`predicted_value` 與 `model_version`。`issued_at` 是實際發布預報的時間；沒有發布時間就不能宣稱提前性。

## events.json

陣列元素包含 `event_id`、`start`、`end`、`type`、`status` 與 `label`。事件是研究警戒事件，必須在介面上與法規違規判定分開。
