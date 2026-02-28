from langgraph.checkpoint.sqlite import SqliteSaver
from src.graph import builder

with SqliteSaver.from_conn_string("audit_history.sqlite") as memory:
    graph = builder.compile(checkpointer=memory)
    
    # get the latest state from the database
    config = {"configurable": {"thread_id": "audit_run_1"}} # wait, I changed it to uuid, we can't easily get the last one unless we query sqlite
    
import sqlite3
import json

conn = sqlite3.connect("audit_history.sqlite")
cursor = conn.cursor()
cursor.execute("SELECT checkpoint FROM checkpoints ORDER BY updated_at DESC LIMIT 1")
row = cursor.fetchone()

# Parse pickle or JSON depending on what langgraph saves
import pickle
if row:
    try:
        cp = pickle.loads(row[0])
        # It's an internal representation
        print(cp["channel_values"]["final_report"].criteria[0].final_score)
        print("Success extracting via pickle")
    except Exception as e:
        print("Could not read checkpoint", e)

