import {
  Component,
  Input,
  ViewEncapsulation,
  Output,
  EventEmitter,
  ViewChild,
  HostListener,
  ContentChild,
  TemplateRef,
} from "@angular/core";

import { curveLinear } from "d3-shape";
import { scaleBand, scaleLinear, scalePoint, scaleTime } from "d3-scale";

import {
  BaseChartComponent,
  LineSeriesComponent,
  ViewDimensions,
  ColorHelper,
  calculateViewDimensions,
  ScaleType,
  Orientation,
  Color,
} from "@swimlane/ngx-charts";

@Component({
  selector: "combo-chart-wind-component",
  templateUrl: "./combo-chart-wind.component.html",
  styleUrls: ["./combo-chart-wind.component.scss"],
  encapsulation: ViewEncapsulation.None,
})
export class BubbleLineChartComponent extends BaseChartComponent {
  @Input() curve: any = curveLinear;
  @Input() legend = false;
  @Input() legendTitle: string = "Legend";
  @Input() legendPosition: string = "right";
  @Input() xAxis;
  @Input() yAxis;
  @Input() showXAxisLabel;
  @Input() showYAxisLabel;
  @Input() xAxisLabel;
  @Input() yAxisLabel;
  @Input() tooltipDisabled: boolean = false;
  @Input() gradient: boolean;
  @Input() showGridLines: boolean = true;
  @Input() activeEntries: any[] = [];
  @Input() schemeType: ScaleType;
  @Input() xAxisTickFormatting: any;
  @Input() yAxisTickFormatting: any;
  @Input() roundDomains: boolean = false;
  @Input() colorSchemeLine: Color;
  @Input() autoScale;
  @Input() lineChart: any;
  @Input() yLeftAxisScaleFactor: any;
  @Input() rangeFillOpacity: number;
  @Input() animations: boolean = true;
  @Input() gridLineNgStyleByXAxisTick;

  @Output() activate: EventEmitter<any> = new EventEmitter();
  @Output() deactivate: EventEmitter<any> = new EventEmitter();

  @ContentChild("tooltipTemplate") tooltipTemplate: TemplateRef<any>;
  @ContentChild("seriesTooltipTemplate")
  seriesTooltipTemplate: TemplateRef<any>;

  @ViewChild(LineSeriesComponent) lineSeriesComponent: LineSeriesComponent;

  dims: ViewDimensions;
  xScale: any;
  yScale: any;
  xDomain: any;
  yDomain: any;
  transform: string;
  colors: ColorHelper;
  colorsLine: ColorHelper;
  margin: any[] = [10, 20, 10, 20];
  xAxisHeight: number = 0;
  yAxisWidth: number = 0;
  legendOptions: any;
  scaleType = ScaleType.Linear;
  xScaleLine;
  yScaleLine;
  xDomainLine;
  yDomainLine;
  seriesDomain;
  combinedSeries;
  xSet;
  filteredDomain;
  hoveredVertical;
  yOrientLeft = Orientation.Left;

  trackBy(index, item): string {
    return `${item.name}`;
  }

  update(): void {
    super.update();
    this.dims = calculateViewDimensions({
      width: this.width,
      height: this.height,
      margins: this.margin,
      showXAxis: this.xAxis,
      showYAxis: this.yAxis,
      xAxisHeight: this.xAxisHeight,
      yAxisWidth: this.yAxisWidth,
      showXLabel: this.showXAxisLabel,
      showYLabel: this.showYAxisLabel,
      showLegend: this.legend,
      legendType: this.schemeType,
      legendPosition: this.legendPosition as any,
    });

    // define scale for bubble series
    this.xScale = this.getXScale();
    this.yScale = this.getYScale();

    // define scale for line chart
    this.xDomainLine = this.getXDomainLine();
    if (this.filteredDomain) {
      this.xDomainLine = this.filteredDomain;
    }

    this.yDomainLine = this.getYDomainLine();
    this.seriesDomain = this.getSeriesDomain();

    this.scaleLines();

    this.setColors();
    this.legendOptions = this.getLegendOptions();

    this.transform = `translate(${this.dims.xOffset} , ${this.margin[0]})`;
  }

  deactivateAll() {
    this.activeEntries = [...this.activeEntries];
    for (const entry of this.activeEntries) {
      this.deactivate.emit({ value: entry, entries: [] });
    }
    this.activeEntries = [];
  }

  @HostListener("mouseleave")
  hideCircles(): void {
    this.hoveredVertical = null;
    this.deactivateAll();
  }

  updateHoveredVertical(item): void {
    this.hoveredVertical = item.value;
    this.deactivateAll();
  }

  updateDomain(domain): void {
    this.filteredDomain = domain;
    this.xDomainLine = this.filteredDomain;
    this.xScaleLine = this.getXScaleLine(this.xDomainLine, this.dims.width);
  }

  scaleLines() {
    this.xScaleLine = this.getXScaleLine(this.xDomainLine, this.dims.width);
    this.yScaleLine = this.getYScaleLine(this.yDomainLine, this.dims.height);
  }

  getSeriesDomain(): any[] {
    this.combinedSeries = this.lineChart.slice(0);
    this.combinedSeries.push({
      name: "WIND DIRECTION",
      series: this.results[0].series,
    });
    return this.combinedSeries.map((d) => d.name);
  }

  isDate(value): boolean {
    if (value instanceof Date) {
      return true;
    }

    return false;
  }

  getScaleType(values): ScaleType {
    let date = true;
    let num = true;

    for (const value of values) {
      if (!this.isDate(value)) {
        date = false;
      }

      if (typeof value !== "number") {
        num = false;
      }
    }

    if (date) {
      return ScaleType.Time;
    }

    if (num) {
      return ScaleType.Linear;
    }

    return ScaleType.Ordinal;
  }

  getXDomainLine(): any[] {
    let values = [];
    for (const results of this.lineChart) {
      for (const d of results.series) {
        if (!values.includes(d.name)) {
          values.push(d.name);
        }
      }
    }
    // add a pad to max and min to manage left/right limit case due to the arrows
    let firstDate = new Date(values[0]);
    firstDate.setHours(firstDate.getHours() - 1);
    values.unshift(firstDate.toISOString());

    let lastDate: Date = new Date(values[values.length - 1]);
    lastDate.setHours(lastDate.getHours() + 1);
    values.push(lastDate.toISOString());

    // get scale type
    this.scaleType = this.getScaleType(values);
    let domain = [];

    if (this.scaleType === "time") {
      const min = Math.min(...values);
      const max = Math.max(...values);
      domain = [min, max];
    } else if (this.scaleType === "linear") {
      values = values.map((v) => Number(v));
      const min = Math.min(...values);
      const max = Math.max(...values);
      domain = [min, max];
    } else {
      domain = values;
    }

    this.xSet = values;
    //console.log('xDomain line series scale type',this.scaleType);
    //console.log('xDomain line series',domain);
    return domain;
  }

  getYDomainLine(): any[] {
    const domain = [];

    for (const results of this.lineChart) {
      for (const d of results.series) {
        if (domain.indexOf(d.value) < 0) {
          domain.push(d.value);
        }
        if (d.min !== undefined) {
          if (domain.indexOf(d.min) < 0) {
            domain.push(d.min);
          }
        }
        if (d.max !== undefined) {
          if (domain.indexOf(d.max) < 0) {
            domain.push(d.max);
          }
        }
      }
    }

    let min = Math.min(...domain);
    const max = Math.max(...domain);
    //min = Math.min(0, min);
    //console.log('yDomain line series',[min-1,max+1]);
    //return [min, max];
    // add a pad to max and min to manage top/down limit case due to the arrows
    return [min - 1, max + 1];
  }

  getXScaleLine(domain, width): any {
    let scale;
    const spacing = 1;
    if (this.scaleType === "time") {
      scale = scaleTime().range([0, width]).domain(domain);
    } else if (this.scaleType === "linear") {
      scale = scaleLinear().range([0, width]).domain(domain);

      if (this.roundDomains) {
        scale = scale.nice();
      }
    } else if (this.scaleType === "ordinal") {
      scale = scaleBand()
        .range([0, width])
        .paddingInner(spacing)
        .domain(domain);
    }
    return scale;
  }

  getYScaleLine(domain, height): any {
    const scale = scaleLinear().range([height, 0]).domain(domain);

    return this.roundDomains ? scale.nice() : scale;
  }

  getXScale(): any {
    this.xDomain = this.getXDomain();

    // add a pad to max and min to manage left/right limit case due to the arrows
    let firstDate = new Date(this.xDomain[0]);
    firstDate.setHours(firstDate.getHours() - 1);
    this.xDomain.unshift(firstDate.toISOString());

    let lastDate: Date = new Date(this.xDomain[this.xDomain.length - 1]);
    lastDate.setHours(lastDate.getHours() + 1);
    this.xDomain.push(lastDate.toISOString());

    // define a spacing otherwise value do not catch x-tick values
    const spacing = 1;
    //console.log('xDomain bubble series',this.xDomain);
    // get scale
    return scaleBand()
      .range([0, this.dims.width])
      .paddingInner(spacing)
      .domain(this.xDomain);
  }

  getYScale(): any {
    // add a pad to max and min to manage top/down limit case due to the arrows
    this.yDomain = [
      (parseFloat(this.getYDomain()[0]) - 1).toString(),
      (parseFloat(this.getYDomain()[1]) + 1).toString(),
    ];
    //this.yDomain = this.getYDomain();
    //console.log('yDomain bubble series',this.yDomain);
    const scale = scaleLinear()
      .range([this.dims.height, 0])
      .domain(this.yDomain);
    return this.roundDomains ? scale.nice() : scale;
  }

  getXDomain(): any[] {
    return this.results[0].series.map((d) => d.x);
  }

  getYDomain() {
    const values = this.results[0].series.map((d) => d.y);
    //console.log('values',values);
    //const min = Math.min(0, ...values);

    const min = Math.min(...values);
    const max = Math.max(...values);
    if (this.yLeftAxisScaleFactor) {
      const minMax = this.yLeftAxisScaleFactor(min, max);
      //return [Math.min(0, minMax.min), minMax.max];
      return [minMax.min, minMax.max];
    } else {
      return [min, max];
    }
  }

  onClick(data) {
    this.select.emit(data);
  }

  setColors(): void {
    let domain;
    if (this.schemeType === ScaleType.Ordinal) {
      domain = this.xDomain;
    } else {
      domain = this.yDomain;
    }
    this.colors = new ColorHelper(
      this.scheme,
      this.schemeType,
      domain,
      this.customColors,
    );
    this.colorsLine = new ColorHelper(
      this.colorSchemeLine,
      this.schemeType,
      domain,
      this.customColors,
    );
  }

  getLegendOptions() {
    const opts = {
      scaleType: this.schemeType,
      colors: undefined,
      domain: [],
      title: undefined,
      position: this.legendPosition,
    };
    if (opts.scaleType === ScaleType.Ordinal) {
      opts.domain = this.seriesDomain;
      opts.colors = this.colorsLine;
      opts.title = this.legendTitle;
    } else {
      opts.domain = this.seriesDomain;
      opts.colors = this.colors.scale;
    }
    return opts;
  }

  updateYAxisWidth({ width }): void {
    this.yAxisWidth = width + 20;
    this.update();
  }

  updateXAxisHeight({ height }): void {
    this.xAxisHeight = height;
    this.update();
  }

  onActivate(item) {
    const idx = this.activeEntries.findIndex((d) => {
      return (
        d.name === item.name &&
        d.value === item.value &&
        d.series === item.series
      );
    });
    if (idx > -1) {
      return;
    }

    this.activeEntries = [item, ...this.activeEntries];
    this.activate.emit({ value: item, entries: this.activeEntries });
  }

  onDeactivate(item) {
    const idx = this.activeEntries.findIndex((d) => {
      return (
        d.name === item.name &&
        d.value === item.value &&
        d.series === item.series
      );
    });

    this.activeEntries.splice(idx, 1);
    this.activeEntries = [...this.activeEntries];

    this.deactivate.emit({ value: item, entries: this.activeEntries });
  }
}
