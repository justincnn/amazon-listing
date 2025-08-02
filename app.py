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
    db = get_db()
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
    db.cursor().executescript(schema_content)
    db.commit()

@app.before_first_request
def setup():
    # Create the database and tables if they don't exist
    db_path = app.config['DATABASE']
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path))
    
    # This will create the db file and tables if they don't exist
    with app.app_context():
        init_db()

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
            return render_template('index.html')
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
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
@require_password
def generate_listing():
    data = request.json
    product_info = data.get('product_info')
    api_url = data.get('api_url')
    api_key = data.get('api_key')
    model_name = data.get('model_name')
    master_prompt = data.get('master_prompt')
    field_to_generate = data.get('field_to_generate') # New field

    if not all([product_info, api_url, api_key, model_name, master_prompt, field_to_generate]):
        return jsonify({"error": "Missing required fields for generation."}), 400

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # The master_prompt from the frontend should now contain the product info
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": master_prompt}
        ],
        # "response_format": {"type": "json_object"}, # Temporarily disable to allow for plain text responses
        "stream": False
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        
        # The expected response from the LLM is a JSON string.
        # We parse the content of the response, and then parse that JSON string.
        # Standard OpenAI API response structure
        llm_response_content = response.json()['choices'][0]['message']['content']
        
        # Clean the response content by removing markdown code block fences
        if llm_response_content.startswith("```json"):
            llm_response_content = llm_response_content[7:]
        if llm_response_content.endswith("```"):
            llm_response_content = llm_response_content[:-3]
        
        llm_response_content = llm_response_content.strip()

        # Attempt to parse the cleaned response as JSON
        generated_data = json.loads(llm_response_content)

        # Handle different structures for 'bullets'
        if field_to_generate == 'bullets':
            if isinstance(generated_data, list):
                # Case 1: The entire response is a JSON array of bullets
                return jsonify({'bullets': generated_data})
            elif isinstance(generated_data, dict) and 'bullets' in generated_data:
                # Case 2: The response is a JSON object with a 'bullets' key
                return jsonify({'bullets': generated_data['bullets']})
        
        # Handle other fields or fall through if 'bullets' structure is unexpected
        if isinstance(generated_data, dict) and field_to_generate in generated_data:
             return jsonify({field_to_generate: generated_data[field_to_generate]})

        # If we reach here, the structure is not what we expected
        return jsonify({"error": f"LLM response for '{field_to_generate}' was not in the expected format."}), 500

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API request failed: {str(e)}"}), 500
    except json.JSONDecodeError:
        # If JSON parsing fails, it might be a plain text response.
        if field_to_generate == 'bullets':
            # If we were expecting bullets, try to parse the text as a list of lines.
            bullets = [b.strip() for b in llm_response_content.strip().split('\n') if b.strip()]
            return jsonify({'bullets': bullets})
        else:
            # Otherwise, return the plain text as is, wrapped in the expected field.
            return jsonify({
                field_to_generate: llm_response_content
            })
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

@app.route('/api/history/<int:id>', methods=['DELETE'])
@require_password
def delete_listing(id):
    db = get_db()
    db.execute('DELETE FROM listings WHERE id = ?', (id,))
    db.commit()
    return jsonify({"success": True, "message": "Listing deleted."})

@app.route('/api/history/export', methods=['GET'])
@require_password
def export_listings():
    db = get_db()
    cursor = db.execute('SELECT * FROM listings ORDER BY created_at DESC')
    listings = cursor.fetchall()
    
    # Create a CSV in memory
    import csv
    import io
    from flask import Response

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['id', 'product_info', 'title', 'bullets', 'description', 'created_at'])
    
    # Write rows
    for row in listings:
        writer.writerow([row['id'], row['product_info'], row['title'], row['bullets'], row['description'], row['created_at']])
    
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=listings_history.csv"}
    )

# --- Main Execution ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)