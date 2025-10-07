import os
from twilio.rest import Client

account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
client = Client(account_sid, auth_token)

call = client.calls.create(
    twiml=f"""
    <Response>
      <Connect>
        <Stream url="wss://c2f630a35e85.ngrok-free.app/" />
      </Connect>
    </Response>
    """,
    to="+358442837983",
    from_="+358454906614",
)

print(call.sid)
