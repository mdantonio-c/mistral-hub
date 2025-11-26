import * as L from "leaflet";
export const Variables = {
  dir: { label: "Wave mean direction", unit: "°" },
  hs: { label: "Significant wave height", unit: "m" },
  t01: { label: "Mean period", unit: "s" },
};
export const MEDITA_BOUNDS = {
  southWest: L.latLng(33.69, 2.9875),
  northEast: L.latLng(48.91, 22.0125),
};
