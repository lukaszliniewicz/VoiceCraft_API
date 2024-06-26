import os
import subprocess
import sys
import time
import shutil
import requests
import traceback
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('install_log.txt'),
        logging.StreamHandler(sys.stdout)
    ]
)

def run_command(command):
    try:
        logging.info(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logging.debug(f"Command output: {result.stdout}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing command: {command}")
        logging.error(f"Error message: {str(e)}")
        logging.error(f"Error output: {e.stderr}")
        raise

def check_program_installed(program):
    logging.info(f"Checking if {program} is installed...")
    try:
        result = shutil.which(program)
        logging.info(f"{program} is {'installed' if result else 'not installed'}")
        return result is not None
    except Exception as e:
        logging.error(f"Error checking if {program} is installed: {str(e)}")
        logging.error(traceback.format_exc())
        raise

def check_choco():
    return check_program_installed('choco')

def install_choco():
    logging.info("Installing Chocolatey...")
    try:
        run_command(['powershell', '-Command', "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))"])
    except Exception as e:
        logging.error(f"Error installing Chocolatey: {str(e)}")
        logging.error(traceback.format_exc())
        raise

def install_dependencies():
    dependencies = ['git', 'curl', 'ffmpeg']
    missing_dependencies = [dep for dep in dependencies if not check_program_installed(dep)]
    
    if missing_dependencies:
        if not check_choco():
            logging.info("Chocolatey is not installed.")
            install_choco()
        
        for dependency in missing_dependencies:
            logging.info(f"Installing {dependency}...")
            try:
                run_command(['choco', 'install', dependency, '-y'])
            except subprocess.CalledProcessError as e:
                logging.error(f"Failed to install {dependency}.")
                raise
    else:
        logging.info("All dependencies are already installed.")

def install_conda(install_path):
    logging.info("Installing Miniconda...")
    try:
        conda_installer = 'Miniconda3-latest-Windows-x86_64.exe'
        run_command(['curl', '-O', f'https://repo.anaconda.com/miniconda/{conda_installer}'])
        run_command([conda_installer, '/InstallationType=JustMe', '/RegisterPython=0', '/S', f'/D={install_path}'])
        os.remove(conda_installer)
    except Exception as e:
        logging.error(f"Error installing Miniconda: {str(e)}")
        logging.error(traceback.format_exc())
        raise

def check_conda(conda_path):
    logging.info(f"Checking if conda is installed at {conda_path}...")
    try:
        conda_exe = os.path.join(conda_path, 'Scripts', 'conda.exe')
        result = os.path.exists(conda_exe)
        logging.info(f"Conda is {'installed' if result else 'not installed'} at {conda_path}")
        return result
    except Exception as e:
        logging.error(f"Error checking if conda is installed at {conda_path}: {str(e)}")
        logging.error(traceback.format_exc())
        raise

def create_conda_env(conda_path, env_name, python_version):
    logging.info(f"Creating conda environment {env_name}...")
    try:
        run_command([f'{conda_path}\\Scripts\\conda.exe', 'create', '-n', env_name, f'python={python_version}', '-y'])
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to create conda environment {env_name}")
        logging.error(f"Error message: {str(e)}")
        raise

def install_requirements(conda_path, env_name, requirements_file):
    logging.info(f"Installing requirements for {env_name} from {requirements_file}...")
    try:
        run_command([f'{conda_path}\\Scripts\\conda.exe', 'run', '-n', env_name, 'pip', 'install', '-r', requirements_file])
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to install requirements for {env_name} from {requirements_file}")
        logging.error(f"Error message: {str(e)}")
        raise

def install_voicecraft_api_dependencies(conda_path, env_name):
    logging.info(f"Installing VoiceCraft API dependencies in {env_name}...")
    try:
        run_command([f'{conda_path}\\Scripts\\conda.exe', 'run', '-n', env_name, 'conda', 'install', 'pytorch==2.0.1', 'torchvision==0.15.2', 'torchaudio==2.0.2', 'pytorch-cuda=11.7', '-c', 'pytorch', '-c', 'nvidia', '-y'])
        run_command([f'{conda_path}\\Scripts\\conda.exe', 'run', '-n', env_name, 'conda', 'install', '-c', 'conda-forge', 'montreal-forced-aligner=2.2.17', 'openfst=1.8.2', 'kaldi=5.5.1068', '-y'])
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to install VoiceCraft API dependencies in {env_name}")
        logging.error(f"Error message: {str(e)}")
        raise

def download_mfa_models(conda_path, env_name):
    logging.info(f"Downloading MFA models in {env_name}...")
    try:
        run_command([f'{conda_path}\\Scripts\\conda.exe', 'run', '-n', env_name, 'mfa', 'model', 'download', 'dictionary', 'english_us_arpa'])
        run_command([f'{conda_path}\\Scripts\\conda.exe', 'run', '-n', env_name, 'mfa', 'model', 'download', 'acoustic', 'english_us_arpa'])
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to download MFA models in {env_name}")
        logging.error(f"Error message: {str(e)}")
        raise

def install_audiocraft(conda_path, env_name, voicecraft_repo_path):
    logging.info(f"Installing audiocraft package in {env_name}...")
    try:
        audiocraft_repo = 'https://github.com/facebookresearch/audiocraft.git'
        audiocraft_commit = 'c5157b5bf14bf83449c17ea1eeb66c19fb4bc7f0'
        
        # Change to the VoiceCraft repository directory
        os.chdir(voicecraft_repo_path)
        
        # Install audiocraft package
        run_command([f'{conda_path}\\Scripts\\conda.exe', 'run', '-n', env_name, 'pip', 'install', '-e', f'git+{audiocraft_repo}@{audiocraft_commit}#egg=audiocraft'])
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to install audiocraft package in {env_name}")
        logging.error(f"Error message: {str(e)}")
        raise

def run_voicecraft_api_server(conda_path, env_name, api_script_path, voicecraft_repo_path):
    logging.info(f"Running VoiceCraft API server in {env_name}...")
    try:
        # Change to the VoiceCraft repository directory
        os.chdir(voicecraft_repo_path)
        
        voicecraft_server_command = [f'{conda_path}\\Scripts\\conda.exe', 'run', '-n', env_name, 'python', api_script_path]
        subprocess.Popen(voicecraft_server_command, creationflags=subprocess.CREATE_NEW_CONSOLE)
    except Exception as e:
        logging.error(f"Failed to run VoiceCraft API server in {env_name}")
        logging.error(f"Error message: {str(e)}")
        logging.error(traceback.format_exc())
        raise

def check_voicecraft_server_online(url, max_attempts=30, wait_interval=10):
    attempt = 1
    while attempt <= max_attempts:
        try:
            logging.info(f"Checking if VoiceCraft server is online at {url} (Attempt {attempt}/{max_attempts})...")
            response = requests.get(url)
            if response.status_code == 200:
                logging.info("VoiceCraft server is online.")
                return True
        except requests.exceptions.RequestException as e:
            logging.warning(f"VoiceCraft server is not online. Waiting... (Attempt {attempt}/{max_attempts})")
        
        time.sleep(wait_interval)
        attempt += 1
    
    logging.error("VoiceCraft server failed to come online within the specified attempts.")
    return False

def download_pretrained_models(repo_path):
    """ Download necessary model files into structured directories using curl. """
    pretrained_models_dir = os.path.join(repo_path, 'pretrained_models')
    os.makedirs(pretrained_models_dir, exist_ok=True)

    # Model specific settings
    model_name = "VoiceCraft_gigaHalfLibri330M_TTSEnhanced_max16s"
    model_dir = os.path.join(pretrained_models_dir, model_name)
    os.makedirs(model_dir, exist_ok=True)

    base_url = f"https://huggingface.co/pyp1/{model_name}/resolve/main/"
    config_url = f"{base_url}config.json"
    model_safetensors_url = f"{base_url}model.safetensors"
    encodec_url = "https://huggingface.co/pyp1/VoiceCraft/resolve/main/encodec_4cb2048_giga.th"

    config_path = os.path.join(model_dir, "config.json")
    model_safetensors_path = os.path.join(model_dir, "model.safetensors")
    encodec_path = os.path.join(pretrained_models_dir, "encodec_4cb2048_giga.th")

    # Download config.json using curl
    if not os.path.exists(config_path):
        logging.info(f"Downloading config.json for {model_name}...")
        run_command(['curl', '-L', config_url, '-o', config_path])

    # Download model.safetensors using curl
    if not os.path.exists(model_safetensors_path):
        logging.info(f"Downloading model.safetensors for {model_name}...")
        run_command(['curl', '-L', model_safetensors_url, '-o', model_safetensors_path])

    # Download encodec model using curl
    if not os.path.exists(encodec_path):
        logging.info("Downloading encodec_4cb2048_giga.th...")
        run_command(['curl', '-L', encodec_url, '-o', encodec_path])

def replace_files(repo_path, file_mappings):
    for src_file, dest_file in file_mappings.items():
        src_path = os.path.join(repo_path, src_file)
        dest_path = os.path.join(repo_path, dest_file)
        try:
            shutil.copy2(src_path, dest_path)
            logging.info(f"Replaced file: {dest_file}")
        except Exception as e:
            logging.error(f"Failed to replace file: {dest_file}")
            logging.error(f"Error message: {str(e)}")
            logging.error(traceback.format_exc())
            raise

def main():
    voicecraft_path = os.path.join(os.getcwd(), 'VoiceCraft_API')
    
    if not os.path.exists(voicecraft_path):
        # Check and install dependencies
        install_dependencies()
        
        os.makedirs(voicecraft_path, exist_ok=True)
        logging.info(f"Created VoiceCraft_API folder at {voicecraft_path}")

        # Clone repository
        logging.info("Cloning VoiceCraft_API repository...")
        try:
            run_command(['git', 'clone', 'https://github.com/lukaszliniewicz/VoiceCraft_API.git', voicecraft_path])
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to clone VoiceCraft_API repository")
            logging.error(f"Error message: {str(e)}")
            raise

        # Install Miniconda
        conda_path = os.path.join(voicecraft_path, 'conda')
        install_conda(conda_path)

        # Check if conda is installed correctly
        if not check_conda(conda_path):
            logging.error("Conda installation failed. Please check the installation logs.")
            return

        voicecraft_env_name = 'voicecraft_api_installer'

        if not os.path.exists(os.path.join(conda_path, 'envs', voicecraft_env_name)):
            # Create voicecraft_api_installer environment
            create_conda_env(conda_path, voicecraft_env_name, '3.9.16')
            
            # Install VoiceCraft API dependencies
            install_requirements(conda_path, voicecraft_env_name, os.path.join(voicecraft_path, 'requirements.txt'))
            install_voicecraft_api_dependencies(conda_path, voicecraft_env_name)
            download_mfa_models(conda_path, voicecraft_env_name)
            
            # Install audiocraft package
            install_audiocraft(conda_path, voicecraft_env_name, voicecraft_path)
        else:
            logging.info(f"Environment {voicecraft_env_name} already exists. Skipping installation.")

        # Replace files in the VoiceCraft repo
        file_mappings = {
            'audiocraft_windows/cluster.py': 'src/audiocraft/audiocraft/utils/cluster.py',
            'audiocraft_windows/environment.py': 'src/audiocraft/audiocraft/environment.py',
            'audiocraft_windows/checkpoint.py': 'src/audiocraft/audiocraft/utils/checkpoint.py'
        }
        replace_files(voicecraft_path, file_mappings)

        # Download pretrained models
        download_pretrained_models(voicecraft_path)
    else:
        logging.info("VoiceCraft_API folder exists. Skipping installation steps.")
        
    # Get the conda path
    conda_path = os.path.join(voicecraft_path, 'conda')

    # Run VoiceCraft API server
    api_script_path = os.path.join(voicecraft_path, 'api.py')
    run_voicecraft_api_server(conda_path, 'voicecraft_api_installer', api_script_path, voicecraft_path)
    
    # Wait for VoiceCraft server to come online
    voicecraft_server_url = 'http://127.0.0.1:8245/docs'
    if not check_voicecraft_server_online(voicecraft_server_url):
        logging.error("VoiceCraft server failed to come online. Exiting...")
        return
    
    logging.info("VoiceCraft API installation and server startup completed successfully.")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.error(f"An error occurred during execution: {str(e)}")
        logging.error(traceback.format_exc())
