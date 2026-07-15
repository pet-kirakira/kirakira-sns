#!/usr/bin/env python3
"""年間予定表（指定管理）を Excel(.xlsx) で生成するツール。

- 年度（4月〜翌3月）の 1〜31日 × 12ヶ月レイアウト
- 土日祝の色分け・祝日名を自動表示
- 予定は「件名・アイコン・色・期間（数日間）」に対応
  - 数日間の予定 … 同じ色でセルを縦に塗り、先頭日に件名を表示
- A3 横・1ページに収まる印刷設定
- 共同編集しやすいようセル結合はしない

使い方:
  # 空のテンプレート（Excelに直接入力する用）
  python -m nenkan_yotei.excel --year 2026 --facility "○○指定管理施設"

  # HTMLアプリで書き出したJSONから予定を流し込む
  python -m nenkan_yotei.excel --input nenkan_yotei_2026.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

try:
    from .holidays import holidays_for_fiscal_year
except ImportError:  # スクリプトとして直接実行された場合
    from holidays import holidays_for_fiscal_year  # type: ignore

FISCAL_MONTHS = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
WD_JP = ["月", "火", "水", "木", "金", "土", "日"]  # date.weekday(): 月=0 ... 日=6
DEFAULT_COLOR = "4A90D9"

# 色（塗り・文字）
SUN_FILL = "FDEAEA"
SAT_FILL = "EAF1FC"
HOL_FILL = "FBE3E3"
INVALID_FILL = "F0F0F0"
HEADER_FILL = "2C3E50"
DAYCOL_FILL = "F4F6F8"
SUN_FONT = "D23C3C"
SAT_FONT = "2F6FD0"

THIN = Side(style="thin", color="BBBBBB")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def reiwa(fy: int) -> str:
    r = fy - 2018  # 令和元年 = 2019
    return "元" if r == 1 else str(r)


def _hex(color: str) -> str:
    """'#RRGGBB' / 'RRGGBB' を 'RRGGBB' に正規化。"""
    return color.lstrip("#").upper()[:6].rjust(6, "0")


def tint(color: str, alpha: float = 0.22) -> str:
    """色を白と混ぜて淡くした 'RRGGBB' を返す（セル塗り用）。"""
    h = _hex(color)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = round(r * alpha + 255 * (1 - alpha))
    g = round(g * alpha + 255 * (1 - alpha))
    b = round(b * alpha + 255 * (1 - alpha))
    return f"{r:02X}{g:02X}{b:02X}"


def fill(rgb: str) -> PatternFill:
    return PatternFill(fill_type="solid", fgColor="FF" + rgb)


def parse_iso(s: str) -> dt.date:
    y, m, d = (int(x) for x in s.split("-"))
    return dt.date(y, m, d)


def load_events(path: Path) -> tuple[int | None, str, list[dict]]:
    """JSON（HTMLアプリの書き出し形式）を読み込む。"""
    obj = json.loads(path.read_text(encoding="utf-8"))
    fy = obj.get("fiscalYear")
    facility = obj.get("facility", "")
    raw = obj.get("events", [])
    events: list[dict] = []
    if isinstance(raw, dict):  # 旧形式 { "YYYY-MM-DD": "件名" }
        for date_s, title in raw.items():
            events.append(
                {"title": str(title), "icon": "", "color": DEFAULT_COLOR,
                 "start": date_s, "end": date_s}
            )
    else:
        for e in raw:
            events.append(
                {
                    "title": e.get("title", ""),
                    "icon": e.get("icon", ""),
                    "color": _hex(e.get("color", DEFAULT_COLOR)),
                    "start": e["start"],
                    "end": e.get("end", e["start"]),
                }
            )
    return (int(fy) if fy else None), facility, events


def events_on(events: list[dict], d: dt.date) -> list[dict]:
    """その日にかかる予定を開始日順で返す。"""
    hit = [e for e in events if parse_iso(e["start"]) <= d <= parse_iso(e["end"])]
    hit.sort(key=lambda e: (e["start"], e["title"]))
    return hit


def build_workbook(fiscal_year: int, facility: str, events: list[dict]) -> Workbook:
    holidays = holidays_for_fiscal_year(fiscal_year)

    wb = Workbook()
    ws = wb.active
    ws.title = f"令和{reiwa(fiscal_year)}年度"

    # 列レイアウト： A=日、以降は各月 [曜, 予定] の2列
    day_col = 1
    n_cols = 1 + len(FISCAL_MONTHS) * 2
    ws.column_dimensions[get_column_letter(day_col)].width = 4.5
    for i in range(len(FISCAL_MONTHS)):
        wd_col = 2 + i * 2
        ev_col = 3 + i * 2
        ws.column_dimensions[get_column_letter(wd_col)].width = 3.4
        ws.column_dimensions[get_column_letter(ev_col)].width = 13.5

    last_col_letter = get_column_letter(n_cols)

    # 1行目：タイトル
    ws.merge_cells(f"A1:{last_col_letter}1")
    t = ws["A1"]
    t.value = f"令和{reiwa(fiscal_year)}年度　年間予定表"
    t.font = Font(size=18, bold=True)
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # 2行目：施設名・期間
    ws.merge_cells(f"A2:{last_col_letter}2")
    sub = f"{fiscal_year}年4月 〜 {fiscal_year + 1}年3月"
    if facility:
        sub = f"【{facility}】　" + sub
    s = ws["A2"]
    s.value = sub
    s.font = Font(size=11, color="555555")
    s.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 18

    header_font = Font(size=11, bold=True, color="FFFFFF")
    center = Alignment(horizontal="center", vertical="center")

    # 3行目：月見出し（曜+予定を結合）／ A3:A4 に「日」
    ws.merge_cells("A3:A4")
    a3 = ws["A3"]
    a3.value = "日"
    a3.font = header_font
    a3.fill = fill(HEADER_FILL)
    a3.alignment = center
    a3.border = BORDER
    ws["A4"].border = BORDER
    ws["A4"].fill = fill(HEADER_FILL)

    for i, m in enumerate(FISCAL_MONTHS):
        wd_col = 2 + i * 2
        ev_col = 3 + i * 2
        c1 = get_column_letter(wd_col)
        c2 = get_column_letter(ev_col)
        ws.merge_cells(f"{c1}3:{c2}3")
        cell = ws[f"{c1}3"]
        cell.value = f"{m}月"
        cell.font = header_font
        cell.fill = fill(HEADER_FILL)
        cell.alignment = center
        for cc in (f"{c1}3", f"{c2}3", f"{c1}4", f"{c2}4"):
            ws[cc].border = BORDER
            ws[cc].fill = fill(HEADER_FILL)
        # 4行目：サブ見出し
        ws[f"{c1}4"].value = "曜"
        ws[f"{c1}4"].font = header_font
        ws[f"{c1}4"].alignment = center
        ws[f"{c2}4"].value = "予定"
        ws[f"{c2}4"].font = header_font
        ws[f"{c2}4"].alignment = center

    ws.row_dimensions[3].height = 18
    ws.row_dimensions[4].height = 15

    data_top = 5  # 1日 = 5行目
    wrap_top = Alignment(horizontal="left", vertical="top", wrap_text=True)

    # 日番号列
    for day in range(1, 32):
        row = data_top + day - 1
        c = ws.cell(row=row, column=day_col, value=day)
        c.font = Font(size=11, bold=True)
        c.fill = fill(DAYCOL_FILL)
        c.alignment = center
        c.border = BORDER
        ws.row_dimensions[row].height = 20

    # 各月・各日
    for i, m in enumerate(FISCAL_MONTHS):
        cal_year = fiscal_year if m >= 4 else fiscal_year + 1
        wd_col = 2 + i * 2
        ev_col = 3 + i * 2
        last_day = (dt.date(cal_year + (1 if m == 12 else 0), (m % 12) + 1, 1)
                    - dt.timedelta(days=1)).day

        for day in range(1, 32):
            row = data_top + day - 1
            wd_cell = ws.cell(row=row, column=wd_col)
            ev_cell = ws.cell(row=row, column=ev_col)
            wd_cell.border = BORDER
            ev_cell.border = BORDER
            wd_cell.alignment = center
            ev_cell.alignment = wrap_top

            if day > last_day:  # その月に存在しない日
                wd_cell.fill = fill(INVALID_FILL)
                ev_cell.fill = fill(INVALID_FILL)
                continue

            d = dt.date(cal_year, m, day)
            wd = d.weekday()
            hol_name = holidays.get(d)

            # 曜日
            wd_cell.value = WD_JP[wd]
            if hol_name or wd == 6:
                wd_cell.font = Font(size=10, bold=True, color=SUN_FONT)
                wd_cell.fill = fill(HOL_FILL if hol_name else SUN_FILL)
            elif wd == 5:
                wd_cell.font = Font(size=10, bold=True, color=SAT_FONT)
                wd_cell.fill = fill(SAT_FILL)
            else:
                wd_cell.font = Font(size=10, color="666666")

            # 予定
            active = events_on(events, d)
            if active:
                lead = next((e for e in active if parse_iso(e["start"]) == d), active[0])
                ev_cell.fill = fill(tint(lead["color"]))
                ev_cell.border = Border(
                    left=Side(style="medium", color="FF" + _hex(lead["color"])),
                    right=THIN, top=THIN, bottom=THIN,
                )
                lines = []
                for e in active:
                    if parse_iso(e["start"]) == d or day == 1:  # 各月セグメントの先頭で件名表示
                        label = (f"{e['icon']} " if e["icon"] else "") + e["title"]
                        lines.append(label.strip())
                ev_cell.value = "\n".join(lines)
                ev_cell.font = Font(size=9)
            elif hol_name:
                ev_cell.value = hol_name
                ev_cell.font = Font(size=9, color=SUN_FONT)
                ev_cell.fill = fill(HOL_FILL)
            elif wd == 6:
                ev_cell.fill = fill(SUN_FILL)
            elif wd == 5:
                ev_cell.fill = fill(SAT_FILL)

    # 表示・印刷設定
    ws.freeze_panes = "B5"
    ws.print_title_rows = "1:4"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A3  # A3
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_margins.left = ws.page_margins.right = 0.3
    ws.page_margins.top = ws.page_margins.bottom = 0.4
    ws.print_options.horizontalCentered = True

    return wb


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="年間予定表(指定管理) Excel 生成ツール")
    parser.add_argument("--year", type=int, help="年度（西暦・4月始まり）。省略時は当年度")
    parser.add_argument("--facility", default=None, help="施設名 / 事業名")
    parser.add_argument("--input", type=Path, help="予定JSON（HTMLアプリの書き出し）")
    parser.add_argument("--output", type=Path, help="出力先 .xlsx")
    args = parser.parse_args(argv)

    fy_json = None
    facility = args.facility or ""
    events: list[dict] = []
    if args.input:
        if not args.input.exists():
            print(f"入力ファイルが見つかりません: {args.input}", file=sys.stderr)
            sys.exit(1)
        fy_json, fac_json, events = load_events(args.input)
        if args.facility is None:
            facility = fac_json

    today = dt.date.today()
    default_fy = today.year if today.month >= 4 else today.year - 1
    fiscal_year = args.year or fy_json or default_fy

    output = args.output or Path(f"nenkan_yotei_{fiscal_year}.xlsx")
    wb = build_workbook(fiscal_year, facility, events)
    wb.save(output)
    print(f"作成しました: {output}（令和{reiwa(fiscal_year)}年度 / 予定 {len(events)} 件）")


if __name__ == "__main__":
    main()
