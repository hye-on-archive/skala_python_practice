"""
저장/성능 비교 모듈
- pydantic 모델 리스트를 pandas DataFrame으로 변환해 CSV / Parquet
  두 포맷으로 저장하고, 각각의 쓰기/읽기 소요 시간(ms)을 측정해 비교한다.
- 실측 데이터가 적을 때는 Parquet의 이점이 잘 드러나지 않으므로,
  동일 스키마를 복제한 대용량 데이터로도 한 번 더 비교해 보여준다.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pydantic import BaseModel


@dataclass
class IOBenchmark:
    """하나의 포맷(csv/parquet)에 대한 쓰기/읽기 성능 측정 결과 (시간 단위: ms)."""

    fmt: str
    write_ms: float
    read_ms: float
    file_size_bytes: int


def models_to_dataframe(records: list[BaseModel]) -> pd.DataFrame:
    """pydantic 모델 리스트 -> pandas DataFrame 변환."""
    return pd.DataFrame([r.model_dump() for r in records])


def warmup_io_engines(out_dir: Path) -> None:
    """CSV/Parquet 벤치마크를 실행하기 전에 한 번 호출한다.

    프로세스에서 pandas.to_parquet()를 처음 호출하면 pyarrow 라이브러리
    로딩·메모리풀/코덱 초기화 등 "콜드 스타트" 비용이 몇 ms~수십 ms 더 붙는다.
    이 비용이 실제 벤치마크 타이밍에 섞이면 포맷 간 공정한 비교가 안 되므로,
    더미 데이터로 미리 한 번 쓰고 읽어서 라이브러리를 예열(warm-up)해 둔다.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    dummy = pd.DataFrame({"a": [1, 2, 3], "b": [1.1, 2.2, 3.3]})

    tmp_csv = out_dir / ".warmup.csv"
    tmp_parquet = out_dir / ".warmup.parquet"

    dummy.to_csv(tmp_csv, index=False)
    pd.read_csv(tmp_csv)
    dummy.to_parquet(tmp_parquet, index=False)
    pd.read_parquet(tmp_parquet)

    tmp_csv.unlink(missing_ok=True)
    tmp_parquet.unlink(missing_ok=True)


def save_and_benchmark(
    df: pd.DataFrame, out_dir: Path, base_name: str
) -> list[IOBenchmark]:
    """DataFrame을 CSV와 Parquet 두 포맷으로 저장하고 읽기/쓰기 시간(ms)을 측정한다.

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
    write_csv_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    _ = pd.read_csv(csv_path)
    read_csv_ms = (time.perf_counter() - t0) * 1000

    results.append(
        IOBenchmark(
            fmt="csv",
            write_ms=write_csv_ms,
            read_ms=read_csv_ms,
            file_size_bytes=csv_path.stat().st_size,
        )
    )

    # ---- Parquet ----
    parquet_path = out_dir / f"{base_name}.parquet"
    t0 = time.perf_counter()
    df.to_parquet(parquet_path, index=False)
    write_parquet_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    _ = pd.read_parquet(parquet_path)
    read_parquet_ms = (time.perf_counter() - t0) * 1000

    results.append(
        IOBenchmark(
            fmt="parquet",
            write_ms=write_parquet_ms,
            read_ms=read_parquet_ms,
            file_size_bytes=parquet_path.stat().st_size,
        )
    )

    return results


def simulate_large_dataset(df: pd.DataFrame, target_rows: int = 72_000) -> pd.DataFrame:
    """실측 데이터(예: 72행)만으로는 Parquet의 이점이 잘 드러나지 않으므로,
    같은 스키마의 행을 반복 복제해 대용량(target_rows) 상황을 시뮬레이션한다.

    실제 API 호출 없이, 이미 검증을 통과한 데이터의 스키마/분포를 그대로 재사용한다.
    """
    if len(df) == 0:
        raise ValueError("빈 데이터프레임은 대용량 시뮬레이션에 사용할 수 없습니다")
    repeat = -(-target_rows // len(df))  # ceil division
    big = pd.concat([df] * repeat, ignore_index=True).iloc[:target_rows].reset_index(drop=True)
    return big


def _winner(csv_value: float, parquet_value: float) -> str:
    """더 작은(더 빠르거나 더 작은) 쪽의 포맷 이름에 ↑ 표시를 붙여 반환한다."""
    return "CSV↑" if csv_value <= parquet_value else "Parquet↑"


def print_benchmark_table(title: str, benchmarks: list[IOBenchmark]) -> None:
    """CSV vs Parquet 성능 비교 결과를 정렬된 표 형태로 출력한다 (ms 단위)."""
    csv_b = next(b for b in benchmarks if b.fmt == "csv")
    parquet_b = next(b for b in benchmarks if b.fmt == "parquet")

    rows: list[tuple[str, float, float]] = [
        ("쓰기(ms)", csv_b.write_ms, parquet_b.write_ms),
        ("읽기(ms)", csv_b.read_ms, parquet_b.read_ms),
        ("크기(byte)", float(csv_b.file_size_bytes), float(parquet_b.file_size_bytes)),
    ]

    if title:
        print(f"    {title}")
    print(f"    {'항목':<12}{'CSV':>12}{'Parquet':>12}   비교")
    print("    " + "-" * 46)
    for label, csv_val, parquet_val in rows:
        print(
            f"    {label:<12}{csv_val:>12.3f}{parquet_val:>12.3f}   "
            f"{_winner(csv_val, parquet_val)}"
        )


def save_meta_json(out_dir: Path, meta: dict) -> Path:
    """스칼라(1건짜리) 검증 데이터(국가정보/IP정보)는 성능비교 대상이 아니므로
    별도로 meta.json 하나에 모아 저장한다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "meta.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
