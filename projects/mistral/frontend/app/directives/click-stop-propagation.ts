import { Directive, HostListener, ElementRef } from "@angular/core";

@Directive({
  selector: "[click-stop-propagation]",
})
export class ClickStopPropagation {
  constructor(el: ElementRef) {
    el.nativeElement.style.cursor = "text";
  }

  @HostListener("click", ["$event"])
  public onClick(event: any): void {
    event.preventDefault();
    event.stopPropagation();
  }
}
