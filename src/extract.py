"""
raw JSON -> pydantic 모델 추출/검증 모듈
- 각 API의 원본 JSON 구조에서 필요한 필드만 뽑아 pydantic 모델로 검증한다.
- 타입/범위 오류가 나면 ValidationError를 잡아서 원인을 기록하고
  전체 파이프라인이 죽지 않도록 처리한다.
"""
from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from src.models import CountryInfo, IPGeoInfo, WeatherHourlyRecord


def extract_weather_records(raw: dict[str, Any]) -> tuple[list[WeatherHourlyRecord], list[str]]:
    """open-meteo 응답(raw)에서 시간대별 기온/강수확률 레코드를 추출한다.

    Returns:
        (검증 통과 레코드 리스트, 검증 실패 사유 리스트)
    """
    valid: list[WeatherHourlyRecord] = []
    errors: list[str] = []

    hourly = raw.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    probs = hourly.get("precipitation_probability", [])

    for idx, (t, temp, prob) in enumerate(zip(times, temps, probs)):
        try:
            record = WeatherHourlyRecord(
                time=t, temperature_2m=temp, precipitation_probability=prob
            )
            valid.append(record)
        except ValidationError as exc:
            msgs = "; ".join(e["msg"] for e in exc.errors())
            errors.append(f"index={idx} time={t} error={msgs}")

    return valid, errors


def extract_korea_country(raw: list[dict[str, Any]]) -> tuple[CountryInfo | None, list[str]]:
    """restcountries legacy.json(국가 리스트)에서 대한민국 레코드만 추출한다."""
    errors: list[str] = []

    korea_raw = next(
        (c for c in raw if c.get("alpha2Code") == "KR" or c.get("name") == "Korea (Republic of)"),
        None,
    )
    if korea_raw is None:
        errors.append("대한민국(KR) 데이터를 찾을 수 없습니다")
        return None, errors

    try:
        country = CountryInfo(
            name=korea_raw.get("name", ""),
            capital=korea_raw.get("capital"),
            region=korea_raw.get("region", ""),
            population=korea_raw.get("population", 0),
            area=korea_raw.get("area"),
            alpha2_code=korea_raw.get("alpha2Code", ""),
        )
        return country, errors
    except ValidationError as exc:
        errors.append(str(exc))
        return None, errors


def extract_ip_info(raw: dict[str, Any]) -> tuple[IPGeoInfo | None, list[str]]:
    """ip-api 응답에서 지역 정보 필드를 추출한다."""
    errors: list[str] = []
    try:
        info = IPGeoInfo(
            query=raw.get("query", ""),
            country=raw.get("country", ""),
            countryCode=raw.get("countryCode", ""),
            region=raw.get("region", ""),
            regionName=raw.get("regionName", ""),
            city=raw.get("city", ""),
            isp=raw.get("isp", ""),
            lat=raw.get("lat", 0.0),
            lon=raw.get("lon", 0.0),
        )
        return info, errors
    except ValidationError as exc:
        errors.append(str(exc))
        return None, errors
