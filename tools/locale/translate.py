# OpenMap's translations. The code's text is English, looked up through ns.L["English"] (Core.lua: the
# English itself where a language has no translation of it). Each language's translations are kept in
# tools/locale/<locale>.json ({ "English": "translation" }); from them this writes
#   OpenMap/Locales/<locale>.lua   the translations the code uses now (each loads only in its own client)
#   the toc's "## Notes-<locale>:" lines (the addon list's description), from the "@toc-notes" entry
#
#   python -P tools/locale/translate.py export   tools/locale/strings.json: every text to translate, where
#                                             it's used (for a translator: the English, the files)
#   python -P tools/locale/translate.py build    the Lua files and the toc lines from the JSON
#   python -P tools/locale/translate.py status   how much of each language is translated
#   python -P tools/locale/translate.py check deDE   one language's JSON checked (nothing written)
# lint (tools/offline-test/lint.py) checks the translations (problems()): their placeholders (%s, %d ...),
# colour codes and line breaks the same as the English's, and the Lua files built from the JSON as it is.
import glob, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
ADDON = os.path.join(REPO, "OpenMap")
OUT = os.path.join(ADDON, "Locales")
TOC = os.path.join(ADDON, "OpenMap.toc")
NOTES_KEY = "@toc-notes"         # (the toc's own Notes line, translated)

# the client languages WoW has, besides English
LOCALES = ["deDE", "esES", "esMX", "frFR", "itIT", "koKR", "ptBR", "ruRU", "zhCN", "zhTW"]

LIT = r'"((?:[^"\\]|\\.)*)"'
KEY = re.compile(r'(?<![\w.])(?:ns\.)?L\[\s*' + LIT + r'\s*\]')


def unescape(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            out.append({"n": "\n", "t": "\t", '"': '"', "'": "'", "\\": "\\"}.get(n, "\\" + n))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")


def code_strings():
    """every L["..."] in the addon's code: English -> [ "file:line", ... ]"""
    found = {}
    for path in sorted(glob.glob(os.path.join(ADDON, "**", "*.lua"), recursive=True)):
        rel = os.path.relpath(path, ADDON).replace("\\", "/")
        if rel.startswith(("Libs/", "Locales/")): continue
        for i, line in enumerate(io.open(path, encoding="utf-8"), 1):
            if line.lstrip().startswith("--"): continue
            for m in KEY.finditer(line):
                found.setdefault(unescape(m.group(1)), []).append("%s:%d" % (rel, i))
    return found


def toc_notes():
    for line in io.open(TOC, encoding="utf-8"):
        if line.startswith("## Notes:"): return line[len("## Notes:"):].strip()


def load(loc):
    p = os.path.join(HERE, loc + ".json")
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}


# ---------------------------------------------------------------- checks
SPEC = re.compile(r"%(?:(\d+)\$)?[-+ #0]*\d*(?:\.\d+)?([sdfgixXcq%])")


def specs(s):
    """the format specifiers in order, as the arguments they take: [(argument number, type), ...]"""
    out, n = [], 0
    for m in SPEC.finditer(s):
        if m.group(2) == "%": continue
        n += 1
        out.append((int(m.group(1)) if m.group(1) else n, m.group(2).replace("i", "d")))
    return sorted(out)


def marks(s):
    """what must come through as it is: colour codes and their ends, textures, line breaks, slash commands"""
    return (sorted(re.findall(r"\|c[0-9a-fA-F]{8}", s)), s.count("|r"), sorted(re.findall(r"\|T[^|]*\|t", s)),
            s.count("\n"), sorted(re.findall(r"/openmap(?: \w+)?", s)))


def text_problems(loc, tr, code, stale=True):
    """a language's translations against the English: what would break or show wrong in game (and, `stale`,
    what the code no longer has: left out of the build, so not a problem for lint)"""
    out = []
    for en, t in tr.items():
        if en == NOTES_KEY or not t: continue
        if not isinstance(t, str):
            out.append("tools/locale/%s.json: %r: not a string" % (loc, en[:50])); continue
        if en not in code:
            if not stale: continue
            out.append("tools/locale/%s.json: %r: no longer in the code (or not quite its English)" % (loc, en[:60])); continue
        if specs(en) != specs(t):
            out.append("tools/locale/%s.json: %r: placeholders %s, the English's %s" % (loc, en[:60], specs(t), specs(en)))
        if marks(en) != marks(t):
            out.append("tools/locale/%s.json: %r: colour codes, textures, line breaks or commands differ from the English's" % (loc, en[:60]))
    return out


def problems():
    out = []
    code = code_strings()
    for loc in LOCALES:
        tr = load(loc)
        out += text_problems(loc, tr, code, stale=False)
        want = render(loc, tr, code)
        p = os.path.join(OUT, loc + ".lua")
        if tr and (not os.path.exists(p) or io.open(p, encoding="utf-8").read() != want):
            out.append("OpenMap/Locales/%s.lua is out of date with tools/locale/%s.json: run python -P tools/locale/translate.py build" % (loc, loc))
    return out


# ---------------------------------------------------------------- build
def render(loc, tr, code):
    keys = [k for k in sorted(code) if tr.get(k)]
    lines = [
        "-- %s translations of OpenMap's text: L[\"English\"] = \"translation\" (Core.lua's ns.L)." % loc,
        "-- Generated by tools/locale/translate.py from tools/locale/%s.json; regenerate rather than edit." % loc,
        "",
        "local _, ns = ...",
        "if GetLocale() ~= \"%s\" then return end" % loc,
        "local L = ns.L",
        "",
    ]
    for k in keys:
        lines.append('L["%s"] = "%s"' % (escape(k), escape(tr[k])))
    return "\n".join(lines) + "\n"


def build():
    code = code_strings()
    os.makedirs(OUT, exist_ok=True)
    notes = {}
    for loc in LOCALES:
        tr = load(loc)
        if not tr: continue
        io.open(os.path.join(OUT, loc + ".lua"), "w", encoding="utf-8", newline="\n").write(render(loc, tr, code))
        if tr.get(NOTES_KEY): notes[loc] = tr[NOTES_KEY].replace("\n", " ")
        n = sum(1 for k in code if tr.get(k))
        print("%s: %d of %d" % (loc, n, len(code)))
    # the toc: its Notes-<locale> lines after its Notes line, in the locales' order
    toc = [l for l in io.open(TOC, encoding="utf-8").read().split("\n") if not l.startswith("## Notes-")]
    at = next(i for i, l in enumerate(toc) if l.startswith("## Notes:"))
    toc[at + 1:at + 1] = ["## Notes-%s: %s" % (loc, notes[loc]) for loc in LOCALES if loc in notes]
    io.open(TOC, "w", encoding="utf-8", newline="\n").write("\n".join(toc))
    bad = problems()
    for p in bad: print(p)


def export():
    code = code_strings()
    data = [{"en": NOTES_KEY, "text": toc_notes(), "where": ["OpenMap.toc (the addon list's description)"]}]
    data += [{"en": k, "where": v} for k, v in sorted(code.items())]
    p = os.path.join(HERE, "strings.json")
    json.dump(data, io.open(p, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print("wrote %s: %d texts" % (os.path.relpath(p, REPO), len(data)))


def status():
    code = code_strings()
    print("%d texts in the code" % len(code))
    for loc in LOCALES:
        tr = load(loc)
        print("  %s: %d translated, %d missing, %d no longer used" % (loc, sum(1 for k in code if tr.get(k)),
              sum(1 for k in code if not tr.get(k)), sum(1 for k in tr if k not in code and k != NOTES_KEY)))


def check(loc):
    """one language's JSON alone (nothing written): its problems, and what it hasn't translated"""
    code = code_strings()
    tr = load(loc)
    bad = text_problems(loc, tr, code)
    for p in bad: print(p)
    missing = [k for k in sorted(code) if not tr.get(k)]
    if not tr.get(NOTES_KEY): missing.insert(0, NOTES_KEY)
    for k in missing: print("missing: %r" % k[:80])
    print("%s: %d problem(s), %d missing, %d of %d translated" % (loc, len(bad), len(missing), len(code) - len([k for k in missing if k != NOTES_KEY]), len(code)))
    sys.exit(1 if bad or missing else 0)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "check" and len(sys.argv) > 2: check(sys.argv[2])
    else: {"export": export, "build": build, "status": status}.get(cmd, lambda: sys.exit("export | build | status | check <locale>"))()
