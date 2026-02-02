#!/usr/bin/python3

"""
Convert the hdf5 files of instantaneous and accumulated precipitation
from the radar composite over the Italian domain into grib2. 

Data source:     National Civil Protection Department ftp site

Maintainer:      Virginia Poli, Agenzia ItaliaMeteo/Arpae 
Creation date:   15.12.2025
Last change:     19.12.2025
Contact:         virginia.poli@agenziaitaliameteo.it/vpoli@arpae.it
"""

import argparse
import os
import sys
import warnings
from datetime import datetime, timedelta

import h5py
import numpy as np
import pyproj
from eccodes import (
    codes_get_double,
    codes_get_long,
    codes_grib_new_from_file,
    codes_grib_new_from_samples,
    codes_release,
    codes_set,
    codes_set_key_vals,
    codes_set_values,
    codes_write,
)
from osgeo import gdal, osr

warnings.filterwarnings("ignore")

# Constant missing values
rmiss_grib = 9999.0
imiss = 255

component_flag = 0  # int CONSTANT


def get_args():
    parser = argparse.ArgumentParser(
        description="Script for converting HDF5 files of instantaneous and accumulated precipitation into grib2 format.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-i",
        "--input_file",
        dest="inputfile",
        required=True,
        help="Input file, required",
    )
    parser.add_argument(
        "-t",
        "--grib_template",
        dest="gribtemplate",
        required=False,
        help="Grib template  for output, optional",
    )
    parser.add_argument(
        "-o",
        "--output_file",
        dest="outputfile",
        required=False,
        help="Output file, optional",
    )
    args = parser.parse_args()

    return args


def get_objects(name, obj):
    # Function to read lats/lons from HDF5
    if "where" in name:
        return obj


def radar_hdf52grib(filein, gribtemplate=None, fileout=None):
    os.environ["PROJ_LIB"] = "/usr/share/proj"
    from osgeo import gdal, osr

    if gribtemplate is not None:
        gaid_template = codes_grib_new_from_file(open(gribtemplate))
        gp = codes_get_double(gaid_template, "generatingProcessIdentifier")
        centre = codes_get_long(gaid_template, "centre")
    else:
        gaid_template = codes_grib_new_from_samples("regular_ll_sfc_grib2")
        gp = 1  # boh?
        centre = 80

    try:
        # Read attributes associated to product to write the correct grib2:
        # - product (RR)
        # - prodpar (only for accumulated precipitation: hours of accumulation)
        # - quantity (instantaneous: RATE or accumulated precipitation: ACRR)
        # - date/time

        with h5py.File(filein, "r") as f:
            product = f["/dataset1/what"].attrs["product"].decode("utf-8")
            quantity = f["/dataset1/data1/what"].attrs["quantity"].decode("utf-8")
            if quantity == "ACRR":
                prodpar = f["/dataset1/what"].attrs["prodpar"]

            datefile = f["/what"].attrs["date"].decode("utf-8")
            timefile = f["/what"].attrs["time"].decode("utf-8")
            print("File date/time:", datefile, timefile, file=sys.stderr)

        # -----------------------------------------------------------------------------------
        # Extraction of the complete dataset from hdf file
        ds = gdal.Open(f'HDF5:"{filein}"://dataset1/data1/data')
        data_arr = ds.GetVirtualMemArray()

        # Extraction of projection parameters
        prj = ds.GetProjection()
        ds_converter = osr.SpatialReference()  # makes an empty spatial ref object
        ds_converter.ImportFromWkt(
            prj
        )  # populates the spatial ref object with our WKT SRS
        ds_forPyProj = ds_converter.ExportToProj4()
        # print( "Input proj = ",ds_forPyProj )

        # Input/output options for projection
        # (in this case regular lat/lon)
        radarDPC_warp_options = {
            "dstSRS": "EPSG:4326",  # destination EPSG
            "srcSRS": ds_forPyProj,  # source EPSG
            "format": "VRT",
            "width": data_arr.shape[1],
            "height": data_arr.shape[0],
            "copyMetadata": True,
            "srcNodata": -9999.0,
            "dstNodata": 9999.0,
            "resampleAlg": "near",
        }

        data = gdal.Warp("", ds, options=gdal.WarpOptions(**radarDPC_warp_options))

        # -----------------------------------------------------------------------------------
        # Extraction of geographical informations from reprojected dataset
        geotransform = data.GetGeoTransform()
        lonFirst = geotransform[0]
        latLast = geotransform[3]
        mesh_dx = geotransform[1]
        mesh_dy = geotransform[5]

        rastr = data.ReadAsArray()
        # Missing extremes calculation
        lonLast = lonFirst + (rastr.shape[1] * mesh_dx)
        latFirst = latLast + (rastr.shape[0] * mesh_dy)
        # print( lonFirst, lonLast )
        # print( latFirst, latLast )

        # -----------------------------------------------------------------------------------
        # Conversion of the unit of measurement as coded in grib format
        # where tha data is not missing
        # RATE: kg m-2 s-1
        # ACRR: kg m-2
        mask = rastr != 9999.0
        prate = rastr.copy()
        if quantity == "RATE":
            prate[mask] = prate[mask] / 3600.0
        elif quantity == "ACRR":
            prate[mask] = prate[mask]
        else:
            print("Unsupported data type, exit", file=sys.stderr)
            exit()

        # =======================================================================
        # Output GRIB
        # =======================================================================

        if fileout is None:
            if quantity == "RATE":
                fileout = f"radar_SRI_{datefile}{timefile[0:4]}.grib2"
            elif quantity == "ACRR":
                fileout = "radar_SRT-{}_{}{}.grib2".format(
                    int(prodpar), datefile, timefile[0:4]
                )

        print(f"Output file = {fileout}", file=sys.stderr)
        fout = open(fileout, "wb")

        # Grid definition and increment format
        iincr = abs(mesh_dx)
        jincr = abs(mesh_dy)

        # Precipitation keys
        pc = 15  # parameterCategory
        pn = 17  # parameterNumber
        discipline = 0  # discipline

        key_map_grib = {
            "generatingProcessIdentifier": gp,
            "centre": centre,
            "missingValue": rmiss_grib,
            "packingType": "grid_simple",
            "bitmapPresent": 1,
            "resolutionAndComponentFlags": 0,
            "topLevel": 0,  # l1
            "bottomLevel": imiss,  # l2
            "iDirectionIncrement": "MISSING",
            "jDirectionIncrement": "MISSING",
            "iDirectionIncrementInDegrees": iincr,
            "jDirectionIncrementInDegrees": jincr,
            "significanceOfReferenceTime": 3,  # VIRGI
            "productionStatusOfProcessedData": 0,  # VIRGI
            "typeOfProcessedData": 0,  # [Analysis products]
            # Emission date/time
            "year": datefile[0:4],
            "month": datefile[4:6],
            "day": datefile[6:8],
            "hour": timefile[0:2],
            "minute": timefile[2:4],
            "parameterCategory": pc,
            "parameterNumber": pn,
            "discipline": discipline,
            "shapeOfTheEarth": 1,
            "scaleFactorOfRadiusOfSphericalEarth": 2,
            "scaledValueOfRadiusOfSphericalEarth": 637099700,
            "productDefinitionTemplateNumber": 0,
            "typeOfFirstFixedSurface": 1,
            "scaleFactorOfFirstFixedSurface": 0,
            "scaledValueOfFirstFixedSurface": 0,
        }

        # Chiave per la cumulata
        if quantity == "ACRR":
            # Template with time statistical values
            codes_set(gaid_template, "productDefinitionTemplateNumber", 8)
            # Accumulation
            codes_set(gaid_template, "typeOfStatisticalProcessing", 1)
            # Time interval
            codes_set(gaid_template, "lengthOfTimeRange", int(prodpar))
            codes_set(gaid_template, "indicatorOfUnitOfTimeRange", 1)  # ore

            # step finale
            codes_set(gaid_template, "endStep", int(prodpar))

        codes_set_key_vals(gaid_template, key_map_grib)

        codes_set_key_vals(
            gaid_template,
            {
                "typeOfGrid": "regular_ll",
                "Ni": rastr.shape[1],  # nx
                "Nj": rastr.shape[0],  # ny
                "longitudeOfFirstGridPointInDegrees": lonFirst,  # xmin (loFirst)
                "longitudeOfLastGridPointInDegrees": lonLast,  # xmax (loLast)
                "latitudeOfFirstGridPointInDegrees": latFirst,  # ymin (laFirst)
                "latitudeOfLastGridPointInDegrees": latLast,  # ymax (laLast)
                "scanningMode": 64,
                "uvRelativeToGrid": component_flag,
            },
        )

        pr_mm = np.flip(prate, 0)
        codes_set_values(gaid_template, pr_mm.flatten())

        codes_write(gaid_template, fout)
        codes_release(gaid_template)
        fout.close()
        return fileout

    except OSError:
        print(f"Cannot open {filein}", file=sys.stderr)
        print("Missing file", file=sys.stderr)


def main():
    args = get_args()

    inputfile = args.inputfile

    try:
        fileout = radar_hdf52grib(inputfile, args.gribtemplate, args.outputfile)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(100)
    # check if fileout exists
    if not os.path.exists(fileout):
        print("Output file does not exist", file=sys.stderr)
        sys.exit(101)
    print(fileout)


if __name__ == "__main__":
    main()
