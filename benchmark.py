import requests
import concurrent.futures
import time



def send_request(gatekeeper_url, payload):
    """
    Sends a POST request to the Gatekeeper with the given payload.

    Args:
        gatekeeper_url (str): The Gatekeeper's URL.
        payload (dict): The request payload containing query type, query, and strategy.

    Returns:
        dict: The JSON response or an error message.
    """
    try:
        response = requests.post(gatekeeper_url, json=payload)
        response.raise_for_status()  # Raise HTTPError for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
    


def benchmark_requests(gatekeeper_url, payload, num_requests):
    """
    Benchmarks a specified number of requests to the Gatekeeper.

    Args:
        gatekeeper_url (str): The Gatekeeper's URL.
        payload (dict): The request payload containing query type, query, and strategy.
        num_requests (int): The number of requests to send.

    Returns:
        tuple: (list of responses, elapsed time in seconds)
    """
    results = []
    start_time = time.time()

    # Use ThreadPoolExecutor for concurrency
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit tasks for execution
        futures = [executor.submit(send_request, gatekeeper_url, payload) for _ in range(num_requests)]
        # Collect results as they complete
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    elapsed_time = time.time() - start_time
    return results, elapsed_time



# def warm_up(gatekeeper_url, read_query, write_query):
#     """
#     Sends warm-up requests to the Gatekeeper for both read and write operations.

#     Args:
#         gatekeeper_url (str): URL of the Gatekeeper's validate endpoint.
#         read_query (str): Read query for warm-up.
#         write_query (str): Write query for warm-up.

#     Returns:
#         None
#     """
#     # Payload templates
#     read_payload = {"type": "read", "query": read_query, "strategy": "direct"}
#     write_payload = {"type": "write", "query": write_query, "strategy": "direct"}

#     # Warm-up read requests
#     print("Warming up with read requests...")
#     for _ in range(10):
#         try:
#             response = requests.post(gatekeeper_url, json=read_payload, timeout=10)
#             print(f"Read warm-up response: {response.status_code}, {response.json()}")
#         except Exception as e:
#             print(f"Read warm-up failed: {e}")

#     # Warm-up write requests
#     print("Warming up with write requests...")
#     for _ in range(10):
#         try:
#             response = requests.post(gatekeeper_url, json=write_payload, timeout=10)
#             print(f"Write warm-up response: {response.status_code}, {response.json()}")
#         except Exception as e:
#             print(f"Write warm-up failed: {e}")

#     # Wait for stabilization
#     print("Waiting for stabilization...")
#     time.sleep(5)


def warm_up(gatekeeper_url):
    """
    Sends warm-up requests to the Gatekeeper for both write and read operations.

    Args:
        gatekeeper_url (str): URL of the Gatekeeper's validate endpoint.

    Returns:
        None
    """
    # Insert three records with different strategies
    write_queries = [
        "INSERT INTO actor (first_name, last_name, last_update) VALUES ('JOHN', 'DOE', NOW());",
        "INSERT INTO actor (first_name, last_name, last_update) VALUES ('JANE', 'SMITH', NOW());",
        "INSERT INTO actor (first_name, last_name, last_update) VALUES ('ALICE', 'JOHNSON', NOW());"
    ]
    
    strategies = ["direct", "random", "customized"]
    
    print("Warming up with write requests...")
    for query, strategy in zip(write_queries, strategies):
        payload = {"type": "write", "query": query, "strategy": strategy}
        try:
            response = requests.post(gatekeeper_url, json=payload, timeout=10)
            print(f"Write warm-up response: {response.status_code}, {response.json()}")
        except Exception as e:
            print(f"Write warm-up failed: {e}")

    # Read back the inserted data
    read_query = "SELECT * FROM actor WHERE first_name IN ('JOHN', 'JANE', 'ALICE');"
    read_payload = {"type": "read", "query": read_query, "strategy": "direct"}

    print("Warming up with read request...")
    try:
        response = requests.post(gatekeeper_url, json=read_payload, timeout=10)
        print(f"Read warm-up response: {response.status_code}, {response.json()}")
    except Exception as e:
        print(f"Read warm-up failed: {e}")
