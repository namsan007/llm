"""마켓컬리 상품 후기 300건 수집, 감성 분석, 시각화."""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

PRODUCT_URL = "https://www.kurly.com/goods/1001498506?collectionCode=26chu-269010"
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "output"
TARGET_COUNT = 300

POSITIVE_WORDS = {
    "좋", "맛있", "만족", "추천", "재구매", "재구입", "효과", "편하", "든든",
    "건강", "원활", "잘 먹", "잘먹", "빠르", "꼼꼼", "신선", "최고", "감사",
    "괜찮", "만족스럽", "부드럽", "간편", "꾸준히", "도움",
}
NEGATIVE_WORDS = {
    "나쁘", "별로", "실망", "불만", "불편", "느리", "늦", "비싸", "비싸다", "아쉽",
    "효과 없", "효과없", "안 맞", "안맞", "부작용", "냄새", "역하", "불쾌", "작다",
    "크다", "새다", "파손", "누락", "환불", "교환", "품절",
}
NEGATION_WORDS = ("안 ", "않", "못", "없", "별로")
DATE_PATTERN = re.compile(r"20\d{2}\.\d{1,2}\.\d{1,2}")


def normalize_text(text: str) -> str:
    """공백과 UI 문구를 정리한 후기 텍스트를 반환한다."""
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace("도움돼요", "").strip()


def review_from_card(card_text: str) -> str:
    """상품명, 날짜, 등급 같은 메타데이터를 제거하고 후기 본문만 반환한다."""
    lines = [normalize_text(line) for line in card_text.splitlines()]
    lines = [line for line in lines if line]
    body: list[str] = []
    for line in lines:
        if line.startswith("[") or DATE_PATTERN.fullmatch(line):
            continue
        if line in {"Image", "이미지", "상품 후기", "후기", "이전", "다음"}:
            continue
        if re.fullmatch(r"(?:VVIP|VIP|멤버스)?[가-힣*]{1,4}", line):
            continue
        if re.fullmatch(r"\d{1,2}대(?:/[가-힣]+)*", line):
            continue
        body.append(line)
    return " ".join(body).strip()


def extract_reviews(html: str) -> list[dict[str, str]]:
    """후기 카드 후보를 HTML에서 찾아 중복 없이 추출한다."""
    soup = BeautifulSoup(html, "html.parser")
    reviews: list[dict[str, str]] = []
    seen: set[str] = set()

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            structured_data = json.loads(script.string or "{}")
        except json.JSONDecodeError:
            continue
        structured_items = [structured_data]
        if isinstance(structured_data, dict) and isinstance(structured_data.get("@graph"), list):
            structured_items.extend(structured_data["@graph"])
        for structured_item in structured_items:
            if not isinstance(structured_item, dict):
                continue
            items = structured_item.get("review", [])
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                review_text = normalize_text(str(item.get("reviewBody", "")))
                if not review_text or review_text in seen:
                    continue
                reviews.append(
                    {
                        "상품명": normalize_text(str(structured_item.get("name", "상품 후기"))),
                        "작성일": str(item.get("datePublished", "")),
                        "후기": review_text,
                    }
                )
                seen.add(review_text)

    for heading in soup.find_all(string=re.compile(r"^\s*\[")):
        title = normalize_text(heading.get_text(" ", strip=True))
        if not title.startswith("[") or "유산균" not in title:
            continue

        candidate = heading.parent
        review_text = ""
        for _ in range(6):
            candidate = candidate.parent if candidate else None
            if candidate is None:
                break
            text = candidate.get_text("\n", strip=True)
            if DATE_PATTERN.search(text) and 20 <= len(text) <= 3000:
                review_text = review_from_card(text)
                break
        else:
            continue

        if not review_text or review_text in seen:
            continue
        date_match = DATE_PATTERN.search(text)
        reviews.append(
            {
                "상품명": title,
                "작성일": date_match.group(0) if date_match else "",
                "후기": review_text,
            }
        )
        seen.add(review_text)
    return reviews


def make_driver() -> webdriver.Chrome:
    """화면 없이 컬리 상품 페이지를 여는 Chrome WebDriver를 만든다."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,3000")
    options.add_argument("--lang=ko-KR")
    options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(options=options)


def click_more_reviews(driver: webdriver.Chrome) -> bool:
    """페이지의 후기 더보기 버튼을 한 번 누르고 성공 여부를 반환한다."""
    try:
        review_area = driver.find_element(By.ID, "review")
    except WebDriverException:
        return False
    buttons = review_area.find_elements(
        By.XPATH,
        ".//*[self::button or self::a][contains(normalize-space(.), '더보기')]",
    )
    for button in reversed(buttons):
        if button.is_displayed() and button.is_enabled():
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            driver.execute_script("arguments[0].click();", button)
            return True
    return False


def crawl_reviews(url: str, target_count: int, pause: float = 0.8) -> list[dict[str, str]]:
    """후기 더보기를 반복해 target_count건을 수집한다. 0은 전체 수집이다."""
    driver = make_driver()
    reviews: list[dict[str, str]] = []
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            lambda current: "상품 후기" in current.find_element(By.TAG_NAME, "body").text
        )
        stagnant = 0
        max_clicks = 3000 if target_count <= 0 else max(80, target_count // 5 + 10)
        for click_number in range(max_clicks):
            reviews = extract_reviews(driver.page_source)
            if target_count > 0 and len(reviews) >= target_count:
                break
            before = len(reviews)
            if not click_more_reviews(driver):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(pause)
                reviews = extract_reviews(driver.page_source)
                if len(reviews) == before:
                    stagnant += 1
                else:
                    stagnant = 0
            else:
                time.sleep(pause)
                updated_reviews = extract_reviews(driver.page_source)
                if len(updated_reviews) == before:
                    stagnant += 1
                else:
                    reviews = updated_reviews
                    stagnant = 0
            if click_number and click_number % 25 == 0:
                print(f"진행 중: {len(reviews):,}건 수집", flush=True)
            if stagnant >= 3:
                break
        return reviews if target_count <= 0 else reviews[:target_count]
    finally:
        driver.quit()


def classify_sentiment(text: str) -> tuple[str, int, int]:
    """간단한 한국어 키워드 사전으로 긍정/부정 점수와 라벨을 계산한다."""
    positive_score = sum(text.count(word) for word in POSITIVE_WORDS)
    negative_score = sum(text.count(word) for word in NEGATIVE_WORDS)
    for negation in NEGATION_WORDS:
        if negation in text:
            positive_score, negative_score = negative_score, positive_score
            break
    if positive_score > negative_score:
        label = "긍정"
    elif negative_score > positive_score:
        label = "부정"
    else:
        label = "중립"
    return label, positive_score, negative_score


def analyze_reviews(reviews: list[dict[str, str]]) -> pd.DataFrame:
    """후기 목록을 DataFrame으로 만들고 감성 분석 결과를 추가한다."""
    data = pd.DataFrame(reviews)
    if data.empty:
        raise ValueError("수집된 후기가 없습니다.")
    result = data["후기"].apply(classify_sentiment)
    data[["감성", "긍정점수", "부정점수"]] = pd.DataFrame(
        result.tolist(), index=data.index
    )
    return data


def save_charts(data: pd.DataFrame, output_dir: Path) -> None:
    """감성 분포와 주요 긍정/부정 키워드 차트를 저장한다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sentiment_counts = data["감성"].value_counts().reindex(
        ["긍정", "중립", "부정"], fill_value=0
    )
    axes[0].bar(sentiment_counts.index, sentiment_counts.values, color=["#2a9d8f", "#8d99ae", "#e76f51"])
    axes[0].set_title("후기 감성 분포")
    axes[0].set_ylabel("후기 수")
    axes[0].grid(axis="y", alpha=0.25)
    for index, value in enumerate(sentiment_counts.values):
        axes[0].text(index, value, str(value), ha="center", va="bottom")

    keyword_counts = Counter()
    for text in data.loc[data["감성"] == "긍정", "후기"]:
        keyword_counts.update(word for word in POSITIVE_WORDS if word in text)
    for text in data.loc[data["감성"] == "부정", "후기"]:
        keyword_counts.update(word for word in NEGATIVE_WORDS if word in text)
    top_keywords = pd.Series(keyword_counts).sort_values(ascending=False).head(10).sort_values()
    axes[1].barh(top_keywords.index, top_keywords.values, color="#457b9d")
    axes[1].set_title("주요 감성 키워드")
    axes[1].set_xlabel("언급 후기 수")
    axes[1].grid(axis="x", alpha=0.25)

    fig.suptitle("마켓컬리 상품 후기 분석")
    fig.tight_layout()
    fig.savefig(output_dir / "review_analysis.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def run(url: str, target_count: int, output_dir: Path) -> None:
    """수집부터 CSV와 차트 저장까지 실행한다."""
    target_description = "전체" if target_count <= 0 else f"최대 {target_count}건"
    print(f"후기 수집 시작: {target_description}")
    try:
        reviews = crawl_reviews(url, target_count)
    except WebDriverException as error:
        raise RuntimeError(
            "Chrome WebDriver를 실행할 수 없습니다. Chrome 설치 상태를 확인하세요."
        ) from error
    data = analyze_reviews(reviews)
    output_dir.mkdir(parents=True, exist_ok=True)
    data.to_csv(output_dir / "kurly_reviews.csv", index=False, encoding="utf-8-sig")
    save_charts(data, output_dir)
    print(f"실제 수집 후기: {len(data):,}건")
    print(data["감성"].value_counts().reindex(["긍정", "중립", "부정"], fill_value=0))
    print(f"결과 폴더: {output_dir.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=PRODUCT_URL, help="컬리 상품 URL")
    parser.add_argument(
        "--count",
        type=int,
        default=TARGET_COUNT,
        help="수집할 최대 후기 수. 0이면 더보기 버튼이 사라질 때까지 전체 수집",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="결과 저장 폴더")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    run(arguments.url, arguments.count, arguments.output)
