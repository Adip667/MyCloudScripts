from csv import DictWriter
import boto3
from time import strftime
import configparser


def get_config_regions():
    """
    read the region configuration from config.txt
    :return: return list of region based on user config.txt
    """
    existing_regions = ('eu-north-1', 'ap-south-1', 'eu-west-3', 'eu-west-2', 'eu-west-1', 'ap-northeast-2',
                        'ap-northeast-1', 'sa-east-1', 'ca-central-1', 'ap-southeast-1', 'ap-southeast-2',
                        'eu-central-1', 'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2')

    _log('INFO: Checking region config')
    config = configparser.ConfigParser()
    config.read('config.txt')
    region_list = []

    if config['ec2_region'].getboolean('All'):
        _log('INFO: Regions from config file are - All regions***')
        return existing_regions
    else:
        region_list = config['ec2_region']['regions'].split(",")
        bad_region = [region for region in region_list if region.strip() not in existing_regions]
        if bad_region:
            _log(f"ERROR: Not found - {bad_region}, Please check your configuration")
        region_list = [region for region in region_list if region.strip() in existing_regions]
        _log(f"INFO: Valid regions from config file are - {region_list}")
        return region_list


def _create_csv_file(file_prefix, headers):
    """
    Create CSV file with headers to be used later to report the results
    :param file_prefix: prefix for the file name
    :param headers: headers for the csv
    :return: file name (prefix+date_time)
    """
    file_name = strftime(file_prefix + "%Y-%b-%d_%H-%M-%S.csv")
    _log('INFO: Creating CSV File and Headers')
    with open(file_name, "w") as file:
        csv_writer = DictWriter(file, fieldnames=headers, lineterminator='\n')
        csv_writer.writeheader()
    return file_name


def add_sg_record_csv(file_name, headers, security_group_record):
    """
    add security group record to existing csv file
    :param file_name: existing csv report, created in _create_csv_file
    :param headers: headers for the existing csv file, used to write data row
    :param security_group_record: sg dictionary to be added to csv
    """

    with open(file_name, "a") as file:
        csv_writer = DictWriter(file, fieldnames=headers, lineterminator='\n')
        _log(f'INFO: Adding following record to CSV - {security_group_record}')
        csv_writer.writerow({
            "Region": security_group_record['Region'],
            "OwnerId": security_group_record['OwnerId'],
            "SG Name": security_group_record['GroupName'],
            "SG Id": security_group_record['GroupId'],
            "VpcId": security_group_record['VpcId'],
            "FromPort": security_group_record['FromPort'],
            "ToPort": security_group_record['ToPort'],
            "IpProtocol": security_group_record['IpProtocol'],
            "Source": security_group_record['Source'],
            "Instances": security_group_record['Instances'],
            "Tags": security_group_record['Tags'],

        })

def scan_sg():
    """
    main function, check each region for security groups with boto3
    then it add them to csv report that contains all the ports, Ips and related instances
    """
    headers = ["Region", "OwnerId", "SG Name", "SG Id", "VpcId", "FromPort",
               "ToPort", "IpProtocol", "Source", "Instances", "Tags"]
    csv_file = _create_csv_file("SG_report_", headers)

    for region in regions:  # iterate over the region list and get the SG's
        ec2 = boto3.client('ec2', region_name=region.strip())
        response = ec2.describe_security_groups()

        _log(f"INFO: currently in region - {region}")

        security_group_record = {'Region': region}  # dict for the SG, will be send later to the CSV

        for sg in response['SecurityGroups']:  # iterate over all the SG in the current region and add data to dict
            _log(f"INFO: Found security group: {sg}")

            security_group_record['GroupName'] = sg['GroupName']
            security_group_record['VpcId'] = sg.get('VpcId')
            security_group_record['OwnerId'] = sg.get('OwnerId')

            security_group_record['Instances'] = ''

            # get instances so we have SG -> relation
            _log('INFO: Checking EC2 Relation')
            instances_for_sg = ec2.describe_instances(
                Filters=[{'Name': 'instance.group-id', 'Values': [sg.get('GroupId'), ]}, ])
            instances_for_sg = [i for instance in instances_for_sg['Reservations'] for i in
                                instance['Instances']]
            instances_for_sg = [instance['InstanceId'] for instance in instances_for_sg]

            # remove 'key'/'value' , so tags look nice in csv
            if not sg.get('Tags'):
                tags_for_format = 'N/A'
            else:
                tags_for_format = {tag.get('Key'): tag.get('Value') for tag in sg.get('Tags')}
            security_group_record['Tags'] = tags_for_format


            if not instances_for_sg:
                _log('INFO: no instances, setting to N/A')
                security_group_record['Instances'] = 'N/A'

            else:
                _log(f'INFO: Related instances - {instances_for_sg}')
                security_group_record['Instances'] = ', '.join(instances_for_sg)  # convert instance list to string



            security_group_record['GroupId'] = sg.get('GroupId')

            if not sg['IpPermissions']:  # for sg with no inbound roles
                _log('SG has no inbound roles, setting to N/A')
                security_group_record['FromPort'] = 'N/A'
                security_group_record['ToPort'] = 'N/A'
                security_group_record['IpProtocol'] = 'N/A'
                security_group_record['Source'] = 'N/A'
                add_sg_record_csv(csv_file, headers, security_group_record)


            for element in sg['IpPermissions']:

                if element['IpProtocol'] != '-1':

                    if element['FromPort'] != -1:
                        security_group_record['FromPort'] = element.get('FromPort')
                        security_group_record['ToPort'] = element.get('ToPort')
                        security_group_record['IpProtocol'] = element.get('IpProtocol')
                    else:
                        _log('SG has no port, setting to N/A')
                        security_group_record['FromPort'] = 'N/A'
                        security_group_record['ToPort'] = 'N/A'
                        security_group_record['IpProtocol'] = element.get('IpProtocol')

                else:  # for '-1' in IpPermissions, print 'All' to csv
                    security_group_record['FromPort'] = 'All'
                    security_group_record['ToPort'] = 'All'
                    security_group_record['IpProtocol'] = 'All'
                #todo - ,
                for group in element['PrefixListIds']:  # if source is another SG , save and add to CSV
                    security_group_record['Source'] = group['PrefixListId']
                    add_sg_record_csv(csv_file, headers, security_group_record)

                for group in element['Ipv6Ranges']:  # if source is another SG , save and add to CSV
                    security_group_record['Source'] = group['CidrIpv6']
                    add_sg_record_csv(csv_file, headers, security_group_record)

                for group in element['UserIdGroupPairs']:  # if source is another SG , save and add to CSV
                    security_group_record['Source'] = group['GroupId']
                    add_sg_record_csv(csv_file, headers, security_group_record)

                for cidr in element['IpRanges']:  # if source a cidr ranger, loop/save/add to csv
                    security_group_record['Source'] = cidr.get('CidrIp')
                    add_sg_record_csv(csv_file, headers, security_group_record)

        _log("INFO: Region END")


def _log(line):
    """
    used instead of print, can log to console and/or log file
    :param line: line to be printed to log
    """

    console = False
    log = False
    if log:
        with open(log_name, "a") as file:
            file.write(str(line) + '\n')
    if console:
        print(line)


if __name__ == '__main__':
    log_name = strftime('sg_log_' + "%Y-%b-%d_%H-%M-%S.log")
    regions = get_config_regions()
    xlsx_name = strftime('sgReport_' + "%Y-%b-%d_%H-%M-%S.xlsx")
    scan_sg()
