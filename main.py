#aws library
import boto3
import json
import time
#import vpc,subnet_id,create_security_group
from netwrok_connection import get_vpc,get_subnet_by_vpc_and_az,create_security_group,configure_trusted_host_security_group
#securate security groups
from netwrok_connection import update_security_group_rules
#configure_mysql_security_group
#keypair and create isntaces
from create_instances import create_key_pair,create_instances
#configure servers
from run_code import install_mysql,configure_manager,configure_worker,get_private_ip,build_images,configure_server
from run_code import configure_iptables_workers,configure_iptables_manager,configure_iptables_proxy,configure_iptables_trusted,configure_iptables_gatekeeper
#benchmarking
from benchmark import benchmark_requests,warm_up
#terminate ressources
from terminate_resources import terminate_all_instances,delete_all_security_groups


def write_json(path):
    with open(path, "w") as config_file:
        json.dump(config_data, config_file, indent=4)

# Creating an EC2 client
ec2 = boto3.client('ec2',region_name='us-east-1')



#1. get VPC
vpc_id=get_vpc(ec2=ec2)


#2. get subnet_id
availability_zone = 'us-east-1e'
subnet_ids_data=get_subnet_by_vpc_and_az(ec2=ec2,vpc_id= vpc_id, availability_zone=availability_zone)
print(subnet_ids_data[0]['SubnetId'])

subnet_id_1=subnet_ids_data[0]['SubnetId']
#3. create security_group
ports = [22, 3306]
securiy_group_id_sql=create_security_group(ec2=ec2,group_name='security_groups_sql',vpc_id=vpc_id,ports=ports)

#4. create keypair
#name of keypair
key_name = 'my-key-pair'
#path of keypair
key_file = f"./{key_name}.pem"
create_key_pair(ec2=ec2,key_name=key_name,key_file=key_file)

#5. create instance:

#ubuntu ami
ami_id = 'ami-0e86e20dae9224db8'


#CPU type
instance_type_micro='t2.micro'
#number of instances
nb_instances_micro=3


###############################Worker Part###############################################

# Step1: Create instances of sql & install mysql

all_instances_data =create_instances(ec2=ec2,ami_id=ami_id,key_name=key_name,
                                    subnet_id=subnet_id_1,security_group_id=securiy_group_id_sql,
                                    instance_type=instance_type_micro, 
                                    num_instances=nb_instances_micro,
                                    availability_zone=availability_zone,instance_name='mysql_instances')

for public_ip in all_instances_data:
    #install sql 
    install_mysql(ip_address=public_ip[1],username='ubuntu',private_key_path=key_file)


# Assign the first instance as manager
manager_instance_data = all_instances_data[0]
manager_ip = manager_instance_data[1]
print("Manger ip is",manager_ip)
#get private ip of manager
private_manger_ip=get_private_ip(ec2=ec2,instance_id=manager_instance_data[0])
#Assign for workers
workers_ips=[]
worker_instances_data = all_instances_data[1:]

private_worker_ips=[]
#configure manager instance
manager_data=configure_manager(ip_address=manager_ip,username='ubuntu',private_key_path=key_file)
#configure workers instance
for i, (worker_id, worker_ip) in enumerate(worker_instances_data):
    print(f"Configuring Worker {i + 1}: {worker_ip}")
    server_id = i + 2  # Start server-id from 2 for the first worker
    #get private ip of each worker
    private_worker_ips.append(get_private_ip(ec2=ec2,instance_id=worker_id))
    configure_worker(ip_address=worker_ip,username='ubuntu',private_key_path=key_file, manager_ip=private_manger_ip, 
                     file=manager_data['File'], position=manager_data['Position'],server_id=server_id )


############################################Saved private ips of workers and manager####################
# Save to a JSON file
config_data = {
    "manager_ip": private_manger_ip,
    "worker_ips": private_worker_ips
}

#save ip addresses
write_json(path="config.json")

print("Configuration saved to config.json")


############################################End of sql part####################################################

#Create a security group for  proxy
ports = [22,8000]
sg_proxy_id=create_security_group(ec2=ec2,group_name='security_proxy',vpc_id=vpc_id,ports=ports)
#CPU type
instance_type_large='t2.large'
#number of instances
nb_instances_large=1
#creat proxy instance
proxy_instances_data =create_instances(ec2=ec2,ami_id=ami_id,key_name=key_name,
                                    subnet_id=subnet_id_1,security_group_id=sg_proxy_id,
                                    instance_type=instance_type_large, 
                                    num_instances=nb_instances_large,
                                    availability_zone=availability_zone,instance_name='proxy')



# #get public_ip of proxy instance
proxy_public_ip=proxy_instances_data[0][1]

#get rpivate ip of proxy instance
proxy_private_ip=get_private_ip(ec2=ec2,instance_id=proxy_instances_data[0][0])

#buid docker image of proxy
#1. Build image of proxy.py with JSON file
dockerfiles = {
        "proxy": "Dockerfile",
    }
build_images(dockerfiles)

#configure instance of proxy
configure_server(ip_address=proxy_public_ip, username='ubuntu', private_key_path=key_file, docker_image_name='proxy')
#Create a security group for proxy
ports = [22, 8000,80,443]
sg_gatekeeper_id=create_security_group(ec2=ec2,group_name='security_groups_gatekeeper',vpc_id=vpc_id,ports=ports)
###################################################GateKeeper#############################################
#1. create gatekeeper instance 
gatekeeper_instances_data =create_instances(ec2=ec2,ami_id=ami_id,key_name=key_name,
                                    subnet_id=subnet_id_1,security_group_id=sg_gatekeeper_id,
                                    instance_type=instance_type_large, 
                                    num_instances=nb_instances_large,
                                    availability_zone=availability_zone,instance_name='gatekeeper')

#2. get public_ip of gatekeeper instance
gatekeeper_public_ip=gatekeeper_instances_data[0][1]
#3. get private ip of gatekeeper
gatekeeper_private_ip=get_private_ip(ec2=ec2,instance_id=gatekeeper_instances_data[0][0])
#4. create a security group of trusted host based on the  private ip of proxy
securiy_group_trusted_id=configure_trusted_host_security_group(ec2_client=ec2, vpc_id=vpc_id, gatekeeper_private_ip=gatekeeper_private_ip,
                                                            proxy_private_ip=proxy_private_ip)

#create trusted_host instance
trusted_instances_data =create_instances(ec2=ec2,ami_id=ami_id,key_name=key_name,
                                    subnet_id=subnet_id_1,security_group_id=securiy_group_trusted_id,
                                    instance_type=instance_type_large, 
                                    num_instances=nb_instances_large,
                                    availability_zone=availability_zone,instance_name='trusted_host')


#get private ip of trusted
trusted_private_ip = get_private_ip(ec2=ec2,instance_id=trusted_instances_data[0][0])

#get public ip of trusted
trusted_public_ip=trusted_instances_data[0][1]
#save private ip of proxy and trusted_host
#Save to a JSON file
config_data = {
    "trust_ip": trusted_private_ip,
    "proxy_ip": proxy_private_ip
}

#save ip addresses
write_json(path="config_trust.json")

#build docker image for trusted host
dockerfiles = {
        "trust": "Dockerfiletrust",
    }
build_images(dockerfiles)

configure_server(ip_address=trusted_public_ip, username='ubuntu', private_key_path=key_file, docker_image_name='trust')


#build docker image for trusted host

dockerfiles = {
        "gatekeeper": "Dockerfilegatekeeper",
    }
build_images(dockerfiles)
configure_server(ip_address=gatekeeper_public_ip, username='ubuntu', private_key_path=key_file, docker_image_name='gatekeeper')


#########################################################################Secure instances##########################################
#configure iptable for workers
for public_id in worker_instances_data:

    configure_iptables_workers(ip_address=public_id[1], username='ubuntu',
                                private_key_path=key_file, proxy_private_ip=proxy_private_ip,
                                manager_private_ip=private_manger_ip)


#configure iptable for manager
configure_iptables_manager(ip_address=manager_ip, username='ubuntu', 
                           private_key_path=key_file, proxy_private_ip=proxy_private_ip
                           , private_worker_ips=private_worker_ips)


#configure iptable for proxy
configure_iptables_proxy(ip_address=proxy_public_ip, username='ubuntu', private_key_path=key_file,
                          private_worker_ips=private_worker_ips, manager_private_ip=private_manger_ip)



#configure iptable for trusted
configure_iptables_trusted(ip_address=trusted_public_ip, username='ubuntu', private_key_path=key_file,
                            proxy_private_ip=proxy_private_ip, gatekeeper_private_ip=gatekeeper_private_ip)


#configure iptable for gatekeeper
configure_iptables_gatekeeper(ip_address=gatekeeper_public_ip, username='ubuntu', private_key_path=key_file,
                               proxy_private_ip=proxy_private_ip)
#############################################################security groups######################################
#mysql configuaration

# mysql_permissions = [
#     {
#         'Direction': 'inbound',
#         'IpProtocol': 'tcp',
#         'FromPort': 3306,
#         'ToPort': 3306,
#         'CidrIp': f'{proxy_private_ip}/32'
#     },
#        {
#         'Direction': 'inbound',
#         'IpProtocol': 'tcp',
#         'FromPort': 22,
#         'ToPort': 22,
#         'CidrIp': '0.0.0.0/0'  # Replace with your trusted public IP for SSH access
#     },
#     {
#         'Direction': 'outbound',
#         'IpProtocol': 'tcp',
#         'FromPort': 3306,
#         'ToPort': 3306,
#         'CidrIp': f'{proxy_private_ip}/32'
#     }
# ]
# #configure_security_group(ec2, sg_id, ip_permissions)
# update_security_group_rules(ec2=ec2,sg_id=securiy_group_id_sql,ip_permissions=mysql_permissions)


# #proxy permission
# proxy_permissions = [
#     # Inbound rule to allow traffic on port 8000 from Trusted Host
#     {
#         'Direction': 'inbound',
#         'IpProtocol': 'tcp',
#         'FromPort': 8000,
#         'ToPort': 8000,
#         'CidrIp': f'{trusted_private_ip}/32'  # Replace with the Trusted Host's private IP
#     },
#     # # Inbound rule to allow SSH access (port 22) from your trusted IP
#    {
#         'Direction': 'inbound',
#         'IpProtocol': 'tcp',
#         'FromPort': 22,
#         'ToPort': 22,
#         'CidrIp': '0.0.0.0/0'  # Replace with your trusted public IP for SSH access
#     },
#     # Outbound rule to respond to Trusted Host on port 8000
#     {
#         'Direction': 'outbound',
#         'IpProtocol': 'tcp',
#         'FromPort': 8000,
#         'ToPort': 8000,
#         'CidrIp': f'{trusted_private_ip}/32'  # Replace with the Trusted Host's private IP
#     }
# ]
# update_security_group_rules(ec2=ec2,sg_id=sg_proxy_id,ip_permissions=proxy_permissions)


# trusted_permissions = [
#     # Inbound rule to allow traffic on port 8000 from Trusted Host
#     {
#         'Direction': 'inbound',
#         'IpProtocol': 'tcp',
#         'FromPort': 8000,
#         'ToPort': 8000,
#         'CidrIp': f'{gatekeeper_private_ip}/32'  # Replace with the Trusted Host's private IP
#     },
#     # # Inbound rule to allow SSH access (port 22) from your trusted IP
#     {
#         'Direction': 'inbound',
#         'IpProtocol': 'tcp',
#         'FromPort': 22,
#         'ToPort': 22,
#         'CidrIp': '0.0.0.0/0'  # Replace with your trusted public IP for SSH access
#     },
#     # Outbound rule to respond to Trusted Host on port 8000
#     {
#         'Direction': 'outbound',
#         'IpProtocol': 'tcp',
#         'FromPort': 8000,
#         'ToPort': 8000,
#         'CidrIp': f'{proxy_private_ip}/32'  # Replace with the Trusted Host's private IP
#     }
# ]

# update_security_group_rules(ec2=ec2,sg_id=securiy_group_trusted_id,ip_permissions=trusted_permissions)
#4. Benchmarking
#set gatekeeper url
gatekeeper_url = f"http://{gatekeeper_public_ip}:8000/validate"


#test for showing result
warm_up(gatekeeper_url=gatekeeper_url)



# Predefined queries
read_query = "SELECT * FROM actor LIMIT 10;"
write_query = "INSERT INTO actor (first_name, last_name, last_update) VALUES ('JOHN', 'DOE', NOW());"

# # Number of requests to send
num_requests = 1000

# # Payload templates
read_payload_template = {"type": "read", "query": read_query, "strategy": ""}
write_payload_template = {"type": "write", "query": write_query, "strategy": ""}

# # # # # Benchmark each strategy

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


#15. Terminate ressources
terminate_all_instances()
time.sleep(120)
delete_all_security_groups()
