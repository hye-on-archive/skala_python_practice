"""
비동기 데이터 수집 모듈
- httpx.AsyncClient + asyncio.gather()로 3개의 서로 다른 API를
  동시에(병렬로) 호출한다.
- transport 파라미터를 주입할 수 있게 만들어서(의존성 주입),
  운영 시에는 실제 네트워크를, 테스트/데모 시에는 httpx.MockTransport를
  사용할 수 있도록 설계했다. (테스트 용이성을 위한 구조)
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=37.5665&longitude=126.9780"
    "&hourly=temperature_2m,precipitation_probability"
    "&forecast_days=3&timezone=Asia/Seoul"
)
RESTCOUNTRIES_URL = "https://files-03.restcountries.com/countries.00/legacy.json"
IP_API_URL = "https://ip-api.com/json/8.8.8.8"

REQUEST_TIMEOUT = 15.0


async def fetch_json(
    client: httpx.AsyncClient, name: str, url: str
) -> dict[str, Any]:
    """단일 API를 호출하고 JSON을 반환한다. 실패 시에도 예외를 던지지 않고
    {"_source": name, "_error": ...} 형태로 결과를 반환해 gather 전체가
    한 API의 실패로 중단되지 않도록 한다."""
    try:
        response = await client.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return {"_source": name, "_error": None, "data": data}
    except httpx.HTTPError as exc:
        return {"_source": name, "_error": str(exc), "data": None}


async def collect_all(
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, dict[str, Any]]:
    """open-meteo, restcountries, ip-api 3개 API를 asyncio.gather()로
    동시 수집한다.

    Args:
        transport: 테스트/데모용 커스텀 전송 계층. None이면 실제 네트워크로 요청한다.

    Returns:
        {"open-meteo": {...}, "restcountries": {...}, "ip-api": {...}}
    """
    async with httpx.AsyncClient(transport=transport) as client:
        results = await asyncio.gather(
            fetch_json(client, "open-meteo", OPEN_METEO_URL),
            fetch_json(client, "restcountries", RESTCOUNTRIES_URL),
            fetch_json(client, "ip-api", IP_API_URL),
        )
    return {r["_source"]: r for r in results}


if __name__ == "__main__":
    # 실제 네트워크로 3개 API를 동시 수집해 결과를 출력하는 진입점.
    # (이 샌드박스 환경은 외부 API 도메인이 방화벽 화이트리스트에 없어 직접
    #  실행 시 연결 오류가 날 수 있음. 실제 로컬 PC에서는 정상 동작한다.)
    collected = asyncio.run(collect_all())
    for source, result in collected.items():
        status = "OK" if result["_error"] is None else f"ERROR: {result['_error']}"
        print(f"[{source}] {status}")
