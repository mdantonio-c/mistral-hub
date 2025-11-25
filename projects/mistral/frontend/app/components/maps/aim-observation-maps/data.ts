export const COLOR_RANGES = {
  snow: [
    { min: 200 / 100, color: "#281521", textColor: "#fff" },
    { min: 150 / 100, color: "#361B2C", textColor: "#fff" },
    { min: 100 / 100, color: "#512942", textColor: "#fff" },
    { min: 75 / 100, color: "#6D3758", textColor: "#fff" },
    { min: 50 / 100, color: "#88446E", textColor: "#fff" },
    { min: 40 / 100, color: "#A35282", textColor: "#fff" },
    { min: 30 / 100, color: "#BB77A0", textColor: "#fff" },
    { min: 20 / 100, color: "#CFA0BD", textColor: null },
    { min: 15 / 100, color: "#DDBBCF", textColor: null },
    { min: 10 / 100, color: "#EAD7E1", textColor: null },
    { min: 5 / 100, color: "#F8F2F5", textColor: null },
    { min: -50 / 100, color: "#FFFFFF", textColor: null },
  ],
  t2m: [
    { min: 319.15, color: "#FFDCDC", textColor: null }, // 46
    { min: 317.15, color: "#FFB4B4", textColor: null }, // 44
    { min: 315.15, color: "#F0A0A0", textColor: null }, // 42
    { min: 313.15, color: "#B46464", textColor: "#fff" }, // 40
    { min: 311.15, color: "#640000", textColor: "#fff" }, // 38
    { min: 309.15, color: "#7C0000", textColor: "#fff" }, // 36
    { min: 307.15, color: "#AF0F14", textColor: "#fff" }, // 34
    { min: 305.15, color: "#C41A0A", textColor: "#fff" }, // 32
    { min: 303.15, color: "#E83709", textColor: "#fff" }, // 30
    { min: 301.15, color: "#F46D0B", textColor: "#fff" }, // 28
    { min: 299.15, color: "#F4880B", textColor: null }, // 26
    { min: 297.15, color: "#F4BD0B", textColor: null }, // 24
    { min: 295.15, color: "#F4D90B", textColor: null }, // 22
    { min: 293.15, color: "#F3FB01", textColor: null }, // 20
    { min: 291.15, color: "#CEF003", textColor: null }, // 18
    { min: 289.15, color: "#9CE106", textColor: null }, // 16
    { min: 287.15, color: "#52CA0B", textColor: null }, // 14
    { min: 285.15, color: "#21BB0E", textColor: "#fff" }, // 12
    { min: 283.15, color: "#07A127", textColor: "#fff" }, // 10
    { min: 281.15, color: "#62AF88", textColor: "#fff" }, // 8
    { min: 279.15, color: "#87D3AB", textColor: null }, // 6
    { min: 277.15, color: "#9FEEC8", textColor: null }, // 4
    { min: 275.15, color: "#BBFFE2", textColor: null }, // 2
    { min: 273.15, color: "#85C8FF", textColor: null }, // 0
    { min: 271.15, color: "#5bb4ff", textColor: "#fff" }, // -2
    { min: 269.15, color: "#0082EF", textColor: "#fff" }, // -4
    { min: 267.15, color: "#0070cc", textColor: "#fff" }, // -6
    { min: 265.15, color: "#0062af", textColor: "#fff" }, // -8
    { min: 263.15, color: "#00528f", textColor: "#fff" }, // -10
    { min: 261.15, color: "#003C7F", textColor: "#fff" }, // -12
    { min: 259.15, color: "#00277A", textColor: "#fff" }, // -14
    { min: 257.15, color: "#002066", textColor: "#fff" }, // -16
    { min: 255.15, color: "#f862f1", textColor: "#fff" }, // -18
    { min: 253.15, color: "#f627eb", textColor: "#fff" }, // -20
    { min: 251.15, color: "#d41dd1", textColor: "#fff" }, // -22
    { min: 249.15, color: "#b000e0", textColor: "#fff" }, // -24
    { min: 247.15, color: "#8000a3", textColor: "#fff" }, // -26
    { min: 245.15, color: "#57007f", textColor: "#fff" }, // -28
    { min: 243.15, color: "#3e007f", textColor: "#fff" }, // -30
    { min: Infinity, color: "#64007F", textColor: "#fff" },
  ],
  prp: [
    { min: 300, color: "#703f78", textColor: null },
    { min: 200, color: "#9f5fab", textColor: null },
    { min: 100, color: "#B887C0", textColor: null },
    { min: 75, color: "#D6A1CC", textColor: null },
    { min: 50, color: "#E7BDDA", textColor: null },
    { min: 40, color: "#E57D9A", textColor: null },
    { min: 30, color: "#DA4C4D", textColor: null },
    { min: 20, color: "#EE5A5C", textColor: null },
    { min: 15, color: "#F6A15C", textColor: null },
    { min: 10, color: "#FCD48E", textColor: null },
    { min: 8, color: "#FFE073", textColor: null },
    { min: 6, color: "#FDFD81", textColor: null },
    { min: 5, color: "#FFFFC6", textColor: null },
    { min: 4, color: "#F2F2A0", textColor: null },
    { min: 3, color: "#D2EBA3", textColor: null },
    { min: 2, color: "#C2E5D7", textColor: null },
    { min: 1, color: "#C7E7EF", textColor: null },
    { min: 0.1, color: "#CFEAF6", textColor: null },
    { min: 0, color: "#E7EFF2", textColor: null },
  ],
  rh: [
    { min: 90, color: "#1000FD", textColor: "#fff" },
    { min: 80, color: "#21FEFF", textColor: null },
    { min: 60, color: "#19FF24", textColor: null },
    { min: 40, color: "#FEFF27", textColor: null },
    { min: 20, color: "#FE8A12", textColor: null },
    { min: 0, color: "#FD1506", textColor: null },
  ],
  ws10m: [
    { min: 50, color: "#ff00c3", textColor: null },
    { min: 30, color: "#ee82ee", textColor: null },
    { min: 20, color: "#ff3333", textColor: null },
    { min: 10, color: "#FFDB58", textColor: null },
    { min: 5, color: "#4bcf4f", textColor: null },
    { min: 2, color: "#7070ff", textColor: null },
    { min: 1, color: "#8bd8f9", textColor: null },
    { min: 0, color: "#D0E6F1", textColor: null },
  ],
};
