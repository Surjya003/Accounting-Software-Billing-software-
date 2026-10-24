"""
Independent Financial & GST Mathematics Engine
Written completely from scratch with NO IMPORTS from 'app'.
Used to verify all calculations independently before checking app outputs.
"""
from decimal import Decimal, ROUND_HALF_UP

def round_cur(val):
    return float(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def calc_line_tax(qty, rate, disc_pct, gst_pct, is_interstate):
    d_qty = Decimal(str(qty))
    d_rate = Decimal(str(rate))
    d_disc = Decimal(str(disc_pct))
    d_gst = Decimal(str(gst_pct))
    
    base = d_qty * d_rate
    discount = base * (d_disc / Decimal("100"))
    taxable = base - discount
    tax_amt = taxable * (d_gst / Decimal("100"))
    
    if is_interstate:
        cgst = Decimal("0")
        sgst = Decimal("0")
        igst = tax_amt
    else:
        cgst = tax_amt / Decimal("2")
        sgst = tax_amt / Decimal("2")
        igst = Decimal("0")
        
    total = taxable + tax_amt
    return {
        "taxable": round_cur(taxable),
        "tax_amount": round_cur(tax_amt),
        "cgst": round_cur(cgst),
        "sgst": round_cur(sgst),
        "igst": round_cur(igst),
        "total": round_cur(total)
    }

def calc_running_balance(opening_bal, opening_type, debits_list, credits_list):
    # Dr is positive (receivable), Cr is negative (payable)
    net = Decimal(str(opening_bal)) if opening_type == "Dr" else -Decimal(str(opening_bal))
    for d in debits_list:
        net += Decimal(str(d))
    for c in credits_list:
        net -= Decimal(str(c))
        
    if net >= 0:
        return {"balance": round_cur(net), "type": "Dr"}
    else:
        return {"balance": round_cur(abs(net)), "type": "Cr"}

def calc_pnl(sales_taxable, sales_returns_taxable, purchase_taxable, purchase_returns_taxable, 
             opening_stock_val, closing_stock_val, expenses_total):
    revenue = Decimal(str(sales_taxable)) - Decimal(str(sales_returns_taxable))
    net_purchases = Decimal(str(purchase_taxable)) - Decimal(str(purchase_returns_taxable))
    cogs = Decimal(str(opening_stock_val)) + net_purchases - Decimal(str(closing_stock_val))
    gross_profit = revenue - cogs
    net_profit = gross_profit - Decimal(str(expenses_total))
    
    return {
        "revenue": round_cur(revenue),
        "net_purchases": round_cur(net_purchases),
        "cogs": round_cur(cogs),
        "gross_profit": round_cur(gross_profit),
        "expenses": round_cur(expenses_total),
        "net_profit": round_cur(net_profit)
    }

def calc_ageing_bucket(invoice_date, as_of_date, amount):
    days = (as_of_date - invoice_date).days
    b0_30 = Decimal("0")
    b31_60 = Decimal("0")
    b61_90 = Decimal("0")
    b91_plus = Decimal("0")
    d_amt = Decimal(str(amount))
    
    if days <= 30:
        b0_30 = d_amt
    elif days <= 60:
        b31_60 = d_amt
    elif days <= 90:
        b61_90 = d_amt
    else:
        b91_plus = d_amt
        
    return {
        "days": days,
        "b0_30": round_cur(b0_30),
        "b31_60": round_cur(b31_60),
        "b61_90": round_cur(b61_90),
        "b91_plus": round_cur(b91_plus)
    }
