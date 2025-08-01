import os
import json
import sqlite3
from flask import Flask, render_template, request, jsonify, g, abort
from functools import wraps
import requests

# --- App Initialization ---
app = Flask(__name__)
app.config['DATABASE'] = os.path.join(os.getcwd(), 'database', 'listings.db')
app.config['APP_PASSWORD'] = os.environ.get('APP_PASSWORD', 'default_password')

# --- Database Setup ---
def get_db():
    if 'db' not in g:
        db_path = app.config['DATABASE']
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def create_schema_sql_if_not_exists():
    schema_content = """
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_info TEXT NOT NULL,
        title TEXT NOT NULL,
        bullets TEXT NOT NULL,
        description TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    if not os.path.exists('schema.sql'):
        with open('schema.sql', 'w') as f:
            f.write(schema_content)

# --- Password Protection ---
def require_password(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f"Bearer {app.config['APP_PASSWORD']}":
            # For API calls, return 401
            if request.path.startswith('/api/'):
                 return jsonify({"error": "Unauthorized"}), 401
            # For page loads, render login
            return render_template('login.html')
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/')
@require_password
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == app.config['APP_PASSWORD']:
            # In a real app, you'd use secure sessions.
            # For this simple tool, we'll pass it in the header via JS.
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "Incorrect password"}), 401
    return render_template('login.html')

@app.route('/api/generate', methods=['POST'])
@require_password
def generate_listing():
    data = request.json
    product_info = data.get('product_info')
    api_url = data.get('api_url')
    api_key = data.get('api_key')
    model_name = data.get('model_name')
    master_prompt = data.get('master_prompt')

    if not all([product_info, api_url, api_key, model_name, master_prompt]):
        return jsonify({"error": "Missing required fields for generation."}), 400

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    prompt_with_product_info = master_prompt.format(product_info=product_info)
    
    payload = {
        "model": model_name,
        "prompt": prompt_with_product_info,
        "stream": False # Ensure we get a single JSON response
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        
        # The expected response from the LLM is a JSON string.
        # We parse the content of the response, and then parse that JSON string.
        llm_response_content = response.json().get('response', '{}')
        generated_data = json.loads(llm_response_content)

        return jsonify({
            "title": generated_data.get("title", ""),
            "bullets": generated_data.get("bullets", []),
            "description": generated_data.get("description", "")
        })

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API request failed: {str(e)}"}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse LLM response. Ensure it returns valid JSON."}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@app.route('/api/save', methods=['POST'])
@require_password
def save_listing():
    data = request.json
    db = get_db()
    db.execute(
        'INSERT INTO listings (product_info, title, bullets, description) VALUES (?, ?, ?, ?)',
        (data['product_info'], data['title'], json.dumps(data['bullets']), data['description'])
    )
    db.commit()
    return jsonify({"success": True, "message": "Listing saved successfully."})

@app.route('/api/history', methods=['GET'])
@require_password
def get_history():
    db = get_db()
    cursor = db.execute('SELECT * FROM listings ORDER BY created_at DESC')
    listings = cursor.fetchall()
    # Convert rows to dictionaries to be jsonified
    return jsonify([dict(row) for row in listings])

# --- Main Execution ---
if __name__ == '__main__':
    create_schema_sql_if_not_exists()
    # Initialize the database if it doesn't exist
    if not os.path.exists(app.config['DATABASE']):
        init_db()
    app.run(host='0.0.0.0', port=5001, debug=True)