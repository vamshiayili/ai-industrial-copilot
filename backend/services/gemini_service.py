import os
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from backend.config import GEMINI_API_KEY, DEFAULT_TEXT_MODEL, DEFAULT_VISION_MODEL, EMBEDDING_MODEL

# Initialize Gemini Client if API key is provided
client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("Gemini client initialized successfully.")
    except Exception as e:
        print(f"Error initializing Gemini client: {e}")
else:
    print("Warning: GEMINI_API_KEY is not set. Running in mock-fallback mode.")

def get_embedding(text: str) -> List[float]:
    """Generates text embedding using text-embedding-004."""
    if not text.strip():
        return [0.0] * 768

    if client:
        try:
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text
            )
            # The API returns a list of embeddings. Extract values from the first one.
            if response.embeddings:
                return response.embeddings[0].values
        except Exception as e:
            print(f"Gemini Embedding API Error: {e}. Falling back to pseudo-embeddings.")
            
    # Deterministic fallback pseudo-embeddings for offline/no-key usage
    # Generates a 768-dimension array based on the text hash
    hasher = hashlib.sha256(text.encode('utf-8'))
    seed = int(hasher.hexdigest(), 16) % (2**32 - 1)
    rng = np.random.default_rng(seed)
    mock_vector = rng.normal(0.0, 1.0, 768).tolist()
    # Normalize vector to unit length
    norm = np.linalg.norm(mock_vector)
    if norm > 0:
        mock_vector = [x / norm for x in mock_vector]
    return mock_vector

def generate_text(prompt: str, system_instruction: Optional[str] = None, model: Optional[str] = None) -> str:
    """Generates text response using gemini-1.5-pro or gemini-1.5-flash."""
    model_name = model or DEFAULT_TEXT_MODEL
    
    if client:
        try:
            config = None
            if system_instruction:
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction
                )
            
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            print(f"Gemini Generation API Error ({model_name}): {e}. Falling back to mock response.")
            
    # Mock fallback response for offline testing
    return f"[MOCK RUN - API KEY MISSING OR FAILED]\n\nBased on your query: '{prompt[:60]}...', here is a simulated engineering response regarding standard operating parameters. Ensure safety guidelines and LOTO protocols are fully deployed prior to maintenance."

def analyze_drawing(image_bytes: bytes, mime_type: str, prompt: str) -> str:
    """Performs visual analysis on drawings/P&IDs using gemini-1.5-flash."""
    if client:
        try:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            response = client.models.generate_content(
                model=DEFAULT_VISION_MODEL,
                contents=[image_part, prompt]
            )
            return response.text
        except Exception as e:
            print(f"Gemini Vision API Error: {e}. Falling back to mock analysis.")
            
    return (
        "[MOCK VISION RUN]\n\nVisual analysis of the drawing has detected: \n"
        "1. A centrifugal pump marked 'Pump-02' (lower-middle section).\n"
        "2. A safety pressure relief valve downstream on Line-024 (safety orange highlights suggest this holds 15 bar max).\n"
        "3. Flow direction indicator arrows point from left to right toward the storage vessel (Tank-10).\n"
        "4. A bypass valve (V-102) is shown in the open position parallel to the primary strainer loop."
    )
