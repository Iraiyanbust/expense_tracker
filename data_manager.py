import json
import os
from datetime import datetime

DATA_FILE = "data.json"
SETTINGS_FILE = "settings.json"

def _load_json(filepath, default_value):
    if not os.path.exists(filepath):
        return default_value
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default_value

def _save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def get_expenses():
    """Returns a list of expense dictionaries."""
    return _load_json(DATA_FILE, [])

def add_expense(amount, category, timestamp=None):
    """Adds a new expense to the data file."""
    expenses = get_expenses()
    if not timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    expenses.append({
        "amount": amount,
        "category": category,
        "time": timestamp
    })
    _save_json(DATA_FILE, expenses)

def get_settings():
    """Returns the user settings dictionary for budget and salary."""
    return _load_json(SETTINGS_FILE, {"budget": 0.0, "salary": 0.0})

def save_settings(budget, salary):
    """Saves the user budget and salary."""
    settings = {"budget": budget, "salary": salary}
    _save_json(SETTINGS_FILE, settings)

CHAT_FILE = "chat_sessions.json"

def get_chat_sessions():
    return _load_json(CHAT_FILE, [])

def save_chat_session(session_id, messages):
    sessions = get_chat_sessions()
    
    # Update if exists, otherwise append
    found = False
    for session in sessions:
        if session["session_id"] == session_id:
            session["messages"] = messages
            found = True
            break
            
    if not found:
        sessions.append({
            "session_id": session_id,
            "messages": messages
        })
        
    _save_json(CHAT_FILE, sessions)
