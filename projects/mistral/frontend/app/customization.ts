import { Injectable } from "@angular/core";
import { JsonPipe } from "@angular/common";
import { FormlyFieldConfig } from "@ngx-formly/core";
import { BaseProjectOptions } from "@rapydo/base.project.options";
import { BytesPipe } from "@rapydo/pipes/bytes";
import { YesNoPipe } from "@rapydo/pipes/yes_or_no";
import { AdminMenu, User } from "@rapydo/types";
import { environment } from "@rapydo/../environments/environment";

@Injectable()
export class ProjectOptions extends BaseProjectOptions {
  private policy_it: string;
  private policy_en: string;
  private participate_en: string;
  private cookiePolicyUrl: string = environment.CUSTOM.COOKIE_POLICY_URL;

  constructor() {
    super();
    this.initTemplates();
  }

  privacy_statements() {
    return [
      //{'label': 'IT', 'text': this.policy_it},
      {
        label: "Click here to visualize our Terms of Use",
        text: this.policy_en,
      },
    ];
  }

  participation_statements() {
    return [
      //{'label': 'IT', 'text': this.policy_it},
      {
        label: "How to publish your weather data on the MISTRAL portal ",
        text: this.participate_en,
      },
    ];
  }

  custom_user_data(): any[] {
    return [
      {
        name: "Disk<br>Quota",
        prop: "disk_quota",
        flexGrow: 0.3,
        pipe: new BytesPipe(),
      },
      { name: "AMQP", prop: "amqp_queue", flexGrow: 0.3 },
      { name: "Req.Exp.", prop: "requests_expiration_days", flexGrow: 0.3 },
      {
        name: "OpenDatasets",
        prop: "open_dataset",
        flexGrow: 0.3,

        pipe: new YesNoPipe(),
      },
      { name: "Datasets", prop: "datasets.length", flexGrow: 0.3 },
    ];
  }

  cookie_law_text(): string {
    return (
      "We use cookies to ensure you get the best experience on our website. " +
      "If you continue to use this site you accept to receive cookies, otherwise you " +
      "can leave this page. If you need more information you can read " +
      `<a target='_blank' rel='noopener noreferrer' href='${this.cookiePolicyUrl}'>privacy and cookie policy</a>`
    );
  }

  cookie_law_button(): string {
    // return null to enable default text
    return null;
  }

  registration_disclaimer(): string {
    return null;
  }

  admin_menu_entries(user: User): AdminMenu[] {
    return [
      {
        enabled: user.isAdmin,
        label: "Bindings",
        router_link: "/app/admin/bindings",
      },
    ];
  }

  private initTemplates() {
    this.policy_it = `
<h5>PERCHÉ QUESTE INFORMAZIONI</h5>

La presente informativa, resa ai sensi del Regolamento (UE) 2016/679 (di seguito "Regolamento"), descrive le modalità di trattamento dei dati personali degli utenti che consultano il sito web o accedono alla piattaforma meteo-hub del progetto Mistral (Progetto europeo CEF 2014-2020 AGREEMENT No INEA/CEF/ICT/A2017/1567101) accessibile per via telematica ai seguenti indirizzi web:<br/>
<ul>
    <li>mistralportal.eu</li>
    <li>mistralportal.it</li>
    <li>meteohub.mistralportal.it</li>
</ul>
La presente informativa è resa unicamente per coloro che accedono ed interagiscono con i siti sopra riportati e non per tutti gli altri siti web eventualmente consultati dall'utente tramite i collegamenti ipertestuali presenti nel sito, per cui Cineca non è responsabile.<br/>
<br/>

<h5>TITOLARE DEL TRATTAMENTO</h5> 
Il "Titolare" del trattamento dei dati personali trattati a seguito della consultazione del nostro sito e di ogni altro dato inserito volontariamente dall'utente nella compilazione di form di richiesta di informazioni o utilizzo dei nostri servizi, è il "CINECA – Consorzio Interuniversitario – Via Magnanelli nr. 6/3 cap. 40033 Casalecchio di Reno (BO) – Tel. Centralino 051 6171411" e-mail: privacy@cineca.it <br/>
<br/>
<br/>

<h5>RESPONSABILE DELLA PROTEZIONE DEI DATI</h5>
Il Responsabile della Protezione dei Dati (RPD) è raggiungibile al seguente indirizzo: Cineca Consorzio Interuniversitario – via Magnanelli 6/3 email: privacy@cineca.it<br/>
<br/>

<h5>BASE GIURIDICA DEL TRATTAMENTO</h5>
La base giuridica del trattamento è rappresentata dal perseguimento del legittimo interesse  del Titolare al corretto funzionamento dei sistemi informatici connessi alla funzionalità del sito, ovvero ai fini di rispondere alle richieste avanzate dagli utenti.
<br/>
Il conferimento dei dati personali forniti volontariamente nella compilazione del form accessibile nella pagina CONTATTI del sito di Mistral o tramite l’invio di email o per la registrazione delle proprie credenziali di accesso,  è facoltativo.  L'eventuale rifiuto di conferirli può comportare l'impossibilità di fruire dei Servizi richiesti. I dati richiesti sono quelli strettamente necessari per rispondere alle richieste dell’utente (dati di contatto).<br/> 
<br/> 

 

<h5>FINALITA' DEL TRATTAMENTO E TIPOLOGIA DI DATI TRATTATI</h5> 

<h5>DATI INSERITI VOLONTARIAMENTE DALL'UTENTE</h5> 

I dati personali forniti direttamente dagli utenti tramite la compilazione di form web based per l’invio di commenti o per  la registrazione al sito  al fine di ricevere  informazioni,o per l'autenticazione alla piattaforma digitale Meteo-hub,   verranno utilizzati per consentire l'invio del materiale informativo richiesto (newsletter, risposte a richieste di informazioni, invio di pubblicazioni “Mistral")e/o per consentire l'accesso alla piattaforma meteo-hub e la fruizione dei  servizi offerti e saranno eventualmente  comunicati unicamente agli altri enti partner del progetto.
<br/>
Nel caso in cui, per accedere ad eventuali servizi on line sia necessaria la registrazione dell’utente per l’accesso al servizio, i dati personali degli utenti (es. indirizzo di posta elettronica del mittente e altri dati personali inseriti nel form), effettuata la scelta del servizio, verranno trattati per le finalità connesse e/o funzionali al servizio prescelto. Specifiche informative di sintesi saranno riportate nelle pagine del sito predisposte per particolari servizi a richiesta.
<br/> 
<br/>

<h5>DATI DI NAVIGAZIONE</h5> 
I sistemi informatici e le procedure software, preposte al funzionamento di questo sito web, acquisiscono, nel corso del loro normale esercizio, alcuni dati la cui trasmissione è insita nell'uso dei protocolli di comunicazione di Internet. Si tratta di informazioni che non sono raccolte per essere associate a interessati identificati, ma che per loro stessa natura potrebbero, attraverso elaborazioni ed associazioni con dati detenuti da terzi, permettere di identificare gli utenti. In questa categoria di dati rientrano gli indirizzi IP o i nomi a dominio dei computer utilizzati dagli utenti che si connettono al sito, gli indirizzi in notazione URI (Uniform Resource Identifier: è una stringa che identifica univocamente una risorsa generica che può essere un indirizzo web, un documento, un file ecc. ) delle risorse richieste, l'orario della richiesta, il metodo utilizzato nel sottoporre la richiesta al server, la dimensione del file ottenuto in risposta, il codice numerico indicante lo stato della risposta data dal server (buon fine, errore, ecc.) ed altri parametri relativi al sistema operativo e all'ambiente informatico dell'utente (browser utilizzato dall'utente).<br/> 
<br/>
Il sistema non consente invece di raccogliere l'identità dell'utente che si collega. <br/> 
<br/>
Tali dati sono utilizzati unicamente su base aggregata e mai personalizzata, per analizzare statisticamente il comportamento dell'utenza al fine di comprendere come i visitatori utilizzano il sito e per misurare l'interesse riscontrato per le diverse pagine che compongono il sito. Ciò consente di migliorare il contenuto del sito e di semplificare e rendere più efficiente la consultazione. 
<br/>
Questi dati vengono utilizzati al solo fine di ricavare informazioni statistiche anonime sull'uso del sito e per controllarne il corretto funzionamento e sono conservati per il periodo necessario alle finalità definite nella presente informativa. I dati in questione potrebbero essere utilizzati per l'accertamento di responsabilità in caso di eventuali reati informatici ai danni del nostro sito, nel rispetto delle garanzie imposte dalla legge. Si precisa che l'utilizzo dei dati di navigazione e dei cookies non è in alcun modo finalizzato alla "profilazione dell'utente" e cioè una tecnica volta alla raccolta di informazioni sui consumatori per meglio indirizzare campagne promozionali e offerte di vendita.<br/> 
<br/>

<h5>CONFIGURAZIONE DEI LOG DEL WEB SERVER DEL CINECA </h5>
Durante la navigazione il browser di ogni utente comunica al web server del Cineca l'indirizzo IP del navigatore. L'indirizzo IP è un numero assegnato automaticamente ad ogni computer durante la navigazione sul web.
<br/>
Il web server del Cineca è configurato in maniera tale da non consentire l'identificazione dell'utente (nome utente) associato all'indirizzo IP o altre informazioni di identità personale pertanto l'utente resta anonimo durante la visita del sito.
<br/> 
<br/>
<h5>L'UTILIZZO DI COOKIES E ALTRI SISTEMI DI TRACCIAMENTO</h5>
Si veda l'informativa disponibile al seguente URL:
${this.cookiePolicyUrl}<br/> 
<br/>

<h5>DESTINATARI DEI DATI</h5>
I destinatari dei dati raccolti a seguito della compilazione di form o invio di e-mail o sottoscrizione al sito sono gli eventuali Responsabili del trattamento nominati dal Titolare, nonché le persone fisiche all’interno del Cineca autorizzate al trattamento dei dati per le finalità sopra riportate.
<br/>
I dati della navigazione (indirizzo IP, sito di provenienza, browser utilizzati, S.O utilizzato, pagine visitate, tempo di permanenza nelle singole pagine ecc. ) alle pagine del sito mistralportal.eu e mistralportal.it sono unicamente trasmessi alla società Google che fornisce al Cineca il servizio denominato Google Analytics  (http://www.google.com/analytics/): si tratta di un servizio di elaborazione statistica degli accessi al sito, che vengono utilizzati unicamente all’interno del progetto Mistral,  per analizzare l'utilizzo del sito da parte degli utenti in un'ottica di miglioramento del servizio offerto e per rendere più rapido e facilmente accessibile l'utilizzo del sito.<br/> 
<br/>
Tali dati non vengono in alcun modo trattati per definire il profilo o la personalità dell'interessato, o per analizzare abitudini o scelte di consumo a fini commerciali.
<br/> 
I suoi dati personali non saranno soggetti a diffusione. <br/> 
<br/>

<h5>CONSERVAZIONE DEI DATI</h5>
I dati di navigazione e i cookies devono saranno conservati per un massimo di sette giorni, salvo espressa richiesta dell’Autorità giudiziaria per l’accertamento di reati. I dati forniti volontariamente dagli utenti saranno conservati fino a quando necessario rispetto alle legittime finalità per le quali sono stati raccolti.<br/> 
<br/>

<h5>DIRITTI DELL’INTERESSATO E MODALITA’ DI ESERCIZIO</h5> 
Si precisa che in riferimento ai suoi dati personali conferiti, è detentore dei seguenti diritti:<br/> 
<br/>
<ol>
<li>di accesso ai suoi dati personali;</li>
<li>di ottenere la rettifica o la cancellazione degli stessi o la limitazione del trattamento che li riguarda;</li>
<li>di opporsi al trattamento;</li>
<li>di proporre reclamo all'autorità di controllo (Garante per la protezione dei dati personali)</li>
</ol>
Per esercitare i diritti sopra riportati potrà rivolgersi al Titolare del trattamento al seguente indirizzo: Cineca Consorzio Interuniversitario – via Magnanelli 6/3, 40033 Casalecchio di Reno (BO) oppure all’indirizzo di posta elettronica: privacy@cineca.it all’attenzione del “Responsabile della protezione dei dati personali”.  Al fine di agevolare il rispetto dei termini di legge, si consiglia di riportare nella richiesta la dicitura "Esercizio diritti ex art. 15 e ss. del Regolamento Europeo n. 679 /2016".<br/>
<br/>
Il Titolare del trattamento è tenuto a fornirle una risposta entro un mese dalla richiesta, estensibili fino a tre mesi in caso di particolare complessità della richiesta.<br/>
<br/>
`;

    this.policy_en = `
<h5>WHY THIS INFORMATION</h5>
This information, made pursuant to Regulation (EU) 2016/679 (hereinafter the "Regulation"), describes the methods of processing of personal data of users who consult the Mistral project website or access the meteo-hub platform, accessible electronically to the following web addresses:<br/>
<ul>
    <li>mistralportal.eu</li>
    <li>mistralportal.it</li>
    <li>meteohub.mistralportal.it</li>
</ul>
This information is provided solely for those who access and interact with the sites listed above and not for all other websites that may be consulted by the user through hypertext links on the site, for which Cineca is not responsible.<br/>
<br/>


<h5>DATA CONTROLLER</h5>
The Controller of the personal data collected during the consultation of our site and any other data voluntarily provided by the user in filling out information request forms, is the "CINECA - Interuniversity Consortium - Via Magnanelli 6/3 cap. 40033 Casalecchio di Reno (BO) - Tel. Switchboard 051 6171411" e-mail: privacy@cineca.it<br/>
<br/>
<br/>

<h5>DATA PROTECTION OFFICER</h5>
The Data Protection Officer (DPO) can be reached at the following address: <br/>Cineca Consorzio Interuniversitario - via Magnanelli 6/3 email: privacy@cineca.it<br/>
<br/>

<h5>LEGAL BASIS OF THE TREATMENT</h5>
The legal basis of the processing is represented by the pursuit of the legitimate interest of the Cineca as a coordinating partner of the Mistral project, pursuant to Article 6 paragraph f) of the Regulation, to the publication on the web of the project informative site aimed at the dissemination of activities and initiatives dissemination of the project itself.<br/> 
<br/>
The provision of personal data voluntarily provided by completing the form available on the CONTACTS page of the Mistral website or by sending e-mail is optional. Any refusal to provide them may make the use of the requested Services impossible. The data requested are those strictly necessary to respond to the user's requests (contact details).<br/> 
<br/> 

<h5>PURPOSE OF THE PROCESSING AND TYPE OF DATA PROCESSED</h5>

<h5>DATA VOLUNTARILY PROVIDED BY THE USER</h5>
The personal data provided directly by users through the compilation of web based forms for sending comments or for registering on the site in order to receive information, or for authentication to the digital Meteo-hub platform, will be used to allow the sending the requested information material (newsletter, replies to requests for information, sending "Mistral" publications) and / or to allow access to the meteo-hub platform and the use of the services offered and will eventually be communicated only to the other partner entities of the project.<br/>
<br/>
In the event that, in order to access any online services users registration is required, the personal data of the users (e.g. the sender's e-mail address and other personal data entered in the form), once the service has been chosen, will be processed for the purposes connected and/or functional to the chosen service. Specific summary policies will be reported on the pages of the site prepared for particular services.
<br/>
<br/>
<h5>BROWSING DATA</h5>
The computer systems and software procedures, responsible for the functioning of this website, acquire, during their normal operation, some data whose transmission is inherent in the use of Internet communication protocols. This information is not collected to be associated with identified interested parties, but by their very nature could, through processing and association with data held by third parties, allow users to be identified. This category of data includes IP addresses or domain names of computers used by users who connect to the site, URI (Uniform Resource Identifier: addresses) is a string that uniquely identifies a generic resource that can be a web address, a document, a file etc. of the requested resources, the time of the request, the method used in submitting the request to the server, the size of the file obtained in response, the numeric code indicating the status of the response given by the server (successful , error, etc.) and other parameters relating to the operating system and the user's computer environment (browser used by the user).<br/>
<br/>
The system does not allow instead to collect the identity of the user who connects.<br/>
<br/>
These data are used only on an aggregate basis and never personalized, to statistically analyze the behavior of the user in order to understand how visitors use the site and to measure the interest found for the different pages that make up the site. This makes possible to improve the content of the site and to simplify the consultation while making it more efficient.<br/>
<br/>
These data are used for the sole purpose of obtaining anonymous statistical information on the use of the site and to check its correct functioning and are kept for the period necessary for the purposes defined in this statement. The data in question could be used to ascertain responsibility in the event of computer crimes against our site, in compliance with the guarantees imposed by the law. It should be noted that the use of browsing data and cookies is in no way aimed at "user profiling", that is, a technique aimed at gathering information on consumers to better target promotional campaigns and sales offers.<br/>
<br/>

<h5>CONFIGURING CINECA WEB SERVER LOGS</h5>
While browsing, each user's browser communicates to the Cineca web server the IP address of the user. The IP address is a number automatically assigned to each computer while browsing the web.<br>
<br/>
The Cineca web server is configured in such a way as not to allow the identification of the user (user name) associated with the IP address or other personal identity information, therefore the user remains anonymous during the site visit.<br>
<br/>

<h5>THE USE OF COOKIES AND OTHER TRACKING SYSTEMS</h5>
See the information available at the following URL:
${this.cookiePolicyUrl}<br/>
<br/>

<h5>DATA RECIPIENTS</h5>
The recipients of the data collected after completing the form or sending an e-mail or subscription to the site are any Data Processors appointed by the Data Controller, as well as the physical persons within the Cineca authorized to process the data for the purposes indicated above.<br/>
<br/>
The browsing data (IP address, site of origin, browser used, OS used, pages visited, time spent on individual pages, etc.) on the pages of the website mistralportal.eu and mistralportal.it are only transmitted to the Google company that provides the Cineca the service called Google Analytics (http://www.google.com/analytics/): it is a service of statistical processing of site accesses, which are used only within the mistral project, to analyze usage of the site by users in order to improve the service offered and to make the use of the site quicker and easier to access.<br/>
These data are not processed in any way to define the profile or personality of the person concerned, or to analyze habits or consumption choices for commercial purposes.<br/>
Your personal data will not be subject to disclosure.<br/>
<br/>

<h5>DATA STORAGE</h5>
Browsing data and cookies must be kept for a maximum of seven days, unless expressly requested by the judicial authority for the detection of crimes.
The data voluntarily provided by users will be kept as long as necessary with respect to the legitimate purposes for which they were collected.
<br/>
<br/>

<h5>RIGHTS OF THE DATA SUBJECT AND METHOD OF EXERCISE</h5>
It is specified that in reference to your personal data, you have the following rights:<br/>
<ol>
<li>access to your personal data;</li>
<li>to obtain the rectification or cancellation of the same or the limitation of the treatment concerning it;</li>
<li>to oppose the processing;</li>
<li>to lodge a complaint with the supervisory authority (Guarantor for the protection of personal data)</li>
</ol>

To exercise the above rights, you can contact the DATA CONTROLLER at the following address: Cineca Interuniversity Consortium - via Magnanelli 6/3, 40033 Casalecchio di Reno (BO) or at the e-mail address: privacy@cineca.it for the attention of "Responsible for the protection of personal data". In order to facilitate compliance with the terms of the law, it is advisable to include in the request the words "Exercise of rights pursuant to article 15 and following of European Regulation n. 679/2016".<br/>
<br/>
The DATA CONTROLLER is required to provide a response within one month of the request, extendable up to three months if the request is particularly complex.<br/>
		`;
    this.participate_en = `
<br>
<h5>Observational data</h5>
<br>
<ol>
<li>
<h6><b>License</b></h6><p>
Data is required to be available with an OPEN license. Most of the data available on MISTRAL has CC BY 4.0 license and this is the recommended license. However, the system is designed to accept and redistribute data with any type of OPEN license.
<br>For further information please contact us: <a href= "mailto:mistral@cineca.it">mistral@cineca.it</a>.</p>
</li>
<li>
<h6><b>Modality</b></h6><p>
Data must be sent to MISTRAL via the AMQP protocol.<br>
AMQP (Advanced Message Queuing Protocol) is a protocol for communications through message queues that guarantees interoperability, security, reliability and persistence.
</p>
<p>
An <b>additional method</b> is available for the <b>Regions</b> to publish the observational data of the ground stations they own:
<ul>
<li>giving the authorization to the Civil Protection to redistribute to MISTRAL the data that it already collects from the Regions. MISTRAL has already activated this collection flow for 11 regions and an autonomous province.</li>
</ul>
</p>
<p>
For further information please contact us: <a href= "mailto:mistral@cineca.it">mistral@cineca.it</a>
</p>
</li>
<li>
<h6><b>Data model: data and metadata</b></h6><p>
Each data is a value associated with 6 unique metadata:
<ul>
<li>
<i>Time</i>: date time of the observation or end of the observation period
</li>
<li>
<i>Longitude, latitude and identifier</i>: geographical coordinates and identification of the data generator
</li>
<li>
<i>Network</i>: it defines stations with homogeneous characteristics (class of instruments, representativeness and / or mobile or fixed stations)
</li>
<li>
<i>Time range</i>: it indicates observation or time of the forecast and any "statistical" processing in coded form using a table
</li>
<li>
<i>Level</i>: the vertical coordinates (possibly layer) in coded form by means of a table
</li>
<li>
<i>Variable</i>: physical parameter defined with a description, unit of measurement, measurement range and significant figures.
</li>
</ul>
</p>
<p>
For more details please see: <a href="https://doc.rmap.cc/rmap_rfc/rfc.html#data-model-dati-e-metadati" target="blank">doc.rmap.cc/rmap_rfc/rfc.html#data-model-dati-e-metadati</a><br>
</p>
<p>
Each data can also be equipped with attributes, for example produced by quality control.
</p>
</li>
<li>
<h6><b>Format</b></h6><p>
The formats managed are:
<ul>
<li>BUFR</li>
<li>JSON (in development)</li>
</ul>
For more details please see: <a href="https://doc.rmap.cc/rmap_rfc/rfc.html#formati" target="blank">doc.rmap.cc/rmap_rfc/rfc.html#formati</a>
</p>
</li>
<li>To publish observational data on the MISTRAL portal, please contact the MISTRAL team: <a href= "mailto:mistral@cineca.it">mistral@cineca.it</a></li>
</ol>
<br>
<h5>Forecast model data</h5>
<p>
To publish forecast model data on the MISTRAL portal, please contact the MISTRAL team: <a href= "mailto:mistral@cineca.it">mistral@cineca.it</a> 
</p>
<br>
<h5>Other types</h5>
<p>
To publish data of other types on the MISTRAL portal, please contact the MISTRAL team: <a href= "mailto:mistral@cineca.it">mistral@cineca.it</a>
</p>

`;
  }
}
