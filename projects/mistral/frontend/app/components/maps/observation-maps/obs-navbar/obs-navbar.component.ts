import { Component, Input, Output, EventEmitter } from "@angular/core";

@Component({
  selector: "app-obs-navbar",
  templateUrl: "./obs-navbar.component.html",
  styleUrls: ["./obs-navbar.component.scss"],
})
export class ObsNavbarComponent {
  @Input() displayMode: string;
  @Input() totalItems: number;
  @Input() loading: boolean = false;
  @Output() viewChange: EventEmitter<string> = new EventEmitter<string>();

  changeView(choice) {
    this.displayMode = choice;
    this.viewChange.emit(choice);
  }
}
