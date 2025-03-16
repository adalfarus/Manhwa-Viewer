from oaplustools.web.utils import get_user_agent
import random
import requests
from typing import List, Union, Optional, Generator, Dict, Tuple
from bs4 import BeautifulSoup
import time
from urllib.parse import quote_plus


class Search:
    def __init__(self, core=None, local_user_agent_num: int = 5):
        self.core = core
        self.local_user_agent_list = [get_user_agent() for _ in range(local_user_agent_num)]

    def get_useragent(self) -> str:
        return random.choice(self.local_user_agent_list)

    def replace_core(self, new_core):
        self.core = new_core

    def search(self, prompt: str, num_results: int = 10):
        if self.core:
            return self.core.search(query=prompt, num_results=num_results, user_agent=self.get_useragent())
        return prompt

    def api_search(self, prompt: str, api_key: str, num_results: int = 10):
        if self.core:
            return self.core.api_search(query=prompt, api_key=api_key, num_results=num_results)
        return prompt


class BingSearchCore:
    def __init__(self, advanced: bool = False):
        self.advanced = advanced

    def search(self, query: str, num_results: int = 10, user_agent: str = "") -> list:
        headers = {"User-Agent": user_agent}
        url = f'https://www.bing.com/search?q={quote_plus(query)}'
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            search_results = []
            results = soup.find_all('li', {'class': 'b_algo'})

            for result in results[:num_results]:
                title_element = result.find('h2')
                if not title_element:
                    continue
                title = title_element.text.strip()
                url = title_element.find('a')['href'].strip()

                if self.advanced:
                    description_element = result.find('p')
                    description = description_element.text.strip() if description_element else 'No description available'
                    search_results.append({"title": title, "url": url, "description": description})
                else:
                    search_results.append(url)

            return search_results
        else:
            print("Failed to retrieve the search results, status code:", response.status_code)
            return []

    def api_search(self, query, api_key, custom_config_id: str = "", num_results=10):
        search_url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {
            "q": query,
            "customconfig": custom_config_id,
            "count": num_results
        }
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()


class GoogleSearchCore:
    def __init__(self, advanced: bool = False):
        self.advanced = advanced

    def search(self, query: str, num_results: int = 10, user_agent: str = "", check: bool = True,
               blacklisted_websites: Optional[List[str]] = None) -> Union[List[str], List[Dict[str, str]]]:
        proxies = None  # If you have proxy settings, configure them here
        escaped_query = query.replace(" ", "+")
        results = []
        total_fetched = 0

        while total_fetched < num_results:
            url = "https://www.google.com/search"
            params = {"q": escaped_query, "num": num_results + 2, "start": total_fetched}
            response = self._make_request(url, params, user_agent, proxies)
            search_results = self._parse_results(response, blacklisted_websites, check, num_results - total_fetched)

            if not search_results:
                break

            results.extend(search_results)
            total_fetched += len(search_results)
            time.sleep(1)  # Respectful pause to prevent being rate-limited

        return results

    def _make_request(self, url: str, params: dict, user_agent: str = "", proxies=None) -> str:
        response = requests.get(url, headers={"User-Agent": user_agent}, params=params,
                                proxies=proxies, timeout=5)
        response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
        return response.text

    def _parse_results(self, html: str, blacklisted_websites: Optional[List[str]], check: bool, needed_results: int) ->\
     List[Union[str, Dict[str, str]]]:
        soup = BeautifulSoup(html, "html.parser")
        result_blocks = soup.find_all("div", attrs={"class": "g"})
        search_results = []

        for result in result_blocks:
            if len(search_results) >= needed_results:
                break
            parsed_result = self._extract_result_data(result)
            if not parsed_result:
                continue
            url, title, description = parsed_result

            if check and blacklisted_websites and any(blacklisted in url for blacklisted in blacklisted_websites):
                continue

            if self.advanced:
                search_results.append({"url": url, "title": title, "description": description})
            else:
                search_results.append(url)

        return search_results

    def _extract_result_data(self, result) -> Optional[Tuple[str, str, str]]:
        link = result.find("a", href=True)
        title = result.find("h3")
        description_box = result.find("div", {"style": "-webkit-line-clamp:2"})

        if link and title and description_box:
            url = link["href"]
            title_text = title.text
            description = description_box.text
            return url, title_text, description
        return None

    def api_search(self, query, api_key, cse_id, num_results=10, start=1):
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": cse_id,
            "q": query,
            "num": num_results,
            "start": start
        }
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raises an exception for HTTP errors
        return response.json()


class DuckDuckGoSearchCore:
    def __init__(self, advanced: bool = False):
        self.advanced = advanced

    def search(self, query: str, num_results: int = 10, user_agent: str = "") -> list:
        headers = {"User-Agent": user_agent}
        url = f'https://duckduckgo.com/html/?q={quote_plus(query)}'
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            search_results = []
            results = soup.find_all('div', {'class': 'result'})

            count = 0  # Counter for valid results added to search_results
            for result in results:
                if count >= num_results:
                    break  # Stop if the required number of results is reached

                title_element = result.find('a', {'class': 'result__a'})
                if not title_element or 'duckduckgo.com' in title_element['href']:
                    continue  # Skip internal links

                title = title_element.text.strip()
                url = title_element['href'].strip()

                if self.advanced:
                    description_element = result.find('a', {'class': 'result__snippet'})
                    description = description_element.text.strip() if description_element else 'No description available'
                    search_results.append({"title": title, "url": url, "description": description})
                else:
                    search_results.append(url)

                count += 1  # Increment valid result counter

            return search_results
        else:
            print("Failed to retrieve the search results, status code:", response.status_code)
            return []

    def api_search(self, query, api_key, num_results):
        pass


def local_test():
    try:
        searcher = Search()  # BingSearchCore())
        # searcher.search("Hello World")
        searcher.replace_core(GoogleSearchCore())
        print(searcher.search("Hello World"))
    except Exception as e:
        print(f"Exception occurred: {e}")
        return False
    print("Test completed successfully.")
    return True


if __name__ == "__main__":
    local_test()
