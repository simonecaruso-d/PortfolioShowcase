# Environment Setting
from dateutil import parser
from datetime import datetime
import pandas as pd
import requests
import warnings
from zoneinfo import ZoneInfo

from streamlit import user

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')
warnings.simplefilter(action='ignore', category=FutureWarning)

# Static Inputs
Headers = {'Authorization': f'Bearer HiddenForSecurity'}

TodayString = datetime.today().strftime('%Y-%m-%d')

OutputDeals      = r"hubspot-crm-exports-all-deals-{today_str}.xlsx".format(today_str=TodayString)
OutputDealsItaly = r"hubspot-custom-reports-deals-products-detail-{today_str}.xlsx".format(today_str=TodayString)

# Transformation Dictionaries
ForcedRawProperties = {'closed_won', 'closed_lost', 'hubspot_owner_id', 'team', 'availability___facility_delivery___total_amount', 'availability___facility_demand___total_amount', 'availability___service_design___total_amount', 'hs_next_meeting_id', 'hs_next_meeting_name', 'hs_next_meeting_start_time'}
StageLabels = {
    '10964765': 'Attract - Target (Sales Program eFM)',
    '10964766': 'Attract - Contact (Sales Program eFM)',
    '14702745': 'Closed won (Public & Private Tenders)',
    '14702746': 'Closed lost (Public & Private Tenders)',
    '14713755': 'Opportunity to monitor (Public & Private Tenders)',
    '14713756': 'Incoming call for tenders (Public & Private Tenders)',
    '14713758': 'In progress (Public & Private Tenders)',
    '14713760': 'Submitted Offer (Public & Private Tenders)',
    '2134631': 'Convert - Opportunity (Sales Program eFM)',
    '2134632': 'Convert - Pre-sales (Sales Program eFM)',
    '2134633': 'Close - Tender Preparation (Sales Program eFM)',
    '2134634': 'Close - Offer Preparation (Sales Program eFM)',
    '2134635': 'Close - Negotiation (Sales Program eFM)',
    '2134636': 'Contract (Sales Program eFM)',
    '2134637': 'Order (Sales Program eFM)',
    '2134638': 'Lost (Sales Program eFM)',
    '85987164': 'RICERCA CLIENTE (Progetto Polis)',
    '85987165': 'PRIMO CONTATTO (Progetto Polis)',
    '85987166': 'OPPORTUNITA\' (Progetto Polis)',
    '85987167': 'NEGOZIAZIONE (Progetto Polis)',
    '85987168': 'PROPOSTA VINCOLANTE (Progetto Polis)',
    '85987169': 'ACCETTAZIONE (Progetto Polis)',
    '88941198': 'SOTTOSCRIZIONE (Progetto Polis)',
    '88941199': 'LOST (Progetto Polis)',}
TeamMapping = {
    'AMS': ' PLATFORM SERVICES - Tech Care Services',
    'DUE DILIGENCE':  ' OCCUPANCY - Due Diligence',
    'ENERGY': ' EXPERIENCE - Energy & Sustainability',
    'ENIGINEERING': ' EXPERIENCE - Engineering',
    'ESSE-RE': ' OCCUPANCY - Esse-Re',
    'FACILITY DELIVER': ' AVAILABILITY - Facility Delivery',
    'FACILITY DEMAND': ' AVAILABILITY - Facility Demand',
    'MYSPOT HUB': ' OCCUPANCY - Place Evolution',
    'PLATFORM SERVICES - ICT': ' PLATFORM SERVICES - ICT',
    'PLATFORM SERVICES - Tech Care': ' PLATFORM SERVICES - TECH CARE',
    'PROJECT-BIM': ' EXPERIENCE - Project',
    'PROPERTY': ' OCCUPANCY - Property',
    'SERVICE DESIGN': ' AVAILABILITY - Service Design',
    'SPACE MANAGEMENT': ' OCCUPANCY - Space Management',
    'WORKPLACE': ' ENGAGEMENT - Workplace',
    'EXPERIENCE - Re-Con': ' EXPERIENCE - Re-Con'}
RecordSourceMap = {'CRM_UI': 'CRM UI', 'INTERNAL_PROCESSING': 'HubSpot Processing', 'IMPORT': 'Import', 'MOBILE_IOS': 'Mobile iOS'}
ForecastMap = {'PIPELINE': 'Pipeline', 'BEST_CASE': 'Best case', 'COMMIT': 'Commit', 'CLOSED': 'Closed won', 'OMIT': 'Not forecasted'}
ItalyColsMap = {
    'Record ID': 'Deal ID',
    'Deal Country': 'Deal Country',
    'Deal owner': 'Deal owner',
    'Deal Stage': 'Deal Stage',
    'Deal Name': 'Deal Name',
    'Pipeline': 'Pipeline',
    'Project Code (ERP)': 'Project Code (ERP)',
    'Priority': 'Priority',
    'HubSpot Team': 'HubSpot Team',
    'Market Side': 'Market Side',
    'Create Date': 'Create date (Deal) - Daily',
    'Last Modified Date': 'Last modified date (Deal) - Daily',
    'Lost Date': 'Lost Date - Daily',
    'Amount': 'Deal Amount',
    'Company name': 'Company name',
    'Team': 'Deal Teams (not required)'}

# Example DataFrame for Comparison
ExampleFile      = r"Deals\RealOutputDeals.xlsx"
ExampleDf        = pd.read_excel(ExampleFile)

# Time Fields
def GenerateTimeFields(prefix, stages):
    return {f"{prefix}_{stageId}": f'{label}' for stageId, label in stages.items()}

CumulativeTimeFields = GenerateTimeFields('hs_v2_cumulative_time_in', StageLabels)
LatestTimeFields     = GenerateTimeFields('hs_v2_latest_time_in', StageLabels)

RequiredColumns = set(ExampleDf.columns.str.strip()) | {'hs_object_id', 'notes_last_updated', 'hs_is_closed_lost', 'hs_is_closed_won'} | set(CumulativeTimeFields.keys()) | set(LatestTimeFields.keys()) | ForcedRawProperties

# Property Name Mapping
def GetFilteredPropertyDefinitions():
    url        = 'https://api.hubapi.com/crm/v3/properties/deals'
    response   = requests.get(url, headers=Headers)
    response.raise_for_status()
    properties = response.json().get("results", [])
    return {property['name']: property.get('label', property['name']) for property in properties if property.get('label', property['name']) in RequiredColumns or property['name'] in RequiredColumns}

PropertyNameMap = GetFilteredPropertyDefinitions()
PropertyNameMap.update({K: f'Cumulative time in "{V}" (HH:mm:ss)' for K, V in CumulativeTimeFields.items()})
PropertyNameMap.update({K: f'Latest time in "{V}" (HH:mm:ss)' for K, V in LatestTimeFields.items()})

PropertyNameMap.update({
    'notes_last_updated': 'Last Activity Date',
    'hs_is_closed_lost': 'Is closed lost',
    'hs_is_closed_won': 'Is Closed Won',
    'availability___facility_delivery___total_amount': ' AVAILABILITY - Facility Delivery - Total Amount',
    'availability___facility_demand___total_amount': ' AVAILABILITY - Facility Demand - Total Amount',
    'availability___service_design___total_amount': ' AVAILABILITY - Service Design - Total Amount',
    "hs_next_meeting_id": "Next Meeting ID",
    "hs_next_meeting_name": "Next Meeting Name",
    "hs_next_meeting_start_time": "Next Meeting Start Time"})

# Data Retrieval and Initial Processing
def GetFilteredDeals():
    propertyKeys       = list(PropertyNameMap.keys())
    propertyParameters = '&'.join([f"properties={property}" for property in propertyKeys])
    deals              = []
    after              = None
    while True:
        url = f'https://api.hubapi.com/crm/v3/objects/deals?limit=100&{propertyParameters}&associations=company&associations=contact'
        if after: url += f'&after={after}'
        response = requests.get(url, headers=Headers)
        data     = response.json()
        deals.extend(data['results'])
        if 'paging' in data and 'next' in data['paging']: after = data['paging']['next']['after']
        else: break
    return pd.json_normalize(deals)

def FetchNamesByIdsForAssoc(ids, objectType):
    names = {}
    endpoint = {'company': 'companies','contact': 'contacts'}[objectType]

    for chunkStart in range(0, len(ids), 100):
        chunk   = ids[chunkStart:chunkStart + 100]
        url     = f'https://api.hubapi.com/crm/v3/objects/{endpoint}/batch/read'
        payload = {'properties': ['name', 'firstname', 'lastname'], 'inputs': [{'id': str(i)} for i in chunk]}

        response = requests.post(url, headers=Headers, json=payload)

        if response.status_code in [200, 207]:
            data = response.json()
            for obj in data.get('results', []):
                objId = str(obj['id'])
                props = obj.get('properties', {})
                if objectType == 'company': names[objId] = props.get('name', '')
                else: names[objId] = f'{props.get("firstname", "")} {props.get("lastname", "")}'.strip()
        else: print(f'❌ Failed fetching {objectType} names: {response.status_code}')

    return names

def ExtractAssociations(df):
    def ExtractIds(col):
        if isinstance(col, list):
            seen = set()
            ids = []
            for item in col:
                val = str(item.get("id", "")).strip()
                if val and val not in seen:
                    seen.add(val)
                    ids.append(val)
            return '; '.join(ids)
        return ''
    
    df['Associated Company IDs'] = df.get('associations.companies.results', []).apply(ExtractIds)
    df['Associated Contact IDs'] = df.get('associations.contacts.results', []).apply(ExtractIds)

    allCompanyIds = df['Associated Company IDs'].dropna().astype(str).str.split(";").explode().str.strip().unique().tolist()
    allContactIds = df['Associated Contact IDs'].dropna().astype(str).str.split(";").explode().str.strip().unique().tolist()
    companyNames  = FetchNamesByIdsForAssoc(allCompanyIds, 'company')
    contactNames  = FetchNamesByIdsForAssoc(allContactIds, 'contact')

    def GetPrimaryName(idListString, mapping):
        ids = [i.strip() for i in idListString.split(";") if i.strip()]
        return mapping.get(ids[0], "") if ids else ""

    def GetAllNames(idListString, mapping):
        ids   = [i.strip() for i in idListString.split(";") if i.strip()]
        seen  = set()
        names = []
        for i in ids:
            name = mapping.get(i)
            if name and name not in seen:
                seen.add(name)
                names.append(str(name))
        return '; '.join(names)

    df['Associated Company']               = df['Associated Company IDs'].apply(lambda x: GetAllNames(x, companyNames))
    df['Associated Company (Primary)']     = df['Associated Company IDs'].apply(lambda x: GetPrimaryName(x, companyNames))
    df['Associated Company IDs (Primary)'] = df['Associated Company IDs'].apply(lambda x: x.split(";")[0].strip() if x else "")
    df['Associated Contact']               = df['Associated Contact IDs'].apply(lambda x: GetAllNames(x, contactNames))

    return df

DealsDf         = GetFilteredDeals()
DealsDf         = ExtractAssociations(DealsDf)
DealsDf.columns = DealsDf.columns.str.replace(r"^properties\.", "", regex=True)

if 'hubspot_owner_id' in DealsDf.columns: DealsDf['owner_id_raw'] = DealsDf['hubspot_owner_id']

DealsDf.rename(columns={K: V for K, V in PropertyNameMap.items() if K in DealsDf.columns}, inplace=True)

# Further Transformations and Enrichments
def MillisecondsToHhmmss(Value):
    try:
        if pd.isna(Value): return ''
        ms = float(Value)
        if ms < 0: return ''
        totalSeconds = int(round(ms / 1000))
        hours = totalSeconds // 3600
        minutes = (totalSeconds % 3600) // 60
        seconds = totalSeconds % 60
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    except: return ''

def ApplyMillisecondsConversion(df, fieldMap, prefix):
    for _, label in fieldMap.items():
        colName = f'{prefix} in "{label}" (HH:mm:ss)'
        if colName in df.columns: df[colName] = df[colName].apply(MillisecondsToHhmmss)

ApplyMillisecondsConversion(DealsDf, CumulativeTimeFields, 'Cumulative time')
ApplyMillisecondsConversion(DealsDf, LatestTimeFields, 'Latest time')

if 'hs_object_id' in DealsDf.columns: DealsDf['Record ID'] = DealsDf['hs_object_id']

# Other API Calls
def FetchPaginated(Url, ResultKey="results"):
    results = []
    after   = None
    while True:
        params   = {'limit': 100}
        if after: params['after'] = after
        response = requests.get(Url, headers=Headers, params=params)
        response.raise_for_status()
        data     = response.json()
        results.extend(data.get(ResultKey, []))
        after    = data.get('paging', {}).get('next', {}).get('after')
        if not after: break
    return results

def GetUserIdNameMap():
    allUsers = FetchPaginated('https://api.hubapi.com/settings/v3/users')
    return {str(user['id']): f"{user.get('firstName', '')} {user.get('lastName', '')}".strip() for user in allUsers}

def GetOwnerMap():
    allOwners = FetchPaginated('https://api.hubapi.com/crm/v3/owners')
    return {str(owner['id']): f"{owner.get('firstName', '')} {owner.get('lastName', '')}".strip() for owner in allOwners}

def GetPipelineStageMap():
    url         = 'https://api.hubapi.com/crm/v3/pipelines/deals'
    response    = requests.get(url, headers=Headers)
    result      = response.json()
    stageMap    = {}
    pipelineMap = {}
    for pipeline in result.get('results', []):
        pipelineMap[pipeline['id']] = pipeline.get('label', pipeline['id'])
        for stage in pipeline.get('stages', []): stageMap[stage['id']] = stage.get('label', stage['id'])
    return pipelineMap, stageMap

def GetTeamMap():
    url      = 'https://api.hubapi.com/settings/v3/users/teams'
    response = requests.get(url, headers=Headers)
    response.raise_for_status()
    result   = response.json()
    return {str(team['id']): team.get('name', '') for team in result.get('results', [])}

UserMap = GetUserIdNameMap()
if 'Updated by user ID' in DealsDf.columns: DealsDf['Updated by user ID'] = DealsDf['Updated by user ID'].apply(lambda X: UserMap.get(str(int(float(X))) if pd.notna(X) else '', ''))

OwnerMap = GetOwnerMap()
if 'owner_id_raw' in DealsDf.columns: DealsDf['Deal owner'] = DealsDf['owner_id_raw'].apply(lambda X: OwnerMap.get(str(int(float(X))) if pd.notna(X) else '', ''))

PipelineMap, StageMap = GetPipelineStageMap()
TeamMap = GetTeamMap()

# Further Cleaning and Normalization
def SafeId(Val):
    try:
        if pd.isna(Val) or str(Val).strip() == '': return None
        return str(int(float(Val))).strip()
    except: return None

def ReplaceIdsWithLabels(df):
    if 'Deal Stage' in df.columns: df['Deal Stage'] = df['Deal Stage'].apply(lambda X: StageMap.get(SafeId(X), X))
    if 'Pipeline' in df.columns: df['Pipeline'] = df['Pipeline'].apply(lambda X: PipelineMap.get(SafeId(X), X))
    if 'HubSpot Team' in df.columns: df['HubSpot Team'] = df['HubSpot Team'].apply(lambda X: TeamMap.get(SafeId(X), X))
    return df

DealsDf = ReplaceIdsWithLabels(DealsDf)

if 'Pipeline' in DealsDf.columns           : DealsDf['Pipeline'] = DealsDf['Pipeline'].replace("default", "Sales Program eFM")
if 'Record source' in DealsDf.columns      : DealsDf['Record source'] = DealsDf['Record source'].map(RecordSourceMap).fillna(DealsDf['Record source'])
if 'Forecast category' in DealsDf.columns  : DealsDf['Forecast category'] = DealsDf['Forecast category'].map(ForecastMap).fillna(DealsDf['Forecast category'])
if 'Sales Program' in DealsDf.columns      : DealsDf['Sales Program'] = DealsDf['Sales Program'].replace({'Sales Program': 'Sales Program eFM'})
if 'Sales Program Scope' in DealsDf.columns: DealsDf['Sales Program Scope'] = DealsDf['Sales Program Scope'].astype(str).str.replace(r"\s*;\s*", "; ", regex=True).str.strip()

def NormalizeTeam(value):
    if not value or pd.isna(value): return ''
    segments = [TeamMapping.get(Seg.strip(), Seg.strip()) for Seg in str(value).split(";")]
    return '; '.join(sorted(set(filter(None, segments))))

if 'Team' in DealsDf.columns: DealsDf['Team'] = DealsDf['Team'].apply(NormalizeTeam)

for Col in DealsDf.columns:
    if Col in ExampleDf.columns:
        if ExampleDf[Col].dtype == 'bool':
            if Col in ['Is closed lost', 'Is Closed Won']: continue
            DealsDf[Col] = DealsDf[Col].fillna(False).astype(bool)
        elif ExampleDf[Col].dtype == 'object': 
            if Col in ['Create Date', 'Close Date', 'Last Activity Date']: continue
            DealsDf[Col] = DealsDf[Col].astype(str).str.strip().replace('nan', pd.NA)
        elif pd.api.types.is_numeric_dtype(ExampleDf[Col]): DealsDf[Col] = pd.to_numeric(DealsDf[Col], errors='coerce')
        elif pd.api.types.is_datetime64_any_dtype(ExampleDf[Col]):
            try:
                if Col not in ['Create Date', 'Close Date', 'Last Activity Date']:
                    DealsDf[Col] = pd.to_datetime(DealsDf[Col], errors='coerce', utc=True)
                    if isinstance(DealsDf[Col].dtype, pd.DatetimeTZDtype): DealsDf[Col] = DealsDf[Col].dt.tz_convert('Europe/Rome').dt.tz_localize(None)
                    DealsDf[Col] = DealsDf[Col].dt.floor('min')
            except Exception as E: print(f"⚠️ Error processing datetime column '{Col}': {E}")

if 'Record ID' in DealsDf.columns         : DealsDf['Record ID'] = pd.to_numeric(DealsDf['Record ID'], errors='coerce').astype('Int64')
if 'Priority' in DealsDf.columns          : DealsDf['Priority'] = DealsDf['Priority'].apply(lambda X: X.capitalize() if isinstance(X, str) and X.strip() != '' else '')
if 'Circle' in DealsDf.columns            : DealsDf['Circle'] = DealsDf['Circle'].astype(str).str.replace(r"\s*;\s*", "; ", regex=True).str.strip()
if 'Città di Interesse' in DealsDf.columns: DealsDf['Città di Interesse'] = DealsDf['Città di Interesse'].astype(str).str.replace(r";(?!\s)", '; ', regex=True).str.strip()

def SafeParseDatetime(val):
    try:
        if pd.isna(val) or str(val).strip() in ['', 'None', 'nan']: return pd.NaT
        dt = parser.isoparse(str(val))
        if dt.tzinfo is not None: dt = dt.astimezone(ZoneInfo('Europe/Rome'))
        return dt.replace(second=0, microsecond=0)
    except Exception as E:
        print(f"⚠️ Failed to parse: {val} → {E}")
        return pd.NaT

for Col in ['Create Date', 'Close Date', 'Last Activity Date']:
    if Col in DealsDf.columns:
        DealsDf[Col] = DealsDf[Col].apply(SafeParseDatetime)
        DealsDf[Col] = DealsDf[Col].dt.strftime("%Y-%m-%d %H:%M:%S")

FinalCols       = [Col for Col in ExampleDf.columns if Col in DealsDf.columns]
DealsDfForItaly = DealsDf.copy()
DealsDf         = DealsDf[FinalCols]
DealsDf         = DealsDf.fillna('').replace('None', '')
DealsDf.to_excel(OutputDeals, index=False)
print(f'✅ Exported Deals to {OutputDeals}')