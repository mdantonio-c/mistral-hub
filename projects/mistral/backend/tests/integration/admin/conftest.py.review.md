# Review — `admin/conftest.py` (fixture di dominio)

## Scopo

Rendere disponibile `admin_headers_EXT` ai quattro moduli admin tramite la discovery
automatica di pytest, senza import della fixture nei test.

## Comportamento

- La fixture ha scope `function` (default), non e' `autouse` ed e' visibile solo nel
  sottoalbero `integration/admin`.
- Il login resta `BaseTests().do_login(client, None, None)`: usa l'admin di default,
  senza creare utenti o ruoli alternativi.
- `assert headers is not None` preserva il controllo sul risultato del login.
- I test continuano a richiedere `admin_headers_EXT` come parametro; non dipendono
  piu' da import che un auto-fix potrebbe considerare inutilizzati.
- Payload builder, creazione di record sintetici e cleanup rimangono in
  [support_EXT.py](support_EXT.py), descritti nella [review del supporto](support_EXT.py.review.md).

## Limite invariato

L'identita' dell'admin e' condivisa con la suite: lo scope per singolo test non crea
un account isolato. I test isolano i record sintetici tramite nomi uuid e cleanup.
