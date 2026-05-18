import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor

# ==========================================================
# 1. SAP SDK & PATH SETUP
# ==========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SDK_PATH = os.path.join(BASE_DIR, "nwrfcsdk", "lib")
INI_PATH = os.path.join(BASE_DIR, "saprfc.ini")
DIST_FILE = os.path.join(BASE_DIR, "active dist list.xlsx - Sheet1.csv")

if os.path.exists(SDK_PATH):
    os.add_dll_directory(SDK_PATH)
from pyrfc import Connection

# ==========================================================
# 2. DATA PROCESSING: REGIONAL SPLIT
# ==========================================================
def load_regional_sites():
    if not os.path.exists(DIST_FILE):
        st.error(f"Missing distributor list: {DIST_FILE}")
        return {}
    
    df = pd.read_csv(DIST_FILE)
    df['Dist Code'] = df['Dist Code'].astype(str).str.strip()
    
    # Map first letter to Region
    mapping = {'N': 'NORTH', 'S': 'SOUTH', 'E': 'EAST', 'W': 'WEST'}
    df['Region'] = df['Dist Code'].str[0].map(mapping)
    
    regions = {}
    for r_name in mapping.values():
        regions[r_name] = df[df['Region'] == r_name]['Dist Code'].tolist()
    return regions

# ==========================================================
# 3. SAP WORKER (Running in Parallel)
# ==========================================================
def run_regional_worker(region_name, dest, sites, start, end):
    try:
        # Load config inside worker for process independence
        from main import get_sap_config # Assuming helper is in main.py
        sap_params = get_sap_config(dest)
        conn = Connection(**sap_params)
        
        # --- Phase 1: Trigger ---
        for site in sites:
            try:
                conn.call('ZSRSS_RFC_STOCK_UPDATE', IV_DISTRI=site, 
                          IV_DATE_FR=start, IV_DATE_TO=end, IV_UPDATE='X')
            except: pass # Ignore UI closures
            
        # --- Phase 2: Harvest ---
        where = []
        for i, site in enumerate(sites):
            cond = f"WERKS EQ '{site}'"
            if i < len(sites) - 1: cond += " OR "
            where.append({'TEXT': cond})

        result = conn.call('RFC_READ_TABLE', QUERY_TABLE='ZSRSS_STOCK_LOG', 
                           DELIMITER='^', OPTIONS=where)

        fields = [f['FIELDNAME'] for f in result['FIELDS']]
        data = [row['WA'].split('^')[:len(fields)] for row in result['DATA']]
        
        df_out = pd.DataFrame(data, columns=fields)
        output_name = f"SRSS_{region_name}_{datetime.now().strftime('%H%M')}.xlsx"
        df_out.to_excel(output_name, index=False)
        
        return True, region_name, len(df_out), output_name
    except Exception as e:
        return False, region_name, str(e), None

# ==========================================================
# 4. STREAMLIT UI
# ==========================================================
st.set_page_config(page_title="SRSS Global Automator", layout="wide")
st.title("🚜 SRSS Global Distribution Automator")

# Load sites once
REGIONS = load_regional_sites()

with st.sidebar:
    st.header("Control Panel")
    target = st.selectbox("Target System", ["IRD", "IRT"])
    d_start = st.date_input("From", datetime(2026, 2, 1))
    d_end = st.date_input("To", datetime(2026, 2, 28))
    
    selected_regions = st.multiselect("Regions", list(REGIONS.keys()), default=list(REGIONS.keys()))

if st.button("🚀 Start Global Run"):
    st.info(f"Initiating parallel lanes for {len(selected_regions)} regions...")
    
    start_ts = time.perf_counter()
    p_bar = st.progress(0)
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = []
        for r in selected_regions:
            futures.append(executor.submit(run_regional_worker, r, target, REGIONS[r], 
                                         d_start.strftime("%Y%m%d"), d_end.strftime("%Y%m%d")))
        
        for i, future in enumerate(futures):
            success, r_name, info, file_path = future.result()
            if success:
                st.success(f"✅ {r_name} Finished: {info} rows extracted.")
                # Show Download Link
                with open(file_path, "rb") as f:
                    st.download_button(f"📥 Download {r_name} Excel", f, file_name=file_path)
            else:
                st.error(f"❌ {r_name} Failed: {info}")
            
            p_bar.progress((i + 1) / len(selected_regions))

    total_time = (time.perf_counter() - start_ts) / 60
    st.balloons()
    st.write(f"⏱️ Total Execution Time: {total_time:.2f} minutes")