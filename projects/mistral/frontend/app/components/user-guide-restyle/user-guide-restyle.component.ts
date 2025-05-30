import { Component, OnInit, EventEmitter, Output } from '@angular/core';

@Component({
  selector: 'user-guide-restyle',
  templateUrl: './user-guide-restyle.component.html',
  styleUrls: ['./user-guide-restyle.component.scss']
})
export class UserGuideRestyleComponent implements OnInit {

  constructor() { }
  isCollapsed = false;
  @Output() onCollapseChange: EventEmitter<boolean> =
    new EventEmitter<boolean>();
  
    changeCollapse() {
      this.isCollapsed = !this.isCollapsed;
      this.onCollapseChange.emit(this.isCollapsed);
    }
  
  ngOnInit(): void {
  }

}
