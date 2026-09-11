"""1970~2024년 출생아수 데이터 정제, 분석, 시각화."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd


DEFAULT_INPUT = Path(__file__).parent / "child_list.xlsx"
DEFAULT_OUTPUT = Path(__file__).parent / "analysis_output" / "birth"
START_YEAR = 1970
END_YEAR = 2024
FORECAST_END_YEAR = 2100
FORECAST_YEARS = 20


def configure_korean_font() -> None:
    """설치된 한글 글꼴을 찾아 그래프의 한글 경고를 방지한다."""
    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    for font_name in ("Malgun Gothic", "NanumGothic", "AppleGothic"):
        if font_name in available_fonts:
            plt.rcParams["font.family"] = font_name
            break
    plt.rcParams["axes.unicode_minus"] = False


def clean_data(input_path: Path) -> pd.DataFrame:
    """엑셀의 가로형 원자료를 분석 가능한 세로형 데이터로 정제한다."""
    raw = pd.read_excel(input_path, sheet_name="데이터", engine="openpyxl")
    raw.columns = raw.columns.astype(str).str.strip()

    metric_column = raw.columns[0]
    required_columns = {metric_column, "출생아수(명)"}
    if "출생아수(명)" not in raw[metric_column].astype(str).str.strip().values:
        raise ValueError("'출생아수(명)' 행을 엑셀에서 찾을 수 없습니다.")

    years = [str(year) for year in range(START_YEAR, END_YEAR + 1)]
    missing_years = [year for year in years if year not in raw.columns]
    if missing_years:
        raise ValueError(f"필수 연도 열이 없습니다: {missing_years}")

    births = raw.loc[
        raw[metric_column].astype(str).str.strip().eq("출생아수(명)"), years
    ].iloc[0]
    data = pd.DataFrame(
        {
            "연도": pd.to_numeric(births.index, errors="coerce"),
            "출생아수": pd.to_numeric(
                births.astype("string").str.replace(",", "", regex=False).str.strip(),
                errors="coerce",
            ).to_numpy(),
        }
    )

    before = len(data)
    data = (
        data.dropna(subset=["연도", "출생아수"])
        .drop_duplicates(subset=["연도"])
        .sort_values("연도")
    )
    data["연도"] = data["연도"].astype(int)
    data["출생아수"] = data["출생아수"].astype(int)
    data["전년 대비 증감"] = data["출생아수"].diff()
    data["전년 대비 증감률(%)"] = data["출생아수"].pct_change() * 100

    print(f"정제 전 행 수: {before:,}")
    print(f"정제 후 행 수: {len(data):,}")
    print(f"제거된 행 수: {before - len(data):,}")
    return data.reset_index(drop=True)


def create_summary(data: pd.DataFrame) -> pd.DataFrame:
    """기간 전체의 핵심 통계를 계산한다."""
    first = data.iloc[0]
    last = data.iloc[-1]
    highest = data.loc[data["출생아수"].idxmax()]
    lowest = data.loc[data["출생아수"].idxmin()]
    return pd.DataFrame(
        {
            "값": [
                first["출생아수"],
                last["출생아수"],
                highest["출생아수"],
                lowest["출생아수"],
                last["출생아수"] - first["출생아수"],
                (last["출생아수"] / first["출생아수"] - 1) * 100,
                data["출생아수"].mean(),
            ]
        },
        index=[
            "1970년 출생아수",
            "2024년 출생아수",
            f"최대 출생아수({int(highest['연도'])}년)",
            f"최소 출생아수({int(lowest['연도'])}년)",
            "1970년 대비 증감",
            "1970년 대비 증감률(%)",
            "기간 평균 출생아수",
        ],
    )


def save_birth_chart(data: pd.DataFrame, output_path: Path) -> None:
    """출생아수 추이를 라인 그래프로 저장한다."""
    configure_korean_font()
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(
        data["연도"],
        data["출생아수"],
        color="#d1495b",
        linewidth=2,
        marker="o",
        markersize=3,
        label="출생아수",
    )
    ax.set_title("1970~2024년 출생아수 추이")
    ax.set_xlabel("연도")
    ax.set_ylabel("출생아수(명)")
    ax.set_xticks(range(START_YEAR, END_YEAR + 1, 5))
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def create_forecast(data: pd.DataFrame) -> pd.DataFrame:
    """최근 20년 로그 선형회귀로 2025~2100년 출생아수를 추정한다."""
    recent = data.tail(FORECAST_YEARS)
    x = recent["연도"].to_numpy(dtype=float)
    log_y = np.log(recent["출생아수"].to_numpy(dtype=float))
    slope, intercept = np.polyfit(x, log_y, 1)
    fitted_log_y = slope * x + intercept
    residuals = log_y - fitted_log_y
    residual_std = np.sqrt(np.sum(residuals**2) / (len(x) - 2))
    x_mean = x.mean()
    sum_squared_deviation = np.sum((x - x_mean) ** 2)
    years = np.arange(END_YEAR + 1, FORECAST_END_YEAR + 1)
    predicted_log = slope * years + intercept
    prediction_se = residual_std * np.sqrt(
        1 + 1 / len(x) + (years - x_mean) ** 2 / sum_squared_deviation
    )
    return pd.DataFrame(
        {
            "연도": years,
            "예상 출생아수": np.rint(np.exp(predicted_log)).astype(int),
            "95% 하한": np.rint(np.exp(predicted_log - 1.96 * prediction_se)).astype(int),
            "95% 상한": np.rint(np.exp(predicted_log + 1.96 * prediction_se)).astype(int),
        }
    )


def save_forecast_chart(
    data: pd.DataFrame, forecast: pd.DataFrame, output_path: Path
) -> None:
    """실제값과 2100년까지의 추정값을 다른 색으로 함께 저장한다."""
    configure_korean_font()
    fig, ax = plt.subplots(figsize=(15, 7))
    ax.plot(
        data["연도"],
        data["출생아수"],
        color="#d1495b",
        linewidth=2,
        label="실제 출생아수",
    )
    ax.plot(
        forecast["연도"],
        forecast["예상 출생아수"],
        color="#2a9d8f",
        linewidth=2,
        linestyle="--",
        label="2025~2100년 추정치(최근 20년 로그 선형회귀)",
    )
    ax.fill_between(
        forecast["연도"],
        forecast["95% 하한"],
        forecast["95% 상한"],
        color="#2a9d8f",
        alpha=0.15,
        label="95% 예측구간",
    )
    ax.axvline(END_YEAR, color="#777777", linewidth=1, linestyle=":")
    ax.set_title("1970~2100년 출생아수 추이 및 추정")
    ax.set_xlabel("연도")
    ax.set_ylabel("출생아수(명)")
    ax.set_xticks(range(START_YEAR, FORECAST_END_YEAR + 1, 10))
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def run_analysis(input_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    data = clean_data(input_path)
    if data.empty:
        raise ValueError("분석할 출생아수 데이터가 없습니다.")

    summary = create_summary(data)
    forecast = create_forecast(data)
    data.to_csv(output_dir / "birth_cleaned.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(output_dir / "birth_summary.csv", encoding="utf-8-sig")
    forecast.to_csv(output_dir / "birth_forecast_2025_2100.csv", index=False, encoding="utf-8-sig")
    save_birth_chart(data, output_dir / "birth_count_line.png")
    save_forecast_chart(data, forecast, output_dir / "birth_count_to_2100.png")

    print("\n주요 분석 결과")
    print(summary.to_string(float_format=lambda value: f"{value:,.2f}"))
    final_forecast = forecast.iloc[-1]
    print(
        f"\n2100년 추정 출생아수: {final_forecast['예상 출생아수']:,}명 "
        f"(95% 구간: {final_forecast['95% 하한']:,}~{final_forecast['95% 상한']:,}명)"
    )
    print(f"\n결과 저장 위치: {output_dir.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="엑셀 입력 경로")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="결과 저장 폴더")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_analysis(args.input, args.output)