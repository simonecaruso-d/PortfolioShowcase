# Environment Setting
from autogen import AssistantAgent
import gradio as gr
from fpdf import FPDF
import io
import markdown
from markitdown import MarkItDown
import os
import re
import streamlit as st
import tempfile
import warnings
warnings.filterwarnings("ignore", message="Couldn't find ffmpeg or avconv")

# Keys & Paths
OpenRouterUrl = "https://openrouter.ai/api/v1"
OpenRouterKey = "or-sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
CVBaseDirectory = r"People Sheets"

# Functions - Parse Curricula
def FileToString(filePath):
    converter   = MarkItDown(enable_plugins=False)
    result      = converter.convert(filePath)
    textContent = result.text_content
    textContent = re.sub(r'(?<!\n)\n(?!\n)', ' ', textContent)
    textContent = re.sub(r'\n{2,}', '\n', textContent)
    lines       = textContent.split('\n')
    newLines    = []
    
    for line in lines:
        if len(line.strip()) > 0 and len(line) < 80:
            if newLines: newLines[-1] += ' ' + line.strip()
            else: newLines.append(line.strip())
        else: newLines.append(line.strip())
    return '\n'.join(newLines)

def ParseCV(baseDirectory, personName):
    for root, directories, _ in os.walk(baseDirectory):
        personName = personName.upper()
        if personName in directories:
            personFolder = os.path.join(root, personName)
            for file in os.listdir(personFolder):
                if file.lower().endswith(".pdf") or file.lower().endswith(".doc") or file.lower().endswith(".docx"): return FileToString(os.path.join(personFolder, file))
    return None

def ParseMultipleCVs(baseDirectory, personNames):
    resultDictionary = {}
    for personName in personNames:
        personName = personName.strip().upper()
        result = ParseCV(baseDirectory, personName)
        if result: resultDictionary[personName] = result
        else: resultDictionary[personName] = "⛔ Curriculum non trovato o formato non supportato."
    return resultDictionary

# Functions - Agents
def GenerateAnswer(model, modelName, userPropmt, terminationMessage, conversationHistory):
    if conversationHistory == []: context = f"{userPropmt}"
    else: context = f"{userPropmt}" + '\nResults from Previous Discussion:' + f"\n{conversationHistory}"

    chatResult = model.initiate_chat(model, message = context)
    chatMessages = [msg["content"] for msg in chatResult.chat_history if msg["name"] == modelName]
    finalMessage = chatMessages[-3] if chatMessages[-1] == terminationMessage  else chatMessages[-1]

    return finalMessage

Instructor = AssistantAgent(
        name="Instructor",
        llm_config={"config_list": [{"model": "qwen/qwen3-30b-a3b:free", "base_url": OpenRouterUrl, "api_key": OpenRouterKey}], "temperature": 0.1},
        is_termination_msg=lambda x: "||TERMINATION||" in x.get("content", "").rstrip(),
        system_message=f"""Ruolo: Esperto interprete di gare pubbliche, offerte e appalti.
                            Obiettivo: Il tuo compito consiste nel tradurre i requisiti generali di gara in istruzioni pratiche e dettagliate per la strutturazione dei curriculum vitae dei partecipanti al progetto.
                               
                            Flusso che devi seguire:
                            1. Leggi attentamente il RequisitoInformativo dato dall'utente e assicurati di comprenderlo appieno, senza aggiungere o assumere nulla che non sia specificato.
                            2. Sintetizza il tipo di contenuto richiesto nel RequisitoInformativo, e correda questa sintesi con un elenco puntato con i campi necessari da includere.
                            3. Non inserire commenti o spiegazioni aggiuntive. 
                            4. Scrivi il tutto in termini di esigenza su singola persona, invece che su gruppi di persone.
                            5. Concludi con la stampa del testo: ||TERMINATION||.""")
Synthetizer = AssistantAgent(
        name="Synthetizer",
        llm_config={"config_list": [{"model": "deepseek/deepseek-r1:free", "base_url": OpenRouterUrl, "api_key": OpenRouterKey}], "temperature": 0.1},
        is_termination_msg=lambda x: "||TERMINATION||" in x.get("content", "").rstrip(),
        system_message=f"""Ruolo: Sales Account per bandi di gara.
                            Obiettivo: Il tuo compito consiste nel sintetizzare bandi di gara in testi dalla dimensione notevolmente più contenuta.
                               
                            Flusso che devi seguire:
                            1. Leggi attentamente il BandoDiGara dato dall'utente e assicurati di comprenderlo appieno, senza aggiungere o assumere nulla che non sia specificato.
                            2. Sintetizza il BandoDiGara: metti il focus su contenuti, ambiti e attività e ignora completamente date, riferimenti normativi, requisiti numerici e informazioni di contatto.
                            3. Non inserire commenti o spiegazioni aggiuntive. 
                            4. Concludi con la stampa del testo: ||TERMINATION||.""")
Drafter = AssistantAgent(
        name="Drafter",
        llm_config={"config_list": [{"model": "meta-llama/llama-4-maverick:free", "base_url": OpenRouterUrl, "api_key": OpenRouterKey}], "temperature": 0.1},
        is_termination_msg=lambda x: "||TERMINATION||" in x.get("content", "").rstrip(),
        system_message=f"""Ruolo: Elaboratore di Curriculum Vitae.
                            Obiettivo: Il tuo compito consiste nell'analizzare il Curriculum e generarne una versione che rispetta le indicazioni che ti vengono fornite nel RequisitoInformativo.

                            Flusso che devi seguire:
                            1. Leggi e comprendi il RequisitoInformativo fornito, seguendo con precisione le linee guida per il tipo di contenuto richiesto e i campi necessari.
                            2. Esamina attentamente ogni Curriculum ricevuto, identificando le informazioni pertinenti richieste nel RequisitoInformativo.
                            3. Genera un testo che contiene quanto richiesto nel RequisitoInformativo, popolato in base al Curriculum, assicurandoti di non omettere nessuna informazione necessaria.
                            4. Mantieni l'integrità dei dati e non aggiungere informazioni che non siano contenute nel Curriculum.
                            5. Non includere commenti o spiegazioni, limitandoti a produrre l'output richiesto.
                            6. Concludi con la stampa del testo: ||TERMINATION||.""")
Seller = AssistantAgent(
        name="Seller",
        llm_config={"config_list": [{"model": "deepseek/deepseek-chat-v3-0324:free", "base_url": OpenRouterUrl, "api_key": OpenRouterKey}], "temperature": 0.1},
        is_termination_msg=lambda x: "||TERMINATION||" in x.get("content", "").rstrip(),
        system_message=f"""Ruolo: Sales Account per bandi di gara.
                            Obiettivo: Il tuo compito consiste nell'analizzare il Curriculum e generarne una versione che ben si adatti ai contenuti del BandoDiGara.

                            Flusso che devi seguire:
                            1. Leggi e comprendi il BandoDiGara fornito, capendo quali sono gli elementi strategicamente più importanti per garantirne la vittoria.
                            2. Esamina attentamente il Curriculum ricevuto, identificando i punti di forza e quelli di debolezza rispetto al BandoDiGara.
                            3. Riscrivi il Curriculum adattandolo al BandoDiGara. Non aggiungere numeri, leggi o altre informazioni quantitative. Limitati a cambiamenti minimali.
                            4. Adatta l'output da te prodotto al DizionarioRuoli, che contiene i ruoli di ogni persona coinvolta nel progetto.
                            5. Non includere commenti o spiegazioni, limitandoti a produrre l'output richiesto.
                            6. Concludi con la stampa del testo: ||TERMINATION||.""")
Reviewer = AssistantAgent(
        name="Reviewer",
        llm_config={"config_list": [{"model": "deepseek/deepseek-chat-v3-0324:free", "base_url": OpenRouterUrl, "api_key": OpenRouterKey}], "temperature": 0.3},
        is_termination_msg=lambda x: "||TERMINATION||" in x.get("content", "").rstrip(),
        system_message=f"""Ruolo: Revisore di Curriculum.
                            Obiettivo: Il tuo compito consiste nell'analizzare il RequisitoUtente e adattare il Curriculum di conseguenza, senza inventare dati o informazioni.

                            Flusso che devi seguire:
                            1. Esamina a fondo il Curriculum, il BandoDiGara e il RequisitoUtente.
                            2. Adatta il Curriculum al RequisitoUtente, senza però dimenticare la coerenza col BandoDiGara.
                            3. Utilizza come base il Curriculum originale, apportando modifiche minime e necessarie per soddisfare il RequisitoUtente, avendo cura di non aggiungere informazioni che non siano già presenti nel Curriculum.
                            4. Non includere commenti o spiegazioni, limitandoti a produrre l'output richiesto.
                            5. Concludi con la stampa del testo: ||TERMINATION||.""")

# Functions - Logic
def AuctionSynthetize(files):
    auctionCall    = ''
    fileList       = []
    for file in files: fileList.append(file.name)
    fileListString = " ".join(fileList)
    filePaths      = re.findall(r'C:\\[A-Za-z0-9_\\\\.]+\.pdf', fileListString)
    for path in filePaths: auctionCall += FileToString(path)
    auctionCall    = GenerateAnswer(Synthetizer, "Synthetizer", f"BandoDiGara: {auctionCall}", "||TERMINATION||", ConversationHistory=[]).replace("||TERMINATION||", "")
    return "✅ Sintesi completata!", auctionCall

def GenerateProfiles(cvRequirement, auctionSynthesis, names, rolesDictionary):
    cvData            = ParseMultipleCVs(CVBaseDirectory, names.split(","))
    generatedProfiles = {}
    markdownOutput    = ""

    for name, curriculum in cvData.items():
        contextFormatter        = f"RequisitoInformativo: {cvRequirement}. Curriculum: {curriculum}."
        draft                   = GenerateAnswer(Drafter, "Drafter", contextFormatter, "||TERMINATION||", []).replace("||TERMINATION||", "")
        contextSeller           = f"BandoDiGara: {auctionSynthesis}. \n Curriculum: {draft}. \n DizionarioRuoli: {rolesDictionary}."
        sellingAnswer           = GenerateAnswer(Seller, "Seller", contextSeller, "||TERMINATION||", []).replace("||TERMINATION||", "").strip()
        generatedProfiles[name] = {'CurriculumData': curriculum, 'FormattedAnswer': draft, 'SellingAnswer': sellingAnswer}
        markdownOutput          += f"### {name.title()}\n\n{sellingAnswer}\n\n---\n"

    return generatedProfiles, "✅ Profili generati!", markdownOutput

def DiscussProfiles(auctionSynthesis, generatedProfiles, userInput, chatHist):
    if not generatedProfiles: return chatHist + [("⚠️", "Nessun profilo disponibile da modificare.")], chatHist
    newChat    = []
    curriculum = {name: profile['SellingAnswer'] for name, profile in generatedProfiles.items()}
    context    = f"""Curriculum: {curriculum}\n BandoDiGara: {auctionSynthesis}\n RequisitoUtente: {userInput}"""
    reviewed   = GenerateAnswer(Reviewer, "Reviewer", context, "||TERMINATION||", chatHist)
    reviewed   = reviewed.replace("||TERMINATION||", "").strip()
    newChat.append((userInput, reviewed))
    chatHist.extend(newChat)
    return chatHist, chatHist

def ResetAll():
    return ("", None, "", "", "", "", "", "", None, None, [], [])

def GeneratePDF(conversationHistory, sellerOutput):
    if conversationHistory:
        if len(conversationHistory[-1][1]) > 5: lastResponse = conversationHistory[-1][1]
        else: lastResponse = 'Conversation History esiste ma è breve'
    elif sellerOutput: lastResponse = sellerOutput
    else: lastResponse = 'Nessun profilo generato'

    lastResponse = re.sub(r'[^\x00-\x7F]+', ' ', lastResponse)
    lastResponse = re.sub(r'[^a-zA-Z0-9\s.,:;/-àèéò@]', '', lastResponse)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Profili Generati", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, lastResponse)
        
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tempFile:
        pdf.output(tempFile.name)
        return "✅ PDF generato con successo!", tempFile.name

# Main
with gr.Blocks() as demo:
    gr.HTML("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
   
    body {
        margin: 0;
        padding: 0;
        font-family: 'Inter', sans-serif;
        background: #717171;
        color: #222;
        background-size: cover;
    }
 
    /* Header */
    .title-container {
        text-align: center;
        padding: 60px 20px 40px;
        position: relative;
        z-index: 2;
        padding-bottom: 0px !important;
        padding-top: 0px !important;
    }
 
    .title-container h1 {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 10px;
        color: #6757f6 !important;
        text-transform: uppercase;
 
    }
 
    .title-container p {
        font-size: 18px;
        color: #555;
        opacity: 0.9;
        margin-bottom: 0px !important;
    }
 
    /* Animazione gradienti */
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
 
    /* Sezioni con effetto Glassmorphism */
    .glass-section {
        padding: 30px 10%;
        max-width: 800px;
        margin: auto;
        background: rgba(255, 255, 255, 0.4);
        backdrop-filter: blur(10px);
        border-radius: 30px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.1);
        transition: all 0.3s ease-in-out;
    }
    .gr-button, button[class*="primary"] {
        border-radius: 30px !important;
        background-color: #6757f6 !important
    }
    .gr-button, button[class*="secondary"]{
        border-radius: 30px !important;
        background-color: #fc9644 !important
    }
    .gr-button, button[class*="stop"]{
        border-radius: 30px !important;
        background-color: #717171 !important
    }
    /* Gradiente per i bottoni con animazione */
    .gr-button {
        background: linear-gradient(135deg, #5A6B4F, #A57A64);
        color: white;
        font-weight: 600;
        font-size: 16px;
        border: none;
        padding: 14px 26px;
        border-radius: 30px;
        box-shadow: 0 8px 20px rgba(90, 107, 79, 0.2);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
 
    .gr-button:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 24px rgba(90, 107, 79, 0.3);
    }
    .input-container input, .input-container textarea {
        background: #d9d5fd !important;
        border-radius: 30px !important;
        color: #000 !important;
    }
    .input-container input::placeholder,
    .input-container textarea::placeholder {
        color: #000 !important;
 
    /* Sfumatura sui campi di input e textarea */
    textarea, input {
        background: rgba(255, 255, 255, 0.6);
        border: none;
        border-radius: 12px;
        padding: 14px;
        font-size: 16px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        color: #333;
        transition: background 0.3s ease;
    }
 
    textarea:focus, input:focus {
        background: rgba(255, 255, 255, 0.8);
        outline: none;
    }
    /* Force center alignment of the upload component label */
    .small-upload {
        height: 40px !important; /* Or any smaller value you prefer */
        padding: 8px !important;
    }
           
    .small-upload .wrap {
        display: flex !important;
        font-size: 14px !important;
        align-items: center;
        justify-content: center;
        height: 60% !important;
        text-align: center;
        padding: 0 10px;
        min-height: unset !important;
    }
 
    .small-upload .wrap label {
        width: 100%;
        font-size: 16px !important;
        font-weight: 600;
        line-height: 1.4;
        display: block;
    }
    .small-upload button {
        height: 100% !important;
        padding: 4px 8px !important;
        font-size: 10px !important;
    }
 
    /* Chatbot con effetto Glassmorphism */
    .gr-chatbot {
        background: rgba(255, 255, 255, 0.4);
        backdrop-filter: blur(8px);
        border-radius: 16px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
 
    /* Effetto scroll trasparente per il background */
    .gr-chatbot .messages {
        background: rgba(255, 255, 255, 0.6);
        backdrop-filter: blur(10px);
    }
 
    /* Etichette con stile più moderno */
    label {
        font-weight: 600;
        margin-bottom: 4px;
        color: #444;
    }
 
    /* Aggiunta di un effetto overlay per un ulteriore tocco di glassmorphism */
    .overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(5px);
        border-radius: 30px;
        z-index: -1;
        padding-bottom: 10px;
    }
    </style>
 
    <div class="title-container">
        <h1>Assie</h1>
        <p>Il tuo Assistente Digitale per l'elaborazione dei Curriculum!</p>
    </div>
 
    <!-- Aggiunta di un overlay per lo sfondo -->
    <div class="overlay"></div>
    """)

    ASState = gr.State()
    GPState = gr.State()
    CState = gr.State([])
    gr.Image(value=r"InvestigAssie.png", show_label=False, container=False, height=200)

    with gr.Column(elem_classes="glass-section", show_progress=True, variant="compact", min_width=1000):
        CVRequirement     = gr.Textbox(label="🎯 Struttura desiderata dell'output ", placeholder="Es. Descrizione delle esperienze lavorative dei membri di progetto", lines=1)
        NamesInput        = gr.Textbox(label="🧑‍💼 Nomi dei Candidati", placeholder="COGNOME NOME, separati da una virgola", lines=1)
        RolesDictionary   = gr.Textbox(label="📇 Ruoli dei Candidati all'interno del progetto", placeholder="COGNOME NOME: Ruolo, separati da una virgola", lines=1)
        AuctionFiles      = gr.File(label="📁 Bandi di Gara (PDF, DOC, DOCX)", file_types=[".pdf", ".doc", ".docx"], file_count="multiple", elem_classes="small-upload")
        SynthetizerButton = gr.Button("📄 Elabora Documenti", variant='primary', elem_classes="btn-purple")
        SynthesisStatus   = gr.Textbox(label="📌 Stato Elaborazione", interactive=False)

    with gr.Column(elem_classes="glass-section", show_progress=True, variant="compact", min_width=1000):
        GenerateButton            = gr.Button("✨ Genera Profili", variant='primary', elem_classes="btn-purple")
        ProfileStatus             = gr.Textbox(label="📌 Stato Generazione", interactive=False)
        GeneratedProfilesMarkdown = gr.Markdown()

    with gr.Column(elem_classes="glass-section", show_progress=True, variant="compact", min_width=1000):
        Chatbot             = gr.Chatbot(label="💬 Revisione CV", height=400, show_copy_button=True)
        ChatInput           = gr.Textbox(label="✍️ Richiedi una modifica", placeholder="Es. Specifica meglio le certificazioni di COGNOME NOME...")
        DiscussButton       = gr.Button("📤 Invia Feedback", variant='primary', elem_classes="btn-purple")
        ExportButton        = gr.Button("📄 Esporta in PDF", variant='primary', elem_classes="btn-purple")
        ExportStatus        = gr.Textbox(label="📌 Stato Esportazione", interactive=False)
        ReviewerResetButton = gr.Button("🔄 Avvia Nuova Revisione", variant='secondary')
        ClearButton         = gr.Button("🧹 Riavvia Assie", variant='stop')

    SynthetizerButton.click(fn=AuctionSynthetize, inputs=[AuctionFiles], outputs=[SynthesisStatus, ASState])
    GenerateButton.click(fn=GenerateProfiles, inputs=[CVRequirement, ASState, NamesInput, RolesDictionary], outputs=[GPState, ProfileStatus, GeneratedProfilesMarkdown])
    DiscussButton.click(fn=DiscussProfiles, inputs=[ASState, GPState, ChatInput, CState], outputs=[Chatbot, CState])
    ChatInput.submit(fn=DiscussProfiles, inputs=[ASState, GPState, ChatInput, CState], outputs=[Chatbot, CState])
    ReviewerResetButton.click(fn=lambda: ([], []), inputs=[], outputs=[Chatbot, CState])
    ClearButton.click(fn=ResetAll, inputs=[], outputs=[CVRequirement, AuctionFiles, NamesInput, RolesDictionary, SynthesisStatus, ProfileStatus, GeneratedProfilesMarkdown, ASState, GPState, CState, Chatbot])
    ExportButton.click(fn=GeneratePDF, inputs=[CState, GeneratedProfilesMarkdown], outputs=[ExportStatus, gr.File(label="Scarica il PDF")])

demo.launch()