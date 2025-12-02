import {
  Component,
  OnInit,
  Input,
  ElementRef,
  Renderer2,
  ChangeDetectorRef,
  Output,
  EventEmitter,
  HostListener,
} from "@angular/core";
import * as L from "leaflet";
@Component({
  selector: "map-side-nav-subseasonal",
  templateUrl: "./side-nav.component.html",
  styleUrls: ["./side-nav.component.scss"],
})
export class SideNavComponentSubseasonal implements OnInit {
  ngOnInit() {}
}
