# EXTENSION TRACEABILITY: questo modulo e stato aggiunto dal piano di estensione
# della copertura backend, fase quick wins, per coprire helper puri dei tool di
# post-processing senza ripetere i flussi runtime gia coperti in `integration/postprocessing`.
# EXTENSION SCOPE: i test verificano mapping di subtype e validazioni di path/template;
# non lanciano `vg6d_transform`, `vg6d_getpoint`, `v7d_transform` o altri binari meteo.
# EXTENSION DATA WINDOW: nessun dataset reale viene usato. I file creati sono placeholder
# temporanei sufficienti per i controlli di esistenza, suffisso e bundle shapefile.
# EXTENSION RUNTIME: `tmp_path` e dizionari locali bastano perche le funzioni sotto test
# falliscono o mutano input prima di qualsiasi subprocess reale.
# EXTENSION CLEANUP: pytest rimuove le directory temporanee; il test del bundle shapefile
# corrotto verifica anche la cancellazione intenzionale della cartella da parte dell'helper.

import pytest
from restapi.exceptions import BadRequest

from mistral.tools import grid_cropping, grid_interpolation, spare_point_interpol


pytestmark = [pytest.mark.integration, pytest.mark.deterministic]


class TestToolHelpers:
    """Verify deterministic helper behavior for spatial post-processing tools."""

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
        """Grid interpolation subtype values mutate params to the expected mode."""
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
        """Spare-point subtype values choose point interpolation modes."""
        # arrange
        # Come sopra, restiamo sul dizionario locale per evitare subprocess e per
        # documentare la differenza fra `boxinter` e `polyinter`.
        params = {"sub_type": sub_type}

        # act
        spare_point_interpol.get_trans_type(params)

        # assert
        assert params["trans_type"] == expected_trans_type

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
        """The UI bbox subtype is translated to the vg6d coordbb subtype."""
        # arrange
        # I valori sono stringhe pure: non serve alcun input GRIB per verificare la
        # normalizzazione che precede il comando esterno.

        # act
        formatted_sub_type = grid_cropping.format_sub_type(sub_type)

        # assert
        assert formatted_sub_type == expected_sub_type

    def test_check_template_filepath_existing_file_returns_none(self, tmp_path):
        """An existing template path is accepted without invoking toolchain code."""
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
        """A missing interpolation template is rejected before subprocess setup."""
        # arrange
        # Il path non viene creato apposta: il ramo di validazione deve fermare la
        # richiesta prima che il tool meteo possa essere composto.
        missing_template_file = tmp_path / "missing-template.grib"

        # act / assert
        with pytest.raises(BadRequest):
            grid_interpolation.check_template_filepath(missing_template_file)

    def test_check_coord_filepath_missing_file_raises_bad_request(self, tmp_path):
        """A missing spare-point coordinate file is rejected immediately."""
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
        """A suffix different from the declared format is rejected."""
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
        """A complete shapefile placeholder bundle passes preflight validation."""
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

    def test_check_coord_filepath_corrupt_shapefile_bundle_removes_folder(
        self, tmp_path
    ):
        """An incomplete shapefile bundle is rejected and its folder is deleted."""
        # arrange
        # Creiamo soltanto il file .shp: mancano .shx e .dbf. Questo esercita il cleanup
        # intenzionale dell'helper senza usare shapefile reali o tool meteo.
        bundle_dir = tmp_path / "corrupt-bundle"
        bundle_dir.mkdir()
        coord_file = bundle_dir / "points.shp"
        coord_file.write_text("placeholder", encoding="utf-8")
        params = {"coord_filepath": str(coord_file), "file_format": "shp"}

        # act / assert
        with pytest.raises(BadRequest):
            spare_point_interpol.check_coord_filepath(params)
        assert not bundle_dir.exists()