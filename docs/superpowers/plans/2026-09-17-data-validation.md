# 環境部公開資料驗證管線實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 建立一個不會誤認測項、可檢查環境部資料欄位並輸出驗證報告的 Python 管線，作為真實資料接入前的安全關卡。

**Architecture:** `pipeline/cwms.py` 只負責 URL 組合、資料形狀抽取、欄位驗證與時間／數值正規化；`pipeline/validate.py` 負責命令列讀檔與輸出報告。API 金鑰只由 `MOENV_API_KEY` 環境變數提供；沒有測項對照時，管線只能產生報告，不能產生前端觀測快照。

**Tech Stack:** Python 3.11 標準函式庫、`unittest`、JSON、CSV、urllib。

## Global Constraints

- 官方資料集的 `m_val` 不得直接標成 COD、SS、pH 或其他測項。
- `DESP` 是監測位置描述；沒有官方測項對照時，`metric_mapping_status` 必須是 `unresolved`。
- API 金鑰只從 `MOENV_API_KEY` 讀取，不能寫入程式、測試輸出、前端快照或日誌。
- 真實資料抓取失敗時，要保留可診斷錯誤，不用示範資料代替。
- 正規化時間必須含 `+08:00` 臺灣時區；無法解析的值列入錯誤。

---

### Task 1: 建立 CWMS 欄位驗證純函式

**Files:**
- Create: `pipeline/__init__.py`
- Create: `pipeline/cwms.py`
- Create: `pipeline/tests/test_cwms.py`

**Interfaces:**
- `build_api_url(dataset_code, api_key, limit=1000, sort='ImportDate desc') -> str`
- `extract_rows(payload) -> list[dict]`
- `validate_rows(rows, metric_mapping=None) -> ValidationReport`
- `normalize_row(row, metric_mapping) -> dict`

- [x] **Step 1: Write the failing tests**

```python
from urllib.parse import parse_qs, urlparse

def test_api_url_requires_an_explicit_key():
    with pytest.raises(ValueError, match='MOENV_API_KEY is required'):
        build_api_url('wqx_p_50', '')

def test_unresolved_metric_mapping_cannot_be_published():
    report = validate_rows([complete_row()], metric_mapping=None)
    assert report.can_publish is False
    assert report.metric_mapping_status == 'unresolved'
    assert 'metric mapping is unresolved' in report.errors

def test_normalize_row_requires_confirmed_metric_mapping():
    with pytest.raises(MetricMappingError):
        normalize_row(complete_row(), None)
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest discover -s pipeline/tests -p "test_*.py" -v`

Expected: FAIL because `pipeline/cwms.py` and its interfaces do not exist.

- [x] **Step 3: Implement the minimal pure functions**

Use only the 16 official fields (`cno`, `abbr`, `dp_no`, `desp`, `m_date`, `m_time`, `m_val`, `status`, `unit`, `std1`, `std2`, `std_s`, `twd97x`, `twd97y`, `wgs84x`, `wgs84y`). Accept JSON payloads that are a list or a dict containing a list under `data`, `records`, or `result`; reject unknown shapes. Parse numeric `m_val`, combine `m_date` and `m_time` with `+08:00`, and require an explicit mapping containing `metric_id` and `metric_name` before normalizing.

- [x] **Step 4: Run focused and full Python tests**

Run: `python -m unittest discover -s pipeline/tests -p "test_*.py" -v`

Expected: PASS with all tests green and no API request.

### Task 2: Add a safe validation CLI and documentation

**Files:**
- Create: `pipeline/validate.py`
- Create: `pipeline/README.md`
- Modify: `README.md`
- Modify: `.gitignore`

- [x] **Step 1: Write a failing CLI contract test**

Add a test that runs the module against a temporary JSON fixture and asserts the report contains `can_publish: false` when no metric mapping is provided.

- [x] **Step 2: Run it to verify the CLI is missing**

Run: `python -m unittest discover -s pipeline/tests -p "test_*.py" -v`

Expected: FAIL because `pipeline.validate` is not available.

- [x] **Step 3: Implement the CLI**

Support `--input`, `--output`, `--metric-id`, and `--metric-name`. Read only local JSON, validate rows, write a UTF-8 report, and exit with status 2 when the report cannot publish. Never print row values or secrets. Document the official endpoint `https://data.moenv.gov.tw/api/v2/wqx_p_50`, the required `MOENV_API_KEY`, and the unresolved measurement-item limitation.

- [x] **Step 4: Run CLI tests and a no-secret dry run**

Run: `python -m unittest discover -s pipeline/tests -p "test_*.py" -v`

Expected: PASS. Run the CLI against a test fixture without `MOENV_API_KEY`; it must create a report and must not make a network request.

## Self-review checklist

- [x] A missing API key is an explicit error, not a fallback to demo data.
- [x] A missing metric mapping blocks publication.
- [x] `m_val` is preserved as a numeric value but never assigned a metric name automatically.
- [x] The report contains row counts, missing columns, invalid rows, units, statuses, and mapping status without leaking values or keys.
- [x] Existing frontend tests still pass.

## 實作狀態

離線驗證管線與 CLI 已完成；真實 API 樣本、測項對照與發布延遲仍是下一個外部資料關卡。
