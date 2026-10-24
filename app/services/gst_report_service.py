"""
GST Reporting Service: GSTR-1, GSTR-3B, and Government Offline Tool JSON Exports.
Implements Indian GST statutory reporting rules:
- GSTR-1: B2B (registered), B2CL (unregistered inter-state > 2.5L), B2CS (unregistered intra / small), CDNR, CDNUR, HSN summary.
- GSTR-3B: Table 3.1 Outward supplies, Table 4 Eligible ITC from purchases/expenses.
- Government JSON export schema for GST Portal Offline Tool.
"""
import json
import os
from datetime import date
from decimal import Decimal
from typing import Dict, Any, List, Optional
from collections import defaultdict
from sqlalchemy.orm import joinedload
from sqlalchemy import asc

from app.database.connection import get_session
from app.database.models import Invoice, InvoiceItem, Party, CompanyProfile, Voucher, VoucherItem, SalesReturn, PurchaseReturn
from app.config import (
    EXPORTS_DIR,
    VOUCHER_CREDIT, VOUCHER_DEBIT
)


def _to_decimal(val) -> Decimal:
    if val is None:
        return Decimal("0.00")
    return Decimal(str(val))


def _clean_str(val) -> str:
    return str(val).strip() if val else ""


def is_valid_gstin(gstin: Optional[str]) -> bool:
    if not gstin:
        return False
    gstin = gstin.strip().upper()
    return len(gstin) == 15 and gstin[:2].isdigit() and gstin[2:12].isalnum()


# Statutory B2CL Threshold History table
# Inter-state supplies to unregistered persons exceeding this threshold are classified as B2CL (Table 5 of GSTR-1).
# CBIC Notification No. 12/2024 - Central Tax (effective 1 Aug 2024) reduced the threshold from Rs. 2.5 Lakh to Rs. 1.0 Lakh.
B2CL_THRESHOLD_HISTORY = [
    (date(2024, 8, 1), Decimal("100000.00")),   # Rs. 1.0 Lakh from 1 Aug 2024 onwards
    (date(2017, 7, 1), Decimal("250000.00")),   # Rs. 2.5 Lakh prior to 1 Aug 2024
]

def get_b2cl_threshold(doc_date: Optional[date] = None) -> Decimal:
    """
    Returns the statutory B2CL threshold based on the invoice/document date.
    - On or after 1 August 2024: Rs. 1,00,000 (Notification 12/2024 - Central Tax)
    - Prior to 1 August 2024: Rs. 2,50,000
    """
    if doc_date is None:
        doc_date = date.today()
    for eff_date, threshold in B2CL_THRESHOLD_HISTORY:
        if doc_date >= eff_date:
            return threshold
    return Decimal("250000.00")


def get_gstr1_data(from_date: date, to_date: date) -> Dict[str, Any]:
    """
    Computes GSTR-1 outward supply data structured into official categories:
    - B2B: Supplies to registered taxable persons
    - B2CL: Large inter-state supplies to unregistered persons (invoice value > statutory threshold: Rs 1.0L since 01-Aug-2024, Rs 2.5L earlier)
    - B2CS: Other supplies to unregistered persons (intra-state or inter-state <= statutory threshold)
    - CDNR: Credit/debit notes issued to registered persons
    - CDNUR: Credit/debit notes issued to unregistered persons
    - HSN: HSN/SAC summary of outward supplies
    - Flat 'rows' list for backward compatibility with UI views.
    """
    with get_session() as session:
        company = session.query(CompanyProfile).first()
        company_state_code = company.state_code.strip() if (company and company.state_code) else "27"
        company_gstin = company.gstin.strip().upper() if (company and company.gstin) else ""

        invoices = (
            session.query(Invoice)
            .options(joinedload(Invoice.items), joinedload(Invoice.party))
            .filter(
                Invoice.invoice_date >= from_date,
                Invoice.invoice_date <= to_date,
                Invoice.status != "cancelled"
            )
            .order_by(asc(Invoice.invoice_date), asc(Invoice.id))
            .all()
        )

        b2b_list = []
        b2cl_list = []
        b2cs_map = defaultdict(lambda: {
            "pos": "",
            "sply_ty": "INTER" if False else "INTRA",
            "txval": Decimal("0.00"),
            "rt": Decimal("0.00"),
            "iamt": Decimal("0.00"),
            "camt": Decimal("0.00"),
            "samt": Decimal("0.00"),
            "csamt": Decimal("0.00")
        })
        hsn_map = defaultdict(lambda: {
            "hsn_sc": "",
            "desc": "",
            "uqc": "OTH",
            "qty": Decimal("0.00"),
            "txval": Decimal("0.00"),
            "iamt": Decimal("0.00"),
            "camt": Decimal("0.00"),
            "samt": Decimal("0.00"),
            "csamt": Decimal("0.00")
        })

        all_rows = []
        tot_taxable = Decimal("0.00")
        tot_cgst = Decimal("0.00")
        tot_sgst = Decimal("0.00")
        tot_igst = Decimal("0.00")
        tot_val = Decimal("0.00")

        for inv in invoices:
            party = inv.party
            party_gstin = (party.gstin or "").strip().upper() if party else ""
            has_gstin = is_valid_gstin(party_gstin)
            party_state_code = (party.state_code or "").strip() if party else company_state_code
            if not party_state_code and has_gstin:
                party_state_code = party_gstin[:2]
            
            is_interstate = (party_state_code != company_state_code) and bool(party_state_code)
            inv_total = _to_decimal(inv.total_amount)
            taxable = _to_decimal(inv.subtotal)
            cgst = _to_decimal(getattr(inv, "cgst_total", 0))
            sgst = _to_decimal(getattr(inv, "sgst_total", 0))
            igst = _to_decimal(getattr(inv, "igst_total", 0))

            tot_taxable += taxable
            tot_cgst += cgst
            tot_sgst += sgst
            tot_igst += igst
            tot_val += inv_total

            threshold = get_b2cl_threshold(inv.invoice_date)
            is_b2cl = is_interstate and (not has_gstin) and (inv_total > threshold)
            row_category = "B2B" if has_gstin else ("B2CL" if is_b2cl else "B2CS")

            row_dict = {
                "voucher_number": inv.invoice_number,
                "invoice_number": inv.invoice_number,
                "voucher_date": inv.invoice_date,
                "invoice_date": inv.invoice_date,
                "party_name": party.name if party else "Walk-in Customer",
                "party_gstin": party_gstin or "URP",
                "party_state": party.state if party else "",
                "party_state_code": party_state_code,
                "category": row_category,
                "taxable_value": float(taxable),
                "cgst": float(cgst),
                "sgst": float(sgst),
                "igst": float(igst),
                "total_tax": float(cgst + sgst + igst),
                "total_value": float(inv_total)
            }
            all_rows.append(row_dict)

            # Group into GSTR-1 Sections
            if has_gstin:
                # B2B
                b2b_list.append({
                    "ctin": party_gstin,
                    "cname": party.name if party else "",
                    "inv": [{
                        "inum": inv.invoice_number,
                        "idt": inv.invoice_date.strftime("%d-%m-%Y"),
                        "val": float(inv_total),
                        "pos": party_state_code,
                        "rchrg": "N",
                        "inv_typ": "R",
                        "itms": [
                            {
                                "num": idx + 1,
                                "itm_det": {
                                    "txval": float(_to_decimal(item.taxable_value)),
                                    "rt": float(_to_decimal(getattr(item, "gst_rate_pct", getattr(item, "tax_rate", 0)))),
                                    "iamt": float(_to_decimal(item.igst_amount)),
                                    "camt": float(_to_decimal(item.cgst_amount)),
                                    "samt": float(_to_decimal(item.sgst_amount)),
                                    "csamt": 0.0
                                }
                            }
                            for idx, item in enumerate(inv.items)
                        ]
                    }]
                })
            elif is_b2cl:
                # B2CL
                b2cl_list.append({
                    "pos": party_state_code,
                    "inv": [{
                        "inum": inv.invoice_number,
                        "idt": inv.invoice_date.strftime("%d-%m-%Y"),
                        "val": float(inv_total),
                        "itms": [
                            {
                                "num": idx + 1,
                                "itm_det": {
                                    "txval": float(_to_decimal(item.taxable_value)),
                                    "rt": float(_to_decimal(getattr(item, "gst_rate_pct", getattr(item, "tax_rate", 0)))),
                                    "iamt": float(_to_decimal(item.igst_amount)),
                                    "csamt": 0.0
                                }
                            }
                            for idx, item in enumerate(inv.items)
                        ]
                    }]
                })
            else:
                # B2CS (summarized by rate and POS)
                for item in inv.items:
                    rate = _to_decimal(getattr(item, "gst_rate_pct", getattr(item, "tax_rate", 0)))
                    key = (party_state_code, rate, "INTER" if is_interstate else "INTRA")
                    entry = b2cs_map[key]
                    entry["pos"] = party_state_code
                    entry["sply_ty"] = "INTER" if is_interstate else "INTRA"
                    entry["rt"] = rate
                    entry["txval"] += _to_decimal(item.taxable_value)
                    entry["iamt"] += _to_decimal(item.igst_amount)
                    entry["camt"] += _to_decimal(item.cgst_amount)
                    entry["samt"] += _to_decimal(item.sgst_amount)

            # HSN summary
            for item in inv.items:
                hsn = (item.hsn_code or "9999").strip()
                h_entry = hsn_map[hsn]
                h_entry["hsn_sc"] = hsn
                h_entry["desc"] = (item.item_description or "General Goods")[:30]
                h_entry["qty"] += _to_decimal(item.quantity)
                h_entry["txval"] += _to_decimal(item.taxable_value)
                h_entry["iamt"] += _to_decimal(item.igst_amount)
                h_entry["camt"] += _to_decimal(item.cgst_amount)
                h_entry["samt"] += _to_decimal(item.sgst_amount)

        # Sales returns (Credit notes for CDNR / CDNUR)
        returns = (
            session.query(SalesReturn)
            .options(joinedload(SalesReturn.party), joinedload(SalesReturn.items))
            .filter(
                SalesReturn.return_date >= from_date,
                SalesReturn.return_date <= to_date
            )
            .all()
        )
        cdnr_list = []
        cdnur_list = []
        for ret in returns:
            party = ret.party
            party_gstin = (party.gstin or "").strip().upper() if party else ""
            has_gstin = is_valid_gstin(party_gstin)
            ret_total = _to_decimal(ret.total_amount)
            taxable = _to_decimal(getattr(ret, "subtotal", 0))
            cgst = _to_decimal(getattr(ret, "cgst_amount", 0))
            sgst = _to_decimal(getattr(ret, "sgst_amount", 0))
            igst = _to_decimal(getattr(ret, "igst_amount", 0))

            note_dict = {
                "nt_num": ret.return_number,
                "nt_dt": ret.return_date.strftime("%d-%m-%Y"),
                "val": float(ret_total),
                "txval": float(taxable),
                "iamt": float(igst),
                "camt": float(cgst),
                "samt": float(sgst)
            }
            if has_gstin:
                cdnr_list.append({"ctin": party_gstin, "cname": party.name if party else "", "notes": [note_dict]})
            else:
                cdnur_list.append(note_dict)

        b2cs_formatted = [
            {
                "sply_ty": v["sply_ty"],
                "pos": v["pos"],
                "rt": float(v["rt"]),
                "txval": float(v["txval"]),
                "iamt": float(v["iamt"]),
                "camt": float(v["camt"]),
                "samt": float(v["samt"]),
                "csamt": 0.0
            }
            for v in b2cs_map.values()
        ]

        hsn_formatted = [
            {
                "num": idx + 1,
                "hsn_sc": v["hsn_sc"],
                "desc": v["desc"],
                "uqc": v["uqc"],
                "qty": float(v["qty"]),
                "txval": float(v["txval"]),
                "iamt": float(v["iamt"]),
                "camt": float(v["camt"]),
                "samt": float(v["samt"]),
                "csamt": 0.0
            }
            for idx, v in enumerate(hsn_map.values())
        ]

        return {
            "report_name": "GSTR-1 Outward Supplies",
            "company_gstin": company_gstin,
            "from_date": from_date,
            "to_date": to_date,
            "rows": all_rows,
            "b2b": b2b_list,
            "b2cl": b2cl_list,
            "b2cs": b2cs_formatted,
            "cdnr": cdnr_list,
            "cdnur": cdnur_list,
            "hsn": {"data": hsn_formatted},
            "total_taxable": float(tot_taxable),
            "total_cgst": float(tot_cgst),
            "total_sgst": float(tot_sgst),
            "total_igst": float(tot_igst),
            "total_tax": float(tot_cgst + tot_sgst + tot_igst),
            "total_value": float(tot_val),
            "invoice_count": len(invoices)
        }


def get_gstr3b_data(from_date: date, to_date: date) -> Dict[str, Any]:
    """
    Computes GSTR-3B monthly return feeder summary:
    - Table 3.1: Outward supplies and inward supplies liable to reverse charge
    - Table 4: Eligible ITC (Input Tax Credit) from purchases and supplier vouchers.
    """
    # 1. Outward supplies from GSTR-1
    gstr1 = get_gstr1_data(from_date, to_date)
    outward_taxable = gstr1["total_taxable"]
    outward_cgst = gstr1["total_cgst"]
    outward_sgst = gstr1["total_sgst"]
    outward_igst = gstr1["total_igst"]

    # 2. Inward supplies (Purchases/Vouchers with Credit to Suppliers)
    with get_session() as session:
        vouchers = (
            session.query(Voucher)
            .filter(
                Voucher.voucher_type == VOUCHER_CREDIT,
                Voucher.voucher_date >= from_date,
                Voucher.voucher_date <= to_date
            )
            .all()
        )
        itc_taxable = Decimal("0.00")
        itc_cgst = Decimal("0.00")
        itc_sgst = Decimal("0.00")
        itc_igst = Decimal("0.00")

        for v in vouchers:
            itc_taxable += _to_decimal(v.amount_untaxed)
            itc_cgst += _to_decimal(v.cgst_amount)
            itc_sgst += _to_decimal(v.sgst_amount)
            itc_igst += _to_decimal(v.igst_amount)

    table_3_1 = {
        "outward_taxable_supplies": {
            "txval": outward_taxable,
            "iamt": outward_igst,
            "camt": outward_cgst,
            "samt": outward_sgst,
            "csamt": 0.0
        },
        "zero_rated_supplies": {"txval": 0.0, "iamt": 0.0, "csamt": 0.0},
        "nil_rated_exempt": {"txval": 0.0},
        "inward_rcm": {"txval": 0.0, "iamt": 0.0, "camt": 0.0, "samt": 0.0, "csamt": 0.0},
        "non_gst_supplies": {"txval": 0.0}
    }

    table_4_itc = {
        "itc_available": {
            "import_goods": {"iamt": 0.0, "csamt": 0.0},
            "import_services": {"iamt": 0.0, "csamt": 0.0},
            "inward_rcm": {"iamt": 0.0, "camt": 0.0, "samt": 0.0, "csamt": 0.0},
            "isd": {"iamt": 0.0, "camt": 0.0, "samt": 0.0, "csamt": 0.0},
            "all_other_itc": {
                "iamt": float(itc_igst),
                "camt": float(itc_cgst),
                "samt": float(itc_sgst),
                "csamt": 0.0
            }
        },
        "itc_reversed": {
            "rule_42_43": {"iamt": 0.0, "camt": 0.0, "samt": 0.0, "csamt": 0.0},
            "other": {"iamt": 0.0, "camt": 0.0, "samt": 0.0, "csamt": 0.0}
        },
        "net_itc": {
            "iamt": float(itc_igst),
            "camt": float(itc_cgst),
            "samt": float(itc_sgst),
            "csamt": 0.0
        }
    }

    # Tax Payable = Outward Tax - Net ITC
    payable_igst = max(0.0, outward_igst - float(itc_igst))
    payable_cgst = max(0.0, outward_cgst - float(itc_cgst))
    payable_sgst = max(0.0, outward_sgst - float(itc_sgst))

    return {
        "report_name": "GSTR-3B Summary",
        "from_date": from_date,
        "to_date": to_date,
        "table_3_1": table_3_1,
        "table_4_itc": table_4_itc,
        "tax_liability": {
            "payable_igst": payable_igst,
            "payable_cgst": payable_cgst,
            "payable_sgst": payable_sgst,
            "total_payable": payable_igst + payable_cgst + payable_sgst
        }
    }


def export_gstr1_offline_json(from_date: date, to_date: date, output_path: Optional[str] = None) -> str:
    """
    Exports GSTR-1 in the official JSON format required by GST Offline Tool v1.3+.
    """
    data = get_gstr1_data(from_date, to_date)
    # Return period format: MMYYYY (e.g., 042026)
    fp = to_date.strftime("%m%Y")
    
    payload = {
        "gstin": data["company_gstin"] or "URP",
        "fp": fp,
        "version": "GST1.3",
        "hash": "hash_placeholder",
        "b2b": data["b2b"],
        "b2cl": data["b2cl"],
        "b2cs": data["b2cs"],
        "cdnr": data["cdnr"],
        "cdnur": data["cdnur"],
        "hsn": data["hsn"]
    }

    if not output_path:
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        fname = f"GSTR1_{data['company_gstin'] or 'EXPORT'}_{fp}.json"
        output_path = os.path.join(EXPORTS_DIR, fname)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return output_path
