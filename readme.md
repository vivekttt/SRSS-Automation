SRSS Stock Movement Integrator (SAP Automation)
A portable, Python-based automation suite designed to trigger high-volume SAP SRSS (Stock Reporting) movements and consolidate the results into a single Master Excel file. This tool is built to handle the automation of over 1,900+ sites by bridging the gap between Python and SAP via RFC (Remote Function Calls).

🚀 Features
Zero-Install Portability: Includes the SAP NWRFC SDK within the project structure, allowing the tool to run on any machine without complex environment variable setup.

Two-Phase Execution:

Phase 1 (Trigger): Calls custom ABAP RFCs (ZSRSS_RFC_STOCK_UPDATE) to process background stock logs for a specified date range and site list.

Phase 2 (Harvest): Uses RFC_READ_TABLE to extract the generated results into a standardized Excel report.

Robust Manual Parser: Bypasses standard SAP .ini parsing to avoid common rc=20 encoding errors (BOM/UTF-8 mismatches).

Self-Healing Environment: Includes a dedicated .bat utility to create local Virtual Environments (venv) and install dependencies (Pandas, Openpyxl, PyRFC) with one click.

📂 Project Structure
Plaintext
SRSS-Automation/
├── nwrfcsdk/             # SAP NetWeaver RFC SDK (Proprietary binaries)
├── venv/                 # Local Python Virtual Environment (created via setup)
├── main.py               # The Core Integrator Script
├── saprfc.ini            # Connection settings (SNC, Host, Client)
├── saprfc.ini.template   # Example config for GitHub/New Users
├── requirements.txt      # Python library dependencies
├── setup_env.bat         # Automated environment installer
├── run_tool.bat          # One-click execution script
└── .gitignore            # Protects SDK and credentials from being pushed
🛠️ Setup Instructions
1. Prerequisites
Python 3.12.x: (Recommended for stable pyrfc support).

SAP NWRFC SDK: You must have the SDK binaries. (Place the nwrfcsdk folder in the project root).

SAP Access: RFC-enabled user credentials and authorization for ZSRSS_RFC_STOCK_UPDATE.

2. Configure Connection
Locate saprfc.ini.template.

Rename it to saprfc.ini.

Update the fields (ASHOST, SYSNR, SNC_PARTNERNAME, etc.) with your environment details.

3. Installation
Double-click setup_env.bat. This script will:

Create a local venv.

Upgrade pip.

Install all necessary libraries automatically.

📡 How it Works
The tool operates in a Stateful Connection model:

Phase 1 (The Trigger): The script loops through the TARGET_SITES provided in main.py. For each site, it calls the RFC. This populates the custom SAP table ZSRSS_STOCK_LOG.

Phase 2 (The Harvest): Once the triggering is complete, a high-speed RFC_READ_TABLE call is made. It uses a dynamic WHERE clause to fetch only the data for the requested sites and date range.

The Output: Data is cleaned (whitespace stripped), date-formatted, and exported to a timestamped Excel file.

⚠️ Security & Licensing
SAP Proprietary SDK: The nwrfcsdk folder is excluded via .gitignore. You must obtain these binaries directly from the SAP Support Portal per company licensing agreements.

Credentials: Never commit the saprfc.ini file. Use the provided .template for sharing the project structure.

SNC Support: This tool is pre-configured to support Secure Network Communications (SNC) via sapcrypto.dll.

🩺 Troubleshooting
rc=20 (Missing Parameters): Ensure your saprfc.ini is in the same folder as main.py and that the DEST name matches exactly in the code.

rc=6 (Connection Closed): This often occurs when triggering UI-heavy reports. The script is designed to catch this error and continue the process as "Successful" if the database update was triggered.

DLL Load Failed: Ensure you are using Python 3.12 and that the nwrfcsdk/lib folder exists.

Author: @vivekttt