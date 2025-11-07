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

@Component({
  selector: "g[ngx-combo-charts-line-seasonal]",
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
export class ComboLineChartSeasonalComponent implements OnChanges {
  @Input() xScale;
  @Input() yScale;
  @Input() colors: ColorHelper;
  @Input() curve = curveLinear;
  @Input() activeEntries: any[];
  @Input() rangeFillOpacity: number;
  @Input() hasRange: boolean;
  @Input() animations: boolean = true;
  @Input() series: any;
  @Input() dims: any;
  @Input() gradient: boolean = false;
  @Input() tooltipDisabled: boolean = false;
  @Input() noBarWhenZero: boolean = false;
  @Input() scaleType: ScaleType = ScaleType.Ordinal;
  @Input() seriesName: string;

  path: string;
  outerPath: string;
  areaPath: string;
  stroke: string;
  private lineColors: Record<string, string> = {
    "Clima Media": "#000000",
    "Clima Min": "#87CEEB",
    "Clima Max": "#FF0000",
  };

  ngOnChanges(changes: SimpleChanges): void {
    this.update();
  }

  update(): void {
    //console.log("this.series", this.series);
    let data = this.sortData(this.series);

    const lineGen = this.getLineGenerator();
    this.path = lineGen(data) || "";

    const areaGen = this.getAreaGenerator();
    this.areaPath = areaGen(data) || "";
    this.stroke = this.lineColors[this.seriesName] || "#000000";
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
        /* console.log(
          "Line point:",
          label,
          "x:",
          value,
          "bandwidth:",
          this.xScale.bandwidth(),
        );*/
        return value + this.xScale.bandwidth() / 2;
      })
      .y((d) => {
        //console.log("y value:", d.value, "scaled:", this.yScale(d.value));
        return this.yScale(d.value);
      })
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
    if (this.scaleType === ScaleType.Linear) {
      data = this.sortLinear(data, "name");
    } else if (this.scaleType === ScaleType.Time) {
      data = this.sortByTime(data, "name");
    } else {
      data = this.sortByDomain(data, "name", "asc", this.xScale.domain());
    }

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
