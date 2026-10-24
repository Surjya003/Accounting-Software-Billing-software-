"""
Cash & Bank Book Business Logic Service
Tracks Cash-in-Hand, Bank account balances, receipts, payments, and contra entries.
Inspired by TallyPrime's Cash Book / Bank Book and Vyapar's Cash & Bank management.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, and_

from app.database.connection import get_session
from app.database.models import BankAccount, CashBankTransaction, Party


def ensure_default_accounts():
    """Creates default Cash-in-Hand account if none exist."""
    with get_session() as session:
        cash = session.query(BankAccount).filter(
            BankAccount.account_type == "Cash",
            BankAccount.account_name == "Cash-in-Hand"
        ).first()
        if not cash:
            cash = BankAccount(
                account_name="Cash-in-Hand",
                account_type="Cash",
                opening_balance=Decimal("0.00"),
                is_active=True,
            )
            session.add(cash)
            session.commit()


def get_all_accounts(include_inactive: bool = False) -> List[Dict[str, Any]]:
    """Returns all bank/cash accounts with current balance."""
    ensure_default_accounts()
    with get_session() as session:
        query = session.query(BankAccount)
        if not include_inactive:
            query = query.filter(BankAccount.is_active.is_(True))
        accounts = query.order_by(BankAccount.account_type.asc(), BankAccount.account_name.asc()).all()

        result = []
        for acc in accounts:
            d = acc.to_dict()
            # Calculate current balance
            receipts = session.query(func.sum(CashBankTransaction.receipt_amount)).filter(
                CashBankTransaction.account_id == acc.id
            ).scalar() or Decimal("0.00")
            payments = session.query(func.sum(CashBankTransaction.payment_amount)).filter(
                CashBankTransaction.account_id == acc.id
            ).scalar() or Decimal("0.00")
            current_balance = (acc.opening_balance or Decimal("0.00")) + receipts - payments
            d['current_balance'] = float(current_balance)
            d['total_receipts'] = float(receipts)
            d['total_payments'] = float(payments)
            result.append(d)
        return result


def create_account(data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new bank/cash account."""
    name = (data.get("account_name") or "").strip()
    if not name:
        raise ValueError("Account name is required.")

    with get_session() as session:
        acc = BankAccount(
            account_name=name,
            account_type=data.get("account_type", "Bank"),
            bank_name=(data.get("bank_name") or "").strip(),
            account_number=(data.get("account_number") or "").strip(),
            ifsc_code=(data.get("ifsc_code") or "").strip().upper(),
            branch=(data.get("branch") or "").strip(),
            opening_balance=Decimal(str(data.get("opening_balance", 0))),
            opening_balance_date=data.get("opening_balance_date", date.today()),
        )
        session.add(acc)
        session.commit()
        session.refresh(acc)
        return acc.to_dict()


def create_transaction(data: Dict[str, Any]) -> Dict[str, Any]:
    """Records a cash/bank transaction."""
    desc_text = (data.get("description") or "").strip()
    if not desc_text:
        raise ValueError("Transaction description is required.")
    if not data.get("account_id"):
        raise ValueError("Account is required.")

    txn_type = data.get("txn_type", "Receipt")
    receipt_amt = Decimal(str(data.get("receipt_amount", 0)))
    payment_amt = Decimal(str(data.get("payment_amount", 0)))

    if txn_type == "Receipt" and receipt_amt <= 0:
        raise ValueError("Receipt amount must be greater than zero.")
    if txn_type == "Payment" and payment_amt <= 0:
        raise ValueError("Payment amount must be greater than zero.")

    with get_session() as session:
        txn = CashBankTransaction(
            account_id=data["account_id"],
            txn_date=data.get("txn_date", date.today()),
            txn_type=txn_type,
            party_id=data.get("party_id"),
            description=desc_text,
            receipt_amount=receipt_amt,
            payment_amount=payment_amt,
            reference_no=(data.get("reference_no") or "").strip(),
            voucher_id=data.get("voucher_id"),
            contra_account_id=data.get("contra_account_id"),
            notes=(data.get("notes") or "").strip(),
        )
        session.add(txn)

        # Automatic mirror entry for Contra transfer between accounts
        if txn_type == "Contra" and data.get("contra_account_id"):
            primary_acc = session.get(BankAccount, data["account_id"])
            mirror_receipt = payment_amt
            mirror_payment = receipt_amt
            contra_desc = f"Contra Transfer with {primary_acc.account_name if primary_acc else 'Account'}"
            mirror_txn = CashBankTransaction(
                account_id=data["contra_account_id"],
                txn_date=data.get("txn_date", date.today()),
                txn_type="Contra",
                party_id=data.get("party_id"),
                description=contra_desc,
                receipt_amount=mirror_receipt,
                payment_amount=mirror_payment,
                reference_no=(data.get("reference_no") or "").strip(),
                contra_account_id=data["account_id"],
                notes=(data.get("notes") or "").strip(),
            )
            session.add(mirror_txn)

        session.commit()
        session.refresh(txn)
        return txn.to_dict()


def get_transactions(
    account_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    txn_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Returns filtered transactions."""
    with get_session() as session:
        query = session.query(CashBankTransaction)
        if account_id:
            query = query.filter(CashBankTransaction.account_id == account_id)
        if start_date:
            query = query.filter(CashBankTransaction.txn_date >= start_date)
        if end_date:
            query = query.filter(CashBankTransaction.txn_date <= end_date)
        if txn_type:
            query = query.filter(CashBankTransaction.txn_type == txn_type)
        txns = query.order_by(desc(CashBankTransaction.txn_date), desc(CashBankTransaction.id)).all()
        return [t.to_dict() for t in txns]


def delete_transaction(txn_id: int) -> bool:
    """Deletes a transaction."""
    with get_session() as session:
        txn = session.query(CashBankTransaction).filter(CashBankTransaction.id == txn_id).first()
        if not txn:
            raise ValueError(f"Transaction #{txn_id} not found.")
        session.delete(txn)
        session.commit()
        return True


def get_account_ledger(
    account_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """Returns running balance ledger for a specific account."""
    if start_date is None:
        start_date = date.today().replace(month=1, day=1)
    if end_date is None:
        end_date = date.today()

    with get_session() as session:
        acc = session.query(BankAccount).filter(BankAccount.id == account_id).first()
        if not acc:
            raise ValueError(f"Account #{account_id} not found.")

        # Opening balance
        running_balance = float(acc.opening_balance or 0)

        # Transactions before start_date (to compute carried-forward balance)
        pre_receipts = session.query(func.sum(CashBankTransaction.receipt_amount)).filter(
            CashBankTransaction.account_id == account_id,
            CashBankTransaction.txn_date < start_date
        ).scalar() or 0
        pre_payments = session.query(func.sum(CashBankTransaction.payment_amount)).filter(
            CashBankTransaction.account_id == account_id,
            CashBankTransaction.txn_date < start_date
        ).scalar() or 0
        opening = running_balance + float(pre_receipts) - float(pre_payments)

        # Transactions in range
        txns = (
            session.query(CashBankTransaction)
            .filter(
                CashBankTransaction.account_id == account_id,
                CashBankTransaction.txn_date >= start_date,
                CashBankTransaction.txn_date <= end_date
            )
            .order_by(CashBankTransaction.txn_date.asc(), CashBankTransaction.id.asc())
            .all()
        )

        rows = []
        balance = opening
        total_receipts = 0.0
        total_payments = 0.0
        for t in txns:
            r = float(t.receipt_amount or 0)
            p = float(t.payment_amount or 0)
            balance += r - p
            total_receipts += r
            total_payments += p
            d = t.to_dict()
            d['running_balance'] = balance
            rows.append(d)

        return {
            "account": acc.to_dict(),
            "opening_balance": opening,
            "transactions": rows,
            "total_receipts": total_receipts,
            "total_payments": total_payments,
            "closing_balance": balance,
        }
