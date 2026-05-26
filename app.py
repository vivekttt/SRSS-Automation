import streamlit as st
import pandas as pd
import time
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from main import run_regional_worker, BASE_DIR, SDK_PATH

st.set_page_config(page_title="SRSS Global Dashboard", page_icon="🚜", layout="wide")

if not os.path.exists(SDK_PATH):
    st.error(f"⚠️ SYSTEM WARNING: SAP NWRFC SDK was not detected at: {SDK_PATH}. Please verify your folder setup.")

def parse_uploaded_file_to_regions(file_buffer):
    if file_buffer.name.endswith('.xlsx') or file_buffer.name.endswith('.xls'):
        df = pd.read_excel(file_buffer)
    else:
        df = pd.read_csv(file_buffer)
    
    target_col = None
    for col in df.columns:
        norm_col = str(col).strip().lower()
        if 'dist' in norm_col and 'code' in norm_col:
            target_col = col
            break
            
    if not target_col:
        target_col = df.columns[0]
        st.warning(f"⚠️ Header 'Dist Code' not found. Analyzing the first column: **'{target_col}'**")

    clean_series = df[target_col].dropna()
    all_codes = []
    for raw_val in clean_series.unique():
        str_val = str(raw_val).strip().upper()
        if str_val and str_val not in ['NAN', 'NAT', 'NONE']:
            all_codes.append(str_val)
            
    regions = {
        "NORTH": [c for c in all_codes if c.startswith('N')],
        "SOUTH": [c for c in all_codes if c.startswith('S')],
        "EAST":  [c for c in all_codes if c.startswith('E')],
        "WEST":  [c for c in all_codes if c.startswith('W')],
        "MISC":  [c for c in all_codes if not c.startswith(('N', 'S', 'E', 'W'))]
    }
    return regions

st.title("🚜 SRSS Global Distribution Automator")
st.markdown("Run high-throughput parallel regional stock updates and harvests from a centralized cockpit.")

with st.sidebar:    
    st.header("⚙️ Target Control Configuration")
    target_sys = st.selectbox("Select Target Environment", ["IRT", "IRD", "IRP"])
    
    st.divider()
    st.subheader("📅 Date Window Configuration")
    col_a, col_b = st.columns(2)
    d_start = col_a.date_input("Start Date", datetime(2026, 2, 1))
    d_end = col_b.date_input("End Date", datetime(2026, 2, 28))
    
    st.divider()
    st.caption("⚡ This interface leverages concurrent multithreading to manage 4 isolated SAP network connections simultaneously.")

uploaded_file = st.file_uploader("Drop your 'active dist list.xlsx' or CSV file here", type=["xlsx", "xls", "csv"])

if uploaded_file:
    with st.spinner("Analyzing data structure and parsing regional lanes..."):
        REGIONS = parse_uploaded_file_to_regions(uploaded_file)
    
    st.subheader("📊 Dynamic Regional Lane Breakdown")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("North Lane", f"{len(REGIONS['NORTH'])} sites")
    m2.metric("South Lane", f"{len(REGIONS['SOUTH'])} sites")
    m3.metric("East Lane", f"{len(REGIONS['EAST'])} sites")
    m4.metric("West Lane", f"{len(REGIONS['WEST'])} sites")
    m5.metric("Misc / Unmapped", f"{len(REGIONS['MISC'])} sites")

    active_lanes = {name: sites for name, sites in REGIONS.items() if len(sites) > 0 and name != "MISC"}

    st.divider()
    if st.button("🚀 Launch Parallel Global Execution", type="primary"):
        global_start_time = time.perf_counter()
        
        sap_start = d_start.strftime("%Y%m%d")
        sap_end = d_end.strftime("%Y%m%d")
        
        st.subheader("📡 Live Execution Output Streams")
        
        with st.status(f"Connecting to SAP {target_sys} and initializing execution lanes...", expanded=True) as status_box:
            
            with ThreadPoolExecutor(max_workers=len(active_lanes)) as executor:
                futures = {
                    executor.submit(run_regional_worker, name, target_sys, sites, sap_start, sap_end): name
                    for name, sites in active_lanes.items()
                }
                
                for future in as_completed(futures):
                    lane_name = futures[future]
                    try:
                        result_msg = future.result()
                        
                        if "✅" in result_msg:
                            st.success(result_msg)
                        elif "⚠️" in result_msg:
                            st.warning(result_msg)
                        else:
                            st.error(result_msg)
                            
                    except Exception as exc:
                        st.error(f"❌ [{lane_name} Lane] Unhandled thread exception: {exc}")
            
            status_box.update(label="All Parallel Tasks Completed!", state="complete")
        
        global_duration = (time.perf_counter() - global_start_time) / 60
        st.balloons()
        st.write(f"⏱️ **Total Processing Pipeline Runtime:** {global_duration:.2f} minutes")
        
        st.subheader("📥 Generated Reports Download Hub")
        st.markdown("Grab your compiled Excel reports directly from the server:")
        
        download_cols = st.columns(4)
        col_idx = 0
        
        for file in os.listdir(BASE_DIR):
            if file.startswith("SRSS_") and file.endswith(".xlsx"):
                file_path = os.path.join(BASE_DIR, file)
                if os.path.getmtime(file_path) > (time.time() - 3600):
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()
                    
                    with download_cols[col_idx % 4]:
                        st.download_button(
                            label=f"Download {file.split('_')[1]} Report",
                            data=file_bytes,
                            file_name=file,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_{file}"
                        )
                    col_idx += 1

else:
    st.info("💡 To begin processing, please drag and drop or upload your master Distributor List Excel sheet above.")