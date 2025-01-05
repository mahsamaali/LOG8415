import boto3
from botocore.exceptions import ClientError
# Initialize clients
ec2_client = boto3.client('ec2')






def terminate_all_instances():
    """
    This function terminates all EC2 instances in an AWS account.
    
    Steps:
    1. The function retrieves all running EC2 instances by calling the `describe_instances` method of the EC2 client.
    2. It extracts the instance IDs from the returned reservations and instances.
    3. If there are any instances to terminate, the function calls `terminate_instances` to terminate them.
    4. It prints a message indicating which instances are being terminated.
    5. If no instances are found, a message is printed indicating that there are no instances to terminate.

    Parameters:
        None.

    Returns:
        None. The function terminates EC2 instances and prints messages indicating the progress.

    Raises:
        Any errors raised by the AWS SDK (Boto3) during the instance termination process.
    """

    # Retrieve all EC2 instances
    instances = ec2_client.describe_instances()['Reservations']

    # Extract instance IDs from the instances
    instance_ids = [instance['InstanceId'] for reservation in instances for instance in reservation['Instances']]
    
    # If there are instances, terminate them
    if instance_ids:
        print(f"Terminating instances: {', '.join(instance_ids)}")
        ec2_client.terminate_instances(InstanceIds=instance_ids)
    else:
        # If no instances found, print a message
        print("No instances to terminate.")



def delete_all_security_groups():
    """
    Deletes all security groups except the default ones.

    Args:
        None

    Returns:
        None: Prints the status of deletion for each security group.
    """
    try:
        # Retrieve all security groups
        response = ec2_client.describe_security_groups()
        security_groups = response.get('SecurityGroups', [])

        for sg in security_groups:
            group_name = sg['GroupName']
            group_id = sg['GroupId']

            # Skip default security groups
            if group_name == 'default':
                print(f"Skipping default security group: {group_name} (ID: {group_id})")
                continue

            try:
                # Attempt to delete the security group
                ec2_client.delete_security_group(GroupId=group_id)
                print(f"Deleted security group: {group_name} (ID: {group_id})")
            except ClientError as e:
                if "DependencyViolation" in str(e):
                    print(f"Cannot delete security group {group_name} (ID: {group_id}) as it is associated with other resources.")
                else:
                    print(f"Error deleting security group {group_name} (ID: {group_id}): {e}")

    except ClientError as e:
        print(f"Error retrieving security groups: {e}")