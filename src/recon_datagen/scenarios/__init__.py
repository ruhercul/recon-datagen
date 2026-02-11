"""Reconciliation scenarios package."""

from .base import ReconciliationScenario
from .bank_recon import BankReconciliationScenario
from .vendor_recon import VendorReconciliationScenario
from .customer_recon import CustomerReconciliationScenario
from .intercompany import IntercompanyScenario
from .gl_subledger import GLSubledgerScenario
from .inventory_recon import InventoryReconciliationScenario
from .fixed_asset_recon import FixedAssetReconciliationScenario
from .payroll_recon import PayrollReconciliationScenario
from .tax_recon import TaxReconciliationScenario
from .expense_recon import ExpenseReconciliationScenario

# Registry of all available scenarios
SCENARIO_REGISTRY: dict[str, type[ReconciliationScenario]] = {
    "bank-recon": BankReconciliationScenario,
    "vendor-recon": VendorReconciliationScenario,
    "customer-recon": CustomerReconciliationScenario,
    "intercompany": IntercompanyScenario,
    "gl-subledger": GLSubledgerScenario,
    "inventory-recon": InventoryReconciliationScenario,
    "fixed-asset-recon": FixedAssetReconciliationScenario,
    "payroll-recon": PayrollReconciliationScenario,
    "tax-recon": TaxReconciliationScenario,
    "expense-recon": ExpenseReconciliationScenario,
}


def get_scenario(name: str) -> ReconciliationScenario:
    """Get a scenario instance by name."""
    if name not in SCENARIO_REGISTRY:
        raise ValueError(f"Unknown scenario: {name}. Available: {list(SCENARIO_REGISTRY.keys())}")
    return SCENARIO_REGISTRY[name]()


def list_scenarios() -> list[dict]:
    """List all available scenarios with descriptions."""
    scenarios = []
    for name, cls in SCENARIO_REGISTRY.items():
        instance = cls()
        scenarios.append({
            "name": name,
            "display_name": instance.display_name,
            "description": instance.description,
            "dataset1_name": instance.dataset1_name,
            "dataset2_name": instance.dataset2_name,
        })
    return scenarios


__all__ = [
    "ReconciliationScenario",
    "BankReconciliationScenario",
    "VendorReconciliationScenario",
    "CustomerReconciliationScenario",
    "IntercompanyScenario",
    "GLSubledgerScenario",
    "InventoryReconciliationScenario",
    "FixedAssetReconciliationScenario",
    "PayrollReconciliationScenario",
    "TaxReconciliationScenario",
    "ExpenseReconciliationScenario",
    "SCENARIO_REGISTRY",
    "get_scenario",
    "list_scenarios",
]
