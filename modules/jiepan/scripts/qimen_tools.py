#!/usr/bin/env python3
"""Read-only chart facts and independent deterministic calculations (Python stdlib)."""
import argparse
import json
from pathlib import Path
import sys

VERSION = "0.2.2"
FIELDS = ("number", "name", "direction", "earth", "sky", "hostedEarth", "hostedSky",
          "star", "door", "god", "earthGod", "dark", "darkBranch", "bird", "empty", "horse")
STATES = {"present", "empty", "notApplicable", "notImplemented", "unknown"}
PROFILES = {f"shijia-{p}-{m}" for p in ("zhuanpan", "feipan", "xingfeimenzhuan", "shenzhuanfeipan")
            for m in ("chaibu", "zhirun")} | {f"{t}-{p}" for t in ("rijia", "yuejia")
            for p in ("zhuanpan", "feipan", "xingfeimenzhuan", "shenzhuanfeipan")}
LAYER_ARRAYS = {"earth": "earth", "sky": "sky", "star": "stars", "door": "doors",
                "god": "heavenGods", "earthGod": "earthGods", "dark": "dark", "darkBranch": "darkBranches"}
BOOL_FIELDS = {"bird", "empty", "horse"}
META_FIELDS = ("input", "profile", "settings", "inactiveSettings", "timeConventions", "pillars", "hour",
               "activePillar", "activeGanZhi", "xun", "hidden", "chiefStar", "chiefDoor", "target", "doorTarget",
               "hostPalace", "birdPalace", "yang", "ju", "dingJu", "solar", "hostTerm", "darkMode",
               "voidBranches", "voidPalaces", "horse", "horsePalace", "layers")


class InputError(ValueError):
    pass


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def pointer_part(value):
    return str(value).replace("~", "~0").replace("/", "~1")


class Chart:
    """Validate query-critical structure, without claiming full JSON Schema validation."""
    def __init__(self, data):
        self.data = data
        if not isinstance(data, dict):
            raise InputError("chart must be a JSON object")
        self.book = data.get("sourceType") == "book"
        if self.book:
            if not data.get("chartId") or not isinstance(data.get("source"), dict) or not data["source"]:
                raise InputError("book chart requires chartId and source provenance")
            if "engineVersion" in data or "snapshotId" in data or "generator" in data:
                raise InputError("book chart cannot claim engine snapshot identity")
        elif data.get("sourceType") not in (None, "engine"):
            raise InputError("unsupported sourceType")
        else:
            if data.get("schemaVersion") != "1.0.0" or data.get("engineVersion") != "0.4.1":
                raise InputError("unsupported engine/schema version; no automatic compatibility conversion")
            for key in ("snapshotId", "profile", "settings", "inactiveSettings", "timeConventions", "pillars",
                        "activePillar", "activeGanZhi", "chiefStar", "chiefDoor", "layers", "darkMode", "palaceStates"):
                if key not in data:
                    raise InputError("missing engine field: " + key)
            if data["timeConventions"].get("timezone") != "UTC+8" or data["timeConventions"].get("dayBoundary") != "23:00":
                raise InputError("unsupported time conventions")
            if data["activePillar"] not in ("hour", "day", "month") or data["pillars"].get(data["activePillar"]) != data["activeGanZhi"]:
                raise InputError("active pillar disagrees with pillars")
        profile = data.get("profile")
        if profile is not None and profile not in PROFILES:
            raise InputError("unsupported profile: " + str(profile))
        if not self.book and profile is None:
            raise InputError("engine profile is required")
        if not self.book:
            s = data["settings"]
            expected_profile = f"{s.get('timeLevel')}-{s.get('pan')}" + (f"-{s.get('method')}" if s.get("timeLevel") == "shijia" else "")
            if profile != expected_profile:
                raise InputError("profile disagrees with settings")
            pan = s.get("pan")
            expected_layers = {"stars": pan != "zhuanpan", "stems": pan != "zhuanpan",
                               "doors": pan in ("feipan", "shenzhuanfeipan"),
                               "gods": pan in ("feipan", "xingfeimenzhuan")}
            if data["layers"] != expected_layers:
                raise InputError("layer modes disagree with profile")
            expected_active = {"shijia": "hour", "rijia": "day", "yuejia": "month"}[s["timeLevel"]]
            if data["activePillar"] != expected_active:
                raise InputError("active pillar disagrees with profile")
            if data["darkMode"] not in ("mingfa", "unavailable"):
                raise InputError("unsupported darkMode")
        palaces = data.get("palaces")
        if not isinstance(palaces, list) or not palaces:
            raise InputError("palaces must be a nonempty list")
        self.palaces = {}
        for i, p in enumerate(palaces):
            if not isinstance(p, dict) or type(p.get("number")) is not int or not 1 <= p["number"] <= 9:
                raise InputError("invalid palace number")
            if p["number"] in self.palaces:
                raise InputError("duplicate palace number")
            self.palaces[p["number"]] = (i, p)
        if not self.book and set(self.palaces) != set(range(1, 10)):
            raise InputError("engine chart must contain all nine palaces")
        self.states = {}
        self.state_pointers = {}
        for i, state in enumerate(data.get("palaceStates", [])):
            n = state.get("number")
            if n not in self.palaces or n in self.states or not isinstance(state.get("fields"), dict):
                raise InputError("invalid/duplicate palaceStates entry")
            self.states[n] = (i, state["fields"])
            for field in state["fields"]:
                self.state_pointers[n, field] = f"/palaceStates/{i}/fields/{pointer_part(field)}"
        if self.book:
            for n, (i, p) in self.palaces.items():
                local = p.get("fieldStates", {})
                if not isinstance(local, dict):
                    raise InputError("book fieldStates must be an object")
                si, states = self.states.get(n, (None, {}))
                combined = dict(states)
                for field, state in local.items():
                    if field not in FIELDS or (field in states and state != states[field]):
                        raise InputError("conflicting/unknown book fieldStates entry")
                    combined[field] = state
                    self.state_pointers[n, field] = f"/palaces/{i}/fieldStates/{pointer_part(field)}"
                self.states[n] = (si, combined)
        for n, (i, palace) in self.palaces.items():
            states = self.states.get(n, (None, {}))[1]
            for field in FIELDS:
                state = states.get(field)
                if not self.book and (field not in palace or state not in STATES - {"unknown"}):
                    raise InputError(f"missing/error engine palace field or status: {n}/{field}")
                if not self.book:
                    layers = data["layers"]
                    settings = data["settings"]
                    if any(type(layers.get(k)) is not bool for k in ("stars", "stems", "doors", "gods")):
                        raise InputError("missing/invalid layer modes")
                    expected = "empty" if palace[field] == "" else "present"
                    if field in ("dark", "darkBranch") and data["darkMode"] == "unavailable":
                        expected = "notImplemented"
                    elif ((field in ("hostedSky", "hostedEarth", "bird") and layers["stars"]) or
                          (n == 5 and ((field in ("sky", "star") and not layers["stars"]) or
                           (field == "door" and (not layers["doors"] or settings.get("middleDoor") != "use")) or
                           (field in ("god", "earthGod") and (not layers["gods"] or settings.get("taiChang") == "omit"))))):
                        expected = "notApplicable"
                    if state != expected:
                        raise InputError(f"status disagrees with method: {n}/{field}")
                    if state in ("notApplicable", "notImplemented") and palace[field] not in ("", False):
                        raise InputError(f"unavailable field contains value: {n}/{field}")
                if state is not None and state not in STATES:
                    raise InputError(f"invalid field status: {n}/{field}")
                if state == "present" and (field not in palace or palace[field] is None or palace[field] == ""):
                    raise InputError(f"present status contradicts value: {n}/{field}")
                if state == "empty" and palace.get(field) != "":
                    raise InputError(f"empty status contradicts value: {n}/{field}")
                if field in palace and palace[field] is not None:
                    value = palace[field]
                    if field in BOOL_FIELDS and type(value) is not bool:
                        raise InputError(f"boolean required: {n}/{field}")
                    if field not in BOOL_FIELDS and field != "number" and not isinstance(value, str):
                        raise InputError(f"string required: {n}/{field}")
                if self.book and palace.get(field) == "" and state is None:
                    raise InputError(f"book empty string needs explicit state: {n}/{field}")
                if not self.book and field in LAYER_ARRAYS:
                    array = data.get(LAYER_ARRAYS[field])
                    if not isinstance(array, list) or len(array) != 9 or array[n - 1] != palace[field]:
                        raise InputError(f"layer array disagrees: {n}/{field}")

    def identity(self):
        keys = ("chartId", "source", "profile") if self.book else ("snapshotId", "schemaVersion", "engineVersion", "profile")
        return {"sourceType": "book" if self.book else "engine", **{k: self.data.get(k) for k in keys}}

    def query(self, palace=None, layer=None, symbol=None):
        if palace is not None and palace not in range(1, 10):
            raise InputError("palace must be 1..9")
        if layer is not None and layer not in FIELDS:
            raise InputError("unknown layer: " + str(layer))
        facts = []
        for n in ([palace] if palace else range(1, 10)):
            i, p = self.palaces.get(n, (None, {}))
            si, states = self.states.get(n, (None, {}))
            for field in ([layer] if layer else FIELDS):
                value = p.get(field)
                state = states.get(field)
                if state is None:
                    state = "unknown" if field not in p or value is None else "present"
                if symbol is not None and (state != "present" or value != symbol):
                    continue
                facts.append({"palace": n, "layer": field, "value": value, "state": state,
                              "pointer": None if i is None or field not in p else f"/palaces/{i}/{field}",
                              "statePointer": self.state_pointers.get((n, field)),
                              "stemRole": "hosted" if field in ("hostedEarth", "hostedSky") else
                                          "main" if field in ("earth", "sky") else None})
        return {"adapterVersion": VERSION, "chart": self.identity(), "facts": facts}

    def metadata(self):
        facts = []
        for field in META_FIELDS:
            exists = field in self.data
            value = self.data.get(field)
            # The engine defines palaceStates only for palace fields. Retain raw
            # null metadata, without inventing a method-specific availability.
            state = "unknown" if not exists else "empty" if value == "" else "present"
            facts.append({"field": field, "value": value, "state": state,
                          "pointer": "/" + pointer_part(field) if exists else None,
                          "stateOrigin": "adapter presence only; no engine metadata availability field"})
        return {"adapterVersion": VERSION, "chart": self.identity(), "facts": facts}


STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
CYCLE = tuple(STEMS[i % 10] + BRANCHES[i % 12] for i in range(60))
BRANCH_PALACES = {b: n for b, n in zip(BRANCHES, (1, 8, 8, 3, 4, 4, 9, 2, 2, 7, 6, 6))}
HOME_DOORS = {1: "休门", 2: "死门", 3: "伤门", 4: "杜门", 6: "开门", 7: "惊门", 8: "生门", 9: "景门"}
OPPOSITE = {n: 10 - n for n in HOME_DOORS}
CALCULATION_REFERENCE = "references/calculation-rules.md"


def derivation(method, inputs, state="present", value=None, **extra):
    return {"derivedVersion": VERSION, "method": method, "state": state, "inputs": inputs,
            "value": value, "ruleReference": CALCULATION_REFERENCE, **extra}


def palace_relation(chart, from_palace, to_palace):
    """Fixed palace elements, independent of any historical corpus or profile."""
    if any(type(n) is not int or n not in chart.palaces for n in (from_palace, to_palace)):
        raise InputError("derived relation requires two known palace numbers")
    elements = {1: "水", 2: "土", 3: "木", 4: "木", 5: "土", 6: "金", 7: "金", 8: "土", 9: "火"}
    produces = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    controls = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
    a, b = elements[from_palace], elements[to_palace]
    if a == b:
        relation, label = "sameElement", "同五行"
    elif produces[a] == b:
        relation, label = "generates", "前宫生后宫"
    elif produces[b] == a:
        relation, label = "generatedBy", "前宫受后宫生"
    elif controls[a] == b:
        relation, label = "overcomes", "前宫克后宫"
    else:
        relation, label = "overcomeBy", "前宫受后宫克"
    return derivation("palace-five-elements-v1", [chart.query(n, "number")["facts"][0] for n in (from_palace, to_palace)],
                      value={"fromElement": a, "toElement": b, "relation": relation, "label": label},
                      chart=chart.identity(), convention="仅比较固定地盘宫五行；不计算旺衰、主客或吉凶。")


def ganzhi_xun(ganzhi, pillar, pointer=None):
    """Cycle lookup only: no datetime conversion, timezone or calendar calculation."""
    if pillar not in ("year", "month", "day", "hour"):
        raise InputError("pillar must explicitly be year, month, day or hour")
    inputs = [{"pillar": pillar, "pointer": pointer, "value": ganzhi,
               "state": "unknown" if ganzhi in (None, "") else "present"}]
    if ganzhi in (None, ""):
        return derivation("ganzhi-xun-v1", inputs, state="unknown", pillar=pillar,
                          reason="所选柱未提供明确干支。", convention="仅按所选柱求旬首、旬空；日空与时空分别计算。")
    if not isinstance(ganzhi, str) or ganzhi not in CYCLE:
        raise InputError("invalid sexagenary ganzhi: " + repr(ganzhi))
    index = CYCLE.index(ganzhi)
    xun_index = index // 10
    void = [BRANCHES[10 - xun_index * 2], BRANCHES[11 - xun_index * 2]]
    value = {"cycleIndex": index, "xunHead": CYCLE[xun_index * 10], "hiddenStem": "戊己庚辛壬癸"[xun_index],
             "voidBranches": void, "voidPalaces": list(dict.fromkeys(BRANCH_PALACES[b] for b in void))}
    return derivation("ganzhi-xun-v1", inputs, value=value, pillar=pillar,
                      convention="六十甲子每十位一旬；所选柱独立取旬空，不按profile替换成起盘柱。")


def xun_from_json(data, pillar):
    if not isinstance(data, dict) or not isinstance(data.get("pillars", {}), dict):
        raise InputError("JSON input and pillars must be objects")
    pillars = data.get("pillars", {})
    pointer = "/pillars/" + pillar if pillar in pillars else None
    result = ganzhi_xun(pillars.get(pillar), pillar, pointer)
    result["profile"] = data.get("profile")
    result["profileUsed"] = False
    comparisons = []
    source_scope = data.get("activePillar")
    derived_value = result["value"] or {}
    for source_field, derived_field in (("xun", "xunHead"), ("hidden", "hiddenStem"),
                                        ("voidBranches", "voidBranches"), ("voidPalaces", "voidPalaces")):
        if source_field not in data:
            continue
        source = data[source_field]
        computed = derived_value.get(derived_field)
        if source_scope is None:
            comparison = "unscoped"
        elif source_scope != pillar:
            comparison = "differentPillar"
        elif computed is None or source is None or source == "" or source == "unknown":
            comparison = "unknown"
        else:
            comparable_sets = (isinstance(source, list) and isinstance(computed, list) and
                               all(isinstance(v, (str, int)) for v in source + computed))
            match = set(source) == set(computed) if comparable_sets else source == computed
            comparison = "match" if match else "conflict"
        comparisons.append({"pointer": "/" + source_field, "sourcePillar": source_scope,
                            "sourceValue": source, "derivedPillar": pillar, "derivedValue": computed,
                            "comparison": comparison})
    result["sourceComparisons"] = comparisons
    return result


def door_pattern(chart, declared_profile=None, center_door_host=None):
    """All eight rotated doors must match. Source facts are never rewritten."""
    source_profile = chart.data.get("profile")
    profile = declared_profile if declared_profile is not None else source_profile
    for p in (source_profile, declared_profile):
        if p is not None and p not in PROFILES:
            raise InputError("unsupported profile: " + str(p))
    if center_door_host is not None and (type(center_door_host) is not int or center_door_host not in HOME_DOORS):
        raise InputError("center-door-host must name an outer palace")
    profile_input = {"pointer": "/profile" if source_profile is not None else None,
                     "sourceValue": source_profile, "declaredValue": declared_profile,
                     "declaredPointer": "cli:--profile" if declared_profile is not None else None}
    inputs = chart.query(layer="door")["facts"]
    center = next(f for f in inputs if f["palace"] == 5)
    center_handling = {"source": center, "declaredHost": center_door_host,
                       "declarationPointer": "cli:--center-door-host" if center_door_host is not None else None,
                       "action": "notUsed"}
    common = {"chart": chart.identity(), "profileBasis": profile_input, "centerHandling": center_handling,
              "convention": "只识别门转盘八门在本宫或对冲宫的全局排列；中心标记不自动挪入外宫。"}
    if source_profile is not None and declared_profile is not None and source_profile != declared_profile:
        return derivation("eight-door-global-pattern-v1", inputs, state="unknown", reason="源profile与显式指定profile冲突。", **common)
    if profile is None:
        return derivation("eight-door-global-pattern-v1", inputs, state="unknown", reason="未明确适用盘式；可显式提供实际profile。", **common)
    pan = profile.split("-")[1]
    if pan not in ("zhuanpan", "xingfeimenzhuan"):
        return derivation("eight-door-global-pattern-v1", inputs, state="notApplicable", reason="本算法仅用于门转布局；飞门盘未按此口径识别。", **common)
    placements = {}
    for fact in inputs:
        if fact["palace"] != 5 and fact["state"] == "present" and fact["value"] in HOME_DOORS.values():
            placements[fact["palace"]] = {"door": fact["value"], "inputPointer": fact["pointer"], "origin": "sourceOuter"}
    if center["state"] == "present" and center["value"] not in (None, ""):
        if center["value"] not in HOME_DOORS.values() or center_door_host is None:
            center_handling["action"] = "unresolved"
            return derivation("eight-door-global-pattern-v1", inputs, state="unknown", reason="中心有门标记，缺少可用的明确寄宫说明。", **common)
        host = placements.get(center_door_host)
        if host is not None and host["door"] != center["value"]:
            center_handling["action"] = "conflict"
            return derivation("eight-door-global-pattern-v1", inputs, state="unknown", reason="中心门与明确寄宫的原门值冲突。", **common)
        if host is not None:
            center_handling["action"] = "matchingHostedReference"
        else:
            host_fact = next(f for f in inputs if f["palace"] == center_door_host)
            if host_fact["state"] not in ("unknown", "empty"):
                center_handling["action"] = "conflict"
                return derivation("eight-door-global-pattern-v1", inputs, state="unknown", reason="寄宫状态不允许由中心标记补出有效门位。", **common)
            placements[center_door_host] = {"door": center["value"], "inputPointer": center["pointer"],
                                           "origin": "explicitCenterHostProjection", "rawHost": host_fact}
            center_handling["action"] = "derivedHostPlacement"
    if center_door_host is not None and center["state"] != "present":
        center_handling["action"] = "noKnownCenterDoor"
    doors = [p["door"] for p in placements.values()]
    if set(placements) != set(HOME_DOORS) or len(doors) != 8 or set(doors) != set(HOME_DOORS.values()):
        return derivation("eight-door-global-pattern-v1", inputs, state="unknown", reason="八个外宫门位未齐，或八门不唯一；不把局部匹配当成全局格局。",
                          effectivePlacements=placements, **common)
    home_matches = [n for n, door in HOME_DOORS.items() if placements[n]["door"] == door]
    opposite_matches = [n for n, door in HOME_DOORS.items() if placements[OPPOSITE[n]]["door"] == door]
    fuyin, fanyin = len(home_matches) == 8, len(opposite_matches) == 8
    pattern = "fuyin" if fuyin else "fanyin" if fanyin else "none"
    result = derivation("eight-door-global-pattern-v1", inputs,
                        value={"pattern": pattern, "fuyin": fuyin, "fanyin": fanyin},
                        effectivePlacements=placements, homeMatchedPalaces=home_matches,
                        oppositeMatchedHomePalaces=opposite_matches, **common)
    if "doorPattern" in chart.data:
        raw = chart.data["doorPattern"]
        comparison = "unknown" if raw is None or raw == "unknown" else "match" if raw == pattern else "conflict"
        result["sourceComparisons"] = [{"pointer": "/doorPattern", "sourceValue": raw,
                                         "derivedValue": pattern, "comparison": comparison}]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    query = sub.add_parser("chart")
    query.add_argument("--json", required=True)
    query.add_argument("--palace", type=int)
    query.add_argument("--layer", choices=FIELDS)
    query.add_argument("--symbol")
    query.add_argument("--metadata", action="store_true")
    palace = sub.add_parser("palace-relation")
    palace.add_argument("--json", required=True)
    palace.add_argument("--from-palace", type=int, required=True)
    palace.add_argument("--to-palace", type=int, required=True)
    xun = sub.add_parser("xun")
    xun_source = xun.add_mutually_exclusive_group(required=True)
    xun_source.add_argument("--json")
    xun_source.add_argument("--ganzhi")
    xun.add_argument("--pillar", required=True, choices=("year", "month", "day", "hour"))
    doors = sub.add_parser("door-pattern")
    doors.add_argument("--json", required=True)
    doors.add_argument("--profile", choices=sorted(PROFILES))
    doors.add_argument("--center-door-host", type=int)
    from theory_lookup import Theory, TheoryError, KINDS, response
    parser.add_argument("--version", action="version", version=VERSION)
    theory = sub.add_parser("theory", help="fixed pure-theory file index, section, or full text")
    theory.add_argument("--files", action="store_true")
    theory.add_argument("--file")
    read_mode = theory.add_mutually_exclusive_group()
    read_mode.add_argument("--full", action="store_true")
    read_mode.add_argument("--sections", action="store_true")
    read_mode.add_argument("--section")
    lookup = sub.add_parser("lookup", help="exact original theory item with conditions and dependencies")
    lookup.add_argument("--kind", choices=KINDS, required=True)
    lookup.add_argument("--item")
    lookup.add_argument("--sky")
    lookup.add_argument("--earth")
    lookup.add_argument("--second")
    lookup.add_argument("--stem-layer", choices=("sky", "earth", "hostedSky", "hostedEarth"))
    life = sub.add_parser("twelve-state", help="original heavenly-stem twelve-stage table")
    life_source = life.add_mutually_exclusive_group(required=True)
    life_source.add_argument("--stem")
    life_source.add_argument("--json")
    life.add_argument("--branch")
    life.add_argument("--palace", type=int)
    life.add_argument("--layer", choices=("sky", "earth", "hostedSky", "hostedEarth"))
    args = parser.parse_args()
    try:
        if args.command == "theory":
            reader = Theory()
            if args.files:
                if args.file or args.full or args.sections or args.section:
                    raise TheoryError("--files cannot combine file or reading options")
                result = reader.files()
            else:
                if not args.file:
                    raise TheoryError("theory requires --files or --file")
                result = reader.read(args.file, full=args.full, section=args.section)
        elif args.command == "lookup":
            if args.kind == "stem":
                if args.item is not None or args.second is not None or args.stem_layer is not None:
                    raise TheoryError("stem lookup uses only explicit --sky and --earth")
            elif args.kind == "door-relation":
                if args.sky is not None or args.earth is not None:
                    raise TheoryError("door-relation uses --item/--second, not sky/earth")
            elif any(v is not None for v in (args.sky, args.earth, args.second, args.stem_layer)):
                raise TheoryError("this item kind does not accept ordered-pair options")
            result = Theory().lookup(args.kind, args.item, args.sky, args.earth, args.second, args.stem_layer)
        elif args.command == "twelve-state":
            if args.json:
                if args.palace is None or args.layer is None:
                    raise TheoryError("chart state query requires explicit --palace and main/hosted --layer")
                fact = Chart(load_json(args.json)).query(args.palace, args.layer)["facts"][0]
                if fact["state"] != "present" or not isinstance(fact["value"], str) or len(fact["value"]) != 1:
                    result = response(fact["state"] if fact["state"] != "present" else "unknown",
                                      reason="selected source layer has no single known stem; no layer substitution", inputFact=fact)
                else:
                    result = Theory().twelve_state(fact["value"], args.branch, None if args.branch else args.palace, fact)
            else:
                if args.layer is not None:
                    raise TheoryError("--layer requires --json")
                result = Theory().twelve_state(args.stem, args.branch, args.palace)
        elif args.command == "chart":
            chart = Chart(load_json(args.json))
            if args.metadata and any(v is not None for v in (args.palace, args.layer, args.symbol)):
                raise InputError("metadata query cannot combine palace/layer/symbol filters")
            result = chart.metadata() if args.metadata else chart.query(args.palace, args.layer, args.symbol)
        elif args.command == "palace-relation":
            result = palace_relation(Chart(load_json(args.json)), args.from_palace, args.to_palace)
        elif args.command == "xun":
            result = xun_from_json(load_json(args.json), args.pillar) if args.json else ganzhi_xun(args.ganzhi, args.pillar, "cli:--ganzhi")
        else:
            result = door_pattern(Chart(load_json(args.json)), args.profile, args.center_door_host)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (InputError, TheoryError, OSError, UnicodeError, json.JSONDecodeError, TypeError, KeyError) as exc:
        print(json.dumps({"error": str(exc), "adapterVersion": VERSION}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())



