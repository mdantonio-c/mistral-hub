# Piano Di Refactoring Della Suite Test Meteo-Hub

## Come usare questo file oggi

Questo file resta nel repository come rationale storico del refactor, non come manuale operativo principale della suite corrente.

Per orientarti oggi usa prima:

- `projects/mistral/backend/tests/docs/guida_finale_suite_test_backend.md`
- `projects/mistral/backend/tests/README.md`
- `projects/mistral/backend/tests/docs/legacy_to_new_suite_matrix.md`

Torna a questo file solo se ti serve ricostruire il perche delle scelte strutturali che hanno portato alla suite finale.

## Obiettivo storico del piano

L'obiettivo del refactor era ridurre duplicazioni, dipendenze implicite e moduli monolitici, senza perdere copertura funzionale.

In termini pratici il piano puntava a:

- separare i test per dominio funzionale;
- limitare la visibilita delle fixture con `conftest.py` posti nel sottoalbero giusto;
- spostare il riuso cross-area in `helpers/` e lasciare la logica di dominio nei moduli locali di `integration/<area>/`;
- sostituire attese fisse e stato condiviso implicito con polling osservabile e cleanup esplicito;
- tracciare in modo leggibile la corrispondenza `legacy -> nuova suite`.

## Stato attuale

Il piano ha raggiunto il suo obiettivo strutturale.

La suite mantenuta oggi e organizzata cosi:

- `projects/mistral/backend/tests/conftest.py` contiene solo fixture globali di suite;
- `projects/mistral/backend/tests/helpers/` contiene il riuso trasversale;
- `projects/mistral/backend/tests/integration/` contiene i test reali separati per dominio;
- `projects/mistral/backend/tests/docs/` contiene la documentazione mantenuta della suite;
- il root di `projects/mistral/backend/tests/` non contiene piu i vecchi moduli `test_*.py` del refactor.

## Risultati strutturali ottenuti

I risultati del refactor sono questi:

- le aree `access_key`, `arco`, `data`, `data_ready`, `dataset`, `observed`, `opendata`, `postprocessing`, `requests` e `schedules` sono ora isolate sotto `integration/`;
- gli helper condivisi di runtime, cleanup, dataset discovery, schedule wiring e finti wrapper Celery sono stati estratti in moduli dedicati sotto `helpers/`;
- i contratti coperti dai monoliti storici sono stati riallineati nella matrice `legacy -> nuova suite`;
- la documentazione corrente e stata concentrata in quattro file mantenuti: guida finale, README, matrice e questo piano storico.

## Cosa non fa piu questo file

Questo documento non traccia piu:

- work package intermedi;
- checklist operative degli agenti;
- prompt storici;
- riferimenti di riga a moduli legacy ormai rimossi dal root della suite.

Questi dettagli non sono piu necessari per usare o capire lo stato corrente della suite.

## Quando consultarlo

Consulta questo file solo se ti serve capire il razionale di alto livello dietro a decisioni come:

- perche il punto di divisione corretto e `root` contro `integration`;
- perche una parte del riuso e stata spostata in `helpers/` mentre altra logica e rimasta in `support.py` locali;
- perche i nuovi test vanno creati direttamente sotto `integration/<area>/` e non nel root della cartella `tests`.

Per il lavoro quotidiano, il punto di verita resta invece nei tre file operativi:

- `projects/mistral/backend/tests/docs/guida_finale_suite_test_backend.md`
- `projects/mistral/backend/tests/README.md`
- `projects/mistral/backend/tests/docs/legacy_to_new_suite_matrix.md`