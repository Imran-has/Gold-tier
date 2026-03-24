"""
Accounting Skills for Gold Tier
Skills for Odoo accounting operations.
"""

from typing import Any, Dict, Optional

from config.settings import RiskLevel
from .base import BaseSkill, SkillResult, register_skill


@register_skill
class CreateInvoiceSkill(BaseSkill):
    """Skill to create invoices in Odoo."""

    name = "create_invoice"
    description = "Create a new customer invoice in Odoo"
    risk_level = RiskLevel.MEDIUM
    requires_mcp = "odoo"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "partner_id": {
                    "type": "integer",
                    "description": "Customer ID in Odoo",
                },
                "lines": {
                    "type": "array",
                    "description": "Invoice line items",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "integer"},
                            "name": {"type": "string"},
                            "quantity": {"type": "number"},
                            "price_unit": {"type": "number"},
                        },
                    },
                },
                "invoice_date": {
                    "type": "string",
                    "description": "Invoice date (YYYY-MM-DD)",
                },
                "due_days": {
                    "type": "integer",
                    "description": "Payment due in days",
                    "default": 30,
                },
            },
            "required": ["partner_id", "lines"],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute invoice creation."""
        # This would use the Odoo MCP server
        # For now, return a placeholder result
        self.logger.info(f"Creating invoice for partner {parameters['partner_id']}")

        return SkillResult(
            success=True,
            data={
                "status": "created",
                "partner_id": parameters["partner_id"],
                "lines_count": len(parameters.get("lines", [])),
                "note": "Requires Odoo MCP server connection",
            },
        )


@register_skill
class ListInvoicesSkill(BaseSkill):
    """Skill to list invoices from Odoo."""

    name = "list_invoices"
    description = "List invoices from Odoo with optional filters"
    risk_level = RiskLevel.LOW
    requires_mcp = "odoo"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "enum": ["draft", "posted", "cancel"],
                    "description": "Invoice state filter",
                },
                "partner_id": {
                    "type": "integer",
                    "description": "Filter by customer",
                },
                "date_from": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD)",
                },
                "date_to": {
                    "type": "string",
                    "description": "End date (YYYY-MM-DD)",
                },
                "limit": {
                    "type": "integer",
                    "default": 50,
                },
            },
            "required": [],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute invoice listing."""
        self.logger.info("Listing invoices with filters: %s", parameters)

        return SkillResult(
            success=True,
            data={
                "invoices": [],
                "total": 0,
                "note": "Requires Odoo MCP server connection",
            },
        )


@register_skill
class RecordExpenseSkill(BaseSkill):
    """Skill to record expenses in Odoo."""

    name = "record_expense"
    description = "Record a new expense in Odoo"
    risk_level = RiskLevel.MEDIUM
    requires_mcp = "odoo"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Expense description",
                },
                "amount": {
                    "type": "number",
                    "description": "Expense amount",
                },
                "date": {
                    "type": "string",
                    "description": "Expense date (YYYY-MM-DD)",
                },
                "category": {
                    "type": "string",
                    "description": "Expense category",
                },
                "reference": {
                    "type": "string",
                    "description": "External reference (receipt number, etc.)",
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes",
                },
            },
            "required": ["name", "amount"],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute expense recording."""
        self.logger.info(f"Recording expense: {parameters['name']} - {parameters['amount']}")

        return SkillResult(
            success=True,
            data={
                "status": "recorded",
                "name": parameters["name"],
                "amount": parameters["amount"],
                "note": "Requires Odoo MCP server connection",
            },
        )


@register_skill
class GenerateFinancialReportSkill(BaseSkill):
    """Skill to generate financial reports from Odoo."""

    name = "generate_financial_report"
    description = "Generate financial reports (P&L, Balance Sheet, etc.)"
    risk_level = RiskLevel.LOW
    requires_mcp = "odoo"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "report_type": {
                    "type": "string",
                    "enum": ["profit_loss", "balance_sheet", "aged_receivables", "aged_payables", "cash_flow"],
                    "description": "Type of report to generate",
                },
                "date_from": {
                    "type": "string",
                    "description": "Report start date (YYYY-MM-DD)",
                },
                "date_to": {
                    "type": "string",
                    "description": "Report end date (YYYY-MM-DD)",
                },
                "comparison_period": {
                    "type": "string",
                    "enum": ["previous_month", "previous_year", "none"],
                    "default": "none",
                },
            },
            "required": ["report_type", "date_from", "date_to"],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute financial report generation."""
        self.logger.info(f"Generating {parameters['report_type']} report")

        return SkillResult(
            success=True,
            data={
                "report_type": parameters["report_type"],
                "period": {
                    "from": parameters["date_from"],
                    "to": parameters["date_to"],
                },
                "status": "generated",
                "note": "Requires Odoo MCP server connection",
            },
        )


@register_skill
class ReconcilePaymentsSkill(BaseSkill):
    """Skill to reconcile payments with invoices."""

    name = "reconcile_payments"
    description = "Reconcile payments with outstanding invoices"
    risk_level = RiskLevel.HIGH
    requires_mcp = "odoo"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "partner_id": {
                    "type": "integer",
                    "description": "Partner to reconcile",
                },
                "auto_reconcile": {
                    "type": "boolean",
                    "description": "Automatically match payments to invoices",
                    "default": False,
                },
            },
            "required": [],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute payment reconciliation."""
        self.logger.info("Reconciling payments")

        return SkillResult(
            success=True,
            data={
                "status": "reconciled",
                "note": "Requires Odoo MCP server connection",
            },
        )


@register_skill
class SendInvoiceSkill(BaseSkill):
    """Skill to send invoices to customers."""

    name = "send_invoice"
    description = "Send an invoice to the customer via email"
    risk_level = RiskLevel.HIGH
    requires_mcp = "odoo"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "integer",
                    "description": "Invoice ID to send",
                },
                "email_template": {
                    "type": "string",
                    "description": "Email template to use",
                    "default": "default",
                },
                "include_pdf": {
                    "type": "boolean",
                    "description": "Attach PDF of invoice",
                    "default": True,
                },
            },
            "required": ["invoice_id"],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute invoice sending."""
        self.logger.info(f"Sending invoice {parameters['invoice_id']}")

        return SkillResult(
            success=True,
            data={
                "invoice_id": parameters["invoice_id"],
                "status": "sent",
                "note": "Requires Odoo MCP server connection",
            },
        )
