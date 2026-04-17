import os

try:
    from twilio.rest import Client
except ImportError:
    Client = None
from dotenv import load_dotenv

load_dotenv()

class SMSService:
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.bypass_sms = os.getenv('BYPASS_SMS', 'false').lower() == 'true'
        
        # Check if credentials are present
        if not all([self.account_sid, self.auth_token, self.from_number]) or \
           'your_account_sid_here' in self.account_sid:
            self.client = None
            self.is_mock = True
            print("WARNING: Twilio credentials not fully configured. SMS will be logged to console (Debug Mode).")
        else:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                self.is_mock = self.bypass_sms
            except Exception as e:
                self.client = None
                self.is_mock = True
                print(f"ERROR: Failed to initialize Twilio client: {e}")

    def format_number(self, number):
        """Ensure number has country code. Default to +91 for Indian numbers."""
        if not number:
            return ""
            
        # 1. Clean input: remove everything except digits
        original = str(number).strip()
        clean_digits = "".join([c for c in original if c.isdigit()])
        
        # 2. Logic for Indian numbers (+91)
        # Case A: 10 digits -> Add +91
        if len(clean_digits) == 10:
            formatted = f"+91{clean_digits}"
        # Case B: 12 digits starting with 91 -> Add +
        elif len(clean_digits) == 12 and clean_digits.startswith('91'):
            formatted = f"+{clean_digits}"
        # Case C: Already has a plus in original -> use clean digits with plus
        elif original.startswith('+'):
            formatted = f"+{clean_digits}"
        # Case D: Default fallback - add + if not present (risky, but better than nothing)
        else:
            # If it's less than 10 digits and doesn't start with country code, 
            # we can't do much, but let's at least try +91 if it's likely a local number
            if len(clean_digits) < 10:
                formatted = f"+91{clean_digits}"
            else:
                formatted = f"+{clean_digits}"
                
        print(f"DEBUG: SMS Formatting: '{original}' -> '{formatted}'")
        return formatted

    def send_otp(self, to_number, otp):
        to_number = self.format_number(to_number)
        message_body = f"Your Microgrid OS verification code is: {otp}. It will expire in 5 minutes."
        
        # Priority: Bypass mode for network/DNS issues
        if self.bypass_sms:
            print("--- REAL SMS BYPASS (DEBUG LOG) ---")
            print(f"TO: {to_number}")
            print(f"BODY: {message_body}")
            print("-----------------------------------")
            return True, "SMS Bypassed: Code logged to terminal console"

        if self.client:
            try:
                message = self.client.messages.create(
                    body=message_body,
                    from_=self.from_number,
                    to=to_number
                )
                print(f"SUCCESS: SMS sent to {to_number}. SID: {message.sid}")
                return True, "SMS sent successfully"
            except Exception as e:
                print(f"ERROR: Failed to send SMS via Twilio: {e}")
                return False, f"Twilio error: {str(e)}"
        else:
            # Fallback debug mode
            print("--- REAL SMS MOCK (DEBUG MODE) ---")
            print(f"TO: {to_number}")
            print(f"BODY: {message_body}")
            print("----------------------------------")
            return True, "Debug mode: SMS logged to console"

# Singleton instance
sms_service = SMSService()

def send_otp_sms(mobile, otp):
    return sms_service.send_otp(mobile, otp)
