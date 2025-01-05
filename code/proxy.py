from flask import Flask, request, jsonify
import pymysql
import random
import json
import threading
from collections import defaultdict
import logging
import subprocess

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load configuration from JSON file
with open("config.json", "r") as config_file:
    config = json.load(config_file)

manager_ip = config["manager_ip"]
worker_ips = config["worker_ips"]

# MySQL credentials
db_user = "replica_user"
db_password = "1234"
db_name = "sakila"

# Track active requests per worker (includes manager for writes and direct reads)
worker_request_count = defaultdict(int)
for ip in worker_ips:
    worker_request_count[ip] = 0
worker_request_count[manager_ip] = 0  # Include manager_ip explicitly

# Lock for thread safety
lock = threading.Lock()


def measure_ping(ip):
    """
    Measures the ping response time to a specific IP address on MacOS.
    Returns the average ping time in milliseconds or a high value if unreachable.
    """
    try:
        # Use ping to measure response time (adjusted for MacOS)
        result = subprocess.run(["ping", "-c", "1", ip], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            # Extract the time from the ping output
            for line in result.stdout.split('\n'):
                if "time=" in line:
                    return float(line.split("time=")[1].split(" ")[0])  # Extract time in ms
        return float('inf')  # Return high value if ping fails
    except Exception as e:
        logging.error(f"Ping to {ip} failed: {str(e)}")
        return float('inf')  # Return high value if exception occurs


def execute_query(target_ip, query):
    """
    Executes a MySQL query on the specified target IP.
    """
    try:
        connection = pymysql.connect(
            host=target_ip,
            user=db_user,
            password=db_password,
            database=db_name,
            port=3306  # MySQL port
        )
        with connection.cursor() as cursor:
            cursor.execute(query)
            if query.strip().lower().startswith("select"):
                result = cursor.fetchall()
            else:
                connection.commit()
                result = {"status": "success"}
        connection.close()
        return result
    except Exception as e:
        logging.error(f"Error executing query on {target_ip}: {str(e)}")
        return {"error": str(e)}


def get_least_busy_worker():
    """
    Selects the worker with the lowest request count.
    """
    with lock:
        return min(worker_request_count, key=worker_request_count.get)


def increment_worker_requests(ip):
    """
    Increments the request count for a worker.
    """
    with lock:
        worker_request_count[ip] += 1


def decrement_worker_requests(ip):
    """
    Decrements the request count for a worker.
    """
    with lock:
        worker_request_count[ip] -= 1


@app.route("/direct", methods=["POST", "GET", "PUT", "DELETE"])
def direct_hit():
    """
    Direct routing: All queries, including reads (SELECT) and writes, go to the manager.
    """
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "Query parameter is missing"}), 400

    # For direct access, both reads and writes go to the manager
    target_ip = manager_ip

    logging.info(f"Routing query to {target_ip}: {query}")

    increment_worker_requests(target_ip)
    try:
        result = execute_query(target_ip, query)
    finally:
        decrement_worker_requests(target_ip)
    return jsonify(result)


@app.route("/random", methods=["POST", "GET", "PUT", "DELETE"])
def random_hit():
    """
    Random routing: Reads go to a random worker, writes go to manager.
    """
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "Query parameter is missing"}), 400

    if query.strip().lower().startswith("select"):
        target_ip = random.choice(worker_ips)  # Random worker for reads
    else:
        target_ip = manager_ip  # Manager for writes

    logging.info(f"Routing query to {target_ip}: {query}")

    increment_worker_requests(target_ip)
    try:
        result = execute_query(target_ip, query)
    finally:
        decrement_worker_requests(target_ip)
    return jsonify(result)


@app.route("/customized", methods=["POST", "GET", "PUT", "DELETE"])
def customized_hit():
    """
    Customized routing: Reads go to the server with the shortest ping time.
    Writes always go to the manager.
    """
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "Query parameter is missing"}), 400

    if query.strip().lower().startswith("select"):
        # Measure ping for all workers and select the one with the shortest response time
        ping_times = {ip: measure_ping(ip) for ip in worker_ips}
        target_ip = min(ping_times, key=ping_times.get)  # Choose the worker with the shortest ping
        logging.info(f"Ping times: {ping_times}")
    else:
        target_ip = manager_ip  # Manager for writes

    logging.info(f"Routing query to {target_ip}: {query}")

    increment_worker_requests(target_ip)
    try:
        result = execute_query(target_ip, query)
    finally:
        decrement_worker_requests(target_ip)
    return jsonify(result)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
