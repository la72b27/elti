"""Export all LT MasterList records where the same postal_code has multiple
different 'Lift Name - Linked' values (i.e. blocks with more than one LMD device).

Output: D:\TempStudy\VibeCoding\LS\export_multi_device.xlsx
"""
from __future__ import annotations
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from collections import defaultdict

LT_FILE  = r"D:\TempStudy\VibeCoding\LS\Lift Talk - MasterList.xlsx"
OUT_FILE = r"D:\TempStudy\VibeCoding\LS\export_multi_device.xlsx"

# Columns to extract (0-based index → label)
COLS = {
    2:  "TC",
    0:  "Town Council",
    3:  "Pfx",
    4:  "Block",
    7:  "Postal Code",
    9:  "Lift Names-All",
    10: "Lift Name - Linked",
    12: "LSS",
    13: "Interface",
    18: "LMD Device ID",
    25: "Full Address",
}
COL_INDICES = sorted(COLS.keys())


def _str(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()


def main() -> None:
    print(f"Reading {LT_FILE} ...")
    wb_in = openpyxl.load_workbook(LT_FILE, read_only=True, data_only=True)
    ws_in = wb_in.active

    # Load all rows keyed by postal_code
    pc_rows: dict[str, list[dict]] = defaultdict(list)
    for row in ws_in.iter_rows(min_row=2, values_only=True):
        tc = _str(row[2])
        if not tc:
            continue
        pc_raw = row[7]
        if pc_raw is None:
            continue
        try:
            pc = str(int(float(pc_raw)))
        except (ValueError, TypeError):
            pc = _str(pc_raw)
        if not pc or pc == "0":
            continue
        linked = _str(row[10])
        pc_rows[pc].append({
            "row":    row,
            "linked": linked,
        })
    wb_in.close()

    # Keep only postal_codes with 2+ distinct Lift Name - Linked values
    multi: list[tuple[str, list]] = []
    for pc, entries in sorted(pc_rows.items()):
        linked_set = {e["linked"] for e in entries}
        if len(linked_set) > 1:
            multi.append((pc, entries))

    print(f"  Found {len(multi)} postal codes with multiple Lift Name - Linked values "
          f"({sum(len(e) for _, e in multi)} total rows)")

    # Write output workbook
    wb_out = openpyxl.Workbook()
    ws_out = wb_out.active
    ws_out.title = "Multi-Device Blocks"

    # Header style
    hdr_font  = Font(bold=True, color="FFFFFF")
    hdr_fill  = PatternFill("solid", fgColor="2A007C")
    hdr_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    headers = [COLS[i] for i in COL_INDICES]
    for col_num, label in enumerate(headers, start=1):
        cell = ws_out.cell(row=1, column=col_num, value=label)
        cell.font      = hdr_font
        cell.fill      = hdr_fill
        cell.alignment = hdr_align

    # Alternating fill per postal_code group
    fill_a = PatternFill("solid", fgColor="F0EEFF")  # light purple
    fill_b = PatternFill("solid", fgColor="FFFFFF")   # white

    row_num = 2
    for idx, (pc, entries) in enumerate(multi):
        grp_fill = fill_a if idx % 2 == 0 else fill_b
        for entry in entries:
            raw = entry["row"]
            for col_num, col_idx in enumerate(COL_INDICES, start=1):
                val = _str(raw[col_idx]) if col_idx < len(raw) else ""
                cell = ws_out.cell(row=row_num, column=col_num, value=val)
                cell.fill = grp_fill
            row_num += 1

    # Auto-width
    for col_num, label in enumerate(headers, start=1):
        max_len = len(label)
        for r in ws_out.iter_rows(min_row=2, max_row=row_num - 1,
                                   min_col=col_num, max_col=col_num):
            for cell in r:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
        ws_out.column_dimensions[get_column_letter(col_num)].width = min(max_len + 2, 40)

    ws_out.freeze_panes = "A2"
    wb_out.save(OUT_FILE)
    print(f"Saved → {OUT_FILE}  ({row_num - 2} rows, {len(multi)} blocks)")


if __name__ == "__main__":
    main()
