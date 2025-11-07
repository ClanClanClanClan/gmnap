#!/usr/bin/env python3
"""
Rapid Real Mathematician Data Collection

Efficiently collect real mathematician names from multiple sources:
1. OpenAlex (1000 authors)
2. arXiv (500 papers = ~1500 unique authors)
3. ORCID (500 profiles)

Total target: ~3000 real mathematician names with country/affiliation data

This gives us enough REAL data to properly validate Phase 2.
"""

import requests
import json
import time
import xml.etree.ElementTree as ET
from typing import List, Dict, Set
from pathlib import Path
from collections import defaultdict
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class RapidCollector:
    """Collect real mathematician data from multiple sources quickly."""

    def __init__(self):
        self.all_profiles = []

    def collect_openalex(self, n: int = 1000) -> List[Dict]:
        """Collect n mathematician profiles from OpenAlex."""
        print(f"\n{'='*80}")
        print(f"COLLECTING FROM OPENALEX (target: {n} authors)")
        print(f"{'='*80}\n")

        profiles = []
        page = 1
        per_page = 200

        while len(profiles) < n:
            print(f"  Page {page} ({len(profiles)}/{n})...")

            response = requests.get(
                "https://api.openalex.org/authors",
                params={
                    'filter': 'topics.id:T10528',  # Mathematics
                    'per-page': per_page,
                    'page': page,
                    'select': 'id,display_name,last_known_institutions,works_count'
                },
                headers={'User-Agent': 'GMNAP-Collector (mailto:research@example.com)'}
            )

            if response.status_code != 200:
                print(f"  ⚠️  Failed: {response.status_code}")
                break

            data = response.json()
            results = data.get('results', [])

            if not results:
                break

            for author in results:
                name = author.get('display_name')
                insts = author.get('last_known_institutions', [])

                if name and insts:
                    country_code = insts[0].get('country_code')
                    if country_code:
                        profiles.append({
                            'name': name,
                            'country_code': country_code,
                            'source': 'openalex',
                            'works_count': author.get('works_count', 0)
                        })

            page += 1
            time.sleep(0.1)  # Rate limiting

            if len(results) < per_page:
                break

        profiles = profiles[:n]
        print(f"✅ Collected {len(profiles)} OpenAlex profiles\n")
        return profiles

    def collect_arxiv(self, n_papers: int = 500) -> List[Dict]:
        """Collect mathematician names from arXiv papers."""
        print(f"\n{'='*80}")
        print(f"COLLECTING FROM ARXIV (target: {n_papers} papers)")
        print(f"{'='*80}\n")

        authors_dict = {}  # Deduplicate by name
        start = 0
        max_per_request = 100

        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }

        while start < n_papers:
            batch_size = min(max_per_request, n_papers - start)
            print(f"  Papers {start} to {start + batch_size}...")

            response = requests.get(
                "http://export.arxiv.org/api/query",
                params={
                    'search_query': 'cat:math.*',
                    'start': start,
                    'max_results': batch_size,
                    'sortBy': 'submittedDate',
                    'sortOrder': 'descending'
                },
                timeout=30
            )

            if response.status_code != 200:
                print(f"  ⚠️  Failed: {response.status_code}")
                break

            root = ET.fromstring(response.content)
            entries = root.findall('atom:entry', namespaces)

            if not entries:
                break

            for entry in entries:
                author_elements = entry.findall('atom:author', namespaces)
                for author_elem in author_elements:
                    name_elem = author_elem.find('atom:name', namespaces)
                    if name_elem is not None and name_elem.text:
                        name = name_elem.text.strip()
                        if name not in authors_dict:
                            authors_dict[name] = {
                                'name': name,
                                'country_code': None,  # arXiv doesn't provide country
                                'source': 'arxiv',
                                'paper_count': 1
                            }
                        else:
                            authors_dict[name]['paper_count'] += 1

            start += batch_size
            time.sleep(3)  # arXiv rate limit

        profiles = list(authors_dict.values())
        print(f"✅ Collected {len(profiles)} unique arXiv authors\n")
        return profiles

    def collect_orcid(self, client_id: str, client_secret: str, n: int = 500) -> List[Dict]:
        """Collect mathematician profiles from ORCID."""
        print(f"\n{'='*80}")
        print(f"COLLECTING FROM ORCID (target: {n} profiles)")
        print(f"{'='*80}\n")

        # Authenticate
        print("Authenticating with ORCID...")
        auth_response = requests.post(
            "https://orcid.org/oauth/token",
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'grant_type': 'client_credentials',
                'scope': '/read-public'
            },
            headers={'Accept': 'application/json'}
        )

        if auth_response.status_code != 200:
            print(f"❌ ORCID authentication failed: {auth_response.status_code}")
            return []

        access_token = auth_response.json()['access_token']
        print("✅ Authenticated\n")

        # Search for mathematicians
        profiles = []
        start = 0
        rows = 100

        while len(profiles) < n:
            print(f"  Searching {start} to {start + rows}...")

            search_response = requests.get(
                "https://pub.orcid.org/v3.0/search/",
                params={
                    'q': 'keyword:mathematics OR affiliation-org-name:mathematics',
                    'start': start,
                    'rows': rows
                },
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/json'
                }
            )

            if search_response.status_code != 200:
                print(f"  ⚠️  Search failed: {search_response.status_code}")
                break

            data = search_response.json()
            results = data.get('result', [])

            if not results:
                break

            # Fetch a subset of profiles (to avoid rate limits)
            for result in results[:20]:  # Take first 20 from each batch
                orcid_id = result.get('orcid-identifier', {}).get('path')
                if not orcid_id:
                    continue

                # Get profile
                profile_response = requests.get(
                    f"https://pub.orcid.org/v3.0/{orcid_id}/person",
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Accept': 'application/json'
                    }
                )

                if profile_response.status_code == 200:
                    try:
                        profile_data = profile_response.json()
                        name_data = profile_data.get('name')

                        # Skip if name_data is None or empty
                        if not name_data:
                            continue

                        # Defensive extraction (handle None values)
                        given_obj = name_data.get('given-names')
                        given = given_obj.get('value', '') if given_obj else ''

                        family_obj = name_data.get('family-name')
                        family = family_obj.get('value', '') if family_obj else ''

                        if family:
                            name = f"{given} {family}".strip()

                            # Safe address extraction
                            addresses = profile_data.get('addresses', {})
                            address_list = addresses.get('address', []) if addresses else []
                            country = None
                            if address_list and len(address_list) > 0:
                                country_obj = address_list[0].get('country', {})
                                country = country_obj.get('value') if country_obj else None

                            profiles.append({
                                'name': name,
                                'country_code': country,
                                'source': 'orcid'
                            })
                    except (AttributeError, KeyError, TypeError, IndexError) as e:
                        # Log and skip problematic profiles
                        print(f"  ⚠️  Skipping profile {orcid_id}: {type(e).__name__}")
                        continue

                time.sleep(0.05)  # Rate limiting

                if len(profiles) >= n:
                    break

            start += rows
            time.sleep(0.5)

        profiles = profiles[:n]
        print(f"✅ Collected {len(profiles)} ORCID profiles\n")
        return profiles

    def combine_and_deduplicate(self, *profile_lists: List[Dict]) -> List[Dict]:
        """Combine profiles from multiple sources and deduplicate."""
        print(f"\n{'='*80}")
        print("COMBINING AND DEDUPLICATING")
        print(f"{'='*80}\n")

        all_profiles = []
        for profiles in profile_lists:
            all_profiles.extend(profiles)

        print(f"Total profiles before dedup: {len(all_profiles)}")

        # Deduplicate by name (case-insensitive)
        seen_names = set()
        unique_profiles = []

        for profile in all_profiles:
            name_normalized = profile['name'].lower().strip()
            if name_normalized not in seen_names:
                seen_names.add(name_normalized)
                unique_profiles.append(profile)

        print(f"Unique profiles after dedup: {len(unique_profiles)}")
        return unique_profiles

    def save_collected_data(self, profiles: List[Dict], output_path: str):
        """Save collected profiles."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Statistics
        source_counts = defaultdict(int)
        country_counts = defaultdict(int)

        for profile in profiles:
            source_counts[profile['source']] += 1
            country = profile.get('country_code', 'Unknown')
            country_counts[country] += 1

        data = {
            'metadata': {
                'total_profiles': len(profiles),
                'collection_date': time.strftime('%Y-%m-%d'),
                'sources': dict(source_counts),
                'top_countries': dict(sorted(country_counts.items(),
                                            key=lambda x: x[1],
                                            reverse=True)[:20])
            },
            'profiles': profiles
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Saved {len(profiles)} profiles to {output_path}")
        return data


def main():
    """Rapid collection of real mathematician data."""
    print("="*80)
    print("RAPID REAL MATHEMATICIAN DATA COLLECTION")
    print("="*80)
    print()
    print("Collecting from 3 sources:")
    print("  1. OpenAlex (1000 authors)")
    print("  2. arXiv (500 papers → ~1500 unique authors)")
    print("  3. ORCID (500 profiles)")
    print()

    collector = RapidCollector()

    # Collect from each source
    openalex_profiles = collector.collect_openalex(n=1000)
    arxiv_profiles = collector.collect_arxiv(n_papers=500)

    # ORCID (with provided credentials)
    CLIENT_ID = "APP-4OAPPEU02QJ92JX9"
    CLIENT_SECRET = "cdf5b6de-7da4-40cb-983e-f8a29de0383a"
    orcid_profiles = collector.collect_orcid(CLIENT_ID, CLIENT_SECRET, n=500)

    # Combine and deduplicate
    all_profiles = collector.combine_and_deduplicate(
        openalex_profiles,
        arxiv_profiles,
        orcid_profiles
    )

    # Save results
    output_path = "data/real_world_collection/rapid_collection_mathematicians.json"
    metadata = collector.save_collected_data(all_profiles, output_path)

    # Print statistics
    print("\n" + "="*80)
    print("COLLECTION COMPLETE")
    print("="*80)
    print(f"\nTotal unique mathematicians: {len(all_profiles)}")
    print("\nBy Source:")
    for source, count in metadata['metadata']['sources'].items():
        print(f"  {source}: {count}")

    print("\nTop 15 Countries:")
    for country, count in list(metadata['metadata']['top_countries'].items())[:15]:
        print(f"  {country}: {count}")

    # Names with country data
    with_country = sum(1 for p in all_profiles if p.get('country_code'))
    print(f"\nProfiles with country data: {with_country}/{len(all_profiles)} ({with_country/len(all_profiles)*100:.1f}%)")

    print(f"\n✅ Real mathematician data collected successfully!")
    print(f"   File: {output_path}")


if __name__ == '__main__':
    main()
