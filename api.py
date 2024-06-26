import os
import shutil
import subprocess
import torch
import torchaudio
from fastapi import FastAPI, File, UploadFile, Form
from models import voicecraft
from data.tokenizer import AudioTokenizer, TextTokenizer
from inference_tts_scale import inference_one_sample
from pydantic import BaseModel
import io
from starlette.responses import StreamingResponse
import getpass
import logging
import platform
from huggingface_hub import hf_hub_download
import requests

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler('api.log'),
                        logging.StreamHandler()
                    ])

app = FastAPI()

class AdditionalArgs(BaseModel):
    top_k: int = 0
    top_p: float = 0.9
    temperature: float = 1.0
    stop_repetition: int = 3
    kvcache: int = 1
    sample_batch_size: int = 1

def get_available_models():
    models_dir = "./pretrained_models"
    models = [f for f in os.listdir(models_dir) if os.path.isdir(os.path.join(models_dir, f))]
    models.sort()  # Sort the models alphabetically
    return models

@app.get("/models")
def get_models():
    models = get_available_models()
    return {"models": models}

def get_latest_snapshot_dir(model_dir):
    snapshot_dir = os.path.join(model_dir, "snapshots")
    if not os.path.exists(snapshot_dir):
        return None

    snapshot_subdirs = [d for d in os.listdir(snapshot_dir) if os.path.isdir(os.path.join(snapshot_dir, d))]
    if not snapshot_subdirs:
        return None

    latest_snapshot_subdir = max(snapshot_subdirs, key=lambda x: os.path.getmtime(os.path.join(snapshot_dir, x)))
    return os.path.join(snapshot_dir, latest_snapshot_subdir)

def get_latest_snapshot_dir(model_dir):
    snapshot_dir = os.path.join(model_dir, "snapshots")
    if not os.path.exists(snapshot_dir):
        return None

    snapshot_subdirs = [d for d in os.listdir(snapshot_dir) if os.path.isdir(os.path.join(snapshot_dir, d))]
    if not snapshot_subdirs:
        return None

    latest_snapshot_subdir = max(snapshot_subdirs, key=lambda x: os.path.getmtime(os.path.join(snapshot_dir, x)))
    return os.path.join(snapshot_dir, latest_snapshot_subdir)

def get_model(model_name, device=None):
    
    model_dir = f"./pretrained_models/{model_name}"
    config_path = os.path.join(model_dir, "config.json")
    model_file_path = os.path.join(model_dir, "model.safetensors")
    
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
    
    try:
        if not os.path.isfile(config_path) or not os.path.isfile(model_file_path):
            if model_name == "VoiceCraft_830M_TTSEnhanced":
                base_url = "https://huggingface.co/pyp1/VoiceCraft_830M_TTSEnhanced/resolve/main/"
            elif model_name == "VoiceCraft_gigaHalfLibri330M_TTSEnhanced_max16s":
                base_url = "https://huggingface.co/pyp1/VoiceCraft_gigaHalfLibri330M_TTSEnhanced_max16s/resolve/main/"
            else:
                raise ValueError(f"Unsupported model: {model_name}")

            # Download config and model files
            response = requests.get(f"{base_url}config.json")
            response.raise_for_status()
            with open(config_path, 'wb') as f:
                f.write(response.content)

            response = requests.get(f"{base_url}model.safetensors")
            response.raise_for_status()
            with open(model_file_path, 'wb') as f:
                f.write(response.content)
    except Exception as e:
        logging.error(f"Failed to download model '{model_name}': {str(e)}")
        raise

    model = voicecraft.VoiceCraft.from_pretrained(model_dir)
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    return model

@app.post("/generate")
async def generate_audio(
    time: float = Form(...),
    target_text: str = Form(""),
    audio: UploadFile = File(...),
    transcript: UploadFile = File(...),
    save_to_file: bool = Form(True),
    output_path: str = Form("."),
    top_k: int = Form(0),
    top_p: float = Form(0.8),
    temperature: float = Form(1.0),
    stop_repetition: int = Form(3),
    kvcache: int = Form(1),
    sample_batch_size: int = Form(4),
    device: str = Form(None),
    model_name: str = Form("")
):
    logging.info("Received request to generate audio")

    # Get the current username
    username = getpass.getuser()

    # Set the USER environment variable to the username
    os.environ['USER'] = username
    logging.debug(f"Set USER environment variable to: {username}")

    # Check if the operating system is Windows
    if platform.system() == 'Windows':
        # Set the environment variable for phonemizer to use a specific espeak library only on Windows
        os.environ['PHONEMIZER_ESPEAK_LIBRARY'] = './espeak/libespeak-ng.dll'
        logging.debug("Set PHONEMIZER_ESPEAK_LIBRARY environment variable")

    # Create the voice folder
    voice_folder = f"./voices/{os.path.splitext(audio.filename)[0]}"
    os.makedirs(voice_folder, exist_ok=True)
    logging.debug(f"Created voice folder: {voice_folder}")

    # Save the uploaded files
    audio_fn = os.path.join(voice_folder, audio.filename)
    transcript_fn = os.path.join(voice_folder, f"{os.path.splitext(audio.filename)[0]}.txt")
    with open(audio_fn, "wb") as f:
        shutil.copyfileobj(audio.file, f)
    with open(transcript_fn, "wb") as f:
        shutil.copyfileobj(transcript.file, f)
    logging.debug(f"Saved uploaded files: {audio_fn}, {transcript_fn}")

    # Prepare alignment if not already done
    mfa_folder = os.path.join(voice_folder, "mfa")
    os.makedirs(mfa_folder, exist_ok=True)
    alignment_file = os.path.join(mfa_folder, f"{os.path.splitext(audio.filename)[0]}.csv")
    if not os.path.isfile(alignment_file):
        logging.info("Preparing alignment...")
        subprocess.run(["mfa", "align", "-v", "--clean", "-j", "1", "--output_format", "csv",
                        voice_folder, "english_us_arpa", "english_us_arpa", mfa_folder])
        logging.info("Alignment completed")
    else:
        logging.info("Alignment file already exists. Skipping alignment.")

    # Read the alignment file and find the closest end time
    cut_off_sec = time
    prompt_end_word = ""
    closest_end = 0
    with open(alignment_file, "r") as f:
        lines = f.readlines()[1:]  # Skip header
        for line in lines:
            begin, end, label, type, *_ = line.strip().split(",")
            end = float(end)
            if end > cut_off_sec:
                break
            closest_end = end
            prompt_end_word = label

    logging.info(f"Identified end value closest to desired time: {closest_end} seconds")

    if not prompt_end_word:
        logging.error("No suitable word found within the desired time frame.")
        return {"message": "No suitable word found within the desired time frame."}

    # Read the transcript file and extract the prompt
    with open(transcript_fn, "r") as f:
        transcript_text = f.read().strip()

    logging.debug(f"Reading transcript file: {transcript_fn}")

    transcript_words = transcript_text.split()
    prompt_end_idx = -1
    for idx, word in enumerate(transcript_words):
        if word.strip(".,!?;:") == prompt_end_word:
            prompt_end_idx = idx
            break

    if prompt_end_idx == -1:
        logging.error("Error: Prompt end word not found in the transcript.")
        return {"message": "Error: Prompt end word not found in the transcript."}

    prompt_transcript = " ".join(transcript_words[:prompt_end_idx+1])

    logging.info(f"Prompt transcript up to closest end word: {prompt_transcript}")

    # Prepend the extracted transcript to the user's prompt
    final_prompt = prompt_transcript + " " + target_text
    logging.info(f"Final prompt to be used: {final_prompt}")

    # Set the device
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    elif device.lower() not in ["cpu", "cuda"]:
        logging.warning("Invalid device specified. Defaulting to CPU.")
        device = "cpu"

    logging.info(f"Using device: {device}")

    # If model_name is provided, use it; otherwise, raise an error
    if model_name is None:
        logging.error("No model name provided.")
        return {"message": "No model name provided."}

    logging.info(f"Loading model: {model_name}")
    model = get_model(model_name, device)

    # Load tokenizers
    text_tokenizer = TextTokenizer(backend="espeak")
    audio_tokenizer = AudioTokenizer(signature=f"./pretrained_models/encodec_4cb2048_giga.th", device=device)

    additional_args = AdditionalArgs(
        top_k=top_k,
        top_p=top_p,
        temperature=temperature,
        stop_repetition=stop_repetition,
        kvcache=kvcache,
        sample_batch_size=sample_batch_size
    )

    decode_config = {
        'top_k': additional_args.top_k,
        'top_p': additional_args.top_p,
        'temperature': additional_args.temperature,
        'stop_repetition': additional_args.stop_repetition,
        'kvcache': additional_args.kvcache,
        "codec_audio_sr": 16000,
        "codec_sr": 50,
        "silence_tokens": [1388, 1898, 131],
        "sample_batch_size": additional_args.sample_batch_size
    }

    # Calculate prompt_end_frame based on the actual closest end time
    prompt_end_frame = int(closest_end * 16000)
    logging.info(f"Prompt end frame: {prompt_end_frame}")

    logging.info("Calling inference_one_sample...")
    try:
        # Generate the audio
        concated_audio, gen_audio = inference_one_sample(
            model, model.args, model.args.phn2num, text_tokenizer, audio_tokenizer,
            audio_fn, final_prompt, device, decode_config, prompt_end_frame
        )
        logging.info("Inference completed.")
        # Empty CUDA cache after inference
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logging.info("CUDA cache emptied.")
    except Exception as e:
        logging.error(f"Error occurred during inference: {str(e)}")
        return {"message": "An error occurred during audio generation."}

    if save_to_file:
        # Save the generated audio to a file
        output_file = os.path.join(output_path, f"{os.path.splitext(audio.filename)[0]}_generated.wav")
        torchaudio.save(output_file, gen_audio[0].cpu(), 16000)
        logging.info(f"Generated audio saved as: {output_file}")
        return {"message": "Audio generated successfully.", "output_file": output_file}
    else:
        # Serve the generated audio as bytes
        audio_bytes = io.BytesIO()
        torchaudio.save(audio_bytes, gen_audio[0].cpu(), 16000, format="wav")
        audio_bytes.seek(0)
        return StreamingResponse(audio_bytes, media_type="audio/wav")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8245)
