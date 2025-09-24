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
import { ColorHelper, ScaleType } from "@swimlane/ngx-charts";
import { area, line, curveLinear } from "d3-shape";

type StringOrNumberOrDate = string | number | Date;
export interface DataItem {
  name: StringOrNumberOrDate;
  value: number;
  extra?: any;
  min?: number;
  max?: number;
  label?: string;
}

@Component({
  selector: "g[ngx-combo-charts-line-chart]",
  template: `
    <svg:g>
      <svg:g
        ngx-charts-line
        class="line-series"
        [data]="series"
        [path]="path"
        [stroke]="stroke"
        [animations]="animations"
        [class.active]="isActive(series)"
        [class.inactive]="isInactive(series)"
      />
      <svg:g
        ngx-charts-area
        *ngIf="hasRange"
        class="line-series-range"
        [data]="series"
        [path]="outerPath"
        [fill]="'#5AA454'"
        [class.active]="isActive(series)"
        [class.inactive]="isInactive(series)"
        [opacity]="rangeFillOpacity"
        [animations]="animations"
      />
    </svg:g>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [
    trigger("animationState", [
      transition(":leave", [
        style({
          opacity: 1,
        }),
        animate(
          500,
          style({
            opacity: 0,
          }),
        ),
      ]),
    ]),
  ],
})
export class ComboLineChartComponent implements OnChanges {
  @Input() xScale;
  @Input() yScale;
  @Input() colors: ColorHelper;
  @Input() scaleType: ScaleType;
  @Input() curve = curveLinear;
  @Input() activeEntries: any[];
  @Input() rangeFillOpacity: number;
  @Input() hasRange: boolean;
  @Input() animations: boolean = true;
  @Input() series: any;
  @Input() seriesLine: any;
  @Input() dims: any;
  @Input() gradient: boolean = false;
  @Input() tooltipDisabled: boolean = false;
  @Input() noBarWhenZero: boolean = false;
  path: string;
  outerPath: string;
  areaPath: string;
  stroke: string;

  ngOnChanges(changes: SimpleChanges): void {
    this.update();
  }

  update(): void {
    let data = this.sortData(this.series);

    const lineGen = this.getLineGenerator();
    this.path = lineGen(data) || "";

    const areaGen = this.getAreaGenerator();
    this.areaPath = areaGen(data) || "";

    if (this.hasRange) {
      const range = this.getRangeGenerator();
      this.outerPath = range(data) || "";
    }

    this.stroke = "#5AA454";
  }

  getLineGenerator(): any {
    return line<any>()
      .x((d) => {
        const label = d.name;
        let value;
        /*if (this.scaleType === ScaleType.Time) {
          value = this.xScale(label);
        } else if (this.scaleType === ScaleType.Linear) {
          value = this.xScale(Number(label));
        } else {
          value = this.xScale(label);
        }*/
        value = this.xScale(label);
        return value;
      })
      .y((d) => this.yScale(d.value))
      .curve(this.curve);
  }

  getRangeGenerator(): any {
    return area<any>()
      .x((d) => {
        const label = d.name;
        let value;
        if (this.scaleType === ScaleType.Time) {
          value = this.xScale(label);
        } else if (this.scaleType === ScaleType.Linear) {
          value = this.xScale(Number(label));
        } else {
          value = this.xScale(label);
        }
        return value;
      })
      .y0((d) => this.yScale(typeof d.min === "number" ? d.min : d.value))
      .y1((d) => this.yScale(typeof d.max === "number" ? d.max : d.value))
      .curve(this.curve);
  }

  getAreaGenerator(): any {
    const xProperty = (d) => {
      const label = d.name;
      return this.xScale(label);
    };

    return area<any>()
      .x(xProperty)
      .y0(() => this.yScale.range()[0])
      .y1((d) => this.yScale(d.value))
      .curve(this.curve);
  }

  sortLinear(data, property: string, direction = "asc"): any[] {
    return data.sort((a, b) => {
      if (direction === "asc") {
        return a[property] - b[property];
      } else {
        return b[property] - a[property];
      }
    });
  }
  sortByDomain(data, property: string, direction = "asc", domain): any[] {
    return data.sort((a, b) => {
      const aVal = a[property];
      const bVal = b[property];

      const aIdx = domain.indexOf(aVal);
      const bIdx = domain.indexOf(bVal);

      if (direction === "asc") {
        return aIdx - bIdx;
      } else {
        return bIdx - aIdx;
      }
    });
  }
  sortByTime(data, property: string, direction = "asc"): any[] {
    return data.sort((a, b) => {
      const aDate = a[property].getTime();
      const bDate = b[property].getTime();

      if (direction === "asc") {
        if (aDate > bDate) return 1;
        if (bDate > aDate) return -1;
        return 0;
      } else {
        if (aDate > bDate) return -1;
        if (bDate > aDate) return 1;
        return 0;
      }
    });
  }
  sortData(data) {
    data = this.sortByTime(data, "name");
    return data;
  }

  isActive(entry): boolean {
    if (!this.activeEntries) return false;
    const item = this.activeEntries.find((d) => {
      return entry.name === d.name;
    });
    return item !== undefined;
  }

  isInactive(entry): boolean {
    if (!this.activeEntries || this.activeEntries.length === 0) return false;
    const item = this.activeEntries.find((d) => {
      return entry.name === d.name;
    });
    return item === undefined;
  }
}
