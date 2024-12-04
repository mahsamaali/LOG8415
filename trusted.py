from flask import Flask, request, jsonify
import requests
import json
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load Proxy configuration
with open("config_trust.json", "r") as config_file:
    config = json.load(config_file)

proxy_ip = config["proxy_ip"]
PROXY_URL = f"http://{proxy_ip}:8000"

@app.route("/process", methods=["POST"])
def process_request():
    """
    Processes requests from the Gatekeeper and forwards them to the Proxy.

    Request format:
    {
        "type": "read" or "write",
        "query": "SQL query string",
        "strategy": "direct", "random", or "customized"
    }

    Returns:
        - Success response from the Proxy.
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

    # Map strategy to Proxy endpoint
    endpoint = f"/{strategy}"

    # Forward the query to the Proxy
    try:
        logging.info(f"Forwarding query to Proxy {PROXY_URL}{endpoint}: {query}")
        response = requests.post(f"{PROXY_URL}{endpoint}", params={"query": query})
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to reach Proxy: {str(e)}")
        return jsonify({"error": f"Failed to reach Proxy: {str(e)}"}), 500


if __name__ == "__main__":
    # Run the Flask app
    app.run(host="0.0.0.0", port=8000)
