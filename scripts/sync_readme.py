#!/usr/bin/env python3
"""Build homepage post links and synchronize the GitHub profile README."""
import argparse
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from asset_urls import version_assets
from site_metadata import site_url as production_url
from blog_index import build_index

ROOT=Path(__file__).resolve().parents[1]

def site_url():
    return production_url(ROOT)

class InlineMarkdown(HTMLParser):
    emphasis = {"strong": "**", "em": "*", "i": "*"}

    def __init__(self):
        super().__init__()
        self.frames = [(None, None, [])]

    def handle_starttag(self, tag, attrs):
        if tag in self.emphasis or tag == "a":
            self.frames.append((tag, dict(attrs).get("href"), []))

    def handle_data(self, data):
        self.frames[-1][2].append(data)

    def handle_endtag(self, tag):
        if self.frames[-1][0] != tag:
            return
        _, href, parts = self.frames.pop()
        content = "".join(parts)
        if tag in self.emphasis:
            marker = self.emphasis[tag]
            content = re.sub(r"\S(?:.*\S)?", lambda match: f"{marker}{match[0]}{marker}", content, flags=re.S)
        elif href:
            content = self.link(content.strip(), href)
        self.handle_data(content)

    @staticmethod
    def link(label, href):
        if href.startswith("#"):
            href=site_url()+"/"+href
        elif href.startswith("/"):
            href=site_url()+href
        return f"[{label}]({href})"

def md(fragment):
    parser = InlineMarkdown()
    parser.feed(fragment)
    parser.close()
    return " ".join("".join(parser.frames[0][2]).split())
def read_home():
    html=(ROOT/"index.html").read_text(encoding="utf-8")
    def required(pattern,label):
        match=re.search(pattern,html,re.S)
        if not match:raise ValueError(f"index.html: missing {label}")
        return match
    bio=required(r'<div\s+class="bio"\s*>(.*?)</div>',"bio")[1]
    languages=required(r'<p class="profile-languages">(.*?)</p>',"languages")[1]
    motto=required(r'<div class="profile-motto">(.*?)</div>\s*</div>',"motto")[1]
    links=required(r'<div class="hero-links">(.*?)</div>',"profile links")[1]
    community=required(r'<section[^>]*id="active-in"[^>]*>(.*?)</section>',"Active In")[1]
    badge=required(r'<a class="visitor-counter"[^>]*>.*?</a>',"visitor badge")[0]
    paragraphs=[]
    for attrs,text in re.findall(r'<p\b([^>]*)>(.*?)</p>',bio,re.S):
        classes=re.search(r'\bclass="([^"]*)"',attrs)
        value=md(text)
        paragraphs.append('*'+value+'*' if classes and 'profile-note' in classes[1].split() else value)
    content={
        "paragraphs":paragraphs,
        "languages":md(languages),
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
    (ROOT / "README.md").write_text(render(), encoding="utf-8", newline="\n")
if __name__=="__main__":main()
