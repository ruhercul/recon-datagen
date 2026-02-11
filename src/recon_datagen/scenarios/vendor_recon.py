"""Vendor/Supplier Reconciliation scenario - AP Ledger vs Vendor Statement."""

from datetime import date, timedelta
from typing import List
import random

from .base import ReconciliationScenario
from ..models import ColumnDef


class VendorReconciliationScenario(ReconciliationScenario):
    """Vendor/Supplier reconciliation: Accounts Payable Ledger vs Vendor Statement.
    
    Dataset 1 (Source): Accounts Payable Ledger
    Dataset 2 (Target): Vendor Statement
    
    Common scenarios:
    - 1:1: Single AP invoice matches single statement line
    - 1:N: Single AP invoice with multiple statement entries (partial payments)
    - Potential: Invoice number variations, timing differences
    """
    
    @property
    def name(self) -> str:
        return "vendor-recon"
    
    @property
    def display_name(self) -> str:
        return "Vendor/Supplier Reconciliation"
    
    @property
    def description(self) -> str:
        return "Reconcile Accounts Payable Ledger against Vendor Statements"
    
    @property
    def dataset1_name(self) -> str:
        return "AP_Ledger"
    
    @property
    def dataset2_name(self) -> str:
        return "Vendor_Statement"
    
    @property
    def dataset1_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("APInvoiceID", "string", is_key=True),
            ColumnDef("VendorID", "string", is_key=True),
            ColumnDef("VendorName", "string"),
            ColumnDef("InvoiceNumber", "string", is_key=True),
            ColumnDef("InvoiceDate", "date"),
            ColumnDef("DueDate", "date"),
            ColumnDef("Currency", "string"),
            ColumnDef("InvoiceAmount", "decimal", is_monetary=True),
        ]
    
    @property
    def dataset2_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("StatementLineID", "string", is_key=True),
            ColumnDef("SupplierAccountNumber", "string", is_key=True),
            ColumnDef("SupplierName", "string"),
            ColumnDef("StatementDate", "date"),
            ColumnDef("InvoiceNumber", "string", is_key=True),
            ColumnDef("InvoiceDate", "date"),
            ColumnDef("Currency", "string"),
            ColumnDef("StatementAmount", "decimal", is_monetary=True),
        ]
    
    @property
    def primary_key_column(self) -> str:
        return "InvoiceNumber"
    
    @property
    def monetary_key_column(self) -> str:
        return "InvoiceAmount"
    
    @property
    def secondary_key_column(self) -> str:
        return "InvoiceNumber"
    
    @property
    def secondary_monetary_column(self) -> str:
        return "StatementAmount"
    
    def _generate_vendor(self) -> tuple[str, str]:
        """Generate vendor ID and name."""
        vendor_id = f"V{random.randint(10000, 99999)}"
        vendor_name = self.faker.company()
        return vendor_id, vendor_name
    
    def _generate_invoice_number(self) -> str:
        """Generate a realistic invoice number."""
        prefixes = ["INV", "SI", "BILL", ""]
        prefix = random.choice(prefixes)
        sep = "-" if prefix else ""
        return f"{prefix}{sep}{random.randint(100000, 999999)}"
    
    def generate_source_record(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date
    ) -> dict:
        """Generate an AP Ledger record."""
        vendor_id, vendor_name = self._generate_vendor()
        due_date = transaction_date + timedelta(days=random.choice([30, 45, 60, 90]))
        currency = random.choice(["USD", "USD", "USD", "EUR", "GBP", "CAD"])
        
        return {
            "APInvoiceID": f"AP{self._generate_unique_id()}",
            "VendorID": vendor_id,
            "VendorName": vendor_name,
            "InvoiceNumber": match_group_id,
            "InvoiceDate": transaction_date,
            "DueDate": due_date,
            "Currency": currency,
            "InvoiceAmount": abs(amount),
        }
    
    def generate_target_records(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date,
        split_count: int = 1,
        exact_match: bool = True
    ) -> List[dict]:
        """Generate Vendor Statement records."""
        records = []
        
        if split_count == 1:
            amounts = [abs(amount)]
        else:
            amounts = self._split_amount(abs(amount), split_count)
        
        vendor_id, vendor_name = self._generate_vendor()
        currency = random.choice(["USD", "USD", "USD", "EUR", "GBP", "CAD"])
        
        for i, split_amount in enumerate(amounts):
            records.append({
                "StatementLineID": f"SL{self._generate_unique_id()}",
                "SupplierAccountNumber": vendor_id,
                "SupplierName": vendor_name,
                "StatementDate": transaction_date,
                "InvoiceNumber": match_group_id,
                "InvoiceDate": transaction_date,
                "Currency": currency,
                "StatementAmount": split_amount,
            })
        
        return records
    
    def generate_unmatched_source_record(self) -> dict:
        """Generate an AP Ledger record with no statement match."""
        txn_date = self._generate_date()
        vendor_id, vendor_name = self._generate_vendor()
        amount = self._generate_amount(500, 75000)
        
        return {
            "APInvoiceID": f"AP{self._generate_unique_id()}",
            "VendorID": vendor_id,
            "VendorName": vendor_name,
            "InvoiceNumber": self._generate_invoice_number(),
            "InvoiceDate": txn_date,
            "DueDate": txn_date + timedelta(days=random.choice([30, 45, 60])),
            "Currency": random.choice(["USD", "EUR", "GBP", "CAD"]),
            "InvoiceAmount": amount,
        }
    
    def generate_unmatched_target_record(self) -> dict:
        """Generate a Vendor Statement record with no AP match."""
        txn_date = self._generate_date()
        vendor_id, vendor_name = self._generate_vendor()
        amount = self._generate_amount(500, 50000)
        
        return {
            "StatementLineID": f"SL{self._generate_unique_id()}",
            "SupplierAccountNumber": vendor_id,
            "SupplierName": vendor_name,
            "StatementDate": txn_date + timedelta(days=random.randint(1, 30)),
            "InvoiceNumber": self._generate_invoice_number(),
            "InvoiceDate": txn_date,
            "Currency": random.choice(["USD", "EUR", "GBP", "CAD"]),
            "StatementAmount": amount,
        }
