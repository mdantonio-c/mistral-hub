import { Injectable } from "@angular/core";

export class TranslationSet {
  public language: string;
  public values: { [key: string]: string } = {};
}

@Injectable({
  providedIn: "root",
})
export class TranslationService {
  private dictionary: { [key: string]: TranslationSet } = {
    it: {
      language: "it",
      values: {
        temperature: "temperatura",
        wind: "vento",
        precipitation: "precipitazione",
        "snow fall": "neve",
        clouds: "nuvolosità",
        product: "prodotto",
        "reference date": "data",
        pressure: "pressione",
        "relative humidity": "umidità relativa",
        "instant at 2m above the ground": "istantanea a 2m dal suolo",
        "cumulated at ground on previous 1h": "cumulata al suolo su 1h",
        "instant speed and direction at 10m above the ground":
          "velocità media e direzione istantanea a 10m dal suolo",
      },
    },
  };

  constructor() {}

  translate(key: string, lang = "en"): string {
    if (!key) return;
    if (this.dictionary[lang] != null) {
      key = key.trim().toLowerCase();
      return this.dictionary[lang].values[key];
    }
  }
}
