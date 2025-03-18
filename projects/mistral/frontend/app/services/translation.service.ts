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
        product: "run",
        "reference date": "data",
        pressure: "pressione",
        "relative humidity": "umidità relativa",
        "instant at 2m above the ground": "istantanea a 2m dal suolo",
        "instant at ground": "istantanea al suolo",
        "cumulated at ground on previous 1h": "cumulata al suolo su 1h",
        "instant speed and direction at 10m above the ground":
          "velocità media e direzione istantanea a 10m dal suolo",
        station: "Stazione",
        "station details": "Dettagli della stazione",
        // station parameters
        "long station or site name": "Nome della stazione o nome del sito",
        "report mnemonic": "Nome della rete",
        latitude: "Latitudine",
        longitude: "Longitudine",
        "height of station ground above mean sea level":
          "Altezza della stazione sul livello del mare",
        "height of barometer above mean sea level":
          "Altezza del barometro sul livello del mare",
        // meteograms parameters
        "temperature/dry-bulb temperature": "Temperatura",
        "total precipitation / total water equivalent": "Precipitazione",
        "wind direction": "Vento: direzione",
        "wind speed": "Vento: velocità",
        // levels and timeranges
        level: "Livello",
        "2.000m above ground": "2m dal suolo",
        "ground or water surface": "Livello del suolo o superficie dell'acqua",
        "10.000m above ground": "10m dal suolo",
        "analysis or observation, istantaneous value":
          "Analisi o osservazione istantanea",
        "accumulation over 1h at forecast time 0": "Cumulato su 1h",
        "accumulated data": "Dato cumulato",
        "accumulated precipitation over 1h": "Precipitazione cumulata su 1h",
        "dates are expressed in local time":
          "le date sono espresse in ora locale",
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
