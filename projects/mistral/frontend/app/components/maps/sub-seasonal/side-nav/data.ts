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
    terzile_1: "meteohub:t2m_terzile_1",
    terzile_2: "meteohub:t2m_terzile_2",
    terzile_3: "meteohub:t2m_terzile_3",
    quintile_1: "meteohub:t2m_quintile_1",
    quintile_5: "meteohub:t2m_quintile_5",
  },
  tp: {
    terzile_1: "meteohub:tp_terzile_1",
    terzile_2: "meteohub:tp_terzile_2",
    terzile_3: "meteohub:tp_terzile_3",
    quintile_1: "meteohub:tp_quintile_1",
    quintile_5: "meteohub:tp_quintile_5",
  },
};
