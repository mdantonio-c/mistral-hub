import { GenericArg } from "../../../../types";

export interface LegendConfig {
  id: string;
  title: string;
  legend_type: string;
  colors: string[];
  labels: string[];
}

export const LEGEND_DATA: LegendConfig[] = [
  {
    id: "tm2",
    legend_type: "legend_t2m",
    title: "T [°C]",
    colors: [
      "#ff9900",
      "#ffcc00",
      "#7200ff",
      "#bf00ff",
      "#ff00ff",
      "#cc00cc",
      "#990099",
      "#660066",
      "#660000",
      "#990000",
      "#cc0000",
      "#ff0000",
      "#ff6600",
      "#ff9900",
      "#ffcc00",
      "#ffff00",
      "#cce500",
      "#7fcc00",
      "#00b200",
      "#00cc7f",
      "#00e5cc",
      "#00ffff",
      "#00bfff",
      "#008cff",
      "#0059ff",
      "#0000ff",
      "#7200ff",
      "#bf00ff",
      "#ff00ff",
      "#cc00cc",
      "#990099",
      "#660066",
      "#660000",
      "#990000",
      "#cc0000",
      "#ff0000",
      "#ff6600",
      "#ff9900",
      "#ffcc00",
    ],
    labels: [
      "46",
      " ",
      "42",
      " ",
      "38",
      " ",
      "34",
      " ",
      "30",
      " ",
      "26",
      " ",
      "22",
      "",
      "18",
      " ",
      "14",
      " ",
      "10",
      " ",
      "6",
      " ",
      "2",
      " ",
      "-2",
      " ",
      "-6",
      " ",
      "-10",
      " ",
      "-14",
      " ",
      "-18",
      "",
      "-22",
      " ",
      "-26",
      " ",
      "-30",
    ],
  },
  {
    id: "ws10m",
    legend_type: "legend_ws",
    title: "WS [m/s]",
    colors: [
      "rgba(192,0,128.0,1.000)",
      "rgba(188,4,130.6,0.983)",
      "rgba(184,8,133.3,0.967)",
      "rgba(180,12,135.9,0.950)",
      "rgba(176,16,138.6,0.933)",
      "rgba(172,20,141.2,0.917)",
      "rgba(168,24,143.9,0.900)",
      "rgba(164,28,146.5,0.883)",
      "rgba(160,32,149.2,0.867)",
      "rgba(156,36,151.8,0.850)",
      "rgba(152,40,154.5,0.833)",
      "rgba(148,44,157.1,0.817)",
      "rgba(144,48,159.8,0.800)",
      "rgba(140,52,162.4,0.783)",
      "rgba(136,56,165.0,0.767)",
      "rgba(132,60,167.7,0.750)",
      "rgba(128,64,170.3,0.733)",
      "rgba(124,68,173.0,0.717)",
      "rgba(120,72,175.6,0.700)",
      "rgba(116,76,178.3,0.683)",
      "rgba(112,80,180.9,0.667)",
      "rgba(108,84,183.6,0.650)",
      "rgba(104,88,186.2,0.633)",
      "rgba(100,92,188.9,0.617)",
      "rgba(96,96,191.5,0.600)",
      "rgba(92,100,194.1,0.583)",
      "rgba(88,104,196.8,0.567)",
      "rgba(84,108,199.4,0.550)",
      "rgba(80,112,202.1,0.533)",
      "rgba(76,116,204.7,0.517)",
      "rgba(72,120,207.4,0.500)",
      "rgba(68,124,210.0,0.483)",
      "rgba(64,128,212.7,0.467)",
      "rgba(60,132,215.3,0.450)",
      "rgba(56,136,218.0,0.433)",
      "rgba(52,140,220.6,0.417)",
      "rgba(48,144,223.3,0.400)",
      "rgba(44,148,225.9,0.383)",
      "rgba(40,152,228.5,0.367)",

      // "rgba(36,156,231.2,0.350)",
      // "rgba(32,160,233.8,0.333)","rgba(28,164,236.5,0.317)","rgba(24,168,239.1,0.300)","rgba(20,172,241.8,0.283)",
      // "rgba(16,176,244.4,0.267)","rgba(12,180,247.1,0.250)","rgba(8,184,249.7,0.233)","rgba(4,188,252.4,0.217)",
      // "rgba(0,192,255.0,0.200)",
    ],
    labels: [
      "42.0",
      " ",
      "40.0",
      " ",
      "38.0",
      " ",
      "36.0",
      " ",
      "34.0",
      " ",
      "32.0",
      " ",
      "30.0",
      " ",
      "28.0",
      " ",
      "26.0",
      " ",
      "24.0",
      " ",
      "22.0",
      " ",
      "20.0",
      " ",
      "18.0",
      " ",
      "16.0",
      " ",
      "14.0",
      " ",
      "12.0",
      " ",
      "10.0",
      // " ","8.0"," ","6.0"," ","4.0"," ","2.0"," ","0.0",

      // "0.0"," ","2.0","","4.0","","6.0","","8.0","","10.0",
      // " ","12.0"," ","14.0"," ","16.0"," ","18.0"," ","20.0", " ",
      // "22.0","","24.0","","26.0","","28.0","","30.0","","32.0",
      // "","34.0","","36.0","","38.0","","40.0","","42.0",],
    ],
  },
  {
    id: "rh",
    legend_type: "legend_rh",
    title: "RH [%]",
    colors: ["blue", "cyan", "green", "yellow", "orange", "red"],
    labels: ["110", "100", "90", "80", "70", "60"],
  },
  {
    id: "pmsl",
    legend_type: "legend_pmsl",
    title: "",
    colors: [],
    labels: [],
  },
  {
    id: "tcc",
    legend_type: "legend_cc",
    title: "T-C [%]",
    colors: [
      "rgba(192.0,192.0,192.0,0.7)",
      "rgba(198.3,198.3,198.3,0.63)",
      "rgba(204.6,204.6,204.6,0.56)",
      "rgba(210.9,210.9,210.9,0.49)",
      "rgba(217.2,217.2,217.2,0.42)",
      "rgba(223.5,223.5,223.5,0.35)",
      // "rgba(229.8,229.8,229.8,0.28)","rgba(236.1,236.1,236.1,0.21)",
      // "rgba(242.4,242.4,242.4,0.14)","rgba(248.7,248.7,248.7,0.07)","rgba(255.0,255.0,2550.0,0)"
    ],
    labels: [
      "100",
      "90",
      "80",
      "70",
      "60",
      "50",
      // "40","30","20","10","0"
    ],
  },
  {
    id: "hcc",
    legend_type: "legend_cc",
    title: "H-C [%]",
    colors: [
      "rgba(0,188,0,0.4)",
      "rgba(0,188,0,0.32)",
      "rgba(0,188,0,0.24)",
      "rgba(0,188,0,0.16)",
      "rgba(0,188,0,0.08)",
      "rgba(0,188,0,0.0)",
    ],
    labels: ["100", "90", "80", "70", "60", "50"],
  },
  {
    id: "mcc",
    legend_type: "legend_cc",
    title: "M-C [%]",
    colors: [
      "rgba(0,0,255,0.4)",
      "rgba(0,0,255,0.32)",
      "rgba(0,0,255,0.24)",
      "rgba(0,0,255,0.16)",
      "rgba(0,0,255,0.08)",
      "rgba(0,0,255,0.0)",
    ],
    labels: ["100", "90", "80", "70", "60", "50"],
  },
  {
    id: "lcc",
    legend_type: "legend_cc",
    title: "L-C [%]",
    colors: [
      "rgba(255,0,0,0.2)",
      "rgba(255,0,0,0.16)",
      "rgba(255,0,0,0.12)",
      "rgba(255,0,0,0.08)",
      "rgba(255,0,0,0.04)",
      "rgba(255,0,0,0.0)",
    ],
    labels: ["100", "90", "80", "70", "60", "50"],
  },
  {
    id: "prp",
    legend_type: "legend_prec",
    title: "Prp [mm]",
    colors: [
      "rgba(0,153,255,1)",
      "rgba(153,153,255,0.95)",
      "rgba(191,128,217,0.9)",
      "rgba(217,140,217,0.85)",
      "rgba(242,166,242,0.8)",
      "rgba(223,83,121, 0.75)",
      "rgba(204,0,0, 0.7)",
      "rgba(255,0,0, 0.65)",
      "rgba(255,115,0, 0.65)",
      "rgba(255,185,67, 0.6)",
      "rgba(255,200,0, 0.55)",
      "rgba(255,255,0, 0.5)",
      "rgba(255,255,128, 0.45)",
      "rgba(225, 227, 22, 0.40)",
      "rgba(128, 255, 0, 0.35)",
      "rgba(48, 196, 135, 0.30)",
      "rgba(0,255,255,0.25)",
      "rgba(0,204,255,0.2)",
    ],
    labels: [
      "300",
      "200",
      "100",
      "75",
      "50",
      "40",
      "30",
      "25",
      "20",
      "15",
      "10",
      "8",
      "6",
      "5",
      "4",
      "3",
      "2",
      "1",
    ],
  },
  {
    id: "sf",
    legend_type: "legend_sf",
    title: "Snow [cm]",
    colors: [
      "rgba(0,255,255,0.25)",
      "rgba(0,204,255,0.2)",
      "rgba(0,153,255,1)",
      "rgba(153,153,255,0.95)",
      "rgba(191,128,217,0.9)",
      "rgba(217,140,217,0.85)",
      "rgba(242,166,242,0.8)",
      "rgba(223,83,121, 0.75)",
      "rgba(204,0,0, 0.7)",
      "rgba(255,0,0, 0.65)",
      "rgba(255,115,0, 0.65)",
      "rgba(255,185,67, 0.6)",
      "rgba(255,200,0, 0.55)",
      "rgba(255,255,0, 0.5)",
      "rgba(255,255,128, 0.45)",
      "rgba(225, 227, 22, 0.40)",
      "rgba(128, 255, 0, 0.35)",
      "rgba(48, 196, 135, 0.30)",
      "rgba(0,255,255,0.25)",
      "rgba(0,204,255,0.2)",
    ],
    labels: [
      "80",
      "60",
      "50",
      "40",
      "30",
      "25",
      "20",
      "15",
      "10",
      "7.5",
      "5",
      "4",
      "3",
      "2.5",
      "2",
      "1.5",
      "1",
      "0.5",
      "0.25",
      "0.1",
    ],
  },
  {
    id: "tpperc",
    legend_type: "legend_tpperc",
    title: "PRP PERC [mm]",
    colors: [
      "rgb(115,115,115)",
      "rgb(11,11,110)",
      "rgb(10,10,214)",
      "rgb(94,74,232)",
      "rgb(161,2,235)",
      "rgb(217,1,255)",
      "red",
      "rgb(255,125,1)",
      "rgb(255,186,1)",
      "rgb(227,227,17)",
      "rgb(230,255,102)",
      "rgb(153,232,15)",
      "rgb(135,204,33)",
      "rgb(18,217,156)",
      "rgb(115,237,199)",
      "rgb(191,242,237)",
    ],
    labels: [
      "10000",
      "500",
      "300",
      "200",
      "150",
      "125",
      "100",
      "80",
      "60",
      "50",
      "40",
      "30",
      "20",
      "10",
      "5",
      "2",
      "0.5",
    ],
  },
  {
    id: "tpprob",
    legend_type: "legend_tpprob",
    title: "PRP PROB [%]",
    colors: [
      "rgb(255,0,0)",
      "rgb(255,117,20)",
      "rgb(255,255,0)",
      "rgb(204,255,0)",
      "rgb(102,255,0)",
      "rgb(0,255,0)",
      "rgb(127,255,212)",
      "rgb(0,255,255)",
      "rgb(0,127,255)",
      "rgb(0,0,255)",
    ],
    labels: ["105", "90", "80", "70", "60", "50", "40", "30", "20", "10", "2"],
  },
];

export const VARIABLES_CONFIG: GenericArg = {
  t2m: [],
  prs: [],
  rh: [],
  ws10m: [],
  prp: [1, 3, 6, 12, 24],
  sf: [1, 3, 6, 12, 24],
  cc: ["low", "medium", "high"],
  tpperc: [1, 10, 25, 50, 70, 75, 80, 90, 95, 99],
  tpprob: [5, 10, 20, 50],
};

export const VARIABLES_CONFIG_BASE: GenericArg = {
  t2m: [],
  ws10m: [],
  prp: [3, 6, 12, 24],
  sf: [3, 6],
  cc: [],
};

export const VARIABLES_CONFIG_OBS: GenericArg = {
  t2m: {
    label: "temperature",
    desc: "instant at 2m above the ground",
    code: "B12101",
    timerange: "254,0,0",
    level: "103,2000,0,0",
    value: [],
    order: 1,
  },
  prp: {
    label: "precipitation",
    desc: "cumulated at ground on previous 1h",
    code: "B13011",
    timerange: "1,0,3600",
    level: "1,0,0,0",
    value: [],
    order: 4,
  },
  /*sf: {
    label: "snow fall",
    code: "",
    value: []
  },*/
  ws10m: {
    label: "wind",
    desc: "instant speed and direction at 10m above the ground",
    code: "B11002 or B11001",
    timerange: "254,0,0",
    level: "103,10000,0,0",
    value: [],
    order: 5,
  },
  rh: {
    label: "relative humidity",
    desc: "instant at 2m above the ground",
    code: "B13003",
    timerange: "254,0,0",
    level: "103,2000,0,0",
    value: [],
    order: 3,
  },
  prs: {
    label: "pressure",
    desc: "instant at ground",
    code: "B10004",
    timerange: "254,0,0",
    level: "1,0,0,0",
    value: [],
    order: 2,
  },
};
