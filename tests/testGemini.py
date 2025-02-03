import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def test_gemini_api():
    """Test Gemini API directly with curl-equivalent request"""
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in environment")
        return
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts":[{
                "text": "Write a story about a magic backpack."
            }]
        }]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print("Success! Response:")
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response text: {e.response.text}")

def test_gemini_cleanup():
    test_cases = [
        {
            "input": "Revised News Script Section: Here's a revised version...",
            "expected": ""
        },
        {
            "input": "**[Meta-comment]** This section needs... Actual narration text.",
            "expected": "Actual narration text."
        }
    ]
    
    for case in test_cases:
        output = generator._gemini_tts_cleanup(case["input"])
        assert case["expected"] in output, f"Failed: {case['input']}"
        assert "revised" not in output.lower()

if __name__ == "__main__":
    test_gemini_api()