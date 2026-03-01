from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import requests
import secrets
import time
from functools import wraps
import os
from dotenv import load_dotenv
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import concurrent.futures

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Security configurations
CORS(app)

# API configuration for both models
API_CONFIG = {
    'seedream4': {
        'url': 'https://ansh-apis.is-dev.org/api/seedream',
        'key': os.getenv('API_KEY_4', 'pak_x6uo_74gENxP0nq3pgadvJqfpT9aC0BY'),
        'model': '4',
        'name': 'Seedream 4.0'
    },
    'seedream5': {
        'url': 'https://ansh-apis.is-dev.org/api/seedream',
        'key': os.getenv('API_KEY_5', 'pak_x6uo_74gENxP0nq3pgadvJqfpT9aC0BY'),  # Same key works for both
        'model': '5',
        'name': 'Seedream 5.0'
    }
}

# Create session with retry strategy
def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Rate limiting
RATE_LIMIT = {}
MAX_REQUESTS_PER_IP = 20
RATE_LIMIT_WINDOW = 3600

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        current_time = time.time()
        
        if ip in RATE_LIMIT:
            requests_count, first_request_time = RATE_LIMIT[ip]
            if current_time - first_request_time < RATE_LIMIT_WINDOW:
                if requests_count >= MAX_REQUESTS_PER_IP:
                    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
                RATE_LIMIT[ip] = (requests_count + 1, first_request_time)
            else:
                RATE_LIMIT[ip] = (1, current_time)
        else:
            RATE_LIMIT[ip] = (1, current_time)
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate')
def generate_page():
    return render_template('generate.html')

@app.route('/api-info')
def api_info():
    return render_template('api.html')

@app.route('/api/models', methods=['GET'])
def get_models():
    """Return available models"""
    return jsonify({
        'models': [
            {'id': '4', 'name': 'Seedream 4.0', 'description': 'Fast generation, good quality'},
            {'id': '5', 'name': 'Seedream 5.0', 'description': 'Higher quality, slower generation'}
        ]
    })

@app.route('/api/generate', methods=['POST'])
@rate_limit
def generate_image():
    logger.debug("Generate image endpoint called")
    
    try:
        # Get and validate data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        prompt = data.get('prompt', '').strip()
        model_id = data.get('model', '5')  # Default to model 5
        
        logger.debug(f"Prompt: {prompt}, Model: {model_id}")
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
            
        if len(prompt) > 1000:
            return jsonify({'error': 'Prompt too long. Maximum 1000 characters.'}), 400
        
        # Select model configuration
        if model_id == '4':
            model_config = API_CONFIG['seedream4']
        else:
            model_config = API_CONFIG['seedream5']
        
        # Sanitize prompt
        sanitized_prompt = ''.join(char for char in prompt if ord(char) < 128)
        
        # Make request to API
        logger.debug(f"Calling {model_config['name']} API")
        
        session = create_session()
        
        try:
            response = session.get(
                model_config['url'],
                params={
                    'key': model_config['key'],
                    'model': model_config['model'],
                    'prompt': sanitized_prompt
                },
                timeout=120
            )
            
            logger.debug(f"API response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.debug(f"Response data: {data}")
                    
                    if 'image' in data:
                        return jsonify({
                            'success': True,
                            'image_url': data['image'],
                            'credit': data.get('credit', 'anshapi'),
                            'model': model_config['name'],
                            'model_id': model_id
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'error': 'Invalid API response format'
                        }), 500
                except ValueError as e:
                    logger.error(f"JSON parse error: {e}")
                    return jsonify({
                        'success': False,
                        'error': 'Invalid JSON response from API'
                    }), 500
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return jsonify({
                    'success': False,
                    'error': f'API error: {response.status_code}'
                }), response.status_code
                
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            return jsonify({
                'success': False,
                'error': 'Request timeout. The API is taking longer than expected. Please try again.'
            }), 504
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return jsonify({
                'success': False,
                'error': 'Connection error. Please check your internet connection.'
            }), 503
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Request failed: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/compare', methods=['POST'])
@rate_limit
def compare_models():
    """Generate images with both models for comparison"""
    logger.debug("Compare models endpoint called")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        prompt = data.get('prompt', '').strip()
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        sanitized_prompt = ''.join(char for char in prompt if ord(char) < 128)
        session = create_session()
        results = {}
        
        # Generate with both models in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_to_model = {}
            
            for model_id, config in API_CONFIG.items():
                future = executor.submit(
                    session.get,
                    config['url'],
                    params={
                        'key': config['key'],
                        'model': config['model'],
                        'prompt': sanitized_prompt
                    },
                    timeout=120
                )
                future_to_model[future] = config['name']
            
            for future in concurrent.futures.as_completed(future_to_model):
                model_name = future_to_model[future]
                try:
                    response = future.result()
                    if response.status_code == 200:
                        data = response.json()
                        if 'image' in data:
                            results[model_name] = {
                                'success': True,
                                'image_url': data['image'],
                                'credit': data.get('credit', 'anshapi')
                            }
                        else:
                            results[model_name] = {
                                'success': False,
                                'error': 'Invalid response format'
                            }
                    else:
                        results[model_name] = {
                            'success': False,
                            'error': f'HTTP {response.status_code}'
                        }
                except Exception as e:
                    results[model_name] = {
                        'success': False,
                        'error': str(e)
                    }
        
        return jsonify({
            'success': True,
            'prompt': prompt,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Compare error: {str(e)}")
        return jsonify({'error': 'Comparison failed'}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)