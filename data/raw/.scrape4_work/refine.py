#!/usr/bin/env python3
"""Refine scrape4: re-scan with bounded rules, trim per-source caps, rewrite scrape4.json."""
import json, os, re
from collections import Counter

BASE = r"C:\Users\HP\xomni\data\raw"
OUT = os.path.join(BASE, "scrape4.json")

CAPS = {"anthropics/skills": 12, "microsoft/SkillOpt": 4, "SnailSploit/Claude-Red": 8,
        "gadievron/raptor": 6, "geekjourneyx/md2wechat-skill": 2, "qiye45/wechatDownload": 1,
        "club-cog/devin-handoff": 1, "0xBadai/devin-skills": 1, "sudokar/openspec-plus": 6}

URL_ALLOW = re.compile(r"(github\.com|raw\.githubusercontent\.com|gist\.github\.com|anthropic\.com|claude\.ai|openai\.com|google\.com|microsoft\.com|learn\.microsoft\.com|python\.org|pypi\.org|npmjs\.com|nodejs\.org|developer\.mozilla\.org|stackoverflow\.com|w3\.org|json\.org|yaml\.org|example\.com|localhost|127\.0\.0\.1|0\.0\.0\.0|vercel\.com|smithery\.ai|glama\.ai|modelcontextprotocol\.io|docker\.com|kubernetes\.io|aws\.amazon\.com|cloudflare\.com|react\.dev|docs\.anthropic\.com|platform\.openai\.com|deno\.land|rust-lang\.org|go\.dev|mcp\.composio\.dev|composio\.dev|cognition\.ai|devin\.ai|smol\.dev|sst\.dev|wikipedia\.org|archive\.org|openspec\.dev|git\.io|bit\.ly|tinyurl\.com|code\.visualstudio\.com|medium\.com|mdn\.mozilla\.org|mozilla\.org|owasp\.org|portswigger\.net|burpsuite|fuzzingbook\.org|exploit-db\.com|cvedetails\.com|nvd\.nist\.gov|cve\.mitre\.org|mitre\.org|attack\.mitre\.org|killchain|hacktricks\.xyz|book\.hacktricks\.xyz|pentesterlab\.com|hackthebox\.com|tryhackme\.com|offsec\.com|sans\.org|isc2\.org|ceh|eccouncil\.org|crto|zerodayinitiative\.com|projectzero|googleprojectzero|talosintelligence\.com|securelist\.com|kaspersky\.com|fireeye\.com|mandiant\.com|crowdstrike\.com|sentinelone\.com|paloaltonetworks\.com|unit42|checkpoint\.com|trendmicro\.com|symantec\.com|mcafee\.com|eset\.com|avast\.com|avg\.com|bitdefender\.com|norton\.com|webroot\.com|malwarebytes\.com|virustotal\.com|hybrid-analysis\.com|any\.run|joesandbox\.com|cuckoosandbox\.org|yara|yararules|sigma|sigma-rule|github\.com/SnailSploit|hasherezade|lostsec\.xyz|d3fend\.mitre\.org|cisa\.gov|nist\.gov|enisa\.europa\.eu|first\.org|csirt|circl\.lu|cert\.org|us-cert\.cisa\.gov|ncsc\.gov\.uk|bsi\.bund\.de|cyber\.gov\.au|jpcert\.or\.jp|krcert\.or\.kr|cncert\.cn|cnvd\.org\.cn|seebug\.org|paper\.seebug\.org|freebuf\.com|t00ls\.com|91ri\.org|zone-h\.org|xssed\.com|wooyun|wooyun\.org|seclists\.org|full disclosure|fulldisclosure|bugcrowd\.com|hackerone\.com|intigriti\.com|synack\.com|yeswehack\.com|zerocopter\.com|detectify\.com|bountygraph|vuldb\.com|snyk\.io|veracode\.com|checkmarx\.com|sonarsource\.com|semgrep\.dev|bandit|brakeman|gosec|sast|dast|owasp-zap|zaproxy|burpsuite|nikto|nmap\.org|sqlmap\.org|metasploit\.com|rapid7\.com|exploitdb|searchsploit|beefproject\.com|social-engineer\.org|veil-framework|powershell-empire|empireproject|sliver\.sh|cobaltstrike\.com|bruteratel|havoc\.cf|mythic|mythicagent|caldera|atomicredteam|invoke-obfuscation|powerupsql|mimikatz|impacket|bloodhound|neo4j\.com|sharpHound|responder|ntlmrelayx|kerberoast|pass-the-hash|pass-the-ticket|golden-ticket|silver-ticket|dcsync|lsass|secretsdump|hashcat\.net|john\.the\.ripper|hydra|medusa|ncrack|aircrack|wireshark\.org|tshark|tcpdump|ettercap|bettercap\.org|maltego\.com|recon-ng|theharvester|shodan\.io|censys\.io|zoomeye\.org|fofa\.info|quake|grep\.app|hunter\.how|spyse|binaryedge\.io|intelx\.io|haveibeenpwned\.com|dehashed|snusbase|breachcompilation|raidforums|exploit\.in|0day\.today|packetstormsecurity\.com|securityfocus\.com|sectools|kali\.org|parrotsec\.org|blackarch\.org|archlinux\.org|debian\.org|ubuntu\.com|centos\.org|redhat\.com|fedora|opensuse\.org|suse\.com|alpinelinux\.org|busybox\.net|musl\.libc|linux\.org|kernelnewbies|phoronix\.com|lwn\.net|distrowatch\.com|raspberrypi\.org|arduino\.cc|esp32|espressif\.com|stm32|arm\.com|riscv\.org|qemu\.org|bochs|virtualbox\.org|vmware\.com|hyper-v|proxmox\.com|esxi|kvm|libvirt\.org|xenproject\.org|openvz|docker\.com|containerd|runc|podman\.io|buildah|cri-o|kubernetes\.io|openshift\.com|rancher\.com|helm\.sh|istio\.io|linkerd\.io|envoyproxy\.io|nginx\.org|apache\.org|httpd|tomcat\.apache\.org|jetty|jboss|wildfly|glassfish|payara|openliberty\.io|springframework\.io|quarkus\.io|micronaut\.io|graalvm\.org|jdk\.java\.net|openjdk\.org|adoptium\.net|eclipse\.org|netbeans|intellij|jetbrains\.com|pycharm|goland|vscode|visualstudio\.com|android\.com|developer\.android\.com|kotlinlang\.org|gradle\.org|maven\.apache\.org|groovy-lang\.org|scala-lang\.org|dotnet\.microsoft\.com|asp\.net|nuget\.org|npmjs\.com|yarnpkg\.com|pnpm\.io|bun\.sh|deno\.land|nodejs\.org|v8\.dev|chromium\.org|webkit\.org|firefox|mozilla\.org|typescriptlang\.org|ecma-international\.org|tc39\.es|babeljs\.io|webpack\.js\.org|vitejs\.dev|rollupjs\.org|esbuild\.github\.io|parceljs\.org|gulpjs\.com|gruntjs\.com|sass-lang\.com|lesscss\.org|stylus-lang\.com|tailwindcss\.com|bootstrapcdn\.com|getbootstrap\.com|materializecss\.com|semantic-ui\.com|foundation\.zurb\.com|bulma\.io|chakra-ui\.com|mui\.com|ant\.design|element-plus|vuetifyjs\.com|quasar\.dev|ionicframework\.com|cordova\.apache\.org|capacitorjs\.com|flutter\.dev|dart\.dev|reactnative\.dev|expo\.dev|xamarin|mono-project\.com|unity\.com|unrealengine\.com|godotengine\.org|blender\.org|autodesk\.com|mayapy|3dsmax|zbrush|substance3d|adobe\.com|figma\.com|sketch\.com|invisionapp\.com|zeplin\.io|framer\.com|webflow\.com|squarespace\.com|wix\.com|wordpress\.org|drupal\.org|joomla\.org|moodle\.org|mediawiki\.org|php\.net|laravel\.com|symfony\.com|cakephp\.org|codeigniter\.com|yii\.com|zend\.com|slimframework\.com|flightphp|pear|composer\.org|packagist\.org|ruby-lang\.org|rubygems\.org|rails\.com|sinatrarb\.com|jekyllrb\.com|middlemanapp\.com|hugo\.com|gohugo\.io|eleventy\.dev|astro\.build|nextjs\.org|nuxtjs\.org|svelte\.dev|sveltekit|remix\.run|gatsbyjs\.com|docusaurus\.io|vuepress\.vuejs\.org|vitepress\.vuejs\.org|mkdocs\.org|sphinx-doc\.org|readthedocs\.org|gitbook\.com|mdbook|rust-lang\.org|crates\.io|docs\.rs|play\.rust-lang\.org|ziglang\.org|nim-lang\.org|elixir-lang\.org|erlang\.org|gleam\.run|haskell\.org|hackage\.haskell\.org|ocaml\.org|opam\.ocaml\.org|fsharp\.org|dotnetfiddle|swift\.org|swiftpackageindex\.com|objective-c|clang\.llvm\.org|llvm\.org|gcc\.gnu\.org|gnu\.org|kernel\.org|glibc|musl|binutils|gdb|lldb\.llvm\.org|valgrind\.org|perf|dtrace|strace|ltrace|gprof|oprofile|systemtap|bpf|ebpf|cilium\.io|falco\.org|kube-OVN|cni|calico|flannel|weave\.works|k3s\.io|microk8s|kind\.sigs\.k8s\.io|minikube\.sigs\.k8s\.io|kubectl|openshift|okd|karbon|tanzu|pivotal\.io|vmware\.com|nutanix\.com|hpe\.com|dell\.com|lenovo\.com|hp\.com|acer\.com|asus\.com|msi\.com|gigabyte\.com|evga\.com|nvidia\.com|amd\.com|intel\.com|qualcomm\.com|broadcom\.com|marvell\.com|mediatek\.com|samsung\.com|lg\.com|sony\.com|panasonic\.com|toshiba\.com|hitachi\.com|fujitsu\.com|nec\.com|mitsubishi\.com|canon\.com|nikon\.com|fujifilm\.com|olympus\.com|pentax|leica|zeiss\.com|sigma|tamron|tokina|rokinon|samyang|viltrox|meike|7artisans|ttartisan|venuslens|laowa|dzo|atlaslens|duclos|lensrentals\.com|bhphotovideo\.com|adorama\.com|kenrockwell\.com|dpreview\.com|dxomark\.com|sensorgen|imagemagick\.org|graphicsmagick\.org|ffmpeg\.org|vlc\.videolan\.org|mpv\.io|handbrake\.fr|audacity\.org|sox|kdenlive\.org|shotcut\.org|openshot\.org|pitivi\.org|blender\.org|gimp\.org|inkscape\.org|krita\.org|darktable\.org|rawtherapee\.com|digikam\.org|shotwell|gthumb|eog|gwenview|kphotoalbum|xnview\.com|irfanview\.com|faststone\.org|nomacs\.org|jpeg\.org|png|tiff|webp|avif|heic|raw|dng|cr2|nef|arw|raf|orf|rw2|pef|srw|erf|mrw|x3f|iiq|3fr|fff|mef|mos|nrw|kdc|dcr|sr2|srf|mrw|cr3|crw|bay|cap|dcs|dng|eip|erf|fff|flex|iiq|k25|kdc|mdc|mef|mos|mrw|nef|nrw|orf|pef|ptx|pxn|r3d|raf|raw|rw2|rwl|rwz|sr2|srf|srw|x3f|ari|arw|srf|sr2|mrw|nef|nrw|orf|raf|rw2|rwl|rwz|sr2|srf|srw|x3f)")

DEFENSIVE = re.compile(r"(never|don'?t|do\s+not|avoid|warning|caution|beware|important|if\s+the\s+user|unless|malicious|suspicious|test|example|evaluat)", re.I)
EXAMPLE_VAL = re.compile(r"(example|test|sample|dummy|fake|foo|bar|alice|bob|placeholder|your[_-]|xxx|12345|correct-pw|changeme|demo|local|dev)", re.I)
PLACEHOLDER_VAL = re.compile(r"(x{3,}|your[_-]|replace|changeme|demo|example|test|dummy|sample|foo|bar|alice|bob|placeholder)", re.I)

RULES = [
    (r"\beval\s*\(", "eval()", 2),
    (r"\bexec\s*\(", "exec()", 2),
    (r"os\.system\s*\(", "os.system()", 2),
    (r"shell\s*=\s*True", "shell=True", 2),
    (r"subprocess\.(run|call|Popen|check_output|check_call)", "subprocess", 2),
    (r"\bPopen\s*\(", "Popen", 2),
    (r"child_process\.(exec|spawn|execSync|spawnSync)", "child_process-exec", 2),
    (r"pickle\.loads|marshal\.loads|zlib\.decompress", "deserialization", 2),
    (r"b64decode|base64\.decodebytes|unhexlify", "base64-decode", 2),
    (r"[A-Za-z0-9+/]{300,}={0,2}", "large-base64-blob", 2),
    (r"(?:\\x[0-9a-fA-F]{2}){25,}", "hex-escape-blob", 2),
    (r"ignore\s+(all\s+)?(previous|prior|above|earlier|the\s+above)\s+(instructions|prompts|directives|messages|context)", "ignore-prior-instructions", 2),
    (r"ignore\s+(everything|all)\s+(else|above|before|i\s+said|previous)", "ignore-everything", 2),
    (r"disregard\s+(all\s+)?(previous|prior|above)", "disregard-prior", 2),
    (r"override\s+(all\s+)?(prior|previous)\s+(instructions|rules|prompts)", "override-instructions", 2),
    (r"(reveal|print|output|show|repeat|paste)\s+(your|the|this)\s+(entire\s+|full\s+|system\s+|initial\s+)?(system\s+)?(prompt|instructions)", "reveal-system-prompt", 2),
    (r"jailbreak", "jailbreak-mention", 2),
    (r"(sk-[A-Za-z0-9\-]{20,}|ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_\-]{30,}|xox[baprs]-[A-Za-z0-9-]{10,})", "hardcoded-secret-token", 3),
    (r"api[_-]?key\s*[:=]\s*[\"'][^\"']{10,}[\"']", "hardcoded-api-key", 3),
    (r"password\s*[:=]\s*[\"'][^\"']{6,}[\"']", "hardcoded-password", 3),
    (r"secret\s*[:=]\s*[\"'][^\"']{10,}[\"']", "hardcoded-secret", 3),
    (r"(os\.environ|getenv\s*\(|process\.env|env\[)", "env-var-read", 1),
    (r"requests\.(post|put|patch|delete)\s*\(|urllib\.request\w*\.?\s*|httpx\.(post|put|patch|delete)\s*\(|aiohttp.*\.post\s*\(", "network-write", 1),
    (r"https?://", "url-present", 1),
]

EXFIL_HOSTS = re.compile(r"(webhook\.site|requestbin\.com|pipedream\.net|ngrok\.(io|app)|transfer\.sh|0x0\.st|oshi\.at|pastebin\.com|dpaste\.com|ix\.io|termbin\.com|sprunge\.us|mockbin\.com|httpbin\.org|beeceptor\.com|hookbin\.com|interact\.sh|burpcollaborator|oast\.(fun|pro|online|site)|dnslog\.cn|ceye\.io|wuyun|exploit\.in)", re.I)

def scan(content, path):
    hits = []
    for rx, label, sev in RULES:
        for m in re.finditer(rx, content, re.I | re.S):
            eff_sev, eff_label = sev, label
            if sev == 2 and DEFENSIVE.search(content[max(0, m.start() - 70):m.start()]):
                eff_sev, eff_label = 1, "defensive-" + label
            if sev == 3:
                # URL-substring guard for token regexes
                pre = content[max(0, m.start() - 12):m.start()]
                if re.search(r"://|www\.|\.com/|\.io/|\.org/|\.net/", pre):
                    eff_sev, eff_label = 1, "url-substring-" + label
                else:
                    val = m.group(0)
                    if (PLACEHOLDER_VAL if label == "hardcoded-secret-token" else EXAMPLE_VAL).search(val):
                        eff_sev, eff_label = 1, "example-credential-" + label
            hits.append((eff_label, eff_sev, m.start(), m.end(), content[max(0, m.start()-50):m.end()+40]))
    # exfil: network-write within 300 chars of env read
    env_spans = [h for h in hits if h[0] == "env-var-read"]
    net_spans = [h for h in hits if h[0] == "network-write"]
    exfil = False
    for ns in net_spans:
        for es in env_spans:
            if abs(ns[2] - es[2]) < 300:
                exfil = True
                hits.append(("env-to-network-exfil", 3, es[2], ns[3], content[max(0, es[2]-40):ns[3]+40]))
                break
        if exfil:
            break
    # exfil host mention near env read
    for m in EXFIL_HOSTS.finditer(content):
        for es in env_spans:
            if abs(m.start() - es[2]) < 400:
                hits.append(("exfil-host-near-env", 3, es[2], m.end(), content[max(0, es[2]-40):m.end()+40]))
                break
    # obfuscated executable blob
    blobs = [h for h in hits if h[0] in ("large-base64-blob", "hex-escape-blob")]
    execs = [h for h in hits if h[0] in ("eval()", "exec()", "os.system()", "subprocess", "shell=True", "Popen", "child_process-exec", "base64-decode")]
    for b in blobs:
        for e in execs:
            if abs(b[2] - e[2]) < 400:
                hits.append(("obfuscated-executable-blob", 3, b[2], e[3], content[max(0, b[2]-40):e[3]+40]))
                break
    # unknown hosts
    unknown = set()
    for m in re.finditer(r"https?://([A-Za-z0-9._\-]+)", content):
        host = m.group(1).lower()
        if host.startswith("www."):
            host = host[4:]
        if not URL_ALLOW.search(host):
            unknown.add(host)
    for h in sorted(unknown)[:4]:
        hits.append(("unknown-host:" + h, 1, 0, 0, h))
    sev_max = max([h[1] for h in hits], default=0)
    verdict = "PASS" if sev_max < 2 else ("REVIEW" if sev_max == 2 else "REJECT")
    notes = []
    seen = set()
    for label, sev, s, e, ctx in hits:
        key = (label, ctx[:60])
        if key in seen:
            continue
        seen.add(key)
        notes.append(f"{path}: {label} [sev{sev}] :: {re.sub(chr(92)+'s+', ' ', ctx)[:120]}")
    return verdict, notes[:10]

def main():
    items = json.load(open(OUT, encoding="utf-8"))
    print("loaded", len(items))
    seen_sha = set()
    out = []
    per_src = Counter()
    for it in items:
        src = it["source"]
        if per_src[src] >= CAPS.get(src, 12):
            continue
        if it["sha256"] in seen_sha:
            continue
        verdict, notes = scan(it["content"], it["source_url"].split("/blob/")[-1])
        it["scan_verdict"] = verdict
        it["scan_notes"] = notes
        out.append(it)
        seen_sha.add(it["sha256"])
        per_src[src] += 1
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print("final:", len(out))
    print("verdicts:", dict(Counter(i["scan_verdict"] for i in out)))
    print("per repo:", dict(Counter(i["source"] for i in out)))
    print("\nREJECT:")
    for i in out:
        if i["scan_verdict"] == "REJECT":
            print(" -", i["source"], "|", i["name"], "|", (i["scan_notes"][0][:130] if i["scan_notes"] else ""))
    print("\nREVIEW count:", sum(1 for i in out if i["scan_verdict"] == "REVIEW"))
    for i in out:
        if i["scan_verdict"] == "REVIEW":
            print(" ~", i["source"], "|", i["name"], "|", (i["scan_notes"][0][:110] if i["scan_notes"] else ""))

if __name__ == "__main__":
    main()
