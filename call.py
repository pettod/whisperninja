import subprocess
import sys

def call_number(phone_number: str):
    # Clean the phone number to avoid spaces
    phone_number = phone_number.replace(" ", "")
    # Create AppleScript command
    applescript = f'''
    tell application "FaceTime"
        activate
        open location "facetime-audio://{phone_number}"
    end tell
    '''
    print(phone_number)
    subprocess.run(["osascript", "-e", applescript])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python call.py <phone_number>")
        sys.exit(1)
    
    phone_number = sys.argv[1]
    call_number(phone_number)