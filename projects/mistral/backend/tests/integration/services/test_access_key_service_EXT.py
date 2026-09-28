# EXTENSION TRACEABILITY - Prompt 06, modello e service access key.
# Origine: questo modulo aggiunge copertura deterministica per AccessKey.generate,
# AccessKey.is_valid e mistral.services.access_key_service.is_access_key_valid.
# Ambito: verifica scadenza default/null, validita con scadenza assente/futura/passata
# e rifiuto di una chiave presentata diversa da quella salvata.
# Finestra dati: nessun dataset reale e nessun record DB sono necessari; le AccessKey
# sono istanze in memoria non persistite.
# Runtime fake: non servono request Flask, BasicAuth reale o database; il service helper
# testato accetta direttamente il record AccessKey e la chiave fornita.
# Cleanup: nessuno stato persistente viene creato, quindi non serve cleanup_registry.
# Baseline non toccata: il file e un nuovo modulo *_EXT.py nel dominio integration/services.

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from mistral.models.sqlalchemy import AccessKey
from mistral.services.access_key_service import is_access_key_valid


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_access_key_generate_sets_default_and_null_expiration_EXT() -> None:
    """Verifica AccessKey.generate con lifetime default e lifetime None.

    Il metodo e puro rispetto al database: crea istanze AccessKey con token casuale,
    creation valorizzato e expiration calcolata solo quando lifetime_seconds non e None.
    """
    # act - genera una chiave con scadenza default e una senza scadenza.
    default_key = AccessKey.generate(user_id=42)
    no_expiration_key = AccessKey.generate(user_id=42, lifetime_seconds=None)

    # assert - la chiave default ha scadenza futura e scope standard.
    assert default_key.user_id == 42
    assert default_key.key
    assert default_key.creation is not None
    assert default_key.expiration is not None
    assert default_key.expiration > default_key.creation
    assert default_key.scope == "read:arco"

    # assert - lifetime None produce chiave non expiring ma conserva gli altri campi.
    assert no_expiration_key.user_id == 42
    assert no_expiration_key.key
    assert no_expiration_key.expiration is None
    assert no_expiration_key.scope == "read:arco"


def test_access_key_model_is_valid_handles_expiration_states_EXT() -> None:
    """Verifica AccessKey.is_valid per scadenza assente, futura e passata.

    Il model method usa datetime.utcnow naive; il test costruisce datetime naive per
    coprire il contratto senza introdurre confronti timezone non pertinenti.
    """
    # arrange - tre istanze in memoria con stati di expiration distinti.
    now = datetime.utcnow()
    without_expiration = AccessKey(
        key="without-expiration-ext",
        creation=now,
        expiration=None,
        user_id=1,
    )
    future_expiration = AccessKey(
        key="future-expiration-ext",
        creation=now,
        expiration=now + timedelta(hours=1),
        user_id=1,
    )
    past_expiration = AccessKey(
        key="past-expiration-ext",
        creation=now,
        expiration=now - timedelta(hours=1),
        user_id=1,
    )

    # act/assert - il model method deve distinguere i tre stati senza DB.
    assert without_expiration.is_valid() is True
    assert future_expiration.is_valid() is True
    assert past_expiration.is_valid() is False


def test_access_key_service_rejects_wrong_key_EXT() -> None:
    """Verifica is_access_key_valid quando la chiave fornita non combacia.

    Il service helper controlla prima esistenza/scadenza e poi uguaglianza del token; il
    test usa expiration None per isolare il ramo wrong-key dalla logica temporale.
    """
    # arrange - record AccessKey in memoria valido ma con token diverso da quello fornito.
    key_record = AccessKey(
        key="expected-service-key-ext",
        creation=datetime.utcnow(),
        expiration=None,
        user_id=1,
    )

    # act/assert - una password BasicAuth errata deve essere rifiutata.
    assert is_access_key_valid(key_record, "wrong-service-key-ext") is False


def test_access_key_service_handles_missing_and_expired_records_EXT() -> None:
    """Verifica rifiuto di record assente e record scaduto nel service helper.

    Il service usa datetime.now(timezone.utc), quindi le expiration costruite qui sono
    timezone-aware per rappresentare correttamente il contratto del livello service.
    """
    # arrange - record scaduto con datetime aware coerente con il service.
    expired_key = AccessKey(
        key="expired-service-key-ext",
        creation=datetime.now(timezone.utc) - timedelta(hours=2),
        expiration=datetime.now(timezone.utc) - timedelta(hours=1),
        user_id=1,
    )

    # act/assert - assenza record e scadenza passata sono entrambe non valide.
    assert is_access_key_valid(None, "whatever") is False
    assert is_access_key_valid(expired_key, "expired-service-key-ext") is False