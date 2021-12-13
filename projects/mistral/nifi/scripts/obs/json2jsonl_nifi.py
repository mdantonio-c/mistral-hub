import json
import sys

if sys.stdin.buffer:

    dictin = json.load(sys.stdin.buffer)

    for i in range(len(dictin)):

        station_name = {}
        station_name["v"] = dictin[i].get("station_name")

        station_hmsl = {}
        station_hmsl["v"] = dictin[i].get("station_hmsl")

        vars_sta = {}
        vars_sta["B01019"] = station_name
        vars_sta["B07030"] = station_hmsl

        data_sta = {}
        data_sta["vars"] = vars_sta

        value = {}
        value["v"] = dictin[i].get("value")

        vars_dyn = {}
        vars_dyn[dictin[i].get("varcode")] = value

        data_dyn = {}
        data_dyn["timerange"] = [
            dictin[i].get("timerange"),
            dictin[i].get("p1"),
            dictin[i].get("p2"),
        ]
        data_dyn["vars"] = vars_dyn
        data_dyn["level"] = [
            dictin[i].get("level1"),
            dictin[i].get("l1"),
            dictin[i].get("level2"),
            dictin[i].get("l2"),
        ]

        dictout = {}
        dictout["ident"] = dictin[i].get("ident")
        dictout["network"] = dictin[i].get("network")
        dictout["lon"] = dictin[i].get("lon")
        dictout["lat"] = dictin[i].get("lat")
        dictout["date"] = dictin[i].get("date")
        dictout["data"] = [data_sta, data_dyn]

        json.dump(dictout, sys.stdout)
        sys.stdout.write("\n")

sys.exit(0)
