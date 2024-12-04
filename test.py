from benchmark import benchmark_requests
from benchmark import warm_up


gatekeeper_public_ip='54.172.160.41'
gatekeeper_url = f"http://{gatekeeper_public_ip}:8000/validate"
read_query = "SELECT * FROM actor LIMIT 10;"
write_query = "INSERT INTO actor (first_name, last_name, last_update) VALUES ('JOHN', 'DOE', NOW());"

# # Number of requests to send
num_requests = 1000

# # Payload templates
read_payload_template = {"type": "read", "query": read_query, "strategy": ""}
write_payload_template = {"type": "write", "query": write_query, "strategy": ""}

strategies = ["random", "customized","direct"]
for strategy in strategies:
    print(f"--- Benchmarking Read Strategy: {strategy} ---")
    read_payload = {**read_payload_template, "strategy": strategy}
    read_results, read_time = benchmark_requests(gatekeeper_url, read_payload, num_requests)
    print(f"Read Requests Completed in {read_time:.2f} seconds")
    print(f"Success: {sum(1 for r in read_results if 'error' not in r)}")
    print(f"Errors: {sum(1 for r in read_results if 'error' in r)}\n")

    print(f"--- Benchmarking Write Strategy: {strategy} ---")
    write_payload = {**write_payload_template, "strategy": strategy}
    write_results, write_time = benchmark_requests(gatekeeper_url, write_payload, num_requests)
    print(f"Write Requests Completed in {write_time:.2f} seconds")
    print(f"Success: {sum(1 for r in write_results if 'error' not in r)}")
    print(f"Errors: {sum(1 for r in write_results if 'error' in r)}\n")

# warm_up(gatekeeper_url)
# read_query = "SELECT * FROM actor LIMIT 10;"
# write_query = "INSERT INTO actor (first_name, last_name, last_update) VALUES ('WARMUP', 'TEST', NOW());"
    
# warm_up(gatekeeper_url, read_query, write_query)
# #print("Warm-up completed. Ready for benchmarking.")

# # Predefined queries
# # read_query = "SELECT * FROM actor LIMIT 10;"
# # write_query = "INSERT INTO actor (first_name, last_name, last_update) VALUES ('JOHN', 'DOE', NOW());"
# # # Number of requests to send
# # num_requests = 10

# # Payload templates
# # read_payload_template = {"type": "read", "query": read_query, "strategy": ""}
# # write_payload_template = {"type": "write", "query": write_query, "strategy": ""}

# # # Benchmark each strategy
# # strategies = ["direct", "random", "customized"]
# # for strategy in strategies:
# #     print(f"--- Benchmarking Read Strategy: {strategy} ---")
# #     read_payload = {**read_payload_template, "strategy": strategy}
# #     read_results, read_time = benchmark_requests(gatekeeper_url, read_payload, num_requests)
# #     print(f"Read Requests Completed in {read_time:.2f} seconds")
# #     print(f"Success: {sum(1 for r in read_results if 'error' not in r)}")
# #     print(f"Errors: {sum(1 for r in read_results if 'error' in r)}\n")

# #     print(f"--- Benchmarking Write Strategy: {strategy} ---")
# #     write_payload = {**write_payload_template, "strategy": strategy}
# #     write_results, write_time = benchmark_requests(gatekeeper_url, write_payload, num_requests)
# #     print(f"Write Requests Completed in {write_time:.2f} seconds")
# #     print(f"Success: {sum(1 for r in write_results if 'error' not in r)}")
# #     print(f"Errors: {sum(1 for r in write_results if 'error' in r)}\n")


# # Number of requests to send
# num_requests = 1000

# # Payload templates
# read_payload_template = {"type": "read", "query": read_query, "strategy": ""}
# write_payload_template = {"type": "write", "query": write_query, "strategy": ""}

# strategies = ["random", "customized","direct"]
# for strategy in strategies:
#     print(f"--- Benchmarking Read Strategy: {strategy} ---")
#     read_payload = {**read_payload_template, "strategy": strategy}
#     read_results, read_time = benchmark_requests(gatekeeper_url, read_payload, num_requests)
#     print(f"Read Requests Completed in {read_time:.2f} seconds")
#     print(f"Success: {sum(1 for r in read_results if 'error' not in r)}")
#     print(f"Errors: {sum(1 for r in read_results if 'error' in r)}\n")

#     print(f"--- Benchmarking Write Strategy: {strategy} ---")
#     write_payload = {**write_payload_template, "strategy": strategy}
#     write_results, write_time = benchmark_requests(gatekeeper_url, write_payload, num_requests)
#     print(f"Write Requests Completed in {write_time:.2f} seconds")
#     print(f"Success: {sum(1 for r in write_results if 'error' not in r)}")
#     print(f"Errors: {sum(1 for r in write_results if 'error' in r)}\n")


