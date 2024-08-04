Few AWS and Azure scripts i wrote when teaching myself python

File name | Description
| ------------- |-------------
SnapshotStorage.py | CLI that calulate the actual size of the AWS EBS snapshost, can then send the report via email or upload to S3
sgReport.py | scan AWS for list of Security groups and creates a CSV report with list of inbound ports
cleanResources.py | CLI that scan AWS for EC2, EBS, AMI, Snapshop and SG, then it check for tag 'keep' for some of the resources, delete the resources and creates xlsx report with results
cleanRG.py | Azure Python script to cleanup resource groups based on tags.
config.txt | config file used by some of the scripts.
SciprtsPermissions.json | used by cleanResources.py
