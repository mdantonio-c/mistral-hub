import { Injectable } from "@angular/core";

enum MetaType {
  AREA = "area",
  LEVEL = "level",
  ORIGIN = "origin",
  PROD_DEF = "proddef",
  PRODUCT = "product",
  QUANTITY = "quantity",
  RUN = "run",
  TASK = "task",
  TIMERANGE = "timerange",
}

@Injectable({
  providedIn: "root",
})
export class ArkimetService {
  static decodeArea(i): string {
    const vals = [];
    switch (i.style) {
      case "GRIB":
        for (const k of Object.keys(i.value)) {
          vals.push(k + "=" + i.value[k]);
        }
        return "GRIB:" + vals.join(",");
      case "ODIMH5":
        for (const k of Object.keys(i.value)) {
          vals.push(k + "=" + i.value[k]);
        }
        return "ODIMH5:" + vals.join(",");
      case "VM2":
        let a = "VM2," + i.id;
        if (i.value !== undefined) {
          for (const k of Object.keys(i.value)) {
            vals.push(k + "=" + i.value[k]);
          }
          a = a + ":" + vals.join(",");
        }
        return a;
    }
  }

  static decodeLevel(i): string {
    let l;
    switch (i.style) {
      case "GRIB1":
        l = [i.level_type];
        if (i.l1 !== undefined) {
          l.push(i.l1);
          if (i.l2 !== undefined) {
            l.push(i.l2);
          }
        }
        return "GRIB1," + l.join(",");
      case "GRIB2S":
        l = [i.level_type, "-", "-"];
        if (i.scale !== undefined) {
          l[1] = i.scale;
        }
        if (i.value !== undefined) {
          l[2] = i.value;
        }
        return "GRIB2S," + l.join(",");
      case "GRIB2D":
        return (
          "GRIB2D," +
          i.l1 +
          "," +
          i.scale1 +
          "," +
          i.value1 +
          "," +
          i.l2 +
          "," +
          i.scale2 +
          "," +
          i.value2
        );
      case "ODIMH5":
        return "ODIMH5,range " + i.mi + " " + i.ma;
    }
  }

  static decodeOrigin(i): string {
    switch (i.style) {
      case "GRIB1":
        return "GRIB1," + i.centre + "," + i.subcentre + "," + i.process;
      case "GRIB2":
        return (
          "GRIB2," +
          i.centre +
          "," +
          i.subcentre +
          "," +
          i.process_type +
          "," +
          i.background_process_id +
          "," +
          i.process_id
        );
      case "BUFR":
        return "BUFR," + i.ce + "," + i.sc;
      case "ODIMH5":
        return "ODIMH5," + i.wmo + "," + i.rad + "," + i.plc;
    }
  }

  static decodeProddef(i): string {
    switch (i.style) {
      case "GRIB":
        const vals = [];
        for (const k of Object.keys(i.value)) {
          if (typeof i.value[k] == "number") {
            vals.push(k + "=" + i.value[k]);
          } else if (typeof i.value[k] == "string") {
            vals.push(k + "=" + '"' + i.value[k] + '"');
          }
        }
        return "GRIB:" + vals.join(",");
    }
  }

  static decodeProduct(i): string {
    switch (i.style) {
      case "GRIB1":
        return "GRIB1," + i.origin + "," + i.table + "," + i.product;
      case "GRIB2":
        return (
          "GRIB2," +
          i.centre +
          "," +
          i.discipline +
          "," +
          i.category +
          "," +
          i.number
        );
      case "BUFR":
        let s = "BUFR," + i.ty + "," + i.st + "," + i.ls;
        if (i.va !== undefined) {
          const vals = [];
          for (const k of Object.keys(i.va)) {
            vals.push(k + "=" + i.va[k]);
          }
          if (vals.length > 0) {
            s += ":" + vals.join(",");
          }
        }
        return s;
      case "ODIMH5":
        return "ODIMH5," + i.ob + "," + i.pr;
      case "VM2":
        let p = "VM2," + i.id;
        if (i.va !== undefined) {
          const vals = [];
          for (const k of Object.keys(i.va)) {
            vals.push(k + "=" + i.va[k]);
          }
          p = p + ":" + vals.join(",");
        }
        return p;
    }
  }

  static decodeQuantity(i): string {
    return i.value.join(",");
  }

  static decodeRun(i): string {
    switch (i.style) {
      case "MINUTE":
        const hour = Math.floor(i.value / 60);
        let h = "" + hour;
        const minute = i.value % 60;
        let m = "" + minute;
        if (hour < 10) {
          h = "0" + h;
        }
        if (minute < 10) {
          m = "0" + m;
        }

        return "MINUTE," + h + ":" + m;
    }
  }

  static decodeTask(i): string {
    return i.value;
  }

  static decodeTimerange(i): string {
    let un = {};
    switch (i.style) {
      case "GRIB1":
        un = {
          0: "m",
          1: "h",
          2: "d",
          3: "mo",
          4: "y",
          5: "de",
          6: "no",
          7: "ce",
          10: "h3",
          11: "h6",
          12: "h12",
          254: "s",
        };
        return (
          "GRIB1," +
          i.trange_type +
          "," +
          i.p1 +
          un[i.unit] +
          "," +
          i.p2 +
          un[i.unit]
        );
      case "GRIB2":
        un = {
          0: "m",
          1: "h",
          2: "d",
          3: "mo",
          4: "y",
          5: "de",
          6: "no",
          7: "ce",
          10: "h3",
          11: "h6",
          12: "h12",
          254: "s",
        };
        return (
          "GRIB2," +
          i.trange_type +
          "," +
          i.p1 +
          un[i.unit] +
          "," +
          i.p2 +
          un[i.unit]
        );
      case "Timedef":
        un = {
          0: "m",
          1: "h",
          2: "d",
          3: "mo",
          4: "y",
          5: "de",
          6: "no",
          7: "ce",
          10: "h3",
          11: "h6",
          12: "h12",
          13: "s",
        };
        let s = "Timedef";
        if (i.step_unit === 255) {
          s += ",-";
        } else {
          s += "," + i.step_len + un[i.step_unit];
        }
        if (i.stat_type !== undefined) {
          s += "," + i.stat_type;
        } else {
          // If i.pt is not defined, then
          // the stat type is 255 and
          // i.pl, i.pu are not defined
          // too (see
          // arki/types/timerange.cc:1358).
          // If the stat type is 255, then
          // proctype = "-" (see
          // arki/types/timerange.cc:1403).
          s += ",-";
        }
        // If i.pu is not defined, then
        // the stat unit is UNIT_MISSING = 255
        // and i.pl is not defined too
        // (see arki/types/timerange.cc:1361).
        // If stat unit is 255, then
        // proclen = "-" (see
        // arki/types/timerange.cc:1408).
        if (i.stat_unit !== undefined) {
          s += "," + i.stat_len + un[i.stat_unit];
        } else {
          s += ",-";
        }
        return s;
      case "BUFR":
        un = {
          0: "m",
          1: "h",
          2: "d",
          3: "mo",
          4: "y",
          5: "de",
          6: "no",
          7: "ce",
          10: "h3",
          11: "h6",
          12: "h12",
          13: "s",
        };
        return "BUFR," + i.va + un[i.un];
    }
  }

  getQuery(filter: any): string {
    // console.log(filter);
    switch (filter.name) {
      case MetaType.AREA:
        return (
          `${MetaType.AREA}:` +
          (filter.values as any[])
            .map((v) => ArkimetService.decodeArea(v))
            .filter((v) => v)
            .join(" or ")
        );
      case MetaType.LEVEL:
        return (
          `${MetaType.LEVEL}:` +
          (filter.values as any[])
            .map((v) => ArkimetService.decodeLevel(v))
            .filter((v) => v)
            .join(" or ")
        );
      case MetaType.ORIGIN:
        return (
          `${MetaType.ORIGIN}:` +
          (filter.values as any[])
            .map((v) => ArkimetService.decodeOrigin(v))
            .filter((v) => v)
            .join(" or ")
        );
      case MetaType.PROD_DEF:
        return (
          `${MetaType.PROD_DEF}:` +
          (filter.values as any[])
            .map((v) => ArkimetService.decodeProddef(v))
            .filter((v) => v)
            .join(" or ")
        );
      case MetaType.PRODUCT:
        return (
          `${MetaType.PRODUCT}:` +
          (filter.values as any[])
            .map((v) => ArkimetService.decodeProduct(v))
            .filter((v) => v)
            .join(" or ")
        );
      case MetaType.QUANTITY:
        return (
          `${MetaType.QUANTITY}:` +
          (filter.values as any[])
            .map((v) => ArkimetService.decodeQuantity(v))
            .filter((v) => v)
            .join(" or ")
        );
      case MetaType.RUN:
        return (
          `${MetaType.RUN}:` +
          (filter.values as any[])
            .map((v) => ArkimetService.decodeRun(v))
            .filter((v) => v)
            .join(" or ")
        );
      case MetaType.TASK:
        return (
          `${MetaType.TASK}:` +
          (filter.values as any[])
            .map((v) => ArkimetService.decodeTask(v))
            .filter((v) => v)
            .join(" or ")
        );
      case MetaType.TIMERANGE:
        return (
          `${MetaType.TIMERANGE}:` +
          (filter.values as any[])
            .map((v) => ArkimetService.decodeTimerange(v))
            .filter((v) => v)
            .join(" or ")
        );
      default:
        throw new Error(`Invalid filter type for ${filter.name}`);
    }
  }
}
