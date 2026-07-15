"""
pydantic v2 스키마 정의 모듈
- 3개 API(open-meteo, restcountries, ip-api) 응답에서 필요한 필드를 추출해
  타입 검증 + 값 범위(range) 검증을 수행하는 모델들을 정의한다.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class WeatherHourlyRecord(BaseModel):
    """open-meteo 시간대별 예보 1건(1시간 단위)에 대한 검증 모델."""

    # 시각(ISO8601 문자열 -> datetime 자동 파싱)
    time: datetime

    # 기온(섭씨). 서울 기준 현실적인 범위로 -40 ~ 50도로 제한
    temperature_2m: float = Field(ge=-40.0, le=50.0)

    # 강수확률(%) : 0 ~ 100 사이만 허용
    precipitation_probability: int = Field(ge=0, le=100)


class CountryInfo(BaseModel):
    """restcountries(legacy.json)에서 대한민국(한국) 레코드만 추출한 검증 모델."""

    name: str = Field(min_length=1)
    capital: str | None = None
    region: str
    population: int = Field(ge=0)
    area: float | None = Field(default=None, ge=0)
    alpha2_code: str = Field(min_length=2, max_length=2)

    @field_validator("alpha2_code")
    @classmethod
    def code_must_be_upper(cls, v: str) -> str:
        # 국가 코드는 항상 대문자 2자리(ISO 3166-1 alpha-2)여야 한다.
        if not v.isalpha() or not v.isupper():
            raise ValueError("alpha2_code는 대문자 알파벳 2자리여야 합니다")
        return v


class IPGeoInfo(BaseModel):
    """ip-api 응답에서 필요한 지역 정보 필드만 추출한 검증 모델."""

    query: str = Field(min_length=7, description="조회한 IP 주소")
    country: str
    countryCode: str = Field(min_length=2, max_length=2)
    region: str
    regionName: str
    city: str
    isp: str
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)

    @field_validator("query")
    @classmethod
    def query_must_look_like_ip(cls, v: str) -> str:
        # 아주 단순한 IPv4 형태(x.x.x.x) 검증. 완벽한 IP 검증은 아니지만
        # 과제 범위에서는 자릿수 기반 형태 검증으로 충분하다.
        parts = v.split(".")
        if len(parts) != 4 or not all(p.isdigit() for p in parts):
            raise ValueError(f"'{v}'는 올바른 IPv4 형식이 아닙니다")
        return v
