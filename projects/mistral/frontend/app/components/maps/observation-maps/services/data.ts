import {FieldsSummary, Network, Product} from "./obs.service";

export interface CodeDescPair {
    code: string;
    desc?: string;
}

export const NETWORKS: CodeDescPair[] = [
    {code: 'agrmet'},
    {code: 'boa'},
    {code: 'cer'},
    {code: 'claster'},
    {code: 'cro'},
    {code: 'fiduma'},
    {code: 'fidupo'},
    {code: 'fiduto'},
    {code: 'fiduve'},
    {code: 'icirfe'},
    {code: 'idrtl9'},
    {code: 'locali'},
    {code: 'marefe'},
    {code: 'profe'},
    {code: 'provpc'},
    {code: 'simnbo'},
    {code: 'simnpr'},
    {code: 'spdsra'},
    {code: 'urbane'},
];

export const PRODUCTS: CodeDescPair[] = [
    {code:"B12101", desc:"TEMPERATURE/DRY-BULB TEMPERATURE"},
    {code:"B13003", desc:"RELATIVE HUMIDITY"},
    {code:"B13011", desc:"TOTAL PRECIPITATION / TOTAL WATER EQUIVALENT"},
    {code:"B13227", desc:"Soil volumetric water content"},
    {code:"B22001", desc:"DIRECTION OF WAVES"},
    {code:"B22043", desc:"SEA/WATER TEMPERATURE"},
    {code:"B22070", desc:"SIGNIFICANT WAVE HEIGHT"},
    {code:"B22071", desc:"SPECTRAL PEAK WAVE PERIOD"},
    {code:"B22074", desc:"AVERAGE WAVE PERIOD"},
    {code:"B13215", desc:"River level"},
    {code:"B11001", desc:"WIND DIRECTION"},
    {code:"B11002", desc:"WIND SPEED"},
    {code:"B10004", desc:"PRESSURE"},
    {code:"B13226", desc:"River discharge"},
    {code:"B11041", desc:"MAXIMUM WIND GUST SPEED"},
    {code:"B13013", desc:"TOTAL SNOW DEPTH"},
    {code:"B14198", desc:"Global radiation flux (downward)"},
    {code:"B13080", desc:"WATER PH"},
    {code:"B13083", desc:"DISSOLVED OXYGEN"},
    {code:"B13231", desc:"Ossigeno disciolto sat"},
    {code:"B22037", desc:"Tidal elevation with respect to national land datum"},
    {code:"B22038", desc:"Tidal elevation with respect to local chart datum"},
    {code:"B22062", desc:"SALINITY"},
    {code:"B22195", desc:"Depth below sea surface"},
    {code:"B11043", desc:"MAXIMUM WIND GUST DIRECTION"}];

export const LEVELS: CodeDescPair[] = [
    {code:"1,0,0,0", desc:"Ground or water surface"},
    {code:"103,2000,0,0", desc:"2.000m above ground"},
    {code:"106,250,0,0", desc:"0.250m below land surface"},
    {code:"106,450,0,0", desc:"0.450m below land surface"},
    {code:"106,700,0,0", desc:"0.700m below land surface"},
    {code:"160,350,0,0", desc:"0.350m below sea level"},
    {code:"103,10000,0,0", desc:"10.000m above ground"},
    {code:"101,0,0,0", desc:"Mean sea level"},
    {code:"160,1000,0,0", desc:"1.000m below sea level"},
    {code:"106,150,0,0", desc:"0.150m below land surface"},
    {code:"106,600,0,0", desc:"0.600m below land surface"}
];

export const TIME_RANGES: CodeDescPair[] = [
    {code:"0,0,3600", desc:"Average over 1h at forecast time 0"},
    {code:"0,0,86400", desc:"Average over 1d at forecast time 0"},
    {code:"1,0,900", desc:"Accumulation over 15m at forecast time 0"},
    {code:"1,0,3600", desc:"Accumulation over 1h at forecast time 0"},
    {code:"1,0,86400", desc:"Accumulation over 1d at forecast time 0"},
    {code:"2,0,3600", desc:"Maximum over 1h at forecast time 0"},
    {code:"2,0,86400", desc:"Maximum over 1d at forecast time 0"},
    {code:"3,0,3600", desc:"Minimum over 1h at forecast time 0"},
    {code:"3,0,86400", desc:"Minimum over 1d at forecast time 0"},
    {code:"254,0,0", desc:"Analysis or observation, istantaneous value"},
    {code:"0,0,1800", desc:"Average over 30m at forecast time 0"},
    {code:"205,0,1800", desc:"Product with a valid time ranging over 30m at forecast time 0"},
    {code:"201,0,86400", desc:"Mode over 1d at forecast time 0"},
    {code:"1,0,1800", desc:"Accumulation over 30m at forecast time 0"},
    {code:"200,0,3600", desc:"Vectorial mean over 1h at forecast time 0"},
    {code:"205,0,3600", desc:"Product with a valid time ranging over 1h at forecast time 0"},
    {code:"205,0,600", desc:"Product with a valid time ranging over 10m at forecast time 0"}
];

export const LICENSES: CodeDescPair[] = [
    {code: "CC-BY", desc: "CC-BY compliant"},
    // {code: "ODL", desc: "ODL"}
];

export const COLORS = ['3030ff','007885','00855D','0D8500','478500','788500','853C00','850000'];

export const FIELDS_SUMMARY: FieldsSummary = {
    items: {
        product: PRODUCTS,
        level: LEVELS,
        timerange: TIME_RANGES,
        network: NETWORKS
    }
}

export const obsData = [{"station":{"id":891,"ident":null,"lat":45.05492,"lon":9.67965,"network":"urbane"}},{"station":{"id":892,"ident":null,"lat":44.808,"lon":10.33049,"network":"urbane"}},{"station":{"id":893,"ident":null,"lat":44.69781,"lon":10.6337,"network":"urbane"}},{"station":{"id":894,"ident":null,"lat":44.50075,"lon":11.32879,"network":"urbane"}},{"station":{"id":895,"ident":null,"lat":44.8325,"lon":11.62114,"network":"urbane"}},{"station":{"id":896,"ident":null,"lat":44.22039,"lon":12.04182,"network":"urbane"}},{"station":{"id":897,"ident":null,"lat":44.415,"lon":12.20003,"network":"urbane"}},{"station":{"id":898,"ident":null,"lat":44.1382,"lon":12.24364,"network":"urbane"}},{"station":{"id":899,"ident":null,"lat":44.05919,"lon":12.57354,"network":"urbane"}},{"station":{"id":900,"ident":null,"lat":44.65639,"lon":10.91699,"network":"urbane"}}];

export interface Bcode {
    bcode: string;
    description: string;
    short?: string;
    unit: string;
    offset: number;
    scale: number;
    userunit: string;
}

export const VAR_TABLE: Bcode[] = [
    {
        "bcode": "B12101",
        "description": "TEMPERATURE/DRY-BULB TEMPERATURE",
        "short": "Temp",
        "unit": "K",
        "offset": -273.15,
        "scale": 1.0,
        "userunit": "°C"
    },
    {
        "bcode": "B13003",
        "description": "RELATIVE HUMIDITY",
        "unit": "%",
        "offset": 0.0,
        "scale": 1.0,
        "userunit": "%"
    },
    {
        "bcode": "B10004",
        "description": "PRESSURE",
        "unit": "Pa",
        "offset": 0.0,
        "scale": 0.01,
        "userunit": "hPa"
    },
    {
        "bcode": "B11001",
        "description": "WIND DIRECTION",
        "unit": "DEGREE TRUE",
        "offset": 0.0,
        "scale": 1.0,
        "userunit": "Degree"
    },
    {
        "bcode": "B11002",
        "description": "WIND SPEED",
        "unit": "M/S",
        "offset": 0.0,
        "scale": 1.0,
        "userunit": "m/s"
    },
    {
        "bcode": "B13011",
        "description": "TOTAL PRECIPITATION / TOTAL WATER EQUIVALENT",
        "unit": "KG/M**2",
        "offset": 0.0,
        "scale": 1.0,
        "userunit": "Kg/m**2"
    },
    {
        "bcode": "B15198",
        "description": "PM2.5 Concentration",
        "unit": "KG/M**3",
        "offset": 0.0,
        "scale": 1000000000.0,
        "userunit": "ug/m**3"
    },
    {
        "bcode": "B15195",
        "description": "PM10 Concentration",
        "unit": "KG/M**3",
        "offset": 0.0,
        "scale": 1000000000.0,
        "userunit": "ug/m**3"
    },
    {
        "bcode": "B15196",
        "description": "CO Concentration",
        "unit": "KG/M**3",
        "offset": 0.0,
        "scale": 1000000000.0,
        "userunit": "ug/m**3"
    },
    {
        "bcode": "B15193",
        "description": "NO2 Concentration",
        "unit": "KG/M**3",
        "offset": 0.0,
        "scale": 1000000000.0,
        "userunit": "ug/m**3"
    },
    {
        "bcode": "B13013",
        "description": "TOTAL SNOW DEPTH",
        "unit": "M",
        "offset": 0.0,
        "scale": 0.1,
        "userunit": "cm"
    },
    {
        "bcode": "20001",
        "description": "HORIZONTAL VISIBILITY",
        "unit": "M",
        "offset": 0.0,
        "scale": 1.0,
        "userunit": "m"
    },
    {
        "bcode": "B25025",
        "description": "Battery voltage",
        "unit": "V",
        "offset": 0.0,
        "scale": 1.0,
        "userunit": "V"
    },
    {
        "bcode": "B25192",
        "description": "Battery charge",
        "unit": "%",
        "offset": 0.0,
        "scale": 1.0,
        "userunit": "%"
    },
    {
        "bcode": "B25193",
        "description": "Battery current",
        "unit": "A",
        "offset": 0.0,
        "scale": 1.0,
        "userunit": "A"
    },
    {
        "bcode": "B15203",
        "description": "PM1 Concentration",
        "unit": "KG/M**3",
        "offset": 0.0,
        "scale": 1000000000.0,
        "userunit": "ug/m**3"
    },
    {
        "bcode": "B49192",
        "description": "Number of particles with diameter < 0.3 um",
        "unit": "number/ml",
        "offset": 0.0,
        "scale": 1.0,
        "userunit": "number/ml"
    },
    {
        "bcode": "B49193",
        "description": "Number of particles with diameter > 0.3 < 0.5 um",
        "unit": "number/ml",
        "offset": 0.0,
        "scale": 1.0,
        "userunit": "number/ml"
    },
    {
        "bcode": "B49194",
        "description": "Number of particles with diameter > 0.5 < 1.0 um",
        "unit": "number/ml",
        "offset": 0.0,
        "scale": 1.0,
        "userunit": "number/ml"
    },
    {
        "bcode": "B49195",
        "description": "Number of particles with diameter > 1.0 < 2.5 um",
        "unit": "number/ml",
        "offset": 0.0,
        "scale": 1.0,
        "userunit": "number/ml"
    },
    {
        "bcode": "B49196",
        "description": "Number of particles with diameter > 2.5 < 5.0 um",
        "unit": "number/ml",
        "offset": 0.0,
        "scale": 1.0,
        "userunit": "number/ml"
    },
    {
        "bcode": "B49197",
        "description": "Number of particles with diameter > 5.0 < 10.0 um",
        "unit": "number/ml",
        "offset": 0.0,
        "scale": 1.0,
        "userunit": "number/ml"
    },
    {
        "bcode": "B15242",
        "description": "CO2 Concentration",
        "unit": "KG/M**3",
        "offset": 0.0,
        "scale": 555560.0,
        "userunit": "ppm"
    },
    {
        "bcode": "B15202",
        "description": "PM5 Concentration",
        "unit": "KG/M**3",
        "offset": 0.0,
        "scale": 1000000000.0,
        "userunit": "ug/m**3"
    }
];

