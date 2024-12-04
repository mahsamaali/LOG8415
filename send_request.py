import requests
import concurrent.futures

# Define the orchestrator URL
# Define the orchestrator URL
def test_orchestrator(orchestrator_ip, num_requests, max_workers):
    """
    Test the orchestrator by sending requests concurrently.

    Args:
    orchestrator_ip (str): The IP or URL of the orchestrator.
    num_requests (int): The number of requests to send.
    max_workers (int): Number of concurrent workers.
    """
    orchestrator_url = f'http://{orchestrator_ip}/new_request'

    # Function to send a single request to the orchestrator
    def send_request(request_id):
        data = {
            "input_text": f"Request number {request_id}"
        }

        try:
            # Send the POST request
            response = requests.post(orchestrator_url, json=data)

            # Check if the request was successful
            if response.status_code == 200:
                # Log the full response content from the orchestrator
                return f"Request {request_id} successful! Response: {response.json()}"
            else:
                return f"Request {request_id} failed with status code: {response.status_code}"
        except requests.exceptions.RequestException as e:
            return f"Request {request_id} failed due to an error: {e}"

    # Using ThreadPoolExecutor to send requests concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_request = {executor.submit(send_request, i + 1): i for i in range(num_requests)}
        
        for future in concurrent.futures.as_completed(future_to_request):
            request_id = future_to_request[future]
            try:
                # Print the result of each request
                print(future.result())
            except Exception as exc:
                print(f"Request {request_id} generated an exception: {exc}")