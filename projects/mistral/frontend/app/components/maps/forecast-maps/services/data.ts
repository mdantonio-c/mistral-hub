export interface KeyValuePair {
  key: string;
  value: string;
}

export const Fields_icon: KeyValuePair[] = [
  { key: "prec1", value: "Accumulated total prec. 1h (kg/m\u00B2)" },
  { key: "prec3", value: "Accumulated total prec. 3h (kg/m\u00B2)" },
  { key: "prec6", value: "Accumulated total prec. 6h (kg/m\u00B2)" },
  { key: "prec12", value: "Accumulated total prec. 12h (kg/m\u00B2)" },
  { key: "prec24", value: "Accumulated total prec. 24h (kg/m\u00B2)" },
  { key: "t2m", value: "Temperature at 2 meters (C°)" },
  { key: "wind", value: "Wind at 10 meters (m/s)" },
  { key: "pressure", value: "Pressure at mean sea level (hPa)" },
  { key: "cloud", value: "Cloud coverage (%)" },
  { key: "cloud_hml", value: "Cloud coverage high, medium, low (%)" },
  { key: "humidity", value: "Relative humidity (%)" },
  { key: "snow1", value: "Accumulated total snow prec. 1h (kg/m\u00B2)" },
  { key: "snow3", value: "Accumulated total snow prec. 3h (kg/m\u00B2)" },
  { key: "snow6", value: "Accumulated total snow prec. 6h (kg/m\u00B2)" },
  { key: "snow12", value: "Accumulated total snow prec. 12h (kg/m\u00B2)" },
  { key: "snow24", value: "Accumulated total snow prec. 24h (kg/m\u00B2)" },
];

export const Fields_cosmo: KeyValuePair[] = [
  { key: "prec1", value: "Accumulated total prec. 1h (kg/m\u00B2)" },
  { key: "prec3", value: "Accumulated total prec. 3h (kg/m\u00B2)" },
  { key: "prec6", value: "Accumulated total prec. 6h (kg/m\u00B2)" },
  { key: "prec12", value: "Accumulated total prec. 12h (kg/m\u00B2)" },
  { key: "prec24", value: "Accumulated total prec. 24h (kg/m\u00B2)" },
  { key: "t2m", value: "Temperature at 2 meters (C°)" },
  { key: "wind", value: "Wind at 10 meters (m/s)" },
  { key: "pressure", value: "Pressure at mean sea level (hPa)" },
  { key: "cloud", value: "Cloud coverage (%)" },
  { key: "cloud_hml", value: "Cloud coverage high, medium, low (%)" },
  { key: "humidity", value: "Relative humidity (%)" },
  { key: "snow3", value: "Accumulated total snow prec. 3h (kg/m\u00B2)" },
  { key: "snow6", value: "Accumulated total snow prec. 6h (kg/m\u00B2)" },
];

export const Fields_wrf: KeyValuePair[] = [
  { key: "prec1", value: "Accumulated total prec. 1h (kg/m\u00B2)" },
  { key: "prec3", value: "Accumulated total prec. 3h (kg/m\u00B2)" },
  { key: "prec6", value: "Accumulated total prec. 6h (kg/m\u00B2)" },
  { key: "prec12", value: "Accumulated total prec. 12h (kg/m\u00B2)" },
  { key: "prec24", value: "Accumulated total prec. 24h (kg/m\u00B2)" },
  { key: "t2m", value: "Temperature at 2 meters (C°)" },
  { key: "wind", value: "Wind at 10 meters (m/s)" },
  { key: "pressure", value: "Pressure at mean sea level (hPa)" },
  { key: "cloud", value: "Cloud coverage (%)" },
  { key: "cloud_hml", value: "Cloud coverage high, medium, low (%)" },
  // { key: "humidity", value: "Relative humidity (%)" },
  // { key: "snow3", value: "Accumulated total snow prec. 3h (kg/m\u00B2)" },
  // { key: "snow6", value: "Accumulated total snow prec. 6h (kg/m\u00B2)" },
];

export const FlashFloodFFields: KeyValuePair[] = [
  {
    key: "percentile",
    value: "6h precipitation percentiles (mm)",
  },
  {
    key: "probability",
    value: "6h precipitation probability (%)",
  },
];

export const Levels_pe: KeyValuePair[] = [
  { key: "1", value: "1" },
  { key: "10", value: "10" },
  { key: "25", value: "25" },
  { key: "50", value: "50" },
  { key: "70", value: "70" },
  { key: "75", value: "75" },
  { key: "80", value: "80" },
  { key: "90", value: "90" },
  { key: "95", value: "95" },
  { key: "99", value: "99" },
];

export const Levels_pr: KeyValuePair[] = [
  { key: "5", value: "5" },
  { key: "10", value: "10" },
  { key: "20", value: "20" },
  { key: "50", value: "50" },
];

export const Runs: KeyValuePair[] = [
  { key: "00", value: "00" },
  { key: "12", value: "12" },
];

export const IffRuns: KeyValuePair[] = [
  { key: "12", value: "IFF" },
  { key: "00", value: "IFF UPDATE" },
];

export const Resolutions: KeyValuePair[] = [
  { key: "lm2.2", value: "COSMO 2.2" },
  { key: "lm5", value: "COSMO 5" },
  { key: "WRF_OL", value: "WRF 1.5" },
  { key: "WRF_DA_ITA", value: " WRF 2.5" },
  { key: "icon", value: "ICON-2I" },
];

export const Platforms: KeyValuePair[] = [
  { key: "G100", value: "G100" },
  { key: "MEUCCI", value: "MEUCCI" },
];

export const Envs: KeyValuePair[] = [
  { key: "PROD", value: "PROD" },
  { key: "DEV", value: "DEVEL" },
];

export const Areas: KeyValuePair[] = [
  { key: "Italia", value: "Italy" },
  { key: "Nord_Italia", value: "Northern Italy" },
  { key: "Centro_Italia", value: "Central Italy" },
  { key: "Sud_Italia", value: "Southern Italy" },
  { key: "Area_Mediterranea", value: "Mediterranean region" },
];
