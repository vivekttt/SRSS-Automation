# SRSS Stock Movement Integrator

Automated tool to trigger SAP SRSS reports and harvest data into Excel.

## 🚀 Setup Instructions

1. **Clone the repo.**
2. **Add the SAP SDK:** - Download the SAP NWRFC SDK from the SAP Support Portal.
   - Extract it into a folder named `nwrfcsdk` in the root of this project.
3. **Configure Connection:**
   - Rename `saprfc.ini.example` to `saprfc.ini`.
   - Update it with your specific SAP server details.
4. **Build Environment:**
   - Double-click `setup_env.bat` to create the virtual environment and install dependencies.
5. **Run:**
   - Double-click `run_tool.bat`.