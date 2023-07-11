import { XAxisTicksComponent } from "@swimlane/ngx-charts";
import {
  Component,
  Input,
  OnInit,
  ViewEncapsulation,
  ChangeDetectionStrategy,
} from "@angular/core";

@Component({
  selector: "g[custom-ngx-x-axis-ticks]",
  template: `
    <svg:g #ticksel>
      <svg:g
        *ngFor="let tick of ticks"
        class="tick"
        [attr.transform]="tickTransform(tick)"
      >
        <title>{{ tickFormat(tick) }}</title>
        <svg:text
          stroke-width="0.01"
          [attr.text-anchor]="textAnchor"
          [attr.transform]="textTransform"
          [style.font-size]="'12px'"
        >
          {{ tickTrim(tickFormat(tick)) }}
        </svg:text>
      </svg:g>
    </svg:g>

    <svg:g *ngFor="let tick of ticks" [attr.transform]="tickTransform(tick)">
      <svg:g *ngIf="showGridLines" [attr.transform]="gridLineTransform()">
        <svg:line
          class="gridline-path gridline-path-vertical"
          [ngStyle]="
            gridLineNgStyleByAxisTick ? gridLineNgStyleByAxisTick(tick) : null
          "
          [attr.y1]="-gridLineHeight"
          y2="0"
        />
      </svg:g>
    </svg:g>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CustomXAxisTick extends XAxisTicksComponent {
  @Input() gridLineNgStyleByAxisTick;
}
