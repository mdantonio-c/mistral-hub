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
        temperature: "Temperatura",
        wind: "Vento",
        precipitation: "Precipitazione",
        snowfall: "Neve",
        clouds: "Copertura Nuvolosa",
        run: "run",
        "reference date": "data",
        pressure: "Pressione",
        "relative humidity": "Umidità Relativa",
        "near surface (%)": "(%)",
        "snow depth": "altezza neve",
        "instant at 2m above the ground": "istantanea a 2m dal suolo",
        "instant at ground": "istantanea al suolo",
        "cumulated at ground on previous 1h": "cumulata 1h (mm)",
        "instant speed and direction at 10m above the ground":
          "velocità media e direzione (m/s)",
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
        "1h precipitation": "Precipitazione oraria",
        "accumulated precipitation": "Precipitazione cumulata",
        "accumulation over 1 hour (mm)": "cumulata 1h (mm)",
        "speed and direction near surface (m/s)":
          "velocità media e direzione (m/s)",
        "speed and direction near surface (km/h)":
          "velocità media e direzione (km/h)",
        "near surface (hPa)": "(hPa)",
        "dates are expressed in local time":
          "le date sono espresse in ora locale",
        "local time": "ora locale",
        "real-time data, not validated": " Dati in tempo reale non validati",
        "scalar field": "Campo scalare",
        total: "Totale",
        "map style": "Stile Mappa",
        "why are some networks missing": "Perchè mancano alcune reti?",
        "given the voluntary nature of participation in the former mistral project, the map does not show data from every regional network. however, work is ongoing to complete the national framework":
          "Data la natura volontaria della partecipazione al progetto Mistral, da cui è derivato questo prodotto, la mappa non mostra i dati di tutte le reti regionali. Sono comunque in corso attività per completare il quadro nazionale",
        networks: "Reti",
        "download data": "Download dati",
        all: "Tutte",
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
