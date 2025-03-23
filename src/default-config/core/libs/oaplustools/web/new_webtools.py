from urllib.parse import urlencode, urlunparse, quote_plus, urlparse, urljoin
import requests
# from duckduckgo_search import DDGS
import random
from bs4 import BeautifulSoup
import re
import json
from html import unescape
from typing import Generator, Type, Union, Optional, TypeVar, Generic, List, Dict
import time
import http.client
import urllib.parse
from abc import ABC, abstractmethod


import warnings
warnings.warn("This module is new and not usable yet. Please use oaplustools.web.webtools instead till release 1.5.0",
              UserWarning, 
              stacklevel=2)

T = TypeVar('T', bound='NonIterable')

class NonIterable(Generic[T]):
    def __init__(self, value: T) -> None:
        if hasattr(value, '__iter__'):
            raise ValueError(f'Value {value} is iterable, which is not allowed.')
        self.value = value

def get_useragent() -> str:
    _useragent_list = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.62',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0',
        "Mozilla/5.0 (Windows NT 8.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    ]
    return random.choice(_useragent_list)

def check_url(url: str, urlTitle: str, inTitle: Optional[Union[str, List[str]]]=None, blacklisted_websites: Optional[list]=None) -> Optional[str]:
    if inTitle is not None and not isinstance(inTitle, list): inTitle = [inTitle]
    if inTitle is None or all([str(x).lower() in urlTitle.lower() for x in inTitle]):
        # Checking if the URL is accessible or leads to a 404 error
        try:
            response = requests.head(url, allow_redirects=True)  # Using HEAD request to get the headers
            if response.status_code == 404:
                print(f"The URL {url} leads to a 404 error, checking next result...")
                return None
        except requests.RequestException as e:
            print(f"Error accessing URL {url}: {e}, checking next result...")
            return None
        if is_crawlable(url):
            if blacklisted_websites is None or not url.split("/")[2] in blacklisted_websites:
                return url
            else:
                print("Blacklisted URL:", url)
        else:
            print(f"The URL {url} cannot be crawled, checking next result...")
    return None
    
def is_crawlable(url: str) -> bool:
    """
    Check if the URL can be crawled by checking the robots.txt file of the website.
    """
    try:
        # Parse the given URL to get the netloc (domain) part
        domain = urlparse(url).netloc
        # Create the URL of the website's robots.txt file
        robots_txt_url = urljoin(f'https://{domain}', 'robots.txt')
        # Send a GET request to the robots.txt URL
        response = requests.get(robots_txt_url)
        # If the request was successful, check if the User-agent is allowed to crawl the URL
        if response.status_code == 200:
            # If "Disallow: /" is found for User-agent: *, it means the website can't be crawled
            if 'User-agent: *\nDisallow: /' in response.text:
                return False
            return True
        else:
            print(f"Failed to retrieve the robots.txt file, status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred while checking the robots.txt file: {e}")
    return False  # Return False if there was an error or the robots.txt file couldn't be retrieved

class search:
    class google_provider:
        def google_search(
                query: str, 
                user_agent: str, 
                num_results: Optional[int]=10, 
                lang: Optional[str]="en", 
                proxy: Optional[str]=None, 
                advanced: Optional[bool]=False, 
                sleep_interval: Optional[int]=0, 
                timeout: Optional[int]=5
        ) -> Union[Dict[str, str], str]:
            proxies = {"https": proxy} if proxy and proxy.startswith("https") else {"http": proxy} if proxy else None
            escaped_term = query.replace(" ", "+")
            start = 0

            while start < num_results:
                resp = requests.get(
                    url="https://www.google.com/search",
                    headers={"User-Agent": user_agent},
                    params={
                        "q": escaped_term,
                        "num": num_results + 2,
                        "hl": lang,
                        "start": start,
                    },
                    proxies=proxies,
                    timeout=timeout,
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                result_block = soup.find_all("div", attrs={"class": "g"})

                for result in result_block:
                    link = result.find("a", href=True)
                    title = result.find("h3")
                    description_box = result.find("div", {"style": "-webkit-line-clamp:2"})
                    
                    if description_box:
                        description = description_box.text
                        
                        if link and title and description:
                            start += 1
                            if advanced:
                                yield {"url": link["href"], "title": title.text, "description": description}
                            else:
                                yield link["href"]

                time.sleep(sleep_interval)
        
        def perform_search(
                query: str, 
                num_results: Optional[Union[int, None]]=10, 
                batch_size: Optional[int]=10, 
                check: Optional[bool]=True, 
                blacklisted_websites: Optional[list]=None
        ) -> List[str]:
            while True:
                user_agent = get_useragent()
                results = google_search(query, user_agent=user_agent, num_results=batch_size, advanced=True)
                filtered_urls = []
                for result in results:
                    url = check_url(result['url'], result['title'], blacklisted_websites=blacklisted_websites) if check else url
                    if url:
                        print("Found URL:", url)
                        filtered_urls.append(url)
                        if len(filtered_urls) == num_results:
                            break
                if not num_results:
                    break
                print("Not enough crawlable URLs found, continuing ...")
            return filtered_urls

        def search_queries(
                queries: Union[str, List[str]], 
                num_results: int, 
                batch_size: Optional[int]=10, 
                blacklisted_websites: Optional[list]=None, 
                per_query: Optional[bool]=True, 
                sort_per_query: Optional[bool]=False, 
                check: Optional[bool]=True
        ) -> Union[List[str], List[List[str]]]:
            if queries is not None and not isinstance(queries, list): queries = [queries]
            results_lst = []
            for query in queries:
                nnr = num_results if per_query else None
                urls = perform_search(query, num_results=nnr, batch_size=batch_size, check=check, blacklisted_websites=blacklisted_websites)
                
                if sort_per_query: results_lst.append(urls)
                else: results_lst.extend(urls)
            return results_lst
        
    class duckduckgo_provider:
        def ddg_instant_answer_search(query: str) -> Union[Generator[Dict[str, str], None, None], bool]:
            headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
            }
            
            params = {
                "q": query,
                "format": "json"
            }

            url = "https://api.duckduckgo.com/"
            resp = requests.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                print("Failed to retrieve the search results.")
                return False
            
            try:
                data = resp.json()
                results = data.get("Results", [])
                if results:
                    for result in results:
                        yield {
                            "title": unescape(result["Text"]),
                            "url": result["FirstURL"],
                            "body": unescape(data["AbstractText"])
                        }
            except ValueError:
                print("Failed to parse the search results.")
                return False

        def perform_search(
                query: str, 
                num_results: Optional[Union[int, None]]=10, 
                check: Optional[bool]=True, 
                blacklisted_websites: Optional[list]=None
        ) -> List[str]:
            while True:
                results = ddg_instant_answer_search(query)
                filtered_urls = []
                for result in results:
                    url = check_url(result['url'], result['title'], blacklisted_websites=blacklisted_websites) if check else url
                    if url:
                        print("Found URL:", url)
                        filtered_urls.append(url)
                        if len(filtered_urls) == num_results:
                            break
                if not num_results:
                    break
                print("Not enough crawlable URLs found, continuing ...")
            return filtered_urls
        
        def search_queries(
                queries: Union[str, List[str]], 
                num_results: int, 
                blacklisted_websites: Optional[list]=None, 
                per_query: Optional[bool]=True, 
                sort_per_query: Optional[bool]=False, 
                check: Optional[bool]=True
        ) -> Union[List[str], List[List[str]]]:
            if queries is not None and not isinstance(queries, list): queries = [queries]
            results_lst = []
            for query in queries:
                nnr = num_results if per_query else None
                urls = perform_search(query, num_results=nnr, check=check, blacklisted_websites=blacklisted_websites)
                
                if sort_per_query: results_lst.append(urls)
                else: results_lst.extend(urls)
            return results_lst
        
    class duckduckgo_search_provider:
        pass
        #def dggs_search(
        #        query: str, 
        #        num_results: Optional[int]=10
        #) -> Generator[Dict[str, str], None, None]:
        #    with DDGS(timeout=20) as ddgs:
        #        results = ddgs.text(query, timelimit=100, safesearch='off')
        #        for r in results[:num_results]:
        #            yield {"title": r['title'], "url": r['href']}
        #            
        #def perform_search(
        #        query: str, 
        #        num_results: Optional[Union[int, None]]=10, 
        #        batch_size: Optional[int]=10, 
        #        check: Optional[bool]=True, 
        #        blacklisted_websites: Optional[list]=None
        #) -> List[str]:
        #    while True:
        #        results = dggs_search(query, num_results=batch_size)
        #        filtered_urls = []
        #        for result in results:
        #            url = check_url(result['url'], result['title'], blacklisted_websites=blacklisted_websites) if check else url
        #            if url:
        #                print("Found URL:", url)
        #                filtered_urls.append(url)
        #                if len(filtered_urls) == num_results:
        #                    break
        #        if not num_results:
        #            break
        #        print("Not enough crawlable URLs found, continuing ...")
        #    return filtered_urls
        
        #def search_queries(
        #        queries: Union[str, List[str]], 
        #        num_results: int, 
        #        batch_size: Optional[int]=10, 
        #        blacklisted_websites: Optional[list]=None, 
        #        per_query: Optional[bool]=True, 
        #        sort_per_query: Optional[bool]=False, 
        #        check: Optional[bool]=True
        #) -> Union[List[str], List[List[str]]]:
        #    if queries is not None and not isinstance(queries, list): queries = [queries]
        #    results_lst = []
        #    for query in queries:
        #        nnr = num_results if per_query else None
        #        urls = perform_search(query, num_results=nnr, batch_size=batch_size, check=check, blacklisted_websites=blacklisted_websites)
                
        #        if sort_per_query: results_lst.append(urls)
        #        else: results_lst.extend(urls)
        #    return results_lst
        
    class bing_provider:
        def bing_search(
                query: str, 
                user_agent: str, 
                num_results: Optional[int]=10
        ) -> Generator[Dict[str, str], None, None]:
            url = f'https://www.bing.com/search?q={quote_plus(query)}'
            headers = {"User-Agent": user_agent}
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                print("Failed to retrieve the search results.")
                return

            soup = BeautifulSoup(response.text, 'html.parser')
            links = [
                (a.text, a['href']) for a in soup.find_all('a', href=True) if 'http' in a['href']
            ]

            for link in links[:num_results]:  # limiting the number of results
                yield {"title": link[0], "url": link[1]}

        def perform_search(
                query: str, 
                num_results: Optional[Union[int, None]]=10, 
                batch_size: Optional[int]=10, 
                check: Optional[bool]=True, 
                blacklisted_websites: Optional[list]=None
        ) -> List[str]:
            while True:
                user_agent = get_useragent()
                results = bing_search(query, user_agent=user_agent, num_results=batch_size)
                filtered_urls = []
                for result in results:
                    url = check_url(result['url'], result['title'], blacklisted_websites=blacklisted_websites) if check else url
                    if url:
                        print("Found URL:", url)
                        filtered_urls.append(url)
                        if len(filtered_urls) == num_results:
                            break
                if not num_results:
                    break
                print("Not enough crawlable URLs found, continuing ...")
            return filtered_urls

        def search_queries(
                queries: Union[str, List[str]], 
                num_results: int, 
                batch_size: Optional[int]=10, 
                blacklisted_websites: Optional[list]=None, 
                per_query: Optional[bool]=True, 
                sort_per_query: Optional[bool]=False, 
                check: Optional[bool]=True
        ) -> Union[List[str], List[List[str]]]:
            if queries is not None and not isinstance(queries, list): queries = [queries]
            results_lst = []
            for query in queries:
                nnr = num_results if per_query else None
                urls = perform_search(query, num_results=nnr, batch_size=batch_size, check=check, blacklisted_websites=blacklisted_websites)
                
                if sort_per_query: results_lst.append(urls)
                else: results_lst.extend(urls)
            return results_lst

class Alpha(ABC):
    class Response(ABC):
        def __init__(self, status, text, reason, headers):
            self.status = status
            self.text = text
            self.reason = reason
            self.headers = headers

    @abstractmethod
    def http_request(self, method, url, data=None, headers=None):
        # Parse the URL to extract the netloc (network location) and path
        url_parts = urllib.parse.urlsplit(url)
        netloc = url_parts.netloc
        path = url_parts.path or '/'
    
        # Ensure headers is a dictionary
        headers = headers or {}
    
        # If data is provided, URL encode it and set the Content-Type header
        if data:
            body = urllib.parse.urlencode(data).encode('ascii')
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            body = None
    
        # Create the connection object
        if url_parts.scheme == 'https':
            conn = http.client.HTTPSConnection(netloc)
        elif url_parts.scheme == 'http':
            conn = http.client.HTTPConnection(netloc)
        else:
            raise ValueError(f"Unsupported URL scheme: {url_parts.scheme}")
    
        try:
            # Send the HTTP request
            conn.request(method, path, body, headers)
            # Get the HTTP response
            response = conn.getresponse()
            # Read and decode the response body
            text = response.read().decode()
        finally:
            # Always close the connection
            conn.close()
    
        # Create and return a Response object
        return Response(response.status, text, response.reason, response.headers)

    @abstractmethod
    def http_get(self, url, headers=None):
        return self.http_request('GET', url, headers=headers)

    @abstractmethod
    def http_post(self, url, data=None, headers=None):
        return self.http_request('POST', url, data=data, headers=headers)

    @abstractmethod
    def http_xhr(self, url, data=None, headers=None):
        # Set the X-Requested-With header to indicate an XHR request
        headers = headers or {}
        headers['X-Requested-With'] = 'XMLHttpRequest'
        # Use the http_request function to send the GET and POST requests
        response_get = self.http_request('GET', url, headers=headers)
        response_post = self.http_request('POST', url, data=data, headers=headers)
        return response_get, response_post

def local_test():
    try:
        pass
    except Exception as e:
        print(f"Exception occurred {e}.")
        return False
    else:
        print("Test completed successfully.")
        return True

if __name__ == "__main__":
    local_test()
