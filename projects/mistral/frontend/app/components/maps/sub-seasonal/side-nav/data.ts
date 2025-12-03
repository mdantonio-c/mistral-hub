import * as L from "leaflet";
export const Variables = {
  t2m: {
    label: "2m Temperature",
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
