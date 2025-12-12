import * as L from "leaflet";
export const Variables = {
  t2m: {
    label: "Temperature",
    descr: "probability distributions weekly averaged",
  },
  tp: {
    label: "Total Precipitation",
    descr: "probability distributions weekly averaged",
  },
};

export const MEDITA_BOUNDS = {
  southWest: L.latLng(30, -7),
  northEast: L.latLng(46, 36),
};

export const Layers = {
  t2m: {
    terzile_1: "meteohub:sub-seasonal-t2m-terzile_1",
    terzile_2: "meteohub:sub-seasonal-t2m-terzile_2",
    terzile_3: "meteohub:sub-seasonal-t2m-terzile_3",
    quintile_1: "meteohub:sub-seasonal-t2m-quintile_1",
    quintile_5: "meteohub:sub-seasonal-t2m-quintile_5",
  },
  tp: {
    terzile_1: "meteohub:sub-seasonal-tp-terzile_1",
    terzile_2: "meteohub:sub-seasonal-tp-terzile_2",
    terzile_3: "meteohub:sub-seasonal-tp-terzile_3",
    quintile_1: "meteohub:sub-seasonal-tp-quintile_1",
    quintile_5: "meteohub:sub-seasonal-tp-quintile_5",
  },
};
export const legendConfig = {
  t2m: "/app/custom/assets/images/legends/subseasonal/temperatura.svg",
  tp: "/app/custom/assets/images/legends/subseasonal/precipitazione.svg",
};
