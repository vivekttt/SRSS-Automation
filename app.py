import streamlit as st
import pandas as pd
import time
import os
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from main import run_regional_worker, BASE_DIR, SDK_PATH

st.set_page_config(page_title="SRSS Global Dashboard", page_icon="🚜", layout="wide")

if "stop_event" not in st.session_state:
    st.session_state.stop_event = threading.Event()

if "is_running" not in st.session_state:
    st.session_state.is_running = False

def load_file_to_dataframe(file_buffer):
    if file_buffer.name.lower().endswith(('.xlsx', '.xls')):
        return pd.read_excel(file_buffer)
    
    try:
        file_buffer.seek(0)
        return pd.read_csv(file_buffer, encoding='utf-8')
    except Exception:
        pass
        
    try:
        file_buffer.seek(0)
        return pd.read_csv(file_buffer, encoding='latin-1')
    except Exception:
        pass
        
    try:
        file_buffer.seek(0)
        return pd.read_csv(file_buffer, encoding='latin-1', sep=None, engine='python', on_bad_lines='skip')
    except Exception as e:
        st.error(f"❌ Critical Structural CSV Failure: {e}")
        return None

def group_series_into_regions(df, chosen_column):
    clean_series = df[chosen_column].dropna()
    all_codes = []
    for raw_val in clean_series.unique():
        str_val = str(raw_val).strip().replace('"', '').replace("'", "").upper()
        if str_val and str_val not in ['NAN', 'NAT', 'NONE']:
            all_codes.append(str_val)
            
    return {
        "NORTH": [c for c in all_codes if c.startswith('N')],
        "SOUTH": [c for c in all_codes if c.startswith('S')],
        "EAST":  [c for c in all_codes if c.startswith('E')],
        "WEST":  [c for c in all_codes if c.startswith('W')],
        "MISC":  [c for c in all_codes if not c.startswith(('N', 'S', 'E', 'W'))]
    }

st.title("🚜 SRSS Global Distribution Automator")
st.markdown("Run high-throughput parallel regional stock updates and harvests from a centralized cockpit.")

with st.sidebar:
    st.header("⚙️ Target Control Configuration")
    target_sys = st.selectbox("Select Target Environment", ["IRT", "IRD"], disabled=st.session_state.is_running)
    
    st.divider()
    st.subheader("📅 Date Window Configuration")
    col_a, col_b = st.columns(2)
    d_start = col_a.date_input("Start Date", datetime(2026, 2, 1), disabled=st.session_state.is_running)
    d_end = col_b.date_input("End Date", datetime(2026, 2, 28), disabled=st.session_state.is_running)
    
    st.divider()
    st.subheader("🔧 Advanced RFC Configuration")
    iv_update_bool = st.toggle("Enable SAP Table Update (IV_UPDATE = 'X')", value=True, disabled=st.session_state.is_running)
    chosen_iv_update = 'X' if iv_update_bool else ''
    st.markdown(f"**Current Status:** Sending `IV_UPDATE = '{chosen_iv_update}'`")

    st.divider()
    
    if st.session_state.is_running:
        st.subheader("🚨 Active Run Management")
        if st.button("🛑 Terminate Active Run", type="primary", use_container_width=True):
            st.session_state.stop_event.set()
            st.session_state.is_running = False
            st.error("🔄 Termination signal sent! Dropping process lanes...")
            time.sleep(1)
            st.rerun()
    else:
        st.caption("⚡ System Status: Idle. Pool ready.")

uploaded_file = st.file_uploader("Drop your 'active dist list.xlsx' or CSV file here", type=["xlsx", "xls", "csv"], disabled=st.session_state.is_running)

if uploaded_file:
    raw_df = load_file_to_dataframe(uploaded_file)
    
    if raw_df is not None:
        columns_list = list(raw_df.columns)
        
        default_idx = 0
        for idx, col in enumerate(columns_list):
            c_norm = str(col).lower()
            if any(k in c_norm for k in ['code', 'plant', 'werks', 'site', 'distributor', 'dist']):
                default_idx = idx
                break
        
        st.success("📂 File loaded successfully!")
        selected_col = st.selectbox(
            "🎯 **Verify/Select the Column containing your Distributor Codes:**", 
            columns_list, 
            index=default_idx, 
            disabled=st.session_state.is_running
        )
        
        REGIONS = group_series_into_regions(raw_df, selected_col)
        st.session_state.current_regions = REGIONS
        
        with st.expander("🔍 Click to preview extracted unique codes for verification", expanded=False):
            st.write(f"**Target Column Active Values Sample (First 15 extracted):**")
            all_found = REGIONS["NORTH"] + REGIONS["SOUTH"] + REGIONS["EAST"] + REGIONS["WEST"] + REGIONS["MISC"]
            st.code(", ".join(all_found[:15]))
        
        st.subheader("📊 Dynamic Regional Lane Breakdown")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("North Lane", f"{len(REGIONS['NORTH'])} sites")
        m2.metric("South Lane", f"{len(REGIONS['SOUTH'])} sites")
        m3.metric("East Lane", f"{len(REGIONS['EAST'])} sites")
        m4.metric("West Lane", f"{len(REGIONS['WEST'])} sites")
        m5.metric("Misc / Unmapped", f"{len(REGIONS['MISC'])} sites")

        active_lanes = {name: sites for name, sites in REGIONS.items() if len(sites) > 0 and name != "MISC"}

        st.divider()
        
        if not st.session_state.is_running:
            if len(active_lanes) == 0:
                st.error("❌ Extraction Error: Zero regional routes mapped. Please check your column dropdown selection above.")
            else:
                if st.button("🚀 Launch Parallel Global Execution", type="primary"):
                    st.session_state.is_running = True
                    st.session_state.stop_event.clear()
                    st.rerun()

        if st.session_state.is_running:
            global_start_time = time.perf_counter()
            sap_start = d_start.strftime("%Y%m%d")
            sap_end = d_end.strftime("%Y%m%d")
            
            st.subheader("📡 Live Execution Output Streams")
            
            with st.status(f"Connecting to SAP {target_sys} (IV_UPDATE='{chosen_iv_update}')...", expanded=True) as status_box:
                with ThreadPoolExecutor(max_workers=len(active_lanes)) as executor:
                    futures = {
                        executor.submit(run_regional_worker, name, target_sys, sites, sap_start, sap_end, chosen_iv_update, st.session_state.stop_event): name
                        for name, sites in active_lanes.items()
                    }
                    
                    for future in as_completed(futures):
                        lane_name = futures[future]
                        try:
                            result_msg = future.result()
                            if "✅" in result_msg:
                                st.success(result_msg)
                            elif "🛑" in result_msg:
                                st.error(result_msg)
                            else:
                                st.warning(result_msg)
                        except Exception as exc:
                            st.error(f"❌ [{lane_name} Lane] Unhandled thread crash: {exc}")
                
                st.session_state.is_running = False
                
                if st.session_state.stop_event.is_set():
                    status_box.update(label="Execution Aborted Midway!", state="error")
                    st.warning("⚠️ Execution was halted early. Reports may be incomplete.")
                else:
                    status_box.update(label="All Parallel Tasks Completed!", state="complete")
                    st.balloons()
                    global_duration = (time.perf_counter() - global_start_time) / 60
                    st.write(f"⏱️ **Total Pipeline Runtime:** {global_duration:.2f} minutes")

            if not st.session_state.stop_event.is_set():
                st.subheader("📥 Generated Reports Download Hub")
                download_cols = st.columns(4)
                col_idx = 0
                
                for file in os.listdir(BASE_DIR):
                    if file.startswith("SRSS_") and file.lower().endswith(".xlsx"):
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