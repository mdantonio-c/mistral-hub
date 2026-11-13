# Test degli helper puri dei tool di post-processing (mistral.tools), senza ripetere
# i flussi runtime gia coperti in `integration/postprocessing`.
# Ambito: i test verificano mapping di subtype e validazioni di path/template;
# non lanciano `vg6d_transform`, `vg6d_getpoint`, `v7d_transform` o altri binari meteo.
# Finestra dati: nessun dataset reale viene usato. I file creati sono placeholder
# temporanei sufficienti per i controlli di esistenza, suffisso e bundle shapefile.
# Runtime: `tmp_path` e dizionari locali bastano perche le funzioni sotto test
# falliscono o mutano input prima di qualsiasi subprocess reale.
# Cleanup: pytest rimuove le directory temporanee; il test del bundle shapefile
# corrotto verifica che l'helper non cancelli nulla nella cartella condivisa.

import pytest
from restapi.exceptions import BadRequest

from mistral.tools import grid_cropping, grid_interpolation, spare_point_interpol


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class TestToolHelpers:
    """Verifica gli helper deterministici dei tool di post-processing spaziale.

    Moduli esercitati: `grid_interpolation`, `spare_point_interpol` e `grid_cropping`
    di mistral.tools.
    """

    @pytest.mark.parametrize(
        ("sub_type", "expected_trans_type"),
        [
            ("near", "inter"),
            ("bilin", "inter"),
            ("average", "boxinter"),
            ("min", "boxinter"),
            ("max", "boxinter"),
        ],
    )
    def test_grid_interpolation_get_trans_type_maps_known_subtypes(
        self, sub_type, expected_trans_type
    ):
        """I sub_type dell'interpolazione su griglia impostano il trans_type atteso.

        Funzione esercitata: `grid_interpolation.get_trans_type`.
        """
        # arrange
        # Il dizionario replica il payload gia validato dagli endpoint. Il tool reale non
        # viene eseguito: il contratto qui e solo la mutazione `trans_type`.
        params = {"sub_type": sub_type}

        # act
        grid_interpolation.get_trans_type(params)

        # assert
        assert params["trans_type"] == expected_trans_type

    @pytest.mark.parametrize(
        ("sub_type", "expected_trans_type"),
        [
            ("near", "inter"),
            ("bilin", "inter"),
            ("average", "polyinter"),
            ("min", "polyinter"),
            ("max", "polyinter"),
        ],
    )
    def test_spare_point_get_trans_type_maps_known_subtypes(
        self, sub_type, expected_trans_type
    ):
        """I sub_type spare-point scelgono la modalita di interpolazione su punti.

        Funzione esercitata: `spare_point_interpol.get_trans_type`.
        """
        # arrange
        # Come sopra, restiamo sul dizionario locale per evitare subprocess e per
        # documentare la differenza fra `boxinter` e `polyinter`.
        params = {"sub_type": sub_type}

        # act
        spare_point_interpol.get_trans_type(params)

        # assert
        assert params["trans_type"] == expected_trans_type

    @pytest.mark.parametrize(
        "helper",
        [grid_interpolation.get_trans_type, spare_point_interpol.get_trans_type],
        ids=["grid_interpolation", "spare_point_interpol"],
    )
    def test_get_trans_type_rejects_unknown_sub_type(self, helper):
        """Un sub_type sconosciuto e rifiutato e non imposta alcun trans_type.

        Funzioni esercitate: `grid_interpolation.get_trans_type` e
        `spare_point_interpol.get_trans_type`. Senza trans_type il comando esterno
        partirebbe con `--trans-type=None`.
        """
        # arrange
        params = {"sub_type": "UNKNOWN"}

        # act / assert
        with pytest.raises(BadRequest, match="Unknown interpolation sub_type: UNKNOWN"):
            helper(params)
        assert "trans_type" not in params

    @pytest.mark.parametrize(
        ("sub_type", "expected_sub_type"),
        [
            ("bbox", "coordbb"),
            ("coord", "coord"),
        ],
    )
    def test_grid_cropping_format_sub_type_normalizes_bbox_only(
        self, sub_type, expected_sub_type
    ):
        """Il sub_type bbox della UI viene tradotto nel sub_type coordbb di vg6d.

        Funzione esercitata: `grid_cropping.format_sub_type`.
        """
        # arrange
        # I valori sono stringhe pure: non serve alcun input GRIB per verificare la
        # normalizzazione che precede il comando esterno.

        # act
        formatted_sub_type = grid_cropping.format_sub_type(sub_type)

        # assert
        assert formatted_sub_type == expected_sub_type

    def test_check_template_filepath_existing_file_returns_none(self, tmp_path):
        """Un template esistente viene accettato senza invocare la toolchain meteo.

        Funzione esercitata: `grid_interpolation.check_template_filepath`.
        """
        # arrange
        # Creiamo un placeholder temporaneo: la funzione controlla solo l'esistenza del
        # path, quindi un file testuale basta e mantiene il test deterministico.
        template_file = tmp_path / "template.grib"
        template_file.write_text("synthetic-template", encoding="utf-8")

        # act
        result = grid_interpolation.check_template_filepath(template_file)

        # assert
        assert result is None

    def test_check_template_filepath_missing_file_raises_bad_request(self, tmp_path):
        """Un template mancante e rifiutato con BadRequest prima del subprocess.

        Funzione esercitata: `grid_interpolation.check_template_filepath`.
        """
        # arrange
        # Il path non viene creato apposta: il ramo di validazione deve fermare la
        # richiesta prima che il tool meteo possa essere composto.
        missing_template_file = tmp_path / "missing-template.grib"

        # act / assert
        with pytest.raises(BadRequest):
            grid_interpolation.check_template_filepath(missing_template_file)

    def test_check_coord_filepath_missing_file_raises_bad_request(self, tmp_path):
        """Un file di coordinate spare-point mancante e rifiutato subito.

        Funzione esercitata: `spare_point_interpol.check_coord_filepath`.
        """
        # arrange
        # Nessun file viene creato: il test copre il primo guard clause dell'helper.
        params = {
            "coord_filepath": str(tmp_path / "missing.shp"),
            "file_format": "shp",
        }

        # act / assert
        with pytest.raises(BadRequest):
            spare_point_interpol.check_coord_filepath(params)

    def test_check_coord_filepath_wrong_format_raises_bad_request(self, tmp_path):
        """Un suffisso diverso dal formato dichiarato viene rifiutato.

        Funzione esercitata: `spare_point_interpol.check_coord_filepath`.
        """
        # arrange
        # Il file esiste, quindi il test attraversa il ramo successivo e verifica che il
        # parametro `file_format` sia coerente con il suffisso reale.
        coord_file = tmp_path / "points.csv"
        coord_file.write_text("lat,lon\n44,11\n", encoding="utf-8")
        params = {"coord_filepath": str(coord_file), "file_format": "shp"}

        # act / assert
        with pytest.raises(BadRequest):
            spare_point_interpol.check_coord_filepath(params)

    def test_check_coord_filepath_valid_shapefile_bundle_returns_none(self, tmp_path):
        """Un bundle shapefile placeholder completo supera la validazione preliminare.

        Funzione esercitata: `spare_point_interpol.check_coord_filepath`.
        """
        # arrange
        # L'helper non interpreta il contenuto shapefile; controlla solo la presenza di
        # .shp, .shx e .dbf. Placeholder vuoti sono quindi sufficienti e non richiedono
        # librerie geospaziali o dati reali.
        bundle_dir = tmp_path / "valid-bundle"
        bundle_dir.mkdir()
        coord_file = bundle_dir / "points.shp"
        coord_file.write_text("placeholder", encoding="utf-8")
        coord_file.with_suffix(".shx").write_text("placeholder", encoding="utf-8")
        coord_file.with_suffix(".dbf").write_text("placeholder", encoding="utf-8")
        params = {"coord_filepath": str(coord_file), "file_format": "shp"}

        # act
        result = spare_point_interpol.check_coord_filepath(params)

        # assert
        assert result is None

    def test_check_coord_filepath_corrupt_shapefile_bundle_keeps_other_files(
        self, tmp_path
    ):
        """Un bundle shapefile incompleto viene rifiutato senza cancellare nulla.

        La cartella degli shapefile e condivisa da tutti i template dell'utente: un
        altro bundle completo e un file sentinella devono restare intatti.
        Funzione esercitata: `spare_point_interpol.check_coord_filepath`.
        """
        # arrange
        # Creiamo soltanto il file .shp del bundle rotto (mancano .shx e .dbf), un
        # secondo bundle completo e un file sentinella nella stessa cartella.
        bundle_dir = tmp_path / "shared-shp-folder"
        bundle_dir.mkdir()
        coord_file = bundle_dir / "broken.shp"
        coord_file.write_text("placeholder", encoding="utf-8")
        other_bundle = [
            bundle_dir / f"valid{suffix}" for suffix in (".shp", ".shx", ".dbf")
        ]
        for path in other_bundle:
            path.write_text("placeholder", encoding="utf-8")
        sentinel = bundle_dir / "sentinel.txt"
        sentinel.write_text("sentinel", encoding="utf-8")
        files_before = {
            p.name: p.read_text(encoding="utf-8") for p in bundle_dir.iterdir()
        }
        params = {"coord_filepath": str(coord_file), "file_format": "shp"}

        # act / assert
        with pytest.raises(BadRequest, match="corrupted"):
            spare_point_interpol.check_coord_filepath(params)
        files_after = {
            p.name: p.read_text(encoding="utf-8") for p in bundle_dir.iterdir()
        }
        assert files_after == files_before
