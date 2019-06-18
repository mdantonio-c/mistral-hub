from utilities.globals import mem
from restapi.swagger import BeSwagger
from bravado_core.validate import validate_object


def validate_data_extraction(criteria):
    validate_object(mem.customizer._validated_spec, DataExtraction, criteria)

#swag = BeSwagger(mem.customizer._endpoints, mem.customizer)
#spec = swag._customizer._validated_spec

DataExtraction = mem.customizer._definitions['definitions']['DataExtraction']