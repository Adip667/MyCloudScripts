# todo - connect to auzre
# todo - get list of RG
# todo - check tags
# todo - delete RG

from azure.mgmt.resource import SubscriptionClient, ResourceManagementClient
from azure.identity import ClientSecretCredential

client_secret = '1'
client_id = '2'
tenant_id ='3'
subscription_id = '4'

credential = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
subscription_client = SubscriptionClient(credential)

for sub in subscription_client.subscriptions.list():
    print(sub)
    print(sub.__getattribute__('subscription_id'))

resource_client = ResourceManagementClient(credential, subscription_id)
group_list = resource_client.resource_groups.list()

for RG in group_list:
    if RG.__getattribute__('tags') is None :
        print('Deleting Name: ' + RG.__getattribute__('name'))
        delete_async_operation = resource_client.resource_groups.begin_delete(RG.__getattribute__('name'))

    elif 'keep' not in RG.__getattribute__('tags'):
        print('Deleting Name: ' + RG.__getattribute__('name')  + ', Tag ' + str(RG.__getattribute__('tags')) )
        delete_async_operation = resource_client.resource_groups.begin_delete(RG.__getattribute__('name'))

    else: print('keeping: ' + RG.__getattribute__('name'))
