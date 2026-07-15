"""日本の国民の祝日を計算するモジュール（外部データ不要）。

春分・秋分の日、ハッピーマンデー、振替休日、国民の休日に対応。
おおむね 1980〜2099 年の範囲で有効。
"""

from __future__ import annotations

import datetime as _dt


def _nth_monday(year: int, month: int, n: int) -> int:
    """month の n 番目の月曜日の「日」を返す。"""
    first_wd = _dt.date(year, month, 1).weekday()  # 月=0 ... 日=6
    offset = (0 - first_wd) % 7  # 最初の月曜までの日数
    return 1 + offset + (n - 1) * 7


def _vernal_equinox(year: int) -> int:
    return int(20.8431 + 0.242194 * (year - 1980) - (year - 1980) // 4)


def _autumnal_equinox(year: int) -> int:
    return int(23.2488 + 0.242194 * (year - 1980) - (year - 1980) // 4)


def holidays_for_year(year: int) -> dict[_dt.date, str]:
    """指定した暦年の祝日 { date: 名称 } を返す。"""
    base: dict[_dt.date, str] = {}

    def add(month: int, day: int, name: str) -> None:
        base[_dt.date(year, month, day)] = name

    add(1, 1, "元日")
    add(1, _nth_monday(year, 1, 2), "成人の日")
    add(2, 11, "建国記念の日")
    if year >= 2020:
        add(2, 23, "天皇誕生日")
    add(3, _vernal_equinox(year), "春分の日")
    add(4, 29, "昭和の日")
    add(5, 3, "憲法記念日")
    add(5, 4, "みどりの日")
    add(5, 5, "こどもの日")
    add(7, _nth_monday(year, 7, 3), "海の日")
    add(8, 11, "山の日")
    add(9, _nth_monday(year, 9, 3), "敬老の日")
    add(9, _autumnal_equinox(year), "秋分の日")
    add(10, _nth_monday(year, 10, 2), "スポーツの日")
    add(11, 3, "文化の日")
    add(11, 23, "勤労感謝の日")

    # 国民の休日：祝日に挟まれた平日（例：シルバーウィーク）
    with_kokumin = dict(base)
    d = _dt.date(year, 1, 1)
    one = _dt.timedelta(days=1)
    while d.year == year:
        if d not in base and d.weekday() != 6:  # 日曜は対象外
            if (d - one) in base and (d + one) in base:
                with_kokumin[d] = "国民の休日"
        d += one

    # 振替休日：祝日が日曜のとき、直後の祝日でない日を休日に
    result = dict(with_kokumin)
    for hol_date in list(with_kokumin):
        if hol_date.weekday() != 6:  # 日曜の祝日のみ
            continue
        cand = hol_date + one
        while cand in with_kokumin:
            cand += one
        result[cand] = "振替休日"

    return result


def holidays_for_fiscal_year(fiscal_year: int) -> dict[_dt.date, str]:
    """年度（4月〜翌3月）にかかる祝日をまとめて返す。"""
    result = holidays_for_year(fiscal_year)
    result.update(holidays_for_year(fiscal_year + 1))
    return result
