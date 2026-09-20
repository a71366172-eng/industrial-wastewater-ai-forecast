"""Safe ingestion helpers for MOENV EMS_S_03 reporting data."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import median
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


API_ENDPOINT = 'https://data.moenv.gov.tw/api/v2/EMS_S_03'
PARAMETER_NAMES = {
    '化學需氧量': 'COD',
    '懸浮固體': 'SS',
    '懸浮固體物': 'SS',
    '氫離子濃度指數': 'pH',
    'PH': 'pH',
    'COD': 'COD',
    'SS': 'SS',
}


def build_api_url(
    api_key: str,
    *,
    offset: int = 0,
    limit: int = 1000,
    output_format: str = 'json',
    year_month: str | None = None,
) -> str:
    if not api_key or not api_key.strip():
        raise ValueError('MOENV API key is required')
    if offset < 0 or limit < 1 or limit > 1000:
        raise ValueError('offset must be nonnegative and limit must be 1–1000')
    if output_format not in {'json', 'csv', 'xml'}:
        raise ValueError('format must be json, csv, or xml')
    params = {
        'format': output_format,
        'offset': str(offset),
        'limit': str(limit),
        'api_key': api_key.strip(),
    }
    if year_month:
        params['year_month'] = year_month
    return f'{API_ENDPOINT}?{urlencode(params)}'


def redact_api_url(url: str) -> str:
    parts = urlsplit(url)
    query = [('api_key', '***') if key.lower() == 'api_key' else (key, value) for key, value in parse_qsl(parts.query)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _casefold_record(record: dict) -> dict[str, object]:
    return {str(key).upper(): value for key, value in record.items()}


def _text(value: object) -> str:
    return '' if value is None else str(value).strip()


def _number(value: object) -> float | None:
    text = _text(value)
    if not text or text.upper() in {'NA', 'N/A', 'NULL', '?'}:
        return None
    return float(text.replace(',', '.'))


def _parameter(value: object) -> str:
    text = _text(value)
    normalized = text.upper().replace('（', '(').replace('）', ')')
    for name, code in PARAMETER_NAMES.items():
        if name.upper() in normalized:
            return code
    return text


def normalize_api_record(record: dict) -> dict:
    source = _casefold_record(record)
    return {
        'plant_id': _text(source.get('EMS_NO')),
        'facility_name': _text(source.get('FAC_NAME')),
        'address': _text(source.get('ADDRESS')),
        'permit_id': _text(source.get('PER_NO')),
        'discharge_point': _text(source.get('LET')),
        'receiving_water': _text(source.get('LET_WATERTYPE')),
        'period_start': _text(source.get('EMI_SDATE')),
        'period_end': _text(source.get('EMI_EDATE')),
        'discharge_volume': _number(source.get('EMI_WATER')),
        'parameter': _parameter(source.get('EMI_ITEM')),
        'value': _number(source.get('EMI_VALUE')),
        'unit': _text(source.get('EMI_UNITS')),
        'source': 'MOENV EMS_S_03',
        'temporal_resolution': 'reporting_period',
    }


def fetch_api_page(api_key: str, *, offset: int = 0, limit: int = 1000, timeout: int = 60) -> list[dict]:
    url = build_api_url(api_key, offset=offset, limit=limit)
    request = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'wastewater-ai-research/1.0'})
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode('utf-8-sig'))
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = payload.get('records') or payload.get('data') or payload.get('result', {}).get('records') or []
    else:
        raise ValueError('unsupported MOENV API response')
    if not isinstance(records, list):
        raise ValueError('MOENV API records field is not a list')
    return [normalize_api_record(record) for record in records if isinstance(record, dict)]


def load_csv_records(path: str | Path) -> list[dict]:
    source = Path(path)
    with source.open('r', encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError('EMS_S_03 CSV has no header')
        required = {'EMS_NO', 'EMI_ITEM', 'EMI_VALUE', 'EMI_UNITS'}
        available = {name.upper() for name in reader.fieldnames}
        missing = sorted(required - available)
        if missing:
            raise ValueError('EMS_S_03 CSV missing columns: ' + ', '.join(missing))
        return [normalize_api_record(row) for row in reader]

def download_records(
    api_key: str,
    *,
    page_size: int = 1000,
    max_pages: int = 100,
    fetcher=None,
) -> list[dict]:
    if page_size < 1 or page_size > 1000:
        raise ValueError('page_size must be 1–1000')
    if max_pages < 1:
        raise ValueError('max_pages must be positive')
    page_fetcher = fetch_api_page if fetcher is None else fetcher
    records: list[dict] = []
    for page in range(max_pages):
        batch = page_fetcher(api_key, offset=page * page_size, limit=page_size)
        records.extend(batch)
        if len(batch) < page_size:
            break
    return records

def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def aggregate_public_summary(records: Iterable[dict]) -> dict:
    groups: dict[tuple[str, str], list[float]] = {}
    for record in records:
        value = record.get('value')
        parameter = _text(record.get('parameter'))
        unit = _text(record.get('unit'))
        if parameter not in {'COD', 'SS', 'pH'} or not isinstance(value, (int, float)):
            continue
        groups.setdefault((parameter, unit), []).append(float(value))
    parameters = {}
    for (parameter, unit), values in sorted(groups.items()):
        parameters[parameter] = {
            'count': len(values),
            'unit': unit,
            'minimum': min(values),
            'median': median(values),
            'p90': _percentile(values, 0.9),
            'maximum': max(values),
        }
    return {
        'schema_version': '1.0',
        'source': 'MOENV EMS_S_03',
        'temporal_resolution': 'reporting_period',
        'privacy': 'aggregated_no_facility_identity',
        'parameters': parameters,
        'limitations': [
            '申報期間資料不是逐時感測資料',
            '不可單獨用於提前數小時預報',
            '公開摘要不含事業名稱、地址、統編、許可證號或管制編號',
        ],
    }
