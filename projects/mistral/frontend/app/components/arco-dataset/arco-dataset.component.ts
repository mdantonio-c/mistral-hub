import {
  Component,
} from "@angular/core";
import { NgxSpinnerService } from "ngx-spinner";
import { ArcoDataset } from "../../types";


@Component({
  selector: "app-arco-dataset",
  templateUrl: "./arco-dataset.component.html",
  styleUrls: ["./arco-dataset.component.scss"],
})
export class ArcoDatasetComponent {
 warningMsg: string | null = null;
   showAlert = false;
}