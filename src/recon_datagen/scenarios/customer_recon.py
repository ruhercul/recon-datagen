"""Customer/Accounts Receivable Reconciliation scenario."""

from datetime import date, timedelta
from typing import List
import random

from .base import ReconciliationScenario
from ..models import ColumnDef


class CustomerReconciliationScenario(ReconciliationScenario):
    """Customer/AR reconciliation: Accounts Receivable Ledger vs Customer Statement.
    
    Dataset 1 (Source): Accounts Receivable Ledger
    Dataset 2 (Target): Customer Statement
    
    Common scenarios:
    - 1:1: Single AR invoice matches single statement line
    - 1:N: Single AR invoice with multiple payments
    - Potential: Payment amount differences, timing variances
    """
    
    @property
    def name(self) -> str:
        return "customer-recon"
    
    @property
    def display_name(self) -> str:
        return "Customer/AR Reconciliation"
    
    @property
    def description(self) -> str:
        return "Reconcile Accounts Receivable Ledger against Customer Statements"
    
    @property
    def dataset1_name(self) -> str:
        return "AR_Ledger"
    
    @property
    def dataset2_name(self) -> str:
        return "Customer_Statement"
    
    @property
    def dataset1_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("ARInvoiceID", "string"),  # Unique identifier
            ColumnDef("CustomerID", "string"),
            ColumnDef("CustomerName", "string"),
            ColumnDef("InvoiceNumber", "string", is_key=True),  # Actual matching key
            ColumnDef("InvoiceDate", "date"),
            ColumnDef("DueDate", "date"),
            ColumnDef("Currency", "string"),
            ColumnDef("InvoiceAmount", "decimal", is_monetary=True),
        ]
    
    @property
    def dataset2_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("StatementLineID", "string"),  # Unique identifier
            ColumnDef("AccountNumber", "string"),
            ColumnDef("CustomerName", "string"),
            ColumnDef("StatementDate", "date"),
            ColumnDef("DocumentNumber", "string", is_key=True),  # Actual matching key
            ColumnDef("DocumentDate", "date"),
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
        return "DocumentNumber"
    
    @property
    def secondary_monetary_column(self) -> str:
        return "StatementAmount"
    
    def _generate_customer(self) -> tuple[str, str]:
        """Generate customer ID and name."""
        customer_id = f"C{random.randint(10000, 99999)}"
        customer_name = self.faker.company()
        return customer_id, customer_name
    
    def _generate_invoice_number(self) -> str:
        """Generate a realistic invoice number."""
        year = random.randint(2023, 2025)
        seq = random.randint(10000, 99999)
        return f"INV-{year}-{seq}"
    
    def generate_source_record(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date
    ) -> dict:
        """Generate an AR Ledger record."""
        customer_id, customer_name = self._generate_customer()
        due_date = transaction_date + timedelta(days=random.choice([30, 45, 60, 90]))
        currency = random.choice(["USD", "USD", "USD", "EUR", "GBP"])
        
        return {
            "ARInvoiceID": f"AR{self._generate_unique_id()}",
            "CustomerID": customer_id,
            "CustomerName": customer_name,
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
        """Generate Customer Statement records."""
        records = []
        
        if split_count == 1:
            amounts = [abs(amount)]
        else:
            amounts = self._split_amount(abs(amount), split_count)
        
        customer_id, customer_name = self._generate_customer()
        currency = random.choice(["USD", "USD", "USD", "EUR", "GBP"])
        
        for i, split_amount in enumerate(amounts):
            records.append({
                "StatementLineID": f"CSL{self._generate_unique_id()}",
                "AccountNumber": customer_id,
                "CustomerName": customer_name,
                "StatementDate": transaction_date,
                "DocumentNumber": match_group_id,
                "DocumentDate": transaction_date,
                "Currency": currency,
                "StatementAmount": split_amount,
            })
        
        return records
    
    def generate_unmatched_source_record(self) -> dict:
        """Generate an AR Ledger record with no statement match."""
        txn_date = self._generate_date()
        customer_id, customer_name = self._generate_customer()
        amount = self._generate_amount(1000, 100000)
        
        return {
            "ARInvoiceID": f"AR{self._generate_unique_id()}",
            "CustomerID": customer_id,
            "CustomerName": customer_name,
            "InvoiceNumber": self._generate_invoice_number(),
            "InvoiceDate": txn_date,
            "DueDate": txn_date + timedelta(days=random.choice([30, 45, 60])),
            "Currency": random.choice(["USD", "EUR", "GBP"]),
            "InvoiceAmount": amount,
        }
    
    def generate_unmatched_target_record(self) -> dict:
        """Generate a Customer Statement record with no AR match."""
        txn_date = self._generate_date()
        customer_id, customer_name = self._generate_customer()
        amount = self._generate_amount(500, 75000)
        
        return {
            "StatementLineID": f"CSL{self._generate_unique_id()}",
            "AccountNumber": customer_id,
            "CustomerName": customer_name,
            "StatementDate": txn_date + timedelta(days=random.randint(1, 30)),
            "DocumentNumber": self._generate_invoice_number(),
            "DocumentDate": txn_date,
            "Currency": random.choice(["USD", "EUR", "GBP"]),
            "StatementAmount": amount,
        }
