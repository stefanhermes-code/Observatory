# Polyurethane Observatory Platform

A comprehensive three-app Streamlit platform for managing PU industry intelligence reports and specifications.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io/)

## 🎯 Overview

The Polyurethane Observatory Platform provides a complete solution for:
- **Public specification collection** (Configurator)
- **Administrative management** (Admin)
- **Report generation** (Generator)

All three applications work together to manage the full lifecycle of PU industry intelligence specifications and reports.

## 📱 Applications

### 1. Configurator (`configurator_app.py`)
**Public-facing app** for collecting intelligence specification requests from users.

**Features:**
- Multi-step form (6 steps: scope, regions, frequency, contact info, address, review)
- No authentication required
- Validates all inputs
- Stores specification requests to Supabase
- Displays pricing and order information
- Generates `mailto:` links for order placement

**Run locally:**
```bash
streamlit run configurator_app.py --server.port 8501
```
Or use: `run_configurator.bat` (Windows)

**Access:** http://localhost:8501

### 2. Admin (`admin_app.py`)
**Owner-only control tower** for managing the entire platform.

**Features:**
- Owner authentication (email + password)
- Dashboard with metrics and alerts
- Process specification requests (approve, reject, invoice, activate)
- Invoicing with VAT logic (Thai vs. Foreign companies)
- HTML invoice/receipt generation and download
- Company workspace management
- User and administrator management
- Intelligence specification management
- Reporting and analytics
- Generation history and audit logs
- Data export (CSV)

**Run locally:**
```bash
streamlit run admin_app.py --server.port 8502
```
Or use: `run_admin.bat` (Windows)

**Access:** http://localhost:8502

### 3. Generator (`generator_app.py`)
**Authenticated app** for workspace users to generate intelligence reports.

**Features:**
- Workspace-based authentication (email + password)
- View connected intelligence specifications
- Manual report generation with frequency enforcement
- Category and region selection for custom reports
- HTML preview with print functionality
- Download reports as HTML
- Complete generation history
- Frequency limits: Daily (1/day), Weekly (1/week), Monthly (1/month)
- Infinite frequency mode for testing/marketing accounts

**Run locally:**
```bash
streamlit run generator_app.py --server.port 8503
```
Or use: `run_generator.bat` (Windows)

**Access:** http://localhost:8503

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Supabase account and project
- OpenAI API key and Assistant ID

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/stefanhermes-code/Observatory.git
cd Observatory
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**

Create a `.env` file in the root directory:
```env
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_ASSISTANT_ID=your_openai_assistant_id
OPENAI_VECTOR_STORE_ID=your_vector_store_id  # Optional, for company list

# Admin Authentication
OWNER_EMAIL=your_admin_email@example.com
OWNER_PASSWORD=your_admin_password
```

4. **Set up Supabase database:**

Run the SQL schema from `development/supabase_schema.sql` in your Supabase SQL editor.

5. **Run an app:**

**Windows (using batch files):**
```bash
run_configurator.bat    # Port 8501
run_admin.bat           # Port 8502
run_generator.bat       # Port 8503
```

**Command line:**
```bash
streamlit run configurator_app.py --server.port 8501
streamlit run admin_app.py --server.port 8502
streamlit run generator_app.py --server.port 8503
```

## ☁️ Streamlit Cloud Deployment

### Deploy Individual Apps

Each app can be deployed separately on Streamlit Cloud:

1. **Push to GitHub** (this repository)

2. **Deploy on Streamlit Cloud:**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Connect your GitHub repository
   - Select the app file:
     - `configurator_app.py` for Configurator
     - `admin_app.py` for Admin
     - `generator_app.py` for Generator
   - Add your secrets (environment variables) in the Streamlit Cloud settings

### Required Secrets for Streamlit Cloud

Add these in Streamlit Cloud → Settings → Secrets:

```toml
[secrets]
SUPABASE_URL = "your_supabase_project_url"
SUPABASE_ANON_KEY = "your_supabase_anon_key"
OPENAI_API_KEY = "your_openai_api_key"
OPENAI_ASSISTANT_ID = "your_openai_assistant_id"
OPENAI_VECTOR_STORE_ID = "your_vector_store_id"
OWNER_EMAIL = "your_admin_email@example.com"
OWNER_PASSWORD = "your_admin_password"
```

### Important Notes for Cloud Deployment

- **File paths:** The apps reference `Background Documentation/` for logos. Ensure these files are committed to GitHub or use absolute URLs.
- **Ports:** Streamlit Cloud handles ports automatically - remove `--server.port` arguments for cloud deployment.
- **Environment variables:** All sensitive data must be in Streamlit Cloud secrets, not in `.env` files.

## 📁 Project Structure

```
.
├── configurator_app.py          # Public specification builder
├── admin_app.py                 # Owner control tower
├── generator_app.py             # Authenticated report generator
├── core/                        # Shared modules
│   ├── __init__.py
│   ├── taxonomy.py              # 11 categories + regions + frequencies
│   ├── validation.py             # Form validation functions
│   ├── database.py              # Configurator database operations
│   ├── admin_db.py              # Admin database operations
│   ├── generator_db.py         # Generator database operations
│   ├── generator_execution.py  # Generator execution flow
│   ├── content_pipeline.py     # Report content generation
│   ├── openai_assistant.py     # OpenAI Assistant integration
│   ├── invoice_generator.py    # Invoice/receipt HTML generation
│   ├── pricing.py              # Pricing calculations
│   ├── auth.py                 # Authentication utilities
│   ├── admin_users.py          # Admin user management
│   ├── workspace_users.py     # Workspace user management
│   └── company_list_manager.py # Company list management
├── development/                # Development docs and scripts
│   ├── supabase_schema.sql     # Database schema
│   ├── OpenAI_Assistant_Instructions_Complete.txt
│   ├── COMPANY_LIST_SETUP.md
│   └── [other development files]
├── Background Documentation/   # Design documents and assets
│   ├── PU Observatory logo V3.png
│   ├── Logo in blue steel no BG.png
│   └── [design documents]
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

## 🎯 Core Concepts

### 11 Intelligence Deliverables
1. Company News Tracking
2. Regional Market Monitoring
3. Industry Context & Insight
4. PU Value-Chain Analysis
5. Competitive Intelligence
6. Sustainability & Regulation Tracking
7. Capacity & Asset Moves
8. M&A and Partnerships
9. Early-Warning Signals
10. Custom Alerts & Updates
11. Executive-Ready Briefings

### Frequency Options
- **Daily**: Continuous monitoring, early-warning signals (1 report per day)
- **Weekly**: Operational monitoring with context (1 report per week)
- **Monthly**: Strategic overview, themes, and outlook (1 report per month)

### Workflow
1. User submits specification via Configurator
2. Admin reviews and approves request
3. Admin generates invoice (with VAT logic for Thai companies)
4. Admin marks request as paid → automatically creates workspace and activates specification
5. Users generate reports via Generator (manual trigger with frequency enforcement)
6. Reports are stored as HTML artifacts with full history

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Your Supabase anonymous key | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `OPENAI_ASSISTANT_ID` | OpenAI Assistant ID | Yes |
| `OPENAI_VECTOR_STORE_ID` | Vector store ID for company list | Optional |
| `OWNER_EMAIL` | Admin email for authentication | Yes |
| `OWNER_PASSWORD` | Admin password | Yes |

### Company List

The platform includes a company list feature (152+ PU industry companies) stored in OpenAI's vector store. See `development/COMPANY_LIST_SETUP.md` for setup instructions.

## 📊 Database Schema

The platform uses Supabase (PostgreSQL) with the following main tables:
- `specification_requests` - User specification submissions
- `company_workspaces` - Company workspaces
- `workspace_members` - Workspace users
- `newsletter_specifications` - Active intelligence specifications
- `newsletter_runs` - Report generation history
- `invoices` - Invoice records
- `audit_log` - Admin action audit trail
- `admin_users` - Admin user accounts

See `development/supabase_schema.sql` for the complete schema.

## 🔐 Security

- **Environment variables:** Never commit `.env` files or secrets to Git
- **Password hashing:** Uses `bcrypt` for workspace user passwords
- **Admin authentication:** Email + password for admin access
- **Workspace authentication:** Email + password for workspace users
- **Audit logging:** All admin actions are logged for traceability

## 🧪 Development

### Running Tests

Development scripts are in the `development/` directory:
- `test_supabase_connection.py` - Test Supabase connection
- `upload_company_list.py` - Upload company list to OpenAI
- `view_uploaded_content.py` - View vector store content

### Adding New Features

1. Core logic goes in `core/` modules
2. UI logic stays in app files (`*_app.py`)
3. Database operations in `*_db.py` modules
4. Update `requirements.txt` for new dependencies

## 📝 License

[Add your license here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📧 Support

For issues and questions, please open an issue on GitHub.

## 🔗 Links

- **GitHub Repository:** https://github.com/stefanhermes-code/Observatory
- **Streamlit Cloud:** [Add your Streamlit Cloud URLs here]

---

Built with ❤️ using [Streamlit](https://streamlit.io/)
