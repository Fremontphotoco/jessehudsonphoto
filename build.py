#!/usr/bin/env python3
"""Build the static jessehudsonphoto.com site from the Squarespace export.

Usage: python3 build.py            (full build, resizes images that aren't cached yet)
       python3 build.py --no-images (HTML only)
"""
import os, re, json, html, shutil, subprocess, sys, urllib.parse, hashlib
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.expanduser("~/Documents/Freelance/jessehudsonphoto.com Site Export/pages")
EXTRA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extra")  # galleries that aren't in the Squarespace export
OUT = os.path.join(ROOT, "docs")          # GitHub Pages serves /docs
IMG = os.path.join(OUT, "img")
LARGE, THUMB = 1800, 640
DOMAIN = "https://jessehudsonphoto.com"
EMAIL = "info@jessehudsonphoto.com"

# ---- site structure ------------------------------------------------------
# (slug, title, export folder, blurb)
COMMERCIAL = [
    ("overview", "Commercial Overview", "commercial-overview", "Selected commercial work."),
    ("architecture", "Architecture", "architecture", ""),
    ("cocktails", "Cocktails", "cocktails", ""),
    ("product", "Product", "product", ""),
    ("food", "Food", "food", ""),
    ("conference", "Conference", "conference", ""),
    ("campaigns", "Campaigns", "press-campaigns", ""),
    ("cadaver-lab", "Cadaver Lab", "cadaver-lab", ""),
]
CONCEPTUAL = [
    ("conceptual", "Conceptual", "conceptual", "Conceptual imagery and installations."),
    ("shelter", "SHELTER", "shelter",
     "SHELTER, 2023 to 2024: a life-size 1950s fallout bunker built inside a downtown Las Vegas storefront, sixty-five miles from the Nevada Test Site. An 800-square-foot immersive walk-through installation at Killing Trends."),
    ("crack-the-surface", "Crack The Surface", "crackthesurface",
     "Crack the Surface focuses on expressing the emotional suffocation that humans face due to various personal and global issues."),
    ("portraiture", "Portraiture", "portraiture", "A collection of portrait photography."),
    ("slaughterhouse-earth", "Slaughterhouse Earth", "slaughter-house-earth", ""),
    ("faulty-connections", "Faulty Connections", "faulty-connections", ""),
    ("human-agency", "Human Agency", "human-agency", ""),
    ("art", "Art", "art", ""),
    ("polaroids", "Polaroids", "polaroids", "A collection of Polaroids."),
    ("skateboarding", "Skateboarding", "skateboarding", "Skate photography."),
    ("landscape", "Landscape", "landscape", "Travel and landscape photography."),
]
EVENTS = [
    ("overview", "Event Overview", "nightlife-overview", "Nightlife and event photography in Las Vegas."),
    ("overview-2018", "Event Overview, 2014 to 2018", "events-overview", "Earlier event work."),
    ("edc-2026", "EDC 2026", "edc-2026", ""),
    ("crykits-playhouse-2022", "Crykits Playhouse 2022", "crykits-playhouse-20220", ""),
    ("downtown-las-vegas", "Downtown Las Vegas", "downtown-las-vegas", ""),
    ("artbat", "ARTBAT, Techno Taco Tuesday 2019", "artbatmusic", ""),
    ("dom-dolla", "Dom Dolla, Club Soda 2019", "club-soda-w_-dom-dolla", ""),
    ("space-yacht-2018", "Space Yacht Vegas 2018", "space-yacht-vegas-121218", ""),
    ("crykits-playhouse-dec-2018", "Crykits Playhouse, Dec 2018", "crykits-playhouse-121318", ""),
    ("nfbn-2018", "NFBN 2018", "nfbn-121118", ""),
    ("friday-night-2018", "Friday Night at Commonwealth 2018", "121415-friday-night", ""),
    ("bumble-biz-2018", "Bumble Biz Holiday Party 2018", "bumble-biz-holiday-party-2018", ""),
    ("crykits-playhouse-jan-2018", "Crykits Playhouse, Jan 2018", "crykits-playhouse-11018", ""),
    ("edc-2018", "EDC 2018", "edc-2018", ""),
    ("edc-2017", "EDC 2017", "edc-2017", ""),
    ("mntra", "MNTRA Artists 2017 to 2018", "mntra", ""),
    ("rich-the-kid", "Rich The Kid 2017", "richthekid", ""),
    ("be-like-max", "Be Like Max 2013 to 2019", "belikemax", ""),
    ("trabb", "T.R@BB 2013 to 2017", "trabb", ""),
    ("ekali-gravez", "Ekali & Gravez 2016", "ekali-gravez", ""),
    ("house-of-bandits", "House of Bandits 2016", "house-of-bandits", ""),
    ("og-maco", "OG Maco 2016", "ogmaco", ""),
    ("future-sunday", "Future Sunday 2016", "future-sunday", ""),
    ("stooki-sound", "Stooki Sound 2016", "stookisound", ""),
    ("lib-2016", "Life Is Beautiful 2016", "lib-2016", ""),
    ("lorde", "Lorde at The Joint 2014", "lorde", ""),
    ("leroy-chops", "Leroy Chops 2014", "new-gallery-1", ""),
]
SECTIONS = [("commercial", "Commercial", COMMERCIAL),
            ("conceptual", "Conceptual", CONCEPTUAL),
            ("events", "Events", EVENTS)]
HOME_GALLERY = "overview"   # export folder for the homepage gallery

# ---- helpers ---------------------------------------------------------------
def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def gallery_items(folder):
    """Ordered list of local image paths for an export folder, using collection.json order."""
    d = os.path.join(EXPORT, folder)
    if not os.path.isdir(d): d = os.path.join(EXTRA, folder)
    files = {f for f in os.listdir(d) if re.search(r'\.(jpe?g|png)$', f, re.I)}
    order = []
    cj = os.path.join(d, "collection.json")
    if os.path.exists(cj):
        try:
            j = json.load(open(cj))
            for it in j.get("items", []):
                u = (it.get("assetUrl") or "").split("?")[0]
                name = urllib.parse.unquote(u.rsplit("/", 1)[-1])
                if name in files and name not in order:
                    order.append(name)
        except Exception:
            pass
    for f in sorted(files):
        if f not in order and not re.search(r'favicon|logo', f, re.I):
            order.append(f)
    return [os.path.join(d, f) for f in order]

def dims(path):
    r = run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path]).stdout
    w = int(re.search(r"pixelWidth: (\d+)", r).group(1)); h = int(re.search(r"pixelHeight: (\d+)", r).group(1))
    return w, h

def web_name(folder, src):
    stem, ext = os.path.splitext(os.path.basename(src))
    base = re.sub(r'[^A-Za-z0-9._-]+', '-', stem).strip('-').lower() or "image"
    return f"{folder}/{base}-{ext.lstrip('.').lower() or 'img'}"   # keep the extension in the name so 001.jpg and 001.jpeg stay distinct

def make_images(jobs):
    """jobs: list of (src, relname). Produces img/<rel>.jpg and img/<rel>_t.jpg; returns {rel: (w,h)}."""
    meta_path = os.path.join(ROOT, ".imgmeta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    def one(job):
        src, rel = job
        large = os.path.join(IMG, rel + ".jpg"); thumb = os.path.join(IMG, rel + "_t.jpg")
        os.makedirs(os.path.dirname(large), exist_ok=True)
        if not os.path.exists(large):
            run(["sips", "-Z", str(LARGE), "-s", "format", "jpeg", "-s", "formatOptions", "82", src, "--out", large])
        if not os.path.exists(thumb):
            run(["sips", "-Z", str(THUMB), "-s", "format", "jpeg", "-s", "formatOptions", "78", src, "--out", thumb])
        if rel not in meta and os.path.exists(large):
            meta[rel] = dims(large)
        return rel
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(one, jobs))
    json.dump(meta, open(meta_path, "w"))
    return meta

# ---- text content from export ---------------------------------------------
def block_html(folder):
    """Concatenate the Squarespace text blocks of a page as clean HTML."""
    p = os.path.join(EXPORT, folder, "page.html")
    if not os.path.exists(p): return ""
    h = open(p, errors="ignore").read()
    blocks = re.findall(r'<div class="sqs-html-content"[^>]*>(.*?)</div>', h, re.S)
    out = []
    for b in blocks:
        b = re.sub(r'\s(style|class|data-[a-z-]+)="[^"]*"', '', b)
        b = re.sub(r'<(/?)h[1-6]>', r'<\1p>', b)            # old site used h2 for body copy
        b = re.sub(r'</?(strong|em)>', '', b)
        b = re.sub(r'<p>\s*</p>', '', b)
        out.append(b.strip())
    return "\n".join(out)

ABOUT_HTML = block_html("about")
CV_HTML = block_html("hudson-cv")
VIDEO_EMBEDS = []  # filled by scan below
for f in ("video-overview", "video", "disposable-future", "sell-the-soul"):
    p = os.path.join(EXPORT, f, "page.html")
    if os.path.exists(p):
        s = open(p, errors="ignore").read().replace("\\/", "/").replace("&quot;", '"')
        for m in re.findall(r'https?://(?:www\.)?(?:youtube\.com/(?:embed/|watch\?v=)|youtu\.be/|player\.vimeo\.com/video/|vimeo\.com/)([A-Za-z0-9_-]+)', s):
            VIDEO_EMBEDS.append(m)
VIDEO_EMBEDS = list(dict.fromkeys(VIDEO_EMBEDS))

# ---- templates -------------------------------------------------------------
CSS = """
:root{--bg:#f4f4f2;--fg:#111;--mute:#9a9a9a;--line:#dcdcdc;--max:1500px;--pad:clamp(20px,3vw,44px)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#111;--fg:#f2f2f2;--mute:#777;--line:#2a2a2a}}
:root[data-theme=dark]{--bg:#111;--fg:#f2f2f2;--mute:#777;--line:#2a2a2a}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 "Helvetica Neue",Helvetica,Inter,Arial,sans-serif;-webkit-font-smoothing:antialiased;letter-spacing:-.005em}
a{color:inherit;text-decoration:none}
header{position:fixed;inset:0 0 auto 0;z-index:20;display:flex;justify-content:space-between;align-items:flex-start;padding:var(--pad);pointer-events:none}
header a,header button{pointer-events:auto}
.brand{font-size:clamp(28px,4.6vw,64px);font-weight:700;letter-spacing:-.05em;line-height:.9}
.brand small{display:block;font-size:12px;font-weight:400;letter-spacing:.06em;text-transform:uppercase;color:var(--mute);margin-top:8px}
nav{text-align:right;font-size:14px;line-height:1.35}
nav a{display:block;color:var(--mute);transition:color .2s}nav a:hover,nav a.on{color:var(--fg)}
.theme{background:none;border:0;color:var(--mute);font:inherit;font-size:12px;cursor:pointer;padding:0;margin-top:8px}
.theme:hover{color:var(--fg)}
/* showcase */
.show{position:relative}
.stage{position:sticky;top:0;height:100vh;height:100dvh;display:flex;align-items:center;justify-content:center;padding:calc(var(--pad) + 60px) var(--pad) calc(var(--pad) + 40px)}
.stage .frame{position:relative;width:min(100%,var(--max));height:100%;display:flex;align-items:center;justify-content:center}
.stage .set{position:absolute;inset:0;display:flex;align-items:center;justify-content:center}
.stage img{position:absolute;max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;opacity:0;transform:scale(.985);transition:opacity .6s ease,transform .9s ease;box-shadow:0 30px 80px -30px rgba(0,0,0,.35);cursor:e-resize}
.stage img.on{opacity:1;transform:none}
.steps{position:relative;margin-top:-100vh;margin-top:-100dvh}
.step{height:100vh;height:100dvh}
.meta{position:fixed;z-index:15;font-size:12px;line-height:1.35;color:var(--mute);pointer-events:none}
.meta.tl{left:var(--pad);bottom:var(--pad)}
.meta.br{right:var(--pad);bottom:var(--pad);text-align:right}
.list{list-style:none;margin:0 0 14px;padding:0}
.list li{color:var(--mute);transition:color .25s,font-size .25s;font-size:14px;line-height:1.5}
.list li.on{color:var(--fg);font-size:clamp(18px,2vw,26px);letter-spacing:-.02em;line-height:1.2;margin:4px 0}
.list a,.hint a{pointer-events:auto}
.hint{color:var(--fg);font-size:12px}.hint a{text-decoration:underline;text-underline-offset:3px}
.count{color:var(--fg);font-size:12px;margin-bottom:6px}
/* preloader */
#pre{position:fixed;inset:0;background:var(--bg);z-index:60;display:flex;align-items:center;justify-content:center;transition:opacity .7s ease}
#pre.out{opacity:0 !important;pointer-events:none;visibility:hidden;transition:opacity .7s ease,visibility 0s .7s}
#pre .pct{position:absolute;left:var(--pad);bottom:var(--pad);font-size:clamp(72px,16vw,220px);font-weight:400;letter-spacing:-.06em;line-height:.85}
#pre .pile{position:relative;width:min(60vw,520px);aspect-ratio:1}
#pre .pile img{position:absolute;width:40%;left:30%;top:30%;box-shadow:0 20px 50px -20px rgba(0,0,0,.4);opacity:0;transition:opacity .4s}
#pre .pile img.in{opacity:1}
/* grid + text pages */
.page{max-width:var(--max);margin:0 auto;padding:calc(var(--pad) + 110px) var(--pad) 120px}
.page h1{font-size:clamp(28px,4vw,54px);font-weight:700;letter-spacing:-.04em;margin:0 0 .5em;line-height:1}
.lead{color:var(--mute);max-width:62ch;font-size:17px}
.prose{max-width:66ch;font-size:16px;line-height:1.6}.prose p{margin:0 0 1em}.prose h2{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--mute);margin:2.4em 0 .8em}
.masonry{columns:3 320px;column-gap:14px;margin-top:40px}
.masonry a{display:block;break-inside:avoid;margin:0 0 14px;background:var(--line)}
.masonry img{display:block;width:100%;height:auto}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:24px 20px;margin-top:40px}
.card img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;background:var(--line)}
.card h2{font-size:15px;font-weight:500;margin:10px 0 0}.card p{margin:0;color:var(--mute);font-size:13px}
.more{display:block;text-align:center;padding:60px 0 20px;color:var(--mute);font-size:12px;letter-spacing:.1em;text-transform:uppercase}
footer{padding:40px var(--pad);color:var(--mute);font-size:12px;display:flex;flex-wrap:wrap;gap:10px 28px;justify-content:space-between}
footer a:hover{color:var(--fg)}
#lb{position:fixed;inset:0;background:rgba(0,0,0,.95);display:none;align-items:center;justify-content:center;z-index:70;cursor:zoom-out}
#lb.on{display:flex}#lb img{max-width:96vw;max-height:94vh;object-fit:contain}
#lb button{position:absolute;top:50%;transform:translateY(-50%);background:none;border:0;color:#fff;font-size:44px;padding:20px;cursor:pointer;opacity:.8}
#lb .prev{left:0}#lb .next{right:0}#lb .x{top:6px;right:6px;transform:none;font-size:30px}
@media(max-width:760px){.stage{padding:calc(var(--pad) + 70px) var(--pad) 150px}.meta.br{display:none}.list li{font-size:13px}.list li.on{font-size:18px}.brand small{display:none}}
"""

JS = """
(function(){
var t=document.querySelector('.theme');try{var saved=localStorage.getItem('theme');if(saved)document.documentElement.setAttribute('data-theme',saved);}catch(e){}
if(t){t.addEventListener('click',function(){var cur=document.documentElement.getAttribute('data-theme');var dark=cur?cur==='dark':matchMedia('(prefers-color-scheme:dark)').matches;var next=dark?'light':'dark';document.documentElement.setAttribute('data-theme',next);try{localStorage.setItem('theme',next)}catch(e){}});}
/* showcase: vertical = series (steps), horizontal = photos within the active series */
var steps=[].slice.call(document.querySelectorAll('.step')),items=[].slice.call(document.querySelectorAll('.list li')),cnt=document.querySelector('.count'),openA=document.querySelector('.hint a.open');
var sets=[].slice.call(document.querySelectorAll('.stage .set'));
var flat=[].slice.call(document.querySelectorAll('.stage img'));
var cur=0,pos=[],lock=0;sets.forEach(function(){pos.push(0)});
function load(im){if(im&&im.dataset.src){im.src=im.dataset.src;delete im.dataset.src;}}
function render(){
  if(sets.length){sets.forEach(function(st,k){var ims=st.children;for(var j=0;j<ims.length;j++){ims[j].classList.toggle('on',k===cur&&j===pos[cur]);}
      if(k===cur){load(ims[pos[k]]);load(ims[pos[k]+1]);load(ims[pos[k]+2]);load(ims[pos[k]-1]);}else if(Math.abs(k-cur)===1){load(ims[0]);}});
    if(cnt)cnt.textContent=(pos[cur]+1)+' / '+sets[cur].children.length;
    if(openA)openA.setAttribute('href',sets[cur].dataset.href);}
  else{flat.forEach(function(im,k){im.classList.toggle('on',k===cur);});[cur,cur+1,cur+2,cur-1].forEach(function(j){load(flat[j])});if(cnt)cnt.textContent=(cur+1)+' / '+flat.length;}
  items.forEach(function(li,k){li.classList.toggle('on',k===cur);});
}
function series(d){var n=Math.min(Math.max(cur+d,0),steps.length-1);if(n===cur)return;cur=n;if(sets.length)pos[cur]=0;render();steps[n].scrollIntoView({behavior:'smooth'});}
function photo(d){if(!sets.length){series(d);return;}var n=sets[cur].children.length;var p=Math.min(Math.max(pos[cur]+d,0),n-1);if(p===pos[cur])return;pos[cur]=p;render();}
if(steps.length){
  var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){var n=+e.target.dataset.i;if(n!==cur){cur=n;if(sets.length)pos[cur]=0;render();}}});},{threshold:.5});
  steps.forEach(function(st){io.observe(st);});render();
  items.forEach(function(li,k){var a=li.querySelector('a');if(a&&a.getAttribute('href')==='#')a.addEventListener('click',function(e){e.preventDefault();series(k-cur);});});
  document.addEventListener('keydown',function(e){var lb=document.getElementById('lb');if(lb&&lb.classList.contains('on'))return;
    if(e.key==='ArrowRight'){e.preventDefault();photo(1);}else if(e.key==='ArrowLeft'){e.preventDefault();photo(-1);}
    else if(e.key==='ArrowDown'||e.key==='PageDown'||e.key===' '){e.preventDefault();series(1);}else if(e.key==='ArrowUp'||e.key==='PageUp'){e.preventDefault();series(-1);}
    else if(e.key==='Home'){series(-cur);}else if(e.key==='End'){series(steps.length);}
    else if(e.key==='Enter'&&sets.length){location.href=sets[cur].dataset.href;}});
  window.addEventListener('wheel',function(e){if(Math.abs(e.deltaX)<=Math.abs(e.deltaY)||Math.abs(e.deltaX)<25)return;e.preventDefault();var now=Date.now();if(now-lock<500)return;lock=now;photo(e.deltaX>0?1:-1);},{passive:false});
  var tx=null,ty=null;window.addEventListener('touchstart',function(e){tx=e.touches[0].clientX;ty=e.touches[0].clientY;},{passive:true});
  window.addEventListener('touchend',function(e){if(tx===null)return;var dx=e.changedTouches[0].clientX-tx,dy=e.changedTouches[0].clientY-ty;tx=null;if(Math.abs(dx)>60&&Math.abs(dx)>Math.abs(dy))photo(dx<0?1:-1);},{passive:true});
  var stage=document.querySelector('.stage');if(stage)stage.addEventListener('click',function(e){if(e.target.tagName!=='IMG')return;var r=stage.getBoundingClientRect();if(e.clientX<r.left+r.width*.3)photo(-1);else photo(1);});
}
/* preloader */
var pre=document.getElementById('pre');
if(pre){var pct=pre.querySelector('.pct'),pile=[].slice.call(pre.querySelectorAll('.pile img')),n=0,total=Math.max(pile.length,1),shown=false;
function done(){if(shown)return;shown=true;pct.textContent='100%';setTimeout(function(){pre.classList.add('out');document.body.style.overflow='';},350);}
document.body.style.overflow='hidden';
pile.forEach(function(im,k){var rot=(k*47)%40-20,dx=(k*31)%50-25,dy=(k*17)%50-25;im.style.transform='translate('+dx+'%,'+dy+'%) rotate('+rot+'deg)';
function tick(){n++;pct.textContent=Math.round(n/total*100)+'%';setTimeout(function(){im.classList.add('in')},k*120);if(n>=total)setTimeout(done,700);}
if(im.complete)tick();else{im.addEventListener('load',tick);im.addEventListener('error',tick);}});
setTimeout(done,4500);}
/* lightbox for grids */
var links=[].slice.call(document.querySelectorAll('[data-full]'));if(!links.length)return;
var lb=document.createElement('div');lb.id='lb';lb.innerHTML='<button class="prev" aria-label="Previous">&#8249;</button><img alt=""><button class="next" aria-label="Next">&#8250;</button><button class="x" aria-label="Close">&times;</button>';
document.body.appendChild(lb);var img=lb.querySelector('img'),i=0;
function show(n){i=(n+links.length)%links.length;img.src=links[i].getAttribute('data-full');lb.classList.add('on');document.body.style.overflow='hidden';}
function hide(){lb.classList.remove('on');document.body.style.overflow='';}
links.forEach(function(a,n){a.addEventListener('click',function(e){e.preventDefault();show(n);});});
lb.querySelector('.prev').onclick=function(e){e.stopPropagation();show(i-1)};lb.querySelector('.next').onclick=function(e){e.stopPropagation();show(i+1)};
lb.querySelector('.x').onclick=function(e){e.stopPropagation();hide()};lb.onclick=function(e){if(e.target===lb||e.target===img)hide()};
document.addEventListener('keydown',function(e){if(!lb.classList.contains('on'))return;if(e.key==='Escape')hide();if(e.key==='ArrowLeft')show(i-1);if(e.key==='ArrowRight')show(i+1);});
})();
"""

VER = hashlib.md5((CSS + JS).encode()).hexdigest()[:8]
NAV = [("work", "/commercial/"), ("conceptual", "/conceptual/"), ("events", "/events/"), ("about", "/about/"), ("say hello", "/contact/")]

def page(title, body, path, desc="", section=None, image=None, pre=""):
    nav = "".join(f'<a href="{h}"{" class=on" if (section==h) else ""}>{t}</a>' for t, h in NAV)
    full = "Jesse Hudson — Photographer, Las Vegas" if path == "/" else f"{title} — Jesse Hudson"
    og = f'<meta property="og:image" content="{DOMAIN}{image}">' if image else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(full)}</title>
<meta name="description" content="{html.escape(desc or 'Jesse Hudson, photographer and creative director, Las Vegas, Nevada.')}">
<link rel="canonical" href="{DOMAIN}{path}">{og}
<meta property="og:title" content="{html.escape(full)}"><meta property="og:type" content="website">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/style.css?v={VER}"></head>
<body>
{pre}
<header><a class="brand" href="/">Jesse Hudson<small>Photographer · Las Vegas</small></a>
<nav>{nav}<button class="theme" aria-label="Toggle dark mode">light / dark</button></nav></header>
{body}
<footer><div>© Jesse Hudson · Las Vegas, Nevada</div><div><a href="mailto:{EMAIL}">{EMAIL}</a> · <a href="https://fremontphotoco.com">Fremont Photo Co</a> · <a href="https://jessehudson.world">Fine art</a> · <a href="/cv/">CV</a></div></footer>
<script src="/app.js?v={VER}" defer></script>
</body></html>"""

def showcase(slides, corner_br=""):
    """slides: list of dicts {rels:[...], title, href}. One sticky stage with a photo set per series + N scroll steps.
    Vertical scroll / up-down keys move between series; left-right keys or sideways swipe move through the photos of the current series."""
    sets = []
    for k, sl in enumerate(slides):
        imgs = "".join(
            f'<img {"src" if (k < 2 and j == 0) or (k == 0 and j < 3) else "data-src"}="/img/{r}.jpg" alt="{html.escape(sl["title"])}"{" class=on" if (k == 0 and j == 0) else ""}>'
            for j, r in enumerate(sl["rels"]))
        sets.append(f'<div class="set" data-s="{k}" data-href="{sl["href"]}">{imgs}</div>')
    items = "".join(
        f'<li{" class=on" if k == 0 else ""}><a href="{sl["href"]}">{html.escape(sl["title"])}</a></li>'
        for k, sl in enumerate(slides))
    steps = "".join(f'<div class="step" data-i="{k}"></div>' for k in range(len(slides)))
    return f"""<section class="show"><div class="stage"><div class="frame">{"".join(sets)}</div></div><div class="steps">{steps}</div></section>
<div class="meta tl"><div class="count">1 / {len(slides[0]["rels"])}</div><ul class="list">{items}</ul><div class="hint">↑↓ series · ← → photos · <a class="open" href="{slides[0]["href"]}">open series</a></div></div>
<div class="meta br">{corner_br}</div>"""

def preloader(rels):
    pile = "".join(f'<img src="/img/{r}_t.jpg" alt="">' for r in rels[:7])
    return f'<div id="pre"><div class="pile">{pile}</div><div class="pct">0%</div></div>'

def write(path, content):
    full = os.path.join(OUT, path.strip("/"), "index.html") if not path.endswith(".html") else os.path.join(OUT, path.strip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w").write(content)

def gallery_html(folder, meta, rels):
    parts = []
    for rel in rels:
        w, h = meta.get(rel, (3, 2))
        tw = THUMB if w >= h else round(THUMB * w / h); th = round(tw * h / w)
        parts.append(f'<a href="/img/{rel}.jpg" data-full="/img/{rel}.jpg"><img src="/img/{rel}_t.jpg" width="{tw}" height="{th}" loading="lazy" alt=""></a>')
    return f'<div class="masonry">{"".join(parts)}</div>'

def build(images=True):
    if os.path.exists(OUT):
        for n in os.listdir(OUT):
            if n != "img": p = os.path.join(OUT, n); shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    os.makedirs(IMG, exist_ok=True)
    open(os.path.join(OUT, "style.css"), "w").write(CSS)
    open(os.path.join(OUT, "app.js"), "w").write(JS)
    open(os.path.join(OUT, "favicon.svg"), "w").write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="#111"/><text x="16" y="22" font-family="Helvetica,Arial" font-size="16" font-weight="700" fill="#fff" text-anchor="middle">JH</text></svg>')
    open(os.path.join(OUT, "CNAME"), "w").write("jessehudsonphoto.com\n")
    open(os.path.join(OUT, ".nojekyll"), "w").write("")

    # collect image jobs
    jobs, galleries = [], {}
    def add(folder):
        rels = []
        for src in gallery_items(folder):
            rel = web_name(folder, src); rels.append(rel); jobs.append((src, rel))
        galleries[folder] = rels
    add(HOME_GALLERY)
    for _, _, items in SECTIONS:
        for slug, title, folder, blurb in items: add(folder)
    meta = make_images(jobs) if images else (json.load(open(os.path.join(ROOT, ".imgmeta.json"))) if os.path.exists(os.path.join(ROOT, ".imgmeta.json")) else {})

    urls = []
    def cover(folder):
        rels = galleries.get(folder) or []
        return rels[0] if rels else None

    # home: scroll showcase of the strongest galleries
    featured = [("commercial", "Commercial Overview", "commercial-overview"), ("conceptual", "Conceptual", "conceptual"),
                ("conceptual", "SHELTER", "shelter"),
                ("conceptual", "Crack The Surface", "crackthesurface"), ("commercial", "Cocktails", "cocktails"),
                ("conceptual", "Portraiture", "portraiture"), ("commercial", "Architecture", "architecture"),
                ("events", "Event Overview", "nightlife-overview"),
                ("conceptual", "Art", "art"), ("commercial", "Product", "product"), ("events", "EDC 2026", "edc-2026")]
    slug_of = {folder: f"/{sec}/{slug}/" for sec, _, items in SECTIONS for slug, _, folder, _ in items}
    slides = [dict(rels=galleries[f], title=t, href=slug_of[f]) for sec, t, f in featured if cover(f)]
    body = showcase(slides, corner_br="Commercial · Conceptual · Events<br>By Jesse Hudson")
    pre = preloader([s["rels"][0] for s in slides])
    write("/", page("Overview", body, "/", "Jesse Hudson, photographer and creative director in Las Vegas, Nevada.", "/", image=f"/img/{slides[0]['rels'][0]}.jpg", pre=pre)); urls.append("/")

    # sections: showcase of that section's galleries
    for sec, sec_title, items in SECTIONS:
        slides = [dict(rels=galleries[folder], title=title, href=f"/{sec}/{slug}/") for slug, title, folder, blurb in items if cover(folder)]
        body = showcase(slides, corner_br=f"{sec_title}<br>{len(slides)} series")
        write(f"/{sec}/", page(sec_title, body, f"/{sec}/", f"{sec_title} photography by Jesse Hudson.", f"/{sec}/", image=f"/img/{slides[0]['rels'][0]}.jpg")); urls.append(f"/{sec}/")
        for slug, title, folder, blurb in items:
            rels = galleries[folder]
            if not rels: continue
            slides = [dict(rel=r, title=title, href="#") for r in rels]
            # list shows gallery title once; counter tracks position
            items_html = f'<li class=on><a href="/{sec}/">{html.escape(sec_title)}</a> / {html.escape(title)}</li>'
            imgs = "".join(f'<img {"src" if k < 2 else "data-src"}="/img/{r}.jpg" alt=""{" class=on" if k == 0 else ""}>' for k, r in enumerate(rels))
            steps = "".join(f'<div class="step" data-i="{k}"></div>' for k in range(len(rels)))
            grid = gallery_html(folder, meta, rels)
            body = f"""<section class="show"><div class="stage"><div class="frame">{imgs}</div></div><div class="steps">{steps}</div></section>
<div class="meta tl"><div class="count">1 / {len(rels)}</div><ul class="list">{items_html}</ul><div class="hint">scroll ↑↓ · ← → · <a href="#all">view all</a></div></div>
<div class="meta br">{html.escape(blurb) if blurb else html.escape(title)}<br>By Jesse Hudson</div>
<div class="page" id="all"><h1>{html.escape(title)}</h1>{f'<p class="lead">{html.escape(blurb)}</p>' if blurb else ''}{grid}</div>"""
            write(f"/{sec}/{slug}/", page(title, body, f"/{sec}/{slug}/", blurb or f"{title}, photography by Jesse Hudson.", f"/{sec}/", image=f"/img/{rels[0]}.jpg")); urls.append(f"/{sec}/{slug}/")

    # video, about, cv, contact
    if VIDEO_EMBEDS:
        frames = "".join(f'<iframe src="https://www.youtube.com/embed/{v}" loading="lazy" allowfullscreen title="Video"></iframe>' if len(v) == 11 else f'<iframe src="https://player.vimeo.com/video/{v}" loading="lazy" allowfullscreen title="Video"></iframe>' for v in VIDEO_EMBEDS)
        vbody = f'<div class="page"><h1>Video</h1><div class="video">{frames}</div></div>'
    else:
        vbody = '<div class="page"><h1>Video</h1><p class="lead">Video work is available on request.</p></div>'
    write("/video/", page("Video", vbody, "/video/", "Video work by Jesse Hudson.", "/video/")); urls.append("/video/")
    write("/about/", page("About", f'<div class="page"><h1>About</h1><div class="prose">{ABOUT_HTML}</div></div>', "/about/", "About Jesse Hudson, mixed media artist and photographer in Las Vegas.", "/about/")); urls.append("/about/")
    write("/cv/", page("CV", f'<div class="page"><h1>CV</h1><div class="prose">{CV_HTML}</div></div>', "/cv/", "Curriculum vitae of Jesse Hudson.", "/cv/")); urls.append("/cv/")
    contact = f'<div class="page"><h1>Say hello</h1><div class="prose"><p>For commissions, licensing and press:</p><p style="font-size:clamp(22px,3vw,40px);letter-spacing:-.03em"><a href="mailto:{EMAIL}">{EMAIL}</a></p><p>Las Vegas, Nevada</p><p>Film developing, cameras and the shop: <a href="https://fremontphotoco.com">fremontphotoco.com</a></p></div></div>'
    write("/contact/", page("Contact", contact, "/contact/", "Contact Jesse Hudson.", "/contact/")); urls.append("/contact/")

    # 404, robots, sitemap
    open(os.path.join(OUT, "404.html"), "w").write(page("Not found", '<div class="page"><h1>Page not found</h1><p class="lead">That page moved. Start from the <a href="/">overview</a>.</p></div>', "/404.html"))
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")
    open(os.path.join(OUT, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"<url><loc>{DOMAIN}{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    n_img = sum(len(v) for v in galleries.values())
    print(f"built {len(urls)} pages, {n_img} photos, videos: {len(VIDEO_EMBEDS)}")

if __name__ == "__main__":
    build(images="--no-images" not in sys.argv)
