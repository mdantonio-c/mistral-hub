import {
  ChangeDetectionStrategy,
  Component,
  Input,
  OnDestroy,
  OnInit,
  HostListener,
} from "@angular/core";
import { Subscription } from "rxjs";

@Component({
  selector: "mst-side-nav",
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./side-nav.component.html",
  styleUrls: ["side-nav.component.scss"],
})
export class SideNavComponent implements OnInit, OnDestroy {
  public isCollapsed = false;

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
}
