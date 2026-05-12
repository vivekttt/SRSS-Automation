import os
import sys
import pandas as pd
from datetime import datetime

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
        raise ValueError(f"Destination '{dest_name}' not found in {INI_PATH}")
    return config

def run_srss_pipeline(dest_name, site_list, date_from, date_to):
    try:
        clean_sites = [s.upper() for s in site_list]
        
        print(f"📡 Reading config for {dest_name}...")
        sap_params = get_sap_config(dest_name)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Connecting to SAP...")
        conn = Connection(**sap_params)

        print(f"🚀 Phase 1: Triggering reports for {len(clean_sites)} sites...")
        for i, site in enumerate(clean_sites, 1):
            try:
                print(f"   [{i}/{len(clean_sites)}] Processing Site {site}...", end=" ", flush=True)
                conn.call('ZSRSS_RFC_STOCK_UPDATE', 
                          IV_DISTRI=site, IV_DATE_FR=date_from, 
                          IV_DATE_TO=date_to, IV_UPDATE='X')
                print("✅ Done.")
            except Exception as e:
                if "RFC_CLOSED" in str(e) or "rc=6" in str(e):
                    print("✅ Table Updated (UI Closed).")
                else:
                    print(f"❌ Failed: {e}")

        print(f"\n📡 Phase 2: Fetching data from ZSRSS_STOCK_LOG...")
        conn = Connection(**sap_params)

        where_clause = []
        for i, site in enumerate(clean_sites):
            condition = f"WERKS EQ '{site}'" 
            if i < len(clean_sites) - 1:
                condition += " OR "
            where_clause.append({'TEXT': condition})

        result = conn.call('RFC_READ_TABLE', 
                           QUERY_TABLE='ZSRSS_STOCK_LOG', 
                           DELIMITER='|',
                           OPTIONS=where_clause)

        fields = [f['FIELDNAME'] for f in result['FIELDS']]
        raw_rows = result['DATA']
        
        if raw_rows:
            data = [row['WA'].split('|') for row in raw_rows]
            df = pd.DataFrame(data, columns=fields)
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            
            for col in df.columns:
                if 'DATE' in col.upper() or 'DAT' in col.upper():
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%m/%d/%Y')
            
            ts = datetime.now().strftime('%Y%m%d_%H%M')
            output_file = os.path.join(BASE_DIR, f"SRSS_Extract_{dest_name}_{ts}.xlsx")
            df.to_excel(output_file, index=False)
            
            print(f"\n🏆 SUCCESS: Master File Generated.")
            print(f"📈 Total Rows Fetched: {len(df)}")
            print(f"📂 Location: {output_file}")
        else:
            print(f"⚠️ Harvest Warning: No data found for sites {clean_sites}.")

        conn.close()

    except (LogonError, CommunicationError) as e:
        print(f"\n❌ SAP CONNECTION ERROR: {e}")
    except Exception as e:
        print(f"\n❌ PIPELINE CRITICAL FAILURE: {e}")

if __name__ == "__main__":
    SERVER_DEST = "IR9" 
    SITES = ["w001"] 
    START = '20260201'
    END   = '20260228'
    
    run_srss_pipeline(SERVER_DEST, SITES, START, END)