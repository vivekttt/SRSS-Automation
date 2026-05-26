import os
import sys
import time
import pandas as pd
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SDK_PATH = os.path.join(BASE_DIR, "nwrfcsdk", "lib")
INI_PATH = os.path.join(BASE_DIR, "saprfc.ini")

if os.path.exists(SDK_PATH):
    os.add_dll_directory(SDK_PATH)
else:
    print(f"❌ CRITICAL ERROR: SAP SDK not found at {SDK_PATH}")
    sys.exit(1)

from pyrfc import Connection, CommunicationError, LogonError

def get_sap_config(dest_name):
    if not os.path.exists(INI_PATH):
        raise FileNotFoundError(f"Cannot find {INI_PATH} at {BASE_DIR}")
    
    config = {}
    found_dest = False
    with open(INI_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(('/', '#', '*')): continue
            if '=' in line:
                key, val = [x.strip() for x in line.split('=', 1)]
                if key.upper() == 'DEST':
                    if found_dest: break 
                    if val.upper() == dest_name.upper():
                        found_dest = True
                        continue
                if found_dest:
                    config[key.lower()] = val
    if not config:
        raise ValueError(f"Destination '{dest_name}' not found in saprfc.ini")
    return config

def extract_regions_from_file(filename):
    file_path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Missing distributor list file: {file_path}")
    
    print(f"📡 Reading file: {filename}...")
    
    if filename.endswith('.xlsx') or filename.endswith('.xls'):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path)
    
    target_col = None
    for col in df.columns:
        norm_col = str(col).strip().lower()
        if 'dist' in norm_col and 'code' in norm_col:
            target_col = col
            break
            
    if not target_col:
        target_col = df.columns[0]
        print(f"⚠️ Could not find exact 'Dist Code' header. Defaulting to first column: '{target_col}'")
    else:
        print(f"🎯 Smart-matched distributor column: '{target_col}'")

    clean_series = df[target_col].dropna()
    
    all_codes = []
    for raw_val in clean_series.unique():
        str_val = str(raw_val).strip().upper()
        # Skip string representations of null blanks
        if str_val and str_val != 'NAN' and str_val != 'NAT' and str_val != 'NONE':
            all_codes.append(str_val)
    
    regions = {
        "NORTH": [c for c in all_codes if c.startswith('N')],
        "SOUTH": [c for c in all_codes if c.startswith('S')],
        "EAST":  [c for c in all_codes if c.startswith('E')],
        "WEST":  [c for c in all_codes if c.startswith('W')],
        "MISC":  [c for c in all_codes if not c.startswith(('N', 'S', 'E', 'W'))]
    }
    
    return regions

def run_regional_worker(region_name, dest_name, site_list, date_from, date_to):
    start_time = time.perf_counter()
    print(f"🚀 [{region_name} LANE] Thread started. Processing {len(site_list)} sites...")
    
    try:
        sap_params = get_sap_config(dest_name)
        conn = Connection(**sap_params)

        for site in site_list:
            try:
                conn.call('ZSRSS_RFC_STOCK_UPDATE', 
                          IV_DISTRI=site, IV_DATE_FR=date_from, 
                          IV_DATE_TO=date_to, IV_UPDATE='')
            except Exception as e:
                if "RFC_CLOSED" not in str(e) and "rc=6" not in str(e):
                    print(f"⚠️  [{region_name}] Site {site} warning: {e}")

        where_clause = []
        for i, site in enumerate(site_list):
            condition = f"WERKS EQ '{site}'" 
            if i < len(site_list) - 1: condition += " OR "
            where_clause.append({'TEXT': condition})

        result = conn.call('RFC_READ_TABLE', QUERY_TABLE='ZSRSS_STOCK_LOG', 
                           DELIMITER='^', OPTIONS=where_clause)

        fields = [f['FIELDNAME'] for f in result['FIELDS']]
        raw_rows = result['DATA']
        
        if raw_rows:
            data = [row['WA'].split('^')[:len(fields)] for row in raw_rows]
            df = pd.DataFrame(data, columns=fields)
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            
            for col in df.columns:
                if 'DATE' in col.upper() or 'DAT' in col.upper():
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%m/%d/%Y')
            
            ts = datetime.now().strftime('%Y%m%d_%H%M')
            output_file = os.path.join(BASE_DIR, f"SRSS_{region_name}_{ts}.xlsx")
            df.to_excel(output_file, index=False)
            
            end_time = time.perf_counter()
            duration = (end_time - start_time) / 60
            conn.close()
            return f"✅ [{region_name}] Finished! Rows harvested: {len(df)} | Time taken: {duration:.2f} mins"
        else:
            conn.close()
            return f"⚠️ [{region_name}] Finished! (No records found in ZSRSS_STOCK_LOG)"
            
    except Exception as e:
        return f"❌ [{region_name} CRITICAL FAILURE]: {e}"

if __name__ == "__main__":
    TARGET_SYSTEM = "IRT"
    
    INPUT_FILE = "active dist list.xlsx" 
    
    START_DATE = "20251001"
    END_DATE = "20251031"
    
    global_start = time.perf_counter()
    print(f"🏁 Starting Global Parallel Run against {TARGET_SYSTEM} at {datetime.now().strftime('%H:%M:%S')}")
    
    try:
        
        REGIONS = extract_regions_from_file(INPUT_FILE)
        
        active_regions = {name: sites for name, sites in REGIONS.items() if len(sites) > 0}
        
        for name, sites in active_regions.items():
            print(f"   📊 Region {name}: Found {len(sites)} sites")
            
        print("\n⚡ Initializing Parallel Execution Pool...")
        
        with ProcessPoolExecutor(max_workers=len(active_regions)) as executor:
            futures = [
                executor.submit(run_regional_worker, name, TARGET_SYSTEM, sites, START_DATE, END_DATE)
                for name, sites in active_regions.items()
            ]
            
            for future in futures:
                print(future.result())

        global_end = time.perf_counter()
        total_duration = (global_end - global_start) / 60
        print(f"\n🏆 ALL PROCESS LANES FINISHED SUCCESSFULLY")
        print(f"⏱️ Total Parallel Run Processing Time: {total_duration:.2f} minutes")
        
    except Exception as e:
        print(f"\n❌ ORCHESTRATOR CRITICAL FAILURE: {e}")