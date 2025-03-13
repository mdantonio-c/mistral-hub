import { CodeDescPair } from "@app/types";

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

  TPPERC1 = "Precipitation percentile 1",
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

export const MultiModelProductLabel = new Map<string, string>([
  [MultiModelProduct.TM, "Temperature"],
  [MultiModelProduct.RH, "Relative Humidity"],
]);

export const DATASETS: CodeDescPair[] = [{ code: "icon", desc: "ICON-2I" }];

export enum ViewModes {
  base,
  adv,
}

export const MOBILE_WIDTH = 760;

export const OSM_LICENSE_HREF =
    '<a href="http://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">Open Street Map</a>',
  CARTODB_LICENSE_HREF =
    '<a href="http://cartodb.com/attributions" target="_blank" rel="noopener noreferrer">CARTO</a>',
  STADIA_LICENSE_HREF =
    '<a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a>',
  MISTRAL_LICENSE_HREF =
    '<a href="./app/license#mistral-products" target="_blank" rel="noopener noreferrer">MISTRAL</a>';
