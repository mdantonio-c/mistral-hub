import { Component, Input, OnInit } from "@angular/core";
import { NgbActiveModal } from "@ng-bootstrap/ng-bootstrap";
import { DataExtractionRequest, Dataset, OpenData } from "../../types";
import { DataService } from "../../services/data.service";
import { NgxSpinnerService } from "ngx-spinner";
import { environment } from "@rapydo/../environments/environment";
import { NotificationService } from "@rapydo/services/notification";
import { Router } from "@angular/router";

// === @swimlane/ngx-datatable/src/types/column-mode.type
enum ColumnMode {
  standard = "standard",
  flex = "flex",
  force = "force",
}

@Component({
  selector: "app-dataset-details",
  templateUrl: "./dataset-details.component.html",
  styleUrls: ["./dataset-details.component.css"],
})
export class DatasetDetailsComponent implements OnInit {
  @Input() dataset: Dataset;
  active = 1;
  data: OpenData[] = [];
  loading: boolean = false;

  ColumnMode = ColumnMode;

  constructor(
    private dataService: DataService,
    public activeModal: NgbActiveModal,
    private router: Router,
    private notify: NotificationService,
    private spinner: NgxSpinnerService
  ) {}

  ngOnInit() {
    if (["FOR", "RAD"].includes(this.dataset.category)) {
      this.spinner.show();
      this.loading = true;
      this.dataService
        .getOpenData(this.dataset.name)
        .subscribe(
          (response) => {
            // this.data = this.normalize(response);
            this.data = response;
            // console.log(this.data);
          },
          (error) => {
            this.notify.showError(error);
          }
        )
        .add(() => {
          this.loading = false;
          this.spinner.hide();
        });
    }
  }

  getFileType(filename) {
    return filename.slice(((filename.lastIndexOf(".") - 1) >>> 0) + 2);
  }

  private normalize(data: DataExtractionRequest[]): OpenData[] {
    const openData = data.map((item) => {
      const container: OpenData = {
        date: item.args.reftime.from,
        run: ("0" + item.args.filters.run[0]["va"]).slice(-2),
        filename: item.fileoutput,
      };
      return container;
    });
    return openData;
  }

  download(filename: string) {
    let link = document.createElement("a");
    link.href = `${environment.backendURI}/api/opendata/${filename}`;
    link.download = filename;
    link.style.visibility = "hidden";
    link.click();
  }

  goTo(route: string) {
    this.activeModal.dismiss();
    this.router.navigate([route], {
      queryParams: { network: this.dataset.id },
    });
  }
}
