"""
raw JSON -> pydantic 모델 추출/검증 모듈
- 각 API의 원본 JSON 구조에서 필요한 필드만 뽑아 pydantic 모델로 검증한다.
- 타입/범위 오류가 나면 ValidationError를 잡아서 원인을 기록하고
  전체 파이프라인이 죽지 않도록 처리한다.
- 실제 모델 생성 + 예외 처리는 _validate_one/_validate_many 두 제네릭 헬퍼로
  통일해서, extract_* 함수들은 "raw JSON을 어떤 필드로 매핑할지"에만 집중한다.
"""
from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from src.models import CountryInfo, IPGeoInfo, WeatherHourlyRecord

ModelT = TypeVar("ModelT", bound=BaseModel)


def _validate_one(model_cls: type[ModelT], kwargs: dict[str, Any]) -> tuple[ModelT | None, str | None]:
    """단일 레코드(국가정보/IP정보처럼 1건짜리 데이터)를 model_cls로 검증한다."""
    try:
        return model_cls(**kwargs), None
    except ValidationError as exc:
        msgs = "; ".join(e["msg"] for e in exc.errors())
        return None, msgs


def _validate_many(
    model_cls: type[ModelT], rows: list[dict[str, Any]]
) -> tuple[list[ModelT], list[str]]:
    """여러 레코드(날씨처럼 행이 여러 개인 데이터)를 model_cls로 검증하고
    (검증 통과 리스트, 실패 사유 리스트)로 분리한다."""
    valid: list[ModelT] = []
    errors: list[str] = []
    for idx, row in enumerate(rows):
        record, error = _validate_one(model_cls, row)
        if record is not None:
            valid.append(record)
        else:
            errors.append(f"index={idx} row={row} error={error}")
    return valid, errors


def extract_weather_records(raw: dict[str, Any]) -> tuple[list[WeatherHourlyRecord], list[str]]:
    """open-meteo 응답(raw)에서 시간대별 기온/강수확률 레코드를 추출한다.

    Returns:
        (검증 통과 레코드 리스트, 검증 실패 사유 리스트)
    """
    hourly = raw.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    probs = hourly.get("precipitation_probability", [])

    rows = [
        {"time": t, "temperature_2m": temp, "precipitation_probability": prob}
        for t, temp, prob in zip(times, temps, probs)
    ]
    return _validate_many(WeatherHourlyRecord, rows)


def extract_korea_country(raw: dict[str, Any]) -> tuple[CountryInfo | None, list[str]]:
    """countries.dev의 단일 국가 조회 응답(/alpha/KOR)에서 대한민국 정보를 검증한다.

    주의: restcountries.com v3.1은 서비스 종료, v5는 유료 API 키(무료 티어 월 500회 제한)가
    필요해 무료 대체 API인 countries.dev/alpha/{code}를 사용한다. 이 엔드포인트는
    "국가 리스트"가 아니라 조회한 나라 하나를 바로 반환하므로, 예전처럼 목록에서
    KR을 검색하는 과정이 필요 없다.
    """
    if not isinstance(raw, dict):
        return None, [f"예상치 못한 응답 타입입니다: {type(raw).__name__}"]

    kwargs = {
        "name": raw.get("name", ""),
        "capital": raw.get("capital"),
        "region": raw.get("region", ""),
        "population": raw.get("population", 0),
        "area": raw.get("area"),
        "alpha2_code": raw.get("alpha2Code", ""),
    }
    country, error = _validate_one(CountryInfo, kwargs)
    return country, ([error] if error else [])


def extract_ip_info(raw: dict[str, Any]) -> tuple[IPGeoInfo | None, list[str]]:
    """ip-api 응답에서 지역 정보 필드를 추출한다."""
    kwargs = {
        "query": raw.get("query", ""),
        "country": raw.get("country", ""),
        "countryCode": raw.get("countryCode", ""),
        "region": raw.get("region", ""),
        "regionName": raw.get("regionName", ""),
        "city": raw.get("city", ""),
        "isp": raw.get("isp", ""),
        "lat": raw.get("lat", 0.0),
        "lon": raw.get("lon", 0.0),
    }
    info, error = _validate_one(IPGeoInfo, kwargs)
    return info, ([error] if error else [])
