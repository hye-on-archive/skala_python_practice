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


def _country_candidates(raw: Any) -> list[dict[str, Any]]:
    """legacy.json의 최상위 컨테이너가 list든 dict든 국가 객체 리스트로 정규화한다.

    restcountries 계열 미러들은 배포 방식에 따라
    - list[dict]  (예전 v2 API 원형)
    - dict[str, dict]  (키가 국가코드/이름/인덱스인 객체로 감싼 변형)
    두 형태를 모두 쓰는 경우가 있어 방어적으로 처리한다.
    """
    if isinstance(raw, list):
        return [c for c in raw if isinstance(c, dict)]
    if isinstance(raw, dict):
        return [c for c in raw.values() if isinstance(c, dict)]
    return []


def _country_name(c: dict[str, Any]) -> str:
    """v2 스키마(name: str)와 v3 스키마(name: {"common": str, ...}) 모두 지원."""
    name = c.get("name")
    if isinstance(name, dict):
        return name.get("common") or name.get("official") or ""
    return name or ""


def _country_alpha2(c: dict[str, Any]) -> str:
    """v2 스키마(alpha2Code)와 v3 스키마(cca2) 모두 지원."""
    return c.get("alpha2Code") or c.get("cca2") or ""


def extract_korea_country(raw: Any) -> tuple[CountryInfo | None, list[str]]:
    """restcountries legacy.json에서 대한민국 레코드만 추출한다.

    top-level 컨테이너 형태(list/dict)와 필드 스키마(v2/v3) 차이를
    모두 방어적으로 처리한다. 자세한 내용은 _country_candidates 참고.
    """
    errors: list[str] = []
    candidates = _country_candidates(raw)

    if not candidates:
        errors.append(
            f"국가 데이터 목록을 해석할 수 없습니다 (top-level type={type(raw).__name__})"
        )
        return None, errors

    korea_raw = next(
        (
            c
            for c in candidates
            if _country_alpha2(c) == "KR"
            or _country_name(c) in ("Korea (Republic of)", "South Korea", "Republic of Korea")
        ),
        None,
    )
    if korea_raw is None:
        errors.append("대한민국(KR) 데이터를 찾을 수 없습니다")
        return None, errors

    capital = korea_raw.get("capital")
    if isinstance(capital, list):  # v3 스키마는 capital이 리스트(["Seoul"])인 경우가 있다
        capital = capital[0] if capital else None

    try:
        country = CountryInfo(
            name=_country_name(korea_raw),
            capital=capital,
            region=korea_raw.get("region", ""),
            population=korea_raw.get("population", 0),
            area=korea_raw.get("area"),
            alpha2_code=_country_alpha2(korea_raw),
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
