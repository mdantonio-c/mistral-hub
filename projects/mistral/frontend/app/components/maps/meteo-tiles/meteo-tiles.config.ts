/*
export interface MMTimeRange {
  idx: number;
  offset: number;
  code: string;
}

export const MULTI_MODEL_TIME_RANGES: MMTimeRange[] = [
  {
    idx: 0,
    code: "254,97200,0",  // "Forecast at t+1d 3h,  instantaneous value"
    offset: 27
  }, {
    idx: 1,
    code: "254,108000,0", // "Forecast at t+1d 6h,  instantaneous value"
    offset: 30
  }, {
    idx: 2,
    code: "254,118800,0", // "Forecast at t+1d 9h,  instantaneous value"
    offset: 33
  }, {
    idx: 3,
    code: "254,129600,0", // "Forecast at t+1d 12h, instantaneous value"
    offset: 36
  }, {
    idx: 4,
    code: "254,140400,0", // "Forecast at t+1d 15h, instantaneous value"
    offset: 39
  }, {
    idx: 5,
    code: "254,151200,0", // "Forecast at t+1d 18h, instantaneous value"
    offset: 42
  }, {
    idx: 6,
    code: "254,162000,0", // "Forecast at t+1d 21h, instantaneous value"
    offset: 45
  }, {
    idx: 7,
    code: "254,172800,0", // "Forecast at t+2d,     instantaneous value"
    offset: 48
  }, {
    idx: 8,
    code: "254,183600,0", // "Forecast at t+2d 3h,  instantaneous value"
    offset: 51
  }, {
    idx: 9,
    code: "254,194400,0", // "Forecast at t+2d 6h,  instantaneous value"
    offset: 54
  }, {
    idx: 10,
    code: "254,205200,0", // "Forecast at t+2d 9h,  instantaneous value"
    offset: 57
  }, {
    idx: 11,
    code: "254,216000,0", // "Forecast at t+2d 12h, instantaneous value"
    offset: 60
  }, {
    idx: 12,
    code: "254,226800,0", // "Forecast at t+2d 15h, instantaneous value"
    offset: 63
  }, {
    idx: 13,
    code: "254,237600,0", // "Forecast at t+2d 18h, instantaneous value"
    offset: 66
  }, {
    idx: 14,
    code: "254,248400,0", // "Forecast at t+2d 21h, instantaneous value"
    offset: 69
  }, {
    idx: 15,
    code: "254,259200,0", // "Forecast at t+3d,     instantaneous value"
    offset: 72
  }, {
    idx: 16,
    code: "254,270000,0", // "Forecast at t+3d 3h,  instantaneous value"
    offset: 75
  }, {
    idx: 17,
    code: "254,280800,0", // "Forecast at t+3d 6h,  instantaneous value"
    offset: 78
  }, {
    idx: 18,
    code: "254,291600,0", // "Forecast at t+3d 9h,  instantaneous value"
    offset: 81
  }, {
    idx: 19,
    code: "254,302400,0", // "Forecast at t+3d 12h, instantaneous value"
    offset: 84
  }, {
    idx: 20,
    code: "254,313200,0", // "Forecast at t+3d 15h, instantaneous value"
    offset: 87
  }, {
    idx: 21,
    code: "254,324000,0", // "Forecast at t+3d 18h, instantaneous value"
    offset: 90
  }, {
    idx: 22,
    code: "254,334800,0", // "Forecast at t+3d 21h, instantaneous value"
    offset: 93
  }, {
    idx: 23,
    code: "254,345600,0", // "Forecast at t+4d,     instantaneous value"
    offset: 96
  }
];
 */

export enum MULTI_MODEL_TIME_RANGES {
  _1D3H = "254,97200,0", // "Forecast at t+1d 3h,  instantaneous value"
  _1D6H = "254,108000,0", // "Forecast at t+1d 6h,  instantaneous value"
  _1D9H = "254,118800,0", // "Forecast at t+1d 9h,  instantaneous value"
  _1D12H = "254,129600,0", // "Forecast at t+1d 12h, instantaneous value"
  _1D15H = "254,140400,0", // "Forecast at t+1d 15h, instantaneous value"
  _1D18H = "254,151200,0", // "Forecast at t+1d 18h, instantaneous value"
  _1D21H = "254,162000,0", // "Forecast at t+1d 21h, instantaneous value"
  _2D = "254,172800,0", // "Forecast at t+2d,     instantaneous value"
  _2D3H = "254,183600,0", // "Forecast at t+2d 3h,  instantaneous value"
  _2D6H = "254,194400,0", // "Forecast at t+2d 6h,  instantaneous value"
  _2D9H = "254,205200,0", // "Forecast at t+2d 9h,  instantaneous value"
  _2D12H = "254,216000,0", // "Forecast at t+2d 12h, instantaneous value"
  _2D15H = "254,226800,0", // "Forecast at t+2d 15h, instantaneous value"
  _2D18H = "254,237600,0", // "Forecast at t+2d 18h, instantaneous value"
  _2D21H = "254,248400,0", // "Forecast at t+2d 21h, instantaneous value"
  _3D = "254,259200,0", // "Forecast at t+3d,     instantaneous value"
  _3D3H = "254,270000,0", // "Forecast at t+3d 3h,  instantaneous value"
  _3D6H = "254,280800,0", // "Forecast at t+3d 6h,  instantaneous value"
  _3D9H = "254,291600,0", // "Forecast at t+3d 9h,  instantaneous value"
  _3D12H = "254,302400,0", // "Forecast at t+3d 12h, instantaneous value"
  _3D15H = "254,313200,0", // "Forecast at t+3d 15h, instantaneous value"
  _3D18H = "254,324000,0", // "Forecast at t+3d 18h, instantaneous value"
  _3D21H = "254,334800,0", // "Forecast at t+3d 21h, instantaneous value"
  _4D = "254,345600,0", // "Forecast at t+4d,     instantaneous value"
}

/*
export enum MULTI_MODEL_TIME_RANGES {
  "254,97200,0",  // "Forecast at t+1d 3h,  instantaneous value"
  "254,108000,0", // "Forecast at t+1d 6h,  instantaneous value"
  "254,118800,0", // "Forecast at t+1d 9h,  instantaneous value"
  "254,129600,0", // "Forecast at t+1d 12h, instantaneous value"
  "254,140400,0", // "Forecast at t+1d 15h, instantaneous value"
  "254,151200,0", // "Forecast at t+1d 18h, instantaneous value"
  "254,162000,0", // "Forecast at t+1d 21h, instantaneous value"
  "254,172800,0", // "Forecast at t+2d,     instantaneous value"
  "254,183600,0", // "Forecast at t+2d 3h,  instantaneous value"
  "254,194400,0", // "Forecast at t+2d 6h,  instantaneous value"
  "254,205200,0", // "Forecast at t+2d 9h,  instantaneous value"
  "254,216000,0", // "Forecast at t+2d 12h, instantaneous value"
  "254,226800,0", // "Forecast at t+2d 15h, instantaneous value"
  "254,237600,0", // "Forecast at t+2d 18h, instantaneous value"
  "254,248400,0", // "Forecast at t+2d 21h, instantaneous value"
  "254,259200,0", // "Forecast at t+3d,     instantaneous value"
  "254,270000,0", // "Forecast at t+3d 3h,  instantaneous value"
  "254,280800,0", // "Forecast at t+3d 6h,  instantaneous value"
  "254,291600,0", // "Forecast at t+3d 9h,  instantaneous value"
  "254,302400,0", // "Forecast at t+3d 12h, instantaneous value"
  "254,313200,0", // "Forecast at t+3d 15h, instantaneous value"
  "254,324000,0", // "Forecast at t+3d 18h, instantaneous value"
  "254,334800,0", // "Forecast at t+3d 21h, instantaneous value"
  "254,345600,0", // "Forecast at t+4d,     instantaneous value"
} */

export enum DatasetProduct {
  TM2 = "Temperature at 2 meters",
  PMSL = "Pressure mean sea level",
  WIND10M = "Wind speed at 10 meters",
  RH = "Relative Humidity",

  PREC1P = "Total Precipitation (1h)",
  PREC3P = "Total Precipitation (3h)",
  PREC6P = "Total Precipitation (6h)",
  PREC12P = "Total Precipitation (12h)",
  PREC24P = "Total Precipitation (24h)",

  SF1 = "Snowfall (1h)",
  SF3 = "Snowfall (3h)",
  SF6 = "Snowfall (6h)",
  SF12 = "Snowfall (12h)",
  SF24 = "Snowfall (24h)",

  TCC = "Total Cloud",
  HCC = "High Cloud",
  MCC = "Medium Cloud",
  LCC = "Low Cloud",

  TPPERC1 = "Precipitation percentiles 1",
  TPPERC10 = "Precipitation percentile 10",
  TPPERC25 = "Precipitation percentile 25",
  TPPERC50 = "Precipitation percentile 50",
  TPPERC70 = "Precipitation percentile 70",
  TPPERC75 = "Precipitation percentile 75",
  TPPERC80 = "Precipitation percentile 80",
  TPPERC90 = "Precipitation percentile 90",
  TPPERC95 = "Precipitation percentile 95",
  TPPERC99 = "Precipitation percentile 99",

  TPPROB5 = "Precipitation probability 5 mm",
  TPPROB10 = "Precipitation probability 10 mm",
  TPPROB20 = "Precipitation probability 20 mm",
  TPPROB50 = "Precipitation probability 50 mm",
}

export enum MultiModelProduct {
  TM = "B12101",
  RH = "B13003",
}
