"""
Torrent search module for searching multiple torrent sites.
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import logging
from urllib.parse import quote_plus
import re

logger = logging.getLogger(__name__)

# Try to import py1337x
try:
    from py1337x import py1337x
    PY1337X_AVAILABLE = True
except ImportError:
    logger.warning("py1337x library not available, falling back to web scraping")
    PY1337X_AVAILABLE = False


class TorrentResult:
    """Represents a single torrent search result."""

    def __init__(self, name: str, magnet: str, size: str, seeders: int, leechers: int, source: str, url: str = None):
        self.name = name
        self.magnet = magnet
        self.size = size
        self.seeders = seeders
        self.leechers = leechers
        self.source = source
        self.url = url

    def to_dict(self):
        return {
            'name': self.name,
            'magnet': self.magnet,
            'size': self.size,
            'seeders': self.seeders,
            'leechers': self.leechers,
            'source': self.source,
            'url': self.url
        }


class TorrentSearchEngine:
    """Multi-provider torrent search engine."""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.timeout = 10
        # Initialize py1337x if available
        if PY1337X_AVAILABLE:
            self.py1337x_client = py1337x()
        else:
            self.py1337x_client = None

    def search_1337x(self, query: str, limit: int = 50, page: int = 1) -> List[TorrentResult]:
        """Search 1337x.to using py1337x API library."""
        results = []

        # Try py1337x API first
        if self.py1337x_client:
            try:
                logger.info(f"Using py1337x API to search for: {query}")
                api_results = self.py1337x_client.search(query, page=page)

                if api_results and 'items' in api_results:
                    for item in api_results['items'][:limit]:
                        try:
                            # Get torrent details for magnet link
                            torrent_id = item.get('torrentId')
                            if torrent_id:
                                torrent_info = self.py1337x_client.info(link=item.get('link'))
                                magnet = torrent_info.get('magnetLink', '')

                                if magnet:
                                    results.append(TorrentResult(
                                        name=item.get('name', 'Unknown'),
                                        magnet=magnet,
                                        size=item.get('size', 'Unknown'),
                                        seeders=int(item.get('seeders', 0)),
                                        leechers=int(item.get('leechers', 0)),
                                        source='1337x',
                                        url=item.get('link', '')
                                    ))
                        except Exception as e:
                            logger.debug(f"Error parsing py1337x result: {e}")
                            continue

                    logger.info(f"Found {len(results)} results from py1337x API")
                    return results
            except Exception as e:
                logger.error(f"Error with py1337x API: {e}, falling back to web scraping")

        # Fallback to web scraping if API fails
        return self._search_1337x_scrape(query, limit)

    def _search_1337x_scrape(self, query: str, limit: int = 20) -> List[TorrentResult]:
        """Search 1337x.to using web scraping (fallback method)."""
        results = []
        try:
            search_url = f"https://1337x.to/search/{quote_plus(query)}/1/"
            response = requests.get(search_url, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                rows = soup.select('table.table-list tbody tr')[:limit]

                for row in rows:
                    try:
                        name_elem = row.select_one('td.name a:nth-of-type(2)')
                        seeders_elem = row.select_one('td.seeds')
                        leechers_elem = row.select_one('td.leeches')
                        size_elem = row.select('td.size')[0] if row.select('td.size') else None

                        if name_elem and seeders_elem:
                            name = name_elem.text.strip()
                            torrent_url = 'https://1337x.to' + name_elem['href']
                            seeders = int(seeders_elem.text.strip())
                            leechers = int(leechers_elem.text.strip()) if leechers_elem else 0
                            size = size_elem.text.strip() if size_elem else 'Unknown'

                            # Get magnet link from detail page
                            magnet = self._get_1337x_magnet(torrent_url)
                            if magnet:
                                results.append(TorrentResult(
                                    name=name,
                                    magnet=magnet,
                                    size=size,
                                    seeders=seeders,
                                    leechers=leechers,
                                    source='1337x',
                                    url=torrent_url
                                ))
                    except Exception as e:
                        logger.debug(f"Error parsing 1337x result: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error searching 1337x: {e}")

        return results

    def _get_1337x_magnet(self, url: str) -> Optional[str]:
        """Get magnet link from 1337x torrent detail page."""
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                magnet_elem = soup.select_one('a[href^="magnet:"]')
                if magnet_elem:
                    return magnet_elem['href']
        except Exception as e:
            logger.debug(f"Error getting 1337x magnet: {e}")
        return None

    def search_thepiratebay(self, query: str, limit: int = 20) -> List[TorrentResult]:
        """Search ThePirateBay using search.php API"""
        results = []
        mirrors = [
            'https://thepiratebay.org',
            'https://thepiratebay10.org',
            'https://tpb.party'
        ]

        for mirror in mirrors:
            try:
                # Use search.php API endpoint
                search_url = f"{mirror}/search.php?q={quote_plus(query)}"
                response = requests.get(search_url, headers=self.headers, timeout=self.timeout)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Try multiple selectors for different TPB layouts
                    rows = soup.select('table#searchResult tbody tr')
                    if not rows:
                        rows = soup.select('table tbody tr')
                    if not rows:
                        rows = soup.select('tr.list-entry')

                    rows = rows[:limit]

                    for row in rows:
                        try:
                            # Try multiple selectors for torrent name
                            name_elem = row.select_one('a.detLink')
                            if not name_elem:
                                name_elem = row.select_one('div.detName a')
                            if not name_elem:
                                name_elem = row.select_one('td:nth-of-type(2) a')

                            magnet_elem = row.select_one('a[href^="magnet:"]')

                            # Get size from description
                            size_elem = row.select_one('font.detDesc')
                            if not size_elem:
                                size_elem = row.select_one('td.detDesc')

                            # Get seeders and leechers
                            seeders_elem = row.select_one('td[align="right"]')
                            if not seeders_elem:
                                tds = row.select('td')
                                seeders_elem = tds[2] if len(tds) > 2 else None
                                leechers_elem = tds[3] if len(tds) > 3 else None
                            else:
                                # Find leechers (next td)
                                leechers_elem = seeders_elem.find_next_sibling('td')

                            if name_elem and magnet_elem:
                                name = name_elem.text.strip()
                                magnet = magnet_elem['href']

                                # Parse size from description
                                size = 'Unknown'
                                if size_elem:
                                    size_text = size_elem.text
                                    # Try different size patterns
                                    size_match = re.search(r'Size[:\s]+(\d+\.?\d*\s*[KMGT]i?B)', size_text)
                                    if not size_match:
                                        size_match = re.search(r'(\d+\.?\d*\s*[KMGT]i?B)', size_text)
                                    if size_match:
                                        size = size_match.group(1)

                                # Parse seeders and leechers
                                try:
                                    seeders = int(seeders_elem.text.strip()) if seeders_elem and seeders_elem.text.strip().isdigit() else 0
                                    leechers = int(leechers_elem.text.strip()) if leechers_elem and leechers_elem.text.strip().isdigit() else 0
                                except (ValueError, AttributeError):
                                    seeders = 0
                                    leechers = 0

                                # Get detail page URL
                                detail_url = name_elem.get('href', '')
                                if detail_url and not detail_url.startswith('http'):
                                    detail_url = mirror + detail_url

                                results.append(TorrentResult(
                                    name=name,
                                    magnet=magnet,
                                    size=size,
                                    seeders=seeders,
                                    leechers=leechers,
                                    source='ThePirateBay',
                                    url=detail_url
                                ))
                        except Exception as e:
                            logger.debug(f"Error parsing TPB result: {e}")
                            continue

                    if results:
                        logger.info(f"Found {len(results)} results from {mirror}")
                        break  # Found working mirror

            except Exception as e:
                logger.debug(f"Error searching TPB mirror {mirror}: {e}")
                continue

        return results

    def search_yts(self, query: str, limit: int = 20) -> List[TorrentResult]:
        """Search YTS (movies only)"""
        results = []
        try:
            api_url = f"https://yts.mx/api/v2/list_movies.json?query_term={quote_plus(query)}&limit={limit}"
            response = requests.get(api_url, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok' and data.get('data', {}).get('movies'):
                    for movie in data['data']['movies']:
                        title = movie.get('title_long', movie.get('title', 'Unknown'))

                        for torrent in movie.get('torrents', []):
                            # Construct magnet link
                            hash_value = torrent.get('hash', '')
                            if hash_value:
                                magnet = f"magnet:?xt=urn:btih:{hash_value}&dn={quote_plus(title)}&tr=udp://tracker.opentrackr.org:1337/announce&tr=udp://open.stealth.si:80/announce"

                                results.append(TorrentResult(
                                    name=f"{title} [{torrent.get('quality', 'Unknown')}]",
                                    magnet=magnet,
                                    size=torrent.get('size', 'Unknown'),
                                    seeders=torrent.get('seeds', 0),
                                    leechers=torrent.get('peers', 0),
                                    source='YTS',
                                    url=movie.get('url', '')
                                ))

        except Exception as e:
            logger.error(f"Error searching YTS: {e}")

        return results

    def search_all(self, query: str, limit_per_source: int = 25, page: int = 1) -> List[TorrentResult]:
        """Search all providers and combine results."""
        all_results = []

        # Search all providers with higher limits
        providers = [
            ('1337x', lambda q, l: self.search_1337x(q, limit=l, page=page)),
            ('ThePirateBay', self.search_thepiratebay),
            ('YTS', self.search_yts)
        ]

        for provider_name, search_func in providers:
            try:
                logger.info(f"Searching {provider_name} for: {query}")
                results = search_func(query, limit_per_source)
                all_results.extend(results)
                logger.info(f"Found {len(results)} results from {provider_name}")
            except Exception as e:
                logger.error(f"Error searching {provider_name}: {e}")

        # Sort by seeders (descending)
        all_results.sort(key=lambda x: x.seeders, reverse=True)

        return all_results


# Global search engine instance
search_engine = TorrentSearchEngine()


def search_torrents(query: str, limit_per_source: int = 25, page: int = 1) -> List[Dict]:
    """
    Search for torrents across multiple providers.

    Args:
        query: Search query
        limit_per_source: Maximum results per provider
        page: Page number for pagination

    Returns:
        List of torrent dictionaries sorted by seeders
    """
    results = search_engine.search_all(query, limit_per_source, page)
    return [r.to_dict() for r in results]
