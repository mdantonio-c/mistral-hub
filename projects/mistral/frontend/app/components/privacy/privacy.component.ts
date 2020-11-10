import { Component } from "@angular/core";
import { ProjectOptions } from "@app/customization";

@Component({
  selector: "privacy",
  templateUrl: "./privacy.component.html",
})
export class PrivacyComponent {
  public terms_of_use: string;

  constructor(private customization: ProjectOptions) {
    const privacy = this.customization.privacy_statements();
    this.terms_of_use = privacy[0].text;
  }
}
