"""
Day1 종합실습 파이프라인 진입점
1) asyncio.gather()로 3개 API 동시 수집
2) pydantic v2 모델로 스키마/범위 검증
3) 검증 통과 데이터를 CSV/Parquet로 저장하고 성능 비교 (ms 단위)
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from src.collectors import collect_all
from src.extract import extract_ip_info, extract_korea_country, extract_weather_records
from src.storage import (
    models_to_dataframe,
    print_benchmark_table,
    save_and_benchmark,
    save_meta_json,
    simulate_large_dataset,
    warmup_io_engines,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LARGE_DATASET_ROWS = 72_000

# httpx는 "httpx" 로거로 "HTTP Request: GET <url> "HTTP/1.1 200 OK"" 형태를
# INFO 레벨로 남긴다. basicConfig로 핸들러를 붙여야 콘솔에 보인다.
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


def _section(title: str) -> None:
    bar = "=" * 64
    print(f"\n{bar}\n{title}\n{bar}")


async def run_pipeline() -> None:
    _section("Day 1 종합실습 — 수집 · 검증 · 품질 파이프라인")

    # ---------------------------------------------------------------
    _section("1) 비동기 수집 (asyncio.gather · httpx)")
    collected = await collect_all()

    failed = {s: r["_error"] for s, r in collected.items() if r["_error"]}
    if failed:
        print("• 일부 API 수집 실패:")
        for source, err in failed.items():
            print(f"    - {source}: {err}")
    else:
        weather_hours = len(
            collected["open-meteo"]["data"].get("hourly", {}).get("time", [])
        )
        country_name = collected["restcountries"]["data"].get("name", "?")
        ip_query = collected["ip-api"]["data"].get("query", "?")
        ip_city = collected["ip-api"]["data"].get("city", "?")
        print("• 3개 API 동시 수집 완료")
        print(f"    - Open-Meteo   : hourly {weather_hours}건")
        print(f"    - 국가정보     : {country_name} (source=countries.dev)")
        print(f"    - ip-api       : {ip_query} / {ip_city}")

    # ---------------------------------------------------------------
    _section("2) Pydantic v2 스키마 검증")

    weather_records: list = []
    if collected["open-meteo"]["_error"] is None:
        weather_records, weather_errors = extract_weather_records(
            collected["open-meteo"]["data"]
        )
        print(f"• weather : valid {len(weather_records)}건 / errors {len(weather_errors)}건")
        for e in weather_errors:
            print(f"    ! {e}")

    country = None
    if collected["restcountries"]["_error"] is None:
        country, country_errors = extract_korea_country(collected["restcountries"]["data"])
        if country:
            print(f"• country : {country.model_dump()}")
        else:
            print(f"• country : 검증실패 {country_errors}")

    ip_info = None
    if collected["ip-api"]["_error"] is None:
        ip_info, ip_errors = extract_ip_info(collected["ip-api"]["data"])
        if ip_info:
            print(f"• ip      : {ip_info.model_dump()}")
        else:
            print(f"• ip      : 검증실패 {ip_errors}")

    # ---------------------------------------------------------------
    _section("3) CSV · Parquet 저장 및 성능 비교")

    if weather_records:
        # pyarrow 최초 로딩 비용이 첫 벤치마크 타이밍에 섞이지 않도록 예열
        warmup_io_engines(DATA_DIR)

        df = models_to_dataframe(weather_records)

        benchmarks = save_and_benchmark(df, DATA_DIR, "weather")
        print(f"• 저장 완료: weather.csv, weather.parquet (실측 {len(df)}행)")
        print_benchmark_table("", benchmarks)

        big_df = simulate_large_dataset(df, target_rows=LARGE_DATASET_ROWS)
        big_benchmarks = save_and_benchmark(big_df, DATA_DIR, "weather_large")
        print(f"\n• 대용량 시뮬레이션 ({len(big_df):,}행):")
        print_benchmark_table("", big_benchmarks)

    meta = {}
    if country:
        meta["country"] = country.model_dump()
    if ip_info:
        meta["ip"] = ip_info.model_dump()
    if meta:
        save_meta_json(DATA_DIR, meta)
        print("\n• 국가·IP 검증 데이터 저장 → meta.json")

    _section("파이프라인 완료 ✅")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
