import sys
import urllib.parse
import os

def call_number(phone_number: str):
    # Clean the phone number to avoid spaces
    phone_number = phone_number.replace(" ", "")

    # Encode it for URL safety
    tel_url = f"tel://{urllib.parse.quote(phone_number)}"

    # Tell macOS to open it, which launches FaceTime/iPhone call
    os.system(f"open '{tel_url}'")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python call.py <phone_number>")
        sys.exit(1)
    
    phone_number = sys.argv[1]
    call_number(phone_number)