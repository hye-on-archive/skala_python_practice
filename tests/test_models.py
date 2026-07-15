"""pydantic v2 스키마 검증에 대한 pytest 테스트."""
import pytest
from pydantic import ValidationError

from src.models import CountryInfo, IPGeoInfo, WeatherHourlyRecord


class TestWeatherHourlyRecord:
    def test_valid_record_passes(self):
        record = WeatherHourlyRecord(
            time="2026-07-15T00:00", temperature_2m=24.5, precipitation_probability=30
        )
        assert record.temperature_2m == 24.5
        assert record.precipitation_probability == 30

    def test_temperature_out_of_range_raises(self):
        # 기온이 현실적인 범위(-40~50도)를 벗어나면 검증 실패해야 한다.
        with pytest.raises(ValidationError):
            WeatherHourlyRecord(
                time="2026-07-15T00:00", temperature_2m=999.0, precipitation_probability=30
            )

    def test_precipitation_probability_out_of_range_raises(self):
        # 강수확률은 0~100 범위를 벗어나면 안 된다.
        with pytest.raises(ValidationError):
            WeatherHourlyRecord(
                time="2026-07-15T00:00", temperature_2m=20.0, precipitation_probability=150
            )

    def test_invalid_time_type_raises(self):
        with pytest.raises(ValidationError):
            WeatherHourlyRecord(
                time="not-a-datetime", temperature_2m=20.0, precipitation_probability=10
            )


class TestCountryInfo:
    def test_valid_country_passes(self):
        country = CountryInfo(
            name="Korea (Republic of)", capital="Seoul", region="Asia",
            population=51780579, area=100210.0, alpha2_code="KR",
        )
        assert country.alpha2_code == "KR"

    def test_negative_population_raises(self):
        with pytest.raises(ValidationError):
            CountryInfo(
                name="Korea (Republic of)", capital="Seoul", region="Asia",
                population=-1, area=100210.0, alpha2_code="KR",
            )

    def test_lowercase_alpha2_code_raises(self):
        # alpha2_code는 대문자 2자리여야 하므로 소문자는 실패해야 한다.
        with pytest.raises(ValidationError):
            CountryInfo(
                name="Korea (Republic of)", capital="Seoul", region="Asia",
                population=51780579, area=100210.0, alpha2_code="kr",
            )


class TestIPGeoInfo:
    def test_valid_ip_info_passes(self):
        info = IPGeoInfo(
            query="8.8.8.8", country="United States", countryCode="US",
            region="VA", regionName="Virginia", city="Ashburn",
            isp="Google LLC", lat=39.03, lon=-77.5,
        )
        assert info.query == "8.8.8.8"

    def test_invalid_ip_format_raises(self):
        with pytest.raises(ValidationError):
            IPGeoInfo(
                query="not-an-ip", country="United States", countryCode="US",
                region="VA", regionName="Virginia", city="Ashburn",
                isp="Google LLC", lat=39.03, lon=-77.5,
            )

    def test_latitude_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            IPGeoInfo(
                query="8.8.8.8", country="United States", countryCode="US",
                region="VA", regionName="Virginia", city="Ashburn",
                isp="Google LLC", lat=999.0, lon=-77.5,
            )
