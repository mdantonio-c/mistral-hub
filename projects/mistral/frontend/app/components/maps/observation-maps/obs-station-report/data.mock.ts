import { DataSeries, Observation } from "../../../../types";

/**
 * Custom method to generate random precipitation data
 * @param data
 */
export const randomize = (data: Observation[]) => {
  let obs: Observation = data[0];
  if (obs) {
    obs.prod.forEach((p) => {
      if (p.var === "B13011") {
        p.val.forEach((v) => {
          v.val = Math.floor(Math.random() * 20);
        });
      }
    });
  }
  return data;
};

export const MockStationTimeSeries: DataSeries[] = [
  {
    name: "Global radiation flux (downward)",
    code: "B14198",
    series: [
      { name: "2020-09-07T00:00:00", value: 227 },
      {
        name: "2020-09-07T01:00:00",
        value: -1,
      },
      { name: "2020-09-07T02:00:00", value: -2 },
      {
        name: "2020-09-07T04:00:00",
        value: 0,
      },
      { name: "2020-09-07T05:00:00", value: 1 },
      {
        name: "2020-09-07T06:00:00",
        value: 86,
      },
      { name: "2020-09-07T07:00:00", value: 258 },
    ],
  },
  {
    name: "TEMPERATURE/DRY-BULB TEMPERATURE",
    code: "B12101",
    series: [
      { name: "2020-09-07T00:00:00", value: 297.53 },
      {
        name: "2020-09-07T00:00:00",
        value: 303.45,
      },
      { name: "2020-09-07T00:00:00", value: 291.75 },
      {
        name: "2020-09-07T01:00:00",
        value: 293.75,
      },
      { name: "2020-09-07T01:00:00", value: 294.15 },
      {
        name: "2020-09-07T01:00:00",
        value: 292.95,
      },
      { name: "2020-09-07T01:00:00", value: 293.15 },
      {
        name: "2020-09-07T02:00:00",
        value: 292.65,
      },
      { name: "2020-09-07T02:00:00", value: 293.75 },
      {
        name: "2020-09-07T02:00:00",
        value: 291.85,
      },
      { name: "2020-09-07T02:00:00", value: 292.15 },
      {
        name: "2020-09-07T04:00:00",
        value: 292.25,
      },
      { name: "2020-09-07T04:00:00", value: 292.95 },
      {
        name: "2020-09-07T04:00:00",
        value: 291.05,
      },
      { name: "2020-09-07T04:00:00", value: 291.75 },
      {
        name: "2020-09-07T05:00:00",
        value: 292.05,
      },
      { name: "2020-09-07T05:00:00", value: 292.65 },
      {
        name: "2020-09-07T05:00:00",
        value: 290.65,
      },
      { name: "2020-09-07T05:00:00", value: 292.05 },
      {
        name: "2020-09-07T06:00:00",
        value: 293.45,
      },
      { name: "2020-09-07T06:00:00", value: 294.95 },
      {
        name: "2020-09-07T06:00:00",
        value: 292.15,
      },
      { name: "2020-09-07T06:00:00", value: 294.75 },
      {
        name: "2020-09-07T07:00:00",
        value: 295.85,
      },
      { name: "2020-09-07T07:00:00", value: 297.25 },
      {
        name: "2020-09-07T07:00:00",
        value: 295.05,
      },
      { name: "2020-09-07T07:00:00", value: 295.45 },
    ],
  },
  {
    name: "RELATIVE HUMIDITY",
    code: "B13003",
    series: [
      { name: "2020-09-07T00:00:00", value: 42 },
      {
        name: "2020-09-07T00:00:00",
        value: 62,
      },
      { name: "2020-09-07T00:00:00", value: 29 },
      {
        name: "2020-09-07T01:00:00",
        value: 45,
      },
      { name: "2020-09-07T01:00:00", value: 48 },
      {
        name: "2020-09-07T01:00:00",
        value: 42,
      },
      { name: "2020-09-07T01:00:00", value: 48 },
      {
        name: "2020-09-07T02:00:00",
        value: 51,
      },
      { name: "2020-09-07T02:00:00", value: 53 },
      {
        name: "2020-09-07T02:00:00",
        value: 47,
      },
      { name: "2020-09-07T02:00:00", value: 52 },
      {
        name: "2020-09-07T04:00:00",
        value: 51,
      },
      { name: "2020-09-07T04:00:00", value: 57 },
      {
        name: "2020-09-07T04:00:00",
        value: 49,
      },
      { name: "2020-09-07T04:00:00", value: 54 },
      {
        name: "2020-09-07T05:00:00",
        value: 54,
      },
      { name: "2020-09-07T05:00:00", value: 59 },
      {
        name: "2020-09-07T05:00:00",
        value: 50,
      },
      { name: "2020-09-07T05:00:00", value: 54 },
      {
        name: "2020-09-07T06:00:00",
        value: 54,
      },
      { name: "2020-09-07T06:00:00", value: 57 },
      {
        name: "2020-09-07T06:00:00",
        value: 52,
      },
      { name: "2020-09-07T06:00:00", value: 53 },
      {
        name: "2020-09-07T07:00:00",
        value: 50,
      },
      { name: "2020-09-07T07:00:00", value: 54 },
      {
        name: "2020-09-07T07:00:00",
        value: 46,
      },
      { name: "2020-09-07T07:00:00", value: 53 },
    ],
  },
  {
    name: "TOTAL PRECIPITATION / TOTAL WATER EQUIVALENT",
    code: "B13011",
    series: [
      { name: "2020-09-07T00:15:00", value: 0 },
      {
        name: "2020-09-07T00:30:00",
        value: 0,
      },
      { name: "2020-09-07T00:45:00", value: 0 },
      {
        name: "2020-09-07T01:00:00",
        value: 0,
      },
      { name: "2020-09-07T01:00:00", value: 0 },
      {
        name: "2020-09-07T01:15:00",
        value: 0,
      },
      { name: "2020-09-07T01:30:00", value: 0 },
      {
        name: "2020-09-07T01:45:00",
        value: 0,
      },
      { name: "2020-09-07T02:00:00", value: 0 },
      {
        name: "2020-09-07T02:00:00",
        value: 0,
      },
      { name: "2020-09-07T03:15:00", value: 0 },
      {
        name: "2020-09-07T03:30:00",
        value: 0,
      },
      { name: "2020-09-07T03:45:00", value: 0 },
      {
        name: "2020-09-07T04:00:00",
        value: 0,
      },
      { name: "2020-09-07T04:00:00", value: 0 },
      {
        name: "2020-09-07T04:15:00",
        value: 0,
      },
      { name: "2020-09-07T04:30:00", value: 0 },
      {
        name: "2020-09-07T04:45:00",
        value: 0,
      },
      { name: "2020-09-07T05:00:00", value: 0 },
      {
        name: "2020-09-07T05:00:00",
        value: 0,
      },
      { name: "2020-09-07T05:15:00", value: 0 },
      {
        name: "2020-09-07T05:30:00",
        value: 0,
      },
      { name: "2020-09-07T05:45:00", value: 0 },
      {
        name: "2020-09-07T06:00:00",
        value: 0,
      },
      { name: "2020-09-07T06:00:00", value: 0 },
      {
        name: "2020-09-07T06:15:00",
        value: 0,
      },
      { name: "2020-09-07T06:30:00", value: 0 },
      {
        name: "2020-09-07T06:45:00",
        value: 0,
      },
      { name: "2020-09-07T07:00:00", value: 0 },
      { name: "2020-09-07T07:00:00", value: 0 },
    ],
  },
  {
    name: "PRESSURE",
    code: "B10004",
    series: [
      { name: "2020-09-07T01:00:00", value: 98060 },
      {
        name: "2020-09-07T02:00:00",
        value: 98080,
      },
      { name: "2020-09-07T04:00:00", value: 98060 },
      {
        name: "2020-09-07T05:00:00",
        value: 98130,
      },
      { name: "2020-09-07T06:00:00", value: 98200 },
      { name: "2020-09-07T07:00:00", value: 98250 },
    ],
  },
  {
    name: "WIND SPEED",
    code: "B11002",
    series: [
      { name: "2020-09-07T01:00:00", value: 0 },
      {
        name: "2020-09-07T01:00:00",
        value: 0,
      },
      { name: "2020-09-07T01:00:00", value: 0 },
      {
        name: "2020-09-07T01:00:00",
        value: 0,
      },
      { name: "2020-09-07T02:00:00", value: 0 },
      {
        name: "2020-09-07T02:00:00",
        value: 0,
      },
      { name: "2020-09-07T02:00:00", value: 0 },
      {
        name: "2020-09-07T02:00:00",
        value: 0,
      },
      { name: "2020-09-07T04:00:00", value: 0 },
      {
        name: "2020-09-07T04:00:00",
        value: 0,
      },
      { name: "2020-09-07T04:00:00", value: 0 },
      {
        name: "2020-09-07T04:00:00",
        value: 0,
      },
      { name: "2020-09-07T05:00:00", value: 0 },
      {
        name: "2020-09-07T05:00:00",
        value: 0,
      },
      { name: "2020-09-07T05:00:00", value: 0 },
      {
        name: "2020-09-07T05:00:00",
        value: 0,
      },
      { name: "2020-09-07T06:00:00", value: 0 },
      {
        name: "2020-09-07T06:00:00",
        value: 0,
      },
      { name: "2020-09-07T06:00:00", value: 0 },
      {
        name: "2020-09-07T06:00:00",
        value: 0,
      },
      { name: "2020-09-07T07:00:00", value: 0 },
      {
        name: "2020-09-07T07:00:00",
        value: 0,
      },
      { name: "2020-09-07T07:00:00", value: 0 },
      { name: "2020-09-07T07:00:00", value: 0 },
    ],
  },
  {
    name: "WIND DIRECTION",
    code: "B11001",
    series: [
      { name: "2020-09-07T01:00:00", value: 0 },
      {
        name: "2020-09-07T01:00:00",
        value: 117,
      },
      { name: "2020-09-07T02:00:00", value: 0 },
      {
        name: "2020-09-07T02:00:00",
        value: 358,
      },
      { name: "2020-09-07T04:00:00", value: 144 },
      {
        name: "2020-09-07T05:00:00",
        value: 304,
      },
      { name: "2020-09-07T06:00:00", value: 172 },
      { name: "2020-09-07T07:00:00", value: 120 },
    ],
  },
  {
    name: "MAXIMUM WIND GUST SPEED",
    code: "B11041",
    series: [
      { name: "2020-09-07T01:00:00", value: 0 },
      {
        name: "2020-09-07T02:00:00",
        value: 0,
      },
      { name: "2020-09-07T04:00:00", value: 0 },
      {
        name: "2020-09-07T05:00:00",
        value: 0,
      },
      { name: "2020-09-07T06:00:00", value: 0 },
      { name: "2020-09-07T07:00:00", value: 0 },
    ],
  },
];

export const MockProductTimeSeries: DataSeries[] = [];
