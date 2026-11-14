"""
DataSentinel QA - Enterprise Excel (.xlsx) I/O Engine
Provides high-performance reading and multi-sheet styled export using openpyxl.
Zero pandas dependency; light, lightning fast, and beautiful.
"""

import os
import io
from datetime import datetime
from typing import List, Dict, Tuple, Any, Optional

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

class ExcelIO:
    @staticmethod
    def read_excel(file_source, sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Reads an Excel file (.xlsx) from a file path or bytes-like object.
        If sheet_name is None, smartly checks for 'Clean_Data' or first data sheet.
        Returns a list of dictionaries with stringified values.
        """
        if isinstance(file_source, (bytes, bytearray)):
            wb = openpyxl.load_workbook(io.BytesIO(file_source), data_only=True)
        else:
            wb = openpyxl.load_workbook(file_source, data_only=True)

        if sheet_name and sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
        elif "Clean_Data" in wb.sheetnames:
            sheet = wb["Clean_Data"]
        else:
            sheet = wb.active

        rows = list(sheet.iter_rows(values_only=True))
        if not rows or len(rows) < 2:
            return []

        # Find header row (first non-empty row)
        header_row_idx = 0
        for idx, r in enumerate(rows):
            if any(cell is not None and str(cell).strip() != "" for cell in r):
                header_row_idx = idx
                break

        raw_headers = rows[header_row_idx]
        headers = [str(h).strip() if h is not None and str(h).strip() != "" else f"col_{i+1}" for i, h in enumerate(raw_headers)]

        dataset = []
        for row in rows[header_row_idx + 1:]:
            if all(v is None or str(v).strip() == "" for v in row):
                continue
            row_dict = {}
            for i, h in enumerate(headers):
                val = row[i] if i < len(row) else ""
                if val is None:
                    row_dict[h] = ""
                elif isinstance(val, datetime):
                    row_dict[h] = val.strftime("%Y-%m-%d")
                else:
                    row_dict[h] = str(val).strip()
            dataset.append(row_dict)

        return dataset

    @staticmethod
    def create_audit_workbook(
        clean_rows: List[Dict[str, Any]],
        quarantined_records: List[Dict[str, Any]],
        summary_metrics: Dict[str, Any] = None
    ) -> openpyxl.Workbook:
        """
        Builds a styled multi-tab Excel workbook:
        1. Summary Dashboard (KPIs, Pass/Fail Rates)
        2. Clean_Production_Data (Formatted table, ready for loading)
        3. Quarantine_Dead_Letter (Violations, error reasons, raw values)
        """
        wb = openpyxl.Workbook()
        ws_summary = wb.active
        ws_summary.title = "Audit_Summary"
        ws_summary.views.sheetView[0].showGridLines = True

        # Styles
        font_title = Font(name="Segoe UI", size=16, bold=True, color="1E293B")
        font_subtitle = Font(name="Segoe UI", size=10, italic=True, color="64748B")
        font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        font_body = Font(name="Segoe UI", size=10, color="0F172A")
        font_bold = Font(name="Segoe UI", size=10, bold=True, color="0F172A")
        font_kpi_num = Font(name="Segoe UI", size=20, bold=True, color="0F172A")

        fill_navy = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        fill_teal = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
        fill_crimson = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid")
        fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        fill_quarantine_row = PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid")
        fill_kpi_card = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

        thin_border = Border(
            left=Side(style='thin', color='E2E8F0'),
            right=Side(style='thin', color='E2E8F0'),
            top=Side(style='thin', color='E2E8F0'),
            bottom=Side(style='thin', color='E2E8F0')
        )

        align_center = Alignment(horizontal="center", vertical="center")

        # ----------------- SHEET 1: AUDIT SUMMARY -----------------
        ws_summary["B2"] = "DataSentinel QA - Pipeline Audit Certificate"
        ws_summary["B2"].font = font_title
        ws_summary["B3"] = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Engine: Enterprise Data QA Suite v2.0"
        ws_summary["B3"].font = font_subtitle

        total_rows = len(clean_rows) + len(quarantined_records)
        clean_count = len(clean_rows)
        quarantine_count = len(quarantined_records)
        pass_rate = round((clean_count / (total_rows or 1)) * 100, 2)

        # KPI Block 1: Total
        ws_summary.merge_cells("B5:C5")
        ws_summary["B5"] = "TOTAL RECORDS"
        ws_summary["B5"].font = Font(name="Segoe UI", size=9, bold=True, color="64748B")
        ws_summary["B5"].alignment = align_center
        ws_summary["B5"].fill = fill_kpi_card

        ws_summary.merge_cells("B6:C6")
        ws_summary["B6"] = total_rows
        ws_summary["B6"].font = font_kpi_num
        ws_summary["B6"].alignment = align_center
        ws_summary["B6"].fill = fill_kpi_card

        # KPI Block 2: Clean
        ws_summary.merge_cells("D5:E5")
        ws_summary["D5"] = "CLEAN & COMMITTED"
        ws_summary["D5"].font = Font(name="Segoe UI", size=9, bold=True, color="047857")
        ws_summary["D5"].alignment = align_center
        ws_summary["D5"].fill = fill_kpi_card

        ws_summary.merge_cells("D6:E6")
        ws_summary["D6"] = clean_count
        ws_summary["D6"].font = Font(name="Segoe UI", size=20, bold=True, color="047857")
        ws_summary["D6"].alignment = align_center
        ws_summary["D6"].fill = fill_kpi_card

        # KPI Block 3: Quarantined
        ws_summary.merge_cells("F5:G5")
        ws_summary["F5"] = "QUARANTINED (DIRTY)"
        ws_summary["F5"].font = Font(name="Segoe UI", size=9, bold=True, color="B91C1C")
        ws_summary["F5"].alignment = align_center
        ws_summary["F5"].fill = fill_kpi_card

        ws_summary.merge_cells("F6:G6")
        ws_summary["F6"] = quarantine_count
        ws_summary["F6"].font = Font(name="Segoe UI", size=20, bold=True, color="B91C1C")
        ws_summary["F6"].alignment = align_center
        ws_summary["F6"].fill = fill_kpi_card

        # KPI Block 4: Pass Rate
        ws_summary.merge_cells("H5:I5")
        ws_summary["H5"] = "PASS RATE %"
        ws_summary["H5"].font = Font(name="Segoe UI", size=9, bold=True, color="1D4ED8")
        ws_summary["H5"].alignment = align_center
        ws_summary["H5"].fill = fill_kpi_card

        ws_summary.merge_cells("H6:I6")
        ws_summary["H6"] = f"{pass_rate}%"
        ws_summary["H6"].font = Font(name="Segoe UI", size=20, bold=True, color="1D4ED8")
        ws_summary["H6"].alignment = align_center
        ws_summary["H6"].fill = fill_kpi_card

        # Table of Summary Parameters
        ws_summary["B9"] = "Audit Parameter"
        ws_summary["C9"] = "Observed Value"
        ws_summary["B9"].font = font_header
        ws_summary["B9"].fill = fill_navy
        ws_summary["C9"].font = font_header
        ws_summary["C9"].fill = fill_navy

        summary_rows = [
            ("Execution Status", "PASSED WITH QUARANTINE" if quarantine_count > 0 else "100% CLEAN"),
            ("Data Integrity Standard", "Zero-Tolerance Schema & Primary Key Unique"),
            ("Auto-Sanitization Applied", "Myanmar Numeral Conversion, ISO Dates, E.164 Phones"),
            ("Dead-Letter Destination", "Quarantine_Audit Table & Sheet"),
            ("Data Warehouse Compatibility", "SQLite / PostgreSQL / DuckDB Parquet Ready")
        ]

        curr_r = 10
        for param, val in summary_rows:
            ws_summary[f"B{curr_r}"] = param
            ws_summary[f"C{curr_r}"] = val
            ws_summary[f"B{curr_r}"].font = font_bold
            ws_summary[f"C{curr_r}"].font = font_body
            ws_summary[f"B{curr_r}"].border = thin_border
            ws_summary[f"C{curr_r}"].border = thin_border
            curr_r += 1

        ws_summary.column_dimensions["A"].width = 4
        ws_summary.column_dimensions["B"].width = 30
        ws_summary.column_dimensions["C"].width = 50
        for col_l in ["D", "E", "F", "G", "H", "I"]:
            ws_summary.column_dimensions[col_l].width = 16

        # ----------------- SHEET 2: CLEAN DATA -----------------
        ws_clean = wb.create_sheet(title="Clean_Data")
        ws_clean.views.sheetView[0].showGridLines = True

        if clean_rows:
            headers = list(clean_rows[0].keys())
            for col_idx, h in enumerate(headers, 1):
                cell = ws_clean.cell(row=1, column=col_idx, value=h)
                cell.font = font_header
                cell.fill = fill_teal
                cell.alignment = align_center

            for row_idx, r_dict in enumerate(clean_rows, 2):
                is_even = (row_idx % 2 == 0)
                for col_idx, h in enumerate(headers, 1):
                    val = r_dict.get(h, "")
                    cell = ws_clean.cell(row=row_idx, column=col_idx, value=val)
                    cell.font = font_body
                    cell.border = thin_border
                    if is_even:
                        cell.fill = fill_zebra

            for col in ws_clean.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws_clean.column_dimensions[col_letter].width = max(max_len + 4, 12)

        # ----------------- SHEET 3: QUARANTINE AUDIT -----------------
        ws_quarantine = wb.create_sheet(title="Quarantine_Audit")
        ws_quarantine.views.sheetView[0].showGridLines = True

        q_headers = ["Row_Index", "Violation_Reasons", "Original_Payload"]
        for col_idx, qh in enumerate(q_headers, 1):
            cell = ws_quarantine.cell(row=1, column=col_idx, value=qh)
            cell.font = font_header
            cell.fill = fill_crimson
            cell.alignment = align_center

        for row_idx, q_rec in enumerate(quarantined_records, 2):
            idx_val = q_rec.get("row_index", row_idx - 1)
            reasons = "; ".join(q_rec.get("reasons", [])) if isinstance(q_rec.get("reasons"), list) else str(q_rec.get("reasons", ""))
            payload = str(q_rec.get("payload", ""))

            c1 = ws_quarantine.cell(row=row_idx, column=1, value=idx_val)
            c2 = ws_quarantine.cell(row=row_idx, column=2, value=reasons)
            c3 = ws_quarantine.cell(row=row_idx, column=3, value=payload)

            for c in [c1, c2, c3]:
                c.font = font_body
                c.fill = fill_quarantine_row
                c.border = thin_border

        ws_quarantine.column_dimensions["A"].width = 12
        ws_quarantine.column_dimensions["B"].width = 45
        ws_quarantine.column_dimensions["C"].width = 75

        return wb

    @staticmethod
    def export_excel_bytes(clean_rows: List[Dict[str, Any]], quarantined_records: List[Dict[str, Any]]) -> bytes:
        """Returns the styled multi-sheet Excel workbook as bytes."""
        wb = ExcelIO.create_audit_workbook(clean_rows, quarantined_records)
        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()
