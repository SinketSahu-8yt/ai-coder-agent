import os
import requests
import re
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Allow all origins for mobile/web compatibility
CORS(app, resources={r"/*": {"origins": "*"}})

API_URL = "https://api.perplexity.ai/chat/completions"

# --- IN-MEMORY DATABASE (Session based) ---
# Format: {'session_id': ['Task 1', 'Task 2']}
user_sessions = {}

SYSTEM_PROMPT = """
YOU ARE A LEGENDARY AI ARCHITECT (AGENT CODING MODE).

YOUR GOAL: Plan, Code, and Track progress.

**CRITICAL RULES FOR TO-DO MANAGEMENT:**
1. You have access to a To-Do list.
2. To ADD a task, strictly use this format: [[ADD_TODO: Install Flask]]
3. To MARK DONE/REMOVE a task, use: [[DEL_TODO: Install Flask]]
4. When starting a big project, first ADD tasks for the plan.
5. After coding a part, DEL the completed task.

**CODING RULES:**
- Write production-ready code.
- Explain briefly in Hinglish.
- Use Markdown for code blocks.
"""

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        api_key = data.get('api_key')
        user_message = data.get('message')
        model = data.get('model', 'sonar-pro')
        file_content = data.get('file_content', '')
        session_id = data.get('session_id') # Frontend se aayega unique ID

        if not api_key:
            return jsonify({"error": "Guru, API Key toh daalo!"}), 400

        # 1. Session Management
        if not session_id:
            session_id = "default"
        
        if session_id not in user_sessions:
            user_sessions[session_id] = []
        
        current_todos = user_sessions[session_id]

        # 2. Context Injection (Inject To-Do List into AI's brain)
        todo_context = "NO ACTIVE TASKS."
        if current_todos:
            todo_context = "CURRENT TO-DO LIST:\n" + "\n".join([f"- {t}" for t in current_todos])

        final_prompt = f"""
        {todo_context}

        USER REQUEST: "{user_message}"
        
        CONTEXT FILE: {file_content[:2000] if file_content else "None"}
        """

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": final_prompt}
        ]

        # 3. Call Perplexity
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": 0.1}

        response = requests.post(API_URL, json=payload, headers=headers)
        if response.status_code != 200:
            return jsonify({"error": f"API Error: {response.text}"})

        ai_reply = response.json()['choices'][0]['message']['content']

        # 4. PARSING LOGIC (The Magic)
        # Extract ADD commands
        adds = re.findall(r'\[\[ADD_TODO: (.*?)\]\]', ai_reply)
        for item in adds:
            if item not in current_todos:
                current_todos.append(item)
        
        # Extract DEL commands
        dels = re.findall(r'\[\[DEL_TODO: (.*?)\]\]', ai_reply)
        for item in dels:
            # Flexible matching (case insensitive strip)
            clean_dels = [t for t in current_todos if item.lower() in t.lower()]
            for t in clean_dels:
                if t in current_todos:
                    current_todos.remove(t)

        # Update Session
        user_sessions[session_id] = current_todos

        # Cleanup output for user (Hidden tags remove kar do)
        display_reply = re.sub(r'\[\[.*?\]\]', '', ai_reply)

        return jsonify({
            "reply": display_reply,
            "todos": current_todos # Updated list bhej rahe hain frontend ko
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
