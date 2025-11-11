import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # .. -- go up one folder, path.abspath makes it an interpretable file path
sys.path.append(project_root)

from scripts.Azure_Database import database

sleep_raw = database()
sleep_df_raw = sleep_raw.query("SELECT * FROM sleep_raw order by dateOfSleep desc")
print(sleep_df_raw.head())
