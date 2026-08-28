import dotenv
import logging
from pathlib import Path
import requests
import socket

personal_token = dotenv.get_key('.env', 'AUDD_API_TOKEN') or ''
API_URL='https://api.audd.io/'
API_TOKENS=[t for t in ['test', personal_token] if t]

logger = logging.getLogger(__name__)


def is_online(host="8.8.8.8", port=53, timeout=2):
    """ A fast, lightweight Internet connectivity check\n
    Creates a TCP socket stream to a DNS server (host) and attempts a connection on the port
    
    Args:
        host: DNS server host to open connection to (default: 8.8.8.8 (Google))
        port: Port on which to connect to server (default: 53)
        
    Returns:
        True is connection was successful, False otherwise
    """
    # Create TCP socket stream
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        
        result = s.connect_ex((host, port))
        
        if result == 0:
            return True
        return False


def send_to_api(filename: Path):
    """ Sends an audio file to the AudD API for recognition
    
    Args:
        filename: Path to the audio file to be sent for recognition
    
    Returns:
    - status: True if API request was successful, False otherwise
    - result: Result text or API error message if the request failed
    """
    payload={
        'return': 'apple_music,spotify',
        'api_token': ''
    }
    HTTP_TIMEOUT= 30
    for token in API_TOKENS:
        response: requests.Response | None = None
        try:
            payload['api_token'] = token
            with open(filename, 'rb') as audio_file:
                file = {'file': audio_file}
                logger.info(f"Uploading '{filename.name}' to AudD API...")
                response = requests.post(
                    API_URL,
                    data=payload,
                    files=file,
                    timeout=HTTP_TIMEOUT
                )
                response.raise_for_status()  # Raise an http error for bad responses
              
            data = response.json()

            if data.get('status') == 'error':
                error_msg = data.get('error', {}).get('error_message', 'Unknown error message')
                error_code = data.get('error_code', 'Unknown error code')
                if error_code == 901:
                    logger.error("Test API token limit reached. Switching to personal API token.")
                    continue
                logger.error(f"\nAPI Error: {error_msg} (Code: {error_code})")
                return (False, error_msg)
            
            elif data.get('status') == 'success':
                song_info= data.get('result', {})
                logger.info("\n---Song recognised successfully!---")
                logger.info(f"Title: {str(song_info.get('title', 'Unknown'))}")
                logger.info(f"Artist: {str(song_info.get('artist', 'Unknown'))}")
                logger.info(f"Album: {str(song_info.get('album', 'Unknown'))}")
                logger.info(f"Release Date: {str(song_info.get('release_date', 'Unknown'))}")
                logger.info(f"Label: {str(song_info.get('label', 'Unknown'))}")
                logger.info(f"Song Link: {str(song_info.get('song_link', 'Unknown'))}")
                return (True, song_info)
        
        except requests.exceptions.HTTPError:
            if response:
                logger.error(f"HTTP error occurred: {response.status_code} - {response.text}", exc_info=True)
        except FileNotFoundError:
            logger.error(f"Error: The file '{filename}' was not found. Check your file path.", exc_info=True)
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
            logger.error(f"Error: The request timed out while uploading the file. Check your Internet connection.", exc_info=True)
        except requests.exceptions.RequestException as err:
            logger.error(f"An error occured: {err}", exc_info=True)
    logger.error("All API tokens exhausted. Upload failed.")
    return (False, "All API tokens exhausted")

