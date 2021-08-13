import { Component, OnInit, ChangeDetectionStrategy } from "@angular/core";
import { NgbActiveModal } from "@ng-bootstrap/ng-bootstrap";

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./archive-delete.modal.html",
})
export class ArchiveDeleteModals implements OnInit {
  constructor(public modal: NgbActiveModal) {}

  public ngOnInit(): void {}
}
