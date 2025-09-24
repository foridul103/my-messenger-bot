import os
import requests
from flask import Flask, request

# Flask অ্যাপ ইনিশিয়ালাইজ করা হচ্ছে
app = Flask(__name__)

# ===============================================================
# গুরুত্বপূর্ণ: এই তিনটি ভ্যালু Render-এর "Environment variables"
# সেকশন থেকে লোড হবে। কোডে সরাসরি এগুলো লিখবেন না।
# ===============================================================
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')
AI_API_KEY = os.environ.get('AI_API_KEY')


def get_ai_response(message):
    """
    এই ফাংশনটি ইউজারের মেসেজ Google Gemini AI-এর কাছে পাঠায়
    এবং সেখান থেকে একটি উত্তর নিয়ে আসে।
    """
    # Gemini API-এর endpoint
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={AI_API_KEY}"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    # যে ফরম্যাটে ডেটা পাঠাতে হবে
    data = {
        "contents": [{
            "parts": [{
                "text": message
            }]
        }]
    }
    
    try:
        # API-তে POST রিকোয়েস্ট পাঠানো হচ্ছে
        response = requests.post(api_url, headers=headers, json=data, timeout=30)
        response.raise_for_status()  # কোনো HTTP error থাকলে তা দেখাবে

        # API থেকে পাওয়া JSON উত্তরটি পার্স করা হচ্ছে
        candidates = response.json().get('candidates', [])
        if candidates and 'content' in candidates[0] and 'parts' in candidates[0]['content']:
            return candidates[0]['content']['parts'][0]['text']
        else:
            # যদি AI কোনো কারণে উত্তর না দেয়
            return "দুঃখিত, আমি এই মুহূর্তে উত্তর তৈরি করতে পারছি না।"

    except requests.exceptions.RequestException as e:
        print(f"Error calling AI API: {e}")
        return "AI এর সাথে সংযোগ করতে একটি সমস্যা হয়েছে। দয়া করে পরে চেষ্টা করুন।"


def send_messenger_message(recipient_id, message_text):
    """
    এই ফাংশনটি ব্যবহারকারীর কাছে মেসেঞ্জারে উত্তর পাঠায়।
    """
    params = {
        "access_token": PAGE_ACCESS_TOKEN
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        },
        "messaging_type": "RESPONSE"
    }
    
    # Facebook Graph API-তে POST রিকোয়েস্ট পাঠানো হচ্ছে
    r = requests.post("https://graph.facebook.com/v18.0/me/messages", params=params, headers=headers, json=data)
    if r.status_code != 200:
        print(f"Failed to send message: {r.status_code} {r.text}")


# ===============================================================
# Webhook সেটআপ এবং মেসেজ হ্যান্ডলিং-এর মূল অংশ
# ===============================================================
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    # --- GET রিকোয়েস্ট: ফেসবুক যখন আপনার webhook URL ভেরিফাই করে ---
    if request.method == 'GET':
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode and token:
            if mode == "subscribe" and token == VERIFY_TOKEN:
                print("WEBHOOK_VERIFIED")
                return challenge, 200
            else:
                return "VERIFICATION_FAILED", 403
        return "INVALID_REQUEST", 400

    # --- POST রিকোয়েস্ট: যখন কোনো ব্যবহারকারী মেসেজ পাঠায় ---
    if request.method == 'POST':
        data = request.get_json()

        if data and data.get("object") == "page":
            for entry in data.get("entry", []):
                for messaging_event in entry.get("messaging", []):
                    # ব্যবহারকারীর কাছ থেকে মেসেজ এলে
                    if messaging_event.get("message"):
                        sender_id = messaging_event["sender"]["id"]        # মেসেজ প্রেরকের আইডি
                        message_text = messaging_event["message"]["text"]   # মেসেজের লেখা

                        # AI থেকে উত্তর আনার জন্য ফাংশন কল করা হচ্ছে
                        ai_reply = get_ai_response(message_text)
                        
                        # ব্যবহারকারীকে উত্তর পাঠানোর জন্য ফাংশন কল করা হচ্ছে
                        send_messenger_message(sender_id, ai_reply)

        # ফেসবুককে সফলভাবে প্রাপ্তির সংকেত পাঠানো হচ্ছে
        return "EVENT_RECEIVED", 200

    # যদি GET বা POST ছাড়া অন্য কোনো মেথড আসে
    return "Method Not Allowed", 405
