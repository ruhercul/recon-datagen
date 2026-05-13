"""Check mapping keys in schema."""
import sys
sys.path.insert(0, 'src')

from recon_datagen.scenarios import get_scenario

# Get the bank-recon scenario
scenario = get_scenario('bank-recon')

print("=" * 60)
print("MAPPING KEYS REPORTED IN GENERATION_STATS:")
print("=" * 60)

# Check what keys are in the schema
dataset1_keys = [col.name for col in scenario.dataset1_schema if col.is_key]
dataset2_keys = [col.name for col in scenario.dataset2_schema if col.is_key]

print(f"\n{scenario.dataset1_name} Key Columns:")
print(f"  {', '.join(dataset1_keys)}")

print(f"\n{scenario.dataset2_name} Key Columns:")
print(f"  {', '.join(dataset2_keys)}")

print("\nThese are the columns users should match on!")
print("✓ FIXED - no more TransactionID or BankTransactionID!" if 'TransactionID' not in dataset1_keys and 'BankTransactionID' not in dataset2_keys else "✗ Still broken")

print("\n" + "=" * 60)
print("BEFORE vs AFTER FIX:")
print("=" * 60)
print("\nBEFORE (WRONG):")
print("  Cash_Ledger Keys: TransactionID, DocumentNumber")
print("  Bank_Statement Keys: BankTransactionID, BankReference")
print("  ❌ TransactionID and BankTransactionID will NEVER match!")

print("\nAFTER (CORRECT):")
print(f"  Cash_Ledger Keys: {', '.join(dataset1_keys)}")
print(f"  Bank_Statement Keys: {', '.join(dataset2_keys)}")
print("  ✓ These are the actual matching keys that link the datasets!")

