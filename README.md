# Gold Tier - Autonomous AI Employee

## Overview

The Gold Tier represents the highest level of autonomy in the AI Employee system, integrating:
- Full Silver Tier capabilities
- Odoo Community accounting system (self-hosted, local)
- Social media management (Facebook, Instagram, Twitter/X)
- Weekly business and accounting audits
- CEO-level briefings
- Ralph Wiggum Loop for autonomous task completion

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GOLD TIER ORCHESTRATOR                        │
│                     (Ralph Wiggum Loop Engine)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │   ODOO MCP   │  │ SOCIAL MCP   │  │  AUDIT MCP   │  │SILVER MCP│ │
│  │   SERVER     │  │   SERVER     │  │   SERVER     │  │  SERVER  │ │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤  ├──────────┤ │
│  │• Invoices    │  │• Facebook    │  │• Weekly Audit│  │• Email   │ │
│  │• Expenses    │  │• Instagram   │  │• CEO Brief   │  │• WhatsApp│ │
│  │• Income      │  │• Twitter/X   │  │• Compliance  │  │• LinkedIn│ │
│  │• Reports     │  │• Analytics   │  │• Logs        │  │• Calendar│ │
│  │• Journals    │  │• Scheduling  │  │• Alerts      │  │          │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘ │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                         SKILL REGISTRY                               │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Accounting Skills │ Social Skills │ Audit Skills │ Core Skills │ │
│  └────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                      AUDIT LOG & RECOVERY                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
Gold/
├── agents/                 # Agent implementations
│   ├── base.py            # Base agent with event handling
│   ├── orchestrator.py    # Main Gold tier orchestrator
│   └── ralph_loop.py      # Ralph Wiggum Loop implementation
├── mcp/                   # MCP Server implementations
│   ├── odoo_server.py     # Odoo JSON-RPC MCP server
│   ├── social_server.py   # Social media MCP server
│   └── audit_server.py    # Audit & monitoring MCP server
├── skills/                # Modular skill implementations
│   ├── base.py            # Base skill framework
│   ├── accounting/        # Accounting skills
│   ├── social/            # Social media skills
│   └── audit/             # Audit and reporting skills
├── config/                # Configuration files
│   ├── settings.py        # Central configuration
│   ├── .env.example       # Environment template
│   └── credentials/       # Credential storage
├── logs/                  # Audit logs
├── events/                # Event queue
├── plans/                 # Execution plans
├── reports/               # Generated reports
│   ├── audits/            # Weekly audit reports
│   └── briefings/         # CEO briefings
├── main.py                # Entry point
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## Components

### 1. Odoo MCP Server
Integrates with Odoo Community Edition (19+) via JSON-RPC:
- Invoice management (create, send, track)
- Expense tracking and categorization
- Income recording
- Financial report generation
- Journal entries

### 2. Social Media MCP Server
Manages social presence across platforms:
- Facebook page posting and analytics
- Instagram content scheduling
- Twitter/X engagement
- Cross-platform summary generation

### 3. Audit MCP Server
Ensures compliance and visibility:
- Weekly business audits
- Weekly accounting audits
- CEO briefing generation
- Compliance checks
- Comprehensive logging

### 4. Ralph Wiggum Loop
Autonomous task execution engine:
1. **Plan** - Analyze task and create execution plan
2. **Execute** - Run the plan step by step
3. **Verify** - Check results against expected outcomes
4. **Retry** - If failed, adjust and retry (up to max attempts)
5. **Report** - Document outcome and lessons learned

## Risk Levels

| Level | Description | Approval Required |
|-------|-------------|-------------------|
| LOW | Read operations, internal analytics | No |
| MEDIUM | Social posts, draft invoices | Yes |
| HIGH | Send invoices, financial transactions | Yes |
| CRITICAL | Delete operations, bulk actions | Yes + Confirmation |

## Getting Started

1. Copy `.env.example` to `.env` and configure credentials
2. Install dependencies: `pip install -r requirements.txt`
3. Configure Odoo connection in settings
4. Set up social media API tokens
5. Run: `python main.py`

## Configuration

See `config/settings.py` for all configurable options including:
- Odoo server URL and credentials
- Social media API tokens
- Audit schedules
- Logging levels
- Retry policies
