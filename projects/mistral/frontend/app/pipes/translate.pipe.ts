import { TranslationService } from "../services/translation.service";
import { Pipe, PipeTransform } from "@angular/core";

@Pipe({
  name: "translate",
  pure: false,
})
export class TranslatePipe implements PipeTransform {
  constructor(private translationService: TranslationService) {}

  transform(value: string, lang?: string, args?: any): any {
    return this.translationService.translate(value, lang) || value;
  }
}
