import csv

from pipeline.real_data import normalize_moenv_rows, validate_plant_csv


def test_template_is_valid():
    from pathlib import Path
    path = Path("data/templates/chemical_plant_training_template.csv")
    report = validate_plant_csv(path)
    assert report.valid
    assert report.accepted == 1


def test_invalid_quality_row_is_not_used(tmp_path):
    source = tmp_path / "plant.csv"
    header = [
        "timestamp", "plant_id", "influent_ph", "influent_conductivity_us_cm",
        "influent_ss_mg_l", "influent_cod_mg_l", "effluent_ph",
        "effluent_ss_mg_l", "effluent_cod_mg_l", "quality_flag",
    ]
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=header)
        writer.writeheader()
        writer.writerow(dict(zip(header, ["2026-01-01T00:00:00+08:00", "A", 7, 100, 10, 20, 7, 5, 10, "sensor_fault"])))
    report = validate_plant_csv(source)
    assert report.valid is False
    assert report.rejected == 1


def test_moenv_data_remains_reporting_period_data():
    row = {
        "EMS_NO": "A", "PER_NO": "P", "LET": "D01", "LET_WATERTYPE": "河川",
        "EMI_SDATE": "2026-01-01", "EMI_EDATE": "2026-03-31", "EMI_WATER": "100",
        "EMI_ITEM": "化學需氧量", "EMI_VALUE": "72", "EMI_UNITS": "mg/L",
    }
    normalized, report = normalize_moenv_rows([row])
    assert report.accepted == 1
    assert normalized[0]["temporal_resolution"] == "reporting_period"

