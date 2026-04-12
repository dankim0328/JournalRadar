import os
import google.generativeai as genai
from google.api_core import exceptions

def check_gemini_status():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable not found.")
        return

    genai.configure(api_key=api_key)
    
    # Try using a lightweight model to test the connection and quota
    # Note: User's script used 'gemini-2.5-pro', but for testing let's try a standard one
    # or the one they are using.
    model_name = "gemini-1.5-flash" 
    print(f"🔄 Testing Gemini API status with model: {model_name}...")
    
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello, this is a quota check. Please respond with 'OK'.")
        print(f"✅ API connection successful! Response: {response.text.strip()}")
        print("\n[Status] Your API key is active and has remaining quota for this model.")
        
    except exceptions.ResourceExhausted as e:
        print(f"⚠️ Quota Exceeded (429): {e}")
        print("\n[Status] You have exhausted your Gemini API quota. If you are on the Free Tier, it will usually reset:")
        print("- Per Minute (RPM): Wait 1 minute.")
        print("- Per Day (RPD): Wait until 00:00 UTC (or your daily reset time).")
        print("\nCheck details at: https://aistudio.google.com/app/plan")
        
    except exceptions.InvalidArgument as e:
        print(f"❌ Invalid API Key or Model Name: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    check_gemini_status()
