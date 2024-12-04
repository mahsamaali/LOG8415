#for managing error in aws
from botocore.exceptions import ClientError

#1. get VPC_id
def get_vpc(ec2):
    '''
    This function retrieves the ID of the default Virtual Private Cloud (VPC) 
    for a given EC2 object using AWS Boto3.

    Steps:
    1. The function accepts an EC2 client object (from the Boto3 library).
    2. It calls the describe_vpcs method with a filter to get VPCs 
       where 'isDefault' is true (which identifies the default VPC).
    3. From the response, it extracts the 'VpcId' of the first VPC 
       in the list of VPCs returned by the describe_vpcs method.
    4. The function returns the extracted VPC ID.

    Parameters:
        ec2: A Boto3 EC2 client object that allows interaction with AWS EC2 service.

    Returns:
        The ID of the default VPC as a string.
    '''

    # Describe VPCs with a filter for the default VPC
    response = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
    
    # Extract the VPC ID from the first VPC in the response list
    vpc_id = response['Vpcs'][0]['VpcId']
    
    # Return the VPC ID
    return vpc_id




#2.get Subnet_ids
def get_subnet_by_vpc_and_az(ec2, vpc_id, availability_zone):
    '''
    This function retrieves the Subnet IDs associated with a given VPC 
    and a specific Availability Zone (AZ) using AWS Boto3.

    Steps:
    1. The function takes three arguments: an EC2 client object, a VPC ID, and the desired Availability Zone.
    2. It calls the describe_subnets method to retrieve the subnets 
       that belong to the specified VPC and Availability Zone.
    3. If subnets are found, the function extracts the 'SubnetId' and 'AvailabilityZone' 
       of each subnet.
    4. If no subnets are found, the function prints a message and returns None.

    Parameters:
        ec2: A Boto3 EC2 client object that allows interaction with AWS EC2 service.
        vpc_id: The ID of the VPC whose subnets need to be retrieved.
        availability_zone: The desired Availability Zone (e.g., 'us-east-1e').

    Returns:
        A list of dictionaries containing Subnet ID and Availability Zone 
        for the subnets in the specified VPC and AZ, or None if no subnets are found.
    '''

    # Retrieve the subnets associated with the given VPC and Availability Zone
    response = ec2.describe_subnets(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]},
        {'Name': 'availability-zone', 'Values': [availability_zone]}
    ])

    if response['Subnets']:
        # Initialize an empty list to collect subnet info
        subnet_info_list = []
        
        # Iterate through the subnets and collect Subnet IDs and Availability Zones
        for subnet in response['Subnets']:
            subnet_info = {
                'SubnetId': subnet['SubnetId'],
                'AvailabilityZone': subnet['AvailabilityZone']
            }
            subnet_info_list.append(subnet_info)
        
        # Return the subnets found in the specified VPC and AZ
        # print("In network_connection; this is  subnet_info_list",subnet_info_list)
        return subnet_info_list
    else:
        # Print a message if no subnets are found and return None
        print(f"No subnets found for VPC ID: {vpc_id} in Availability Zone: {availability_zone}")
        return None


#3. create security group and return security id
def create_security_group(ec2,group_name ,vpc_id, ports):
    '''
    This function creates or retrieves a security group in a given VPC using AWS Boto3.

    Steps:
    1. The function accepts three arguments: an EC2 client object, a VPC ID, and a list of port numbers.
    2. It checks if a security group with the given group name ('my-security-group') already exists.
    3. If the group exists, it returns the existing security group ID.
    4. If the group does not exist, it creates a new security group in the specified VPC.
    5. After creation, it configures ingress rules to allow traffic on the specified ports.
    6. Finally, the function returns the security group ID.

    Parameters:
        ec2: A Boto3 EC2 client object to interact with AWS EC2 service.
        vpc_id: The ID of the VPC where the security group will be created.
        ports: A list of port numbers to allow in the security group ingress rules.

    Returns:
        The ID of the security group, either existing or newly created.
    '''

    # Check if the security group already exists
    try:
        response = ec2.describe_security_groups(GroupNames=[group_name])
        security_group_id = response['SecurityGroups'][0]['GroupId']
        print(f"Security group '{group_name}' already exists with ID: {security_group_id}")
        return security_group_id

    except ClientError as e:
        if 'InvalidGroup.NotFound' in str(e):
            print(f"Security group '{group_name}' does not exist, creating a new one.")

            # Create a new security group
            security_group = ec2.create_security_group(
                GroupName=group_name,
                Description="Security group for EC2 instances",
                VpcId=vpc_id
            )

            # Get the security group ID
            security_group_id = security_group['GroupId']
            print(f"Security group created: {security_group_id}")

            # Dynamically configure the security group ingress rules
            ip_permissions = [
                {
                    'IpProtocol': 'tcp',
                    'FromPort': port,
                    'ToPort': port,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
                for port in ports
            ]

            ec2.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=ip_permissions
            )
            print(f"Security group configured for ports: {', '.join(map(str, ports))}.")
            return security_group_id

        else:
            raise e




def configure_trusted_host_security_group(ec2_client, vpc_id, gatekeeper_private_ip, proxy_private_ip):
    """
    Creates and configures a security group for the Trusted Host.
    
    Args:
        ec2_client: Boto3 EC2 client.
        vpc_id (str): VPC ID where the security group will be created.
        gatekeeper_private_ip (str): Gatekeeper's private IP.
        proxy_private_ip (str): Proxy's private IP.
    
    Returns:
        str: Security group ID.
    """
    try:
        # Create Security Group
        response = ec2_client.create_security_group(
            GroupName="TrustedHostSG",
            Description="Security group for Trusted Host",
            VpcId=vpc_id
        )
        sg_id = response['GroupId']
        print(f"Created Security Group: {sg_id}")

        # Add Inbound Rules
        ec2_client.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                # Allow HTTP traffic from Gatekeeper
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 8000,
                    'ToPort': 8000,
                    'IpRanges': [{'CidrIp': f"{gatekeeper_private_ip}/32"}]
                },
                # Allow SSH access temporarily (optional)
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]  # Replace with your IP range for security
                }
            ]
        )
        print("Inbound rules added.")

        # Add Outbound Rules
        ec2_client.authorize_security_group_egress(
            GroupId=sg_id,
            IpPermissions=[
                # Allow HTTP traffic to the Proxy
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 8000,
                    'ToPort': 8000,
                    'IpRanges': [{'CidrIp': f"{proxy_private_ip}/32"}]
                }
            ]
        )
        print("Outbound rules added.")

        return sg_id

    except Exception as e:
        print(f"Error configuring security group: {e}")
        return None
    



# def configure_mysql_security_group(ec2,sg_id, proxy_private_ip,):
#     """
#     Configures inbound and outbound rules for a MySQL security group to restrict access to the proxy's private IP.
    
#     Parameters:
#     ec2
#     sg_id (str): Security Group ID for the MySQL instances.
#     proxy_private_ip (str): The private IP of the proxy instance.

    
#     Returns:
#     dict: Response from the AWS EC2 client.
#     """
  
    
#     try:
#         # Configure Inbound Rule
#         inbound_rule = {
#             'IpProtocol': 'tcp',
#             'FromPort': 3306,
#             'ToPort': 3306,
#             'IpRanges': [{'CidrIp': f'{proxy_private_ip}/32'}]
#         }
        
#         ec2.authorize_security_group_ingress(
#             GroupId=sg_id,
#             IpPermissions=[inbound_rule]
#         )
#         print(f"Inbound rule added to allow MySQL (3306) access from {proxy_private_ip}.")
        
#         # Configure Outbound Rule
#         outbound_rule = {
#             'IpProtocol': 'tcp',
#             'FromPort': 3306,
#             'ToPort': 3306,
#             'IpRanges': [{'CidrIp': f'{proxy_private_ip}/32'}]
#         }
        
#         ec2.authorize_security_group_egress(
#             GroupId=sg_id,
#             IpPermissions=[outbound_rule]
#         )
#         print(f"Outbound rule added to allow MySQL (3306) responses to {proxy_private_ip}.")
        
#         return {"status": "Success", "message": "Security group updated."}
    
#     except Exception as e:
#         print(f"Error updating security group: {e}")
#         return {"status": "Error", "message": str(e)}


def configure_security_group(ec2, sg_id, ip_permissions):
    """
    Configures inbound and outbound rules for a security group dynamically.
    
    Parameters:
    ec2: Boto3 EC2 client.
    sg_id (str): Security Group ID to be updated.
    ip_permissions (list): A list of dictionaries specifying inbound and outbound rules.
                           Each dictionary should have 'Direction', 'IpProtocol', 'FromPort', 
                           'ToPort', and 'CidrIp'.
    
    Returns:
    dict: Status of the operation.
    """
    try:
        # Configure Inbound Rules
        inbound_rules = [
            {
                'IpProtocol': rule['IpProtocol'],
                'FromPort': rule['FromPort'],
                'ToPort': rule['ToPort'],
                'IpRanges': [{'CidrIp': rule['CidrIp']}]
            }
            for rule in ip_permissions if rule['Direction'] == 'inbound'
        ]
        
        if inbound_rules:
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=inbound_rules
            )
            print("Inbound rules added successfully.")
        
        # Configure Outbound Rules
        outbound_rules = [
            {
                'IpProtocol': rule['IpProtocol'],
                'FromPort': rule['FromPort'],
                'ToPort': rule['ToPort'],
                'IpRanges': [{'CidrIp': rule['CidrIp']}]
            }
            for rule in ip_permissions if rule['Direction'] == 'outbound'
        ]
        
        if outbound_rules:
            ec2.authorize_security_group_egress(
                GroupId=sg_id,
                IpPermissions=outbound_rules
            )
            print("Outbound rules added successfully.")
        
        return {"status": "Success", "message": "Security group updated."}
    
    except Exception as e:
        print(f"Error updating security group: {e}")
        return {"status": "Error", "message": str(e)}


def update_security_group_rules(ec2, sg_id, ip_permissions):
    """
    Updates inbound and outbound rules for a security group dynamically by replacing existing rules.
    
    Parameters:
    ec2: Boto3 EC2 client.
    sg_id (str): Security Group ID to be updated.
    ip_permissions (list): A list of dictionaries specifying inbound and outbound rules.
                           Each dictionary should have 'Direction', 'IpProtocol', 'FromPort', 
                           'ToPort', and 'CidrIp'.
    
    Returns:
    dict: Status of the operation.
    """
    try:
        # Retrieve current security group rules
        current_sg = ec2.describe_security_groups(GroupIds=[sg_id])['SecurityGroups'][0]
        current_inbound = current_sg.get('IpPermissions', [])
        current_outbound = current_sg.get('IpPermissionsEgress', [])

        # Separate inbound and outbound rules from ip_permissions
        inbound_rules = [
            {
                'IpProtocol': rule['IpProtocol'],
                'FromPort': rule['FromPort'],
                'ToPort': rule['ToPort'],
                'IpRanges': [{'CidrIp': rule['CidrIp']}]
            }
            for rule in ip_permissions if rule['Direction'] == 'inbound'
        ]
        outbound_rules = [
            {
                'IpProtocol': rule['IpProtocol'],
                'FromPort': rule['FromPort'],
                'ToPort': rule['ToPort'],
                'IpRanges': [{'CidrIp': rule['CidrIp']}]
            }
            for rule in ip_permissions if rule['Direction'] == 'outbound'
        ]

        # Revoke existing inbound rules and add updated ones
        if current_inbound:
            ec2.revoke_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=current_inbound
            )
            print("Existing inbound rules revoked.")

        if inbound_rules:
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=inbound_rules
            )
            print("Inbound rules added successfully.")

        # Revoke existing outbound rules and add updated ones
        if current_outbound:
            ec2.revoke_security_group_egress(
                GroupId=sg_id,
                IpPermissions=current_outbound
            )
            print("Existing outbound rules revoked.")

        if outbound_rules:
            ec2.authorize_security_group_egress(
                GroupId=sg_id,
                IpPermissions=outbound_rules
            )
            print("Outbound rules added successfully.")

        return {"status": "Success", "message": "Security group rules updated."}

    except Exception as e:
        print(f"Error updating security group: {e}")
        return {"status": "Error", "message": str(e)}
