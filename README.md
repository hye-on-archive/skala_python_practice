# Day 1 종합실습 — 실무형 수집·검증·품질 파이프라인

3개의 외부 API(Open-Meteo, countries.dev, ip-api)를 `asyncio.gather()`로 동시 수집하고,
`pydantic v2`로 스키마/범위를 검증한 뒤, CSV/Parquet 두 포맷으로 저장하며 성능을 비교하는 파이프라인.

## 실행 방법

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

pytest -v                         # 단위 테스트 18건
ruff check .                      # 코드 스타일 검사
python -m src.main                 # 전체 파이프라인 실행 (반드시 프로젝트 루트에서 실행)
```

실행 결과는 `data/` 아래에 `weather.csv` / `weather.parquet` / `meta.json` 등으로 저장된다.

## 폴더 구조

```
src/
  collectors.py   비동기 수집 (httpx + asyncio.gather)
  models.py       pydantic v2 스키마 (타입/범위 검증)
  extract.py      raw JSON -> pydantic 모델 추출/검증
  storage.py      CSV/Parquet 저장 및 성능(ms) 비교
  main.py         파이프라인 진입점
tests/            pytest 테스트 (모델/추출/수집 로직)
scripts/          API 응답 구조 진단용 보조 스크립트
data/             실행 결과 저장 위치 (git 추적 제외)
```

## 진행하며 부딪힌 이슈 & 해결 (실무형 트러블슈팅 기록)

- **ip-api 403 Forbidden**: 무료(비회원) 티어는 HTTPS 미지원. `http://`로 변경해 해결.
- **restcountries 서비스 종료**: v3.1 종료, v5는 유료 API 키 필요. 무료 대체 API
  `countries.dev/alpha/{code}`로 교체. 이 API는 국가 목록이 아니라 단일 국가 객체를
  바로 반환하므로 파싱 로직을 리스트 검색 -> 단일 객체 파싱으로 단순화.
- **`pytest` 단독 실행 시 `ModuleNotFoundError: No module named 'src'`**: `python -m pytest`는
  cwd를 sys.path에 자동 추가하지만 plain `pytest`는 그렇지 않음. `pytest.ini`에
  `pythonpath = .` 추가로 해결.
- **Parquet 벤치마크 왜곡**: 프로세스에서 `to_parquet()`를 처음 호출하면 pyarrow 라이브러리
  로딩/초기화 비용(수~수십 ms)이 붙어 소량 데이터에서 Parquet가 부당하게 느리게 측정됨.
  실측 벤치마크 전에 더미 데이터로 한 번 써보고 지우는 `warmup_io_engines()`를 추가해
  순수 저장/읽기 성능만 측정하도록 수정.

## 성능 비교 관찰

72행(실측) 규모에서는 CSV가 유리하지만, 72,000행(시뮬레이션)으로 늘리면 Parquet가
쓰기/읽기/파일크기 전 항목에서 압도적으로 유리해진다. 컬럼 지향 압축 포맷의 이점은
데이터 규모가 커질수록 드러나며, 소량 데이터에서는 오히려 오버헤드로 작용할 수 있음을
확인했다.
