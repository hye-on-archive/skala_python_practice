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
    raw = [
        {"name": "Japan", "alpha2Code": "JP", "capital": "Tokyo", "region": "Asia",
         "population": 125800000, "area": 377975.0},
        {"name": "Korea (Republic of)", "alpha2Code": "KR", "capital": "Seoul",
         "region": "Asia", "population": 51780579, "area": 100210.0},
    ]
    country, errors = extract_korea_country(raw)
    assert country is not None
    assert country.alpha2_code == "KR"
    assert errors == []


def test_extract_korea_country_not_found():
    raw = [{"name": "Japan", "alpha2Code": "JP", "capital": "Tokyo",
            "region": "Asia", "population": 1, "area": 1.0}]
    country, errors = extract_korea_country(raw)
    assert country is None
    assert len(errors) == 1


def test_extract_korea_country_handles_dict_top_level():
    # 일부 restcountries 미러는 list가 아니라 {코드/이름/인덱스: 국가객체} 형태의
    # dict로 감싸서 제공한다. 이 경우에도 정상적으로 찾아야 한다.
    raw = {
        "0": {"name": "Japan", "alpha2Code": "JP", "capital": "Tokyo",
              "region": "Asia", "population": 1, "area": 1.0},
        "1": {"name": "Korea (Republic of)", "alpha2Code": "KR", "capital": "Seoul",
              "region": "Asia", "population": 51780579, "area": 100210.0},
    }
    country, errors = extract_korea_country(raw)
    assert country is not None
    assert country.alpha2_code == "KR"
    assert errors == []


def test_extract_korea_country_handles_v3_schema():
    # restcountries v3 스키마: name이 {"common": ...} 객체, 코드가 cca2,
    # capital이 리스트인 경우도 지원해야 한다.
    raw = [
        {"name": {"common": "Korea, Republic of", "official": "Republic of Korea"},
         "cca2": "KR", "capital": ["Seoul"], "region": "Asia",
         "population": 51780579, "area": 100210.0},
    ]
    country, errors = extract_korea_country(raw)
    assert country is not None
    assert country.alpha2_code == "KR"
    assert country.capital == "Seoul"
    assert errors == []


def test_extract_korea_country_unrecognized_top_level_type():
    country, errors = extract_korea_country("not-a-list-or-dict")
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
