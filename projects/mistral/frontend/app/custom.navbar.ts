import {
  Component,
  Input,
  ChangeDetectionStrategy,
  Output,
  EventEmitter,
} from "@angular/core";

import { User } from "@rapydo/types";
import { environment } from "@rapydo/../environments/environment";

@Component({
  selector: "customlinks",
  templateUrl: "./custom.navbar.links.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CustomNavbarComponent {
  @Input() user: User;
  @Output() onClick: EventEmitter<null> = new EventEmitter<null>();
  projectHome: string = environment.CUSTOM.PROJECT_HOME;
  infoHome: string = environment.CUSTOM.INFO_HOME;
  ckanCatalogUrl: string = environment.CUSTOM.CKAN_CATALOG_URL;

  constructor() {}

  public collapse() {
    this.onClick.emit();
  }
}

@Component({
  selector: "custombrand",
  templateUrl: "./custom.navbar.brand.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CustomBrandComponent {
  projectTitle: string;
  projectHome: string = environment.CUSTOM.PROJECT_HOME;
  infoHome: string = environment.CUSTOM.INFO_HOME;
  constructor() {
    let t = environment.projectTitle;
    t = t.replace(/^'/, "");
    t = t.replace(/'$/, "");
    this.projectTitle = t;
  }
}
