#!/usr/bin/env python3
"""Generate mirrored READMEs from index.html and published posts. Standard library only."""
import argparse
import base64
import json
import os
import re
from datetime import date
from html import escape, unescape
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]

def site_url():
    repository=os.environ.get("GITHUB_REPOSITORY")
    if repository:
        return f"https://{repository.split('/')[0].lower()}.github.io"
    html=(ROOT/"index.html").read_text(encoding="utf-8")
    canonical=re.search(r'<link rel="canonical" href="([^"]+)"',html)
    if not canonical:raise ValueError("index.html: missing canonical URL")
    return canonical[1].rstrip("/")
def md(fragment):
    fragment=re.sub(r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>',lambda m:"["+re.sub(r"<[^>]*>","",m[2]).strip()+"]("+m[1]+")",fragment,flags=re.S|re.I)
    fragment=re.sub(r"<strong>(.*?)</strong>",r"**\1**",fragment,flags=re.S|re.I)
    fragment=re.sub(r"<em>(.*?)</em>",r"*\1*",fragment,flags=re.S|re.I)
    return unescape(" ".join(re.sub(r"<[^>]+>","",fragment).split()))
def read_home():
    html=(ROOT/"index.html").read_text(encoding="utf-8")
    def required(pattern,label):
        match=re.search(pattern,html,re.S)
        if not match:raise ValueError(f"index.html: missing {label}")
        return match
    bio=required(r'<div\s+class="bio"\s*>(.*?)</div>',"bio")[1]
    note=required(r'<p class="profile-note">(.*?)</p>',"profile note")[1]
    languages=required(r'<p class="profile-languages">(.*?)</p>',"languages")[1]
    motto=required(r'<div class="profile-motto">(.*?)</div>\s*</div>',"motto")[1]
    links=required(r'<div class="hero-links">(.*?)</div>',"profile links")[1]
    greeting=required(r'<img class="profile-greeting" src="([^"]+)" alt="([^"]+)"',"greeting")
    community=required(r'<section[^>]*id="community"[^>]*>(.*?)</section>',"Active In")[1]
    badge=required(r'<a class="visitor-counter"[^>]*>.*?</a>',"visitor badge")[0]
    content={
        "paragraphs":[md(x) for x in re.findall(r'<p\b[^>]*>(.*?)</p>',bio,re.S)],
        "note":md(note), "languages":md(languages),
        "motto_label":md(required(r'<h3 class="motto-heading">(.*?)</h3>',"motto label")[1]),
        "quotes":[md(x) for x in re.findall(r'<p>(.*?)</p>',motto,re.S)],
        "links":[md(x) for x in re.findall(r'<a\b[^>]*>.*?</a>',links,re.S)],
        "greeting":(greeting[1],unescape(greeting[2])),
        "communities":[md(title) for title in re.findall(r'<h3>(.*?)</h3>',community,re.S)],
        "badge":re.sub(r' loading="lazy"',"",badge),
    }
    for field in ("paragraphs","quotes","links","communities"):
        if not content[field]:raise ValueError(f"index.html: empty or unrecognized {field}")
    return content

def read_post_entries(limit=3):
    found=[]
    for file in (ROOT/"posts").glob("*.md"):
        raw=file.read_text(encoding="utf-8")
        fm=re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n",raw,re.S)
        if not fm: raise ValueError(f"{file.name}: missing frontmatter")
        fields={}
        for line in fm[1].splitlines():
            if ":" in line and not line.lstrip().startswith("#"):
                k,v=line.split(":",1);fields[k.strip()]=v.strip().strip("'\"")
        if not fields.get("title") or not fields.get("date"):raise ValueError(f"{file.name}: missing title or date")
        dt=date.fromisoformat(fields["date"])
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",file.stem):raise ValueError(f"Invalid article slug: {file.stem}")
        found.append((dt,file.stem,fields["title"]))
    found.sort(reverse=True)
    return found[:limit]

def render():
    home=read_home()
    site=site_url()
    image_path,image_alt=home["greeting"]
    owner=urlsplit(site).hostname.removesuffix(".github.io")
    repository=os.environ.get("GITHUB_REPOSITORY",f"{owner}/{owner}.github.io")
    image_url=f"https://raw.githubusercontent.com/{repository}/main/"+image_path
    posts=read_post_entries()
    return (
      '## About\n\n'
      +f'<img src="{escape(image_url,quote=True)}" alt="{escape(image_alt,quote=True)}" width="430" />\n\n'
      +f'*{home["note"]}*\n\n'
      +'\n\n'.join(home["paragraphs"])+'\n\n'
      +home["languages"]+'\n\n'
      +home["motto_label"]+'\n\n'
      +'\n\n'.join(f'*{quote}*' for quote in home["quotes"])+'\n\n'
      +' · '.join(home["links"])+'\n\n'
      +home["badge"]+'\n\n'
      +f'[Visit my website for more information]({site}/)\n\n'
      +'## Active In\n\n'
      +'\n'.join(f'- {title}' for title in home["communities"])+'\n\n'
      +'## Recent Blog\n\n'
      +('\n'.join(f'- [{title}]({site}/blog/{slug}/)' for _,slug,title in posts)
         if posts else 'No published articles yet.')+'\n\n'
      +f'[View all articles]({site}/blog/)\n'
    )

def request(method,url,token,body=None):
    req=Request(url,method=method,data=json.dumps(body).encode() if body is not None else None,headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","Content-Type":"application/json","User-Agent":"FuTseYi-readme-sync"})
    with urlopen(req,timeout=30) as response:return json.load(response)
def sync_profile(text,token):
    url="https://api.github.com/repos/FuTseYi/FuTseYi/contents/README.md"
    current=request("GET",url,token)
    if base64.b64decode(current["content"]).decode("utf-8")==text:
        print("Profile README already matches.");return
    request("PUT",url,token,{"message":"docs: sync README from personal website","branch":"main","sha":current["sha"],"content":base64.b64encode(text.encode("utf-8")).decode("ascii")})
    print("Updated FuTseYi/FuTseYi README")

def update_site():
    """Inject the same latest-post list into the deployed homepage, not source HTML."""
    from html import escape as html_escape
    SITE=site_url()
    output=ROOT/"_site"/"index.html"
    html=output.read_text(encoding="utf-8")
    if "<!-- LATEST-POSTS -->" not in html:
        raise ValueError("Missing homepage Latest Posts slot")
    entries=[]
    posts=read_post_entries(limit=None)
    for dt,slug,title in posts[:3]:
        url=f"{SITE}/blog/{slug}/"
        entries.append(f'<article class="project-item"><time class="contribution-date" datetime="{dt.isoformat()}">{dt:%Y.%m.%d}</time><div><h3><a href="{html_escape(url,quote=True)}">{html_escape(title)} <span class="link-arrow" aria-hidden="true"></span></a></h3></div></article>')
    if len(posts)>3 or not posts:
        label="View all articles" if posts else "Browse recent articles"
        entries.append(f'<a class="list-toggle" href="{SITE}/blog/">{label} <span class="link-arrow" aria-hidden="true"></span></a>')
    html=re.sub(r"<!-- LATEST-POSTS -->.*?<!-- /LATEST-POSTS -->",lambda _: "".join(entries),html,flags=re.S)
    output.write_text(html,encoding="utf-8")
    print("Injected latest blog posts into deployed homepage.")

def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--sync-profile",action="store_true")
    arg.add_argument("--update-site",action="store_true")
    args=arg.parse_args()
    if args.update_site:
        update_site();return
    text=render();path=ROOT/"README.md"
    if not path.exists() or path.read_text(encoding="utf-8")!=text:
        path.write_text(text,encoding="utf-8");print("Generated website README")
    else:print("Website README unchanged")
    if args.sync_profile:
        token=os.environ.get("PROFILE_README_TOKEN","")
        if not token:raise SystemExit("PROFILE_README_TOKEN is missing; configure one fine-grained token scoped to FuTseYi/FuTseYi with Contents:write")
        sync_profile(text,token)
if __name__=="__main__":main()
