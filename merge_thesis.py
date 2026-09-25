#!/usr/bin/env python3
"""
Merge the English thesis PDF with the Hebrew summary PDF so that ALL
internal links (including Hebrew -> English cross-document links) survive
any viewer, including Apple Preview re-saves.

The trick: after merging, every GoTo link that uses a *named* destination
is rewritten to an *explicit* destination (direct page reference + coords).
Explicit destinations don't depend on the /Names tree, so nothing can
strip them.

Usage:
    pip install pikepdf
    python3 merge_thesis.py english.pdf hebrew.pdf merged_out.pdf
"""
import sys
import pikepdf

# Optional aliases: Hebrew link name -> destination name that exists in the
# English PDF. Use this when a Hebrew \hyperlink points at something that has
# no \hypertarget in the English source, by aliasing it to hyperref's automatic
# anchors (section.2.1, definition.3, figure.1.2, theorem.3.1, ...). Those
# automatic names change when numbering changes, so prefer adding a
# \hypertarget{target:...}{} in the English source and leave this empty.
ALIASES = {
    # "target:sec:related": "section.1.6",
}


def collect_named_dests(pdf):
    """name -> destination array, from /Names/Dests and old-style /Dests."""
    dests = {}

    def norm(v):
        # value can be the dest array directly, or a dict with /D
        if isinstance(v, pikepdf.Dictionary) and "/D" in v:
            return v.D
        return v

    root = pdf.Root
    if "/Names" in root and "/Dests" in root.Names:
        def walk(node):
            if "/Names" in node:
                arr = node.Names
                for j in range(0, len(arr), 2):
                    dests[str(arr[j])] = norm(arr[j + 1])
            if "/Kids" in node:
                for k in node.Kids:
                    walk(k)
        walk(root.Names.Dests)
    if "/Dests" in root:  # old-style name dict
        for k, v in root.Dests.items():
            dests[str(k)] = norm(v)
    return dests


def resolve_links(pdf, dests):
    """Rewrite every named GoTo link annotation to an explicit destination."""
    fixed, missing = 0, []
    for page in pdf.pages:
        if "/Annots" not in page:
            continue
        for a in page.Annots:
            if a.get("/Subtype") != "/Link":
                continue
            name = None
            if "/A" in a and str(a.A.get("/S")) == "/GoTo":
                d = a.A.get("/D")
                if isinstance(d, (pikepdf.String, pikepdf.Name)):
                    name = str(d)
            elif "/Dest" in a and isinstance(a.Dest, (pikepdf.String, pikepdf.Name)):
                name = str(a.Dest)
            if name is None:
                continue
            if name not in dests and name in ALIASES:
                name = ALIASES[name]
            if name in dests:
                if "/A" in a:
                    del a["/A"]
                if "/Dest" in a:
                    del a["/Dest"]
                a.Dest = dests[name]
                fixed += 1
            else:
                missing.append(name)
    return fixed, missing


def main(english_path, hebrew_path, out_path):
    eng = pikepdf.open(english_path)
    heb = pikepdf.open(hebrew_path)

    n_eng = len(eng.pages)
    # append Hebrew pages (annotations are copied along)
    eng.pages.extend(heb.pages)

    # merge name tables: English names + Hebrew's own names
    dests = collect_named_dests(eng)          # includes target:* , cite.0@* ...
    heb_dests = collect_named_dests(heb)      # Hebrew's own page.N etc.
    # Hebrew dest arrays reference Hebrew page objects; remap to the copies
    # that now live inside `eng` (pikepdf copies pages, keeping structure).
    # Easiest reliable remap: match by page index.
    # Names defined in BOTH files: the Hebrew-section anchors must win
    # (guards against stray \hypertarget copies left in the English source).
    PREFER_HEBREW = ("chapter:hebrew:",)
    heb_page_objgen = {heb.pages[i].objgen: i for i in range(len(heb.pages))}
    for name, d in heb_dests.items():
        try:
            idx = heb_page_objgen.get(d[0].objgen)
        except Exception:
            idx = None
        if idx is not None:
            new_d = pikepdf.Array([eng.pages[n_eng + idx].obj] + list(d)[1:])
            if name.startswith(PREFER_HEBREW):
                dests[name] = new_d
            else:
                dests.setdefault(name, new_d)

    fixed, missing = resolve_links(eng, dests)
    eng.save(out_path)
    print(f"pages: {len(eng.pages)} | named links resolved to explicit: {fixed}")
    if missing:
        print(f"WARNING - {len(missing)} links point to names that exist in "
              f"neither PDF (left as-is): {sorted(set(missing))}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:4])
