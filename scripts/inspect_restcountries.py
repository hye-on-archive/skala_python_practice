"""restcountries legacy.json의 실제 최상위 구조를 확인하기 위한 1회성 진단 스크립트.
사용법: (venv 활성화 후) python scripts/inspect_restcountries.py
"""
import json

import httpx

URL = "https://files-03.restcountries.com/countries.00/legacy.json"


def describe(obj, depth=0, max_depth=3):
    indent = "  " * depth
    if depth > max_depth:
        print(f"{indent}...(더 깊음, 생략)")
        return
    if isinstance(obj, dict):
        keys = list(obj.keys())
        print(f"{indent}dict, key count={len(keys)}, sample keys={keys[:5]}")
        if keys:
            print(f"{indent}-> keys[0]='{keys[0]}'의 값 타입 확인:")
            describe(obj[keys[0]], depth + 1, max_depth)
    elif isinstance(obj, list):
        print(f"{indent}list, length={len(obj)}")
        if obj:
            print(f"{indent}-> obj[0]의 타입 확인:")
            describe(obj[0], depth + 1, max_depth)
    else:
        print(f"{indent}{type(obj).__name__}: {repr(obj)[:200]}")


r = httpx.get(URL, timeout=20)
print("HTTP status:", r.status_code)
data = r.json()
print("\n=== 구조 ===")
describe(data)

print("\n=== 원본 앞부분 800자 (참고용) ===")
print(json.dumps(data, ensure_ascii=False)[:800])
