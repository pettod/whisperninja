import asyncio
import websockets
import json
import base64
import pyaudio

CHUNK = 320  # 20ms of 8kHz mono 16-bit PCM

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=8000, input=True, output=True, frames_per_buffer=CHUNK)

async def handler(websocket):
    async for message in websocket:
        data = json.loads(message)
        if data.get("event") == "media":
            audio = base64.b64decode(data["media"]["payload"])
            stream.write(audio)  # play remote audio through speakers

        # capture mic and send it back
        mic_data = stream.read(CHUNK, exception_on_overflow=False)
        await websocket.send(json.dumps({
            "event": "media",
            "media": {"payload": base64.b64encode(mic_data).decode()}
        }))

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8080):
        await asyncio.Future()  # run forever

asyncio.run(main())
