"""Exact excerpts from this package's fixed pure-theory files; Python stdlib only."""
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat

VERSION = "0.2.2"
STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
ALLOWED = (
    "references/principles.md", "references/terminology.md", "references/symbols.md",
    "references/patterns.md", "references/timing.md", "references/patterns/stem-relations.md",
    "references/tables/door-relations.md", "references/tables/doors.md", "references/tables/gods.md",
    "references/tables/palace-images.md", "references/tables/stars.md", "references/tables/states.md",
    "references/tables/stems-branches.md", "references/topics/business-wealth.md",
    "references/topics/examination.md", "references/topics/litigation.md",
    "references/topics/lost-property.md", "references/topics/other-topics.md",
    "references/topics/work-transfer.md",
)
TABLES = {"star": "stars", "door": "doors", "god": "gods", "palace": "palace-images",
          "stem-symbol": "stems-branches", "branch": "stems-branches"}
KINDS = ("topic", "star", "door", "god", "palace", "stem", "door-relation", "stem-symbol", "branch", "section", "any")
DECLARED_NAME = re.compile(r'(?:名曰|名为|名谓|故名|又名|又叫|故曰)[“"]([^”"\r\n]+)[”"]')
EXPLICIT_NAMED_REFERENCES = (
    re.compile(r'(?:参照|参看|参见|对照|参考)\s*[“"]([^”"\r\n]+)[”"]'),
    re.compile(r'(?:同|与)\s*[“"]([^”"\r\n]+)[”"]\s*(?:格|之格)?\s*(?:正好|刚好|正)?\s*(?:一样|相同|相反|不同|类似|相比|相较)'),
    re.compile(r'如\s*[“"]([^”"\r\n]+)[”"]\s*(?:格|之格)?\s*(?:所述|所说|所论|所示)'),
)


class TheoryError(ValueError):
    pass


def safe_file(root, relative):
    """Reject escapes and every reparse component before opening any source file."""
    if not isinstance(relative, str) or not relative or relative != relative.strip():
        raise TheoryError("file must be an exact package-relative pure-theory path")
    name = relative.replace("\\", "/")
    parts = name.split("/")
    if (PurePosixPath(name).is_absolute() or PureWindowsPath(relative).is_absolute()
            or any(part in ("", ".", "..") or part.startswith(".") for part in parts)
            or ":" in name or any(ord(ch) < 32 for ch in name) or name not in ALLOWED):
        raise TheoryError("file is outside the fixed pure-theory whitelist")
    root = Path(root).absolute()
    current = root
    for component in (None, *parts):
        if component is not None:
            current = current / component
        status = current.lstat()
        if stat.S_ISLNK(status.st_mode) or getattr(status, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise TheoryError("symlink/junction/reparse sources are not allowed")
    resolved = current.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve(strict=True)) or not resolved.is_file():
        raise TheoryError("source must be a regular file within this package")
    return name, resolved


class Document:
    def __init__(self, root, relative):
        self.path, path = safe_file(root, relative)
        self.raw = path.read_bytes()
        self.lines = self.raw.decode("utf-8").splitlines(keepends=True)
        if not self.lines:
            raise TheoryError("empty theory source")
        self.offsets = [0]
        for line in self.lines:
            self.offsets.append(self.offsets[-1] + len(line.encode("utf-8")))
        self.title = self.lines[0].strip().lstrip("\ufeff# ")

    def text(self, start, end):
        return "".join(self.lines[start - 1:end])

    def fragment(self, start, end, roles):
        if not 1 <= start <= end <= len(self.lines):
            raise TheoryError("source line range is invalid")
        return {"file": self.path, "title": self.title, "roles": sorted(roles),
                "lineRange": {"start": start, "end": end},
                "utf8ByteRange": {"start": self.offsets[start - 1], "end": self.offsets[end], "endExclusive": True},
                "text": self.text(start, end)}

    def excerpts(self, spans):
        merged = []
        for start, end, role in sorted(spans):
            if start > end:
                continue
            if merged and start <= merged[-1][1] + 1:
                a, b, roles = merged[-1]
                merged[-1] = (a, max(end, b), roles | {role})
            else:
                merged.append((start, end, {role}))
        return [self.fragment(a, b, roles) for a, b, roles in merged]

    def sections(self):
        headings = [(i, line.strip().lstrip("# ")) for i, line in enumerate(self.lines, 1)
                    if re.match(r"#{2,6} ", line)]
        if not headings:
            return [{"label": self.title, "start": 1, "end": len(self.lines)}]
        return [{"label": label, "start": start, "end": headings[j + 1][0] - 1 if j + 1 < len(headings) else len(self.lines)}
                for j, (start, label) in enumerate(headings)]

    def footer_start(self):
        positions = [i for i, line in enumerate(self.lines, 1) if line.startswith("出处：")]
        return positions[-1] if positions else len(self.lines) + 1

    def common(self, first, footer=None):
        spans = [(1, first - 1, "sharedPremise")]
        footer = self.footer_start() if footer is None else footer
        if footer <= len(self.lines):
            spans.append((footer, len(self.lines), "sharedConclusionAndSource"))
        return spans


def response(state="present", **values):
    return {"toolVersion": VERSION, "state": state, **values}


class Theory:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def doc(self, relative):
        return Document(self.root, relative)

    def files(self):
        return response(files=[{"file": name, "title": self.doc(name).title} for name in ALLOWED],
                        boundary="fixed package pure-theory whitelist; no case or arbitrary-path search")

    def read(self, relative, full=False, section=None):
        doc = self.doc(relative)
        if full and section is not None:
            raise TheoryError("full and section cannot be combined")
        if full:
            return response(scope="full", sources=[doc.fragment(1, len(doc.lines), {"fullText"})])
        sections = doc.sections()
        if section is None:
            return response(file=doc.path, title=doc.title, sections=sections, fullRead={"command": "theory", "file": doc.path, "full": True})
        matches = [s for s in sections if section == s["label"]] or [s for s in sections if section in s["label"]]
        if len(matches) != 1:
            return response("unknown", reason="ambiguous section" if matches else "no matching section", candidates=matches)
        selected = matches[0]
        spans = doc.common(sections[0]["start"]) + [(selected["start"], selected["end"], "selectedSection")]
        if ("共用" in sections[0]["label"] or doc.path.startswith("references/topics/") and any(word in sections[0]["label"] for word in ("先问清", "对象", "考生", "当事人", "一般钱物"))):
            spans.append((sections[0]["start"], sections[0]["end"], "topicObjectPremise"))
        return response(scope="partial", item=selected["label"], sources=doc.excerpts(spans), fullRead={"command": "theory", "file": doc.path, "full": True})

    def entries(self, kind):
        if kind == "topic":
            names = [n for n in ALLOWED if n.startswith("references/topics/")]
        elif kind in TABLES:
            names = ["references/tables/" + TABLES[kind] + ".md"]
        elif kind in ("section", "any"):
            names = list(ALLOWED)
        else:
            raise TheoryError("kind has a dedicated ordered query")
        rows = []
        for name in names:
            doc = self.doc(name)
            sections = doc.sections()
            if kind in ("topic", "section", "any", "palace"):
                records = sections
            else:
                marks = [(i, re.sub(r"^[（(][^）)]+[）)]", "", match.group(1)).strip())
                         for i, line in enumerate(doc.lines, 1)
                         if (match := re.match(r"\*\*([^：]+)：\*\*", line))]
                footer = doc.footer_start()
                if kind == "door":
                    footer = next((i for i, line in enumerate(doc.lines, 1) if line.startswith("八门在五行上")), footer)
                elif kind == "god":
                    footer = next((i for i, line in enumerate(doc.lines, 1) if line.startswith("八神运行的规律")), footer)
                records = [{"label": label, "start": start, "end": min(marks[j + 1][0] - 1 if j + 1 < len(marks) else footer - 1, footer - 1)}
                           for j, (start, label) in enumerate(marks)]
                if kind in ("stem-symbol", "branch"):
                    chars = STEMS if kind == "stem-symbol" else BRANCHES
                    records = [row for row in records if row["label"] in chars]
                    # The final bold item stops at the next actual heading, not the next distant bold item.
                    for row in records:
                        next_heading = next((s["start"] for s in sections if s["start"] > row["start"]), len(doc.lines) + 1)
                        row["end"] = min(row["end"], next_heading - 1)
            first = records[0]["start"] if records else 1
            for row in records:
                aliases = {row["label"]}
                if kind == "star": aliases.add(row["label"].removesuffix("星"))
                if kind == "door": aliases.add(row["label"].removesuffix("门"))
                if kind == "god": aliases.add(row["label"].split("（")[0])
                if kind == "palace":
                    match = re.search(r"([乾坤震巽坎离艮兑])卦", row["label"])
                    if match: aliases.update((match[1], match[1] + "宫", match[1] + "卦"))
                    # Index only the original explicitly labelled latter-heaven/nine-palace number.
                    number = re.search(r"([一二三四五六七八九])（(?:后天八卦数|九宫数)", doc.text(row["start"], row["end"]))
                    if number:
                        aliases.update((number[1], str("一二三四五六七八九".index(number[1]) + 1)))
                extra_premise = None
                common_first = first
                if kind == "branch":
                    common_first = sections[0]["start"]
                    parent = next(s for s in sections if "十二地支所主" in s["label"])
                    extra_premise = (parent["start"], first - 1)
                rows.append({**row, "file": name, "aliases": sorted(aliases), "first": common_first,
                             "extraPremise": extra_premise, "kind": kind})
        return rows

    def lookup(self, kind, item=None, sky=None, earth=None, second=None, stem_layer=None):
        if kind == "stem":
            return self.stem(sky, earth)
        if kind == "door-relation":
            return self.door_relation(item, second, stem_layer)
        if not isinstance(item, str) or not item.strip():
            raise TheoryError("item must be a nonempty item/section label")
        entries = self.entries(kind)
        exact = [row for row in entries if item in row["aliases"]]
        title_matches = [row for row in entries if item in row["label"]]
        body_matches = [row for row in entries if item in self.doc(row["file"]).text(row["start"], row["end"])]
        matches = exact or title_matches or body_matches
        if len(matches) != 1:
            return response("unknown", reason="ambiguous item; specify kind or exact section" if matches else "no entry in current theory", candidates=[{k: row[k] for k in ("file", "label", "start", "end")} for row in matches])
        row = matches[0]
        doc = self.doc(row["file"])
        footer = doc.footer_start()
        if kind == "door": footer = next((i for i, line in enumerate(doc.lines, 1) if line.startswith("八门在五行上")), footer)
        if kind == "god": footer = next((i for i, line in enumerate(doc.lines, 1) if line.startswith("八神运行的规律")), footer)
        spans = doc.common(row["first"], footer) + [(row["start"], row["end"], "selectedItem")]
        if row.get("extraPremise"):
            spans.append((*row["extraPremise"], "sectionPremise"))
        # Retain the topic's explicit initial object/role section as shared prerequisites.
        if kind in ("topic", "section", "any"):
            first = doc.sections()[0]
            if "共用" in first["label"] or doc.path.startswith("references/topics/") and any(word in first["label"] for word in ("先问清", "对象", "考生", "当事人", "一般钱物")):
                spans.append((first["start"], first["end"], "topicObjectPremise"))
        return response(scope="partial", kind=kind, item=row["label"], sources=doc.excerpts(spans),
                        fullRead={"command": "theory", "file": doc.path, "full": True})

    def stem_records(self):
        doc = self.doc("references/patterns/stem-relations.md")
        rows = []
        for i, line in enumerate(doc.lines, 1):
            match = re.match(r"([甲乙丙丁戊己庚辛壬癸])/([甲乙丙丁戊己庚辛壬癸])，", line)
            if match:
                end = i
                while end < len(doc.lines) and doc.lines[end].strip(): end += 1
                rows.append({"key": match[1] + "/" + match[2], "start": i, "end": end})
        return doc, rows

    @staticmethod
    def original_evidence(doc, row, match):
        """A literal matched wording span, not a label-similarity inference."""
        text = doc.text(row["start"], row["end"])
        prefix = text[:match.start()]
        start = doc.offsets[row["start"] - 1] + len(prefix.encode("utf-8"))
        return {"file": doc.path, "lineRange": {"start": row["start"] + prefix.count("\n"),
                                                "end": row["start"] + text[:match.end()].count("\n")},
                "utf8ByteRange": {"start": start, "end": start + len(match.group().encode("utf-8")), "endExclusive": True},
                "text": match.group()}

    def stem(self, sky, earth):
        if not isinstance(sky, str) or not isinstance(earth, str) or len(sky) != 1 or len(earth) != 1 or sky not in STEMS or earth not in STEMS:
            raise TheoryError("sky and earth must each be one explicit heavenly stem")
        doc, rows = self.stem_records()
        by_key = {row["key"]: row for row in rows}
        key, reverse = sky + "/" + earth, earth + "/" + sky
        if key not in by_key:
            return response("unknown", reason="no such ordered pair in original table; hidden Jia not substituted automatically", sky=sky, earth=earth)
        spans = doc.common(rows[0]["start"], next((i for i, line in enumerate(doc.lines, 1) if line.startswith("以上九个天干")), doc.footer_start()))
        selected, pending, dependency, unresolved = set(), [(key, "selectedOrderedPair")], [], []
        if reverse != key and reverse in by_key: pending.append((reverse, "reverseComparison"))
        labels, definitions = {}, {}
        for row in rows:
            text = doc.text(row["start"], row["end"])
            for match in DECLARED_NAME.finditer(text):
                label = match[1]
                labels.setdefault(label, set()).add(row["key"])
                definitions.setdefault((label, row["key"]), self.original_evidence(doc, row, match))
        while pending:
            current, role = pending.pop(0)
            row = by_key[current]
            spans.append((row["start"], row["end"], role))
            if current in selected: continue
            selected.add(current)
            text = doc.text(row["start"], row["end"])
            index = rows.index(row)
            previous_reference = re.search(r"前者|与前|上述|同前|同上|上文|同理|前边", text)
            if previous_reference and index:
                previous = rows[index - 1]["key"]
                dependency.append({"from": current, "to": previous, "basis": "original preceding-reference wording",
                                   "evidence": self.original_evidence(doc, row, previous_reference)})
                pending.append((previous, "precedingDependency"))
            for pattern in EXPLICIT_NAMED_REFERENCES:
                for match in pattern.finditer(text):
                    quote = match[1]
                    targets = labels.get(quote, set())
                    evidence = self.original_evidence(doc, row, match)
                    if re.search(r'(?:不|勿|莫|未|无需|无须|不得|不可|并非|不是|非)\s*(?:应|宜|要|再|直接|自动)?\s*$', text[max(0, match.start() - 10):match.start()]):
                        unresolved.append({"from": current, "name": quote, "candidates": sorted(targets),
                                           "reason": "reference wording is negated; no affirmative cross-entry assertion", "evidence": evidence})
                        continue
                    if len(targets) != 1 or current in targets:
                        unresolved.append({"from": current, "name": quote, "candidates": sorted(targets),
                                           "reason": "named target absent, ambiguous, or self-reference; no cross-entry assertion",
                                           "evidence": evidence})
                        continue
                    target = next(iter(targets))
                    dependency.append({"from": current, "to": target, "basis": "original named comparison",
                                       "evidence": evidence, "targetDefinitionEvidence": definitions[quote, target]})
                    if target not in selected:
                        pending.append((target, "namedDependency"))
        return response(scope="partial", kind="stem", sky=sky, earth=earth,
                        layerConvention={"sky": "天盘所指定干", "earth": "地盘所指定干", "hosted": "主干/寄干由调用者显式给定；不从别层拼接"},
                        dependencyLinks=dependency, unresolvedNamedReferences=unresolved,
                        namedReferencePolicy="Only explicit original reference/comparison wording with an unambiguous other entry is linked; shared names alone do not add an entry.",
                        sources=doc.excerpts(spans), fullRead={"command": "theory", "file": doc.path, "full": True})

    def door_relation(self, first, second, stem_layer):
        doors = "开休生伤杜景死惊"
        first = first.removesuffix("门") if isinstance(first, str) else first
        second = second.removesuffix("门") if isinstance(second, str) else second
        if not isinstance(first, str) or not isinstance(second, str) or len(first) != 1 or len(second) != 1 or first not in doors or second not in doors + STEMS:
            raise TheoryError("door-relation needs one door and an explicit second door/stem")
        if second in STEMS and stem_layer not in ("sky", "earth", "hostedSky", "hostedEarth"):
            return response("unknown", reason="door-plus-stem layer is unspecified in original table; explicitly identify the actual layer")
        if second in doors and stem_layer is not None:
            raise TheoryError("door-plus-door does not accept a stem-layer declaration")
        doc = self.doc("references/tables/door-relations.md")
        match = [(i, line) for i, line in enumerate(doc.lines, 1)
                 if (parsed := re.match(r"([开休生伤杜景死惊])加([开休生伤杜景死惊甲乙丙丁戊己庚辛壬癸、]+)：", line))
                 and parsed[1] == first and second in parsed[2].split("、")]
        if len(match) != 1: return response("unknown", reason="no unique entry in original door table")
        first_item = next(i for i, line in enumerate(doc.lines, 1) if line.startswith("**"))
        row = match[0][0]
        return response(scope="partial", kind="door-relation", first=first, second=second, stemLayer=stem_layer,
                        layerConvention="活动门/本位门须由当前盘式另行确认；此命令仅取原文，不从名字反推布局。",
                        sources=doc.excerpts(doc.common(first_item) + [(row, row, "selectedOrderedPair")]),
                        fullRead={"command": "theory", "file": doc.path, "full": True})

    def state_table(self):
        doc = self.doc("references/tables/states.md")
        header = next((i for i, line in enumerate(doc.lines, 1) if line.startswith("|干|")), None)
        if header is None: raise TheoryError("twelve-state table header missing")
        columns = doc.lines[header - 1].strip().strip("|").split("|")[1:]
        if len(columns) != 12 or len(set(columns)) != 12: raise TheoryError("invalid twelve-state columns")
        cells = {}
        for i in range(header + 2, len(doc.lines) + 1):
            line = doc.lines[i - 1].strip()
            if not line.startswith("|"): break
            values = line.strip("|").split("|")
            if len(values) != 13 or set(values[1:]) != set(BRANCHES): raise TheoryError("invalid twelve-state source row")
            for stem in values[0].split("、"):
                if stem not in STEMS or len(stem) != 1 or stem in cells: raise TheoryError("invalid/duplicate stem row")
                cells[stem] = {branch: {"value": name, "row": i, "column": j + 2} for j, (name, branch) in enumerate(zip(columns, values[1:]))}
        return doc, header, cells

    def twelve_state(self, stem, branch=None, palace=None, input_fact=None):
        if not isinstance(stem, str) or len(stem) != 1 or stem not in STEMS:
            raise TheoryError("stem must be one explicit heavenly stem")
        if branch is not None and (not isinstance(branch, str) or len(branch) != 1 or branch not in BRANCHES):
            raise TheoryError("branch must be one explicit earthly branch")
        if branch is not None and palace is not None: raise TheoryError("branch and palace cannot be combined")
        if palace is not None and (type(palace) is not int or not 1 <= palace <= 9): raise TheoryError("palace must be 1..9")
        doc, header, cells = self.state_table()
        section = next(s for s in doc.sections() if s["label"] == "天干寄生十二状态")
        conditions = [(1, doc.sections()[0]["start"] - 1, "sharedPremise"),
                      (section["start"], header - 1, "tableConvention"), (header, header + 1, "columnHeader")]
        last_table = max((v["row"] for row in cells.values() for v in row.values()), default=header)
        conditions.append((last_table + 1, section["end"], "applicationConditionsAndSource"))
        # Monthly strength remains a separate relation; return its actual conditions, never a synthesized score.
        month = next(s for s in doc.sections() if s["label"] == "五行与月令")
        conditions.append((month["start"], month["end"], "monthOrderCondition"))
        branches, palace_source = [branch] if branch else [], None
        if palace is not None:
            numerals = "一二三四五六七八九"
            for i, line in enumerate(doc.lines, 1):
                mappings = re.findall(r"([一二三四六七八九])宫(?:含)?([子丑寅卯辰巳午未申酉戌亥]+)", line)
                if mappings:
                    mapping = {numerals.index(n) + 1: list(bs) for n, bs in mappings}
                    branches = mapping.get(palace, [])
                    palace_source = doc.fragment(i, i, {"palaceBranchMapping"})
                    break
        if not branches:
            return response("unknown", reason="no explicit branch; center has no invented branch or implicit hosting", stem=stem, palace=palace, inputFact=input_fact,
                            sources=doc.excerpts(conditions), palaceBranchSource=palace_source)
        if stem not in cells: return response("unknown", reason="no stem row in current source table")
        result = []
        for selected in branches:
            cell = cells[stem][selected]
            conditions.append((cell["row"], cell["row"], "selectedOriginalRow"))
            result.append({"stem": stem, "branch": selected, "value": cell["value"], "tableRow": cell["row"], "tableColumn": cell["column"]})
        return response(scope="partial", convention="天干寄生十二状态原表；并非字段可用状态，也非地支五行十二状态；各地支分别列值，不合成宫状态。",
                        values=result, palace=palace, inputFact=input_fact, palaceBranchSource=palace_source,
                        sources=doc.excerpts(conditions), fullRead={"command": "theory", "file": doc.path, "full": True})
