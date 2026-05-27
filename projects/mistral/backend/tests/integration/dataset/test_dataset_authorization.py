"""Integration tests for dataset authorization and visibility rules.

These tests build a small controlled scenario with temporary datasets and a
temporary user so they can verify how the API behaves with:

- public datasets,
- private datasets not assigned to the user,
- private datasets explicitly assigned to the user.
"""

import json
from typing import Any

from mistral.models.sqlalchemy import DatasetCategories
from mistral.tests.helpers.datasets import first_public_dataset_id
import pytest
from faker import Faker
from restapi.connectors import sqlalchemy
from restapi.tests import API_URI, BaseTests, FlaskClient


pytestmark = [
    pytest.mark.integration,
    pytest.mark.deterministic,
    pytest.mark.runtime_sensitive,
]


PUBLIC_DATASET_NAME = "lm5"  # "ICON_2I_SURFACE_PRESSURE_LEVELS"


def _delete_dataset(db, dataset_id: int) -> None:
    """Delete one temporary dataset created by the test, including user links.

    The test may create datasets only for its own setup. Before removing the row
    it also detaches any many-to-many user associations so database cleanup is
    complete and predictable.
    """
    # Rimuoviamo lo stato creato dal test per non lasciare dati che possano influenzare
    # gli scenari successivi.
    dataset = db.Datasets.query.get(dataset_id)
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if dataset is None:
        return

    # Scorriamo gli elementi restituiti dal backend per trovare solo quelli rilevanti
    # per questo scenario.
    for user in dataset.users.all():
        dataset.users.remove(user)

    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.delete(dataset)
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.commit()


def _ensure_dataset_exists(db, cleanup_registry, dataset_name: str):
    """Return a usable dataset for the scenario, creating one if necessary.

    The authorization test needs a couple of concrete dataset rows with known
    names. If the environment already provides them, the test reuses them. If it
    does not, the helper creates temporary datasets and registers cleanup so the
    scenario remains self-contained.
    """
    # Costruiamo lo stato controllato richiesto dal test, usando gli stessi canali che
    # il backend espone in produzione quando possibile.
    dataset = db.Datasets.query.filter_by(name=dataset_name).first()
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if dataset is not None:
        # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo
        # direttamente nelle asserzioni.
        return dataset

    # Leggiamo lo stato dal database di test per collegare la risposta API agli effetti
    # persistiti dal backend.
    license_entry = db.License.query.filter_by().first()
    # Leggiamo lo stato dal database di test per collegare la risposta API agli effetti
    # persistiti dal backend.
    attribution = db.Attribution.query.first()
    # Gestiamo esplicitamente il caso limite, cosi il test spiega cosa deve succedere
    # quando lo stato non e quello ideale.
    if license_entry is None or attribution is None:
        # Saltiamo lo scenario quando i dati runtime richiesti non esistono, perche il
        # contratto non sarebbe verificabile in modo significativo.
        pytest.skip(
            "At least one license and one attribution are required to create test datasets"
        )

    dataset = db.Datasets(
        arkimet_id=dataset_name,
        name=dataset_name,
        description=f"Temporary dataset for {dataset_name}",
        category=DatasetCategories.OBS,
        fileformat="bufr",
        license_id=license_entry.id,
        attribution_id=attribution.id,
    )
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.add(dataset)
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.commit()
    # Agganciamo il cleanup appena creiamo la risorsa, cosi il teardown resta affidabile
    # anche in caso di fallimento.
    cleanup_registry.add(lambda: _delete_dataset(db, dataset.id))

    # Restituiamo un valore gia normalizzato, cosi il chiamante puo usarlo direttamente
    # nelle asserzioni.
    return dataset


def test_dataset_endpoints_respect_user_authorizations(
    client: FlaskClient,
    faker: Faker,
    cleanup_registry,
) -> None:
    """Verify how dataset visibility changes with public access and explicit grants.

    The test prepares two private datasets, grants the user access to only one of
    them, and then checks that the API exposes exactly what that user should see.
    It also flips the user's ``open_dataset`` flag to confirm that explicit grants
    still work even after public-catalog access is disabled.
    """
    # arrange
    # Prepariamo lo scenario catalogo dataset con dati minimi e controllati, cosi la
    # verifica successiva resta legata a un comportamento preciso.
    base = BaseTests()
    # Leggiamo lo stato dal database di test per collegare la risposta API agli effetti
    # persistiti dal backend.
    db = sqlalchemy.get_instance()
    dataset_to_auth = _ensure_dataset_exists(
        db,
        cleanup_registry,
        "sa_dataset_special",
    )
    unauth_dataset = _ensure_dataset_exists(
        db,
        cleanup_registry,
        "sa_dataset",
    )

    original_dataset_to_auth_license_id = dataset_to_auth.license_id
    original_unauth_dataset_license_id = unauth_dataset.license_id

    fake_private_group = db.GroupLicense(
        name="private_group",
        descr="mock private_group",
        is_public=False,
    )
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.add(fake_private_group)
    db.session.flush()

    fake_private_license = db.License(
        name="private auth license",
        descr="mock private license",
        group_license_id=fake_private_group.id,
    )
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.add(fake_private_license)
    db.session.flush()

    unauth_dataset.license_id = fake_private_license.id
    dataset_to_auth.license_id = fake_private_license.id
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.add(unauth_dataset)
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.add(dataset_to_auth)
    # Persistiamo la modifica nel database di test, altrimenti le chiamate successive
    # non vedrebbero lo scenario preparato.
    db.session.commit()

    permissions: dict[str, Any] = {
        "datasets": json.dumps([str(dataset_to_auth.id)]),
        "open_dataset": True,
    }
    # Creiamo un utente temporaneo con permessi mirati, cosi il test non dipende da
    # account preesistenti.
    user_uuid, user_data = base.create_user(client, permissions)
    # Effettuiamo il login per ottenere header autentici, identici a quelli usati dalle
    # chiamate API successive.
    user_headers, _ = base.do_login(
        client,
        user_data.get("email"),
        user_data.get("password"),
    )
    # Effettuiamo il login per ottenere header autentici, identici a quelli usati dalle
    # chiamate API successive.
    admin_headers, _ = base.do_login(client, None, None)

    try:
        # act
        # Eseguiamo l'azione sotto test una sola volta, mantenendo separata la fase di
        # verifica dal setup.
        list_response = client.get(f"{API_URI}/datasets", headers=user_headers)
        public_dataset_id = first_public_dataset_id(
            base.get_content(list_response) or []
        )
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        public_dataset_response = client.get(
            f"{API_URI}/datasets/{public_dataset_id}",
            headers=user_headers,
        )
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        missing_dataset_response = client.get(
            f"{API_URI}/datasets/{faker.pystr()}",
            headers=user_headers,
        )
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        unauthorized_dataset_response = client.get(
            f"{API_URI}/datasets/sa_dataset",
            headers=user_headers,
        )
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        authorized_dataset_response = client.get(
            f"{API_URI}/datasets/sa_dataset_special",
            headers=user_headers,
        )

        update_response = client.put(
            f"{API_URI}/admin/users/{user_uuid}",
            headers=admin_headers,
            json={
                "open_dataset": False,
                "datasets": permissions["datasets"],
            },
        )
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        hidden_public_dataset_response = client.get(
            f"{API_URI}/datasets/{public_dataset_id}",
            headers=user_headers,
        )
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        still_authorized_dataset_response = client.get(
            f"{API_URI}/datasets/sa_dataset_special",
            headers=user_headers,
        )
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        error_dataset_response = client.get(
            f"{API_URI}/datasets/error",
            headers=user_headers,
        )
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        duplicates_dataset_response = client.get(
            f"{API_URI}/datasets/duplicates",
            headers=user_headers,
        )

        # assert
        # Verifichiamo l'effetto osservabile prodotto dal backend, cioe il contratto che
        # questo test vuole proteggere.
        assert list_response.status_code == 200
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert isinstance(base.get_content(list_response), list)
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine
        # prima di usare il payload.
        assert public_dataset_response.status_code == 200
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert isinstance(base.get_content(public_dataset_response), dict)
        # Verifichiamo che la risposta segnali correttamente una risorsa assente o non
        # visibile prima di usare il payload.
        assert missing_dataset_response.status_code == 404
        # Verifichiamo che la risposta segnali correttamente una risorsa assente o non
        # visibile prima di usare il payload.
        assert unauthorized_dataset_response.status_code == 404

        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine
        # prima di usare il payload.
        assert authorized_dataset_response.status_code == 200
        authorized_content = base.get_content(authorized_dataset_response)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert isinstance(authorized_content, dict)
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert authorized_content["is_public"] is False

        # Verifichiamo che la risposta confermi la cancellazione senza body di risposta
        # prima di usare il payload.
        assert update_response.status_code == 204
        # Verifichiamo che la risposta segnali correttamente una risorsa assente o non
        # visibile prima di usare il payload.
        assert hidden_public_dataset_response.status_code == 404
        # Verifichiamo che la risposta confermi che l'operazione richiesta e andata a buon fine
        # prima di usare il payload.
        assert still_authorized_dataset_response.status_code == 200
        # Verifichiamo che la risposta segnali correttamente una risorsa assente o non
        # visibile prima di usare il payload.
        assert error_dataset_response.status_code == 404
        # Verifichiamo che la risposta segnali correttamente una risorsa assente o non
        # visibile prima di usare il payload.
        assert duplicates_dataset_response.status_code == 404
    finally:
        # Eseguiamo una chiamata HTTP reale attraverso il client Flask, cosi routing,
        # autorizzazione e serializzazione vengono verificati insieme.
        user_delete_response = client.delete(
            f"{API_URI}/admin/users/{user_uuid}",
            headers=admin_headers,
        )
        # Verifichiamo che la risposta confermi la cancellazione senza body di risposta
        # prima di usare il payload.
        assert user_delete_response.status_code == 204

        # Leggiamo lo stato dal database di test per collegare la risposta API agli
        # effetti persistiti dal backend.
        current_license = db.License.query.filter_by().first()
        # Controlliamo il contratto specifico dello scenario, non soltanto che il codice
        # sia arrivato fin qui senza eccezioni.
        assert current_license is not None
        unauth_dataset.license_id = original_unauth_dataset_license_id or current_license.id
        dataset_to_auth.license_id = (
            original_dataset_to_auth_license_id or current_license.id
        )
        # Persistiamo la modifica nel database di test, altrimenti le chiamate
        # successive non vedrebbero lo scenario preparato.
        db.session.add(unauth_dataset)
        # Persistiamo la modifica nel database di test, altrimenti le chiamate
        # successive non vedrebbero lo scenario preparato.
        db.session.add(dataset_to_auth)
        db.session.flush()
        # Persistiamo la modifica nel database di test, altrimenti le chiamate
        # successive non vedrebbero lo scenario preparato.
        db.session.delete(fake_private_license)
        # Persistiamo la modifica nel database di test, altrimenti le chiamate
        # successive non vedrebbero lo scenario preparato.
        db.session.delete(fake_private_group)
        # Persistiamo la modifica nel database di test, altrimenti le chiamate
        # successive non vedrebbero lo scenario preparato.
        db.session.commit()