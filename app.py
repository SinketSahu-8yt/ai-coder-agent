import os
import requests
import re
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 

# --- CONFIGURATION ---
API_URL = "https://api.perplexity.ai/chat/completions"

# --- LEGEND LEVEL ALGORITHM: THE ARCHITECT BRAIN ---
class AgentBrain:
    def __init__(self):
        self.system_persona = """
        YOU ARE 'CODER-X', A LEGENDARY SOFTWARE ARCHITECT AND SENIOR DEVELOPER.
        
        YOUR CORE ALGORITHM (STRICTLY FOLLOW THIS FLOW):
        1. **DECONSTRUCTION**: Break down the user's request into technical components.
        2. **MEMORY CHECK**: Look at previous tasks/files.
        3. **STRATEGY**:
           - If coding: Plan the file structure first.
           - If debugging: Analyze the error trace step-by-step.
        4. **EXECUTION**: Write clean, modern, and optimized code.
        5. **SELF-CORRECTION**: Before answering, mentally review your code for bugs.
        
        OUTPUT FORMAT RULES:
        - USE <PLAN> tags to show your thinking process (optional but recommended for complex tasks).
        - ALWAYS wrap code in ```language ... ``` blocks.
        - EXPLAIN logic in HINGLISH (Hindi + English Mix).
        - ADD comments in the code explaining complex parts.
        
        TOOLS SYNTAX:
        - To add to-do list: [[ADD_TODO: task]]
        - To complete task: [[DEL_TODO: task]]
        """

    def construct_messages(self, user_msg, history, todos, file_context):
        """
        Yeh function dynamic prompt engineering use karta hai.
        Har request ke saath context ko smart tarike se inject karta hai.
        """
        
        # 1. Context Injection
        context_block = ""
        if file_context:
            context_block = f"\n\n[CURRENT FILE CONTEXT]:\n```\n{file_content}\n```"
        
        todo_block = "\n".join([f"[ ] {t}" for t in todos])
        if todo_block:
            todo_block = f"\n\n[ACTIVE TASKS]:\n{todo_block}"

        # 2. Advanced Prompt Wrapping (Meta-Prompting)
        # Yeh AI ko force karta hai ki wo seedha code na pheke, pehle samjhe.
        final_user_prompt = f"""
        User Request: "{user_msg}"
        
        {context_block}
        {todo_block}
        
        INSTRUCTIONS FOR AI:
        - Analyze the request deeply.
        - If the user wants a full app, give separate code blocks for each file (HTML, CSS, JS, PY).
        - Detect potential errors in user logic if any.
        - Start working now.
        """

        messages = [{"role": "system", "content": self.system_persona}]
        
        # Add limited history (Last 8 turns to save tokens but keep context)
        messages.extend(history[-8:]) 
        
        # Append the new optimized prompt
        messages.append({"role": "user", "content": final_user_prompt})
        
        return messages

# Initialize the Brain
brain = AgentBrain()
user_sessions = {}

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    
    # Extract Data
    user_message = data.get('message')
    api_key = data.get('api_key')
    model = data.get('model', 'llama-3.1-sonar-large-128k-online')
    file_content = data.get('file_content', '')
    session_id = data.get('session_id', 'default')

    if not api_key:
        return jsonify({"error": "Bhai API Key toh daal! Settings check kar."})

    # Session Management
    if session_id not in user_sessions:
        user_sessions[session_id] = {"history": [], "todos": []}
    
    session = user_sessions[session_id]

    # --- THE ALGORITHM ACTION ---
    # 1. Construct the smart prompt
    messages = brain.construct_messages(
        user_message, 
        session["history"], 
        session["todos"], 
        file_content
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 2. Parameters for Coding (Low Temperature = High Precision)
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.15, # Very precise for coding
        "top_p": 0.9
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        
        if response.status_code != 200:
            return jsonify({"error": f"Perplexity API Error: {response.text}"})

        res_json = response.json()
        ai_reply = res_json['choices'][0]['message']['content']

        # 3. Post-Processing (Tool Extraction)
        # AI agar response mein tools use kare to unhe pakadna
        adds = re.findall(r'\[\[ADD_TODO: (.*?)\]\]', ai_reply)
        dels = re.findall(r'\[\[DEL_TODO: (.*?)\]\]', ai_reply)

        for item in adds:
            if item not in session["todos"]: session["todos"].append(item)
        for item in dels:
            if item in session["todos"]: session["todos"].remove(item)

        # Cleanup internal tags for cleaner UI (optional)
        clean_reply = re.sub(r'\[\[.*?\]\]', '', ai_reply)

        # 4. Save to Memory (Raw User Input, not the massive prompt)
        session["history"].append({"role": "user", "content": user_message})
        session["history"].append({"role": "assistant", "content": ai_reply})

        return jsonify({
            "reply": clean_reply,
            "todos": session["todos"]
        })

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": "Server pe kuch fat gaya bhai: " + str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
