#!/usr/bin/env python3
"""Scrape4: clone skill repos, extract SKILL.md files, static security scan, write scrape4.json."""
import json, os, re, hashlib, subprocess, sys, time, shutil

BASE = r"C:\Users\HP\xomni\data\raw"
OUT = os.path.join(BASE, "scrape4.json")
WORK = os.path.join(BASE, ".scrape4_work")
os.makedirs(WORK, exist_ok=True)
GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0")

REPOS = [
    ("anthropics/skills", "anthropic-official"),
    ("microsoft/skills", "microsoft-official"),
    ("microsoft/SkillOpt", "microsoft-official"),
    ("SnailSploit/Claude-Red", "security-collection"),
    ("gadievron/raptor", "security-collection"),
    ("VoltAgent/awesome-agent-skills", "awesome-collection"),
    ("geekjourneyx/md2wechat-skill", "community"),
    ("qiye45/wechatDownload", "community"),
    ("ciembor/agent-rules-books", "community"),
    ("club-cog/devin-handoff", "devin"),
    ("0xBadai/devin-skills", "devin"),
    ("sudokar/openspec-plus", "devin-adjacent"),
    ("akshay5995/smol", "smol"),
    ("tmc/smol-dev-go", "smol"),
]

# ---------- security scan ----------
URL_ALLOW = re.compile(r"(github\.com|raw\.githubusercontent\.com|gist\.github\.com|anthropic\.com|claude\.ai|openai\.com|google\.com|microsoft\.com|learn\.microsoft\.com|python\.org|pypi\.org|npmjs\.com|nodejs\.org|developer\.mozilla\.org|stackoverflow\.com|w3\.org|json\.org|yaml\.org|example\.com|localhost|127\.0\.0\.1|0\.0\.0\.0|vercel\.com|smithery\.ai|glama\.ai|modelcontextprotocol\.io|docker\.com|kubernetes\.io|aws\.amazon\.com|cloudflare\.com|react\.dev|docs\.anthropic\.com|platform\.openai\.com|npmjs\.com|deno\.land|rust-lang\.org|go\.dev|mcp\.composio\.dev|composio\.dev|cognition\.ai|devin\.ai|smol\.dev|sst\.dev|wikipedia\.org|archive\.org|openspec\.dev|git\.io|bit\.ly|tinyurl\.com|code\.visualstudio\.com|shopify\.dev|stripe\.com|developer\.apple\.com|android\.com|spring\.io|jakarta\.ee|maven\.apache\.org|gradle\.org|pip\.pypa\.io|docs\.python\.org|pandas\.pydata\.org|numpy\.org|scikit-learn\.org|pytorch\.org|tensorflow\.org|huggingface\.co|kaggle\.com|jupyter\.org|anaconda\.com|mysql\.com|postgresql\.org|mongodb\.com|redis\.io|sqlite\.org|elastic\.co|gitlab\.com|bitbucket\.org|sourceforge\.net|crates\.io|rubygems\.org|packagist\.org|mvnrepository\.com|cdnjs\.com|unpkg\.com|jsdelivr\.net|fontawesome\.com|getbootstrap\.com|tailwindcss\.com|nextjs\.org|nuxtjs\.org|svelte\.dev|vuejs\.org|angular\.io|emberjs\.com|djangoproject\.com|flask\.palletsprojects\.com|fastapi\.tiangolo\.com|expressjs\.com|laravel\.com|rubyonrails\.org|springframework\.io|dotnet\.microsoft\.com|golang\.org|gcc\.gnu\.org|llvm\.org|kernel\.org|gnu\.org|freedesktop\.org|gnome\.org|kde\.org|xfce\.org|openstack\.org|apache\.org|eclipse\.org|mozilla\.org|mozilla\.com|apple\.com|amazon\.com|azure\.com|azure\.microsoft\.com|ibm\.com|oracle\.com|salesforce\.com|hubspot\.com|zapier\.com|make\.com|n8n\.io|airtable\.com|notion\.so|figma\.com|adobe\.com|canva\.com|slack\.com|discord\.com|telegram\.org|whatsapp\.com|facebook\.com|instagram\.com|twitter\.com|x\.com|linkedin\.com|youtube\.com|twitch\.tv|reddit\.com|medium\.com|substack\.com|ghost\.org|wordpress\.org|shopify\.com|etsy\.com|ebay\.com|alibaba\.com|taobao\.com|jd\.com|weixin\.qq\.com|qq\.com|weibo\.com|zhihu\.com|bilibili\.com|douyin\.com|tiktok\.com|baidu\.com|aliyuncs\.com|qiniu\.com|upyun\.com|cloudinary\.com|imgur\.com|flickr\.com|pexels\.com|unsplash\.com|shutterstock\.com|gettyimages\.com|envato\.com|freepik\.com|flaticon\.com|iconfinder\.com|gstatic\.com|googleapis\.com|googleusercontent\.com|cloudfront\.net|fastly\.net|akamai\.net|akamaized\.net|cloudflare\.net|w3schools\.com|geeksforgeeks\.org|tutorialspoint\.com|freecodecamp\.org|codecademy\.com|coursera\.org|udemy\.com|edx\.org|khanacademy\.org|wikipedia\.com|wikimedia\.org|wiktionary\.org|wikihow\.com|howstuffworks\.com|investopedia\.com|forbes\.com|cnn\.com|bbc\.com|nytimes\.com|theguardian\.com|reuters\.com|bloomberg\.com|ft\.com|wsj\.com|economist\.com|nature\.com|science\.org|sciencedirect\.com|springer\.com|ieee\.org|acm\.org|arxiv\.org|semanticscholar\.org|pubmed\.ncbi\.nlm\.nih\.gov|ncbi\.nlm\.nih\.gov|doi\.org|crossref\.org|orcid\.org|scholar\.google\.com|maps\.google\.com|earth\.google\.com|weather\.com|accuweather\.com|openweathermap\.org|wunderground\.com|timeanddate\.com|worldtimeapi\.org|ipapi\.co|ipinfo\.io|geoip\.dbip\.db|nominatim\.openstreetmap\.org|openstreetmap\.org|overpass-api\.de|osrm\.org|graphhopper\.com|mapbox\.com|tomtom\.com|here\.com|esri\.com|arcgis\.com|qgis\.org|gdal\.org|geojson\.org|mapproxy\.org|tile\.openstreetmap\.org|tileserver\.com|maptiler\.com|carto\.com|kepler\.gl|deck\.gl|mapbox-gl\.js|leafletjs\.com|openlayers\.org|d3js\.org|chartjs\.org|plotly\.com|highcharts\.com|amcharts\.com|fusioncharts\.com|anychart\.com|google\.co\.in|amazon\.in|flipkart\.com|myntra\.com|ajio\.com|snapdeal\.com|paytm\.com|phonepe\.com|gpay\.com|upi\.org\.in|npi\.org\.in|incometaxindia\.gov\.in|gst\.gov\.in|irctc\.co\.in|nseindia\.com|bseindia\.com|moneycontrol\.com|economictimes\.indiatimes\.com|ndtv\.com|timesofindia\.indiatimes\.com|indianexpress\.com|thehindu\.com|hindustantimes\.com|zeenews\.india\.com|aajtak\.in|news18\.com|reuters\.in|swiggy\.com|zomato\.com|bigbasket\.com|grofers\.com|blinkit\.com|zepto\.com|dmart\.com|reliancefresh\.com|more\.com|naturemade\.com|amazon\.aws|aws\.amazon\.com\.cn|aliyun\.com|tencent\.com|bytedance\.com|baidu\.com\.cn|163\.com|sina\.com\.cn|sohu\.com|ifeng\.com|thepaper\.cn|caixin\.com|yicai\.com|36kr\.com|huxiu\.com|pingwest\.com|jiemian\.com|guancha\.cn|people\.com\.cn|xinhuanet\.com|cctv\.com|china\.com\.cn|gov\.cn|moe\.gov\.cn|pku\.edu\.cn|tsinghua\.edu\.cn|zju\.edu\.cn|fudan\.edu\.cn|sjtu\.edu\.cn|nju\.edu\.cn|whu\.edu\.cn|hit\.edu\.cn|xjtu\.edu\.cn|uestc\.edu\.cn|bupt\.edu\.cn|seu\.edu\.cn|tju\.edu\.cn|tongji\.edu\.cn|ecnu\.edu\.cn|hnu\.edu\.cn|scu\.edu\.cn|sysu\.edu\.cn|xmu\.edu\.cn|sdu\.edu\.cn|jlu\.edu\.cn|dlut\.edu\.cn|neu\.edu\.cn|nwpu\.edu\.cn|nwafu\.edu\.cn|lzu\.edu\.cn|cqu\.edu\.cn|hust\.edu\.cn|uestc\.edu\.cn|buaa\.edu\.cn|bit\.edu\.cn|nankai\.edu\.cn|tjmu\.edu\.cn|smmu\.edu\.cn|fmmu\.edu\.cn|cmu\.edu\.cn|shmu\.edu\.cn|zjum\.edu\.cn|wmu\.edu\.cn|fjmu\.edu\.cn|gxmu\.edu\.cn|kmmu\.edu\.cn|ynu\.edu\.cn|gzu\.edu\.cn|guet\.edu\.cn|gxnu\.edu\.cn|nnnu\.edu\.cn|gxu\.edu\.cn|gxufe\.edu\.cn|gxzmy\.edu\.cn|gxtcmi\.edu\.cn)")

DEFENSIVE_PREFIX = re.compile(r"(never|don'?t|do\s+not|avoid|warning|caution|beware|important|if\s+the\s+user|unless|when\s+asked|malicious|suspicious|ignore\s+any\s+instructions\s+to)", re.I)

RULES = [
    (r"\beval\s*\(", "eval()", 3),
    (r"\bexec\s*\(", "exec()", 3),
    (r"os\.system\s*\(", "os.system()", 3),
    (r"shell\s*=\s*True", "shell=True", 3),
    (r"subprocess\.(run|call|Popen|check_output|check_call)", "subprocess", 3),
    (r"\bPopen\s*\(", "Popen", 3),
    (r"child_process\.(exec|spawn|execSync|spawnSync)", "child_process exec", 3),
    (r"eval\s*\(?\s*[`\"']?(process|os|sys|__import__)", "eval-of-env", 3),
    (r"b64decode|base64\.decodebytes|unhexlify", "base64/hex decode", 2),
    (r"pickle\.loads|marshal\.loads|zlib\.decompress|importlib\.util\.spec_from_file_location", "deserialization", 2),
    (r"[A-Za-z0-9+/]{200,}={0,2}", "large-base64-blob", 2),
    (r"(?:\\x[0-9a-fA-F]{2}){15,}", "hex-escape-blob", 2),
    (r"(sk-[A-Za-z0-9\-]{20,}|ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_\-]{30,}|xox[baprs]-[A-Za-z0-9-]{10,})", "hardcoded-secret-token", 3),
    (r"api[_-]?key\s*[:=]\s*[\"'][^\"']{10,}[\"']", "hardcoded-api-key", 3),
    (r"password\s*[:=]\s*[\"'][^\"']{6,}[\"']", "hardcoded-password", 3),
    (r"secret\s*[:=]\s*[\"'][^\"']{10,}[\"']", "hardcoded-secret", 3),
    (r"(os\.environ|getenv\s*\(|process\.env|env\[)", "env-var-read", 1),
    (r"requests\.(post|put|patch|delete)\s*\(|urllib\.request.*(POST|PUT)|httpx\.(post|put|patch|delete)|aiohttp.*\.post", "network-write", 1),
    (r"(requests|urllib|httpx|aiohttp|axios|fetch)\s*\(?.*(os\.environ|process\.env|getenv|api[_-]?key|password|secret|token)", "env-or-secret-to-network", 3),
    (r"https?://", "url-present", 1),
    (r"ignore\s+(all\s+)?(previous|prior|above|earlier|the\s+above)\s+(instructions|prompts|directives|messages|context)", "ignore-prior-instructions", 2),
    (r"ignore\s+(everything|all)\s+(else|above|before|i\s+said|previous)", "ignore-everything", 2),
    (r"disregard\s+(all\s+)?(previous|prior|above)", "disregard-prior", 2),
    (r"override\s+(all\s+)?(prior|previous)\s+(instructions|rules|prompts)", "override-instructions", 2),
    (r"you\s+are\s+now\s+", "persona-override", 2),
    (r"pretend\s+(you\s+are|to\s+be)", "persona-override", 2),
    (r"(reveal|print|output|show|repeat|paste)\s+(your|the|this)\s+(entire\s+|full\s+|system\s+|initial\s+)?(system\s+)?(prompt|instructions)", "reveal-system-prompt", 2),
    (r"jailbreak", "jailbreak-mention", 2),
    (r"do\s+not\s+(reveal|tell|share|mention|print|repeat)\s+(your|the|this)\s+(system|initial)?\s*(prompt|instructions)", "anti-reveal-defensive", 1),
    (r"never\s+(ignore|disregard|forget)", "defensive-anti-injection", 1),
    (r"prompt\s+injection", "injection-mention", 1),
]

def scan_skill(content, path):
    hits = []
    for rx, label, sev in RULES:
        for m in re.finditer(rx, content, re.I | re.S):
            ctx_start = max(0, m.start() - 50)
            ctx = re.sub(r"\s+", " ", content[ctx_start:m.end() + 30]).strip()
            eff_sev = sev
            eff_label = label
            if sev == 2 and DEFENSIVE_PREFIX.search(content[max(0, m.start() - 70):m.start()]):
                eff_sev = 1
                eff_label = "defensive-" + label
            hits.append((eff_label, eff_sev, ctx[:120]))
    # URL host analysis
    unknown_hosts = set()
    for m in re.finditer(r"https?://([A-Za-z0-9._\-]+)", content):
        host = m.group(1).lower()
        if host.startswith("www."):
            host = host[4:]
        if not URL_ALLOW.search(host):
            unknown_hosts.add(host)
    for h in sorted(unknown_hosts)[:5]:
        hits.append(("unknown-host:" + h, 1, h))
    sev_max = max([s for _, s, _ in hits], default=0)
    verdict = "PASS" if sev_max < 2 else ("REVIEW" if sev_max == 2 else "REJECT")
    # escalate: any reject-level hit => REJECT (already); downgrade defensive-labeled sev-3? no.
    # Build notes
    notes = []
    for label, sev, ctx in hits[:12]:
        notes.append(f"{path}: {label} [sev{sev}] :: {ctx}")
    return verdict, notes, hits

def sha256(b):
    return hashlib.sha256(b).hexdigest()

def parse_frontmatter(text):
    name, desc, lic = "", "", ""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            fm = text[3:end]
            for line in fm.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip().lower(), v.strip().strip("\"'")
                    if k in ("name", "title") and not name:
                        name = v
                    elif k in ("description", "summary") and not desc:
                        desc = v
                    elif k == "license" and not lic:
                        lic = v
    return name, desc, lic

def read_license(repo_dir):
    for fn in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md", "LICENSE-MIT", "LICENSE-APACHE"):
        p = os.path.join(repo_dir, fn)
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    return f.read(300).strip().replace("\n", " | ")
            except Exception:
                return fn
    return ""

def default_branch(repo_dir):
    try:
        r = subprocess.run(["git", "-C", repo_dir, "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True, timeout=20)
        b = r.stdout.strip()
        return b if b else "main"
    except Exception:
        return "main"

def main():
    items = []
    stats = {}
    # load existing partial
    if os.path.exists(OUT):
        try:
            items = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            items = []
    done_repos = {it.get("source") for it in items}
    for repo, cat in REPOS:
        if repo in done_repos and not os.environ.get("FORCE"):
            print(f"SKIP {repo} (already in output)")
            continue
        safe = repo.replace("/", "__")
        d = os.path.join(WORK, safe)
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
        print(f"CLONE {repo} ...", flush=True)
        t0 = time.time()
        try:
            r = subprocess.run(["git", "clone", "--depth", "1", "--single-branch",
                                f"https://github.com/{repo}.git", d],
                               capture_output=True, text=True, timeout=180, env=GIT_ENV)
            if r.returncode != 0:
                print(f"  clone FAILED: {r.stderr[:200]}", flush=True)
                stats[repo] = "clone-failed"
                continue
        except Exception as e:
            print(f"  clone EXC: {e}", flush=True)
            stats[repo] = "clone-exc"
            continue
        print(f"  cloned in {time.time()-t0:.0f}s", flush=True)
        lic = read_license(d)
        branch = default_branch(d)
        files = []
        for root, dirs, fns in os.walk(d):
            if ".git" in root:
                continue
            for fn in fns:
                if fn.lower() == "skill.md":
                    files.append(os.path.join(root, fn))
        files.sort()
        print(f"  SKILL.md files: {len(files)}", flush=True)
        stats[repo] = len(files)
        n_added = 0
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
                continue
            if len(content) > 150000:
                continue
            rel = os.path.relpath(fp, d).replace("\\", "/")
            name, desc, fm_lic = parse_frontmatter(content)
            if not name:
                name = os.path.basename(os.path.dirname(fp))
            cat_parts = rel.split("/")
            category = cat_parts[0] if len(cat_parts) > 1 else "root"
            category = f"{cat}::{category}" if category not in ("", "root") else cat
            url = f"https://github.com/{repo}/blob/{branch}/{rel}"
            verdict, notes, hits = scan_skill(content, rel)
            item = {
                "name": name,
                "source": repo,
                "source_url": url,
                "category": category,
                "description": desc,
                "content": content,
                "sha256": sha256(content.encode("utf-8")),
                "license": fm_lic or lic,
                "scan_verdict": verdict,
                "scan_notes": notes,
            }
            items.append(item)
            n_added += 1
        # write incrementally
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)
        print(f"  +{n_added} items, total {len(items)}", flush=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    # summary
    from collections import Counter
    vc = Counter(i["scan_verdict"] for i in items)
    print("\n=== SUMMARY ===")
    print(f"total items: {len(items)}")
    print(f"verdicts: {dict(vc)}")
    print(f"repos: {json.dumps(stats)}")
    by_repo = Counter(i["source"] for i in items)
    print(f"items per repo: {json.dumps(dict(by_repo))}")
    # top findings: REJECTs and notable REVIEWs
    print("\n=== REJECTS ===")
    for i in items:
        if i["scan_verdict"] == "REJECT":
            print(f"- {i['source']}/{i['name']}")
            for n in i["scan_notes"][:4]:
                print(f"    {n[:160]}")
    print("\n=== REVIEW (first 3 notes each) ===")
    for i in items:
        if i["scan_verdict"] == "REVIEW":
            print(f"- {i['source']}/{i['name']}: {i['scan_notes'][0][:140] if i['scan_notes'] else ''}")

if __name__ == "__main__":
    main()
