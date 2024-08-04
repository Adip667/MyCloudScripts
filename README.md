Few AWS and Azure scripts i wrote when teaching myself python

File name | Description
| ------------- |-------------
sgReport.py | scan AWS for list of Security groups and creates a CSV report with list of inbound ports
cleanResources.py | scan AWS for EC2, EBS, AMI, Snapshop and SG, then it check for tag 'keep' for some of the resources, delete the resources and creates xlsx report with results
