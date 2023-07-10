import { Component,  EventEmitter, Output} from '@angular/core';
import { ViewportScroller } from '@angular/common';
@Component({
    selector: "app-user-guide",
    templateUrl: "./user-guide.component.html",
    styleUrls: ["./user-guide.component.scss"]
})
export class UserGuideComponent{
    public isCollapsed = true;
    
    @Output() onCollapseChange: EventEmitter<boolean> =
    new EventEmitter<boolean>();
    constructor(
      private viewportScroller: ViewportScroller
    ) { }



    public onClickScroll(elementId: string): void { 
      this.viewportScroller.scrollToAnchor(elementId);
  
    }
    changeCollapse() {
      this.isCollapsed = !this.isCollapsed;
      this.onCollapseChange.emit(this.isCollapsed);
    }
    ngOnInit(): void {
      
    }
   
  
}