# EXTENSION TRACEABILITY: questo modulo e stato aggiunto dal piano di estensione
# della copertura backend, fase quick wins, per coprire parser puri del service
# DB-All.e senza toccare i test legacy o i flussi observed runtime-sensitive.
# EXTENSION SCOPE: i test verificano trasformazioni di query e filtri in strutture
# Python usate dal backend: non aprono database DB-All.e, non leggono summary JSON e non
# interrogano dataset reali.
# EXTENSION DATA WINDOW: nessun dato meteorologico reale viene usato. Le date sono
# sintetiche e servono solo a verificare parsing e propagazione dei campi datetime.
# EXTENSION RUNTIME: i monkeypatch sostituiscono soltanto la mappa dataset -> network e
# il DSN aggregazioni, perche questi contratti dipendono da configurazione runtime ma la
# logica sotto test resta locale e deterministica.
# EXTENSION CLEANUP: non vengono creati file o record DB; i monkeypatch sono ripristinati
# automaticamente da pytest a fine test.

import datetime as dt

import pytest

import mistral.services.dballe as dballe_service
from mistral.exceptions import InvalidFiltersException
from mistral.services.dballe import BeDballe


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class TestDballeQueryParsing:
    """Verify deterministic DB-All.e query parsing helpers."""

    def test_from_query_to_dic_parses_reftime_and_multi_value_filters(self):
        """A textual query is converted to the dictionary shape used downstream."""
        # arrange
        # La stringa e interamente sintetica ma riproduce la grammatica supportata dal
        # parser: reftime con bounds, filtri multi-valore e license scalar.
        query = (
            "reftime: >=2020-02-01 01:00,<=2020-02-04 15:13;"
            "level:1,0,0,0 or 103,2000,0,0;"
            "product:B11001 or B13011;"
            "timerange:0,0,3600 or 1,0,900;"
            "network:fidupo or agrmet;"
            "license:public"
        )

        # act
        parsed_query = BeDballe.from_query_to_dic(query)

        # assert
        assert parsed_query["datetimemin"] == dt.datetime(2020, 2, 1, 1, 0)
        assert parsed_query["datetimemax"] == dt.datetime(2020, 2, 4, 15, 13)
        assert parsed_query["level"] == ["1,0,0,0", "103,2000,0,0"]
        assert parsed_query["product"] == ["B11001", "B13011"]
        assert parsed_query["timerange"] == ["0,0,3600", "1,0,900"]
        assert parsed_query["network"] == ["fidupo", "agrmet"]
        assert parsed_query["license"] == "public"

    def test_from_filters_to_lists_maps_frontend_codes_to_dballe_fields(self):
        """Filter dictionaries become ordered DB-All.e fields and value lists."""
        # arrange
        # Ogni filtro usa il formato `code` prodotto dagli endpoint. Level e timerange
        # esercitano la conversione a tuple numeriche, mentre network/product restano
        # stringhe. Il campo `ignored` documenta che i filtri non ammessi vengono saltati.
        filters = {
            "level": [{"code": "1,0,0,0"}],
            "network": [{"code": "agrmet"}],
            "product": [{"code": "B13011"}],
            "timerange": [{"code": "1,0,3600"}],
            "ignored": [{"code": "unused"}],
        }

        # act
        fields, queries = BeDballe.from_filters_to_lists(filters)

        # assert
        assert fields == ["level", "rep_memo", "var", "trange"]
        assert queries == [[(1, None, None, None)], ["agrmet"], ["B13011"], [(1, 0, 3600)]]

    def test_from_query_to_lists_maps_query_dictionary_to_dballe_lists(self):
        """Already parsed query dictionaries keep ordering and tuple conversions."""
        # arrange
        # La query evita qualsiasi accesso a summary DB-All.e: il test protegge solo la
        # normalizzazione dei nomi campo e dei valori compositi level/timerange.
        datetimemin = dt.datetime(2020, 4, 6, 0, 0)
        query = {
            "network": ["agrmet", "fidupo"],
            "timerange": ["1,0,3600"],
            "level": ["1,0,0,0"],
            "datetimemin": datetimemin,
        }

        # act
        fields, queries = BeDballe.from_query_to_lists(query)

        # assert
        assert fields == ["rep_memo", "trange", "level", "datetimemin"]
        assert queries == [
            ["agrmet", "fidupo"],
            [(1, 0, 3600)],
            [(1, None, None, None)],
            [datetimemin],
        ]

    def test_parse_query_for_maps_translates_api_names_to_dballe_names(self):
        """Map query parameters are adapted to DB-All.e cursor field names."""
        # arrange
        # Lo scenario miscela filtri da tradurre e campi gia ammessi. Non viene creato un
        # explorer DB-All.e reale: il contratto e il dizionario risultante.
        datetimemin = dt.datetime(2020, 4, 6, 0, 0)
        query = {
            "network": ["agrmet"],
            "product": ["B13011"],
            "timerange": ["1,0,3600"],
            "level": ["1,0,0,0"],
            "datetimemin": datetimemin,
            "latmin": 44.0,
        }

        # act
        parsed_query = BeDballe.parse_query_for_maps(query)

        # assert
        assert parsed_query == {
            "rep_memo": "agrmet",
            "var": "B13011",
            "trange": (1, 0, 3600),
            "level": (1, None, None, None),
            "datetimemin": datetimemin,
            "latmin": 44.0,
        }

    def test_parse_query_for_data_extraction_uses_dataset_networks_and_reftime(
        self, monkeypatch
    ):
        """Observed extraction query parsing uses a fake dataset-network map."""
        # arrange
        # Il monkeypatch sostituisce la lettura della configurazione Arkimet con una
        # mappa locale. Questo rende il test portabile tra locale e CI e copre il ramo
        # positivo senza affidarsi a dataset reali.
        def fake_get_observed_dataset_params(dataset):
            return {"dataset-a": ["agrmet", "urbane"]}[dataset]

        monkeypatch.setattr(
            dballe_service.arki_service,
            "get_observed_dataset_params",
            fake_get_observed_dataset_params,
        )
        filters = {
            "network": [{"code": "agrmet"}],
            "product": [{"code": "B13011"}],
        }
        reftime = {
            "from": "2020-04-06T00:00:00Z",
            "to": "2020-04-06T02:00:00Z",
        }

        # act
        fields, queries = BeDballe.parse_query_for_data_extraction(
            ["dataset-a"], filters=filters, reftime=reftime
        )

        # assert
        assert fields == ["rep_memo", "var", "datetimemin", "datetimemax"]
        assert queries == [
            ["agrmet"],
            ["B13011"],
            [dt.datetime(2020, 4, 6, 0, 0)],
            [dt.datetime(2020, 4, 6, 2, 0)],
        ]

    def test_parse_query_for_data_extraction_rejects_network_outside_dataset(
        self, monkeypatch
    ):
        """A requested network not declared by the dataset fake is rejected."""
        # arrange
        # Il diniego e costruito in modo controllato e portabile: il dataset fake espone
        # solo `agrmet`, mentre il filtro chiede una rete diversa.
        def fake_get_observed_dataset_params(dataset):
            return {"dataset-a": ["agrmet"]}[dataset]

        monkeypatch.setattr(
            dballe_service.arki_service,
            "get_observed_dataset_params",
            fake_get_observed_dataset_params,
        )
        filters = {"network": [{"code": "outside"}]}

        # act / assert
        with pytest.raises(InvalidFiltersException):
            BeDballe.parse_query_for_data_extraction(["dataset-a"], filters=filters)

    def test_is_query_for_pluvio_aggregations_selects_configured_dsn(
        self, monkeypatch
    ):
        """Hourly B13011 timeranges are routed to the configured aggregation DSN."""
        # arrange
        # Il DSN reale dipende dall'ambiente, quindi viene sostituito con un valore
        # locale. La logica verificata resta la selezione sul prodotto e sul p2 orario.
        monkeypatch.setattr(BeDballe, "AGGREGATIONS_DSN", "dballe-aggregations")
        aggregation_query = {"product": ["B13011"], "timerange": ["1,0,3600"]}
        normal_query = {"product": ["B11001"], "timerange": ["1,0,3600"]}

        # act
        aggregation_dsn = BeDballe.is_query_for_pluvio_aggregations(aggregation_query)
        normal_dsn = BeDballe.is_query_for_pluvio_aggregations(normal_query)

        # assert
        assert aggregation_dsn == "dballe-aggregations"
        assert normal_dsn is None

    def test_get_queries_and_dsn_list_with_itertools_expands_filter_combinations(
        self, monkeypatch
    ):
        """Multiple filter values are expanded into independent query dictionaries."""
        # arrange
        # La query contiene due dimensioni multi-valore. Il DSN fake consente di
        # verificare che solo la combinazione pluviometrica oraria venga marcata per le
        # aggregazioni, senza aprire connessioni DB-All.e.
        monkeypatch.setattr(BeDballe, "AGGREGATIONS_DSN", "dballe-aggregations")
        original_query = {
            "network": ["agrmet"],
            "product": ["B13011", "B11001"],
            "timerange": ["1,0,3600", "1,0,1800"],
        }

        # act
        query_and_dsn_list = BeDballe.get_queries_and_dsn_list_with_itertools(
            original_query
        )

        # assert
        assert query_and_dsn_list == [
            {
                "query": {
                    "network": ["agrmet"],
                    "product": ["B13011"],
                    "timerange": ["1,0,3600"],
                },
                "aggregations_dsn": "dballe-aggregations",
            },
            {
                "query": {
                    "network": ["agrmet"],
                    "product": ["B13011"],
                    "timerange": ["1,0,1800"],
                },
                "aggregations_dsn": None,
            },
            {
                "query": {
                    "network": ["agrmet"],
                    "product": ["B11001"],
                    "timerange": ["1,0,3600"],
                },
                "aggregations_dsn": None,
            },
            {
                "query": {
                    "network": ["agrmet"],
                    "product": ["B11001"],
                    "timerange": ["1,0,1800"],
                },
                "aggregations_dsn": None,
            },
        ]