"""raw JSON -> pydantic 모델 추출 로직에 대한 pytest 테스트."""
from src.extract import extract_ip_info, extract_korea_country, extract_weather_records


def test_extract_weather_records_filters_invalid_rows():
    raw = {
        "hourly": {
            "time": ["2026-07-15T00:00", "2026-07-15T01:00", "2026-07-15T02:00"],
            "temperature_2m": [24.5, 999.0, 23.0],  # 두번째 값은 범위 초과
            "precipitation_probability": [10, 20, 30],
        }
    }
    valid, errors = extract_weather_records(raw)
    assert len(valid) == 2
    assert len(errors) == 1
    assert "index=1" in errors[0]


def test_extract_korea_country_found():
    # countries.dev/alpha/KOR 실제 응답 예시(필요 필드만 발췌)
    raw = {
        "name": "Korea (Republic of)",
        "capital": "Seoul",
        "region": "Asia",
        "population": 51780579,
        "area": 100210,
        "alpha2Code": "KR",
        "alpha3Code": "KOR",
    }
    country, errors = extract_korea_country(raw)
    assert country is not None
    assert country.alpha2_code == "KR"
    assert country.capital == "Seoul"
    assert errors == []


def test_extract_korea_country_invalid_population_raises_validation_error():
    # population이 음수면 pydantic 검증에서 실패해야 한다.
    raw = {
        "name": "Korea (Republic of)", "capital": "Seoul", "region": "Asia",
        "population": -1, "area": 100210, "alpha2Code": "KR",
    }
    country, errors = extract_korea_country(raw)
    assert country is None
    assert len(errors) == 1


def test_extract_korea_country_unexpected_response_type():
    # countries.dev가 배열이나 에러 문자열 등 dict가 아닌 응답을 주면
    # 예외 없이 실패 사유를 기록해야 한다.
    country, errors = extract_korea_country(["unexpected", "list"])
    assert country is None
    assert len(errors) == 1


def test_extract_ip_info_valid():
    raw = {"query": "8.8.8.8", "country": "United States", "countryCode": "US",
           "region": "VA", "regionName": "Virginia", "city": "Ashburn",
           "isp": "Google LLC", "lat": 39.03, "lon": -77.5}
    info, errors = extract_ip_info(raw)
    assert info is not None
    assert errors == []


def test_extract_ip_info_invalid_query():
    raw = {"query": "invalid-ip", "country": "United States", "countryCode": "US",
           "region": "VA", "regionName": "Virginia", "city": "Ashburn",
           "isp": "Google LLC", "lat": 39.03, "lon": -77.5}
    info, errors = extract_ip_info(raw)
    assert info is None
    assert len(errors) == 1
