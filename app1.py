# -*- coding: utf-8 -*-
"""
Created on Fri Apr 18 22:40:07 2025

@author: tehre
"""

from flask import Flask, request, jsonify
import uuid
import os
import requests
from deep_translator import GoogleTranslator
import azure.cognitiveservices.speech as speechsdk

# ==== Flask Setup ====
app = Flask(__name__)

# ==== OpenRouter & Azure Keys ====
OPENROUTER_API_KEY = "sk-or-..."  # REDACT FOR PRODUCTION
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
AZURE_TTS_KEY_1 = "..."  # REDACT
AZURE_TRANSLATOR_KEY = "..."
AZURE_REGION = "southeastasia"
AZURE_TRANSLATOR_REGION = "southeastasia"
translator_endpoint = "https://api.cognitive.microsofttranslator.com"

# ==== Helpers ====

def translate_urdu_to_english(text):
    try:
        return GoogleTranslator(source="ur", target="en").translate(text)
    except Exception as e:
        print(f"Translation error: {e}")
        return ""

def translate_english_to_urdu(text):
    url = f"{translator_endpoint}/translate?api-version=3.0&from=en&to=ur"
    headers = {
        'Ocp-Apim-Subscription-Key': AZURE_TRANSLATOR_KEY,
        'Ocp-Apim-Subscription-Region': AZURE_TRANSLATOR_REGION,
        'Content-type': 'application/json'
    }
    body = [{'text': text}]
    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    result = response.json()
    return result[0]['translations'][0]['text']

def is_query_mental_health_related(text):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = (
        "You are a classifier. Respond only with 'Yes' or 'No'.\n"
        "Is the following text related to mental health, physical health, emotions, depression, anxiety, or therapy?\n\n"
        f"Text: \"{text}\"\nAnswer:"
    )
    payload = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        result = response.json()
        answer = result["choices"][0]["message"]["content"].strip().lower()
        return "yes" in answer
    except Exception as e:
        print(f"Classifier Exception: {e}")
        return False

def generate_response_melogpt(english_text):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "MentalHealthBot"
    }

    payload = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [
            {
                "role": "user",
                "content": f"A patient says: \"{english_text}\". Respond as a kind and helpful mental health therapist."
            }
        ]
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Response generation failed: {e}")
        return "Error generating response."

def azure_tts_urdu(text):
    try:
        translated_urdu = translate_english_to_urdu(text)
        ssml = f"""
        <speak version='1.0' xml:lang='ur-PK'>
            <voice xml:lang='ur-PK' xml:gender='Male' name='ur-PK-AsadNeural'>
                {translated_urdu}
            </voice>
        </speak>
        """
        tts_url = f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": AZURE_TTS_KEY_1,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-32kbitrate-mono-mp3",
            "User-Agent": "UrduMentalHealthBot"
        }
        response = requests.post(tts_url, headers=headers, data=ssml.encode("utf-8"))
        if response.status_code == 200:
            filename = f"static/response_{uuid.uuid4().hex}.mp3"
            with open(filename, "wb") as f:
                f.write(response.content)
            return filename
        else:
            print("Azure TTS Error:", response.status_code, response.text)
            return None
    except Exception as e:
        print(f"TTS Exception: {e}")
        return None

# ==== API Route ====

@app.route("/api/mental-health", methods=["POST"])
def mental_health_api():
    data = request.get_json()
    urdu_text = data.get("text", "")

    if not urdu_text:
        return jsonify({"error": "No Urdu text provided."}), 400

    english_text = translate_urdu_to_english(urdu_text)

    if not english_text.strip():
        return jsonify({"error": "Failed to translate Urdu to English."}), 500

    if is_query_mental_health_related(english_text):
        reply_en = generate_response_melogpt(english_text)
        audio_path = azure_tts_urdu(reply_en)
    else:
        reply_en = "I'm sorry! I can only give advice related to mental health."
        audio_path = azure_tts_urdu(reply_en)

    if audio_path:
        return jsonify({
            "urdu_input": urdu_text,
            "english_translation": english_text,
            "response_english": reply_en,
            "audio_file_url": f"/{audio_path}"
        })
    else:
        return jsonify({"error": "Failed to generate Urdu speech."}), 500

# ==== Run Server ====
if __name__ == "__main__":
    if not os.path.exists("static"):
        os.makedirs("static")
    app.run(host="0.0.0.0", port=5000, debug=True)
