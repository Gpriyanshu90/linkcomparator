from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import json
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend-backend communication

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compare', methods=['POST'])
def compare_profiles():
    try:
        data = request.json
        api_key = data.get('api_key')
        profile1_url = data.get('profile1_url', '')
        profile1_text = data.get('profile1_text', '')
        profile2_url = data.get('profile2_url', '')
        profile2_text = data.get('profile2_text', '')
        
        # Validation
        if not api_key:
            return jsonify({'error': 'API key is required'}), 400
            
        if (not profile1_url and not profile1_text) or (not profile2_url and not profile2_text):
            return jsonify({'error': 'Both profiles information is required'}), 400
        
        # Prepare profile information
        profile1_info = f"LinkedIn URL: {profile1_url}\n{profile1_text}" if profile1_url else profile1_text
        profile2_info = f"LinkedIn URL: {profile2_url}\n{profile2_text}" if profile2_url else profile2_text
        
        # Enhanced Gemini prompt
        prompt = f"""You are a professional LinkedIn profile analyst. Analyze and compare these two LinkedIn profiles in detail.

PROFILE 1:
{profile1_info}

PROFILE 2:
{profile2_info}

Provide a comprehensive comparison. Return your analysis as a JSON object with this EXACT structure:

{{
  "overview": {{
    "profile1": "Brief 2-3 sentence overview of Profile 1's professional identity",
    "profile2": "Brief 2-3 sentence overview of Profile 2's professional identity"
  }},
  "similarities": [
    "List 3-5 key similarities between the profiles",
    "Include industry overlap, common skills, similar career paths, etc."
  ],
  "differences": [
    "List 3-5 key differences between the profiles",
    "Include seniority gaps, different specializations, industry differences, etc."
  ],
  "skills": {{
    "common": ["skill1", "skill2", "skill3"],
    "profile1Unique": ["unique_skill1", "unique_skill2"],
    "profile2Unique": ["unique_skill1", "unique_skill2"]
  }},
  "careerTrajectory": {{
    "profile1": "Describe the career progression and growth pattern",
    "profile2": "Describe the career progression and growth pattern"
  }},
  "strengths": {{
    "profile1": ["strength1", "strength2", "strength3"],
    "profile2": ["strength1", "strength2", "strength3"]
  }},
  "summary": "A comprehensive 3-4 sentence summary comparing both profiles, highlighting who might be better suited for what types of roles or situations."
}}

CRITICAL: Return ONLY the JSON object. No markdown code blocks, no extra text, just pure JSON."""
        
        # Updated Gemini API endpoint with correct model name
        # Use gemini-pro or gemini-1.5-pro for better results
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"

        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048,
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        
        print("Sending request to Gemini API...")
        response = requests.post(gemini_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get('error', {}).get('message', f'API returned status {response.status_code}')
            return jsonify({'error': f'Gemini API Error: {error_msg}'}), 400
        
        result = response.json()
        
        # Handle quota or other API errors
        if 'error' in result:
            return jsonify({'error': result['error']['message']}), 400
        
        # Extract response text
        if 'candidates' not in result or not result['candidates']:
            return jsonify({'error': 'No response from AI model'}), 500
            
        ai_output = result['candidates'][0]['content']['parts'][0]['text']
        print(f"AI Response: {ai_output[:200]}...")
        
        # Clean up the response - remove markdown code blocks if present
        ai_output = ai_output.strip()
        ai_output = re.sub(r'^```json\s*', '', ai_output)
        ai_output = re.sub(r'^```\s*', '', ai_output)
        ai_output = re.sub(r'\s*```$', '', ai_output)
        
        # Extract JSON
        match = re.search(r'\{[\s\S]*\}', ai_output)
        if not match:
            return jsonify({'error': 'Could not parse AI response as JSON. Please try again.'}), 500
        
        try:
            report = json.loads(match.group(0))
        except json.JSONDecodeError as e:
            return jsonify({'error': f'Invalid JSON format from AI: {str(e)}'}), 500
        
        # Validate report structure
        required_keys = ['overview', 'similarities', 'differences', 'skills', 'careerTrajectory', 'strengths', 'summary']
        for key in required_keys:
            if key not in report:
                report[key] = {} if key in ['overview', 'skills', 'careerTrajectory', 'strengths'] else []
        
        return jsonify({'success': True, 'report': report})

    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout. Please try again.'}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Network error: {str(e)}'}), 500
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='127.0.0.1')