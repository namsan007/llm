# 마켓컬리 후기 분석

상품 페이지의 후기를 최대 300건 수집하고, 간단한 한국어 감성 키워드 분석과 Matplotlib 차트를 생성합니다.

## 실행

PowerShell에서 프로젝트 루트(`c:\work`) 기준으로 실행합니다.

```powershell
python market\market_review_analysis.py
```

수집 개수나 결과 폴더를 바꾸려면 다음처럼 실행합니다.

```powershell
python market\market_review_analysis.py --count 300 --output market\output
```

상품 페이지의 후기를 가능한 한 모두 수집하려면 다음처럼 실행합니다.

```powershell
python market\market_review_analysis.py --count 0 --output market\output_all
```

전체 후기가 약 2만 건 이상이면 수집에 수십 분이 걸릴 수 있습니다. 컬리의 요청 제한이나 페이지 구조 변경으로 더보기 버튼이 사라지면 그 시점까지 확보한 후기만 저장됩니다.

실행 결과:

- `market/output/kurly_reviews.csv`: 상품명, 작성일, 후기, 감성, 긍정점수, 부정점수
- `market/output/review_analysis.png`: 감성 분포와 주요 키워드 차트

## 주의사항

- Chrome 브라우저가 설치되어 있어야 하며, Selenium이 ChromeDriver를 자동으로 준비해야 합니다.
- 컬리의 페이지 구조나 접근 정책이 바뀌면 수집 가능한 후기 수가 목표보다 적을 수 있습니다. 프로그램은 실제 수집 건수를 출력합니다.
- 감성 분류는 외부 학습 모델이 아닌 상품 후기용 키워드 사전 기반의 해석 가능한 기준입니다. 분석 정확도를 높이려면 `market_review_analysis.py`의 `POSITIVE_WORDS`, `NEGATIVE_WORDS`를 보완하세요.
- 컬리 사이트의 이용약관과 robots 정책을 준수하고 과도한 요청을 피하기 위해 후기 확장 사이에 짧은 대기 시간을 둡니다.
