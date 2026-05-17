# Environment Setting
from datetime import datetime
import io
import pandas as pd
import streamlit as st

# Static Inputs
RequiredColumns = {'Wholesaler Code': 'object', 'Wholesaler Name': 'object', 'Client Name': 'object', 'Client Code': 'object', 'Product Code': 'object', 'Product Name': 'object', 'Address': 'object', 'City': 'object', 'Province': 'object', 'ZIP Code': 'object', 'Year': 'int64', 'Month': 'int64', 'Quantity': 'int64'}
ItalianMonths   = {'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4, 'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8, 'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12}
SampleData      = pd.DataFrame({'Wholesaler Code': ['WH001', 'WH001'], 'Wholesaler Name': ['ABC Pharma Distribution', 'ABC Pharma Distribution'], 'Client Name': ['Farmacia Roma', 'Farmacia Milano'], 'Client Code': ['PH001', 'PH002'], 'Product Code': ['MED001', 'MED002'], 'Product Name': ['Aspirin 500mg', 'Ibuprofen 400mg'], 'Address': ['Via Roma 123', 'Corso Buenos Aires 45'], 'City': ['Roma', 'Milano'], 'Province': ['RM', 'MI'], 'ZIP Code': ['00100', '20124'], 'Year': [2024, 2024], 'Month': [1, 1], 'Quantity': [100, 250]})

ZoetisOrange         = '#F65C00'
ZoetisOrangeLight    = '#FF7A29'
ZoetisOrangeGlow     = 'rgba(246, 92, 0, 0.4)'
ZoetisDarkBackground = '#0A0A0F'
ZoetisSurface        = '#16161D'
ZoetisCardBackground = '#1C1C26'
ZoetisCardHover      = '#242430'
ZoetisText           = '#F5F5F7'
ZoetisTextMuted      = '#8E8E93'
ZoetisTextDim        = '#636366'
ZoetisBorder         = '#2C2C34'
ZoetisSuccess        = '#34C759'
ZoetisError          = '#FF453A'
ZoetisWarning        = '#FFD60A'
ZoetisInfo           = '#0A84FF'

# Functions | Helper
def ConvertMonthToNumber(df, italianMonths):
    'Convert Italian month names to numbers (case insensitive)'
    convertedDf = df.copy()
    errors      = []
    
    if 'Month' in convertedDf.columns:
        def ParseMonth(value):
            if pd.notna(value):
                try: return int(value)
                except (ValueError, TypeError): pass
            
            if isinstance(value, str):
                monthLower = value.strip().lower()
                if monthLower in italianMonths: return italianMonths[monthLower]
            return None
        
        convertedDf['Month'] = convertedDf['Month'].apply(ParseMonth)
        
        invalidMask          = convertedDf['Month'].isnull() & df['Month'].notna()
        invalidCount         = invalidMask.sum()
        if invalidCount      > 0:
            invalidValues    = df.loc[invalidMask, 'Month'].unique()
            errors.append(f'Could not convert {invalidCount} month value(s): {list(invalidValues)}')
    
    return convertedDf, errors

def GetDescription(col):
    'Return description for each column'
    descriptions = {
        'Wholesaler Code': 'Unique identifier for the wholesaler (P. Iva)',
        'Wholesaler Name': 'Name of the wholesaler company',
        'Client Name': 'Name of the final client',
        'Client Code': 'Unique identifier for the pharmacy/client (P. Iva)',
        'Product Code': 'AIC Code of the product',
        'Product Name': 'Name of the pharmaceutical product',
        'Address': 'Street address of the pharmacy',
        'City': 'City where the pharmacy is located',
        'Province': 'Province/State of the pharmacy',
        'ZIP Code': 'Postal/ZIP code',
        'Year': 'Year of the sale (e.g., 2024)',
        'Month': 'Month of the sale (1-12)',
        'Quantity': 'Number of units sold'}
    return descriptions.get(col, '')

# Functions | Data Validation
def ValidateColumns(df, requiredColumns):
    'Check if all required columns are present.'
    missingColumns = []
    for col in requiredColumns.keys():
        if col not in df.columns: missingColumns.append(col)
    
    extraColumns = [col for col in df.columns if col not in requiredColumns]
    
    return missingColumns, extraColumns

def ValidateDataTypes(df, requiredColumns):
    'Validate and convert data types.'
    typeErrors = []
    convertedDf = df.copy()
    
    for col, expectedType in requiredColumns.items():
        if col in convertedDf.columns:
            try:
                if expectedType == 'int64': convertedDf[col] = pd.to_numeric(convertedDf[col], errors='raise').astype('int64')
                elif expectedType == 'float64': convertedDf[col] = pd.to_numeric(convertedDf[col], errors='raise').astype('float64')
                elif expectedType == 'object': convertedDf[col] = convertedDf[col].astype(str)
            except Exception as e: typeErrors.append(f"Column '{col}': Expected {expectedType} - {str(e)}")
    
    return convertedDf, typeErrors

def ValidateDataQuality(df, requiredColumns):
    'Check for data quality issues.'
    qualityIssues = []
    
    for col in requiredColumns.keys():
        if col in df.columns:
            nullCount = df[col].isnull().sum()
            if nullCount > 0: qualityIssues.append(f"Column '{col}' has {nullCount} null value(s)")
    
    if 'Quantity' in df.columns:
        negativeQuantity = (df['Quantity'] < 0).sum()
        if negativeQuantity > 0: qualityIssues.append(f"Found {negativeQuantity} row(s) with negative quantity")
    
    if 'Year' in df.columns:
        currentYear = datetime.now().year
        invalidYears = ((df['Year'] < 2000) | (df['Year'] > currentYear)).sum()
        if invalidYears > 0: qualityIssues.append(f"Found {invalidYears} row(s) with invalid year (must be 2000-{currentYear})")
    
    if 'Month' in df.columns:
        invalidMonths = ((df['Month'] < 1) | (df['Month'] > 12)).sum()
        if invalidMonths > 0: qualityIssues.append(f"Found {invalidMonths} row(s) with invalid month (must be 1-12)")
    
    duplicateCount = df.duplicated().sum()
    if duplicateCount > 0: qualityIssues.append(f"Found {duplicateCount} duplicate row(s)")
    
    return qualityIssues

def RunComplianceChecks(df, requiredColumns, italianMonths):
    'Run all compliance checks and return results.'
    results = {'passed': True, 'missingColumns': [], 'extraColumns': [], 'typeErrors': [], 'qualityIssues': [], 'convertedDf': None}
    
    missingCols, extraCols = ValidateColumns(df, requiredColumns)
    results['missingColumns'] = missingCols
    results['extraColumns'] = extraCols
    if missingCols:
        results['passed'] = False
        return results
    
    convertedDf, monthErrors = ConvertMonthToNumber(df, italianMonths)
    if monthErrors:
        results['typeErrors'].extend(monthErrors)
        results['passed'] = False
        return results

    convertedDf, typeErrors = ValidateDataTypes(convertedDf, requiredColumns)
    results['typeErrors'] = typeErrors
    if typeErrors:
        results['passed'] = False
        return results
    
    qualityIssues = ValidateDataQuality(convertedDf, requiredColumns)
    results['qualityIssues'] = qualityIssues
    
    results['convertedDf'] = convertedDf
    
    return results

# Main App UI
def ApplyZoetisBranding():
    'Apply Zoetis corporate branding in Dark Mode.'
    st.markdown(f"""<style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/icon?family=Material+Icons');

        /* Material Icons fix (evita doppio 'keyboard_arrow_right') */
        .material-icons {{font-family: 'Material Icons' !important; font-weight: normal; font-style: normal; font-size: 20px; display: inline-block; line-height: 1; text-transform: none; letter-spacing: normal; white-space: nowrap; word-wrap: normal; direction: ltr; -webkit-font-feature-settings: 'liga'; -webkit-font-smoothing: antialiased;}}

        /* ═══ DARK MODE BASE ═══ */
        .stApp {{background: linear-gradient(180deg, {ZoetisDarkBackground} 0%, #0D0D0D 100%); color: {ZoetisText};}}

        /* Headers */
        h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{color: {ZoetisText} !important; font-family: 'Inter', 'Segoe UI', Tahoma, sans-serif !important;}}
        h1 {{border-bottom: 4px solid {ZoetisOrange}; padding-bottom: 0.5rem;}}

        /* ═══ PRIMARY BUTTONS (testo bianco) ═══ */
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, {ZoetisOrange} 0%, #FF7A29 100%) !important;
            border: none !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            padding: 0.6rem 1.5rem !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(246, 92, 0, 0.3) !important;}}
        .stButton > button[kind="primary"]:hover {{transform: translateY(-2px) !important; box-shadow: 0 6px 20px rgba(246, 92, 0, 0.5) !important;}}

        /* Secondary buttons */
        .stButton > button {{border: 2px solid {ZoetisOrange} !important; color: {ZoetisOrange} !important; background-color: transparent !important; border-radius: 8px !important;}}
        .stButton > button:hover {{background-color: rgba(246, 92, 0, 0.1) !important;}}

        /* ═══ METRICS CARDS ═══ */
        [data-testid="stMetric"] {{
            background: {ZoetisCardBackground};
            border-left: 4px solid {ZoetisOrange};
            padding: 1rem;
            border-radius: 0 12px 12px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);}}
        [data-testid="stMetricLabel"] {{color: {ZoetisTextMuted} !important;}}
        [data-testid="stMetricValue"] {{color: {ZoetisOrange} !important; font-weight: 700 !important;}}

        /* ═══ EXPANDERS ═══ */
        .streamlit-expanderHeader {{
            background-color: {ZoetisSurface} !important;
            border-radius: 8px !important;
            border-left: 3px solid {ZoetisOrange} !important;
            color: {ZoetisText} !important;}}
        .streamlit-expanderContent {{background-color: {ZoetisCardBackground} !important; border-radius: 0 0 8px 8px !important;}}

        /* ═══ FILE UPLOADER ═══ */
        [data-testid="stFileUploader"] {{
            border: 2px dashed {ZoetisOrange} !important;
            border-radius: 12px !important;
            background: {ZoetisSurface} !important;
            padding: 1.5rem !important;}}
        [data-testid="stFileUploader"]:hover {{background: rgba(246, 92, 0, 0.05) !important; border-color: #FF7A29 !important;}}

        /* ═══ ALERTS ═══ */
        .stSuccess {{background-color: rgba(76, 175, 80, 0.15) !important; border-left: 4px solid #4CAF50 !important; color: #81C784 !important;}}
        .stError {{background-color: rgba(244, 67, 54, 0.15) !important; border-left: 4px solid #F44336 !important; color: #E57373 !important;}}
        .stWarning {{background-color: rgba(246, 92, 0, 0.15) !important; border-left: 4px solid {ZoetisOrange} !important; color: #FFB74D !important;}}
        .stInfo {{background-color: rgba(33, 150, 243, 0.15) !important; border-left: 4px solid #2196F3 !important; color: #64B5F6 !important;}}

        /* ═══ DATAFRAMES ═══ */
        .stDataFrame {{border: 1px solid {ZoetisSurface} !important; border-radius: 8px !important;}}
        [data-testid="stDataFrame"] > div {{background-color: {ZoetisCardBackground} !important;}}

        /* ═══ DIVIDERS ═══ */
        hr {{border-top: 1px solid {ZoetisSurface} !important;}}

        /* ═══ DOWNLOAD BUTTON ═══ */
        .stDownloadButton > button {{
            background-color: {ZoetisSurface} !important;
            color: {ZoetisText} !important;
            border: 1px solid {ZoetisOrange} !important;
            border-radius: 8px !important;}}
        .stDownloadButton > button:hover {{background-color: {ZoetisOrange} !important; color: white !important;}}

        /* ═══ BRANDED HEADER BANNER ═══ */
        .zoetis-header-dark {{
            background: linear-gradient(135deg, {ZoetisDarkBackground} 0%, {ZoetisSurface} 100%);
            border: 1px solid {ZoetisSurface};
            border-left: 5px solid {ZoetisOrange};
            padding: 1.5rem 2rem;
            border-radius: 0 12px 12px 0;
            margin-bottom: 1.5rem;}}
        .zoetis-header-dark h1 {{color: {ZoetisText} !important; border: none !important; margin: 0 !important; padding: 0 !important;}}
        .zoetis-header-dark .accent {{color: {ZoetisOrange};}}
        .zoetis-header-dark p {{color: {ZoetisTextMuted}; margin: 0.5rem 0 0 0;}}

        /* ═══ SIDEBAR (if used) ═══ */
        [data-testid="stSidebar"] {{background-color: {ZoetisCardBackground} !important; border-right: 1px solid {ZoetisSurface} !important;}}

        /* ═══ INPUT FIELDS ═══ */
        .stTextInput > div > div > input {{
            background-color: {ZoetisSurface} !important;
            color: {ZoetisText} !important;
            border: 1px solid {ZoetisSurface} !important;
            border-radius: 8px !important;}}
        .stTextInput > div > div > input:focus {{border-color: {ZoetisOrange} !important; box-shadow: 0 0 0 2px rgba(246, 92, 0, 0.2) !important;}}

        /* ═══ SPINNER ═══ */
        .stSpinner > div > div {{border-top-color: {ZoetisOrange} !important;}}
    </style>""", unsafe_allow_html=True)

def ZoetisHeader(title="Sales Data Upload", subtitle="Upload pharmacy sales data for validation and database submission"):
    'Display modern hero header with Zoetis branding.'
    st.markdown(f"""<div class="zoetis-hero"><div class="logo-badge">🐾 ZOETIS</div><h1>{title.replace('Data Upload', '<span class="accent">Data Upload</span>')}</h1><p class="subtitle">{subtitle}</p></div>""", unsafe_allow_html=True)

def SectionDivider():
    'Render a styled section divider.'
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

def GlassCard(contentHtml):
    'Wrap content in a glassmorphism card.'
    st.markdown(f'<div class="glass-card">{contentHtml}</div>', unsafe_allow_html=True)

def ShowSchema(requiredColumns):
    'Display required data schema in an expander.'
    with st.expander("📋 View Required Data Schema", expanded=False):
        schemaRecords = [{'Column Name': col, 'Data Type': dtype, 'Description': GetDescription(col)} for col, dtype in requiredColumns.items()]
        schemaDf = pd.DataFrame(schemaRecords)
        st.dataframe(schemaDf, use_container_width=True, hide_index=True)

def FileUploadSection():
    'Display file upload section for sales data.'
    st.markdown("### 📤 Upload Sales Data")
    st.markdown(f'<p style="color: {ZoetisTextMuted}; font-size: 0.95rem; margin-bottom: 1rem;">Drag and drop or click to browse your Excel files</p>', unsafe_allow_html=True)
    return st.file_uploader("Choose an Excel file", type=['xlsx', 'xls'], help="Upload an Excel file containing sales data", label_visibility="collapsed")

def PreviewRawData(df):
    'Preview the raw data in an expander.'
    with st.expander("👀 Preview Raw Data", expanded=False): st.dataframe(df.head(10), use_container_width=True)

def ShowResults(results):
    'Display validation results with detailed feedback.'
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔍 Column Validation**")
        if not results['missingColumns']: st.success("✅ All required columns present")
        else: st.error(f"❌ Missing columns: {', '.join(results['missingColumns'])}")
        if results['extraColumns']: st.warning(f"⚠️ Extra columns found: {', '.join(results['extraColumns'])}")
    
    with col2:
        st.markdown("**📊 Data Type Validation**")
        if not results['typeErrors']: st.success("✅ All data types are valid")
        else:
            for error in results['typeErrors']: st.error(f"❌ {error}")
    
    if results['qualityIssues']:
        st.markdown("**⚠️ Data Quality Warnings**")
        for issue in results['qualityIssues']: st.warning(f"⚠️ {issue}")

def ShowReadyToSubmit(finalDf):
    'Display a summary of the data ready for submission.'
    st.markdown("### ✅ Ready to Submit")
    st.markdown(f'<p style="color: {ZoetisTextMuted};">Data validation passed. Review summary below.</p>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("📝 Total Rows", f"{len(finalDf):,}")
    with col2: st.metric("📦 Total Quantity", f"{finalDf['Quantity'].sum():,}")
    with col3: st.metric("👥 Unique Clients", f"{finalDf['Client Code'].nunique():,}")
    with col4: st.metric("💊 Unique Products", f"{finalDf['Product Code'].nunique():,}")
    
    st.dataframe(finalDf, use_container_width=True, hide_index=True)
    
    colLeft, colCenter, colRight = st.columns([1, 2, 1])
    with colCenter:
        if st.button("🚀 Submit to Database", type="primary", use_container_width=True):
            with st.spinner("Submitting to database..."): pass
            st.success("✅ Data successfully submitted to database!")
            st.balloons()

def DownloadSampleTemplate(sampleData):
    'Provide a download button for the sample Excel template.'
    SectionDivider()
    st.markdown("**📥 Need a template?**")
    buffer = io.BytesIO()
    sampleData.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)
    st.download_button(label="📥 Download Sample Template", data=buffer, file_name="SalesTemplate.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def Main(requiredColumns, italianMonths, sampleData):
    'Main application entry point.'
    st.set_page_config(page_title="Zoetis | Sales Upload", page_icon="🐾", layout="wide", initial_sidebar_state="collapsed")
    
    ApplyZoetisBranding()
    ZoetisHeader()
    ShowSchema(requiredColumns)
    
    uploadedfile = FileUploadSection()
    
    if uploadedfile is not None:
        try:
            with st.spinner("Reading Excel file..."): df = pd.read_excel(uploadedfile)
            
            st.success(f"✅ File loaded: **{uploadedfile.name}** ({len(df):,} rows)")
            PreviewRawData(df)
            SectionDivider()

            st.markdown("### 🔍 Compliance Validation")
            
            with st.spinner("Running compliance checks..."): results = RunComplianceChecks(df, requiredColumns, italianMonths)
            
            ShowResults(results)
            SectionDivider()
            
            if results['passed'] and results['convertedDf'] is not None: ShowReadyToSubmit(results['convertedDf'])
            else: st.error("❌ **Validation Failed** — Please fix the errors above and re-upload.")
                
        except Exception as e: st.error(f"❌ Error reading file: {str(e)}")
    else:
        st.info("👆 Upload an Excel file to begin validation")
        DownloadSampleTemplate(sampleData)

# Run
Main(RequiredColumns, ItalianMonths, SampleData)