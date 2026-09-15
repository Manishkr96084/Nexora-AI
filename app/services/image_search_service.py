import urllib.request
import json
import urllib.parse
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ImageSearchService:
    @classmethod
    def search_images(cls, query: str, count: int = 4) -> List[Dict[str, str]]:
        """
        Searches for real high-quality public domain/web images matching the query.
        Uses Wikimedia Commons API & DuckDuckGo Image Search fallback.
        Returns a list of dicts: [{'title': str, 'image_url': str, 'source': str}]
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        images = []

        # 1. Query Wikimedia Commons API
        try:
            encoded_query = urllib.parse.quote(clean_query)
            wiki_url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={encoded_query}&gsrnamespace=6&prop=imageinfo&iiprop=url|size&format=json&gsrlimit={count * 2}"
            req = urllib.request.Request(wiki_url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                pages = data.get('query', {}).get('pages', {})
                for pid, page in pages.items():
                    raw_title = page.get('title', '').replace('File:', '')
                    title = raw_title.rsplit('.', 1)[0].replace('_', ' ')
                    imageinfo = page.get('imageinfo', [])
                    if imageinfo and 'url' in imageinfo[0]:
                        img_url = imageinfo[0]['url']
                        # Filter out non-displayable formats
                        if not img_url.lower().endswith(('.svg', '.tif', '.tiff', '.ogv', '.webm', '.pdf', '.djvu')):
                            images.append({
                                'title': title or clean_query,
                                'image_url': img_url,
                                'source': img_url
                            })
                            if len(images) >= count:
                                break
        except Exception as e:
            logger.error(f"Wikimedia Image Search error: {e}")

        # 2. DuckDuckGo Image Search Fallback / Supplement
        if len(images) < count:
            try:
                ddg_init_url = f"https://duckduckgo.com/?q={urllib.parse.quote(clean_query)}"
                req = urllib.request.Request(ddg_init_url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
                    vqd_match = re.search(r'vqd=([\d-]+)', html)
                    if vqd_match:
                        vqd = vqd_match.group(1)
                        i_url = f"https://duckduckgo.com/i.js?q={urllib.parse.quote(clean_query)}&o=json&vqd={vqd}"
                        req2 = urllib.request.Request(i_url, headers=headers)
                        with urllib.request.urlopen(req2, timeout=5) as resp2:
                            res_json = json.loads(resp2.read().decode('utf-8'))
                            for item in res_json.get('results', []):
                                img_url = item.get('image')
                                if img_url and img_url.startswith('http') and not any(i['image_url'] == img_url for i in images):
                                    images.append({
                                        'title': item.get('title', clean_query),
                                        'image_url': img_url,
                                        'source': item.get('url', img_url)
                                    })
                                    if len(images) >= count:
                                        break
            except Exception as e:
                logger.error(f"DuckDuckGo Image Search error: {e}")

        return images[:count]

    @classmethod
    def format_image_search_markdown(cls, query: str, images: List[Dict[str, str]]) -> str:
        """Formats image search results into structured markdown cards."""
        if not images:
            return f"🔍 **Image Search Results for:** *'{query}'*\n\n⚠️ No direct images were found for this query. Please try refined keywords like `'images of BITS Pilani'` or `'photos of VIT Vellore'`."

        lines = [f"🖼️ **Image Search Results for:** *'{query}'*\n"]
        for idx, img in enumerate(images, 1):
            title = img.get('title', 'Image')
            url = img.get('image_url')
            source = img.get('source', url)
            lines.append(f"### {idx}. {title}\n![{title}]({url})\n[🔗 View Original Source]({source})\n")

        return "\n".join(lines)
