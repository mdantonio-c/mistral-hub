import {
  Component,
  Input,
  Output,
  SimpleChanges,
  EventEmitter,
  OnChanges,
  ChangeDetectionStrategy,
} from "@angular/core";
import { trigger, style, animate, transition } from "@angular/animations";
import { formatLabel } from "@swimlane/ngx-charts";
import * as moment from "moment";

enum PlacementTypes {
  Top = "top",
  Bottom = "bottom",
  Left = "left",
  Right = "right",
  Center = "center",
}
enum StyleTypes {
  popover = "popover",
  tooltip = "tooltip",
}
enum ScaleType {
  Time = "time",
  Linear = "linear",
  Ordinal = "ordinal",
  Quantile = "quantile",
}
type StringOrNumberOrDate = string | number | Date;
interface BubbleChartDataItem {
  name: StringOrNumberOrDate;
  x: StringOrNumberOrDate;
  y: StringOrNumberOrDate;
  r: number;
  extra?: any;
}

interface BubbleChartSeries {
  name: StringOrNumberOrDate;
  series: BubbleChartDataItem[];
}

@Component({
  selector: "g[ngx-combo-charts-bubble-series]",
  template: `
    <svg:g *ngFor="let circle of circles; trackBy: trackBy">
      <svg:g [attr.transform]="circle.transform">
        <svg:g
          ngx-charts-circle
          [@animationState]="'active'"
          class="circle"
          [cx]="0"
          [cy]="0"
          [r]="circle.radius"
          [fill]="circle.color"
          [style.opacity]="circle.opacity"
          [class.active]="circle.isActive"
          [pointerEvents]="'all'"
          [data]="circle.value"
          [classNames]="circle.classNames"
          (select)="onClick(circle.data)"
          (activate)="activateCircle(circle)"
          (deactivate)="deactivateCircle(circle)"
          ngx-tooltip
          [tooltipDisabled]="tooltipDisabled"
          [tooltipPlacement]="placementTypes.Top"
          [tooltipType]="styleTypes.tooltip"
          [tooltipContext]="circle.data"
        />
      </svg:g>
    </svg:g>
    <svg:g *ngFor="let arrow of arrows; let i = index; trackBy: trackBy">
      <svg:g [attr.transform]="arrow.transform">
        <!--        <svg-->
        <!--          viewBox="0 -5 40 10"-->
        <!--          width="40"-->
        <!--          height="10"-->
        <!--          style="overflow: visible;"-->
        <!--        >-->
        <svg
          viewBox="0 -5 20 10"
          width="20"
          height="10"
          style="overflow: visible;"
        >
          <line
            x1="0"
            y1="-5"
            x2="15"
            y2="-5"
            stroke="#E08352"
            stroke-width="2"
          />
          <!--          <polygon points="40,-5 30,-10 30,0" fill="#E08352" />-->
          <polygon points="18,-5 15,-7.5 15,-2.5" fill="#E08352" />
        </svg>
      </svg:g>
    </svg:g>
    <svg:g *ngFor="let arrow of arrows; let i = index; trackBy: trackBy">
      <svg:g [attr.transform]="arrow.windNameTransform">
        <!--        <svg-->
        <!--          viewBox="0 -5 40 10"-->
        <!--          width="40"-->
        <!--          height="10"-->
        <!--          style="overflow: visible;"-->
        <!--        >-->
        <svg
          viewBox="0 -5 20 10"
          width="20"
          height="10"
          style="overflow: visible;"
        >
          <text x="0" y="-5" fill="#D57042" font-size="8">
            {{ windNames[i] }}
          </text>
        </svg>
      </svg:g>
    </svg:g>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [
    trigger("animationState", [
      transition("* => void", [
        style({
          opacity: 1,
          transform: "*",
        }),
        animate(250, style({ opacity: 0, transform: "scale(0)" })),
      ]),
    ]),
  ],
})
export class ComboBubbleSeriesComponent implements OnChanges {
  @Input() data: BubbleChartSeries;
  @Input() xScale;
  @Input() yScale;
  @Input() rScale;
  @Input() xScaleType: ScaleType;
  @Input() yScaleType: ScaleType;
  @Input() visibleValue;
  @Input() activeEntries: any[];
  @Input() xAxisLabel: string;
  @Input() yAxisLabel: string;
  @Input() tooltipDisabled: boolean = false;
  @Input() colors;
  @Input() gradient: boolean;
  @Input() animations: boolean = true;

  @Output() select = new EventEmitter();
  @Output() activate = new EventEmitter();
  @Output() deactivate = new EventEmitter();

  circles: any[];
  arrows: any[];
  windNames: string[] = [];
  placementTypes = PlacementTypes;
  styleTypes = StyleTypes;

  ngOnChanges(changes: SimpleChanges): void {
    this.update();
  }

  update(): void {
    this.circles = this.getCircles();
    this.arrows = this.getArrows();
    // console.log('arrows',this.arrows);
    // console.log('circle',this.circles);
  }
  getArrows(): any[] {
    const seriesName = this.data[0].name;
    return this.data[0].series
      .map((d, i) => {
        if (
          typeof d.y !== "undefined" &&
          typeof d.x !== "undefined" &&
          typeof d.value !== "undefined"
        ) {
          const angle = d.value;
          this.windNames.push(this.windNomenclature(angle));
          const cx = this.xScale(moment.utc(d.x).local().toDate());
          const cy = this.yScale(Number(d.y));
          const isActive = !this.activeEntries.length
            ? true
            : this.isActive({ name: seriesName });
          const opacity = isActive ? 1 : 0.3;
          const data = Object.assign({}, d, {
            series: seriesName,
            name: d.name,
            value: d.y,
            x: d.x,
            angle: d.value,
          });
          return {
            data,
            angle,
            classNames: [`circle-data-${i}`],
            cx,
            cy,
            opacity,
            seriesName,
            isActive,
            // wind direction is showed starting from NORD 0° and with negative verse
            transform: `translate(${cx},${cy}) rotate(${angle - 90 + 180})`,
            windNameTransform: `translate(${cx - 5},${cy - 5})`,
          };
        }
      })
      .filter((circle) => circle !== undefined);
  }

  /* useful to give a name to wind direction */
  windNomenclature(angle): string {
    if (angle == 0) return "N";
    if (angle >= 1 && angle <= 44) return "N-NE";
    if (angle == 45) return "NE";
    if (angle >= 46 && angle <= 89) return "NE-E";
    if (angle == 90) return "E";
    if (angle >= 91 && angle <= 134) return "E-SE";
    if (angle == 135) return "SE";
    if (angle >= 136 && angle <= 179) return "SE-S";
    if (angle == 180) return "S";
    if (angle >= 181 && angle <= 224) return "S-SW";
    if (angle == 225) return "SW";
    if (angle >= 226 && angle <= 269) return "SW-W";
    if (angle == 270) return "W";
    if (angle >= 271 && angle <= 314) return "W-NW";
    if (angle == 315) return "NW";
    if (angle >= 316 && angle <= 359) return "NW-N";
  }
  getCircles(): any[] {
    const seriesName = this.data[0].name;
    return this.data[0].series
      .map((d, i) => {
        if (typeof d.y !== "undefined" && typeof d.x !== "undefined") {
          const y = d.y;
          const x = d.x;
          const r = d.r;

          const radius = r;
          const tooltipLabel = formatLabel(d.name);
          //const cx = this.xScaleType === ScaleType.Linear ? this.xScale(Number(x)) : this.xScale(x);
          const cx = this.xScale(moment.utc(x).local().toDate());
          //const cy = this.yScaleType === ScaleType.Linear ? this.yScale(Number(y)) : this.yScale(y);
          const cy = this.yScale(Number(y));
          const color =
            this.colors.scaleType === ScaleType.Linear
              ? this.colors.getColor(r)
              : this.colors.getColor(seriesName);

          const isActive = !this.activeEntries.length
            ? true
            : this.isActive({ name: seriesName });
          const opacity = isActive ? 1 : 0.3;

          const data = Object.assign({}, d, {
            series: seriesName,
            name: d.name,
            value: d.y,
            x: d.x,
            radius: d.r,
          });
          //console.log('cx',cx,'cy',cy,'cxtype',typeof(cx),'cytype',typeof(cy))
          return {
            data,
            x,
            y,
            r,
            classNames: [`circle-data-${i}`],
            value: y,
            label: x,
            cx,
            cy,
            radius,
            tooltipLabel,
            color,
            opacity,
            seriesName,
            isActive,
            transform: `translate(${cx},${cy})`,
          };
        }
      })
      .filter((circle) => circle !== undefined);
  }

  onClick(data): void {
    this.select.emit(data);
  }

  isActive(entry): boolean {
    if (!this.activeEntries) return false;
    const item = this.activeEntries.find((d) => {
      return entry.name === d.name;
    });
    return item !== undefined;
  }

  isVisible(circle): boolean {
    if (this.activeEntries.length > 0) {
      return this.isActive({ name: circle.seriesName });
    }

    return circle.opacity !== 0;
  }

  activateCircle(circle): void {
    circle.barVisible = true;
    this.activate.emit({ name: this.data.name });
  }

  deactivateCircle(circle): void {
    circle.barVisible = false;
    this.deactivate.emit({ name: this.data.name });
  }

  trackBy(index, circle): string {
    return `${circle.data.series} ${circle.data.name}`;
  }
}
