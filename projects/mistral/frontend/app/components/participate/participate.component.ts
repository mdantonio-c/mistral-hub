import { Component } from "@angular/core";
import { ProjectOptions } from "@app/customization";

@Component({
  selector: "participate",
  templateUrl: "./participate.component.html",
})
export class ParticipateComponent {
  public terms_of_participation: string;

  constructor(private customization: ProjectOptions) {
    const participate = this.customization.participation_statements();
    this.terms_of_participation = participate[0].text;
  }
}
