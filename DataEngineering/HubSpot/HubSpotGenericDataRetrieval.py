# Environment Setting
import pandas as pd 
import requests

# API Request Elements
payload={}
headers = {'Authorization': 'Hidden for security reasons'}

# Functions
def HubSpotRequest(url, headers, payload):
    response = requests.request('GET', url, headers=headers, data=payload)
    dataJson = response.json()
    results  = dataJson['results']
    after    = dataJson['paging']['next']['after']
    lenght   = len(dataJson)
    df       = pd.DataFrame.from_dict(pd.json_normalize(results), orient='columns')
    
    while lenght>1:
        responseTwo = requests.request('GET', f'{url}&after={after}', headers=headers, data=payload)
        dataJsonTwo = responseTwo.json()
        resultsTwo  = dataJsonTwo['results']
        lenght      = len(dataJsonTwo)
        dfTwo       = pd.DataFrame.from_dict(pd.json_normalize(resultsTwo), orient='columns')
        df          = pd.concat([df, dfTwo], ignore_index=True)
        if lenght>1: after=dataJsonTwo['paging']['next']['after']
    
    return df

# Run
OwnersDf     = HubSpotRequest('https://api.hubapi.com/owners/v2/owners', headers, payload)
LineItemsDf  = HubSpotRequest('https://api.hubapi.com/crm/v4/objects/line_items/?properties=name&properties=hs_product_id&properties=quantity&properties=hs_tcv&properties=hs_margin_tcv&properties=price&associations=deals&limit=100', headers, payload)
CSMDomainsDf = HubSpotRequest('https://api.hubapi.com/cms/v3/domains', headers, payload)
MeetingsDf   = HubSpotRequest('https://api.hubapi.com/crm/v3/objects/meetings?limit=100&properties=hs_meeting_title&properties=hubspot_owner_id&properties=hs_meeting_start_time&properties=hs_meeting_end_time&properties=hs_meeting_outcome&associations=companies&associations=contacts&associations=deals', headers, payload)
ProductsDf   = HubSpotRequest('https://api.hubapi.com/crm/v4/objects/products/?properties=hs_all_owner_ids&properties=hs_all_team_ids&properties=hs_lastmodifieddate&properties=name&properties=amount&properties=hs_product_type&properties=description&properties=quantity&properties=price&limit=100', headers, payload)

# Export
OwnersDf.to_excel('Owners.xlsx', sheet_name= 'Owners', index=False, header=True)
LineItemsDf.to_excel('LineItems.xlsx', sheet_name= 'Line Items', index=False, header=True)
CSMDomainsDf.to_excel('CSMDomains.xlsx', sheet_name= 'CSM Domains', index=False, header=True)
MeetingsDf.to_excel('Meetings.xlsx', sheet_name= 'Meetings', index=False, header=True)
ProductsDf.to_excel('Products.xlsx', sheet_name= 'Products', index=False, header=True)