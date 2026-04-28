import json
import os
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")

if API_KEY:
    client = Groq(api_key=API_KEY)
else:
    client = None

MODEL_FAST = "llama-3.1-8b-instant"
MODEL_REASONING = "openai/gpt-oss-120b"
MODEL_VISION = "meta-llama/llama-4-scout-17b-16e-instruct"

def parse_expense_input(user_input):
    """
    Parses natural language input to extract amount and category.
    """
    if not client:
        return {"error": "GROQ_API_KEY not configured in .env"}

    prompt = f"""
    You are an intelligent expense parser. 
    Extract the expense amount and category from the following text.
    Text: "{user_input}"
    
    Return pure JSON with the exact following keys:
    {{
        "amount": <number>,
        "category": "<string>"
    }}
    Do not wrap in markdown tags like ```json. Just return the raw JSON object.
    If category is ambiguous, pick a common one (e.g. Food, Transport, Utilities, Entertainment, Shopping).
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=MODEL_FAST,
        )
        response_text = chat_completion.choices[0].message.content
        result = json.loads(response_text.strip())
        
        # Format time on our end
        result["time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return result
    except Exception as e:
        return {"error": str(e)}

def parse_receipt_image(base64_image):
    """
    Parses a base64 encoded image to extract amount and category via a vision model.
    """
    if not client:
        return {"error": "GROQ_API_KEY not configured in .env"}

    prompt = """
    You are an intelligent expense parser. 
    Analyze the uploaded receipt/expense image and extract the amount and the category.
    
    Return pure JSON with the exact following keys:
    {
        "amount": <number>,
        "category": "<string>"
    }
    Do not wrap in markdown tags like ```json. Just return the raw JSON object.
    If the category is ambiguous, pick a common one (e.g. Food, Transport, Utilities, Entertainment, Shopping).
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            model=MODEL_VISION,
        )
        response_text = chat_completion.choices[0].message.content
        result = json.loads(response_text.strip())
        
        # Format time on our end
        result["time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return result
    except Exception as e:
        return {"error": str(e)}

def parse_bulk_expenses_from_text(document_text):
    """
    Parses a large block of text (like a CSV or PDF ledger) to extract an array of expenses.
    """
    if not client:
        return {"error": "GROQ_API_KEY not configured in .env"}

    prompt = f"""
    You are an intelligent expense parser. 
    Analyze the following raw text extracted from a financial document (like a PDF statement or Excel sheet).
    Identify all distinct expenses and extract their amounts and categories.

    Raw Document Text:
    {document_text}

    Return pure JSON representing a list of objects with the exact following keys:
    [
        {{
            "amount": <number>,
            "category": "<string>"
        }},
        ...
    ]
    Do not wrap in markdown tags like ```json. Just return the raw JSON array.
    If a category is ambiguous, pick a common one (e.g. Food, Transport, Utilities, Entertainment, Shopping).
    IGNORE random deposits or incomes. Only extract expenses/withdrawals.
    IF no expenses are found, return an empty array [].
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=MODEL_REASONING,
        )
        response_text = chat_completion.choices[0].message.content
        result_array = json.loads(response_text.strip())
        
        # Validate and format time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        for item in result_array:
            item["time"] = current_time
            
        return result_array
    except Exception as e:
        return {"error": str(e)}

def analyze_spending(expenses):
    """
    Analyzes historical spending and generates insights.
    """
    if not client:
        return "GROQ_API_KEY not configured in .env"
        
    if not expenses:
        return "No expenses to analyze yet."

    data_str = json.dumps(expenses, indent=2)
    prompt = f"""
    You are a financial advisor AI.
    Analyze the user's expenses.
    All currency values MUST be in Indian Rupees (₹), never use $.

    Data:
    {data_str}
    
    Give:
    1. Spending breakdown (category-wise)
    2. Key insights (changes, unusual behavior)
    3. Behavioral patterns
    4. Warnings (if overspending)
    5. Actionable advice
    
    Be specific, concise, and realistic. Use structured markdown formatting with bullet points.
    Do not use generic fluff. Speak professionally like a fintech advisor.
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_REASONING,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error connecting to AI: {str(e)}"

def advisor_mode(chat_history, expenses, budget, alerts_str):
    """
    Answers specific user questions contextually with chat memory and alerts.
    """
    if not client:
        return "GROQ_API_KEY not configured in .env"
        
    data_str = json.dumps(expenses, indent=2)
    
    # Extract previous history and the current user input
    history_str = ""
    for msg in chat_history[:-1]:
        history_str += f"{msg['role'].capitalize()}: {msg['content']}\n"
        
    user_input = chat_history[-1]["content"] if chat_history else ""

    prompt = f"""
    You are a financial advisor AI.
    All currency values MUST be in Indian Rupees (₹), never use $.
    
    If the user asks anything unrelated to personal finance, expenses, budgeting, or savings:
    - Politely refuse.
    - Say you can only assist with financial queries.
    
    User financial data:
    {data_str}
    
    User budget:
    {budget}
    
    Active alerts:
    {alerts_str}
    
    Conversation history:
    {history_str}
    
    User query:
    {user_input}
    
    Tasks:
    1. If the user asks about summarizing alerts, warnings, or fixing, explain the Active alerts clearly, what they mean, and provide actionable remedies prioritized by urgency.
    2. If the user asks for monthly expenses or month-wise breakdown, group the expenses by month using their 'time' field and summarize the spending month-wise.
    3. Otherwise, give a clear, concise, structured, and reasoned answer to their specific query.
    4. Always keep it practical and avoid generic replies.
    """
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_REASONING,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error connecting to AI: {str(e)}"
