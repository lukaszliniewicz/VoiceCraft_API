
# VoiceCraft API Quick Start Guide

The VoiceCraft API is supposed to be a user-friendly, eay to install and Windows-compatible FastAPI application designed to extend the VoiceCraft text-to-speech (TTS) model with a convenient interface for generating speech audio from text. It comes with Windows and Linux one-click installers.

This guide provides an overview of the API, how to install, run it, and an example of how to use it. It was made for [Pandrator](https://github.com/lukaszliniewicz/Pandrator). 

## API Overview

The API endpoint `/generate` accepts POST requests with several parameters for customizing the TTS generation process:

- **time**: The cut-off time (in seconds) - how much of the sample is to be used for voice cloning, recommended between 3 and 9 (required).
- **target_text**: The text you wish to generate speech for (required).
- **audio**: The input audio file in WAV format (should be 16000hz and mono) which will be used to clone the voice (required).
- **transcript**: The full transcript of the input audio file, named as the wav file (required).
- **save_to_file**: Whether to save the generated audio to a file (default `True`).
- **output_path**: The directory where the output audio file should be saved (default `.`).
- Additional parameters for fine-tuning the generation (`top_k`, `top_p`, `temperature`, `stop_repetition`, `kvcache`, `sample_batch_size`, `device`).

The response will either be a JSON containing a message and the output file path (if `save_to_file` is `True`) or a streaming response with the generated audio (if `save_to_file` is `False`).

## Trying Out the API

After starting the API server, you can explore and test the API using the Swagger UI by navigating to `http://127.0.0.1:8245/docs` in your browser. This interface allows you to easily send requests to the API and view responses.

## Example Implementation

Below is an example Python script demonstrating how to send a request to the API:

```python
import requests

url = 'http://127.0.0.1:8245/generate'
files = {
    'audio': open('path/to/your/audio.wav', 'rb'),
    'transcript': open('path/to/your/transcript.txt', 'rb')
}
data = {
    'time': 5.0,
    'target_text': 'The text you want to generate',
    'save_to_file': True,
    'output_path': './generated_audios',
    # Add other form fields as needed
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

## Installation and Running

### Automatic installation
#### Linux
You can use `install_and_run.sh` to install the api and run it later on linux systems (it supports various package managers).

1. Download the script from Releases
3. Make the script executable
   ```
   chmod +x start_and_run.sh
   ```
4. Run the script
   ```
   sudo ./install_and_run.sh
   ```
#### Windows 

1. Download the .exe or .py file from Releases
2. Open the .exe with administrator priviliges if you want it to install git and ffmpeg automatically, or
3. Run the .py file from the Windows Terminal

### Manual installation

1. Clone the VoiceCraft API repository:
   ```
   git clone https://github.com/lukaszliniewicz/VoiceCraft_API.git
   ```
2. Change into the repository directory:
   ```
   cd VoiceCraft_API
   ```
3. Create a conda environment named `voicecraft_api`:
   ```
   conda create -n voicecraft_api python=3.9.16
   ```
4. Activate the environment:
   ```
   conda activate voicecraft_api
   ```
5. Install audiocraft:
   ```
   pip install -e git+https://github.com/facebookresearch/audiocraft.git@c5157b5bf14bf83449c17ea1eeb66c19fb4bc7f0#egg=audiocraft
   ```
6. Install pytorch etc.
   ```
   conda install pytorch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 pytorch-cuda=11.7 -c pytorch -c nvidia
   ```
7. Install the API requirements
   ```
   pip install -r requirements.txt
   ```
8. Install Montreal Forced Aligner
   ```
   conda install -c conda-forge montreal-forced-aligner=2.2.17 openfst=1.8.2 kaldi=5.5.1068
   ```
9. Install Montreal Forced Aligner models
   ``` 
   mfa model download dictionary english_us_arpa
   mfa model download acoustic english_us_arpa
   ```
10. If running on Linux, install Espeak NG:
    ```
    sudo apt-get install espeak-ng
    ```
10. Install `ffmpeg` as per your OS instructions.
11. If running on Windows, after installing `audiocraft`, replace the specified files with those from the `audiocraft_windows` directory in this repository to make it compatible with Windows:
   - Replace `src/audiocraft/audiocraft/utils/cluster.py` with `audiocraft_windows/cluster.py`
   - Replace `src/audiocraft/audiocraft/environment.py` with `audiocraft_windows/environment.py`
   - Replace `src/audiocraft/audiocraft/utils/checkpoint.py` with `audiocraft_windows/checkpoint.py`
12. Download the model and the encoder (one of the `.pth` files and the `.th` file) into the `pretrained_models` folder in the repository from [HuggingFace](https://huggingface.co/pyp1/VoiceCraft/tree/main).
13. Run the api (remember to always activate the Conda environment first!):
    ```
    python api.py (Windows) or python3 api.py (Linux)
    ```

## Additional Notes

- The API automatically performs audio-text alignment if not already performed for the given WAV/TXT pair and prepends the correct portion of the transcript to the prompt. It created a folder for each "voice" with the wav/txt pair and the alignment csv.
- You can simply send the text you want to generate, and the rest is handled automatically.

# The original readme: <br> VoiceCraft: Zero-Shot Speech Editing and Text-to-Speech in the Wild
[Demo](https://jasonppy.github.io/VoiceCraft_web) [Paper](https://jasonppy.github.io/assets/pdfs/VoiceCraft.pdf)


### TL;DR
VoiceCraft is a token infilling neural codec language model, that achieves state-of-the-art performance on both **speech editing** and **zero-shot text-to-speech (TTS)** on in-the-wild data including audiobooks, internet videos, and podcasts.

To clone or edit an unseen voice, VoiceCraft needs only a few seconds of reference.

## How to run inference
There are three ways:

1. with Google Colab. see [quickstart colab](#quickstart-colab)
2. with docker. see [quickstart docker](#quickstart-docker)
3. without docker. see [environment setup](#environment-setup)

When you are inside the docker image or you have installed all dependencies, Checkout [`inference_tts.ipynb`](./inference_tts.ipynb).

If you want to do model development such as training/finetuning, I recommend following [envrionment setup](#environment-setup) and [training](#training).

## News
:star: 03/28/2024: Model weights for giga330M and giga830M are up on HuggingFace🤗 [here](https://huggingface.co/pyp1/VoiceCraft/tree/main)!

:star: 04/05/2024: I finetuned giga330M with the TTS objective on gigaspeech and 1/5 of librilight, the model outperforms giga830M on TTS. Weights are [here](https://huggingface.co/pyp1/VoiceCraft/tree/main). Make sure maximal prompt + generation length <= 16 seconds (due to our limited compute, we had to drop utterances longer than 16s in training data)

## TODO
- [x] Codebase upload
- [x] Environment setup
- [x] Inference demo for speech editing and TTS
- [x] Training guidance
- [x] RealEdit dataset and training manifest
- [x] Model weights (giga330M.pth, giga830M.pth, and gigaHalfLibri330M_TTSEnhanced_max16s.pth)
- [x] Better guidance on training/finetuning
- [x] Write colab notebooks for better hands-on experience
- [ ] HuggingFace Spaces demo
- [ ] Command line
- [ ] Improve efficiency


## QuickStart Colab

:star: To try out speech editing or TTS Inference with VoiceCraft, the simplest way is using Google Colab.
Instructions to run are on the Colab itself.

1. To try [Speech Editing](https://colab.research.google.com/drive/1FV7EC36dl8UioePY1xXijXTMl7X47kR_?usp=sharing)
2. To try [TTS Inference](https://colab.research.google.com/drive/1lch_6it5-JpXgAQlUTRRI2z2_rk5K67Z?usp=sharing)

## QuickStart Docker
:star: To try out TTS inference with VoiceCraft, you can also use docker. Thank [@ubergarm](https://github.com/ubergarm) and [@jayc88](https://github.com/jay-c88) for making this happen.

Tested on Linux and Windows and should work with any host with docker installed.
```bash
# 1. clone the repo on in a directory on a drive with plenty of free space
git clone git@github.com:jasonppy/VoiceCraft.git
cd VoiceCraft

# 2. assumes you have docker installed with nvidia container container-toolkit (windows has this built into the driver)
# https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/1.13.5/install-guide.html
# sudo apt-get install -y nvidia-container-toolkit-base || yay -Syu nvidia-container-toolkit || echo etc...

# 3. First build the docker image
docker build --tag "voicecraft" .

# 4. Try to start an existing container otherwise create a new one passing in all GPUs
./start-jupyter.sh  # linux
start-jupyter.bat   # windows

# 5. now open a webpage on the host box to the URL shown at the bottom of:
docker logs jupyter

# 6. optionally look inside from another terminal
docker exec -it jupyter /bin/bash
export USER=(your_linux_username_used_above)
export HOME=/home/$USER
sudo apt-get update

# 7. confirm video card(s) are visible inside container
nvidia-smi

# 8. Now in browser, open inference_tts.ipynb and work through one cell at a time
echo GOOD LUCK
```

## Environment setup
```bash
conda create -n voicecraft python=3.9.16
conda activate voicecraft

pip install -e git+https://github.com/facebookresearch/audiocraft.git@c5157b5bf14bf83449c17ea1eeb66c19fb4bc7f0#egg=audiocraft
pip install xformers==0.0.22
pip install torchaudio==2.0.2 torch==2.0.1 # this assumes your system is compatible with CUDA 11.7, otherwise checkout https://pytorch.org/get-started/previous-versions/#v201
apt-get install ffmpeg # if you don't already have ffmpeg installed
apt-get install espeak-ng # backend for the phonemizer installed below
pip install tensorboard==2.16.2
pip install phonemizer==3.2.1
pip install datasets==2.16.0
pip install torchmetrics==0.11.1
# install MFA for getting forced-alignment, this could take a few minutes
conda install -c conda-forge montreal-forced-aligner=2.2.17 openfst=1.8.2 kaldi=5.5.1068
# install MFA english dictionary and model
mfa model download dictionary english_us_arpa
mfa model download acoustic english_us_arpa
# pip install huggingface_hub
# conda install pocl # above gives an warning for installing pocl, not sure if really need this

# to run ipynb
conda install -n voicecraft ipykernel --no-deps --force-reinstall
```

If you have encountered version issues when running things, checkout [environment.yml](./environment.yml) for exact matching.

## Inference Examples
Checkout [`inference_speech_editing.ipynb`](./inference_speech_editing.ipynb) and [`inference_tts.ipynb`](./inference_tts.ipynb)

## Training
To train an VoiceCraft model, you need to prepare the following parts:
1. utterances and their transcripts
2. encode the utterances into codes using e.g. Encodec
3. convert transcripts into phoneme sequence, and a phoneme set (we named it vocab.txt)
4. manifest (i.e. metadata)

Step 1,2,3 are handled in [./data/phonemize_encodec_encode_hf.py](./data/phonemize_encodec_encode_hf.py), where
1. Gigaspeech is downloaded through HuggingFace. Note that you need to sign an agreement in order to download the dataset (it needs your auth token)
2. phoneme sequence and encodec codes are also extracted using the script.

An example run:

```bash
conda activate voicecraft
export CUDA_VISIBLE_DEVICES=0
cd ./data
python phonemize_encodec_encode_hf.py \
--dataset_size xs \
--download_to path/to/store_huggingface_downloads \
--save_dir path/to/store_extracted_codes_and_phonemes \
--encodec_model_path path/to/encodec_model \
--mega_batch_size 120 \
--batch_size 32 \
--max_len 30000
```
where encodec_model_path is avaliable [here](https://huggingface.co/pyp1/VoiceCraft). This model is trained on Gigaspeech XL, it has 56M parameters, 4 codebooks, each codebook has 2048 codes. Details are described in our [paper](https://jasonppy.github.io/assets/pdfs/VoiceCraft.pdf). If you encounter OOM during extraction, try decrease the batch_size and/or max_len.
The extracted codes, phonemes, and vocab.txt will be stored at `path/to/store_extracted_codes_and_phonemes/${dataset_size}/{encodec_16khz_4codebooks,phonemes,vocab.txt}`.

As for manifest, please download train.txt and validation.txt from [here](https://huggingface.co/datasets/pyp1/VoiceCraft_RealEdit/tree/main), and put them under `path/to/store_extracted_codes_and_phonemes/manifest/`. Please also download vocab.txt from [here](https://huggingface.co/datasets/pyp1/VoiceCraft_RealEdit/tree/main) if you want to use our pretrained VoiceCraft model (so that the phoneme-to-token matching is the same).

Now, you are good to start training!

```bash
conda activate voicecraft
cd ./z_scripts
bash e830M.sh
```

It's the same procedure to prepare your own custom dataset. Make sure that if 

## Finetuning
You also need to do step 1-4 as Training, and I recommend to use AdamW for optimization if you finetune a pretrained model for better stability. checkout script `./z_scripts/e830M_ft.sh`.

If your dataset introduce new phonemes (which is very likely) that doesn't exist in the giga checkpoint, make sure you combine the original phonemes with the phoneme from your data when construction vocab. And you need to adjust `--text_vocab_size` and `--text_pad_token` so that the former is bigger than or equal to you vocab size, and the latter has the same value as `--text_vocab_size` (i.e. `--text_pad_token` is always the last token). Also since the text embedding are now of a different size, make sure you modify the weights loading part so that I won't crash (you could skip loading `text_embedding` or only load the existing part, and randomly initialize the new)

## License
The codebase is under CC BY-NC-SA 4.0 ([LICENSE-CODE](./LICENSE-CODE)), and the model weights are under Coqui Public Model License 1.0.0 ([LICENSE-MODEL](./LICENSE-MODEL)). Note that we use some of the code from other repository that are under different licenses: `./models/codebooks_patterns.py` is under MIT license; `./models/modules`, `./steps/optim.py`, `data/tokenizer.py` are under Apache License, Version 2.0; the phonemizer we used is under GNU 3.0 License.

## Acknowledgement
We thank Feiteng for his [VALL-E reproduction](https://github.com/lifeiteng/vall-e), and we thank audiocraft team for open-sourcing [encodec](https://github.com/facebookresearch/audiocraft).

## Citation
```
@article{peng2024voicecraft,
  author    = {Peng, Puyuan and Huang, Po-Yao and Li, Daniel and Mohamed, Abdelrahman and Harwath, David},
  title     = {VoiceCraft: Zero-Shot Speech Editing and Text-to-Speech in the Wild},
  journal   = {arXiv},
  year      = {2024},
}
```

## Disclaimer
Any organization or individual is prohibited from using any technology mentioned in this paper to generate or edit someone's speech without his/her consent, including but not limited to government leaders, political figures, and celebrities. If you do not comply with this item, you could be in violation of copyright laws.

