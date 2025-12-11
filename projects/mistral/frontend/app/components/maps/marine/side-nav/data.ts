import * as L from "leaflet";
export const Variables = {
  dir: { label: "Wave direction", unit: "°" },
  hs: { label: "Significant wave height", unit: "m" },
  t01: { label: "Wave period", unit: "s" },
};
export const MEDITA_BOUNDS = {
  southWest: L.latLng(30 - 3, -7 - 3),
  northEast: L.latLng(46 + 3, 36 + 3),
};

export const Layers = {
  hs: "meteohub:ww3_hs-hs",
  t01: "meteohub:ww3_t01-t01",
};
