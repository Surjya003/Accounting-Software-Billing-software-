"""
GST Engine - Tax Calculation Engine for Indian GST
Ported from Billing-software/src/core/business_logic/gst_engine.py
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict
from enum import Enum


class TransactionType(Enum):
    INTRA_STATE = "Intra-state"
    INTER_STATE = "Inter-state"
    EXPORT_LUT = "Export (LUT/Bond)"
    EXPORT_IGST = "Export (IGST)"
    SEZ_LUT = "SEZ (LUT/Bond)"
    SEZ_IGST = "SEZ (IGST)"


class GSTEngine:
    """Comprehensive GST calculation engine supporting all supply types."""
    VALID_TAX_RATES = {Decimal("0"), Decimal("5"), Decimal("12"), Decimal("18"), Decimal("28")}

    @staticmethod
    def determine_transaction_type(source_state_code: str, dest_state_code: str) -> TransactionType:
        """Determine if a transaction is intra-state or inter-state based on state codes."""
        if source_state_code and dest_state_code:
            if source_state_code.strip() == dest_state_code.strip():
                return TransactionType.INTRA_STATE
            else:
                return TransactionType.INTER_STATE
        return TransactionType.INTRA_STATE

    @staticmethod
    def calculate_line_item(
        qty: Decimal,
        rate: Decimal,
        discount_percent: Decimal,
        tax_rate: Decimal,
        transaction_type: TransactionType,
        is_rcm: bool = False
    ) -> Dict[str, Decimal]:
        """
        Calculate GST for a single line item.
        
        Args:
            qty: Quantity of item
            rate: Unit price
            discount_percent: Discount percentage (0-100)
            tax_rate: GST rate (5, 12, 18, 28)
            transaction_type: Intra/Inter state
            is_rcm: Reverse Charge Mechanism flag
            
        Returns:
            Dict with base_amount, discount_amount, taxable_value, cgst_amt, sgst_amt, 
            igst_amt, total_tax, total_amount
        """
        qty = Decimal(str(qty))
        rate = Decimal(str(rate))
        discount_percent = Decimal(str(discount_percent))
        tax_rate = Decimal(str(tax_rate))

        if qty < 0 or rate < 0 or discount_percent < 0 or tax_rate < 0:
            raise ValueError("Negative values not allowed.")

        # Calculate base and discount
        base_amount = qty * rate
        discount_amount = base_amount * (discount_percent / Decimal("100"))
        taxable_value = base_amount - discount_amount
        taxable_value = taxable_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        cgst_amt = Decimal("0.00")
        sgst_amt = Decimal("0.00")
        igst_amt = Decimal("0.00")

        # Tax exemptions: RCM or Export LUT
        should_calculate_tax = not is_rcm and transaction_type not in [
            TransactionType.EXPORT_LUT, TransactionType.SEZ_LUT
        ]

        if should_calculate_tax:
            total_tax_amt = taxable_value * (tax_rate / Decimal("100"))
            total_tax_amt = total_tax_amt.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            if transaction_type == TransactionType.INTRA_STATE:
                half_tax = total_tax_amt / Decimal("2")
                half_tax = half_tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                cgst_amt = half_tax
                sgst_amt = total_tax_amt - half_tax
            else:
                igst_amt = total_tax_amt

        total_tax = cgst_amt + sgst_amt + igst_amt
        total_amount = taxable_value + total_tax

        return {
            'base_amount': base_amount,
            'discount_amount': discount_amount,
            'taxable_value': taxable_value,
            'cgst_amt': cgst_amt,
            'sgst_amt': sgst_amt,
            'igst_amt': igst_amt,
            'total_tax': total_tax,
            'total_amount': total_amount
        }

    @staticmethod
    def calculate_gst(amount: Decimal, rate: Decimal, source_state_code: str, dest_state_code: str) -> Dict[str, Decimal]:
        """
        Legacy wrapper for backward compatibility.
        Calculates GST on a single amount without quantity/discount.
        """
        t_type = GSTEngine.determine_transaction_type(source_state_code, dest_state_code)

        result = GSTEngine.calculate_line_item(
            qty=Decimal("1"),
            rate=amount,
            discount_percent=Decimal("0"),
            tax_rate=rate,
            transaction_type=t_type
        )

        return {
            'cgst': result['cgst_amt'],
            'sgst': result['sgst_amt'],
            'igst': result['igst_amt'],
            'total_tax': result['total_tax']
        }
