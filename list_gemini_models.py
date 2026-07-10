import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure API key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ GOOGLE_API_KEY not found in .env")
    exit(1)

genai.configure(api_key=api_key)

# List available models
print("Available Google Generative AI models:")
print("-" * 60)

for model in genai.list_models():
    if hasattr(model, 'name') and hasattr(model, 'supported_generation_methods'):
        # Extract the model name from the path (e.g., 'models/gemini-pro' -> 'gemini-pro')
        model_name = model.name.replace("models/", "")
        methods = model.supported_generation_methods
        print(f"{model_name}")
        print(f"  Methods: {', '.join(methods) if isinstance(methods, list) else methods}")
        print()
