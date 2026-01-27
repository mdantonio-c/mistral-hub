import { Component, OnInit } from "@angular/core";
import { NgxSpinnerService } from "ngx-spinner";
import { ArcoDataset } from "../../types";
import { ArcoService } from "../../services/arco.service";
import { NotificationService } from "@rapydo/services/notification";
import { catchError } from "rxjs/operators";
import { of } from "rxjs";
import { environment } from "@rapydo/../environments/environment";

@Component({
  selector: "app-arco-dataset",
  templateUrl: "./arco-dataset.component.html",
  styleUrls: ["./arco-dataset.component.scss"],
})
export class ArcoDatasetComponent implements OnInit {
  warningMsg: string | null = null;
  showAlert = false;
  datasets: ArcoDataset[] = [];
  loading: boolean = false;

  constructor(
    private spinner: NgxSpinnerService,
    private arcoService: ArcoService,
    public notify: NotificationService,
  ) {}

  ngOnInit(): void {
    this.load();
  }

  private load() {
    this.loading = true;
    this.spinner.show();
    this.arcoService
      .getArcoDatasets()
      .pipe(catchError(() => of([])))
      .subscribe(
        (result: ArcoDataset[]) => {
          this.datasets = result || [];
          this.datasets = []
          // for testing purposes duplicate datasets
          // this.datasets = this.datasets.concat(this.datasets);
          // keep datasets as returned
        },
        (error) => this.notify.showError(error),
      )
      .add(() => {
        this.spinner.hide();
        this.loading = false;
      });
  }

  onFileSelected(event: any) {
    const file: File = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e: any) => {
        try {
          const dataset: ArcoDataset = JSON.parse(e.target.result);
        } catch (error) {
          this.warningMsg = "Error parsing JSON file.";
          this.showAlert = true;
        }
      };
      reader.readAsText(file);
    }
  }

  copyArcoUrl(ds: ArcoDataset) {
    const url = this.getArcoUrl(ds);
    if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard
        .writeText(url)
        .then(() => this.notify.showSuccess("ARCO URL copied to clipboard"))
        .catch(() => this.notify.showError("Failed to copy ARCO URL"));
    } else {
      this.notify.showError("Clipboard API not available");
    }
  }

  getArcoUrl(ds: ArcoDataset): string {
    const backendURINoPort = environment.backendURI.replace(/:\\d+$/, "");
    return `${backendURINoPort}/api/arco/${ds.folder}`;
  }
}