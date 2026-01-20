import { trigger, style, animate, transition } from "@angular/animations";
import { LineChartComponent, ScaleType } from "@swimlane/ngx-charts";
import {
  Component,
  Input,
  OnInit,
  ViewEncapsulation,
  ChangeDetectionStrategy,
} from "@angular/core";

const styles = `
  .line-highlight {
    display: none;
  }
  .line-highlight.active {
    display: block;
  }
`;

@Component({
  selector: "custom-ngx-charts-line-chart",
  template: `
    <ngx-charts-chart
      [view]="[width, height]"
      [showLegend]="legend"
      [legendOptions]="legendOptions"
      [activeEntries]="activeEntries"
      [animations]="animations"
      (legendLabelClick)="onClick($event)"
      (legendLabelActivate)="onActivate($event)"
      (legendLabelDeactivate)="onDeactivate($event)"
    >
      <svg:defs>
        <svg:clipPath [attr.id]="clipPathId">
          <svg:rect
            [attr.width]="dims.width + 10"
            [attr.height]="dims.height + 10"
            [attr.transform]="'translate(-5, -5)'"
          />
        </svg:clipPath>
      </svg:defs>
      <svg:g [attr.transform]="transform" class="line-chart chart">
        <svg:g
          custom-ngx-x-axis
          *ngIf="xAxis"
          [xScale]="xScale"
          [dims]="dims"
          [showGridLines]="showGridLines"
          [gridLineNgStyleByAxisTick]="gridLineNgStyleByXAxisTick"
          [showLabel]="showXAxisLabel"
          [labelText]="xAxisLabel"
          [trimTicks]="trimXAxisTicks"
          [rotateTicks]="rotateXAxisTicks"
          [maxTickLength]="maxXAxisTickLength"
          [tickFormatting]="xAxisTickFormatting"
          [ticks]="xAxisTicks"
          (dimensionsChanged)="updateXAxisHeight($event)"
        ></svg:g>
        <svg:g
          ngx-charts-y-axis
          *ngIf="yAxis"
          [yScale]="yScale"
          [dims]="dims"
          [showGridLines]="showGridLines"
          [showLabel]="showYAxisLabel"
          [labelText]="yAxisLabel"
          [trimTicks]="trimYAxisTicks"
          [ticks]="yAxisTicks"
          [maxTickLength]="maxYAxisTickLength"
          [tickFormatting]="yAxisTickFormatting"
          [referenceLines]="referenceLines"
          [showRefLines]="showRefLines"
          [showRefLabels]="showRefLabels"
          (dimensionsChanged)="updateYAxisWidth($event)"
        ></svg:g>
        <svg:g *ngFor="let tick of yScale.ticks()">
          <svg:line
            x1="0"
            [attr.x2]="dims.width"
            [attr.y1]="yScale(tick)"
            [attr.y2]="yScale(tick)"
            stroke="#e4e4e4"
            stroke-width="1"
          />
        </svg:g>

        <svg:g *ngIf="showRefLines && referenceLines?.length">
          <svg:line
            *ngFor="let ref of referenceLines"
            [attr.x1]="0"
            [attr.x2]="dims.width"
            [attr.y1]="yScale(ref.value)"
            [attr.y2]="yScale(ref.value)"
            [attr.stroke]="ref.color || 'red'"
            [attr.stroke-width]="ref.strokeWidth || 1"
            [attr.stroke-opacity]="ref.opacity || 1"
            stroke-dasharray="4,2"
          />
        </svg:g>
        <svg:g [attr.clip-path]="clipPath">
          <svg:g *ngIf="!isSSR">
            <svg:g
              *ngFor="let series of results; trackBy: trackBy"
              [@animationState]="'active'"
            >
              <svg:g
                ngx-charts-line-series
                [xScale]="xScale"
                [yScale]="yScale"
                [colors]="colors"
                [data]="series"
                [activeEntries]="activeEntries"
                [scaleType]="scaleType"
                [curve]="curve"
                [rangeFillOpacity]="rangeFillOpacity"
                [hasRange]="hasRange"
                [animations]="animations"
              />
            </svg:g>
          </svg:g>
          <svg:g *ngIf="isSSR">
            <svg:g *ngFor="let series of results; trackBy: trackBy">
              <svg:g
                ngx-charts-line-series
                [xScale]="xScale"
                [yScale]="yScale"
                [colors]="colors"
                [data]="series"
                [activeEntries]="activeEntries"
                [scaleType]="scaleType"
                [curve]="curve"
                [rangeFillOpacity]="rangeFillOpacity"
                [hasRange]="hasRange"
                [animations]="animations"
              />
            </svg:g>
          </svg:g>

          <svg:g *ngIf="!tooltipDisabled" (mouseleave)="hideCircles()">
            <svg:g
              ngx-charts-tooltip-area
              [dims]="dims"
              [xSet]="xSet"
              [xScale]="xScale"
              [yScale]="yScale"
              [results]="results"
              [colors]="colors"
              [tooltipDisabled]="tooltipDisabled"
              [tooltipTemplate]="seriesTooltipTemplate"
              (hover)="updateHoveredVertical($event)"
            />

            <svg:g *ngFor="let series of results">
              <svg:g
                ngx-charts-circle-series
                [xScale]="xScale"
                [yScale]="yScale"
                [colors]="colors"
                [data]="series"
                [scaleType]="scaleType"
                [visibleValue]="hoveredVertical"
                [activeEntries]="activeEntries"
                [tooltipDisabled]="tooltipDisabled"
                [tooltipTemplate]="tooltipTemplate"
                (select)="onClick($event)"
                (activate)="onActivate($event)"
                (deactivate)="onDeactivate($event)"
              />
            </svg:g>
          </svg:g>
        </svg:g>
      </svg:g>
      <svg:g
        ngx-charts-timeline
        *ngIf="timeline && scaleType != 'ordinal'"
        [attr.transform]="timelineTransform"
        [results]="results"
        [view]="[timelineWidth, height]"
        [height]="timelineHeight"
        [scheme]="scheme"
        [customColors]="customColors"
        [scaleType]="scaleType"
        [legend]="legend"
        (onDomainChange)="updateDomain($event)"
      >
        <svg:g *ngFor="let series of results; trackBy: trackBy">
          <svg:g
            ngx-charts-line-series
            [xScale]="timelineXScale"
            [yScale]="timelineYScale"
            [colors]="colors"
            [data]="series"
            [scaleType]="scaleType"
            [curve]="curve"
            [hasRange]="hasRange"
            [animations]="animations"
          />
        </svg:g>
      </svg:g>
    </ngx-charts-chart>
  `,
  //styleUrls: ['../common/base-chart.component.scss'],
  encapsulation: ViewEncapsulation.None,
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
  styles: [styles],
})
export class CustomLineChart extends LineChartComponent {
  @Input() gridLineNgStyleByXAxisTick;
  @Input() dateInterval;
  @Input() scaleType: ScaleType = ScaleType.Time;
  @Input() yAxisTicks;
  area = false;
  xSet: any[] = [];
  hoveredVertical: any = null;
  override getXDomain(): any[] {
    if (this.dateInterval?.length === 2) {
      const values = this.getUniqueXDomainValues(this.results);
      this.xSet = [...values].sort((a, b) => {
        const aDate = a.getTime();
        const bDate = b.getTime();
        if (aDate > bDate) return 1;
        if (bDate > aDate) return -1;
        return 0;
      });
      return this.dateInterval;
    }
    return super.getXDomain();
  }
  getUniqueXDomainValues(results: any[]): any[] {
    const valueSet = new Set();
    for (const result of results) {
      for (const d of result.series) {
        valueSet.add(d.name);
      }
    }
    return Array.from(valueSet);
  }
}
