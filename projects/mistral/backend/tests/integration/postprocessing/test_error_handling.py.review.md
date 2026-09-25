# Review — `test_error_handling.py`

> File di review generato per facilitare la revisione manuale della suite. Non modifica codice.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/integration/postprocessing/test_error_handling.py](projects/mistral/backend/tests/integration/postprocessing/test_error_handling.py)
- **Scopo**: verificare i **percorsi di fallimento** del postprocessing forecast e observed: postprocessore sconosciuto; derived/statistic forecast con input mancanti; derived/statistic observed con input incompleti. In tutti i casi la request deve restare in stato `FAILURE` e l'errore emergere come `Ignore`.
- **Tipologia**: integrazione **end-to-end reale** con **monkeypatch manuale** degli hook di fallimento Celery (vedi §6). `data_extract` è eseguito sincrono via `send_task`. Marker (modulo): `integration`, `deterministic`, **`runtime_sensitive`**.
- **RUNTIME-SENSITIVE — skip silenziosi**: i 3 test forecast usano `pp_forecast_env` (skip su `lm5` assente); i 2 test observed usano `pp_observed_env` (skip su `agrmet`/`ALCHEMY_*`/dati assenti).

## 2. Backend realmente testato

| Elemento | Path | Ruolo |
|---|---|---|
| Task `data_extract` (gestione eccezioni) | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L42) | Due `except`: il primo cattura `PostProcessingException` (→ `error_message=str(exc)`, `raise Ignore`); il secondo cattura `Exception` generica (→ `error_message="Failed to extract data"`, `raise exc`). Il `finally` fa `commit` e (status≠SUCCESS) chiamerebbe `notify_by_email`. |
| Controllo postprocessore abilitato | [tasks/data_extraction.py](projects/mistral/backend/tasks/data_extraction.py#L265) | `if pp_type not in enabled_postprocessors: raise ValueError("Unknown post-processor", pp_type)` ([L279](projects/mistral/backend/tasks/data_extraction.py#L279)). |
| `pp1.pp_derived_variables` | [tools/derived_variables.py](projects/mistral/backend/tools/derived_variables.py#L10) | Con input mancanti, `vg6d_transform`/`v7d_transform` fallisce → `PostProcessingException("Error in post-processing: no results")`. |
| `pp2.pp_statistic_elaboration` | [tools/statistic_elaboration.py](projects/mistral/backend/tools/statistic_elaboration.py#L15) | Timerange non trovato → `PostProcessingException("Error in post-processing: Timeranges … not found …")`. |
| Wrapper `@CeleryExt.task` | `restapi.connectors.celery` | `except Ignore → mark_task_as_failed_ignore`; `except Exception → mark_task_as_failed`. **Entrambi gli hook sono patchati dal test** (vedi §6). |

## 3. Mappa delle dipendenze

| Dipendenza | Tipo | Dove definita | Cosa fa / effetti collaterali |
|---|---|---|---|
| `pp_forecast_env` / `pp_observed_env` | fixture | [postprocessing/conftest.py](projects/mistral/backend/tests/integration/postprocessing/conftest.py) | Ambienti `lm5`/`agrmet`; skip silenziosi. |
| `PostprocessingEnv.execute(..., expect_failure=True)` | helper | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | **Monkeypatcha** `mark_task_as_failed`, `mark_task_as_failed_ignore`, `notify_by_email`; invia il task; ripristina nel `finally`. |
| `PostprocessingEnv.assert_failure` | helper | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Asserisce `status=="FAILURE"` e (se messaggio non `None`) substring in `error_message`. |
| `Ignore` | eccezione | `restapi.connectors.celery` (re-export di `celery.exceptions.Ignore`) | Atteso da `pytest.raises`. |
| `forecast_derived_variable_missing_filters` / `forecast_statistic_elaboration_missing_filters` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Filtri volutamente incompleti/invalidi. |
| `observed_derived_variable_missing_filters` | builder | [postprocessing/support.py](projects/mistral/backend/tests/integration/postprocessing/support.py) | Solo B12101 (temperatura): insufficiente per derived **e** per statistic. |
| `faker.pystr()` | dato | `faker` | Genera il `processor_type` ignoto del primo test. |

## 4. Analisi dettagliata di ogni test

### `test_unknown_postprocessor_marks_request_as_failure`
- **Obiettivo**: un `processor_type` sconosciuto fa fallire la request lasciandola in `FAILURE`.
- **Backend coinvolto**: controllo `enabled_postprocessors` → `raise ValueError(...)` → **secondo** `except` del task (`error_message="Failed to extract data"`, rilancio) → wrapper `except Exception` → `mark_task_as_failed` (patchato → `raise Ignore(str(exc))`).
- **Flusso**: `create_request()` → `postprocessor={"processor_type": faker.pystr()}` → `with pytest.raises(Ignore, match="Unknown post-processor"): execute(postprocessors=[pp], expect_failure=True)` → `assert_failure(request_id, expected_message=None)`.
- **Assert**: l'eccezione è `Ignore` con messaggio contenente `"Unknown post-processor"`; la request è `FAILURE`.
- **Dettaglio cruciale**: `expected_message=None` è **intenzionale**: il `error_message` **persistito** è `"Failed to extract data"` (ramo generico), mentre la stringa `"Unknown post-processor"` vive solo nell'eccezione `Ignore`. Il test verifica il messaggio sull'eccezione (`match=`) e **salta** il controllo sul DB.
- **Casi coperti**: validazione del tipo postprocessore + ramo `mark_task_as_failed` (Exception generica).

### `test_forecast_derived_variables_require_all_inputs`
- **Obiettivo**: derived forecast fallisce se mancano i campi sorgente.
- **Backend coinvolto**: estrazione (solo P) → `pp1.pp_derived_variables` (`vg6d_transform` exit≠0) → `PostProcessingException` → **primo** `except` (`raise Ignore`) → wrapper `except Ignore` → `mark_task_as_failed_ignore` (patchato → rilancia `Ignore`).
- **Flusso**: `create_request()` → `with pytest.raises(Ignore): execute(filters=forecast_derived_variable_missing_filters(), postprocessors=[forecast_derived_variable_postprocessor()], expect_failure=True)` → `assert_failure(request_id)`.
- **Assert**: `Ignore` sollevata; `status=FAILURE`; `error_message` contiene `"Error in post-processing"` (default).
- **Casi coperti**: ramo `PostProcessingException` + `mark_task_as_failed_ignore`.

### `test_forecast_statistic_elaboration_requires_valid_timerange`
- **Obiettivo**: statistic forecast fallisce con selezione di timerange invalida.
- **Backend coinvolto**: `pp2.pp_statistic_elaboration` → nessun input per il timerange richiesto → `PostProcessingException("…Timeranges … not found …")`.
- **Flusso**: `create_request()` → `with pytest.raises(Ignore): execute(filters=forecast_statistic_elaboration_missing_filters(), postprocessors=[forecast_statistic_elaboration_postprocessor()], expect_failure=True)` → `assert_failure(request_id)`.
- **Assert**: `Ignore`; `FAILURE`; `error_message` contiene `"Error in post-processing"`.
- **Casi coperti**: ramo timerange-non-trovato.

### `test_observed_derived_variables_require_all_inputs`
- **Obiettivo**: derived observed fallisce con input mancanti.
- **Backend coinvolto**: `observed_extraction` (BUFR) → `pp1.pp_derived_variables` (`v7d_transform`) → `PostProcessingException`.
- **Flusso**: `create_request()` → `with pytest.raises(Ignore): execute(filters=observed_derived_variable_missing_filters(), postprocessors=[observed_derived_variable_postprocessor()], expect_failure=True)` → `assert_failure(request_id)`.
- **Assert**: `Ignore`; `FAILURE`; `"Error in post-processing"`.
- **Casi coperti**: ramo derived observed fallito.

### `test_observed_statistic_elaboration_requires_all_inputs`
- **Obiettivo**: statistic observed fallisce con input incompleti.
- **Backend coinvolto**: `pp2.pp_statistic_elaboration` ramo BUFR → `PostProcessingException`.
- **Flusso**: `create_request()` → `with pytest.raises(Ignore): execute(filters=observed_derived_variable_missing_filters(), postprocessors=[observed_statistic_elaboration_postprocessor()], expect_failure=True)` → `assert_failure(request_id)`.
- **Assert**: `Ignore`; `FAILURE`; `"Error in post-processing"`.
- **Casi coperti**: ramo statistic observed fallito. **Nota**: riusa volutamente `observed_derived_variable_missing_filters` (solo B12101) per non fornire il timerange/var necessari alla statistica.

## 5. Call chain

```
execute(req, expect_failure=True):
  monkeypatch celery_connector.mark_task_as_failed        → raise Ignore(str(exc))
  monkeypatch celery_connector.mark_task_as_failed_ignore → raise exc (Ignore originale)
  monkeypatch data_extraction_task.notify_by_email        → no-op
  send_task("data_extract", ...)
    data_extract (eager):
      ── ramo "sconosciuto": raise ValueError → except Exception(task) → error_message="Failed to extract data"; raise exc
                              → wrapper except Exception → mark_task_as_failed(patch) → raise Ignore("Unknown post-processor…")
      ── ramo "input mancanti": pp1/pp2 → PostProcessingException → except(task) → error_message=str(exc); raise Ignore
                              → wrapper except Ignore → mark_task_as_failed_ignore(patch) → raise (Ignore originale)
      finally: commit (persiste FAILURE + error_message); notify_by_email(no-op)
  finally: ripristina i 3 simboli originali
pytest.raises(Ignore[, match]) ; assert_failure(req[, expected_message])
```

## 6. Comportamenti nascosti

- **Monkeypatch manuale di un connettore condiviso**: `execute(expect_failure=True)` riscrive a runtime `restapi.connectors.celery.mark_task_as_failed`, `…mark_task_as_failed_ignore` e `mistral.tasks.data_extraction.notify_by_email`, ripristinandoli nel `finally`. Non usa `monkeypatch`/`test_runtime`: è stato globale, sicuro per le normali eccezioni ma fragile in esecuzione parallela.
- **Due hook ≠ due percorsi**: il file esercita **entrambi** i rami del wrapper. Solo il primo test passa per `mark_task_as_failed` (Exception generica → `Ignore` *sintetizzata* dal test); gli altri quattro passano per `mark_task_as_failed_ignore` (`Ignore` *già* sollevata dal task). Per questo servono entrambe le patch.
- **`error_message` persistito diverso dal messaggio dell'eccezione** nel test “sconosciuto”: DB = `"Failed to extract data"`, eccezione = `"Unknown post-processor"`. Da qui `expected_message=None`.
- **`notify_by_email` patchato per sopprimere l'email reale**: nel `finally` del task, con `status=FAILURE`, l'email verrebbe inviata davvero (SMTP). La patch la annulla; senza, i test toccherebbero un servizio esterno.
- **`status=FAILURE` e `error_message` sono persistiti dal `finally` (commit) del task**, *prima* che l'`Ignore` propaghi; per questo `assert_failure` può rileggerli dal DB dopo `pytest.raises`.
- **Il fallimento dipende dall'exit code dei binari**: per i test derived/statistic, l'esito `FAILURE` presuppone che `vg6d_transform`/`v7d_transform` ritorni ≠0 (o che lo split timerange non trovi nulla). È un comportamento del **tool esterno**, non garantito dal solo codice Python (vedi §8).
- **`ValueError` con args-tuple**: `raise ValueError("Unknown post-processor: {}", pp_type)` produce `str(exc)` del tipo `("Unknown post-processor: {}", '…')`; il `match="Unknown post-processor"` è una ricerca di sottostringa, quindi passa comunque.

## 7. Checklist di revisione

- [ ] Confermare che il monkeypatch manuale degli hook Celery sia accettabile o vada migrato su `monkeypatch`/`test_runtime` per il ripristino robusto.
- [ ] Verificare che `vg6d_transform`/`v7d_transform` ritornino davvero errore con input mancanti nell'ambiente CI (altrimenti il test potrebbe non andare in `FAILURE`).
- [ ] Confermare che il messaggio persistito `"Failed to extract data"` per il postprocessore sconosciuto sia il contratto voluto (vs. un messaggio più specifico).
- [ ] Verificare che la soppressione di `notify_by_email` copra tutti i rami di errore (sì: avviene prima dell'invio del task e per qualunque eccezione).
- [ ] Per i test observed: ricordare la doppia guardia di skip (`agrmet` + `ALCHEMY_*`/dati).

## 8. Possibili criticità

- **Fallimento dipendente dai tool esterni**: l'asserzione di `FAILURE` per derived/statistic poggia sul comportamento (exit code) di `vg6d_transform`/`v7d_transform`. Se un giorno il tool producesse output (vuoto) con exit 0, la pipeline potrebbe terminare in `SUCCESS` e il test fallirebbe per ragioni non legate alla logica testata.
- **Over-mocking della gestione errori reale**: patchando gli hook, gli effetti reali (`update_state`, `send_event`, email) **non** vengono testati; si verifica solo che l'errore arrivi come `Ignore` e che la request sia marcata `FAILURE`.
- **Stato globale condiviso**: la riscrittura di simboli di `restapi.connectors.celery` è globale; sotto `xdist`/parallelo potrebbe interferire con altri test che invocano task.
- **Assert volutamente lasco** sul messaggio del test “sconosciuto” (`expected_message=None`): nasconde che il messaggio DB è generico; un revisore potrebbe non accorgersene.
- **Skip silenziosi**: ambienti senza `lm5`/`agrmet`/DBALLE rimuovono i test dalla copertura senza segnalazione evidente.

## 9. Riassunto finale

| Test | Backend | Cosa verifica | Mock/patch | Fixture | Complessità |
|---|---|---|---|---|---|
| `test_unknown_postprocessor_marks_request_as_failure` | `data_extract` (ValueError→`mark_task_as_failed`) | `Ignore("Unknown post-processor")` + `FAILURE` | hook Celery + `notify_by_email` | `pp_forecast_env` | Media |
| `test_forecast_derived_variables_require_all_inputs` | `pp1` (`vg6d_transform`) → `PostProcessingException` | `Ignore` + `FAILURE` (`Error in post-processing`) | hook Celery + email | `pp_forecast_env` | Media |
| `test_forecast_statistic_elaboration_requires_valid_timerange` | `pp2` (timerange non trovato) | `Ignore` + `FAILURE` | hook Celery + email | `pp_forecast_env` | Media |
| `test_observed_derived_variables_require_all_inputs` | `pp1` BUFR (`v7d_transform`) | `Ignore` + `FAILURE` | hook Celery + email | `pp_observed_env` | Media |
| `test_observed_statistic_elaboration_requires_all_inputs` | `pp2` BUFR | `Ignore` + `FAILURE` | hook Celery + email | `pp_observed_env` | Media |
