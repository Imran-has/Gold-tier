"""
Odoo MCP Server
Provides Model Context Protocol interface for Odoo Community Edition (19+).
Uses JSON-RPC API for all accounting operations.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import aiohttp

from config.settings import config, RiskLevel, get_operation_risk, requires_approval


@dataclass
class OdooConnection:
    """Manages connection to Odoo server."""
    url: str
    database: str
    username: str
    password: str
    uid: Optional[int] = None
    session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Establish connection and authenticate with Odoo."""
        if self.session is None:
            self.session = aiohttp.ClientSession()

        try:
            # Authenticate via JSON-RPC
            auth_response = await self._call(
                "/web/session/authenticate",
                {
                    "db": self.database,
                    "login": self.username,
                    "password": self.password,
                }
            )

            if auth_response and auth_response.get("uid"):
                self.uid = auth_response["uid"]
                return True
            return False
        except Exception as e:
            logging.error(f"Odoo connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Close the connection."""
        if self.session:
            await self.session.close()
            self.session = None
            self.uid = None

    async def _call(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a JSON-RPC call to Odoo."""
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.url}{endpoint}"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": int(datetime.now().timestamp() * 1000),
        }

        try:
            async with self.session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=config.odoo.timeout),
            ) as response:
                result = await response.json()
                if "error" in result:
                    logging.error(f"Odoo error: {result['error']}")
                    return None
                return result.get("result")
        except Exception as e:
            logging.error(f"Odoo RPC call failed: {e}")
            return None

    async def call_kw(
        self,
        model: str,
        method: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
    ) -> Optional[Any]:
        """Call a method on an Odoo model via JSON-RPC."""
        if not self.uid:
            raise ValueError("Not authenticated with Odoo")

        call_args = [self.database, self.uid, self.password, model, method, args or []]
        if kwargs:
            call_args.append(kwargs)

        return await self._call(
            "/jsonrpc",
            {
                "service": "object",
                "method": "execute_kw",
                "args": call_args,
            }
        )


class OdooMCPServer:
    """
    MCP Server for Odoo accounting operations.
    Provides tools for invoices, expenses, income, reports, and journals.
    """

    def __init__(self):
        self.name = "odoo_mcp"
        self.logger = logging.getLogger(f"gold.mcp.{self.name}")
        self.connection: Optional[OdooConnection] = None
        self.is_running = False
        self._tools = self._define_tools()

    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """Define available MCP tools for Odoo operations."""
        return {
            # Invoice operations
            "create_invoice": {
                "name": "create_invoice",
                "description": "Create a new customer invoice in Odoo",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "partner_id": {"type": "integer", "description": "Customer ID"},
                        "invoice_date": {"type": "string", "description": "Invoice date (YYYY-MM-DD)"},
                        "lines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_id": {"type": "integer"},
                                    "quantity": {"type": "number"},
                                    "price_unit": {"type": "number"},
                                    "name": {"type": "string"},
                                },
                            },
                        },
                    },
                    "required": ["partner_id", "lines"],
                },
                "risk_level": RiskLevel.MEDIUM,
            },
            "send_invoice": {
                "name": "send_invoice",
                "description": "Send an invoice to the customer via email",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "invoice_id": {"type": "integer", "description": "Invoice ID to send"},
                    },
                    "required": ["invoice_id"],
                },
                "risk_level": RiskLevel.HIGH,
            },
            "list_invoices": {
                "name": "list_invoices",
                "description": "List invoices with optional filters",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string", "enum": ["draft", "posted", "cancel"]},
                        "partner_id": {"type": "integer"},
                        "date_from": {"type": "string"},
                        "date_to": {"type": "string"},
                        "limit": {"type": "integer", "default": 100},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "get_invoice": {
                "name": "get_invoice",
                "description": "Get details of a specific invoice",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "invoice_id": {"type": "integer", "description": "Invoice ID"},
                    },
                    "required": ["invoice_id"],
                },
                "risk_level": RiskLevel.LOW,
            },
            # Expense operations
            "create_expense": {
                "name": "create_expense",
                "description": "Create a new expense record",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Expense description"},
                        "amount": {"type": "number", "description": "Expense amount"},
                        "date": {"type": "string", "description": "Expense date (YYYY-MM-DD)"},
                        "category": {"type": "string", "description": "Expense category"},
                        "reference": {"type": "string", "description": "External reference"},
                    },
                    "required": ["name", "amount"],
                },
                "risk_level": RiskLevel.MEDIUM,
            },
            "list_expenses": {
                "name": "list_expenses",
                "description": "List expenses with optional filters",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "date_from": {"type": "string"},
                        "date_to": {"type": "string"},
                        "category": {"type": "string"},
                        "limit": {"type": "integer", "default": 100},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            # Payment operations
            "create_payment": {
                "name": "create_payment",
                "description": "Create a payment record",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "partner_id": {"type": "integer", "description": "Partner ID"},
                        "amount": {"type": "number", "description": "Payment amount"},
                        "payment_type": {"type": "string", "enum": ["inbound", "outbound"]},
                        "payment_date": {"type": "string", "description": "Payment date"},
                        "reference": {"type": "string"},
                    },
                    "required": ["partner_id", "amount", "payment_type"],
                },
                "risk_level": RiskLevel.HIGH,
            },
            # Report operations
            "get_profit_loss": {
                "name": "get_profit_loss",
                "description": "Generate profit and loss report",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                        "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    },
                    "required": ["date_from", "date_to"],
                },
                "risk_level": RiskLevel.LOW,
            },
            "get_balance_sheet": {
                "name": "get_balance_sheet",
                "description": "Generate balance sheet report",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Report date (YYYY-MM-DD)"},
                    },
                    "required": ["date"],
                },
                "risk_level": RiskLevel.LOW,
            },
            "get_aged_receivables": {
                "name": "get_aged_receivables",
                "description": "Get aged receivables report",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "As of date"},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            # Partner operations
            "list_partners": {
                "name": "list_partners",
                "description": "List customers/vendors",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "is_customer": {"type": "boolean"},
                        "is_vendor": {"type": "boolean"},
                        "search": {"type": "string"},
                        "limit": {"type": "integer", "default": 100},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "create_partner": {
                "name": "create_partner",
                "description": "Create a new customer or vendor",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Partner name"},
                        "email": {"type": "string"},
                        "phone": {"type": "string"},
                        "is_customer": {"type": "boolean", "default": True},
                        "is_vendor": {"type": "boolean", "default": False},
                    },
                    "required": ["name"],
                },
                "risk_level": RiskLevel.MEDIUM,
            },
            # Journal operations
            "list_journal_entries": {
                "name": "list_journal_entries",
                "description": "List journal entries",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "date_from": {"type": "string"},
                        "date_to": {"type": "string"},
                        "journal_id": {"type": "integer"},
                        "limit": {"type": "integer", "default": 100},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
        }

    async def start(self) -> bool:
        """Start the Odoo MCP server and establish connection."""
        if not config.odoo.is_configured():
            self.logger.warning("Odoo not configured - server starting in disconnected mode")
            self.is_running = True
            return True

        self.connection = OdooConnection(
            url=config.odoo.url,
            database=config.odoo.database,
            username=config.odoo.username,
            password=config.odoo.password,
        )

        connected = await self.connection.connect()
        if connected:
            self.logger.info("Connected to Odoo server")
            self.is_running = True
            return True
        else:
            self.logger.error("Failed to connect to Odoo server")
            self.is_running = True  # Still running, just not connected
            return False

    async def stop(self) -> None:
        """Stop the Odoo MCP server."""
        if self.connection:
            await self.connection.disconnect()
        self.is_running = False
        self.logger.info("Odoo MCP server stopped")

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools for MCP discovery."""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["input_schema"],
            }
            for tool in self._tools.values()
        ]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        approval_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Execute a tool by name with given arguments."""
        if tool_name not in self._tools:
            return {"error": f"Unknown tool: {tool_name}"}

        tool = self._tools[tool_name]

        # Check if approval is required
        if requires_approval(f"odoo.{tool_name}"):
            if approval_callback:
                approved = await approval_callback(tool_name, arguments)
                if not approved:
                    return {"error": "Action not approved", "requires_approval": True}
            else:
                return {
                    "error": "Action requires approval",
                    "requires_approval": True,
                    "risk_level": tool["risk_level"].value,
                }

        # Execute the tool
        method_name = f"_execute_{tool_name}"
        if hasattr(self, method_name):
            try:
                result = await getattr(self, method_name)(arguments)
                return {"success": True, "result": result}
            except Exception as e:
                self.logger.error(f"Tool execution error: {e}")
                return {"success": False, "error": str(e)}
        else:
            return {"error": f"Tool not implemented: {tool_name}"}

    # Tool implementations

    async def _execute_create_invoice(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a customer invoice."""
        if not self.connection or not self.connection.uid:
            return {"error": "Not connected to Odoo"}

        invoice_lines = []
        for line in args.get("lines", []):
            invoice_lines.append((0, 0, {
                "product_id": line.get("product_id"),
                "quantity": line.get("quantity", 1),
                "price_unit": line.get("price_unit", 0),
                "name": line.get("name", ""),
            }))

        invoice_data = {
            "move_type": "out_invoice",
            "partner_id": args["partner_id"],
            "invoice_date": args.get("invoice_date", datetime.now().strftime("%Y-%m-%d")),
            "invoice_line_ids": invoice_lines,
        }

        result = await self.connection.call_kw(
            "account.move",
            "create",
            [invoice_data],
        )

        return {"invoice_id": result}

    async def _execute_send_invoice(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Send an invoice via email."""
        if not self.connection or not self.connection.uid:
            return {"error": "Not connected to Odoo"}

        invoice_id = args["invoice_id"]

        # First, post the invoice if it's in draft
        await self.connection.call_kw(
            "account.move",
            "action_post",
            [[invoice_id]],
        )

        # Send the invoice email
        result = await self.connection.call_kw(
            "account.move",
            "action_invoice_sent",
            [[invoice_id]],
        )

        return {"sent": True, "invoice_id": invoice_id}

    async def _execute_list_invoices(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List invoices with filters."""
        if not self.connection or not self.connection.uid:
            return {"error": "Not connected to Odoo"}

        domain = [("move_type", "in", ["out_invoice", "out_refund"])]

        if args.get("state"):
            domain.append(("state", "=", args["state"]))
        if args.get("partner_id"):
            domain.append(("partner_id", "=", args["partner_id"]))
        if args.get("date_from"):
            domain.append(("invoice_date", ">=", args["date_from"]))
        if args.get("date_to"):
            domain.append(("invoice_date", "<=", args["date_to"]))

        result = await self.connection.call_kw(
            "account.move",
            "search_read",
            [domain],
            {
                "fields": ["name", "partner_id", "invoice_date", "amount_total", "state"],
                "limit": args.get("limit", 100),
            },
        )

        return result or []

    async def _execute_get_invoice(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get invoice details."""
        if not self.connection or not self.connection.uid:
            return {"error": "Not connected to Odoo"}

        result = await self.connection.call_kw(
            "account.move",
            "read",
            [[args["invoice_id"]]],
            {
                "fields": [
                    "name", "partner_id", "invoice_date", "invoice_date_due",
                    "amount_untaxed", "amount_tax", "amount_total", "state",
                    "invoice_line_ids", "payment_state",
                ],
            },
        )

        return result[0] if result else {"error": "Invoice not found"}

    async def _execute_create_expense(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create an expense record."""
        if not self.connection or not self.connection.uid:
            return {"error": "Not connected to Odoo"}

        expense_data = {
            "name": args["name"],
            "total_amount": args["amount"],
            "date": args.get("date", datetime.now().strftime("%Y-%m-%d")),
            "reference": args.get("reference", ""),
        }

        result = await self.connection.call_kw(
            "hr.expense",
            "create",
            [expense_data],
        )

        return {"expense_id": result}

    async def _execute_list_expenses(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List expenses."""
        if not self.connection or not self.connection.uid:
            return {"error": "Not connected to Odoo"}

        domain = []
        if args.get("date_from"):
            domain.append(("date", ">=", args["date_from"]))
        if args.get("date_to"):
            domain.append(("date", "<=", args["date_to"]))

        result = await self.connection.call_kw(
            "hr.expense",
            "search_read",
            [domain],
            {
                "fields": ["name", "date", "total_amount", "state"],
                "limit": args.get("limit", 100),
            },
        )

        return result or []

    async def _execute_create_payment(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a payment."""
        if not self.connection or not self.connection.uid:
            return {"error": "Not connected to Odoo"}

        payment_data = {
            "partner_id": args["partner_id"],
            "amount": args["amount"],
            "payment_type": args["payment_type"],
            "date": args.get("payment_date", datetime.now().strftime("%Y-%m-%d")),
            "ref": args.get("reference", ""),
        }

        result = await self.connection.call_kw(
            "account.payment",
            "create",
            [payment_data],
        )

        return {"payment_id": result}

    async def _execute_list_partners(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List partners (customers/vendors)."""
        if not self.connection or not self.connection.uid:
            return {"error": "Not connected to Odoo"}

        domain = []
        if args.get("is_customer"):
            domain.append(("customer_rank", ">", 0))
        if args.get("is_vendor"):
            domain.append(("supplier_rank", ">", 0))
        if args.get("search"):
            domain.append(("name", "ilike", args["search"]))

        result = await self.connection.call_kw(
            "res.partner",
            "search_read",
            [domain],
            {
                "fields": ["name", "email", "phone", "customer_rank", "supplier_rank"],
                "limit": args.get("limit", 100),
            },
        )

        return result or []

    async def _execute_create_partner(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new partner."""
        if not self.connection or not self.connection.uid:
            return {"error": "Not connected to Odoo"}

        partner_data = {
            "name": args["name"],
            "email": args.get("email", ""),
            "phone": args.get("phone", ""),
            "customer_rank": 1 if args.get("is_customer", True) else 0,
            "supplier_rank": 1 if args.get("is_vendor", False) else 0,
        }

        result = await self.connection.call_kw(
            "res.partner",
            "create",
            [partner_data],
        )

        return {"partner_id": result}

    async def _execute_get_profit_loss(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate profit and loss report."""
        if not self.connection or not self.connection.uid:
            return {"error": "Not connected to Odoo"}

        date_from = args["date_from"]
        date_to = args["date_to"]

        # Get income account move lines
        income_lines = await self.connection.call_kw(
            "account.move.line",
            "search_read",
            [[
                ("date", ">=", date_from),
                ("date", "<=", date_to),
                ("account_id.account_type", "in", ["income", "income_other"]),
                ("parent_state", "=", "posted"),
            ]],
            {"fields": ["balance"]},
        )

        # Get expense account move lines
        expense_lines = await self.connection.call_kw(
            "account.move.line",
            "search_read",
            [[
                ("date", ">=", date_from),
                ("date", "<=", date_to),
                ("account_id.account_type", "in", ["expense", "expense_direct_cost"]),
                ("parent_state", "=", "posted"),
            ]],
            {"fields": ["balance"]},
        )

        total_income = abs(sum(l["balance"] for l in (income_lines or [])))
        total_expenses = abs(sum(l["balance"] for l in (expense_lines or [])))

        return {
            "period": {"from": date_from, "to": date_to},
            "income": total_income,
            "expenses": total_expenses,
            "net_profit": total_income - total_expenses,
        }

    async def _execute_get_balance_sheet(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate balance sheet."""
        if not self.connection or not self.connection.uid:
            return {"error": "Not connected to Odoo"}

        as_of_date = args["date"]

        async def get_total(account_types):
            lines = await self.connection.call_kw(
                "account.move.line",
                "search_read",
                [[
                    ("date", "<=", as_of_date),
                    ("account_id.account_type", "in", account_types),
                    ("parent_state", "=", "posted"),
                ]],
                {"fields": ["balance"]},
            )
            return sum(l["balance"] for l in (lines or []))

        assets = await get_total(["asset_receivable", "asset_cash", "asset_current", "asset_fixed", "asset_non_current", "asset_prepayments"])
        liabilities = await get_total(["liability_payable", "liability_current", "liability_non_current"])
        equity = await get_total(["equity", "equity_unaffected"])

        return {
            "as_of_date": as_of_date,
            "assets": abs(assets),
            "liabilities": abs(liabilities),
            "equity": abs(equity),
            "total_liabilities_equity": abs(liabilities) + abs(equity),
        }

    async def _execute_get_aged_receivables(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get aged receivables report."""
        if not self.connection or not self.connection.uid:
            return {"error": "Not connected to Odoo"}

        # Query open receivables
        receivables = await self.connection.call_kw(
            "account.move",
            "search_read",
            [[
                ("move_type", "=", "out_invoice"),
                ("payment_state", "!=", "paid"),
                ("state", "=", "posted"),
            ]],
            {
                "fields": ["name", "partner_id", "invoice_date", "invoice_date_due", "amount_residual"],
            },
        )

        return {
            "as_of_date": args.get("date", datetime.now().strftime("%Y-%m-%d")),
            "open_invoices": receivables or [],
        }

    async def _execute_list_journal_entries(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List journal entries."""
        if not self.connection or not self.connection.uid:
            return {"error": "Not connected to Odoo"}

        domain = []
        if args.get("date_from"):
            domain.append(("date", ">=", args["date_from"]))
        if args.get("date_to"):
            domain.append(("date", "<=", args["date_to"]))
        if args.get("journal_id"):
            domain.append(("journal_id", "=", args["journal_id"]))

        result = await self.connection.call_kw(
            "account.move",
            "search_read",
            [domain],
            {
                "fields": ["name", "date", "journal_id", "amount_total", "state"],
                "limit": args.get("limit", 100),
            },
        )

        return result or []

    async def health_check(self) -> Dict[str, Any]:
        """Health check for Odoo MCP server."""
        connected = False
        if self.connection and self.connection.uid:
            # Try a simple call to verify connection
            try:
                await self.connection.call_kw("res.users", "search_count", [[]])
                connected = True
            except Exception:
                connected = False

        return {
            "name": self.name,
            "is_running": self.is_running,
            "connected": connected,
            "odoo_url": config.odoo.url if config.odoo.is_configured() else None,
            "tools_available": len(self._tools),
        }
