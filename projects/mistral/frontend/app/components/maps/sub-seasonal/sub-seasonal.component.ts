import { BaseMapComponent } from "../base-map.component";
import { Component, Injector, Input, OnInit } from "@angular/core";
import * as L from "leaflet";
import {
  CARTODB_LICENSE_HREF,
  MISTRAL_LICENSE_HREF,
  OSM_LICENSE_HREF,
  STADIA_LICENSE_HREF,
  ViewModes,
} from "../meteo-tiles/meteo-tiles.config";
import { Params } from "@angular/router";
import * as moment from "moment";
import { Variables, Layers, legendConfig } from "./side-nav/data";
import { TilesService } from "../meteo-tiles/services/tiles.service";
import { environment } from "@rapydo/../environments/environment";
@Component({
  selector: "app-sub-seasonal",
  templateUrl: "./sub-seasonal.component.html",
  styleUrls: ["./sub-seasonal.component.scss"],
})
export class SubSeasonalComponent extends BaseMapComponent implements OnInit {
  @Input() minZoom: number = 4;
  @Input() maxZoom: number = 7;

  selectedWeek;
  selectedLayer;
  wmsPath;
  run;
  weekList = [];
  bounds = new L.LatLngBounds(new L.LatLng(25, -20), new L.LatLng(55, 50));
  private maps_url: string = "";
  private legendControl;
  constructor(injector: Injector, private tileService: TilesService) {
    super(injector);
    this.options["layers"] = [this.LAYER_LIGHTMATTER];
    this.wmsPath = this.tileService.getWMSUrl();
    this.selectedLayer = Variables[Object.keys(Variables)[0]].label;
    this.maps_url = environment.CUSTOM.MAPS_URL;
  }

  options = {
    zoomControl: false,
    // center: L.latLng([41.3, 12.5]),
    // maxBoundsViscosity: 1.0,
    maxBounds: this.bounds,
    minZoom: this.minZoom,
    maxZoom: this.maxZoom,
    timeDimension: false,
    timeDimensionControl: false,
  };

  LAYER_LIGHTMATTER = L.tileLayer(
    "https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}{r}.png",
    {
      id: "mapbox.light",
      attribution: `&copy; ${CARTODB_LICENSE_HREF} | &copy; ${MISTRAL_LICENSE_HREF}`,
      maxZoom: this.maxZoom,
      minZoom: this.minZoom,
    },
  );

  layersControl = {
    baseLayers: {
      "Carto Map Light": this.LAYER_LIGHTMATTER,
    },
  };

  protected centerMap() {
    if (this.map) {
      //const mapCenter = super.getMapCenter();
      // map center for ICON
      const mapCenter = L.latLng(45, 12.5);
      this.map.fitBounds(this.bounds);
      this.map.setZoom(this.minZoom + 1);
    }
  }
  public receiveWeek(week: string) {
    console.log("week", week);
    this.selectedWeek = week;
    this.toggleLayer(this.selectedLayer, true);
  }
  protected onMapReady(map: L.Map) {
    this.map = map;
    setTimeout(() => {
      this.map.invalidateSize(true);
      this.map.setView([41.3, 12.5], 5);
    }, 200);
    //this.centerMap();
    this.addIBorderLayer(map);
  }

  ngOnInit(): void {
    super.ngOnInit();
    this.loadWeeks();
    this.route.queryParams.subscribe((params: Params) => {
      const lang = params["lang"];
      if (["it", "en"].includes(lang)) {
        this.lang = lang;
      }
    });
  }
  public printDatasetDescription(): string {
    return "Sub-seasonal";
  }
  public printVarDescSupport(layerId: string): string {
    return "";
  }
  public printDatasetProduct(): string {
    return "";
  }
  protected toggleLayer(obj, receiveWeek: boolean = false) {
    if (!receiveWeek) this.selectedLayer = Variables[obj].label;
    else this.selectedLayer = obj;
    if (this.map.hasLayer(this.layersControl["overlays"])) {
      this.map.removeLayer(this.layersControl["overlays"]);
    }
    const key = Object.keys(Variables).find(
      (k) => Variables[k].label === this.selectedLayer,
    );
    const date = this.extractAndFormatDate(this.selectedWeek);
    this.addLayerGroup(key, date);
    this.layersControl["overlays"].addTo(this.map);
    this.updateLegends(key);
  }
  public printReferenceDate() {
    return "";
  }

  getTileWms(layerId: string, time: string) {
    return L.tileLayer.wms(this.wmsPath, {
      layers: layerId,
      transparent: true,
      format: "image/png",
      tileSize: 1024,
      time: time,
    } as any);
  }
  public loadWeeks(reload: boolean = false) {
    const readyFileName = "READY.json";
    fetch(`${this.maps_url}/api/sub-seasonal/status`)
      .then((response) => response.json())
      .then((data) => {
        const from = new Date(data.from);
        const to = new Date(data.to);
        this.run = `${data.run.slice(6, 8)}-${data.run.slice(
          4,
          6,
        )}-${data.run.slice(0, 4)}`;
        this.weekList = this.getWeeksBetween(from, to);
        this.afterWeeksLoaded();
      });
  }
  private getWeeksBetween(from: Date, to: Date): string[] {
    const format = (d: Date) =>
      `${String(d.getDate()).padStart(2, "0")}/${String(
        d.getMonth() + 1,
      ).padStart(2, "0")}/${d.getFullYear()}`;

    const weeks: string[] = [];

    let current = new Date(from);

    while (current <= to) {
      const start = new Date(current);
      const end = new Date(current);
      end.setDate(end.getDate() + 6);

      weeks.push(`${format(start)} - ${format(end)}`);
      current.setDate(current.getDate() + 7);
    }

    return weeks;
  }

  private afterWeeksLoaded() {
    if (!this.map) return;
    const key = Object.keys(Variables).find(
      (k) => Variables[k].label === this.selectedLayer,
    );
    const firstWeekDate = this.extractAndFormatDate(this.weekList[0]);
    this.selectedWeek = this.weekList[0];
    this.addLayerGroup(key, firstWeekDate);
    this.layersControl["overlays"].addTo(this.map);
    this.updateLegends(key);
  }
  private extractAndFormatDate(rangeString) {
    const firstPart = rangeString.split(" - ")[0];
    const [day, month, year] = firstPart.split("/");
    return `${year}-${month}-${day}`;
  }

  private addLayerGroup(key, date) {
    const terzile1 = this.getTileWms(Layers[key].terzile_1, date).setOpacity(
      0.6,
    );
    const terzile2 = this.getTileWms(Layers[key].terzile_2, date).setOpacity(
      0.6,
    );
    const terzile3 = this.getTileWms(Layers[key].terzile_3, date).setOpacity(
      0.6,
    );
    const quintile1 = this.getTileWms(Layers[key].quintile_1, date).setOpacity(
      0.6,
    );
    const quintile5 = this.getTileWms(Layers[key].quintile_5, date).setOpacity(
      0.6,
    );
    const layerGroup = L.layerGroup([
      terzile1,
      terzile2,
      terzile3,
      quintile1,
      quintile5,
    ]);
    this.layersControl["overlays"] = layerGroup;
  }

  private addIBorderLayer(map: L.Map) {
    fetch("./app/custom/assets/images/geoJson/confini_mediterraneo.geojson")
      .then((response) => response.json())
      .then((data) => {
        L.geoJSON(data, {
          style: {
            color: "black",
            weight: 1,
            opacity: 1,
          },
        }).addTo(map);
      });
  }

  private addLegendSvg(svgPath: string) {
    if (!this.map) return;
    if (this.legendControl) this.legendControl.remove();
    this.legendControl = new L.Control({ position: "bottomleft" });
    this.legendControl.onAdd = () => {
      let div = L.DomUtil.create("div");
      div.style.clear = "unset";
      div.innerHTML += `<img class="legenda" src="${svgPath}">`;
      return div;
    };
    this.legendControl.addTo(this.map);
  }

  private updateLegends(layerId: string) {
    const config = legendConfig[layerId];
    if (!config) return;
    this.addLegendSvg(config);
  }
}
