"""Inventory Reconciliation scenario - ERP Inventory vs Physical Count."""

from datetime import date, timedelta
from typing import List
import random

from .base import ReconciliationScenario
from ..models import ColumnDef


class InventoryReconciliationScenario(ReconciliationScenario):
    """Inventory reconciliation: ERP Inventory Records vs Physical Count Sheet.
    
    Dataset 1 (Source): ERP Inventory Records
    Dataset 2 (Target): Physical Count Sheet
    
    Common scenarios:
    - 1:1: Single ERP item matches single count record
    - 1:N: One ERP item counted in multiple bins/sessions
    - Potential: Quantity variances, unit cost differences
    """
    
    @property
    def name(self) -> str:
        return "inventory-recon"
    
    @property
    def display_name(self) -> str:
        return "Inventory Reconciliation"
    
    @property
    def description(self) -> str:
        return "Reconcile ERP Inventory Records against Physical Count Sheets"
    
    @property
    def dataset1_name(self) -> str:
        return "ERP_Inventory"
    
    @property
    def dataset2_name(self) -> str:
        return "Physical_Count"
    
    @property
    def dataset1_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("ItemNumber", "string", is_key=True),  # Actual matching key
            ColumnDef("SKU", "string"),
            ColumnDef("Location", "string"),
            ColumnDef("Bin", "string"),
            ColumnDef("QuantityOnHand", "integer"),
            ColumnDef("UnitCost", "decimal", is_monetary=True),
            ColumnDef("ExtendedValue", "decimal"),
            ColumnDef("UOM", "string"),
        ]
    
    @property
    def dataset2_schema(self) -> List[ColumnDef]:
        return [
            ColumnDef("CountSessionID", "string"),  # Unique identifier
            ColumnDef("ItemCode", "string", is_key=True),  # Actual matching key
            ColumnDef("Location", "string"),
            ColumnDef("Bin", "string"),
            ColumnDef("CountQuantity", "integer"),
            ColumnDef("UnitCostAtCount", "decimal", is_monetary=True),
            ColumnDef("CountValue", "decimal"),
            ColumnDef("UOM", "string"),
        ]
    
    @property
    def primary_key_column(self) -> str:
        return "ItemNumber"
    
    @property
    def monetary_key_column(self) -> str:
        return "UnitCost"
    
    @property
    def secondary_key_column(self) -> str:
        return "ItemCode"
    
    @property
    def secondary_monetary_column(self) -> str:
        return "UnitCostAtCount"
    
    def _generate_item_number(self) -> str:
        """Generate a realistic item number."""
        prefixes = ["ITM", "SKU", "MAT", "PRD", ""]
        prefix = random.choice(prefixes)
        sep = "-" if prefix else ""
        return f"{prefix}{sep}{random.randint(100000, 999999)}"
    
    def _generate_sku(self, item_number: str) -> str:
        """Generate SKU based on item number."""
        return f"SKU-{item_number[-6:]}"
    
    def _get_location(self) -> str:
        """Get a warehouse location."""
        return random.choice(["WH01", "WH02", "WH03", "DC01", "DC02", "PLANT01"])
    
    def _get_bin(self) -> str:
        """Get a bin location."""
        aisle = random.choice(["A", "B", "C", "D", "E"])
        rack = random.randint(1, 50)
        level = random.randint(1, 5)
        return f"{aisle}{rack:02d}-{level}"
    
    def _get_uom(self) -> str:
        """Get unit of measure."""
        return random.choice(["EA", "CS", "PK", "BX", "KG", "LB", "PC"])
    
    def generate_source_record(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date
    ) -> dict:
        """Generate an ERP Inventory record."""
        location = self._get_location()
        bin_loc = self._get_bin()
        quantity = random.randint(10, 5000)
        unit_cost = abs(amount)
        
        return {
            "ItemNumber": match_group_id,
            "SKU": self._generate_sku(match_group_id),
            "Location": location,
            "Bin": bin_loc,
            "QuantityOnHand": quantity,
            "UnitCost": unit_cost,
            "ExtendedValue": round(quantity * unit_cost, 2),
            "UOM": self._get_uom(),
        }
    
    def generate_target_records(
        self,
        match_group_id: str,
        amount: float,
        transaction_date: date,
        split_count: int = 1,
        exact_match: bool = True
    ) -> List[dict]:
        """Generate Physical Count records."""
        records = []
        
        location = self._get_location()
        bin_loc = self._get_bin()
        total_quantity = random.randint(10, 5000)
        unit_cost = abs(amount)
        uom = self._get_uom()
        
        if split_count == 1:
            quantities = [total_quantity]
        else:
            # Split quantity across multiple count sessions
            base_qty = total_quantity // split_count
            quantities = [base_qty] * split_count
            quantities[-1] += total_quantity - sum(quantities)
        
        for i, qty in enumerate(quantities):
            records.append({
                "CountSessionID": f"CNT{self._generate_unique_id()}",
                "ItemCode": match_group_id,
                "Location": location,
                "Bin": bin_loc if split_count == 1 else f"{bin_loc}-{i+1}",
                "CountQuantity": qty,
                "UnitCostAtCount": unit_cost,
                "CountValue": round(qty * unit_cost, 2),
                "UOM": uom,
            })
        
        return records
    
    def generate_unmatched_source_record(self) -> dict:
        """Generate an ERP Inventory record with no count match."""
        item_number = self._generate_item_number()
        quantity = random.randint(10, 5000)
        unit_cost = round(random.uniform(1, 500), 2)
        
        return {
            "ItemNumber": item_number,
            "SKU": self._generate_sku(item_number),
            "Location": self._get_location(),
            "Bin": self._get_bin(),
            "QuantityOnHand": quantity,
            "UnitCost": unit_cost,
            "ExtendedValue": round(quantity * unit_cost, 2),
            "UOM": self._get_uom(),
        }
    
    def generate_unmatched_target_record(self) -> dict:
        """Generate a Physical Count record with no ERP match."""
        item_code = self._generate_item_number()
        quantity = random.randint(1, 500)
        unit_cost = round(random.uniform(1, 500), 2)
        
        return {
            "CountSessionID": f"CNT{self._generate_unique_id()}",
            "ItemCode": item_code,
            "Location": self._get_location(),
            "Bin": self._get_bin(),
            "CountQuantity": quantity,
            "UnitCostAtCount": unit_cost,
            "CountValue": round(quantity * unit_cost, 2),
            "UOM": self._get_uom(),
        }
