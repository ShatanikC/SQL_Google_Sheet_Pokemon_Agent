# SQL_Google_Sheet_Pokemon_Agent
An autonomous Text-to-SQL Streamlit agent that securely ingests live Google Sheets data into an optimized SQLite database. Powered by LangChain and Groq, it features a built-in self-correcting loop that intercepts, analyzes, and automatically fixes syntax errors over multiple execution attempts before rendering clean data tables to the user.

# ⚡ A Simple Pokémon SQL Agent

[![Streamlit App](https://static.streamlit.io/badge-svg.svg)](https://share.streamlit.io/)
![LangChain](https://img.shields.io/badge/Framework-LangChain-black?style=flat-square)
![Groq](https://img.shields.io/badge/LLM-Groq%20Llama%203.3-orange?style=flat-square)
![SQLite](https://img.shields.io/badge/Database-SQLite-blue?style=flat-square)
![SQLAlchemy](https://img.shields.io/badge/Toolkit-SQLAlchemy-red?style=flat-square)

An intelligent, self-correcting Natural Language-to-SQL (Text-to-SQL) data agent built with **Streamlit**, **LangChain**, and **Groq (Llama-3.3-70b)**. This system securely ingests live tabular insights from a targeted Google Sheet, automatically transforms and registers schema records inside an operational SQLite repository, and enables users to query data via simple conversational text.

---

## 🚀 Key Structural Features

* **Dynamic Sheets Ingestion:** Utilizes a secure GCP service account workspace connection to parse target data structures via the Google Sheets API.
* **Schema Normalization Engine:** Strips dataframe spaces and problematic strings to provision a clean database table structure (`pokemon_data`).
* **Self-Correction Compilation Loop:** Includes an isolated execution tracking system that captures execution anomalies (`sqlite3.OperationalError`, structural bugs) and transparently issues up to **3 automated corrective passes** through an autonomous correction LLM chain.
* **Masked Error Logging:** Intercepts low-level stack traces and transforms potentially sensitive system/database strings into sanitized diagnostic feedback blocks for non-technical users.

---

## 🛠️ System Workflow

1. **Ingestion Tier:** Google Sheets API ➔ Staging Pandas Dataframe ➔ Columns Sanitized.
2. **Persistence Tier:** SQLAlchemy Engine ➔ SQLite DB Engine (`pokemon.db`) ➔ `pokemon_data` Table Ingestion.
3. **Prompt Framework:** Context Mapping (`get_lean_schema`) + User Prompt Injection ➔ Llama-3.3-70b Inference ➔ SQL String Extraction.
4. **Resilient Execution Evaluation:** * **If Execution Succeeds:** Displays sanitized data results directly to the Streamlit UI frame.
   * **If Execution Fails:** Invokes `correction_chain` with Schema Context + Failed Query Context + Target Error Log. Loops until success or retry index hits limit (Max 3 attempts).

---

## 📋 Production Configuration (Secrets Management)

For deployment via **Streamlit Community Cloud**, ensure your environment properties remain secure. Do not push standard `.env` or local secrets assets directly into public source trees. Navigate to your app settings panel via your **Streamlit Workspace Dashboard**, access the **Secrets** panel, and inject this compliant TOML layout:

```toml
# Streamlit Cloud Production Secrets Configuration
groq = "gsk_your_secure_groq_api_token_here"

[google_sheet]
sheet_id = "your_google_spreadsheet_unique_id_string"
sheet_range = "Sheet1!A1:Z100"

[gcp_service_account]
type = "service_account"
project_id = "your-gcp-project-id"
private_key_id = "your_private_key_identifier"
private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your_client_id_numeric_string"
auth_uri = "[https://accounts.google.com/o/oauth2/auth](https://accounts.google.com/o/oauth2/auth)"
token_uri = "[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)"
auth_provider_x509_cert_url = "[https://www.googleapis.com/oauth2/v1/certs](https://www.googleapis.com/oauth2/v1/certs)"
client_x509_cert_url = "[https://www.googleapis.com/robot/v1/metadata/x509/](https://www.googleapis.com/robot/v1/metadata/x509/)..."
universe_domain = "googleapis.com"