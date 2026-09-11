"""S&P 500 historical data cleansing and analysis."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DEFAULT_INPUT = Path(__file__).parent / "stock" / "S&P 500 과거 데이터.csv"
DEFAULT_OUTPUT = Path(__file__).parent / "analysis_output"
START_DATE = "2000-01-01"
END_DATE = "2019-12-31"


def clean_data(input_path: Path) -> pd.DataFrame:
    """Load the CSV, clean its types, sort it by date, and add analysis columns."""
    raw = pd.read_csv(input_path)
    required_columns = {"날짜", "종가", "시가", "고가", "저가", "변동 %"}
    missing_columns = required_columns.difference(raw.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    data = raw.copy()
    data["날짜"] = pd.to_datetime(
        data["날짜"].astype("string").str.replace(r"\s+", "", regex=True),
        format="%Y-%m-%d",
        errors="coerce",
    )

    numeric_columns = ["종가", "시가", "고가", "저가", "거래량"]
    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column].astype("string").str.replace(",", "", regex=False),
            errors="coerce",
        )
    data["변동 %"] = pd.to_numeric(
        data["변동 %"].astype("string").str.replace("%", "", regex=False),
        errors="coerce",
    )

    before = len(data)
    data = data.dropna(subset=["날짜", "종가"]).drop_duplicates(subset=["날짜"])
    data = data.sort_values("날짜").set_index("날짜")
    data = data.loc[START_DATE:END_DATE].copy()
    data["일간 수익률"] = data["종가"].pct_change()
    data["누적 수익률"] = (1 + data["일간 수익률"]).cumprod() - 1
    data["고점 대비 하락률"] = data["종가"] / data["종가"].cummax() - 1
    data["20일 이동평균"] = data["종가"].rolling(20).mean()
    data["60일 이동평균"] = data["종가"].rolling(60).mean()

    removed_rows = before - len(data)
    print(f"정제 전 행 수: {before:,}")
    print(f"정제 후 행 수: {len(data):,}")
    print(f"제거된 행 수: {removed_rows:,}")
    if not data.empty and data.index.max() < pd.Timestamp("2019-12-31"):
        print(
            "경고: CSV에 2019년 12월 데이터가 없어 "
            f"{data.index.max():%Y-%m-%d}까지만 포함됩니다."
        )
    return data


def create_summary(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create descriptive, yearly, and monthly analysis tables."""
    daily_returns = data["일간 수익률"].dropna()
    summary = pd.DataFrame(
        {
            "값": [
                data["종가"].iloc[0],
                data["종가"].iloc[-1],
                data["종가"].min(),
                data["종가"].max(),
                daily_returns.mean(),
                daily_returns.std(),
                daily_returns.std() * np.sqrt(252),
                data["고점 대비 하락률"].min(),
                data["누적 수익률"].iloc[-1],
            ]
        },
        index=[
            "시작 종가",
            "마지막 종가",
            "기간 최저 종가",
            "기간 최고 종가",
            "평균 일간 수익률",
            "일간 수익률 표준편차",
            "연환산 변동성",
            "최대 낙폭",
            "누적 수익률",
        ],
    )

    yearly = data["종가"].resample("YE").agg(["first", "last", "min", "max"])
    yearly.columns = ["연초 종가", "연말 종가", "연중 최저", "연중 최고"]
    yearly["연간 수익률"] = yearly["연말 종가"].pct_change()

    monthly = data["종가"].resample("ME").agg(["first", "last"])
    monthly.columns = ["월초 종가", "월말 종가"]
    monthly["월간 수익률"] = monthly["월말 종가"] / monthly["월초 종가"] - 1
    return summary, yearly, monthly


def save_price_chart(data: pd.DataFrame, output_path: Path) -> None:
    """Save the requested closing-price line chart."""
    fig, ax = plt.subplots(figsize=(15, 7))
    ax.plot(data.index, data["종가"], color="#1f77b4", linewidth=1.2, label="S&P 500 Close")
    ax.set_title("S&P 500 Closing Price (January 2000 - December 2019)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Close")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def run_analysis(input_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    data = clean_data(input_path)
    if data.empty:
        raise ValueError("선택한 기간에 사용할 데이터가 없습니다.")

    summary, yearly, monthly = create_summary(data)
    data.to_csv(output_dir / "sp500_cleaned.csv", encoding="utf-8-sig")
    summary.to_csv(output_dir / "sp500_summary.csv", encoding="utf-8-sig")
    yearly.to_csv(output_dir / "sp500_yearly_returns.csv", encoding="utf-8-sig")
    monthly.to_csv(output_dir / "sp500_monthly_returns.csv", encoding="utf-8-sig")
    save_price_chart(data, output_dir / "sp500_close_line.png")

    print("\n주요 분석 결과")
    print(summary.to_string(float_format=lambda value: f"{value:,.4f}"))
    print(f"\n결과 저장 위치: {output_dir.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="CSV input path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output directory")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_analysis(args.input, args.output)