import { Injectable } from "@angular/core";
import { Observable } from "rxjs";
import { ApiService } from "@rapydo/services/api";
import { ExchangeBindings } from "@app/types";

@Injectable({
  providedIn: "root",
})
export class AdminService {
  constructor(private api: ApiService) {}

  getBindings(): Observable<ExchangeBindings> {
    return this.api.get<ExchangeBindings>(
      "outbindings",
      {},
      { validationSchema: "ExchangeBindings" }
    );
  }

  enableBinding(user, network): Observable<null> {
    return this.api.post(`outbindings/${user}/${network}`);
  }

  disableBinding(user, network): Observable<null> {
    return this.api.delete(`outbindings/${user}/${network}`);
  }
}
