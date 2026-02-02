# Financial Reconciliation System

An AI-powered financial reconciliation platform that intelligently matches CRM invoices with ERP bank transactions using LangChain and Google Gemini. The system performs comprehensive auditing to detect complex financial anomalies including currency mismatches, tax discrepancies, and pricing errors.

## 🎯 Features

- **🤖 AI-Powered Matching**: LangChain-based agent using Google Gemini for intelligent invoice-to-payment reconciliation
- **🔍 Multi-Layer Analysis**: 
  - Rule-based integrity auditing (Ghost Payments, Orphan Transactions, Outstanding Invoices)
  - AI-driven anomaly detection (Currency, Tax, Price discrepancies)
- **📊 Interactive Dashboard**: Professional Streamlit UI with real-time visualizations
- **🔗 Dolibarr Integration**: Seamless connection to Dolibarr ERP/CRM via REST API
- **🎨 Data Visualization**: Altair charts for severity distribution and discrepancy analysis

## 🏗️ Architecture

```
projet-s/
├── src/
│   ├── core/
│   │   ├── agentic_matcher.py    # LangChain reconciliation agent
│   │   ├── analyst.py            # AI financial anomaly detector
│   │   ├── audit.py              # Rule-based integrity checks
│   │   └── llm_client.py         # LLM abstraction layer
│   ├── integrations/
│   │   └── dolibarr.py           # Dolibarr API client
│   ├── db/
│   │   └── schema.py             # SQLAlchemy models
│   ├── ui/
│   │   └── app.py                # Streamlit dashboard
│   └── config.py                 # Configuration management
├── data/
│   └── project.db                # SQLite database
├── docker-compose.yml            # Dolibarr + MariaDB setup
└── requirements.txt
```

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.10 or higher
- **Docker & Docker Compose**: For running Dolibarr ERP
- **Google Gemini API Key**: [Get one here](https://aistudio.google.com/app/apikey)

### 1. Clone the Repository

```bash
git clone https://github.com/louishorlaville/projet-s.git
cd projet-s
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

Edit `src/config.py` with your credentials:

```python
# Dolibarr Configuration
DOLIBARR_API_URL = "http://localhost:8080/api/index.php"
DOLIBARR_API_KEY = "your_dolibarr_api_key"

# LLM Configuration
LLM_PROVIDER = "gemini"
LLM_API_KEY = "your_gemini_api_key"
LLM_MODEL = "gemini-2.5-flash"
```

> **⚠️ Security Note**: For production, use environment variables instead of hardcoding credentials.

### 4. Start Dolibarr ERP

```bash
docker-compose up -d
```

Access Dolibarr at `http://localhost:8080`:
- **Username**: `admin`
- **Password**: `admin`

**Initial Setup**:
1. Navigate to **Setup → Modules** and enable:
   - Invoices
   - Third Parties
   - Bank & Cash
2. Go to **Setup → API/Webservices** and generate an API key
3. Update `src/config.py` with the generated API key

### 5. Initialize Database

```bash
python -c "from src.db.schema import get_engine, init_db; init_db(get_engine('data/project.db'))"
```

### 6. Launch the Application

```bash
venv/bin/streamlit run src/ui/app.py
```

The dashboard will open at `http://localhost:8501`

## 📖 Usage

### Running Reconciliation

1. **Prepare Data in Dolibarr**:
   - Create Third Parties (Customers)
   - Generate Invoices
   - Record Bank Transactions

2. **Execute Reconciliation**:
   - Click **"Run Reconciliation"** in the sidebar
   - The system will:
     - Match invoices to payments using AI
     - Perform integrity audits
     - Detect complex financial anomalies
     - Display unified discrepancy analysis

3. **Review Results**:
   - **Accounts Receivable**: View all invoices with status
   - **Bank Transactions**: Review payment records
   - **Reconciliation Results**: See matched pairs with confidence scores
   - **Discrepancy Analysis**: Investigate detected issues with visualizations

### Understanding Discrepancies

| Type                  | Source      | Severity    | Description                                                  |
| --------------------- | ----------- | ----------- | ------------------------------------------------------------ |
| **GHOST_PAYMENT**     | Rule-Based  | HIGH        | Invoice marked PAID in Dolibarr but no reconciliation record |
| **ORPHAN_PAYMENT**    | Rule-Based  | MEDIUM      | Bank transaction with no matching invoice                    |
| **OUTSTANDING**       | Rule-Based  | MEDIUM      | Unpaid invoice with no payment match                         |
| **CURRENCY_MISMATCH** | AI Analysis | HIGH        | Invoice/Payment currency discrepancy                         |
| **TAX_ERROR**         | AI Analysis | MEDIUM      | Inconsistent or missing tax amounts                          |
| **PRICE_DISCREPANCY** | AI Analysis | MEDIUM-HIGH | Significant amount differences (>2%)                         |

## 🛠️ Development

### Project Structure

- **`src/core/`**: Business logic and AI agents
- **`src/integrations/`**: External system connectors
- **`src/ui/`**: User interface components
- **`src/db/`**: Data models and persistence
- **`src/utils/`**: Helper scripts and utilities

### Utility Scripts

```bash
# Clear reconciliation results
python src/utils/clear_reconciliation.py

# Clean application state
python src/utils/clean_state.py
```

### Testing

```bash
# Run tests (if available)
pytest tests/
```

## 🔧 Configuration

### LLM Models

The system supports Google Gemini models. To change the model:

```python
# src/config.py
LLM_MODEL = "gemini-2.5-flash"  # Fast, cost-effective
# LLM_MODEL = "gemini-1.5-pro"  # More accurate, slower
```

### Database

By default, SQLite is used (`data/project.db`). For production, consider PostgreSQL:

```python
# src/db/schema.py
DATABASE_URL = "postgresql://user:password@localhost/reconciliation"
```

## 📊 Technology Stack

- **Backend**: Python 3.10+
- **AI Framework**: LangChain, Google Gemini
- **UI**: Streamlit
- **Visualization**: Altair
- **Database**: SQLAlchemy (SQLite/PostgreSQL)
- **ERP**: Dolibarr
- **Containerization**: Docker

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🙏 Acknowledgments

- Built with [LangChain](https://www.langchain.com/)
- Powered by [Google Gemini](https://ai.google.dev/)
- ERP integration via [Dolibarr](https://www.dolibarr.org/)
- UI framework by [Streamlit](https://streamlit.io/)

## 📧 Contact

For questions or support, please open an issue on GitHub.
