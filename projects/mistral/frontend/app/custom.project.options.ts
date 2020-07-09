import { Injectable } from "@angular/core";

import { BytesPipe } from "@rapydo/pipes/pipes";

@Injectable()
export class ProjectOptions {
  private policy_it: string;
  private policy_en: string;

  constructor() {
    this.initTemplates();
  }
  public get_option(opt): any {
    if (opt == "show_footer") {
      return true;
    }
    if (opt == "privacy_acceptance") {
      return this.privacy_acceptance();
    }
    if (opt == "user_page") {
      return {
        custom: [
          {
            name: "Disk<br>Quota",
            prop: "disk_quota",
            flexGrow: 0.3,
            pipe: new BytesPipe(),
          },
          { name: "AMQP", prop: "amqp_queue", flexGrow: 0.3 },
        ],
      };
    }

    if (opt == "cookie_law_text") {
      return "We uses cookies to ensure you get the best experience on our website. If you continue to use this site you accept to receive cookies, otherwise you can leave this page. If you need more information you can read <a target='_blank' href='https://www.cineca.it/privacy/cookies-cineca'>privacy and cookie policy</a>";
    }
    return null;
  }

  /*	
	private registration_options() {
		return {}
	}
*/

  private privacy_acceptance() {
    return [
      //{'label': 'IT', 'text': this.policy_it},
      {
        label: "Click here to visualize our Terms of Use",
        text: this.policy_en,
      },
    ];
  }

  private initTemplates() {
    this.policy_it = `
PERCHÉ QUESTE INFORMAZIONI

La presente informativa, resa ai sensi del Regolamento (UE) 2016/679 (di seguito "Regolamento"), descrive le modalità di trattamento dei dati personali degli utenti che consultano il sito web o accedono alla piattaforma meteo-hub del progetto Mistral (Progetto europeo CEF 2014-2020 AGREEMENT No INEA/CEF/ICT/A2017/1567101) accessibile per via telematica ai seguenti indirizzi web:

mistralportal.eu
mistralportal.it
meteo-hub.hpc.cineca.it

La presente informativa è resa unicamente per coloro che accedono ed interagiscono con i siti sopra riportati e non per tutti gli altri siti web eventualmente consultati dall'utente tramite i collegamenti ipertestuali presenti nel sito, per cui Cineca non è responsabile.

Le forniamo quindi le seguenti informazioni: 

IL TITOLARE DEL TRATTAMENTO 

Il "Titolare" del trattamento dei dati personali trattati a seguito della consultazione del nostro sito e di ogni altro dato inserito volontariamente dall'utente nella compilazione di form di richiesta di informazioni o utilizzo dei nostri servizi, è il "CINECA – Consorzio Interuniversitario – Via Magnanelli nr. 6/3 cap. 40033 Casalecchio di Reno (BO) – Tel. Centralino 051 6171411" e-mail: privacy@cineca.it 


Può rivolgersi al Titolare del trattamento scrivendo all’indirizzo sopra riportato o inviando una e-mail al seguente indirizzo di posta elettronica: privacy@cineca.it

RESPONSABILE DELLA PROTEZIONE DEI DATI

The Data Protection Officer (DPO) is present at Cineca, appointed pursuant to art. 37 of EU Regulation 2016/679. The data protection officer can be contacted at the following e-mail address: dpo@cineca.it


BASE GIURIDICA DEL TRATTAMENTO

La base giuridica del trattamento è rappresentata dal perseguimento del legittimo interesse del Cineca in quanto partner coordinatore del progetto Mistral, ai sensi dell’articolo 6 comma f) del Regolamento, alla pubblicazione su web del sito informativo di progetto volto alla diffusione delle attività ed iniziative di dissemination del progetto stesso.
Il conferimento dei dati personali forniti volontariamente nella compilazione della form accessibile nella pagina CONTATTI del sito di Mistral o tramite l’invio di email o per la registrazione delle proprie credenziali di accesso,  è facoltativo.  L'eventuale rifiuto di conferirli può comportare l'impossibilità di fruire dei Servizi richiesti. I dati richiesti sono quelli strettamente necessari per rispondere alle richieste dell’utente (dati di contatto). 

 

FINALITA' DEL TRATTAMENTO E TIPOLOGIA DI DATI TRATTATI 

DATI INSERITI VOLONTARIAMENTE DALL'UTENTE 

I dati personali forniti direttamente dagli utenti tramite la compilazione di form web based per l’invio di commenti o per  la registrazione al sito  al fine di ricevere  informazioni,o per l'autenticazione alla piattaforma digitale Meteo-hub,   verranno utilizzati per consentire l'invio del materiale informativo richiesto (newsletter, risposte a richieste di informazioni, invio di pubblicazioni “Mistral")e/o per consentire l'accesso alla piattaforma meteo-hub e la fruizione dei  servizi offerti e saranno eventualmente  comunicati unicamente agli altri enti partner del progetto.


DATI DI NAVIGAZIONE 

I sistemi informatici e le procedure software, preposte al funzionamento di questo sito web, acquisiscono, nel corso del loro normale esercizio, alcuni dati la cui trasmissione è insita nell'uso dei protocolli di comunicazione di Internet. Si tratta di informazioni che non sono raccolte per essere associate a interessati identificati, ma che per loro stessa natura potrebbero, attraverso elaborazioni ed associazioni con dati detenuti da terzi, permettere di identificare gli utenti. In questa categoria di dati rientrano gli indirizzi IP o i nomi a dominio dei computer utilizzati dagli utenti che si connettono al sito, gli indirizzi in notazione URI (Uniform Resource Identifier: è una stringa che identifica univocamente una risorsa generica che può essere un indirizzo web, un documento, un file ecc. ) delle risorse richieste, l'orario della richiesta, il metodo utilizzato nel sottoporre la richiesta al server, la dimensione del file ottenuto in risposta, il codice numerico indicante lo stato della risposta data dal server (buon fine, errore, ecc.) ed altri parametri relativi al sistema operativo e all'ambiente informatico dell'utente (browser utilizzato dall'utente). 

Il sistema non consente invece di raccogliere l'identità dell'utente che si collega. 

Tali dati sono utilizzati unicamente su base aggregata e mai personalizzata, per analizzare statisticamente il comportamento dell'utenza al fine di comprendere come i visitatori utilizzano il sito e per misurare l'interesse riscontrato per le diverse pagine che compongono il sito. Ciò consente di migliorare il contenuto del sito e semplificarne e di rendere più efficiente la consultazione.

Questi dati vengono utilizzati al solo fine di ricavare informazioni statistiche anonime sull'uso del sito e per controllarne il corretto funzionamento e sono conservati per il periodo necessario alle finalità definite nella presente informativa. I dati in questione potrebbero essere utilizzati per l'accertamento di responsabilità in caso di eventuali reati informatici ai danni del nostro sito, nel rispetto delle garanzie imposte dalla legge. Si precisa che l'utilizzo dei dati di navigazione e dei cookies non è in alcun modo finalizzato alla "profilazione dell'utente" e cioè una tecnica volta alla raccolta di informazioni sui consumatori per meglio indirizzare campagne promozionali e offerte di vendita.

CONFIGURAZIONE DEI LOG DEL WEB SERVER DEL CINECA 

Durante la navigazione il browser di ogni utente comunica al web server del Cineca l'indirizzo IP del navigatore. L'indirizzo IP è un numero assegnato automaticamente ad ogni computer durante la navigazione sul web.

Il web server del Cineca è configurato in maniera tale da non consentire l'identificazione dell'utente (nome utente) associato all'indirizzo IP o altre informazioni di identità personale pertanto l'utente resta anonimo durante la visita del sito.

L'UTILIZZO DI COOKIES E ALTRI SISTEMI DI TRACCIAMENTO

Si veda l'informativa disponibile al seguente URL:
https://www.cineca.it/privacy/cookies-cineca




DESTINATARI DEI DATI

I destinatari dei dati raccolti a seguito della compilazione di form o invio di e-mail o sottoscrizione al sito sono il Titolare del trattamento (Cineca) e gli eventuali Responsabili del trattamento nominati dal Titolare, nonché le persone fisiche all’interno del Cineca autorizzate al trattamento dei dati per le finalità sopra riportate. 

I dati della navigazione (indirizzo IP, sito di provenienza, browser utilizzati, S.O utilizzato, pagine visitate, tempo di permanenza nelle singole pagine ecc. ) alle pagine del sito mistralportal.eu e mistralportal.it sono unicamente trasmessi alla società Google che fornisce al Cineca il servizio denominato Google Analytics  (http://www.google.com/analytics/): si tratta di un servizio di elaborazione statistica degli accessi al sito, che vengono utilizzati unicamente all’interno del progetto Mistral,  per analizzare l'utilizzo del sito da parte degli utenti in un'ottica di miglioramento del servizio offerto e per rendere più rapido e facilmente accessibile l'utilizzo del sito.

Tali dati non vengono in alcun modo trattati per definire il profilo o la personalità dell'interessato, o per analizzare abitudini o scelte di consumo a fini commerciali. 

I suoi dati personali non saranno soggetti a diffusione. 

CONSERVAZIONE DEI DATI

Salvo il caso in cui l’interessato non esprima la richiesta di cancellazione dei propri dati personali, i dati raccolti saranno conservati fino a che saranno necessari rispetto alle legittime finalità per le quali sono stati raccolti.

 

DIRITTI DELL’INTERESSATO E MODALITA’ DI ESERCIZIO 

Si precisa che in riferimento ai suoi dati personali conferiti, è detentore dei seguenti diritti:

1.	di accesso ai suoi dati personali;
2.	di ottenere la rettifica o la cancellazione degli stessi o la limitazione del trattamento che lo riguardano;
3.	di opporsi al trattamento;
4.	di proporre reclamo all'autorità di controllo (Garante per la protezione dei dati personali)
Per esercitare i diritti sopra riportati potrà rivolgersi al Titolare del trattamento al seguente indirizzo: Cineca Consorzio Interuniversitario – via Magnanelli 6/3, 40033 Casalecchio di Reno (BO) oppure all’indirizzo di posta elettronica: privacy@cineca.it all’attenzione del “Responsabile della protezione dei dati personali”.  Al fine di agevolare il rispetto dei termini di legge, si consiglia di riportare nella richiesta la dicitura "Esercizio diritti ex art. 15 e ss. del Regolamento Europeo n. 679 /2016".

Il Titolare del trattamento è tenuto a fornirle una risposta entro un mese dalla richiesta, estensibili fino a tre mesi in caso di particolare complessità della richiesta. 
`;

    this.policy_en = `
This information, made pursuant to Regulation (EU) 2016/679 (hereinafter the "Regulation"), describes the methods of processing of personal data of users who consult the Mistral project website or access the meteo-hub platform, accessible electronically to the following web addresses:<br/>
<ul>
    <li>mistralportal.eu</li>
    <li>mistralportal.it</li>
    <li>meteo-hub.hpc.cineca.it</li>
</ul>
This information is provided solely for those who access and interact with the sites listed above and not for all other websites that may be consulted by the user through hypertext links on the site, for which Cineca is not responsible.<br/>
<br/>
We therefore provide you with the following information:<br/>
<br/>

<h5>HOLDER OF DATA PROCESSING</h5>
The Holder of the treatment of personal data entered during the consultation of our site and any other data entered voluntarily by the user in filling out information request forms, is the "CINECA - Interuniversity Consortium - Via Magnanelli 6/3 cap. 40033 Casalecchio di Reno (BO) - Tel. Switchboard 051 6171411" e-mail: privacy@cineca.it<br/>
<br/>
You can contact the Holder of the treatment by writing to the above address or by sending an e-mail to the following e-mail address: privacy@cineca.it<br/>
<br/>

<h5>RESPONSIBLE FOR DATA PROTECTION</h5>
The Data Protection Officer (DPO) can be reached at the following address: <br/>Cineca Consorzio Interuniversitario - via Magnanelli 6/3 email: privacy@cineca.it<br/>
<br/>

<h5>LEGAL BASIS OF THE TREATMENT</h5>
The legal basis of the processing is represented by the pursuit of the legitimate interest of the Cineca as a coordinating partner of the Mistral project, pursuant to Article 6 paragraph f) of the Regulation, to the publication on the web of the project informative site aimed at the dissemination of activities and initiatives dissemination of the project itself.<br/> 

The provision of personal data provided voluntarily in completing the form accessible on the CONTACTS page of the Mistral website or by sending e-mail or to register your login credentials is optional. Any refusal to provide them may make it impossible to use the requested Services. The data requested are those strictly necessary to respond to the user's requests (contact details).<br/> 
<br/> 

<h5>PURPOSE OF THE TREATMENT AND TYPE OF DATA PROCESSED</h5>

<h5>DATA ENTERING VOLUNTARILY BY THE USER</h5>
The personal data provided directly by users through the compilation of web based forms for sending comments or for registering on the site in order to receive information, or for authentication to the digital Meteo-hub platform, will be used to allow the sending the requested information material (newsletter, replies to requests for information, sending "Mistral" publications) and / or to allow access to the meteo-hub platform and the use of the services offered and will eventually be communicated only to the other partner entities of the project.<br/>
<br/>

<h5>NAVIGATION DATA</h5>
The computer systems and software procedures, responsible for the functioning of this website, acquire, during their normal operation, some data whose transmission is inherent in the use of Internet communication protocols. This information is not collected to be associated with identified interested parties, but by their very nature could, through processing and association with data held by third parties, allow users to be identified. This category of data includes IP addresses or domain names of computers used by users who connect to the site, URI (Uniform Resource Identifier: addresses) is a string that uniquely identifies a generic resource that can be a web address, a document, a file etc. of the requested resources, the time of the request, the method used in submitting the request to the server, the size of the file obtained in response, the numeric code indicating the status of the response given by the server (successful , error, etc.) and other parameters relating to the operating system and the user's computer environment (browser used by the user).<br/>
<br/>
The system does not allow instead to collect the identity of the user who connects.<br/>
<br/>
These data are used only on an aggregate basis and never personalized, to statistically analyze the behavior of the user in order to understand how visitors use the site and to measure the interest found for the different pages that make up the site. This makes it possible to improve the content of the site and simplify it and make the consultation more efficient.<br/>
<br/>
These data are used for the sole purpose of obtaining anonymous statistical information on the use of the site and to check its correct functioning and are kept for the period necessary for the purposes defined in this statement. The data in question could be used to ascertain responsibility in the event of computer crimes against our site, in compliance with the guarantees imposed by the law. It should be noted that the use of navigation data and cookies is in no way aimed at "user profiling", that is, a technique aimed at gathering information on consumers to better target promotional campaigns and sales offers.<br/>
<br/>

<h5>CONFIGURING THE LOGS OF THE CINECA WEB SERVER</h5>
While browsing, each user's browser communicates to the Cineca web server the IP address of the navigator. The IP address is a number automatically assigned to each computer while browsing the web.<br>
<br/>
The Cineca web server is configured in such a way as not to allow the identification of the user (user name) associated with the IP address or other personal identity information, therefore the user remains anonymous during the site visit.<br>
<br/>

<h5>THE USE OF COOKIES AND OTHER TRACKING SYSTEMS</h5>
See the information available at the following URL:
https://www.cineca.it/privacy/cookies-cineca<br/>
<br/>

<h5>DATA ADDRESSEES</h5>
The recipients of the data collected after completing the form or sending an e-mail or subscription to the site are the HOLDER OF DATA PROCESSING (Cineca) and any Data Processors appointed by the Holder, as well as the physical persons within the Cineca authorized to process the data for the purposes indicated above<br/>.
<br/>
The navigation data (IP address, site of origin, browser used, OS used, pages visited, time spent on individual pages, etc.) on the pages of the website mistralportal.eu and mistralportal.it are only transmitted to the Google company that provides the Cineca the service called Google Analytics (http://www.google.com/analytics/): it is a service of statistical processing of site accesses, which are used only within the mistral project, to analyze usage of the site by users in order to improve the service offered and to make the use of the site quicker and easier to access.<br/>
These data are not processed in any way to define the profile or personality of the person concerned, or to analyze habits or consumption choices for commercial purposes.<br/>
Your personal data will not be subject to disclosure.<br/>
<br/>

<h5>DATA STORAGE</h5>
Except in the event that the data subject does not express the request for deletion of his personal data, the data collected will be kept until they are necessary with respect to the legitimate purposes for which they were collected.<br/>
<br/>

<h5>RIGHTS OF THE INTERESTED PARTY AND METHOD OF EXERCISE</h5>
It is specified that in reference to your personal data, you are the holder of the following rights:<br/>
<ol>
<li>access to your personal data;</li>
<li>to obtain the rectification or cancellation of the same or the limitation <br/>of the treatment concerning it;</li>
<li>to oppose the processing;</li>
<li>to lodge a complaint with the supervisory authority (Guarantor for the prot<br/>ection of personal data)</li>
</ol>

To exercise the above rights, you can contact the Holder of data processing  at the following address: Cineca Interuniversity Consortium - via Magnanelli 6/3, 40033 Casalecchio di Reno (BO) or at the e-mail address: privacy@cineca.it for the attention of "Responsible for the protection of personal data". In order to facilitate compliance with the terms of the law, it is advisable to include in the request the words "Exercise of rights pursuant to article 15 and following of European Regulation n. 679/2016".<br/>
<br/>
The Holder of data processing is required to provide a response within one month of the request, extendable up to three months if the request is particularly complex.<br/>
		`;
  }
}
