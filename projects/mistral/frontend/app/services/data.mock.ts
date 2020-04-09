import {DerivedVariables, StorageUsage, SummaryStats} from "./data.service";

export const MockStorageUsageResponse: StorageUsage = {
    "quota": 5368709120,
    "used": 2973844488
};

export const MockDerivedVariables: DerivedVariables[] = [
    {code: 'B11001', desc: 'Wind direction'},
    {code: 'B11002', desc: 'Wind speed'},
    {code: 'B11003', desc: 'U-component'},
    {code: 'B11004', desc: 'V-component'},
    {code: 'B12103', desc: 'Dew-point temperature'},
    {code: 'B12194', desc: 'Air density'},
    {code: 'B13001', desc: 'Specific humidity'},
    {code: 'B13003', desc: 'Relative humidity'},
    {code: 'B13205', desc: 'Snowfall (grid-scale + convective)'}
];

export const MockSummaryStatsResponse: SummaryStats = {
    "b": [2019, 9, 1, 12, 0, 0],
    "c": 637000,
    "e": [2019, 10, 9, 12, 0, 0],
    "s": 456198422400
};

export const MockGribTemplateResponse: RapydoBundle<any> = [
    {
        "files": [
            "/uploads/965812e7-b8d3-45d3-b05a-6ee31d347ea5/shp/it_100km.grib"
        ],
        "type": "grib"
    }
];

export const MockShapeTemplateResponse: RapydoBundle<any> = [
    {
        "files": [
            "/uploads/965812e7-b8d3-45d3-b05a-6ee31d347ea5/shp/it_100km.shp"
        ],
        "type": "shp"
    }
];

export const MockDatasetsResponse: any = [ 
    {
        "description": "COSMO a 2.2km sull'Italia, area completa",
        "id": "lm2.2",
        "name": "lm2.2"
    }, {
        "description": "COSMO a 5km sul Mediterraneo, area completa",
        "id": "lm5",
        "name": "lm5"
    }
];

export const MockFiltersResponse: any = {
    "items": {
        "area": [{
            "desc": "GRIB(Ni=576, Nj=701, latfirst=-8500000, latlast=5500000, latp=-47000000, lonfirst=-3800000, lonlast=7700000, lonp=10000000, rot=0, type=10)",
            "s": "GRIB",
            "t": "area",
            "va": {
                "Ni": 576,
                "Nj": 701,
                "latfirst": -8500000,
                "latlast": 5500000,
                "latp": -47000000,
                "lonfirst": -3800000,
                "lonlast": 7700000,
                "lonp": 10000000,
                "rot": 0,
                "type": 10
            }
        }, {
            "desc": "GRIB(Ni=576, Nj=701, latfirst=-8500000, latlast=5500000, latp=-47000000, lonfirst=-3790000, lonlast=7710000, lonp=10000000, rot=0, type=10)",
            "s": "GRIB",
            "t": "area",
            "va": {
                "Ni": 576,
                "Nj": 701,
                "latfirst": -8500000,
                "latlast": 5500000,
                "latp": -47000000,
                "lonfirst": -3790000,
                "lonlast": 7710000,
                "lonp": 10000000,
                "rot": 0,
                "type": 10
            }
        }, {
            "desc": "GRIB(Ni=576, Nj=701, latfirst=-8490000, latlast=5510000, latp=-47000000, lonfirst=-3800000, lonlast=7700000, lonp=10000000, rot=0, type=10)",
            "s": "GRIB",
            "t": "area",
            "va": {
                "Ni": 576,
                "Nj": 701,
                "latfirst": -8490000,
                "latlast": 5510000,
                "latp": -47000000,
                "lonfirst": -3800000,
                "lonlast": 7700000,
                "lonp": 10000000,
                "rot": 0,
                "type": 10
            }
        }],
        "level": [{
            "desc": "sfc Surface (of the Earth, which includes sea surface) 0 0",
            "lt": 1,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Cloud base level 0 0",
            "lt": 2,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Cloud top level 0 0",
            "lt": 3,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc 0 deg (C) isotherm level 0 0",
            "lt": 4,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Nominal top of atmosphere 0 0",
            "lt": 8,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Mean sea level 0 0 0 0",
            "lt": 102,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Fixed height above ground height in meters (2 octets) 2 0",
            "l1": 2,
            "lt": 105,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Fixed height above ground height in meters (2 octets) 10 0",
            "l1": 10,
            "lt": 105,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 1 0",
            "l1": 1,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 2 0",
            "l1": 2,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 3 0",
            "l1": 3,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 4 0",
            "l1": 4,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 5 0",
            "l1": 5,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 6 0",
            "l1": 6,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 7 0",
            "l1": 7,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 8 0",
            "l1": 8,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 9 0",
            "l1": 9,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 10 0",
            "l1": 10,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 11 0",
            "l1": 11,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 12 0",
            "l1": 12,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 13 0",
            "l1": 13,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 14 0",
            "l1": 14,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 15 0",
            "l1": 15,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 16 0",
            "l1": 16,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 17 0",
            "l1": 17,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 18 0",
            "l1": 18,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 19 0",
            "l1": 19,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 20 0",
            "l1": 20,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 21 0",
            "l1": 21,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 22 0",
            "l1": 22,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 23 0",
            "l1": 23,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 24 0",
            "l1": 24,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 25 0",
            "l1": 25,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 26 0",
            "l1": 26,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 27 0",
            "l1": 27,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 28 0",
            "l1": 28,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 29 0",
            "l1": 29,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 30 0",
            "l1": 30,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 31 0",
            "l1": 31,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 32 0",
            "l1": 32,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 33 0",
            "l1": 33,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 34 0",
            "l1": 34,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 35 0",
            "l1": 35,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 36 0",
            "l1": 36,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 37 0",
            "l1": 37,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 38 0",
            "l1": 38,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 39 0",
            "l1": 39,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 40 0",
            "l1": 40,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 41 0",
            "l1": 41,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 42 0",
            "l1": 42,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 43 0",
            "l1": 43,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 44 0",
            "l1": 44,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 45 0",
            "l1": 45,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 46 0",
            "l1": 46,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 47 0",
            "l1": 47,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 48 0",
            "l1": 48,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 49 0",
            "l1": 49,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 50 0",
            "l1": 50,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 51 0",
            "l1": 51,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 52 0",
            "l1": 52,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 53 0",
            "l1": 53,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 54 0",
            "l1": 54,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 55 0",
            "l1": 55,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 56 0",
            "l1": 56,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 57 0",
            "l1": 57,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 58 0",
            "l1": 58,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 59 0",
            "l1": 59,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 60 0",
            "l1": 60,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 61 0",
            "l1": 61,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 62 0",
            "l1": 62,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 63 0",
            "l1": 63,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 64 0",
            "l1": 64,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 65 0",
            "l1": 65,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Hybrid level level number (2 octets) 66 0",
            "l1": 66,
            "lt": 109,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 1 2",
            "l1": 1,
            "l2": 2,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 2 3",
            "l1": 2,
            "l2": 3,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 3 4",
            "l1": 3,
            "l2": 4,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 4 5",
            "l1": 4,
            "l2": 5,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 5 6",
            "l1": 5,
            "l2": 6,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 6 7",
            "l1": 6,
            "l2": 7,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 7 8",
            "l1": 7,
            "l2": 8,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 8 9",
            "l1": 8,
            "l2": 9,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 9 10",
            "l1": 9,
            "l2": 10,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 10 11",
            "l1": 10,
            "l2": 11,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 11 12",
            "l1": 11,
            "l2": 12,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 12 13",
            "l1": 12,
            "l2": 13,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 13 14",
            "l1": 13,
            "l2": 14,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 14 15",
            "l1": 14,
            "l2": 15,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 15 16",
            "l1": 15,
            "l2": 16,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 16 17",
            "l1": 16,
            "l2": 17,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 17 18",
            "l1": 17,
            "l2": 18,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 18 19",
            "l1": 18,
            "l2": 19,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 19 20",
            "l1": 19,
            "l2": 20,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 20 21",
            "l1": 20,
            "l2": 21,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 21 22",
            "l1": 21,
            "l2": 22,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 22 23",
            "l1": 22,
            "l2": 23,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 23 24",
            "l1": 23,
            "l2": 24,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 24 25",
            "l1": 24,
            "l2": 25,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 25 26",
            "l1": 25,
            "l2": 26,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 26 27",
            "l1": 26,
            "l2": 27,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 27 28",
            "l1": 27,
            "l2": 28,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 28 29",
            "l1": 28,
            "l2": 29,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 29 30",
            "l1": 29,
            "l2": 30,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 30 31",
            "l1": 30,
            "l2": 31,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 31 32",
            "l1": 31,
            "l2": 32,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 32 33",
            "l1": 32,
            "l2": 33,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 33 34",
            "l1": 33,
            "l2": 34,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 34 35",
            "l1": 34,
            "l2": 35,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 35 36",
            "l1": 35,
            "l2": 36,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 36 37",
            "l1": 36,
            "l2": 37,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 37 38",
            "l1": 37,
            "l2": 38,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 38 39",
            "l1": 38,
            "l2": 39,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 39 40",
            "l1": 39,
            "l2": 40,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 40 41",
            "l1": 40,
            "l2": 41,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 41 42",
            "l1": 41,
            "l2": 42,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 42 43",
            "l1": 42,
            "l2": 43,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 43 44",
            "l1": 43,
            "l2": 44,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 44 45",
            "l1": 44,
            "l2": 45,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 45 46",
            "l1": 45,
            "l2": 46,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 46 47",
            "l1": 46,
            "l2": 47,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 47 48",
            "l1": 47,
            "l2": 48,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 48 49",
            "l1": 48,
            "l2": 49,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 49 50",
            "l1": 49,
            "l2": 50,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 50 51",
            "l1": 50,
            "l2": 51,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 51 52",
            "l1": 51,
            "l2": 52,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 52 53",
            "l1": 52,
            "l2": 53,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 53 54",
            "l1": 53,
            "l2": 54,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 54 55",
            "l1": 54,
            "l2": 55,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 55 56",
            "l1": 55,
            "l2": 56,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 56 57",
            "l1": 56,
            "l2": 57,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 57 58",
            "l1": 57,
            "l2": 58,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 58 59",
            "l1": 58,
            "l2": 59,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 59 60",
            "l1": 59,
            "l2": 60,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 60 61",
            "l1": 60,
            "l2": 61,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 61 62",
            "l1": 61,
            "l2": 62,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 62 63",
            "l1": 62,
            "l2": 63,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 63 64",
            "l1": 63,
            "l2": 64,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 64 65",
            "l1": 64,
            "l2": 65,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "ml Layer between two hybrid levels level number of top level number of bottom 65 66",
            "l1": 65,
            "l2": 66,
            "lt": 110,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Depth below land surface centimeters (2 octets) 0 0",
            "l1": 0,
            "lt": 111,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Depth below land surface centimeters (2 octets) 1 0",
            "l1": 1,
            "lt": 111,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Depth below land surface centimeters (2 octets) 2 0",
            "l1": 2,
            "lt": 111,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Depth below land surface centimeters (2 octets) 6 0",
            "l1": 6,
            "lt": 111,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Depth below land surface centimeters (2 octets) 18 0",
            "l1": 18,
            "lt": 111,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Depth below land surface centimeters (2 octets) 54 0",
            "l1": 54,
            "lt": 111,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Depth below land surface centimeters (2 octets) 162 0",
            "l1": 162,
            "lt": 111,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Depth below land surface centimeters (2 octets) 486 0",
            "l1": 486,
            "lt": 111,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Depth below land surface centimeters (2 octets) 1458 0",
            "l1": 1458,
            "lt": 111,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Layer between two depths below land surface - depth of upper surface, depth of lower surface (cm) 0 10",
            "l1": 0,
            "l2": 10,
            "lt": 112,
            "s": "GRIB1",
            "t": "level"
        }, {
            "desc": "sfc Layer between two depths below land surface - depth of upper surface, depth of lower surface (cm) 10 190",
            "l1": 10,
            "l2": 190,
            "lt": 112,
            "s": "GRIB1",
            "t": "level"
        }],
        "origin": [{
            "ce": 80,
            "desc": "GRIB1 from 80, subcentre 255, process 12",
            "pr": 12,
            "s": "GRIB1",
            "sc": 255,
            "t": "origin"
        }],
        "proddef": [{
            "desc": "GRIB(ld=254, tod=1)",
            "s": "GRIB",
            "t": "proddef",
            "va": {"ld": 254, "tod": 1}
        }, {"desc": "GRIB(tod=1)", "s": "GRIB", "t": "proddef", "va": {"tod": 1}}],
        "product": [{
            "desc": "P Pressure Pa",
            "or": 80,
            "pr": 1,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "MSL Mean sea level pressure Pa",
            "or": 80,
            "pr": 2,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "T Temperature K",
            "or": 80,
            "pr": 11,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "None Maximum temperature K",
            "or": 80,
            "pr": 15,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "None Minimum temperature K",
            "or": 80,
            "pr": 16,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "None Dew-point temperature K",
            "or": 80,
            "pr": 17,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "U U-component of wind m s^-1",
            "or": 80,
            "pr": 33,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "V V-component of wind m s^-1",
            "or": 80,
            "pr": 34,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "None Vertical velocity m s^-1",
            "or": 80,
            "pr": 40,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "Q Specific humidity kg kg^-1",
            "or": 80,
            "pr": 51,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "None Precipitable water kg m^-2",
            "or": 80,
            "pr": 54,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "TP Total precipitation kg m^-2",
            "or": 80,
            "pr": 61,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "SF Water equivalentof accumulated snow depth kg m^-2",
            "or": 80,
            "pr": 65,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "SD Snow depth m (of water equivalent)",
            "or": 80,
            "pr": 66,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "TCC Total cloud cover %",
            "or": 80,
            "pr": 71,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "LCC Low cloud cover %",
            "or": 80,
            "pr": 73,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "MCC Medium cloud cover %",
            "or": 80,
            "pr": 74,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "HCC High cloud cover %",
            "or": 80,
            "pr": 75,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "LSF Large scale snow-fall kg m^-2",
            "or": 80,
            "pr": 79,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "SR Surface roughness m",
            "or": 80,
            "pr": 83,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "AL Albedo -",
            "or": 80,
            "pr": 84,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "ST Surface temperature of soil K",
            "or": 80,
            "pr": 85,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "RO Water run-off kg m^-2",
            "or": 80,
            "pr": 90,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "None Ice thickness m",
            "or": 80,
            "pr": 92,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "None Net short-wave radiation flux (surface) W m^-2",
            "or": 80,
            "pr": 111,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "None Net long-wave radiation flux (surface) W m^-2",
            "or": 80,
            "pr": 112,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "None Net short-wave radiation flux(atmosph.top) W m^-2",
            "or": 80,
            "pr": 113,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "None Net long-wave radiation flux(atmosph.top) W m^-2",
            "or": 80,
            "pr": 114,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "SLHF (surface) Latent heat flux W m^-2",
            "or": 80,
            "pr": 121,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "SSHF (surface) Sensible heat flux W m^-2",
            "or": 80,
            "pr": 122,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "None Momentum flux, u-component N m^-2",
            "or": 80,
            "pr": 124,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "None Momentum flux, v-component N m^-2",
            "or": 80,
            "pr": 125,
            "s": "GRIB1",
            "t": "product",
            "ta": 2
        }, {
            "desc": "GRIB1(080, 201, 005)",
            "or": 80,
            "pr": 5,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 022)",
            "or": 80,
            "pr": 22,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 023)",
            "or": 80,
            "pr": 23,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 029)",
            "or": 80,
            "pr": 29,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 031)",
            "or": 80,
            "pr": 31,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 033)",
            "or": 80,
            "pr": 33,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 035)",
            "or": 80,
            "pr": 35,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 036)",
            "or": 80,
            "pr": 36,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 039)",
            "or": 80,
            "pr": 39,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 041)",
            "or": 80,
            "pr": 41,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 068)",
            "or": 80,
            "pr": 68,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 069)",
            "or": 80,
            "pr": 69,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 072)",
            "or": 80,
            "pr": 72,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 073)",
            "or": 80,
            "pr": 73,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 082)",
            "or": 80,
            "pr": 82,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 084)",
            "or": 80,
            "pr": 84,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 091)",
            "or": 80,
            "pr": 91,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 094)",
            "or": 80,
            "pr": 94,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 095)",
            "or": 80,
            "pr": 95,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 102)",
            "or": 80,
            "pr": 102,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 129)",
            "or": 80,
            "pr": 129,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 133)",
            "or": 80,
            "pr": 133,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 139)",
            "or": 80,
            "pr": 139,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 145)",
            "or": 80,
            "pr": 145,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 146)",
            "or": 80,
            "pr": 146,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 152)",
            "or": 80,
            "pr": 152,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 170)",
            "or": 80,
            "pr": 170,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 171)",
            "or": 80,
            "pr": 171,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 187)",
            "or": 80,
            "pr": 187,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 191)",
            "or": 80,
            "pr": 191,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 192)",
            "or": 80,
            "pr": 192,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 193)",
            "or": 80,
            "pr": 193,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 194)",
            "or": 80,
            "pr": 194,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 197)",
            "or": 80,
            "pr": 197,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 198)",
            "or": 80,
            "pr": 198,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 199)",
            "or": 80,
            "pr": 199,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 200)",
            "or": 80,
            "pr": 200,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 203)",
            "or": 80,
            "pr": 203,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 201, 215)",
            "or": 80,
            "pr": 215,
            "s": "GRIB1",
            "t": "product",
            "ta": 201
        }, {
            "desc": "GRIB1(080, 203, 203)",
            "or": 80,
            "pr": 203,
            "s": "GRIB1",
            "t": "product",
            "ta": 203
        }, {"desc": "GRIB1(080, 203, 204)", "or": 80, "pr": 204, "s": "GRIB1", "t": "product", "ta": 203}],
        "run": [{"desc": "MINUTE(00:00)", "s": "MINUTE", "t": "run", "va": 0}, {
            "desc": "MINUTE(12:00)",
            "s": "MINUTE",
            "t": "run",
            "va": 720
        }],
        "summarystats": {
            "b": [2019, 9, 1, 12, 0, 0],
            "c": 637000,
            "e": [2019, 10, 9, 12, 0, 0],
            "s": 456198422400
        },
        "timerange": [{
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 0 time unit second",
            "p1": 0,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 3600 time unit second",
            "p1": 1,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 7200 time unit second",
            "p1": 2,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 10800 time unit second",
            "p1": 3,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 14400 time unit second",
            "p1": 4,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 18000 time unit second",
            "p1": 5,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 21600 time unit second",
            "p1": 6,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 25200 time unit second",
            "p1": 7,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 28800 time unit second",
            "p1": 8,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 32400 time unit second",
            "p1": 9,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 36000 time unit second",
            "p1": 10,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 39600 time unit second",
            "p1": 11,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 43200 time unit second",
            "p1": 12,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 46800 time unit second",
            "p1": 13,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 50400 time unit second",
            "p1": 14,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 54000 time unit second",
            "p1": 15,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 57600 time unit second",
            "p1": 16,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 61200 time unit second",
            "p1": 17,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 64800 time unit second",
            "p1": 18,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 68400 time unit second",
            "p1": 19,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 72000 time unit second",
            "p1": 20,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 75600 time unit second",
            "p1": 21,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 79200 time unit second",
            "p1": 22,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 82800 time unit second",
            "p1": 23,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 86400 time unit second",
            "p1": 24,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 90000 time unit second",
            "p1": 25,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 93600 time unit second",
            "p1": 26,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 97200 time unit second",
            "p1": 27,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 100800 time unit second",
            "p1": 28,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 104400 time unit second",
            "p1": 29,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 108000 time unit second",
            "p1": 30,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 111600 time unit second",
            "p1": 31,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 115200 time unit second",
            "p1": 32,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 118800 time unit second",
            "p1": 33,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 122400 time unit second",
            "p1": 34,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 126000 time unit second",
            "p1": 35,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 129600 time unit second",
            "p1": 36,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 133200 time unit second",
            "p1": 37,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 136800 time unit second",
            "p1": 38,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 140400 time unit second",
            "p1": 39,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 144000 time unit second",
            "p1": 40,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 147600 time unit second",
            "p1": 41,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 151200 time unit second",
            "p1": 42,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 154800 time unit second",
            "p1": 43,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 158400 time unit second",
            "p1": 44,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 162000 time unit second",
            "p1": 45,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 165600 time unit second",
            "p1": 46,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 169200 time unit second",
            "p1": 47,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 172800 time unit second",
            "p1": 48,
            "p2": 0,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 0,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 0 p2 3600 time unit second",
            "p1": 0,
            "p2": 1,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 3600 p2 7200 time unit second",
            "p1": 1,
            "p2": 2,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 7200 p2 10800 time unit second",
            "p1": 2,
            "p2": 3,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 10800 p2 14400 time unit second",
            "p1": 3,
            "p2": 4,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 14400 p2 18000 time unit second",
            "p1": 4,
            "p2": 5,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 18000 p2 21600 time unit second",
            "p1": 5,
            "p2": 6,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 21600 p2 25200 time unit second",
            "p1": 6,
            "p2": 7,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 25200 p2 28800 time unit second",
            "p1": 7,
            "p2": 8,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 28800 p2 32400 time unit second",
            "p1": 8,
            "p2": 9,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 32400 p2 36000 time unit second",
            "p1": 9,
            "p2": 10,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 36000 p2 39600 time unit second",
            "p1": 10,
            "p2": 11,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 39600 p2 43200 time unit second",
            "p1": 11,
            "p2": 12,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 43200 p2 46800 time unit second",
            "p1": 12,
            "p2": 13,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 46800 p2 50400 time unit second",
            "p1": 13,
            "p2": 14,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 50400 p2 54000 time unit second",
            "p1": 14,
            "p2": 15,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 54000 p2 57600 time unit second",
            "p1": 15,
            "p2": 16,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 57600 p2 61200 time unit second",
            "p1": 16,
            "p2": 17,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 61200 p2 64800 time unit second",
            "p1": 17,
            "p2": 18,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 64800 p2 68400 time unit second",
            "p1": 18,
            "p2": 19,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 68400 p2 72000 time unit second",
            "p1": 19,
            "p2": 20,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 72000 p2 75600 time unit second",
            "p1": 20,
            "p2": 21,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 75600 p2 79200 time unit second",
            "p1": 21,
            "p2": 22,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 79200 p2 82800 time unit second",
            "p1": 22,
            "p2": 23,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 82800 p2 86400 time unit second",
            "p1": 23,
            "p2": 24,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 86400 p2 90000 time unit second",
            "p1": 24,
            "p2": 25,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 90000 p2 93600 time unit second",
            "p1": 25,
            "p2": 26,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 93600 p2 97200 time unit second",
            "p1": 26,
            "p2": 27,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 97200 p2 100800 time unit second",
            "p1": 27,
            "p2": 28,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 100800 p2 104400 time unit second",
            "p1": 28,
            "p2": 29,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 104400 p2 108000 time unit second",
            "p1": 29,
            "p2": 30,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 108000 p2 111600 time unit second",
            "p1": 30,
            "p2": 31,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 111600 p2 115200 time unit second",
            "p1": 31,
            "p2": 32,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 115200 p2 118800 time unit second",
            "p1": 32,
            "p2": 33,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 118800 p2 122400 time unit second",
            "p1": 33,
            "p2": 34,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 122400 p2 126000 time unit second",
            "p1": 34,
            "p2": 35,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 126000 p2 129600 time unit second",
            "p1": 35,
            "p2": 36,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 129600 p2 133200 time unit second",
            "p1": 36,
            "p2": 37,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 133200 p2 136800 time unit second",
            "p1": 37,
            "p2": 38,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 136800 p2 140400 time unit second",
            "p1": 38,
            "p2": 39,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 140400 p2 144000 time unit second",
            "p1": 39,
            "p2": 40,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 144000 p2 147600 time unit second",
            "p1": 40,
            "p2": 41,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 147600 p2 151200 time unit second",
            "p1": 41,
            "p2": 42,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 151200 p2 154800 time unit second",
            "p1": 42,
            "p2": 43,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 154800 p2 158400 time unit second",
            "p1": 43,
            "p2": 44,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 158400 p2 162000 time unit second",
            "p1": 44,
            "p2": 45,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 162000 p2 165600 time unit second",
            "p1": 45,
            "p2": 46,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 165600 p2 169200 time unit second",
            "p1": 46,
            "p2": 47,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Product with a valid time ranging between reference time + P1 and reference time + P2 - p1 169200 p2 172800 time unit second",
            "p1": 47,
            "p2": 48,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 2,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 3600 time unit second",
            "p1": 0,
            "p2": 1,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 7200 time unit second",
            "p1": 0,
            "p2": 2,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 10800 time unit second",
            "p1": 0,
            "p2": 3,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 14400 time unit second",
            "p1": 0,
            "p2": 4,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 18000 time unit second",
            "p1": 0,
            "p2": 5,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 21600 time unit second",
            "p1": 0,
            "p2": 6,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 25200 time unit second",
            "p1": 0,
            "p2": 7,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 28800 time unit second",
            "p1": 0,
            "p2": 8,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 32400 time unit second",
            "p1": 0,
            "p2": 9,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 36000 time unit second",
            "p1": 0,
            "p2": 10,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 39600 time unit second",
            "p1": 0,
            "p2": 11,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 43200 time unit second",
            "p1": 0,
            "p2": 12,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 46800 time unit second",
            "p1": 0,
            "p2": 13,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 50400 time unit second",
            "p1": 0,
            "p2": 14,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 54000 time unit second",
            "p1": 0,
            "p2": 15,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 57600 time unit second",
            "p1": 0,
            "p2": 16,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 61200 time unit second",
            "p1": 0,
            "p2": 17,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 64800 time unit second",
            "p1": 0,
            "p2": 18,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 68400 time unit second",
            "p1": 0,
            "p2": 19,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 72000 time unit second",
            "p1": 0,
            "p2": 20,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 75600 time unit second",
            "p1": 0,
            "p2": 21,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 79200 time unit second",
            "p1": 0,
            "p2": 22,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 82800 time unit second",
            "p1": 0,
            "p2": 23,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 86400 time unit second",
            "p1": 0,
            "p2": 24,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 90000 time unit second",
            "p1": 0,
            "p2": 25,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 93600 time unit second",
            "p1": 0,
            "p2": 26,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 97200 time unit second",
            "p1": 0,
            "p2": 27,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 100800 time unit second",
            "p1": 0,
            "p2": 28,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 104400 time unit second",
            "p1": 0,
            "p2": 29,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 108000 time unit second",
            "p1": 0,
            "p2": 30,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 111600 time unit second",
            "p1": 0,
            "p2": 31,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 115200 time unit second",
            "p1": 0,
            "p2": 32,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 118800 time unit second",
            "p1": 0,
            "p2": 33,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 122400 time unit second",
            "p1": 0,
            "p2": 34,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 126000 time unit second",
            "p1": 0,
            "p2": 35,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 129600 time unit second",
            "p1": 0,
            "p2": 36,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 133200 time unit second",
            "p1": 0,
            "p2": 37,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 136800 time unit second",
            "p1": 0,
            "p2": 38,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 140400 time unit second",
            "p1": 0,
            "p2": 39,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 144000 time unit second",
            "p1": 0,
            "p2": 40,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 147600 time unit second",
            "p1": 0,
            "p2": 41,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 151200 time unit second",
            "p1": 0,
            "p2": 42,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 154800 time unit second",
            "p1": 0,
            "p2": 43,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 158400 time unit second",
            "p1": 0,
            "p2": 44,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 162000 time unit second",
            "p1": 0,
            "p2": 45,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 165600 time unit second",
            "p1": 0,
            "p2": 46,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 169200 time unit second",
            "p1": 0,
            "p2": 47,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Average (reference time + P1 to reference time + P2) - p1 0 p2 172800 time unit second",
            "p1": 0,
            "p2": 48,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 3,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 3600 time unit second",
            "p1": 0,
            "p2": 1,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 7200 time unit second",
            "p1": 0,
            "p2": 2,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 10800 time unit second",
            "p1": 0,
            "p2": 3,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 14400 time unit second",
            "p1": 0,
            "p2": 4,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 18000 time unit second",
            "p1": 0,
            "p2": 5,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 21600 time unit second",
            "p1": 0,
            "p2": 6,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 25200 time unit second",
            "p1": 0,
            "p2": 7,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 28800 time unit second",
            "p1": 0,
            "p2": 8,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 32400 time unit second",
            "p1": 0,
            "p2": 9,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 36000 time unit second",
            "p1": 0,
            "p2": 10,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 39600 time unit second",
            "p1": 0,
            "p2": 11,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 43200 time unit second",
            "p1": 0,
            "p2": 12,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 46800 time unit second",
            "p1": 0,
            "p2": 13,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 50400 time unit second",
            "p1": 0,
            "p2": 14,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 54000 time unit second",
            "p1": 0,
            "p2": 15,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 57600 time unit second",
            "p1": 0,
            "p2": 16,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 61200 time unit second",
            "p1": 0,
            "p2": 17,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 64800 time unit second",
            "p1": 0,
            "p2": 18,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 68400 time unit second",
            "p1": 0,
            "p2": 19,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 72000 time unit second",
            "p1": 0,
            "p2": 20,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 75600 time unit second",
            "p1": 0,
            "p2": 21,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 79200 time unit second",
            "p1": 0,
            "p2": 22,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 82800 time unit second",
            "p1": 0,
            "p2": 23,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 86400 time unit second",
            "p1": 0,
            "p2": 24,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 90000 time unit second",
            "p1": 0,
            "p2": 25,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 93600 time unit second",
            "p1": 0,
            "p2": 26,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 97200 time unit second",
            "p1": 0,
            "p2": 27,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 100800 time unit second",
            "p1": 0,
            "p2": 28,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 104400 time unit second",
            "p1": 0,
            "p2": 29,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 108000 time unit second",
            "p1": 0,
            "p2": 30,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 111600 time unit second",
            "p1": 0,
            "p2": 31,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 115200 time unit second",
            "p1": 0,
            "p2": 32,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 118800 time unit second",
            "p1": 0,
            "p2": 33,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 122400 time unit second",
            "p1": 0,
            "p2": 34,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 126000 time unit second",
            "p1": 0,
            "p2": 35,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 129600 time unit second",
            "p1": 0,
            "p2": 36,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 133200 time unit second",
            "p1": 0,
            "p2": 37,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 136800 time unit second",
            "p1": 0,
            "p2": 38,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 140400 time unit second",
            "p1": 0,
            "p2": 39,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 144000 time unit second",
            "p1": 0,
            "p2": 40,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 147600 time unit second",
            "p1": 0,
            "p2": 41,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 151200 time unit second",
            "p1": 0,
            "p2": 42,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 154800 time unit second",
            "p1": 0,
            "p2": 43,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 158400 time unit second",
            "p1": 0,
            "p2": 44,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 162000 time unit second",
            "p1": 0,
            "p2": 45,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 165600 time unit second",
            "p1": 0,
            "p2": 46,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 169200 time unit second",
            "p1": 0,
            "p2": 47,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }, {
            "desc": "Accumulation (reference time + P1 to reference time + P2) product considered valid at reference time + P2 - p1 0 p2 172800 time unit second",
            "p1": 0,
            "p2": 48,
            "s": "GRIB1",
            "t": "timerange",
            "ty": 4,
            "un": 1
        }]
    }
};

export const MockRequestsTotalResponse: any = {"total": 2};

export const MockRequestsNoDataResponse: any = [];

export const MockRequestsResponse: any = [
    {
        "args": {
            "datasets": ["lm5"],
            "filters": {
                "proddef": [{"desc": "GRIB(tod=1)", "s": "GRIB", "va": {"tod": 1}}],
                "product": [{"desc": "T Temperature K", "or": 80, "pr": 11, "s": "GRIB1", "ta": 2}],
                "run": [{"desc": "MINUTE(00:00)", "s": "MINUTE", "va": 0}],
                "timerange": [{
                    "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 0 time unit second",
                    "p1": 0,
                    "p2": 0,
                    "s": "GRIB1",
                    "ty": 0,
                    "un": 1
                }, {
                    "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 3600 time unit second",
                    "p1": 1,
                    "p2": 0,
                    "s": "GRIB1",
                    "ty": 0,
                    "un": 1
                }]
            },
            "postprocessors": []
        },
        "end_date": "2019-11-21T08:02:02.710789",
        "fileoutput": "data-20191121T080202Z-9896b1d0-9ae4-456a-899d-78cb904b3c02.grib",
        "filesize": 341539308,
        "id": 246,
        "name": "Test-scheduled",
        "schedule_id": 11,
        "status": "SUCCESS",
        "submission_date": "2019-11-21T08:02:02.542379",
        "task_id": "9896b1d0-9ae4-456a-899d-78cb904b3c02"
    },
    {
        "args": {
            "datasets": ["lm2.2"],
            "filters": {
                "level": [{
                    "desc": "sfc Surface (of the Earth, which includes sea surface) 0 0",
                    "lt": 1,
                    "s": "GRIB1"
                }, {
                    "desc": "sfc Cloud base level 0 0",
                    "lt": 2,
                    "s": "GRIB1"
                }, {
                    "desc": "sfc Cloud top level 0 0",
                    "lt": 3,
                    "s": "GRIB1"
                }, {
                    "desc": "sfc 0 deg (C) isotherm level 0 0",
                    "lt": 4,
                    "s": "GRIB1"
                }, {
                    "desc": "sfc Nominal top of atmosphere 0 0",
                    "lt": 8,
                    "s": "GRIB1"
                }, {
                    "desc": "sfc Mean sea level 0 0 0 0",
                    "lt": 102,
                    "s": "GRIB1"
                }, {
                    "desc": "sfc Fixed height above ground height in meters (2 octets) 2 0",
                    "l1": 2,
                    "lt": 105,
                    "s": "GRIB1"
                }, {
                    "desc": "sfc Fixed height above ground height in meters (2 octets) 10 0",
                    "l1": 10,
                    "lt": 105,
                    "s": "GRIB1"
                }],
                "product": [{
                    "desc": "U U-component of wind m s^-1",
                    "or": 80,
                    "pr": 33,
                    "s": "GRIB1",
                    "ta": 2
                }, {"desc": "V V-component of wind m s^-1", "or": 80, "pr": 34, "s": "GRIB1", "ta": 2}],
                "timerange": [{
                    "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 0 time unit second",
                    "p1": 0,
                    "p2": 0,
                    "s": "GRIB1",
                    "ty": 0,
                    "un": 1
                }, {
                    "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 3600 time unit second",
                    "p1": 1,
                    "p2": 0,
                    "s": "GRIB1",
                    "ty": 0,
                    "un": 1
                }, {
                    "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 7200 time unit second",
                    "p1": 2,
                    "p2": 0,
                    "s": "GRIB1",
                    "ty": 0,
                    "un": 1
                }, {
                    "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 10800 time unit second",
                    "p1": 3,
                    "p2": 0,
                    "s": "GRIB1",
                    "ty": 0,
                    "un": 1
                }]
            },
            "postprocessors": [{"type": "additional_variables", "variables": ["B11001", "B11002"]}],
            "reftime": null
        },
        "end_date": "2019-10-31T14:15:01.868711",
        "fileoutput": "data-20191031T141501Z-fa40e3eb-42f3-4963-bd43-9bd324955952.grib",
        "filesize": 103382016,
        "id": 199,
        "name": "test-vento",
        "status": "SUCCESS",
        "submission_date": "2019-10-31T14:09:59.543570",
        "task_id": null
    }
];

export const MockSchedulesTotalResponse: any = {"total": 3};

export const MockSchedulesNoDataResponse: any = [];

export const MockSchedulesResponse: any = [
    {
        "args": {
            "datasets": ["lm5"],
            "filters": {
                "proddef": [{"desc": "GRIB(tod=1)", "s": "GRIB", "va": {"tod": 1}}],
                "product": [{"desc": "T Temperature K", "or": 80, "pr": 11, "s": "GRIB1", "ta": 2}],
                "run": [{"desc": "MINUTE(00:00)", "s": "MINUTE", "va": 0}],
                "timerange": [{
                    "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 0 time unit second",
                    "p1": 0,
                    "p2": 0,
                    "s": "GRIB1",
                    "ty": 0,
                    "un": 1
                }, {
                    "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 3600 time unit second",
                    "p1": 1,
                    "p2": 0,
                    "s": "GRIB1",
                    "ty": 0,
                    "un": 1
                }]
            },
            "postprocessors": [],
            "reftime": {"from": "2019-09-01T00:00:00.000Z", "to": "2019-09-30T12:02:00.000Z"}
        },
        "creation_date": "2019-10-28T12:03:44.625372",
        "enabled": true,
        "every": 2,
        "id": 11,
        "name": "Test-scheduled",
        "period": "days",
        "periodic": true,
        "periodic_settings": "every 2 days",
        "requests_count": 8
    },
    {
        "args": {
            "datasets": ["lm2.2"],
            "filters": {
                "level": [{
                    "desc": "sfc Surface (of the Earth, which includes sea surface) 0 0",
                    "lt": 1,
                    "s": "GRIB1"
                }, {"desc": "sfc Cloud base level 0 0", "lt": 2, "s": "GRIB1"}],
                "product": [{"desc": "P Pressure Pa", "or": 80, "pr": 1, "s": "GRIB1", "ta": 2}],
                "timerange": [{
                    "desc": "Forecast product valid at reference time + P1 (P1>0) - p1 0 time unit second",
                    "p1": 0,
                    "p2": 0,
                    "s": "GRIB1",
                    "ty": 0,
                    "un": 1
                }]
            },
            "postprocessors": []
        },
        "creation_date": "2019-09-24T15:44:26.049672",
        "crontab": true,
        "crontab_settings": {"hour": 5, "minute": 0},
        "enabled": true,
        "id": 3,
        "name": "lm2.2 pressure at surface and cloud level",
        "requests_count": 7
    },
    {
        "args": {
            "datasets": ["lm5"],
            "filters": {
                "area": [{
                    "desc": "GRIB(Ni=1083, Nj=559, latfirst=-13050000, latlast=12060000, latp=-47000000, lonfirst=-25290000, lonlast=23400000, lonp=10000000, rot=0, type=10)",
                    "s": "GRIB",
                    "va": {
                        "Ni": 1083,
                        "Nj": 559,
                        "latfirst": -13050000,
                        "latlast": 12060000,
                        "latp": -47000000,
                        "lonfirst": -25290000,
                        "lonlast": 23400000,
                        "lonp": 10000000,
                        "rot": 0,
                        "type": 10
                    }
                }],
                "level": [{
                    "desc": "sfc Surface (of the Earth, which includes sea surface) 0 0",
                    "lt": 1,
                    "s": "GRIB1"
                }],
                "product": [{"desc": "P Pressure Pa", "or": 80, "pr": 1, "s": "GRIB1", "ta": 2}],
                "run": [{"desc": "MINUTE(00:00)", "s": "MINUTE", "va": 0}]
            }
        },
        "creation_date": "2019-09-17T12:42:10.125201",
        "crontab": true,
        "crontab_settings": {"hour": 0, "minute": 0},
        "enabled": false,
        "id": 1,
        "name": "lm5",
        "requests_count": 0
    }
];
