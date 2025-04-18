# -*- coding: utf-8 -*-
"""
Updated on Fri Apr 18 2025

@author: tehre
"""

import os
import uuid
import requests
import speech_recognition as sr
import azure.cognitiveservices.speech as speechsdk
from deep_translator import GoogleTranslator

# ==== OpenRouter API Setup ====
OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ==== Azure API Keys ====
AZURE_TTS_KEY_1 = "5hLz8c1SpUvWuruisUMtFZEROsgujtGCCHyonwCtza6AFJnOD1EEJQQJ99BDACqBBLyXJ3w3AAAYACOGvI2D"
AZURE_TRANSLATOR_KEY = "BOOpV2mHXV44rGFAVdDME76Qd69rNj26gIEkqC6sohJ6qCHpsdyzJQQJ99BDACqBBLyXJ3w3AAAbACOG4Ij2"
AZURE_REGION = "southeastasia"
AZURE_TRANSLATOR_REGION = "southeastasia"
translator_endpoint = "https://api.cognitive.microsofttranslator.com"

# ==== Translation Helpers ====

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

# ==== Mental Health Classifier ====

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
        print(f"[Classifier Result]: {answer}")
        return "yes" in answer
    except Exception as e:
        print(f"Classifier Exception: {e}")
        return False

# ==== Response Generator (OpenRouter DeepSeek) ====

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
        reply = result["choices"][0]["message"]["content"].strip()
        print(f"💬 Response (English): {reply}")
        return reply
    except Exception as e:
        print(f"Response generation failed: {e}")
        return "Error generating response."

# ==== Azure TTS (Text-to-Speech) for Urdu ====

def azure_tts_urdu(text):
    try:
        translated_urdu = translate_english_to_urdu(text)
        print("📝 Urdu Translation:", translated_urdu)

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
            filename = f"response_{uuid.uuid4().hex}.mp3"
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"✅ Urdu speech saved to '{filename}'")

            if os.name == 'nt':
                os.system(f'start {filename}')
            else:
                os.system(f'mpg123 {filename}')
        else:
            print("Azure TTS Error:", response.status_code, response.text)

    except Exception as e:
        print(f"TTS Exception: {e}")

# ==== Main Execution Pipeline ====

def recognize_and_translate_urdu():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎙️ Speak your query in Urdu:")
        audio = recognizer.listen(source)

    try:
        urdu_text = recognizer.recognize_google(audio, language="ur-PK")
        english_text = translate_urdu_to_english(urdu_text)

        print("\n🗣️ Your Query (Urdu):", urdu_text)
        print("🌐 Translated (English):", english_text)

        if not english_text.strip():
            print("❗ Translation failed or empty.")
            return

        if is_query_mental_health_related(english_text):
            response = generate_response_melogpt(english_text)
            azure_tts_urdu(response)
        else:
            print("⛔ Not a mental health related query.")
            azure_tts_urdu("میں معذرت کرتا ہوں! میں صرف آپ کی ذہنی صحت سے متعلق مشورے دے سکتا ہوں۔")

    except sr.UnknownValueError:
        print("❌ Could not understand the audio.")
    except sr.RequestError as e:
        print(f"🛑 Speech recognition error: {e}")
    except Exception as e:
        print(f"🚨 General Error: {e}")

if __name__ == "__main__":
    recognize_and_translate_urdu()
