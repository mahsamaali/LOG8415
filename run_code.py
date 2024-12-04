import paramiko
import os
from scp import SCPClient
import time
import re

import subprocess
import os


def get_private_ip(ec2,instance_id):
    """
    Retrieves the private IP address of an EC2 instance by its instance ID.

    Args:
        instance_id (str): The ID of the EC2 instance.

    Returns:
        str: The private IP address of the instance.
    """

    # Get instance information
    response = ec2.describe_instances(InstanceIds=[instance_id])
    reservations = response.get('Reservations', [])
    
    if not reservations:
        raise ValueError(f"No reservations found for instance ID: {instance_id}")

    instances = reservations[0].get('Instances', [])
    if not instances:
        raise ValueError(f"No instances found for instance ID: {instance_id}")

    # Extract private IP
    private_ip = instances[0].get('PrivateIpAddress', None)
    if not private_ip:
        raise ValueError(f"Private IP not found for instance ID: {instance_id}")

    return private_ip



#SSH Connection 
def wait_for_ssh(ip_address, username, private_key_path, retries=10, delay=30):
    """
    Tries to establish an SSH connection to a given EC2 instance multiple times until successful or retries run out.

    Args:
    ip_address (str): The public IP address of the EC2 instance.
    username (str): The SSH username (usually 'ubuntu').
    private_key_path (str): Path to the private key (.pem) used to authenticate the SSH connection.
    retries (int): Number of retries before failing (default is 10).
    delay (int): Delay between retries in seconds (default is 30 seconds).

    Returns:
    bool: True if SSH connection is successful, False if all retries fail.
    """
    key = paramiko.RSAKey.from_private_key_file(private_key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for attempt in range(retries):
        try:
            print(f"Attempting SSH connection to {ip_address} (Attempt {attempt+1}/{retries})...")
            client.connect(hostname=ip_address, username=username, pkey=key, timeout=10)
            client.close()
            print(f"SSH connection to {ip_address} successful!")
            return True
        except paramiko.ssh_exception.NoValidConnectionsError as e:
            print(f"SSH connection failed: {e}")
        except paramiko.AuthenticationException as e:
            print(f"SSH Authentication failed: {e}")
        except paramiko.SSHException as e:
            print(f"General SSH error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        
        print(f"Waiting {delay} seconds before retrying...")
        time.sleep(delay)
    
    print(f"Unable to establish SSH connection to {ip_address} after {retries} attempts.")
    return False




# Function to execute SSH commands via Paramiko
def ssh_exec_command(ip_address, username, private_key_path, commands, capture_last_output=False):
    #, fetch_codename=False
    """
    Executes a list of commands over SSH and optionally captures the output of the last command.
    
    Args:
        ip_address (str): The public IP address of the EC2 instance.
        username (str): The SSH username (usually 'ubuntu').
        private_key_path (str): Path to the private key (.pem) used to authenticate the SSH connection.
        commands (list): A list of shell commands (str) to be executed on the remote EC2 instance.
        capture_last_output (bool): If True, captures and returns the output of the last command.
        fetch_codename (bool): If True, fetches the OS codename dynamically and updates commands.

    Returns:
        dict or str or None:
            - If `capture_last_output` is True, returns parsed data (if applicable).
            - If `fetch_codename` is True, returns the OS codename.
            - Otherwise, returns None.
    """
    key = paramiko.RSAKey.from_private_key_file(private_key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip_address, username=username, pkey=key)

    last_output = None

    try:
        # Execute all commands
        for i, command in enumerate(commands):
            print(f"Executing command: {command}")
            stdin, stdout, stderr = client.exec_command(command, get_pty=True)
            stdout.channel.recv_exit_status()
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            if error:
                print(f"Error for command '{command}': {error}")

            print(f"Output for command '{command}': {output}")

            # Capture and parse output of the last command
            if capture_last_output and i == len(commands) - 1:
                lines = output.splitlines()

                # Remove warning and separator lines
                filtered_lines = [
                    line for line in lines if not line.startswith("mysql:") and not line.startswith("+")
                ]

                # Ensure valid output
                if len(filtered_lines) >= 2:  # Header and at least one data row
                    header = filtered_lines[0].strip()
                    data = filtered_lines[1].strip()
                    print("Parsed Header:", header)
                    print("Parsed Data:", data)
                    if "File" in header and "Position" in header:
                        columns = re.split(r'\s+', header)
                        values = re.split(r'\s+', data)
                        file_index = columns.index("File")
                        position_index = columns.index("Position")
                        last_output = {
                            "File": values[file_index],
                            "Position": int(values[position_index])
                        }

    finally:
        client.close()

    return last_output if capture_last_output else None

def progress(filename, size, sent):
    """
    Displays the progress of the file transfer in MB.
    
    Args:
    filename (str): The name of the file being transferred.
    size (int): The total size of the file in bytes.
    sent (int): The number of bytes sent so far.
    
    Returns:
    None
    """
    size_mb = size / (1024 * 1024)  # Convert bytes to megabytes
    sent_mb = sent / (1024 * 1024)  # Convert bytes to megabytes
    percentage = (sent / size) * 100
    print(f"{filename}: {sent_mb:.2f}/{size_mb:.2f} MB transferred ({percentage:.2f}%)")


# Function to transfer files via SCP (Paramiko)
def transfer_file(ip_address, username, private_key_path, local_filepath, remote_filepath):
    """
    Transfers a file from the local machine to the specified EC2 instance using SCP (via Paramiko),
    with progress reporting.

    Args:
    ip_address (str): The public IP address of the EC2 instance.
    username (str): The SSH username (usually 'ubuntu').
    private_key_path (str): Path to the private key (.pem) used to authenticate the SCP connection.
    local_filepath (str): The local path to the file that needs to be transferred.
    remote_filepath (str): The destination path on the EC2 instance where the file should be transferred.

    Returns:
    None: Transfers the file and displays the progress.
    """
    # Check if local file exists
    if not os.path.exists(local_filepath):
        print(f"Local file {local_filepath} does not exist")
        return
    
    # Load the private key
    key = paramiko.RSAKey.from_private_key_file(private_key_path)
    
    # Establish SSH connection
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip_address, username=username, pkey=key)

    # Use SCPClient to transfer the file with progress callback
    print(f"Transferring {local_filepath} to {remote_filepath} on {ip_address}")
    try:
        with SCPClient(client.get_transport(), progress=progress) as scp:
            scp.put(local_filepath, remote_filepath)
            print("File transfer completed successfully.")
    except Exception as e:
        print(f"Failed to transfer file: {e}")
    
    # Close SSH connection
    client.close()




# Function to set up FastAPI app on the EC2 instance
def install_mysql(ip_address, username, private_key_path):

    """
    Sets up Docker containers on a worker, dynamically based on the number of containers per worker.
    Installs necessary packages, runs the containers, and returns their statuses, IP, and port information.

    Args:
        ip_address (str): The public IP address of the EC2 instance.
        username (str): The SSH username (usually 'ubuntu').
        private_key_path (str): Path to the private key (.pem) used for SSH.
        container_start_port (int): The starting port number for the first container on this worker.

    Returns:
        dict: Information about the worker instance's IP, ports, and statuses for each container.
    """
    if not wait_for_ssh(ip_address, username, private_key_path):
        print(f"Failed to establish SSH connection to {ip_address}")
        return

    #install my sql
    commands = [
    'sudo apt update',
    'sudo apt install mysql-server -y',
    'sudo systemctl start mysql',
    'sudo systemctl enable mysql',
    'mysql --version',
    "PRIVATE_IP=$(hostname -I | awk '{print $1}') && sudo sed -i \"s/^bind-address.*/bind-address = ${PRIVATE_IP}/\" /etc/mysql/mysql.conf.d/mysqld.cnf",
    "sudo systemctl restart mysql"
    ]
    ssh_exec_command(ip_address, username, private_key_path, commands)

#################################install Sakila ###########################################
    
    commands = [
    "sudo apt update",
    "sudo apt install wget -y",
    "wget https://downloads.mysql.com/docs/sakila-db.tar.gz -O /tmp/sakila-db.tar.gz",
    "tar -xvzf /tmp/sakila-db.tar.gz -C /tmp",
    # Use root user (no password) for creating the database
    "sudo mysql -u root -e 'CREATE DATABASE sakila;'",
    # Use root user (no password) to import schema and data
    "sudo mysql -u root sakila < /tmp/sakila-db/sakila-schema.sql",
    "sudo mysql -u root sakila < /tmp/sakila-db/sakila-data.sql",
    # Show databases to confirm creation
    "sudo mysql -u root -e 'SHOW DATABASES;'",
    #create a new user
    "sudo mysql -u root -e \"CREATE USER 'replica_user'@'%' IDENTIFIED BY '1234';\"",
    "sudo mysql -u root -e \"ALTER USER 'replica_user'@'%' IDENTIFIED WITH 'mysql_native_password' BY '1234';\"",
    "sudo mysql -u root -e \"GRANT ALL PRIVILEGES ON *.* TO 'replica_user'@'%' WITH GRANT OPTION;\"",
    "sudo mysql -u root -e \"FLUSH PRIVILEGES;\""

    ]
    ssh_exec_command(ip_address, username, private_key_path, commands)

#################################install sysbench ###########################################
    commands = [
    "sudo apt-get update",
    "sudo apt-get install sysbench -y",
    # Prepare database for Sysbench
    """PRIVATE_IP=$(hostname -I | awk '{print $1}') && sysbench /usr/share/sysbench/oltp_read_write.lua \
    --mysql-host=$PRIVATE_IP \
    --mysql-user=replica_user \
    --mysql-password=1234 \
    --mysql-db=sakila \
    prepare""",
    # Test database performance
    """PRIVATE_IP=$(hostname -I | awk '{print $1}') && sysbench /usr/share/sysbench/oltp_read_only.lua \
    --mysql-host=$PRIVATE_IP \
    --mysql-user=replica_user \
    --mysql-password=1234 \
    --mysql-db=sakila \
    --time=60 \
    --threads=4 \
    run"""
]
    ssh_exec_command(ip_address, username, private_key_path, commands)




def configure_manager(ip_address, username, private_key_path):

    commands = [
    "PRIVATE_IP=$(hostname -I | awk '{print $1}') && sudo sed -i \"s/^bind-address.*/bind-address = ${PRIVATE_IP}/\" /etc/mysql/mysql.conf.d/mysqld.cnf",
    "sudo sed -i '/^\\[mysqld\\]/a server-id = 1' /etc/mysql/mysql.conf.d/mysqld.cnf",
    "sudo sed -i '/^\\[mysqld\\]/a log_bin = /var/log/mysql/mysql-bin.log' /etc/mysql/mysql.conf.d/mysqld.cnf",
    "sudo sed -i '/^\\[mysqld\\]/a binlog_do_db = sakila' /etc/mysql/mysql.conf.d/mysqld.cnf",
    "sudo systemctl restart mysql",
     """PRIVATE_IP=$(hostname -I | awk '{print $1}') && mysql -u replica_user -p'1234' -h $PRIVATE_IP -e 'SHOW MASTER STATUS;'"""
    ]
    master_status =ssh_exec_command(ip_address, username, private_key_path, commands, capture_last_output=True)


    if master_status:
        print(f"Master Status: File={master_status['File']}, Position={master_status['Position']}")
        return master_status
    else:
        print("Failed to retrieve master status.")
        return None
 
def configure_worker(ip_address, username, private_key_path, manager_ip, file, position,server_id):
    """
    Configures a MySQL worker instance for replication.
    
    Args:
        ip_address (str): The public IP address of the worker instance.
        username (str): The SSH username (usually 'ubuntu').
        private_key_path (str): Path to the private key (.pem) used for SSH.
        manager_ip (str): Public IP address of the manager instance.
        file (str): Binary log file from the manager (e.g., 'mysql-bin.000001').
        position (int): Log position from the manager (e.g., 873).
    Returns:
        None
    """
    # Configure server-id and restart MySQL
    commands = [
        "PRIVATE_IP=$(hostname -I | awk '{print $1}') && sudo sed -i \"s/^bind-address.*/bind-address = ${PRIVATE_IP}/\" /etc/mysql/mysql.conf.d/mysqld.cnf",
        f"sudo sed -i '/^\\[mysqld\\]/a server-id = {server_id}' /etc/mysql/mysql.conf.d/mysqld.cnf",  # Ensure unique server-id
        "sudo sed -i '/^\\[mysqld\\]/a relay-log = /var/log/mysql/mysql-relay-bin' /etc/mysql/mysql.conf.d/mysqld.cnf",
        "sudo systemctl restart mysql",
    ]
    ssh_exec_command(ip_address, username, private_key_path, commands)

    replication_commands = [
    # Retrieve the private IP of the worker instance dynamically
    "PRIVATE_IP=$(hostname -I | awk '{print $1}')",
    
    # Configure the worker for replication
    f"""PRIVATE_IP=$(hostname -I | awk '{{print $1}}') && mysql -u replica_user -p'1234' -h $PRIVATE_IP -e "CHANGE MASTER TO MASTER_HOST='{manager_ip}', MASTER_USER='replica_user', MASTER_PASSWORD='1234', MASTER_LOG_FILE='{file}', MASTER_LOG_POS={position};\"""",
    
    # Start the replication process
    """PRIVATE_IP=$(hostname -I | awk '{print $1}') && mysql -u replica_user -p'1234' -h $PRIVATE_IP -e "START SLAVE;\"""",
    
    # Verify the replication status
    """PRIVATE_IP=$(hostname -I | awk '{print $1}') && mysql -u replica_user -p'1234' -h $PRIVATE_IP -e "SHOW SLAVE STATUS\\G;\""""
    ]

    ssh_exec_command(ip_address, username, private_key_path, replication_commands)








def build_images(dockerfiles):
    """
    Dynamically builds Docker images and saves them as compressed tar.gz files.

    Args:
        dockerfiles (dict): A dictionary where the key is the image name and the value is the Dockerfile path.
                            For example: {"container1": "Dockerfile_1", "container2": "Dockerfile_2"}
    """
    for image_name, dockerfile_path in dockerfiles.items():
        # Build the Docker image dynamically using the Dockerfile
        print(f"Building Docker image {image_name} using {dockerfile_path}...")
        build_command = ["docker", "build", "-f", dockerfile_path, "-t", image_name, "."]
        result = subprocess.run(build_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            print(f"Error building Docker image {image_name}: {result.stderr.decode('utf-8')}")
            continue
        
        print(f"Successfully built Docker image {image_name}")

        # Save the Docker image directly as a compressed tar.gz file
        tar_gz_file = f"{image_name}.tar.gz"
        print(f"Saving Docker image {image_name} as compressed {tar_gz_file}...")

        try:
            # Save the Docker image and compress it
            with open(tar_gz_file, "wb") as f_out:
                save_command = ["docker", "save", image_name]
                gzip_command = ["gzip"]
                save_process = subprocess.Popen(save_command, stdout=subprocess.PIPE)
                gzip_process = subprocess.Popen(gzip_command, stdin=save_process.stdout, stdout=f_out)
                save_process.stdout.close()  # Allow save_process to receive a SIGPIPE if gzip_process exits
                gzip_process.communicate()   # Wait for gzip to finish

                if gzip_process.returncode == 0:
                    print(f"Compressed Docker image saved as {tar_gz_file}")
                else:
                    print(f"Error saving compressed Docker image {image_name}")
        except Exception as e:
            print(f"Failed to save compressed Docker image {image_name}: {e}")







def configure_server(ip_address, username, private_key_path, docker_image_name):
    """
    Configures the trusted host by installing Docker and deploying the specified Docker image.

    Args:
        ip_address (str): The IP address of the trusted host.
        username (str): SSH username.
        private_key_path (str): Path to the private SSH key.
        docker_image_name (str): Name of the Docker image to deploy.
    """
    # Installing Docker
    commands = [
        'sudo apt-get update -y',
        'sudo apt-get install -y ca-certificates curl',
        'sudo install -m 0755 -d /etc/apt/keyrings',
        'sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc',
        'sudo chmod a+r /etc/apt/keyrings/docker.asc',
        'echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null',
        'sudo apt-get update -y',
        'sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin',
        'sudo docker run hello-world',
    ]
    ssh_exec_command(ip_address, username, private_key_path, commands)

    # Transfer Docker image to the instance
    local_filepath = f'./{docker_image_name}.tar.gz'
    remote_filepath = f'/home/ubuntu/{docker_image_name}.tar.gz'
    transfer_file(ip_address, username, private_key_path, local_filepath, remote_filepath)

    # Load Docker image
    commands = [f'gzip -dc /home/ubuntu/{docker_image_name}.tar.gz | sudo docker load']
    ssh_exec_command(ip_address, username, private_key_path, commands)

    # Run the Docker container
    commands = [f'sudo docker run -d -p 8000:8000 {docker_image_name}:latest']
    ssh_exec_command(ip_address, username, private_key_path, commands)


def configure_iptables_workers(ip_address, username, private_key_path, proxy_private_ip, manager_private_ip):
    """
    Configures iptables rules on a worker instance.

    Args:
        ip_address (str): IP address of the worker instance.
        username (str): SSH username.
        private_key_path (str): Path to the SSH private key.
        proxy_private_ip (str): Private IP of the proxy instance.
        manager_private_ip (str): Private IP of the manager instance.
    """
    commands = [
        # Allow SSH access
        "sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT",
        
        # Allow MySQL traffic from Proxy
        f"sudo iptables -A INPUT -p tcp --dport 3306 -s {proxy_private_ip} -j ACCEPT",
        
        # Allow MySQL replication traffic from Manager
        f"sudo iptables -A INPUT -p tcp --dport 3306 -s {manager_private_ip} -j ACCEPT",

        # Allow loopback traffic
        "sudo iptables -A INPUT -i lo -j ACCEPT",
        "sudo iptables -A OUTPUT -o lo -j ACCEPT",
        
        # Allow established and related connections
        "sudo iptables -A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT",
        
        # Default policy to drop all other traffic
        "sudo iptables -P INPUT DROP",
        "sudo iptables -P FORWARD DROP",
        "sudo iptables -P OUTPUT ACCEPT",
        
        # Save the rules
        "sudo mkdir -p /etc/iptables/",
        "sudo iptables-save | sudo tee /etc/iptables/rules.v4"
    ]
    
    ssh_exec_command(ip_address, username, private_key_path, commands)


# def configure_iptables_manager(ip_address, username, private_key_path, proxy_private_ip, private_worker_ips):
#     """
#     Configures iptables rules on a manager instance.

#     Args:
#         ip_address (str): IP address of the manager instance.
#         username (str): SSH username.
#         private_key_path (str): Path to the SSH private key.
#         proxy_private_ip (str): Private IP of the proxy instance.
#         private_worker_ips (list): List of private IPs of worker instances.
#     """
#     commands = [
#         # Allow SSH access
#         "sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT",
        
#         # Allow MySQL traffic from Proxy
#         f"sudo iptables -A INPUT -p tcp --dport 3306 -s {proxy_private_ip} -j ACCEPT",
        
#         # Allow MySQL replication traffic from Workers
#     ]
    
#     # Add rules for each worker IP
#     for worker_ip in private_worker_ips:
#         commands.append(f"sudo iptables -A INPUT -p tcp --dport 3306 -s {worker_ip} -j ACCEPT")
    
#     # Add remaining rules
#     commands.extend([
#         # Allow loopback traffic
#         "sudo iptables -A INPUT -i lo -j ACCEPT",
#         "sudo iptables -A OUTPUT -o lo -j ACCEPT",
#         # Allow established and related connections
#         "sudo iptables -A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT",
        
#         # Default policy to drop all other traffic
#         "sudo iptables -P INPUT DROP",
#         "sudo iptables -P FORWARD DROP",
#         "sudo iptables -P OUTPUT ACCEPT",
        
#         # Save the rules
#         "sudo mkdir -p /etc/iptables/",
#         "sudo iptables-save | sudo tee /etc/iptables/rules.v4"
#     ])
    
#     ssh_exec_command(ip_address, username, private_key_path, commands)



def configure_iptables_manager(ip_address, username, private_key_path, proxy_private_ip, private_worker_ips):
    """
    Configures iptables rules on a manager instance.

    Args:
        ip_address (str): IP address of the manager instance.
        username (str): SSH username.
        private_key_path (str): Path to the SSH private key.
        proxy_private_ip (str): Private IP of the proxy instance.
        private_worker_ips (list): List of private IPs of worker instances.
    """
    commands = [
        # Allow SSH access
        "sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT",
        
        
        # Allow MySQL replication traffic from Workers
    ]
    
    # Add rules for each worker IP
    for worker_ip in private_worker_ips:
        commands.append(f"sudo iptables -A INPUT -p tcp --dport 3306 -s {worker_ip} -j ACCEPT")
    
    # Add remaining rules
    commands.extend([
        # Allow loopback traffic
        "sudo iptables -A INPUT -i lo -j ACCEPT",
        "sudo iptables -A OUTPUT -o lo -j ACCEPT",
        # Allow established and related connections
        "sudo iptables -A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT",
        #"sudo iptables -A OUTPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT",
        # Default policy to drop all other traffic
        "sudo iptables -P INPUT DROP",
        "sudo iptables -P FORWARD DROP",
        "sudo iptables -P OUTPUT ACCEPT",
        
        # Save the rules
        "sudo mkdir -p /etc/iptables/",
        "sudo iptables-save | sudo tee /etc/iptables/rules.v4"
    ])
    
    ssh_exec_command(ip_address, username, private_key_path, commands)






def configure_iptables_proxy(ip_address, username, private_key_path, private_worker_ips, manager_private_ip):
    """
    Configures iptables rules on a proxy instance.

    Args:
        ip_address (str): IP address of the proxy instance.
        username (str): SSH username.
        private_key_path (str): Path to the SSH private key.
        private_worker_ips (list): List of private IPs of worker instances.
        manager_private_ip (str): Private IP of the manager instance.
    """
    commands = [
        # Allow SSH access
        "sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT",
        
        # Allow application traffic on port 8000
        "sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT",
    ]
    
    # Allow outgoing traffic to Workers (Read Queries)
    for worker_ip in private_worker_ips:
        commands.append(f"sudo iptables -A OUTPUT -p tcp --dport 3306 -d {worker_ip} -j ACCEPT")
    
    # Allow outgoing traffic to Manager (Write Queries)
    commands.append(f"sudo iptables -A OUTPUT -p tcp --dport 3306 -d {manager_private_ip} -j ACCEPT")
    
    # Allow established and related connections
    commands.extend([
        # Allow loopback traffic
        "sudo iptables -A INPUT -i lo -j ACCEPT",
        "sudo iptables -A OUTPUT -o lo -j ACCEPT",

        "sudo iptables -A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT",
        "sudo iptables -A OUTPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT",
        
        # Default policy to drop all other traffic
        "sudo iptables -P INPUT DROP",
        "sudo iptables -P FORWARD DROP",
        "sudo iptables -P OUTPUT ACCEPT",
        
        # Save the rules
        "sudo mkdir -p /etc/iptables/",
        "sudo iptables-save | sudo tee /etc/iptables/rules.v4"
    ])
    
    ssh_exec_command(ip_address, username, private_key_path, commands)






def configure_iptables_trusted(ip_address, username, private_key_path, proxy_private_ip, gatekeeper_private_ip):
    """
    Configures iptables rules on the trusted instance.

    Args:
        ip_address (str): IP address of the trusted instance.
        username (str): SSH username.
        private_key_path (str): Path to the SSH private key.
        proxy_private_ip (str): Private IP of the proxy instance.
        gatekeeper_private_ip (str): Private IP of the gatekeeper instance.
    """
    commands = [
        # Allow SSH access
        "sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT",
        
        # Allow incoming traffic on port 8000 from Gatekeeper
        f"sudo iptables -A INPUT -p tcp --dport 8000 -s {gatekeeper_private_ip} -j ACCEPT",
        
        # Allow outgoing traffic to Proxy on port 8000
        f"sudo iptables -A OUTPUT -p tcp --dport 8000 -d {proxy_private_ip} -j ACCEPT",

        # Allow loopback traffic
        "sudo iptables -A INPUT -i lo -j ACCEPT",
        "sudo iptables -A OUTPUT -o lo -j ACCEPT",
        
        # Allow established and related connections
        "sudo iptables -A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT",
        "sudo iptables -A OUTPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT",
        
        # Default policy to drop all other traffic
        "sudo iptables -P INPUT DROP",
        "sudo iptables -P FORWARD DROP",
        "sudo iptables -P OUTPUT ACCEPT",
        
        # Save the rules
        "sudo mkdir -p /etc/iptables/",
        "sudo iptables-save | sudo tee /etc/iptables/rules.v4"
    ]
    
    ssh_exec_command(ip_address, username, private_key_path, commands)







def configure_iptables_gatekeeper(ip_address, username, private_key_path, proxy_private_ip):
    """
    Configures iptables rules on the gatekeeper instance.

    Args:
        ip_address (str): IP address of the gatekeeper instance.
        username (str): SSH username.
        private_key_path (str): Path to the SSH private key.
        proxy_private_ip (str): Private IP of the proxy instance.
    """
    commands = [
        # Allow SSH access
        "sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT",

        # Allow HTTP/HTTPS traffic from all clients
        "sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT",   # HTTP
        "sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT",  # HTTPS

        # Allow incoming traffic on port 8000 from clients
        "sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT",

        # Allow outgoing traffic to Proxy on port 8000
        f"sudo iptables -A OUTPUT -p tcp --dport 8000 -d {proxy_private_ip} -j ACCEPT",

        # Allow loopback traffic
        "sudo iptables -A INPUT -i lo -j ACCEPT",
        "sudo iptables -A OUTPUT -o lo -j ACCEPT",

        # Allow established and related connections
        "sudo iptables -A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT",
        "sudo iptables -A OUTPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT",

        # Default policy to drop all other traffic
        "sudo iptables -P INPUT DROP",
        "sudo iptables -P FORWARD DROP",
        "sudo iptables -P OUTPUT ACCEPT",

        # Save the rules
        "sudo mkdir -p /etc/iptables/",
        "sudo iptables-save | sudo tee /etc/iptables/rules.v4"
    ]

    ssh_exec_command(ip_address, username, private_key_path, commands)
