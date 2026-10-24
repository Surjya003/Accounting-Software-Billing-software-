import sys

with open("scratch/audit/phase2_modules_audit.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('["current_stock"]', '["stock_quantity"]')
text = text.replace("['current_stock']", "['stock_quantity']")

with open("scratch/audit/phase2_modules_audit.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Replacement done successfully.")
