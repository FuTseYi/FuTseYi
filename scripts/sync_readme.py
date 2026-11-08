#!/usr/bin/env python3
"""Build homepage post links and synchronize the GitHub profile README."""
import argparse
import base64
import json
import os
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen
from asset_urls import version_assets
from site_metadata import site_url as production_url
from blog_index import build_index

ROOT=Path(__file__).resolve().parents[1]

def site_url():
    return production_url(ROOT)

def md(fragment):
    fragment=re.sub(r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>',lambda m:"["+re.sub(r"<[^>]*>","",m[2]).strip()+"]("+(site_url()+"/"+m[1] if m[1].startswith("#") else m[1])+")",fragment,flags=re.S|re.I)
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
    community=required(r'<section[^>]*id="active-in"[^>]*>(.*?)</section>',"Active In")[1]
    badge=required(r'<a class="visitor-counter"[^>]*>.*?</a>',"visitor badge")[0]
    content={
        "paragraphs":[md(x) for x in re.findall(r'<p\b[^>]*>(.*?)</p>',bio,re.S)],
        "note":md(note), "languages":md(languages),
        "motto_label":md(required(r'<h3 class="motto-heading">(.*?)</h3>',"motto label")[1]),
        "quotes":[md(x) for x in re.findall(r'<p>(.*?)</p>',motto,re.S)],
        "links":[md(x) for x in re.findall(r'<a\b[^>]*>.*?</a>',links,re.S)],
        "communities":[(md(title),image) for image,title in re.findall(r'<article class="project-item">\s*<img[^>]*src="([^"]+)"[^>]*>.*?<h3>(.*?)</h3>',community,re.S)],
        "badge":re.sub(r' loading="lazy"',"",badge),
    }
    for field in ("paragraphs","quotes","links","communities"):
        if not content[field]:raise ValueError(f"index.html: empty or unrecognized {field}")
    return content

def read_post_entries(limit=6):
    """Use the same ordered article metadata as BLOG_INDEX.json."""
    articles=build_index(ROOT)
    return [(date.fromisoformat(item["date"]),item["slug"],item["title"])
            for item in articles[:limit]]

def community_row(title,image,site):
    match=re.fullmatch(r'\[(.*?)\]\((.*?)\)',title)
    if not match:raise ValueError("Invalid community link")
    return f'<span><img src="{image if image.startswith("https://") else site + "/" + image}" alt="" width="32" align="middle" />&nbsp;<a href="{match[2]}">{match[1]}</a></span>'

def render():
    home=read_home()
    site=site_url()
    posts=read_post_entries()
    return (
      '## About\n\n'
      +f'**Homepage**: [{site.split("://",1)[-1]}]({site}/)\n\n'
      +f'*{home["note"]}*\n\n'
      +'\n\n'.join(home["paragraphs"])+'\n\n'
      +home["languages"]+'\n\n'
      +home["motto_label"]+'\n\n'
      +'\n\n'.join(f'*{quote}*' for quote in home["quotes"])+'\n\n'
      +' · '.join(home["links"])+'\n\n'
      +home["badge"]+'\n\n'
      +'## Active In\n\n'
      +'<p>\n'+' &nbsp;&nbsp;&nbsp; '.join(community_row(title,image,site) for title,image in home["communities"])+'\n</p>\n\n'
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
    identity={"name":os.environ.get("PROFILE_COMMITTER_NAME","github-actions[bot]"),
              "email":os.environ.get("PROFILE_COMMITTER_EMAIL","41898282+github-actions[bot]@users.noreply.github.com")}
    request("PUT",url,token,{"message":"docs: sync README from personal website","author":identity,"committer":identity,"branch":"main","sha":current["sha"],"content":base64.b64encode(text.encode("utf-8")).decode("ascii")})
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
    for dt,slug,title in posts[:6]:
        url=f"{SITE}/blog/{slug}/"
        entries.append(f'<article class="project-item"><time class="contribution-date" datetime="{dt.isoformat()}">{dt:%Y.%m.%d}</time><div><h3><a href="{html_escape(url,quote=True)}"><span class="link-label">{html_escape(title[:-2])}<span class="title-tail">{html_escape(title[-2:])}&nbsp;<span class="link-arrow" aria-hidden="true"></span></span></span></a></h3></div></article>')
    content='<div class="project-list" id="latest-posts">'+"".join(entries)+'</div>'
    if len(posts)>6 or not posts:
        label="View all articles" if posts else "Browse recent articles"
        content+=f'<a class="list-toggle" href="{SITE}/blog/">{label} <span class="link-arrow" aria-hidden="true"></span></a>'
    html=re.sub(r"<!-- LATEST-POSTS -->.*?<!-- /LATEST-POSTS -->",lambda _: content,html,flags=re.S)
    output.write_text(version_assets(html, ROOT),encoding="utf-8")
    print("Injected latest blog posts into deployed homepage.")

def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--sync-profile",action="store_true")
    arg.add_argument("--update-site",action="store_true")
    args=arg.parse_args()
    if args.update_site:
        update_site();return
    if not args.sync_profile:
        arg.error("specify --update-site or --sync-profile")
    token=os.environ.get("PROFILE_README_TOKEN","")
    if not token:raise SystemExit("PROFILE_README_TOKEN is missing; configure a GitHub App token scoped to FuTseYi/FuTseYi with Contents:write")
    sync_profile(render(),token)
if __name__=="__main__":main()
