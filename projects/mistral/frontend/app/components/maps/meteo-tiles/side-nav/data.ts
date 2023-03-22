import { DatasetProduct as DP } from "../meteo-tiles.config";
import { ValueLabel } from "../../../../types";

export const PRECIPITATION_HOURS: ValueLabel[] = [
  { value: 1, label: DP.PREC1P },
  { value: 3, label: DP.PREC3P },
  { value: 6, label: DP.PREC6P },
  { value: 12, label: DP.PREC12P },
  { value: 24, label: DP.PREC24P },
];
export const SNOW_HOURS: ValueLabel[] = [
  { value: 1, label: DP.SF1 },
  { value: 3, label: DP.SF3 },
  { value: 6, label: DP.SF6 },
  { value: 12, label: DP.SF12 },
  { value: 24, label: DP.SF24 },
];
export const CLOUD_LEVELS: ValueLabel[] = [
  { value: "low", label: DP.LCC },
  { value: "medium", label: DP.MCC },
  { value: "high", label: DP.HCC },
  /*{ value: "total", label: DP.TCC }*/
];
export const IFF_PERCENTILES: ValueLabel[] = [
  { value: 1, label: DP.TPPERC1 },
  { value: 10, label: DP.TPPERC10 },
  { value: 25, label: DP.TPPERC25 },
  { value: 50, label: DP.TPPERC50 },
  { value: 70, label: DP.TPPERC70 },
  { value: 75, label: DP.TPPERC75 },
  { value: 80, label: DP.TPPERC80 },
  { value: 90, label: DP.TPPERC90 },
  { value: 95, label: DP.TPPERC95 },
  { value: 99, label: DP.TPPERC99 },
];
export const IFF_PROBABILITIES: ValueLabel[] = [
  { value: 5, label: DP.TPPROB5 },
  { value: 10, label: DP.TPPROB10 },
  { value: 20, label: DP.TPPROB20 },
  { value: 50, label: DP.TPPROB50 },
];

/**
 * Custom mapper for overlay titles into component codes
 * @param title
 */
export function toLayerCode(title: string): string | null {
  switch (title) {
    case DP.TM2:
      return "t2m";
    case DP.PMSL:
      return "prs";
    case DP.RH:
      return "rh";
    case DP.WIND10M:
      return "ws10m";
    case DP.PREC1P:
    case DP.PREC3P:
    case DP.PREC6P:
    case DP.PREC12P:
    case DP.PREC24P:
      return "prp";
    case DP.SF1:
    case DP.SF3:
    case DP.SF6:
    case DP.SF12:
    case DP.SF24:
      return "sf";
    case DP.LCC:
    case DP.MCC:
    case DP.HCC:
    case DP.TCC:
      return "cc";
    case DP.TPPERC1:
    case DP.TPPERC10:
    case DP.TPPERC25:
    case DP.TPPERC50:
    case DP.TPPERC70:
    case DP.TPPERC75:
    case DP.TPPERC80:
    case DP.TPPERC90:
    case DP.TPPERC95:
    case DP.TPPERC99:
      return "tpperc";
    case DP.TPPROB5:
    case DP.TPPROB10:
    case DP.TPPROB20:
    case DP.TPPROB50:
      return "tpprob";
    default:
      return null;
  }
}

export function toLayerTitle(
  code: string,
  lvl: string | number | null = null,
): string | null {
  if (lvl) {
    lvl = `${lvl}`;
  }
  switch (code) {
    case "t2m":
      return DP.TM2;
    case "prs":
      return DP.PMSL;
    case "rh":
      return DP.RH;
    case "prp":
      switch (lvl) {
        case "1":
          return DP.PREC1P;
        case "3":
          return DP.PREC3P;
        case "6":
          return DP.PREC6P;
        case "12":
          return DP.PREC12P;
        case "24":
          return DP.PREC24P;
      }
      return DP.PREC1P;
    case "sf":
      switch (lvl) {
        case "1":
          return DP.SF1;
        case "3":
          return DP.SF3;
        case "6":
          return DP.SF6;
        case "12":
          return DP.SF12;
        case "24":
          return DP.SF24;
      }
      return DP.SF1;
    case "cc":
      switch (lvl) {
        case "low":
          return DP.LCC;
        case "medium":
          return DP.MCC;
        case "high":
          return DP.HCC;
        case "total":
          return DP.TCC;
      }
      return DP.LCC;
    case "tpperc":
      switch (lvl) {
        case "1":
          return DP.TPPERC1;
        case "10":
          return DP.TPPERC10;
        case "25":
          return DP.TPPERC25;
        case "50":
          return DP.TPPERC50;
        case "24":
          return DP.TPPERC70;
        case "75":
          return DP.TPPERC75;
        case "80":
          return DP.TPPERC80;
        case "90":
          return DP.TPPERC90;
        case "95":
          return DP.TPPERC95;
        case "99":
          return DP.TPPERC99;
      }
      return DP.TPPERC25;
    case "tpprob":
      switch (lvl) {
        case "1":
          return DP.TPPROB5;
        case "10":
          return DP.TPPROB10;
        case "25":
          return DP.TPPROB20;
        case "50":
          return DP.TPPROB50;
      }
      return DP.TPPROB20;
    default:
      return null;
  }
}
