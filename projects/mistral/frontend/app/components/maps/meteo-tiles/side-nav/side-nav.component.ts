import {
  ChangeDetectionStrategy,
  Component,
  Input,
  Output,
  OnDestroy,
  OnInit,
  HostListener,
  EventEmitter,
} from "@angular/core";
import { Subscription } from "rxjs";

@Component({
  selector: "map-side-nav",
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./side-nav.component.html",
  styleUrls: ["side-nav.component.scss"],
})
export class SideNavComponent implements OnInit, OnDestroy {
  public isCollapsed = false;
  @Output() onZoomIn: EventEmitter<null> = new EventEmitter<null>();
  @Output() onZoomOut: EventEmitter<null> = new EventEmitter<null>();

  subscription: Subscription = new Subscription();
  routeDataSubscription!: Subscription;

  constructor() {}

  ngOnInit() {}

  ngOnDestroy() {
    this.subscription.unsubscribe();
  }

  @HostListener("dblclick", ["$event"])
  @HostListener("click", ["$event"])
  @HostListener("mousedown", ["$event"])
  @HostListener("wheel", ["$event"])
  public onClick(event: any): void {
    event.stopPropagation();
  }

  zoom(event, inOut: string) {
    event.preventDefault();
    switch (inOut) {
      case "in":
        this.onZoomIn.emit();
        break;
      case "out":
        this.onZoomOut.emit();
        break;
      default:
        console.error(`Invalid zoom param: ${inOut}`);
    }
  }
}
