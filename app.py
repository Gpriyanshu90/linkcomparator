from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import json
import re
import os
from dotenv import load_dotenv


load_dotenv


app = Flask(__name__)
CORS(app, resources={r"/compare": {"origins": "*"}})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compare', methods=['POST'])
def compare_profiles():
    try:
        data = request.json
        # api_key = data.get('api_key')
        api_key = os.getenv("Gemini_api_key")
        profile1_url = data.get('profile1_url', '')
        profile1_text = data.get('profile1_text', '')
        profile2_url = data.get('profile2_url', '')
        profile2_text = data.get('profile2_text', '')
        
        print(api_key)

        # Validation
        if not api_key:
            return jsonify({'error': 'API key is required'}), 400

        if (not profile1_url and not profile1_text) or (not profile2_url and not profile2_text):
            return jsonify({'error': 'Both profiles information is required'}), 400

        profile1_info = f"LinkedIn URL: {profile1_url}\n{profile1_text}" if profile1_url else profile1_text
        profile2_info = f"LinkedIn URL: {profile2_url}\n{profile2_text}" if profile2_url else profile2_text

        prompt = f"""
You are a professional LinkedIn profile analyst.

PROFILE 1:
{profile1_info}

PROFILE 2:
{profile2_info}

Return only JSON:
{{
  "overview": {{
    "profile1": "...",
    "profile2": "..."
  }},
  "similarities": ["..."],
  "differences": ["..."],
  "skills": {{
    "common": ["..."],
    "profile1Unique": ["..."],
    "profile2Unique": ["..."]
  }},
  "careerTrajectory": {{
    "profile1": "...",
    "profile2": "..."
  }},
  "strengths": {{
    "profile1": ["..."],
    "profile2": ["..."]
  }},
  "summary": "..."
}}
"""

        # FIXED GEMINI ENDPOINT
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048
            }
        }

        headers = {'Content-Type': 'application/json'}
        response = requests.post(gemini_url, headers=headers, json=payload, timeout=30)

        if response.status_code != 200:
            return jsonify({'error': f"Gemini API Error: {response.text}"}), 400

        result = response.json()

        if "candidates" not in result:
            return jsonify({"error": "No output returned by Gemini"}), 500

        ai_output = result['candidates'][0]['content']['parts'][0]['text']

        ai_output = ai_output.strip()
        ai_output = re.sub(r'^```json', '', ai_output)
        ai_output = re.sub(r'^```', '', ai_output)
        ai_output = re.sub(r'```$', '', ai_output)

        match = re.search(r'\{[\s\S]*\}', ai_output)
        if not match:
            return jsonify({"error": "Invalid JSON from AI"}), 500

        report = json.loads(match.group(0))

        return jsonify({'success': True, 'report': report})

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=5000)
