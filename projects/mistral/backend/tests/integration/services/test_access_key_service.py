# Test deterministici di AccessKey.generate, AccessKey.is_valid (models/sqlalchemy.py)
# e mistral.services.access_key_service.is_access_key_valid.
# Ambito: verifica scadenza default/null, validita con scadenza assente/futura/passata/
# uguale a now (stessa regola per modello e service, orologio fisso), generazione in UTC
# con fuso, round-trip PostgreSQL e rifiuto di una chiave diversa da quella salvata.
# Finestra dati: nessun dataset reale; le AccessKey sono istanze in memoria, tranne nel
# round-trip, che salva una chiave per un utente temporaneo.
# Runtime fake: non servono request Flask o BasicAuth reale; il service helper testato
# accetta direttamente il record AccessKey e la chiave fornita.
# Cleanup: la chiave e l'utente del round-trip sono rimossi da cleanup_registry.

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import mistral.models.sqlalchemy as models_module
import pytest
from mistral.models.sqlalchemy import AccessKey
from mistral.services.access_key_service import is_access_key_valid
from mistral.tests.helpers.auth import (
    create_authenticated_test_user,
    register_test_user_cleanup,
)
from restapi.connectors import sqlalchemy
from restapi.tests import BaseTests, FlaskClient

FIXED_NOW = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)


class _FixedNowDateTime(datetime):
    """Orologio del modulo dei modelli fermo a FIXED_NOW."""

    @classmethod
    def now(cls, tz=None):
        return FIXED_NOW if tz is None else FIXED_NOW.astimezone(tz)


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


def test_access_key_generate_sets_default_and_null_expiration() -> None:
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

    # assert - lifetime None produce chiave senza scadenza ma conserva gli altri campi.
    assert no_expiration_key.user_id == 42
    assert no_expiration_key.key
    assert no_expiration_key.expiration is None
    assert no_expiration_key.scope == "read:arco"


def test_access_key_model_is_valid_handles_expiration_states() -> None:
    """Verifica AccessKey.is_valid per scadenza assente, futura e passata.

    Le datetime sono senza fuso, come in un'istanza non ancora salvata: il modello le
    considera UTC.
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

    # act/assert - il metodo del modello deve distinguere i tre stati senza DB.
    assert without_expiration.is_valid() is True
    assert future_expiration.is_valid() is True
    assert past_expiration.is_valid() is False


def test_access_key_service_rejects_wrong_key() -> None:
    """Verifica is_access_key_valid quando la chiave fornita non combacia.

    Il service helper controlla prima esistenza/scadenza e poi uguaglianza del token; il
    test usa expiration None cosi conta solo il confronto tra chiave salvata e fornita.
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


def test_access_key_service_handles_missing_and_expired_records() -> None:
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


def test_access_key_generate_uses_utc_with_timezone() -> None:
    """Verifica che creation ed expiration generate siano datetime UTC con fuso."""
    # act
    key = AccessKey.generate(user_id=42, lifetime_seconds=60)

    # assert
    assert key.creation.utcoffset() == timedelta(0)
    assert key.expiration.utcoffset() == timedelta(0)
    assert key.expiration - key.creation == timedelta(seconds=60)


@pytest.mark.parametrize(
    ("expiration", "expected"),
    [
        (None, True),
        (FIXED_NOW + timedelta(seconds=1), True),
        (FIXED_NOW, False),
        (FIXED_NOW - timedelta(seconds=1), False),
        (FIXED_NOW.astimezone(timezone(timedelta(hours=2))), False),
        (FIXED_NOW.replace(tzinfo=None) + timedelta(seconds=1), True),
    ],
    ids=["none", "future", "equal-to-now", "past", "now-other-timezone", "naive-utc"],
)
def test_access_key_model_and_service_share_the_expiration_rule(
    monkeypatch: pytest.MonkeyPatch,
    expiration: datetime | None,
    expected: bool,
) -> None:
    """Modello e service danno lo stesso esito, anche all'istante esatto di scadenza.

    La chiave e scaduta quando ``expiration <= now``; il service verifica anche il token.
    """
    # arrange
    monkeypatch.setattr(models_module, "datetime", _FixedNowDateTime)
    key = AccessKey(
        key="shared-rule-ext",
        creation=FIXED_NOW - timedelta(hours=1),
        expiration=expiration,
        user_id=1,
    )

    # act / assert
    assert key.is_valid() is expected
    assert is_access_key_valid(key, "shared-rule-ext") is expected
    assert is_access_key_valid(key, "wrong-shared-rule-ext") is False


def test_access_key_round_trip_on_postgresql(
    client: FlaskClient,
    cleanup_registry,
) -> None:
    """Una chiave riletta da PostgreSQL si valida senza TypeError su naive/aware.

    La colonna e ``timestamp with time zone``: il valore riletto ha il fuso.
    """
    # arrange
    base = BaseTests()
    db = sqlalchemy.get_instance()
    user = create_authenticated_test_user(base, client)
    register_test_user_cleanup(
        base,
        client,
        cleanup_registry,
        user_uuid=user.uuid,
        root_path=user.output_dir.parent,
    )
    key = AccessKey.generate(user_id=user.user_id, lifetime_seconds=3600)
    db.session.add(key)
    db.session.commit()
    key_id = key.id

    def delete_key() -> None:
        stored = db.AccessKey.query.get(key_id)
        if stored is not None:
            db.session.delete(stored)
            db.session.commit()

    cleanup_registry.add(delete_key)

    # act
    db.session.expire_all()
    stored_key = db.AccessKey.query.get(key_id)

    # assert
    assert stored_key.expiration.utcoffset() is not None
    assert stored_key.is_valid() is True
    assert is_access_key_valid(stored_key, stored_key.key) is True
    assert is_access_key_valid(stored_key, "wrong-round-trip-ext") is False
    stored_key.expiration = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.session.commit()
    db.session.expire_all()
    expired_key = db.AccessKey.query.get(key_id)
    assert expired_key.is_valid() is False
    assert is_access_key_valid(expired_key, expired_key.key) is False
