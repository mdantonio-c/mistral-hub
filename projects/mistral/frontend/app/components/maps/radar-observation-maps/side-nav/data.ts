import { GenericArg } from "../../../../types";
import { ValueLabel } from "../../../../types";
import { DatasetProduct as DP } from "../../meteo-tiles/meteo-tiles.config";

export const VARIABLES_CONFIG: GenericArg = {
  sri: [],
  //srt_adj: [1,3,6,12,24]
  //srt_adj: [1]
  srt_adj: [1],
};

export enum Products {
  SRTADJ1 = "Surface Rainfall Total (1h)",
  SRTADJ3 = "SRT ADJ (3h)",
  SRTADJ6 = "SRT ADJ (6h)",
  SRTADJ12 = "SRT ADJ (12h)",
  SRTADJ24 = "SRT ADJ (24h)",
  SRI = "Surface Rainfall Intensity",
}

export const SRT_ADJ_HOURS: ValueLabel[] = [
  { value: 1, label: Products.SRTADJ1 },
  { value: 3, label: Products.SRTADJ3 },
  { value: 6, label: Products.SRTADJ6 },
  { value: 12, label: Products.SRTADJ12 },
  { value: 24, label: Products.SRTADJ24 },
];

export const layerMap = {
  [Products.SRI]: "meteohub:SRI",
  [Products.SRTADJ1]: "meteohub:SRT",
};

export function toLayerCode(title: string): string | null {
  switch (title) {
    case Products.SRTADJ1:
    case Products.SRTADJ3:
    case Products.SRTADJ6:
    case Products.SRTADJ12:
    case Products.SRTADJ24:
      return "srt_adj";
    case Products.SRI:
      return "sri";
    default:
      return null;
  }
}
