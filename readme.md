# SRSS Stock Movement Integrator (SAP Automation)

A portable, Python-based automation suite designed to trigger high-volume SAP SRSS (Stock Reporting) movements and consolidate the results into a single Master Excel file. Built to automate 1,900+ sites by bridging Python and SAP via RFC (Remote Function Calls).

---

## 🚀 Features

* **Zero-Install Portability:** Includes the SAP NWRFC SDK within the project structure, allowing the tool to run on any machine without complex system-wide environment setup.
* **Two-Phase Execution:**
    * **Phase 1 (Trigger):** Calls custom ABAP RFCs (`ZSRSS_RFC_STOCK_UPDATE`) to process background logs.
    * **Phase 2 (Harvest):** Uses `RFC_READ_TABLE` to extract results into a standardized Excel report.
* **Robust Manual Parser:** Bypasses standard SAP `.ini` parsing to avoid common `rc=20` encoding errors.
* **Self-Healing Environment:** Automated `.bat` utility to create local Virtual Environments (`venv`) and install dependencies with one click.

---

## 📂 Project Structure

```text
SRSS-Automation/
├── nwrfcsdk/             # SAP NetWeaver RFC SDK (Proprietary binaries)
├── venv/                 # Local Python Virtual Environment (created via setup)
├── main.py               # The Core Integrator Script
├── saprfc.ini            # Connection settings (SNC, Host, Client) - [LOCAL ONLY]
├── saprfc.ini.template   # Example config for GitHub/New Users
├── requirements.txt      # Python library dependencies
├── setup_env.bat         # Automated environment installer
├── run_tool.bat          # One-click execution script
└── .gitignore            # Protects SDK and credentials from being pushed

```

---

## 🛠️ Installation & Setup

### 1. Prerequisites
* **Python 3.12.x:** Ensure Python 3.12 is installed (it is the most stable version for `pyrfc` pre-compiled wheels).
* **SAP SDK:** Place your `nwrfcsdk` folder into the root of this project directory.

### 2. Configuration
1.  Locate `saprfc.ini.template`.
2.  Rename it to `saprfc.ini`.
3.  Update the **ASHOST**, **SYSNR**, **CLIENT**, and **SNC** parameters to match your specific SAP environment.

### 3. Build the Environment
Double-click **`setup_env.bat`**. This script will:
* Build a localized virtual Python environment (`venv`).
* Upgrade `pip` to the latest version.
* Install **Pandas**, **Openpyxl**, and **PyRFC** automatically.

### 4. Execute the Tool
Double-click **`run_tool.bat`**. The tool will:
* Establish a secure connection to SAP.
* Trigger the background reports for the site list defined in `main.py`.
* Harvest the data and save a timestamped Excel extract into the project folder.

---

## 📡 Technical Logic: The "Harvest"
The tool utilizes `RFC_READ_TABLE` with a partitioned site list to prevent buffer overflows during extraction. This ensures that even when harvesting data for 1,900+ sites across a full month:
* The connection remains stable.
* The memory footprint is minimized.
* Data integrity is maintained through automated whitespace stripping and date standardization.

---

## ⚠️ Security Notice
* **Credentials:** This repository uses a `.gitignore` to prevent `saprfc.ini` from being pushed to version control. **Never** remove `saprfc.ini` from the ignore list or commit real IP addresses/SNC names.
* **Licensing:** The SAP NWRFC SDK is proprietary software owned by SAP SE. This repository contains the code to interface with it, but the SDK binaries themselves must be sourced legally from the SAP Support Portal.

---

## 👤 Author & Contact
**Vivek Tiwari** GitHub: [@vivekttt](https://github.com/vivekttt)