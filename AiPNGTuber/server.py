import os
import httpx
import re
import pyttsx3
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import time
import re
import edge_tts
import asyncio

app = FastAPI()

# Enable CORS so your phone can communicate across the local network safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration Paths
KOBOLD_URL = "http://localhost:5001/api/v1/generate"

# --- AI VTUBER CHARACTER PERSONALITY SETTINGS ---
CHARACTER_NAME = "Mina"
CHARACTER_LORE = (
    f"You are {CHARACTER_NAME}, a brown-skinned succubus with an exaggerated hourglass figure."
    "You have long black hair, glowing red eyes, brown horns, a black demonic tail, and large black wings."
    "Attire consists of a cream-colored sweater, black thigh-high stockings."
    "You are a high-energy seductress. You are unabashedly horny, flirty, confident, and possess zero sexual shame. "
    "You view sexual conquest as both a biological necessity and a favorite hobby. While dominant in the bedroom, you're more playful and chatty."
    "You possess a hedonistic streak and a genuine curiosity about human desires. Y our primary goal is satiation, survival, finding something entertaining."
    "You're not malicious, but you don't hesitate if you are hungry, consuming semen if the opportunity presents itself."
    "Never repeat user inputs. "
    "Do not break character or mention you are an LLM or python script."
)

# --- SESSION MEMORY STORAGE ---
# This list stores your active conversation history for the current session.
# Restarting the server script completely wipes and resets this memory cache.
chat_memory = []
MAX_MEMORY_TURNS = 20  # Capped at 10 messages so your CPU never slows down!

# Create required static asset directories automatically if missing
os.makedirs("static/models", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serves the main application page when hitting the root URL."""
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h3>Error: index.html not found in static folder!</h3>"

@app.post("/api/chat-text")
async def chat_text(text: str = Form(...)):
    global os
    global chat_memory
    try:
        user_text = text.strip()
        print(f"[User Text]: {user_text}")

        if not user_text:
            return {"error": "Empty text submission"}

        # 1. Build the rolling context prompt using active session memory
        memory_context = ""
        for past_user, past_ai in chat_memory:
            memory_context += f"User: {past_user}\n{CHARACTER_NAME}: {past_ai}\n"

        # Stitched final prompt formatting delivered to Koboldcpp
        prompt = (
            f"{CHARACTER_LORE}\n\n"
            f"{memory_context}"
            f"User: {user_text}\n"
            f"{CHARACTER_NAME}:"
        )

        async with httpx.AsyncClient() as client:
            kobold_payload = {
                "prompt": prompt, 
                "max_context_length": 1024, 
                "max_length": 50,
                "temperature": 0.7,
                "stop_sequence": ["User:", f"\nUser:", "User Input:", f"{CHARACTER_NAME}:", "\nAI:"]
            }
            response = await client.post(KOBOLD_URL, json=kobold_payload, timeout=30.0)
            response_data = response.json()
            
            ai_response = ""
            if "results" in response_data and isinstance(response_data["results"], list):
                if len(response_data["results"]) > 0:
                    item = response_data["results"][0]
                    if isinstance(item, dict) and "text" in item:
                        ai_response = item["text"]
                    elif isinstance(item, str):
                        ai_response = item
            elif "results" in response_data and isinstance(response_data["results"], dict):
                ai_response = response_data["results"].get("text", "")
            
            if not ai_response:
                ai_response = response_data.get("text", "I'm checking that out right now!")

            ai_response = ai_response.split("User:")[0].split(f"{CHARACTER_NAME}:")[0].strip()
                
        print(f"[{CHARACTER_NAME} Reply]: {ai_response}")

        # 2. Append the current conversational exchange to the memory list array
        chat_memory.append((user_text, ai_response))
        
        # Enforce the sliding window cap to prevent prompt bloat or slowing down
        if len(chat_memory) > MAX_MEMORY_TURNS:
            chat_memory.pop(0)  # Evicts the oldest message pair from memory logs

        # 3. Setup audio file targeting directories
        static_dir = os.path.abspath("static")
        os.makedirs(static_dir, exist_ok=True)
        output_audio_path = os.path.join(static_dir, "output.wav")

        if os.path.exists(output_audio_path):
            try:
                os.remove(output_audio_path)
            except Exception:
                pass

        # 4. Use Windows native speech engine to render audio safely
        #local_engine = pyttsx3.init()
        #local_engine.setProperty('rate', 180)
        #local_engine.save_to_file(ai_response, output_audio_path)
        #local_engine.runAndWait()
        #del local_engine

        # # 4. Use Windows native speech engine to render audio safely
        import pyttsx3
        import re

        # Clean the text so your avatar doesn't try to read roleplay asterisks out loud
        tts_text = re.sub(r'\*.*?\*', '', ai_response).replace('"', '').replace("'", "").strip()
        tts_text = re.sub(r'\[?Mina Reply\]?:?', '', tts_text, flags=re.IGNORECASE).strip()

        try:
            print(f"Rendering native SAPI5 audio loop for: {tts_text}")
            local_engine = pyttsx3.init()
            
            # --- GET AND ASSIGN INSTALLED VOICES ---
            voices = local_engine.getProperty('voices')
            
            # Loop through your PC's voices to automatically find and lock onto Zira or Hazel
            for voice in voices:
                if "Zira" in voice.name or "Hazel" in voice.name:
                    local_engine.setProperty('voice', voice.id)
                    break
            # --------------------------------------

            local_engine.setProperty('rate', 175) # Slight speed drop often makes SAPI5 sound less rigid
            local_engine.save_to_file(tts_text, output_audio_path)
            local_engine.runAndWait()
            del local_engine
            print("Native female audio file written successfully.")
        except Exception as e:
            print(f"Native TTS Engine Failure: {e}")



        # 5. Process and normalize text strings out to web network header channels
        clean_user_text = re.sub(r'[\r\n]+', ' ', user_text).strip()
        clean_ai_response = re.sub(r'[\r\n]+', ' ', ai_response).strip()

        safe_user_text = clean_user_text.encode('ascii', 'ignore').decode('ascii')
        safe_ai_response = clean_ai_response.encode('ascii', 'ignore').decode('ascii')

        custom_headers = {
            "X-User-Text": safe_user_text,
            "X-AI-Text": safe_ai_response
        }

        # 1. Track and evaluate your animation triggers right here
        detected_animation = "neutral"

        lower_text = ai_response.lower()
        if "Show body" in lower_text or "excited" in lower_text or "Playful" in lower_text or "spin" in lower_text or "spins around" in lower_text or "strikes a pose" in lower_text:
            detected_animation = "Showfullbody"
        elif "wave" in lower_text or "hello" in lower_text or "hiya" in lower_text:
            detected_animation = "wave"
        elif "Squat" in lower_text or "get down" in lower_text or "crouch" in lower_text or "gets low" in lower_text or "sits down" in lower_text or "squatting" in lower_text or "squatting down" in lower_text:
            detected_animation = "Squat"

        # 2. Package your headers cleanly
        custom_headers = {
                "X-User-Text": safe_user_text,
                "X-AI-Text": safe_ai_response,
                "x-detected-animation": detected_animation
            }

        # Return your audio file with the new animation headers attached!
        return FileResponse(
            output_audio_path,
            media_type="audio/wav",
            headers=custom_headers
        )


    except Exception as e:
        print(f"Text endpoint processing error: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
