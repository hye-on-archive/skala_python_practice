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


def extract_korea_country(raw: dict[str, Any]) -> tuple[CountryInfo | None, list[str]]:
    """countries.dev의 단일 국가 조회 응답(/alpha/KOR)에서 대한민국 정보를 검증한다.

    주의: restcountries.com v3.1은 서비스 종료, v5는 유료 API 키(무료 티어 월 500회 제한)가
    필요해 무료 대체 API인 countries.dev/alpha/{code}를 사용한다. 이 엔드포인트는
    "국가 리스트"가 아니라 조회한 나라 하나를 바로 반환하므로, 예전처럼 목록에서
    KR을 검색하는 과정이 필요 없다.
    """
    errors: list[str] = []

    if not isinstance(raw, dict):
        errors.append(f"예상치 못한 응답 타입입니다: {type(raw).__name__}")
        return None, errors

    try:
        country = CountryInfo(
            name=raw.get("name", ""),
            capital=raw.get("capital"),
            region=raw.get("region", ""),
            population=raw.get("population", 0),
            area=raw.get("area"),
            alpha2_code=raw.get("alpha2Code", ""),
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
