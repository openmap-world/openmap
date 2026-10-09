# Downloads every overlay texture named in the reveal data (cached; skips existing).
import re, sys, time, os, urllib.request
reveal, out = sys.argv[1], sys.argv[2]
s = open(reveal, encoding="utf-8").read()
ids = sorted(set(x.strip() for v in re.findall(r'\] = "([^"]+)"', s) for x in v.split(",")))
done = fail = 0
for i in ids:
    p = os.path.join(out, i + ".blp")
    if os.path.exists(p) and os.path.getsize(p) > 0: done += 1; continue
    try:
        req = urllib.request.Request("https://wago.tools/api/casc/%s?download" % i, headers={"User-Agent": "openmap-tools/1"})
        data = urllib.request.urlopen(req, timeout=30).read()
        open(p, "wb").write(data); done += 1
    except Exception as e:
        fail += 1; print("fail", i, e, flush=True)
    time.sleep(0.15)
print("done", done, "failed", fail, flush=True)
