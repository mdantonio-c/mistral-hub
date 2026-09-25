# Review — `helpers/templates/endpoint_template.py` (template guida, non eseguibile)

> File di review per il template strutturale dei test. Non viene collezionato da pytest.

## 1. Informazioni generali

- **Percorso**: [projects/mistral/backend/tests/helpers/templates/endpoint_template.py](projects/mistral/backend/tests/helpers/templates/endpoint_template.py)
- **Scopo**: riferimento strutturale (arrange/act/assert) per chi scrive o rifattorizza test. **Non è un test reale**.
- **Tipologia**: documentazione/scaffold (non eseguibile come test: pur contenendo metodi `test_...`, non fa asserzioni reali — i corpi sono `pass`).

## 2. Elementi definiti

- `pytestmark = [pytest.mark.integration, pytest.mark.example_area]` — marker d'esempio (`example_area` **non** è registrato in [tests/conftest.py](projects/mistral/backend/tests/conftest.py)).
- `class TestExampleArea` con `test_happy_path_returns_expected_status` e `test_invalid_input_returns_error`: scheletri con `pass`, solo a scopo illustrativo.
- Commenti finali con le "Regole di adozione" della suite.

## 3. Comportamenti nascosti

- **Non è in un path `test_*.py`**, quindi pytest non lo raccoglie: i metodi `test_...` non vengono eseguiti.
- **Usa un marker non registrato** (`example_area`): se il file venisse mai raccolto, emetterebbe warning sui marker sconosciuti.

## 4. Checklist di revisione

- [ ] Confermare che il file resti fuori dalla collection di pytest (nome cartella/file).
- [ ] Verificare che le linee guida qui descritte coincidano con le convenzioni effettive della suite.

## 5. Possibili criticità

- **Codice "test-like" non eseguito**: i metodi `test_...` con `pass` potrebbero trarre in inganno un lettore frettoloso facendo credere che esista copertura "example_area".
