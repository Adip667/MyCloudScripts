import argparse
import boto3
from time import strftime
import configparser
from botocore.exceptions import ClientError
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def get_config_account():
    """
    get the account number from the config file, used for snapshot
    :return: account number in list.
    """
    _log('INFO: Checking account config')
    config = configparser.ConfigParser()
    config.read('config.txt')
    account_details = [config['aws_details']['aws_account']]
    _log(f"INFO: Found account: {account_details[0]}")
    return account_details


def scan_snapshots(snapshotid):
    """
    check the actual size of snapshots
    :param snapshotid: if operation=snap contain snap ID else contain None
    """

    account = get_config_account()
    Total_snapshot_storage_MB = 0
    print(regions)
    _log(f'INFO: Checking snapshots in {regions}')

    ebs = boto3.client('ebs')

    if not snapshotid:
        # scan all snapshot in a region
        ec2 = boto3.client('ec2', region_name=regions.strip())
        response = ec2.describe_snapshots(OwnerIds=account)
        for snap in response['Snapshots']:
            try:
                blocks = ebs.list_snapshot_blocks(SnapshotId=snap['SnapshotId'])
                # while NextToken not empty - continue counting
                snap_storage = len(blocks['Blocks'])
                while blocks.get('NextToken'):
                    blocks = ebs.list_snapshot_blocks(SnapshotId=snap['SnapshotId'], NextToken=blocks.get('NextToken'))
                    snap_storage += len(blocks['Blocks'])

                Total_snapshot_storage_MB += snap_storage
                _log(
                    f"{snap['SnapshotId']} ({snap_storage * 0.5} MB), {snap['VolumeId']}({snap['VolumeSize']} GB) ")

            except ClientError as e:
                _log(f'ERROR: {e}')

        _log(f"Total snapshot storage for account{account}: {Total_snapshot_storage_MB * 0.5} MB")

    else:
        blocks = ebs.list_snapshot_blocks(SnapshotId=snapshotid)
        Total_snapshot_storage_MB += len(blocks['Blocks'])
        _log(
            f"{snapshotid} ({len(blocks['Blocks']) * 0.5} MB)")


def upload_report_s3(path, bucketName, filename):
    """
    Upload files to S3
    :param path: path to the file
    :param bucketName: bucket name to upload to
    :param filename: the file to upload
    """
    s3 = boto3.resource('s3')
    try:
        s3.meta.client.upload_file(path, bucketName, filename)
    except ClientError as e:
        print(e)


def send_report_SES(sender, recipient, ses_region, subject, body, file_path):
    # based on aws example
    CHARSET = "utf-8"
    client = boto3.client('ses', region_name=ses_region)

    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    msg_body = MIMEMultipart('alternative')
    textpart = MIMEText(body.encode(CHARSET), 'plain', CHARSET)
    msg_body.attach(textpart)

    attachment = MIMEApplication(open(file_path, 'rb').read())
    attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file_path))

    msg.attach(msg_body)
    msg.attach(attachment)

    try:
        response = client.send_raw_email(Source=sender, Destinations=[recipient],
                                         RawMessage={'Data': msg.as_string(), })
    except ClientError as e:
        print(e)


def _log(line):
    # handle print to log file and console
    console = True

    if Logfile:
        with open(log_name, "a") as file:
            file.write(str(line) + '\n')
    if console:
        print(line)


if __name__ == '__main__':

    Logfile = False
    log_name = strftime('SnapStorage_' + "%Y-%b-%d_%H-%M-%S.log")

    # get command from CLI
    parser = argparse.ArgumentParser(description='Run cleanup as config in the config.txt file')
    parser.add_argument('--operation', '-o', type=str,
                        help='an operation name, Can be "sr"(scan region) or "snap"(check specific snap)')
    parser.add_argument('--region', '-r', type=str,
                        help='region id')
    parser.add_argument('--snapid', '-s', type=str,
                        help='snapshot id if operation is "snap"')
    parser.add_argument('--log', metavar='Bool', type=str,
                        help='Will create logs file for the CLI Operations')
    parser.add_argument('--share', '-sh', type=str,
                        help='will share log file via s3 or email')
    args = parser.parse_args()

    if (args.log == 'True'):
        Logfile = True

    # get region from AWS
    ebs = boto3.client('ec2')
    regions = ebs.describe_regions()
    regions = [region.get('RegionName') for region in regions['Regions']]

    # check region in CLI param exist
    if args.region in regions:
        regions = args.region
        print(regions)
        # scan entire region or specific snap.
        if args.operation == "sr":
            scan_snapshots(None)
        elif args.operation == "snap":
            scan_snapshots(args.snapid)

    # share log with email or S3 if requested in CLI
    bucketName = 'asdascsasd'
    path = os.path.abspath(log_name)
    print(path)
    if args.log == 'True' and args.share == 's3':
        upload_report_s3(path, bucketName, log_name)
    elif args.log == 'True' and args.share == 'email':
        send_report_SES("sender@email.com", "recipient@email.com", 'us-east-1', "Storage report",
                        "Attached storage report log", path)
