#for managing error in aws
from botocore.exceptions import ClientError
#for getting permission on key pairs(chmod 400)
import os
import stat
import time
import base64

#Create key pairs
def create_key_pair(ec2, key_name, key_file):
    '''
    This function checks if an EC2 key pair exists, and if not, it creates a new key pair. 
    The key pair is saved to a file with appropriate permissions.

    Steps:
    1. The function accepts three arguments: an EC2 client object, the key pair name, and the path to the key file.
    2. It checks if the key pair with the specified name already exists using describe_key_pairs.
    3. If the key pair exists, it prints a message and sets the correct file permissions for the key file.
    4. If the key pair does not exist, it creates a new key pair and saves the private key material to a .pem file.
    5. The function sets the correct permissions (read-only for the owner) on the key file to ensure security.

    Parameters:
        ec2: A Boto3 EC2 client object to interact with AWS EC2 service.
        key_name: The name of the key pair to create or check for.
        key_file: The path to the .pem file to store the key.

    Returns:
        None.
    '''

    # Check if the key pair already exists
    try:
        ec2.describe_key_pairs(KeyNames=[key_name])
        print(f"Key Pair '{key_name}' already exists.")
        
        # Set proper permissions for the pem file (read-only for the owner)
        os.chmod(key_file, stat.S_IRUSR)

    # If the key pair doesn't exist, create a new one
    except ClientError as e:
        if 'InvalidKeyPair.NotFound' in str(e):
            # Create the key pair
            key_pair = ec2.create_key_pair(KeyName=key_name)
            
            # Save the private key material to a .pem file
            with open(f'{key_name}.pem', 'w') as file:
                file.write(key_pair['KeyMaterial'])
            print(f"Key Pair created and saved as {key_name}.pem")
            
            # Set proper permissions for the pem file (read-only for the owner)
            os.chmod(key_file, stat.S_IRUSR)
        else:
            raise e


def create_instances(ec2, ami_id, key_name, subnet_id, security_group_id, instance_type, num_instances, availability_zone,instance_name):
    '''
    Launch EC2 instances in the specified availability zone.

    Parameters:
        ec2: A Boto3 EC2 client object to interact with AWS EC2 service.
        ami_id: The Amazon Machine Image (AMI) ID to use for launching instances.
        key_name: The key pair name to associate with the instances.
        subnet_id: The subnet ID where the instances will be launched.
        security_group_id: The security group ID to assign to the instances.
        instance_type: The type of instance to launch (e.g., t2.micro).
        num_instances: The number of instances to launch.
        availability_zone: The AZ where the instances should be launched.

    Returns:
        A list of tuples containing instance IDs and public IPs for the instances that were launched.
    '''

    # Launch EC2 instances in the specified availability zone
    response = ec2.run_instances(
        ImageId=ami_id,
        MinCount=num_instances,
        MaxCount=num_instances,
        InstanceType=instance_type,
        KeyName=key_name,
        SubnetId=subnet_id,
        SecurityGroupIds=[security_group_id],
        Placement={'AvailabilityZone': availability_zone},  # Specify the AZ here
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': f'{instance_name}'}]
        }],
        Monitoring={'Enabled': True}
    )

    instance_ids = [instance['InstanceId'] for instance in response['Instances']]
    print(f"Created instances: {instance_ids}")
    
    ec2.get_waiter('instance_running').wait(InstanceIds=instance_ids)
    print(f"Instances are now running: {instance_ids}")
    
    instances_info = ec2.describe_instances(InstanceIds=instance_ids)
    
    instances_data = []
    for reservation in instances_info['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            public_ip = instance['PublicIpAddress']
            instances_data.append((instance_id, public_ip))
    
    print(f"Instances' data (ID, Public IP): {instances_data}")
    
    return instances_data







