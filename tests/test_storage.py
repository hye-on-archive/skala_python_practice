"""CSV/Parquet 저장·벤치마크(storage.py)에 대한 pytest 테스트.

실제 파일 I/O가 발생하므로 pytest 기본 제공 tmp_path 픽스처를 사용해
테스트 실행 후 자동으로 정리되는 임시 디렉터리에서만 파일을 쓰고 읽는다.
"""
import json

import pandas as pd
import pytest

from src.models import WeatherHourlyRecord
from src.storage import (
    models_to_dataframe,
    save_and_benchmark,
    save_meta_json,
    simulate_large_dataset,
)


def _sample_records() -> list[WeatherHourlyRecord]:
    return [
        WeatherHourlyRecord(
            time="2026-07-15T00:00", temperature_2m=24.5, precipitation_probability=10
        ),
        WeatherHourlyRecord(
            time="2026-07-15T01:00", temperature_2m=23.8, precipitation_probability=20
        ),
    ]


def test_save_and_benchmark_writes_and_rereads_csv_and_parquet(tmp_path):
    df = models_to_dataframe(_sample_records())
    benchmarks = save_and_benchmark(df, tmp_path, "weather_test")

    assert {b.fmt for b in benchmarks} == {"csv", "parquet"}
    assert all(b.write_ms >= 0 and b.read_ms >= 0 for b in benchmarks)

    csv_path = tmp_path / "weather_test.csv"
    parquet_path = tmp_path / "weather_test.parquet"
    assert csv_path.exists()
    assert parquet_path.exists()
    assert len(pd.read_csv(csv_path)) == 2
    assert len(pd.read_parquet(parquet_path)) == 2


def test_simulate_large_dataset_repeats_rows_to_target_size():
    df = models_to_dataframe(_sample_records())  # 2행
    big = simulate_large_dataset(df, target_rows=7)
    assert len(big) == 7
    # 원본 스키마(컬럼)는 그대로 유지되어야 한다
    assert list(big.columns) == list(df.columns)


def test_simulate_large_dataset_rejects_empty_dataframe():
    empty_df = pd.DataFrame(columns=["time", "temperature_2m", "precipitation_probability"])
    with pytest.raises(ValueError):
        simulate_large_dataset(empty_df, target_rows=10)


def test_save_meta_json_writes_readable_json(tmp_path):
    meta = {"country": {"name": "Korea (Republic of)"}, "ip": {"query": "8.8.8.8"}}
    path = save_meta_json(tmp_path, meta)

    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == meta
