import sqlite3

con = sqlite3.connect("data/test_accounting.db")
cur = con.cursor()
cur.execute("""
    SELECT voucher_number, voucher_type, debit_amount, credit_amount, narration, payment_mode 
    FROM vouchers 
    WHERE voucher_number NOT LIKE 'INV%' 
      AND voucher_number NOT LIKE 'PUR%' 
      AND voucher_number NOT LIKE 'CN%' 
      AND voucher_number NOT LIKE 'DN%'
""")
for r in cur.fetchall():
    print(r)
con.close()
