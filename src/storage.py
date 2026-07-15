"""
저장/성능 비교 모듈
- pydantic 모델 리스트를 pandas DataFrame으로 변환해 CSV / Parquet
  두 포맷으로 저장하고, 각각의 쓰기/읽기 소요 시간을 측정해 비교한다.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pydantic import BaseModel


@dataclass
class IOBenchmark:
    """하나의 포맷(csv/parquet)에 대한 쓰기/읽기 성능 측정 결과."""

    fmt: str
    write_seconds: float
    read_seconds: float
    file_size_bytes: int


def models_to_dataframe(records: list[BaseModel]) -> pd.DataFrame:
    """pydantic 모델 리스트 -> pandas DataFrame 변환."""
    return pd.DataFrame([r.model_dump() for r in records])


def save_and_benchmark(
    df: pd.DataFrame, out_dir: Path, base_name: str
) -> list[IOBenchmark]:
    """DataFrame을 CSV와 Parquet 두 포맷으로 저장하고 읽기/쓰기 시간을 측정한다.

    Args:
        df: 저장할 데이터프레임
        out_dir: 저장 디렉터리
        base_name: 확장자를 뺀 파일 베이스 이름 (예: "weather")

    Returns:
        [csv 결과, parquet 결과] 리스트
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[IOBenchmark] = []

    # ---- CSV ----
    csv_path = out_dir / f"{base_name}.csv"
    t0 = time.perf_counter()
    df.to_csv(csv_path, index=False)
    write_csv_sec = time.perf_counter() - t0

    t0 = time.perf_counter()
    _ = pd.read_csv(csv_path)
    read_csv_sec = time.perf_counter() - t0

    results.append(
        IOBenchmark(
            fmt="csv",
            write_seconds=write_csv_sec,
            read_seconds=read_csv_sec,
            file_size_bytes=csv_path.stat().st_size,
        )
    )

    # ---- Parquet ----
    parquet_path = out_dir / f"{base_name}.parquet"
    t0 = time.perf_counter()
    df.to_parquet(parquet_path, index=False)
    write_parquet_sec = time.perf_counter() - t0

    t0 = time.perf_counter()
    _ = pd.read_parquet(parquet_path)
    read_parquet_sec = time.perf_counter() - t0

    results.append(
        IOBenchmark(
            fmt="parquet",
            write_seconds=write_parquet_sec,
            read_seconds=read_parquet_sec,
            file_size_bytes=parquet_path.stat().st_size,
        )
    )

    return results


def print_benchmark_table(name: str, benchmarks: list[IOBenchmark]) -> None:
    """성능 비교 결과를 보기 좋은 표 형태로 출력한다."""
    print(f"\n=== {name} 저장 성능 비교 ===")
    print(f"{'포맷':<10}{'쓰기(s)':<12}{'읽기(s)':<12}{'파일크기(byte)':<15}")
    for b in benchmarks:
        print(
            f"{b.fmt:<10}{b.write_seconds:<12.6f}{b.read_seconds:<12.6f}{b.file_size_bytes:<15}"
        )
