import nemo.collections.asr as nemo_asr
import time
import torch
import threading

model_lock = threading.Lock()


# use_lhotse=False avoids the "pretokenize in main process" Lhotse warning
TRANSCRIBE_OPTS = {"use_lhotse": False, "num_workers": 0}


def warmup(model):
    with model_lock:
        with torch.inference_mode():
            model.transcribe(["warmup.wav"], **TRANSCRIBE_OPTS)


def transcribe(model):
    with model_lock:
        print("\n\n\n\n\nTranscribing...")
        start_time = time.time()
        with torch.inference_mode():
            transcriptions = model.transcribe(["test.wav"], **TRANSCRIBE_OPTS)[0].text
        processing_time = time.time() - start_time
        print(transcriptions)
        print(f"Time taken: {processing_time:.2f} seconds\n\n\n\n\n")


def main():
    # Load the model
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = nemo_asr.models.ASRModel.from_pretrained(
        model_name="nvidia/parakeet-tdt-0.6b-v3"
    ).to(device)

    # Keep the GPU warm 
    threading.Thread(target=warmup, args=(model,), daemon=True).start()
    transcribe(model)


if __name__ == "__main__":
    main()
