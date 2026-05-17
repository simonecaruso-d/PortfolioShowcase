# Environment Setting
from autogen import AssistantAgent
import asyncio
from bs4 import BeautifulSoup
import chainlit as cl
import os
import pandas as pd
import pdfplumber
import requests
from serpapi import GoogleSearch
import warnings

warnings.filterwarnings("ignore", message="Couldn't find ffmpeg or avconv")

# Constants & Keys
OpenRouterUrl = "https://openrouter.ai/api/v1"
OpenRouterKey = "sk-or-xxxxxxxxxxxxxxxxxx"
SerpApiKey    = "xxxxxxxxxxxxxxxxxxxxxxxx"

NewsletterFolderPath = r"Newsletter Samples"
CurrentNewsletter    = ""
ArticlesSample       = ""

# Functions - Examples Processing
def ExtractPdfTexts(folderPath):
    texts = []
    for filename in os.listdir(folderPath):
        if filename.lower().endswith(".pdf"):
            filepath = os.path.join(folderPath, filename)
            with pdfplumber.open(filepath) as pdf:
                fileText = ""
                for page in pdf.pages:
                    data = page.extract_text()
                    if data: fileText += data + "\n"
                texts.append(fileText)
    return "\n".join(texts)

# Functions - News Extraction
def FindNews(searchTerm, gl, hl, serpApiKey, articlesToExtract, engine="google_news"):
    params      = {"engine": engine, "q": searchTerm, "gl": gl, "hl": hl, "api_key": serpApiKey}
    search      = GoogleSearch(params)
    results     = search.get_dict()
    newsResults = results.get("news_results", [])[:articlesToExtract]
    newsList    = []
    for news in newsResults:
        new = {"Title": news.get("title"), "Date": news.get("date"), "Link": news.get("link")}
        newsList.append(new)

    return pd.DataFrame(newsList)

def ExtractFullText(url):
    try:
        headers    = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response   = requests.get(url, headers=headers, timeout=10)
        soup       = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        content    = "\n".join(p.get_text() for p in paragraphs)
        return content
    except Exception as e: return f"Errore nell'accesso a {url}: {e}"

# Agents - Definitions & Functions
Analyzer = AssistantAgent(
        name="Analyzer",
        llm_config={"config_list": [{"model": "deepseek/deepseek-r1:free", "base_url": OpenRouterUrl, "api_key": OpenRouterKey}], "temperature": 0.2},
        is_termination_msg=lambda x: "||TERMINATION||" in x.get("content", "").rstrip(),
        system_message=f"""Ruolo: Sei un analista editoriale. 
                            Obiettivo: Identificare le caratteristiche chiare dei TestiEsempio in modo da replicare fedelmente tale stile in future generazioni testuali.
                            Segui il seguente flusso processuale:
                            1. Analizza i TestiEsempio per identificare:
                                A. Stile (formale/informale, diretto/descrittivo, tecnico/divulgativo);
                                B. Tono (entusiasta, istituzionale, ecc.);
                                C. Lessico (termini tecnici, metafore, inglesismi);
                                D. Struttura (intro, corpo, CTA);
                                E. Target (pubblico a cui si rivolge);
                            2. Comunica in maniere sintetica e chiara le caratteristiche stilistiche e strutturali dei TestiEsempio.
                            3. Concludi con la stampa del testo: ||TERMINATION||""")
KeyWordsExtracter = AssistantAgent(
        name="KeyWordsExtracter",
        llm_config={"config_list": [{"model": "deepseek/deepseek-r1-0528:free", "base_url": OpenRouterUrl, "api_key": OpenRouterKey}], "temperature": 0.3},
        is_termination_msg=lambda x: "||TERMINATION||" in x.get("content", "").rstrip(),
        system_message=f"""Ruolo: Sei un esperto in SEO.
                            Obiettivo: Leggere il NewsletterTopic e generare al massimo tre parole chiave che ne rappresentano il tema principale.
                            Segui il seguente flusso processuale:
                            1. Leggi attentamente il testo del NewsletterTopic.
                            2. Identifica le parole chiave più rilevanti che riassumono il tema principale.
                            3. Seleziona da una a massimo cinque parole chiave.
                            4. Restituisci le parole chiave in un formato facilmente utilizzabile per la ricerca di articoli pertinenti.
                            5. Non includere spiegazioni o commenti, solo le parole chiave.
                            6. Concludi con la stampa del testo: ||TERMINATION||""")
TitleMatcher = AssistantAgent(
        name="TitleMatcher",
        llm_config={"config_list": [{"model": "qwen/qwen3-30b-a3b:free", "base_url": OpenRouterUrl, "api_key": OpenRouterKey}], "temperature": 0.3},
        is_termination_msg=lambda x: "||TERMINATION||" in x.get("content", "").rstrip(),
        system_message=f"""Ruolo: Sei un esperto in SEO editoriale.
                            Obiettivo: Leggere il NewsletterTopic e confrontarlo con i TitoliArticoli per identificare quelli più rilevanti .
                            Flusso processuale:
                            1. Leggi attentamente il NewsletterTopic .
                            2. Leggi i TitoliArticoli.
                            3. Identifica i 5 titoli più pertinenti al tema della newsletter e più interessanti per una newsletter aziendale, prediligendo temi di business, politici e legali.
                            4. Restituisci i titoli e solo i titoli in una lista separandoli tramite il carattere "|". Attieniti  a questo formato: Titolo1|Titolo2|Titolo3|Titolo4|Titolo5.
                            5. Non includere spiegazioni o commenti, solo i titoli.
                            6. Concludi con la stampa del testo: ||TERMINATION||""")
Synthetizer = AssistantAgent(
        name="Synthetizer",
        llm_config={"config_list": [{"model": "meta-llama/llama-4-maverick:free", "base_url": OpenRouterUrl, "api_key": OpenRouterKey}], "temperature": 0.3},
        is_termination_msg=lambda x: "||TERMINATION||" in x.get("content", "").rstrip(),
        system_message=f"""Ruolo: Sei un esperto in sintesi di testi.
                            Obiettivo: Leggere il TestoArticolo e sintetizzarlo per ridurne la lunghezza.
                            Flusso processuale:
                            1. Leggi attentamente il TestoArticolo.
                            2. Identifica le informazioni chiave e i concetti principali.
                            3. Riduci il testo mantenendo il significato originale, eliminando ripetizioni e dettagli non essenziali. Non ridurre troppo.
                            4. Restituisci il testo sintetizzato in un formato chiaro e conciso.
                            5. Non includere spiegazioni o commenti, solo il testo sintetizzato.
                            6. Concludi con la stampa del testo: ||TERMINATION||""")       
Writer = AssistantAgent(
        name="Writer",
        llm_config={"config_list": [{"model": "deepseek/deepseek-chat-v3-0324:free", "base_url": OpenRouterUrl, "api_key": OpenRouterKey}], "temperature": 0.6},
        is_termination_msg=lambda x: "||TERMINATION||" in x.get("content", "").rstrip(),
        system_message=f"""Ruolo: Sei un redattore professionista di newsletter aziendali.
                            Obiettivo: Scrivere una newsletter seguendo lo stile, il tono e la struttura analizzati e forniti in StileNewsletter.
                            Flusso processuale:
                            1. Analizza attentamente lo StileNewsletter. 
                                Non inventare uno stile personale: adatta ogni testo alle caratteristiche stilistiche e strutturali ricevute.
                                Capisci ed usa in modo coerente:
                                A. Il tono indicato;
                                B. Il registro linguistico;
                                C. Il lessico specifico;
                                D. La struttura suggerita;
                            2. Analizza il TopicNewsletter deciso dall'utente. 
                            3. Analizza gli ArticoliEsempio forniti.
                            4. Genera un testo sul tema del TopicNewsletter, utilizzando le informazioni e i concetti chiave degli ArticoliEsempio.
                            5. Assicurati che il testo sia coerente con lo stile e il tono analizzati in StileNewsletter.
                            6. Concludi con la stampa del testo: ||TERMINATION||""")
Reviewer = AssistantAgent(
        name="Reviewer",
        llm_config={"config_list": [{"model": "deepseek/deepseek-r1:free", "base_url": OpenRouterUrl, "api_key": OpenRouterKey}], "temperature": 0.4},
        is_termination_msg=lambda x: "||TERMINATION||" in x.get("content", "").rstrip(),
        system_message=f"""Ruolo: Sei un redattore professionista di newsletter aziendali.
                            Obiettivo: Rivedere e migliorare il testo della Newsletter in base al FeedbackUtente. 
                            Flusso processuale:
                            1. Analizza attentamente il FeedbackUtente. 
                            2. Adatta la Newsletter in base al FeedbackUtente. 
                            3. Utilizza, se necessario, gli ArticoliEsempio forniti.
                            4. Non modificare in modo significativo lo stile, il tono e la struttura della Newsletter, a meno che non sia specificamente richiesto dal FeedbackUtente.
                            5. Concludi con la stampa del testo: ||TERMINATION||""")

async def GenerateAnswer(prompt, model, modelName):
    rawResult    = await asyncio.to_thread(model.initiate_chat, model, message=prompt)
    chatMessages = [msg["content"] for msg in rawResult.chat_history if msg["name"] == modelName]
    finalMessage = chatMessages[-3] if chatMessages[-1] == "||TERMINATION||"  else chatMessages[-1]
    return finalMessage.replace("||TERMINATION||", "")

# Functions - Aggregators
async def ExamplesProcessing(examplesFilePath):
    oldexamples   = ExtractPdfTexts(examplesFilePath)
    examplesStyle = await GenerateAnswer(f"TestiEsempio: \n{oldexamples}", Analyzer, "Analyzer")

    return examplesStyle

async def NewsExtraction(topic):
    keywords   = await GenerateAnswer(f"NewsletterTopic: \n{topic}", KeyWordsExtracter, "KeyWordsExtracter")
    news       = FindNews(searchTerm=keywords, gl="it", hl="it", serpApiKey=SerpApiKey, articlesToExtract=25, engine="google_news")
    newsTitles = news['Title'].tolist()

    relevantTitles = await GenerateAnswer(f"NewsletterTopic: \n{topic}.\n TitoliArticoli: \n{newsTitles}", TitleMatcher, "TitleMatcher")
    relevantTitles = relevantTitles.split('|')
    news           = news[news['Title'].isin(relevantTitles)]
    news['Body']   = news['Link'].apply(ExtractFullText)
    synthList      = []
    for text in news['Body']:
        summary = await GenerateAnswer(f"TestoArticolo: \n{text}\n", Synthetizer, "Synthetizer")
        synthList.append(summary)

    news['Synthesis'] = synthList
    articles = "\n\n".join(news['Title'] + " " + news['Synthesis'])

    return articles

async def GenerateContent(topic, examplesFilePath):
    articles = await NewsExtraction(topic)
    style    = await ExamplesProcessing(examplesFilePath)
    output   = await GenerateAnswer(f"StileNewsletter: \n{style}.\n\n TopicNewsletter: \n{topic}.\n\n ArticoliEsempio: \n{articles}", Writer, "Writer")
    return output, articles

# Main
@cl.on_chat_start
async def Start():
    imagePath = r"Newsie.png"
    image     = cl.Image(path=imagePath, name="LogoNewsie", display="inline")
    await cl.Message(content="📰 **Benvenuto/a. Sono Newsie, il tuo assistente AI per la scrittura di newsletter!**", elements=[image], author="Newsie").send()
    await cl.Message(content="🎯 Inserisci il tema della newsletter:", author="Newsie").send()

@cl.on_message
async def HandleMessage(message: cl.Message):
    global CurrentNewsletter
    global ArticlesSample
    topicOrFeedback = message.content.strip()
    response        = cl.Message(content="⏳ Sto elaborando…", author="Newsie")
    await response.send()

    if not CurrentNewsletter:
        result, articles  = await GenerateContent(topicOrFeedback, NewsletterFolderPath)
        CurrentNewsletter = result
        ArticlesSample    = articles
        response.content  = result
    else:
        reviewed          = await GenerateAnswer(f"Newsletter: \n{CurrentNewsletter}\n\nFeedbackUtente: \n{topicOrFeedback}\n\n ArticoliEsempio: \n{ArticlesSample}",Reviewer, "Reviewer")
        CurrentNewsletter = reviewed
        response.content  = reviewed

    await response.update()