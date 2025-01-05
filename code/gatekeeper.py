from flask import Flask, request, jsonify
import requests
import json
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load Trusted Host configuration
with open("config_trust.json", "r") as config_file:
    config = json.load(config_file)

trusted_host_ip = config["trust_ip"]
TRUSTED_HOST_URL = f"http://{trusted_host_ip}:8000/process"

@app.route("/validate", methods=["POST"])
def validate_request():
    """
    Validates incoming client requests and forwards them to the Trusted Host.

    Request format:
    {
        "type": "read" or "write",
        "query": "SQL query string",
        "strategy": "direct", "random", or "customized"
    }

    Returns:
        - Success response from the Trusted Host.
        - Error response if validation or forwarding fails.
    """
    data = request.json

    # Validate input
    if not data:
        return jsonify({"error": "No data provided"}), 400

    query_type = data.get("type")
    query = data.get("query")
    strategy = data.get("strategy", "direct")  # Default strategy is direct

    if query_type not in ["read", "write"]:
        return jsonify({"error": "Invalid query type"}), 400

    if not query:
        return jsonify({"error": "No query provided"}), 400

    if strategy not in ["direct", "random", "customized"]:
        return jsonify({"error": "Invalid strategy"}), 400

    # Forward the validated request to the Trusted Host
    try:
        logging.info(f"Forwarding validated request to Trusted Host: {data}")
        response = requests.post(TRUSTED_HOST_URL, json=data)
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to reach Trusted Host: {str(e)}")
        return jsonify({"error": f"Failed to reach Trusted Host: {str(e)}"}), 500


if __name__ == "__main__":
    # Run the Flask app
    app.run(host="0.0.0.0", port=8000)
