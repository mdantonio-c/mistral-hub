import {Injectable} from '@angular/core';

enum MetaType {
    AREA = "area",
    LEVEL = "level",
    ORIGIN = "origin",
    PROD_DEF = "proddef",
    PRODUCT = "product",
    QUANTITY = "quantity",
    RUN = "run",
    TASK = "task",
    TIMERANGE = "timerange"
}

@Injectable()
export class ArkimetService {

    getQuery(filter: any): string {
        console.log(filter);
        switch (filter.name) {
            case MetaType.AREA:
                return `${MetaType.AREA}:`+(filter.values as any[]).map(v => ArkimetService.decodeArea(v)).join(' or ');
            case MetaType.LEVEL:
                return `${MetaType.LEVEL}:`+(filter.values as any[]).map(v => ArkimetService.decodeLevel(v)).join(' or ');
            case MetaType.ORIGIN:
                return `${MetaType.ORIGIN}:`+(filter.values as any[]).map(v => ArkimetService.decodeOrigin(v)).join(' or ');
            case MetaType.PROD_DEF:
                return `${MetaType.PROD_DEF}:`+(filter.values as any[]).map(v => ArkimetService.decodeProddef(v)).join(' or ');
            case MetaType.PRODUCT:
                return `${MetaType.PRODUCT}:`+(filter.values as any[]).map(v => ArkimetService.decodeProduct(v)).join(' or ');
            case MetaType.QUANTITY:
                return `${MetaType.QUANTITY}:`+(filter.values as any[]).map(v => ArkimetService.decodeQuantity(v)).join(' or ');
            case MetaType.RUN:
                return `${MetaType.RUN}:`+(filter.values as any[]).map(v => ArkimetService.decodeRun(v)).join(' or ');
            case MetaType.TASK:
                return `${MetaType.TASK}:`+(filter.values as any[]).map(v => ArkimetService.decodeTask(v)).join(' or ');
            case MetaType.TIMERANGE:
                return `${MetaType.TIMERANGE}:`+(filter.values as any[]).map(v => ArkimetService.decodeTimerange(v)).join(' or ');
            default:
                throw `Invalid filter type for ${filter.name}`;
        }
    }

    static decodeArea(i): string {
        let vals = [];
        switch (i.s) {
            case "GRIB":
                for (let k in i.va) {
                    vals.push(k + "=" + i.va[k]);
                }
                return "GRIB:" + vals.join(",");
            case "ODIMH5":
                for (let k in i.va) {
                    vals.push(k + "=" + i.va[k]);
                }
                return "ODIMH5:" + vals.join(",");
            case "VM2":
                let a = "VM2," + i.id;
                if (i.va !== undefined) {
                    for (let k in i.va) {
                        vals.push(k + "=" + i.va[k]);
                    }
                    a = a + ":" + vals.join(",");
                }
                return a;
        }
    }

    static decodeLevel(i): string {
        let l;
        switch (i.s) {
            case "GRIB1":
                l = [i.lt];
                if (i.l1 !== undefined) {
                    l.push(i.l1);
                    if (i.l2 !== undefined) {
                        l.push(i.l2);
                    }
                }
                return "GRIB1," + l.join(",");
            case "GRIB2S":
                l = [i.lt, '-', '-'];
                if (i.sc != undefined)
                    l[1] = i.sc;
                if (i.va != undefined)
                    l[2] = i.va;
                return "GRIB2S," + l.join(",");
            case "GRIB2D":
                return "GRIB2D," + i.l1 + "," + i.s1 + "," + i.v1 + "," + i.l2 + "," + i.s2 + "," + i.v2;
            case "ODIMH5":
                return "ODIMH5,range " + i.mi + " " + i.ma;
        }
    }

    static decodeOrigin(i): string {
        switch (i.s) {
            case "GRIB1":
                return "GRIB1," + i.ce + "," + i.sc + "," + i.pr;
            case "GRIB2":
                return "GRIB2," + i.ce + "," + i.sc + "," + i.pt + "," + i.bi + "," + i.pi;
            case "BUFR":
                return "BUFR," + i.ce + "," + i.sc;
            case "ODIMH5":
                return "ODIMH5," + i.wmo + "," + i.rad + "," + i.plc;
        }
    }

    static decodeProddef(i): string {
        switch (i.s) {
            case "GRIB":
                let vals = [];
                for (let k in i.va) {
                    vals.push(k + "=" + i.va[k]);
                }
                return "GRIB:" + vals.join(",");
        }
    }

    static decodeProduct(i): string {
        switch (i.s) {
            case "GRIB1":
                return "GRIB1," + i.or + "," + i.ta + "," + i.pr;
            case "GRIB2":
                return "GRIB2," + i.ce + "," + i.di + "," + i.ca + "," + i.no;
            case "BUFR":
                let s = "BUFR," + i.ty + "," + i.st + "," + i.ls;
                if (i.va != undefined) {
                    let vals = [];
                    for (let k in i.va) {
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
                if (i.va != undefined) {
                    let vals = [];
                    for (let k in i.va) {
                        vals.push(k + "=" + i.va[k]);
                    }
                    p = p + ":" + vals.join(",");
                }
                return p;
        }
    }

    static decodeQuantity(i): string {
        return i.va.join(",");
    }

    static decodeRun(i): string {
        switch (i.s) {
            case "MINUTE":
                let hour = Math.floor(i.va / 60);
                let h = "" + hour;
                let minute = i.va % 60;
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
        return i.va
    }

    static decodeTimerange(i): string {
        let un = {};
        switch (i.s) {
            case "GRIB1":
                un = {
                    0: 'm',
                    1: 'h',
                    2: 'd',
                    3: 'mo',
                    4: 'y',
                    5: 'de',
                    6: 'no',
                    7: 'ce',
                    10: 'h3',
                    11: 'h6',
                    12: 'h12',
                    254: 's'
                };
                return "GRIB1," + i.ty + "," + i.p1 + un[i.un] + "," + i.p2 + un[i.un];
            case "GRIB2":
                un = {
                    0: 'm',
                    1: 'h',
                    2: 'd',
                    3: 'mo',
                    4: 'y',
                    5: 'de',
                    6: 'no',
                    7: 'ce',
                    10: 'h3',
                    11: 'h6',
                    12: 'h12',
                    254: 's'
                };
                return "GRIB2," + i.ty + "," + i.p1 + un[i.un] + "," + i.p2 + un[i.un];
            case "Timedef":
                un = {
                    0: 'm',
                    1: 'h',
                    2: 'd',
                    3: 'mo',
                    4: 'y',
                    5: 'de',
                    6: 'no',
                    7: 'ce',
                    10: 'h3',
                    11: 'h6',
                    12: 'h12',
                    13: 's'
                };
                let s = "Timedef";
                if (i.su == 255) {
                    s += ",-"
                } else {
                    s += "," + i.sl + un[i.su];
                }
                if (i.pt != undefined) {
                    s += "," + i.pt
                } else {
                    // If i.pt is not defined, then
                    // the stat type is 255 and
                    // i.pl, i.pu are not defined
                    // too (see
                    // arki/types/timerange.cc:1358).
                    // If the stat type is 255, then
                    // proctype = "-" (see
                    // arki/types/timerange.cc:1403).
                    s += ",-"
                }
                // If i.pu is not defined, then
                // the stat unit is UNIT_MISSING = 255
                // and i.pl is not defined too
                // (see arki/types/timerange.cc:1361).
                // If stat unit is 255, then
                // proclen = "-" (see
                // arki/types/timerange.cc:1408).
                if (i.pu != undefined) {
                    s += "," + i.pl + un[i.pu]
                } else {
                    s += ",-"
                }
                return s;
            case "BUFR":
                un = {
                    0: 'm',
                    1: 'h',
                    2: 'd',
                    3: 'mo',
                    4: 'y',
                    5: 'de',
                    6: 'no',
                    7: 'ce',
                    10: 'h3',
                    11: 'h6',
                    12: 'h12',
                    13: 's'
                };
                return "BUFR," + i.va + un[i.un];
        }
    }
}
