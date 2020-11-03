import { Component, Input, OnInit } from "@angular/core";
import { NgbActiveModal } from "@ng-bootstrap/ng-bootstrap";
import { DataExtractionRequest, Dataset } from "../../types";
import { DataService } from "../../services/data.service";
import { NgxSpinnerService } from "ngx-spinner";
import { environment } from "@rapydo/../environments/environment";

// === @swimlane/ngx-datatable/src/types/column-mode.type
enum ColumnMode {
  standard = "standard",
  flex = "flex",
  force = "force",
}

interface OpenData {
  date: string;
  run: string;
  filename: string;
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

  // columns = [{prop: 'date'}, {name: 'run'}, {name: 'Download', sortable: false}];
  ColumnMode = ColumnMode;

  constructor(
    private dataService: DataService,
    public activeModal: NgbActiveModal,
    private spinner: NgxSpinnerService
  ) {}

  ngOnInit() {
    this.spinner.show();
    this.loading = true;
    this.dataService
      .getOpenData(this.dataset.id)
      .subscribe(
        (response) => {
          this.data = this.normalize(response);
          console.log(this.data);
        },
        (error) => {
          // TODO
          console.error(error);
        }
      )
      .add(() => {
        this.loading = false;
        this.spinner.hide();
      });
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

  download(filename) {
    let link = document.createElement("a");
    link.href = `${environment.backendURI}/api/data/${filename}`;
    link.download = filename;
    link.style.visibility = "hidden";
    link.click();
  }
}
