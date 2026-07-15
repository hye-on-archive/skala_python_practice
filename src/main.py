"""
Day1 종합실습 파이프라인 진입점
1) asyncio.gather()로 3개 API 동시 수집
2) pydantic v2 모델로 스키마/범위 검증
3) 검증 통과 데이터를 CSV/Parquet로 저장하고 성능 비교
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from src.collectors import collect_all
from src.extract import extract_ip_info, extract_korea_country, extract_weather_records
from src.storage import models_to_dataframe, print_benchmark_table, save_and_benchmark

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


async def run_pipeline() -> None:
    print("1) 비동기 수집 시작 (open-meteo / restcountries / ip-api 동시 요청)")
    collected = await collect_all()

    for source, result in collected.items():
        status = "OK" if result["_error"] is None else f"FAIL: {result['_error']}"
        print(f"   - {source}: {status}")

    print("\n2) pydantic 스키마 검증")

    # --- 날씨 ---
    weather_records: list = []
    if collected["open-meteo"]["_error"] is None:
        weather_records, weather_errors = extract_weather_records(
            collected["open-meteo"]["data"]
        )
        print(f"   - weather: 검증통과 {len(weather_records)}건, 실패 {len(weather_errors)}건")
        for e in weather_errors:
            print(f"     ! {e}")

    # --- 국가정보(대한민국) ---
    country = None
    if collected["restcountries"]["_error"] is None:
        country, country_errors = extract_korea_country(collected["restcountries"]["data"])
        print(f"   - country: {'검증통과' if country else '검증실패'} {country_errors}")

    # --- IP 지역정보 ---
    ip_info = None
    if collected["ip-api"]["_error"] is None:
        ip_info, ip_errors = extract_ip_info(collected["ip-api"]["data"])
        print(f"   - ip-api: {'검증통과' if ip_info else '검증실패'} {ip_errors}")

    print("\n3) 저장 및 성능 비교 (CSV vs Parquet)")

    if weather_records:
        df = models_to_dataframe(weather_records)
        benchmarks = save_and_benchmark(df, DATA_DIR, "weather")
        print_benchmark_table("weather", benchmarks)

    if country:
        df = models_to_dataframe([country])
        benchmarks = save_and_benchmark(df, DATA_DIR, "country_kr")
        print_benchmark_table("country_kr", benchmarks)

    if ip_info:
        df = models_to_dataframe([ip_info])
        benchmarks = save_and_benchmark(df, DATA_DIR, "ip_geo")
        print_benchmark_table("ip_geo", benchmarks)


if __name__ == "__main__":
    asyncio.run(run_pipeline())
