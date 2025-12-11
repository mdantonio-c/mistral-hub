import { Component, Input, ChangeDetectionStrategy } from "@angular/core";
import { KeyValue } from "@rapydo/types";

@Component({
  selector: "[mistral-profile-row]",
  templateUrl: "mistral-profile-row.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MistralProfileRowComponent {
  @Input() row: KeyValue;

  constructor() {}
}
