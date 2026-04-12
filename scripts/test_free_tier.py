import os
import google.generativeai as genai

api_key = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=api_key)

print("Testing gemini-1.5-flash...")
try:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Hello")
    print(f"Success! Response: {response.text}")
except Exception as e:
    print(f"Failed: {e}")

print("\nTesting gemini-1.5-pro...")
try:
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content("Hello")
    print(f"Success! Response: {response.text}")
except Exception as e:
    print(f"Failed: {e}")
