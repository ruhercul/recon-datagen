"""Payroll Reconciliation scenario - Payroll System vs GL."""

from datetime import date, timedelta
from typing import List
import random

from .base import ReconciliationScenario
from ..models import ColumnDef


class PayrollReconciliationScenario(ReconciliationScenario):
    """Payroll reconciliation: Payroll System vs General Ledger (Payroll).
    
    Dataset 1 (Source): Payroll System
    Dataset 2 (Target): General Ledger (Payroll)
    
    Common scenarios:
    - 1:1: Single payroll run matches single GL journal
    - 1:N: Single payroll run split across multiple GL entries
    - Potential: Timing differences, rounding in tax calculations
    """
    
    @property
    def name(self) -> str:
        return "payroll-recon"
    
    @property
    def display_name(self) -> str:
        return "Payroll Reconciliation"
    
    @property
    def description(self) -> str:
        return "Reconcile Payroll System against General Ledger payroll entries"
    
    @property
    def dataset1_name(self) -> str:
        return "Payroll_System"
    
    @property
    def dataset2_name(self) -> str:
        return "GL_Payroll"
    
    @property
    def dataset1_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("EmployeeID", "string", is_key=True),
            ColumnDef("EmployeeName", "string"),
            ColumnDef("PayPeriod", "string", is_key=True),
            ColumnDef("PayrollRunID", "string", is_key=True),
            ColumnDef("GrossPay", "decimal"),
            ColumnDef("NetPay", "decimal", is_monetary=True),
            ColumnDef("TaxesWithheld", "decimal"),
            ColumnDef("DepartmentCode", "string"),
        ]
    
    @property
    def dataset2_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("PayPeriod", "string", is_key=True),
            ColumnDef("JournalID", "string", is_key=True),
            ColumnDef("SalaryExpense", "decimal"),
            ColumnDef("TaxExpense", "decimal"),
            ColumnDef("BenefitsExpense", "decimal"),
            ColumnDef("CashPaid", "decimal", is_monetary=True),
            ColumnDef("Currency", "string"),
            ColumnDef("DepartmentCode", "string"),
        ]
    
    @property
    def primary_key_column(self) -> str:
        return "PayrollRunID"
    
    @property
    def monetary_key_column(self) -> str:
        return "NetPay"
    
    @property
    def secondary_key_column(self) -> str:
        return "JournalID"
    
    @property
    def secondary_monetary_column(self) -> str:
        return "CashPaid"
    
    def _get_pay_period(self, txn_date: date) -> str:
        """Get pay period identifier."""
        # Bi-weekly pay periods
        week_num = txn_date.isocalendar()[1]
        period_num = (week_num - 1) // 2 + 1
        return f"{txn_date.year}-PP{period_num:02d}"
    
    def _get_department(self) -> str:
        """Get a department code."""
        return random.choice(["SALES", "ENG", "FIN", "HR", "OPS", "MKT", "IT", "ADMIN"])
    
    def generate_source_record(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date
    ) -> dict:
        """Generate a Payroll System record."""
        gross_pay = round(abs(amount) * random.uniform(1.3, 1.5), 2)
        taxes = round(gross_pay * random.uniform(0.2, 0.35), 2)
        net_pay = abs(amount)
        
        return {
            "EmployeeID": f"EMP{random.randint(10000, 99999)}",
            "EmployeeName": self.faker.name(),
            "PayPeriod": self._get_pay_period(transaction_date),
            "PayrollRunID": match_group_id,
            "GrossPay": gross_pay,
            "NetPay": net_pay,
            "TaxesWithheld": taxes,
            "DepartmentCode": self._get_department(),
        }
    
    def generate_target_records(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date,
        split_count: int = 1,
        exact_match: bool = True
    ) -> List[dict]:
        """Generate GL Payroll records."""
        records = []
        
        if split_count == 1:
            amounts = [abs(amount)]
        else:
            amounts = self._split_amount(abs(amount), split_count)
        
        pay_period = self._get_pay_period(transaction_date)
        department = self._get_department()
        
        for i, split_amount in enumerate(amounts):
            gross = round(split_amount * random.uniform(1.3, 1.5), 2)
            tax_expense = round(gross * random.uniform(0.08, 0.12), 2)
            benefits = round(gross * random.uniform(0.1, 0.2), 2)
            
            records.append({
                "PayPeriod": pay_period,
                "JournalID": match_group_id if split_count == 1 else f"{match_group_id}-{i+1:02d}",
                "SalaryExpense": gross,
                "TaxExpense": tax_expense,
                "BenefitsExpense": benefits,
                "CashPaid": split_amount,
                "Currency": "USD",
                "DepartmentCode": department,
            })
        
        return records
    
    def generate_unmatched_source_record(self) -> dict:
        """Generate a Payroll System record with no GL match."""
        txn_date = self._generate_date()
        gross_pay = round(random.uniform(3000, 15000), 2)
        taxes = round(gross_pay * random.uniform(0.2, 0.35), 2)
        net_pay = round(gross_pay - taxes - random.uniform(200, 800), 2)
        
        return {
            "EmployeeID": f"EMP{random.randint(10000, 99999)}",
            "EmployeeName": self.faker.name(),
            "PayPeriod": self._get_pay_period(txn_date),
            "PayrollRunID": f"PR-{self._generate_reference_id()}",
            "GrossPay": gross_pay,
            "NetPay": net_pay,
            "TaxesWithheld": taxes,
            "DepartmentCode": self._get_department(),
        }
    
    def generate_unmatched_target_record(self) -> dict:
        """Generate a GL Payroll record with no payroll system match."""
        txn_date = self._generate_date()
        gross = round(random.uniform(3000, 15000), 2)
        
        return {
            "PayPeriod": self._get_pay_period(txn_date),
            "JournalID": f"JE-{self._generate_reference_id()}",
            "SalaryExpense": gross,
            "TaxExpense": round(gross * random.uniform(0.08, 0.12), 2),
            "BenefitsExpense": round(gross * random.uniform(0.1, 0.2), 2),
            "CashPaid": round(gross * random.uniform(0.6, 0.75), 2),
            "Currency": "USD",
            "DepartmentCode": self._get_department(),
        }
