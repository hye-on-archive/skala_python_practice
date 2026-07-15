"""
asyncio.gather 기반 비동기 수집 로직에 대한 pytest 테스트.
실제 네트워크에 의존하면 CI/테스트 환경에 따라 결과가 불안정해지므로
(flaky test 방지), httpx.MockTransport로 HTTP 계층만 모킹해서
"3개 API를 동시에 호출하고 각각 정상적으로 파싱하는지"를 검증한다.
"""
import httpx
import pytest

from src.collectors import IP_API_URL, OPEN_METEO_URL, RESTCOUNTRIES_URL, collect_all


def _mock_handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.startswith(OPEN_METEO_URL.split("?")[0]):
        return httpx.Response(200, json={"hourly": {"time": [], "temperature_2m": [], "precipitation_probability": []}})
    if url.startswith(RESTCOUNTRIES_URL):
        # countries.dev/alpha/{code}는 국가 리스트가 아니라 단일 국가 객체를 반환한다.
        return httpx.Response(200, json={"name": "Korea (Republic of)", "capital": "Seoul",
                                          "region": "Asia", "population": 51780579,
                                          "area": 100210, "alpha2Code": "KR"})
    if url.startswith(IP_API_URL):
        return httpx.Response(200, json={"query": "8.8.8.8"})
    return httpx.Response(404)


@pytest.mark.asyncio
async def test_collect_all_returns_three_sources():
    transport = httpx.MockTransport(_mock_handler)
    result = await collect_all(transport=transport)
    assert set(result.keys()) == {"open-meteo", "restcountries", "ip-api"}
    for source, r in result.items():
        assert r["_error"] is None, f"{source} 수집 실패: {r['_error']}"


@pytest.mark.asyncio
async def test_collect_all_handles_http_error():
    # 하나의 API가 500 에러를 반환해도 전체 gather가 죽지 않고
    # 개별 결과에 에러가 기록되어야 한다.
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).startswith(OPEN_METEO_URL.split("?")[0]):
            return httpx.Response(500)
        return _mock_handler(request)

    transport = httpx.MockTransport(handler)
    result = await collect_all(transport=transport)
    assert result["open-meteo"]["_error"] is not None
    assert result["restcountries"]["_error"] is None
    assert result["ip-api"]["_error"] is None
