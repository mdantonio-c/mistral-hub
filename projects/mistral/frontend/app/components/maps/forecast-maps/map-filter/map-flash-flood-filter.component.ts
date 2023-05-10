import { Component, OnInit, Input, Output, EventEmitter } from "@angular/core";
import { FormBuilder, FormGroup, Validators } from "@angular/forms";
import {
  KeyValuePair,
  FlashFloodFFields,
  IffRuns,
  Levels_pe,
  Levels_pr,
} from "../services/data";
import { MeteoFilter } from "../services/meteo.service";
import { AuthService } from "@rapydo/services/auth";
import { NgbActiveModal, NgbModal } from "@ng-bootstrap/ng-bootstrap";

// #####################################################
@Component({
  selector: "ngbd-modal-content",
  template: `
    <div class="modal-header">
      <h4 class="modal-title">PRODUCTS</h4>
      <button
        type="button"
        class="btn-close"
        aria-label="Close"
        (click)="activeModal.dismiss('Cross click')"
      ></button>
    </div>
    <div class="modal-body">
      <p>
        <b>IFF</b>: blending product using yesterday's 12UTC ECMWF ensemble
        forecast with the 21UTC COSMO-2I-EPS forecast.
      </p>
      <p>
        <b>IFF update</b>: updated blending product using today's 00UTC ECMWF
        ensemble forecast with the 21UTC COSMO-2I-EPS forecast.
      </p>
      Both products are created with the
      <a
        href="https://github.com/ecmwf/ecPoint/blob/master/README.md"
        target="_blank"
        rel="noopener noreferrer"
        >ecPoint</a
      >
      post-processing system.
    </div>
    <div class="modal-footer">
      <button
        type="button"
        class="btn btn-outline-dark"
        (click)="activeModal.close('Close click')"
      >
        Close
      </button>
    </div>
  `,
  // This is an "update" of the Run 12 and it is available ~ 2h later.
})
export class NgbdModalContent {
  @Input() name;

  constructor(public activeModal: NgbActiveModal) {}
}
// #####################################################
@Component({
  selector: "app-map-flash-flood-filter",
  templateUrl: "./map-flash-flood-filter.component.html",
  styleUrls: ["./map-filter.component.css"],
  // #####################################################
  // providers: [MapFlashFloodFilterComponent, NgbModal]
  // #####################################################
})
export class MapFlashFloodFilterComponent implements OnInit {
  filterForm: FormGroup;
  fields: KeyValuePair[] = FlashFloodFFields;
  levels_pe: KeyValuePair[] = Levels_pe;
  levels_pr: KeyValuePair[] = Levels_pr;
  runs: KeyValuePair[] = IffRuns;

  resolutions: KeyValuePair[] = [{ key: "lm2.2", value: "2.2" }];
  areas: KeyValuePair[] = [
    { key: "Italia", value: "Italy" },
    { key: "Nord_Italia", value: "Northern Italy" },
    { key: "Centro_Italia", value: "Central Italy" },
    { key: "Sud_Italia", value: "Southern Italy" },
  ];
  user;

  @Output() onFilterChange: EventEmitter<MeteoFilter> =
    new EventEmitter<MeteoFilter>();

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private modalService: NgbModal, // ##################################################### // config: MapFlashFloodFilterComponent, private modalService: NgbModal // #####################################################
  ) {
    this.filterForm = this.fb.group({
      field: ["percentile", Validators.required],
      level_pe: ["25"],
      level_pr: ["20"],
      run: ["12", Validators.required],

      res: ["lm2.2", Validators.required],
      area: ["Italia", Validators.required],
    });
    //  config.backdrop = 'static';
    // config.keyboard = false;
  }

  ngOnInit() {
    this.user = this.authService.getUser();
    // subscribe for form value changes
    this.onChanges();
    // apply filter the first time
    this.filter();
  }
  // #####################################################
  // open(content) {
  //   this.modalService.open(content);
  // }
  // #####################################################

  private onChanges(): void {
    this.filterForm.valueChanges.subscribe((val) => {
      this.filter();
    });
  }
  // #####################################################
  open() {
    const modalRef = this.modalService.open(NgbdModalContent);
    // modalRef.componentInstance.name = 'World';
  }
  // #####################################################

  private filter() {
    let filter: MeteoFilter = this.filterForm.value;
    this.onFilterChange.emit(filter);
  }
}
