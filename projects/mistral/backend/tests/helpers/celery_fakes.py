"""Fake minimali di Celery per i test di integrazione che devono restare locali.

Questi helper sono volutamente semplici. Permettono a un test di chiamare il vero
endpoint Flask o la vera funzione del task, sostituendo solo lo strato di trasporto
Celery che normalmente parlerebbe con il broker e con i worker esterni (l'oggetto
restituito da ``celery.get_instance()`` del connettore restapi).

In pratica servono quando un test vuole dimostrare che:

- l'applicazione accetta l'invio di un task,
- la logica di scheduling decide se un task va inviato oppure no,
- viene creata una riga di richiesta con il contenuto atteso,

senza dipendere anche da RabbitMQ, dai tempi dei worker o dal codice di estrazione
pesante.
"""

from __future__ import annotations

from typing import Any

from celery import states

import mistral.tasks.data_extraction as data_extraction_task
from mistral.services.sqlapi_db_manager import SqlApiDbManager


class AcceptTasksWithoutRunningCelery:
    """Registra gli invii di task Celery senza mai inoltrarli al broker reale.

    I test usano questo fake quando vogliono che il codice applicativo si comporti
    come se l'invio del task fosse riuscito, mantenendo l'esecuzione tutta nello
    stesso processo. Il fake salva ogni invio in ``sent_tasks``, cosi il test puo
    ispezionare cosa sarebbe stato inviato a Celery.
    """

    def __init__(self, *accepted_task_names: str) -> None:
        self.sent_tasks: list[dict[str, Any]] = []
        self.celery_app = _AcceptingCeleryApp(
            accepted_task_names=set(accepted_task_names),
            sent_tasks=self.sent_tasks,
        )

    def delete_periodic_task(self, *args: Any, **kwargs: Any) -> bool:
        """Simula la rimozione riuscita di una voce periodica di Celery.

        Alcuni percorsi del codice si aspettano che il wrapper Celery esponga
        questo metodo. Il fake restituisce sempre ``True`` perche durante il test
        non esiste un vero task periodico da rimuovere.
        """
        return True


class _AcceptingCeleryApp:
    """Facade minimale di ``celery_app`` per ``AcceptTasksWithoutRunningCelery``."""

    def __init__(
        self,
        *,
        accepted_task_names: set[str],
        sent_tasks: list[dict[str, Any]],
    ) -> None:
        self.accepted_task_names = accepted_task_names
        self.sent_tasks = sent_tasks

    def send_task(self, name: str, *args: Any, **kwargs: Any) -> None:
        """Salva l'invio di un task invece di mandarlo a Celery.

        Se ``accepted_task_names`` non e vuoto, il fake controlla anche che il codice
        sotto test invii solo i nomi di task attesi dal test.
        """
        if self.accepted_task_names:
            assert name in self.accepted_task_names
        self.sent_tasks.append({"name": name, "args": args, "kwargs": kwargs})
        return None


class InlineDataReadyExtractionCelery:
    """Sostituisce l'esecuzione di ``data_extract`` nel worker con un effetto sul DB.

    I test periodici data-ready vogliono verificare la decisione dello scheduler:
    va generata o no una nuova richiesta di estrazione? Non serve eseguire il vero
    worker di estrazione. Questo fake traduce l'invio del task Celery nella stessa
    riga ``Request`` che il resto del test si aspetta di trovare nel DB.
    """

    def __init__(self, db: Any) -> None:
        self.celery_app = _InlineDataReadyExtractionApp(db)

    def delete_periodic_task(self, *args: Any, **kwargs: Any) -> bool:
        """Finge che la rimozione del task periodico sia riuscita.

        Il percorso data-ready puo chiamare questo metodo sul wrapper Celery. Per
        questo fake non c'e nulla da rimuovere, quindi il metodo segnala solo
        successo.
        """
        return True


class InlineDataExtractCelery:
    """Esegue ``data_extract`` subito, nello stesso processo del test.

    Alcuni test di integrazione hanno bisogno dei veri effetti dell'estrazione,
    come la creazione di file e la pubblicazione opendata, ma vogliono comunque
    evitare di dipendere da RabbitMQ e da worker Celery esterni. Questo fake tiene
    locale il trasporto del task chiamando direttamente ``data_extract.run(...)``.
    """

    def __init__(self) -> None:
        self.celery_app = _InlineDataExtractApp()

    def delete_periodic_task(self, *args: Any, **kwargs: Any) -> bool:
        """Segnala successo nella rimozione del task periodico anche se non esiste.

        Il fake inline non registra mai veri task periodici in Celery, ma il wrapper
        usato in produzione deve comunque esporre questo metodo. Restituire ``True``
        soddisfa quei percorsi del codice senza aggiungere altro setup al test.
        """
        return True


class _InlineDataReadyExtractionApp:
    """Facade minimale di ``celery_app`` che emula gli effetti di ``data_extract``."""

    def __init__(self, db: Any) -> None:
        self.db = db

    def send_task(
        self,
        name: str,
        args: tuple[Any, ...] | None = None,
        **kwargs: Any,
    ) -> None:
        """Converte l'invio di ``data_extract`` in una riga di richiesta sintetica.

        Il metodo verifica che il codice sotto test stia davvero inviando
        ``data_extract`` in modalita ``data_ready``. Poi salta gli invii duplicati
        per lo stesso reftime oppure inserisce una nuova richiesta riuscita, cosi
        il chiamante puo fare asserzioni sullo stato risultante della schedule.
        """
        assert name == "data_extract"
        assert args is not None
        (
            user_id,
            datasets,
            reftime,
            filters,
            postprocessors,
            output_format,
            _request_id,
            _only_reliable,
            _pushing_queue,
            schedule_id,
            data_ready,
            opendata,
        ) = args
        assert data_ready is True

        last_request = (
            self.db.Request.query.filter_by(
                schedule_id=schedule_id,
                status=states.SUCCESS,
            )
            .order_by(self.db.Request.submission_date.desc())
            .first()
        )
        if last_request and last_request.args.get("reftime") == reftime:
            return None

        request_name = SqlApiDbManager.get_schedule_name(self.db, schedule_id)
        request = SqlApiDbManager.create_request_record(
            self.db,
            user_id,
            request_name,
            {
                "datasets": datasets,
                "reftime": reftime,
                "filters": filters,
                "postprocessors": postprocessors,
                "output_format": output_format,
            },
            schedule_id=schedule_id,
            opendata=opendata,
        )
        request.status = states.SUCCESS
        self.db.session.add(request)
        self.db.session.commit()
        return None


class _InlineDataExtractApp:
    """Facade minimale di ``celery_app`` che esegue ``data_extract`` inline."""

    def send_task(
        self,
        name: str,
        args: tuple[Any, ...] | list[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Esegue il vero task di estrazione invece di metterlo in coda."""
        assert name == "data_extract"
        assert args is not None
        data_extraction_task.data_extract.run(*args)
        return None