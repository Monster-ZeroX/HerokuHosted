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

    def search_1337x(self, query: str, limit: int = 20) -> List[TorrentResult]:
        """Search 1337x.to"""
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
        """Search ThePirateBay mirrors"""
        results = []
        mirrors = [
            'https://thepiratebay.org',
            'https://thepiratebay10.org',
            'https://tpb.party'
        ]

        for mirror in mirrors:
            try:
                search_url = f"{mirror}/search/{quote_plus(query)}/1/99/0"
                response = requests.get(search_url, headers=self.headers, timeout=self.timeout)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    rows = soup.select('#searchResult tbody tr')[:limit]

                    for row in rows:
                        try:
                            name_elem = row.select_one('a.detLink')
                            magnet_elem = row.select_one('a[href^="magnet:"]')
                            size_elem = row.select_one('font.detDesc')
                            seeders_elem = row.select('td')[2] if len(row.select('td')) > 2 else None
                            leechers_elem = row.select('td')[3] if len(row.select('td')) > 3 else None

                            if name_elem and magnet_elem:
                                name = name_elem.text.strip()
                                magnet = magnet_elem['href']

                                # Parse size from description
                                size = 'Unknown'
                                if size_elem:
                                    size_match = re.search(r'Size (\d+\.?\d*\s*[KMGT]iB)', size_elem.text)
                                    if size_match:
                                        size = size_match.group(1)

                                seeders = int(seeders_elem.text.strip()) if seeders_elem else 0
                                leechers = int(leechers_elem.text.strip()) if leechers_elem else 0

                                results.append(TorrentResult(
                                    name=name,
                                    magnet=magnet,
                                    size=size,
                                    seeders=seeders,
                                    leechers=leechers,
                                    source='ThePirateBay',
                                    url=mirror + name_elem['href']
                                ))
                        except Exception as e:
                            logger.debug(f"Error parsing TPB result: {e}")
                            continue

                    if results:
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

    def search_all(self, query: str, limit_per_source: int = 10) -> List[TorrentResult]:
        """Search all providers and combine results."""
        all_results = []

        # Search all providers
        providers = [
            ('1337x', self.search_1337x),
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


def search_torrents(query: str, limit_per_source: int = 10) -> List[Dict]:
    """
    Search for torrents across multiple providers.

    Args:
        query: Search query
        limit_per_source: Maximum results per provider

    Returns:
        List of torrent dictionaries sorted by seeders
    """
    results = search_engine.search_all(query, limit_per_source)
    return [r.to_dict() for r in results]
