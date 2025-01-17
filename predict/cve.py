import re
import time

import urllib
import flask
import requests
from bs4 import BeautifulSoup


def get_cve(cve_id: str) -> dict:
    """Returns a dictionary containing all the information required for a CVE

    Args:
        cve_id (str): The CVE ID to collect information for
    Returns:
        A dictionary with the following keys:
            "id": The CVE's ID
            "desc": The CVE's description
            "git_links": A list of tuples of the form (old link, converted link)
            "normal_links": A list of strings representing the links
    """
    cve_id = cve_id.upper()
    if is_valid_cve_id(cve_id):
        raw_cve = scrape_cve(cve_id)
        if raw_cve is not None:
            return process_cve(raw_cve)

    return None


def scrape_cve(cve_id) -> dict:
    """Collects information on a CVE entry from the NVD

    Args:
        cve_id (str): The CVE ID to collect information for
    Returns:
        A dictionary with the following keys:
            "id": The CVE's ID
            "desc": The CVE's description
            "links": A list of all the links associated with the CVE
    """
    entry = {"id": cve_id}
    url = "https://services.nvd.nist.gov/rest/json/cve/1.0/{}".format(cve_id)

    response = requests.get(url)

    # Non-existent CVE
    if not response.ok:
        return None

    data = response.json()

    cve = data["result"]["CVE_Items"][0]["cve"]

    entry["desc"] = cve["description"]["description_data"][0]["value"]
    entry["links"] = list(map(lambda reference: reference["url"], cve["references"]["reference_data"]))

    return entry


def process_cve(entry) -> dict:
    """Converts a raw CVE entry into the proper format.

    Returns:
        A dictionary with the following keys:
            "id": The CVE's ID
            "desc": The CVE's description
            "git_links": A list of tuples of the form (old link, converted link)
            "normal_links": A list of strings representing the links
    """
    links = entry["links"]

    del entry["links"]

    entry["git_links"] = []
    entry["normal_links"] = []

    for link in links:
        parsed_link = urllib.parse.urlparse(link)
        if is_github_link(parsed_link):
            entry["git_links"].append(
                (link, convert_github_link(entry["id"], parsed_link))
            )
        elif is_git_link(parsed_link):
            entry["git_links"].append(
                (link, convert_git_link(entry["id"], parsed_link))
            )
        else:
            entry["normal_links"].append(link)

    return entry


# The official CVE spec states that the numbers at the end won't exceed 7 digits
cve_pattern = re.compile("^CVE-\d{4}-\d{4,7}$")


def is_valid_cve_id(cve_id) -> bool:
    """Checks whether the given CVE ID is valid

    Args:
        cve_id (str): The supposed CVE ID
    Returns:
        True if the CVE ID was valid, false otherwise
    """
    return cve_pattern.match(cve_id) is not None


github_pattern = re.compile(
    "\/?([A-Za-z0-9\-]+)\/([A-Za-z0-9\-]+)\/commit\/([0-9a-f]{5,40})\/?$"
)


def is_github_link(parsed_link: urllib.parse.ParseResult) -> bool:
    """Checks whether the given parsed link is a github commit link

    Args:
        parsed_link (ParseResult): A named tuple representing a supposed github
            link
    Returns:
        True if the given link is a github commit link, false otherwise
    """
    return (
        (parsed_link.netloc == "github.com" or parsed_link.netloc == "www.github.com")
        and github_pattern.match(parsed_link.path) is not None
    )


def convert_github_link(cve_id: str, parsed_link: urllib.parse.ParseResult) -> str:
    """Converts the given parsed link into the format used by our system

    Args:
        cve_id (str): The CVE ID which this link will be associated with
        parsed_link (ParseResult): A named tuple representing the github link
    Returns:
        The converted link
    """
    match = github_pattern.match(parsed_link.path)

    return flask.url_for(
        "main.info_page",
        cve_id=cve_id,
        repo_user=match.group(1),
        repo_name=match.group(2),
        commit=match.group(3),
    )


# A dictionary mapping known repositories to their github mirrors.
# Dict[URL, Tuple[repo_user, repo_name]]
known_repositories = {
    "git.qemu.org": ("qemu", "qemu"),
    "git.openssl.org": ("openssl", "openssl"),
    "git.kernel.org": ("torvalds", "linux"),
    "git.videolan.org": ("FFmpeg", "FFmpeg"),
    "git.libav.org": ("libav", "libav"),
    "libvirt.org": ("libvirt", "libvirt"),
}


def is_git_link(parsed_link: urllib.parse.ParseResult) -> bool:
    """Checks whether the given parsed link is a git commit link

    Args:
        parsed_link (ParseResult): A named tuple representing a supposed git
            link
    Returns:
        True if the given link is a git commit link, false otherwise
    """
    query = urllib.parse.parse_qs(parsed_link.query)

    if "a" not in query:
        return False

    return parsed_link.netloc in known_repositories and "commit" in query["a"][0]


def convert_git_link(cve_id: str, parsed_link: urllib.parse.ParseResult) -> str:
    """Converts the given parsed link into the format used by our system

    Args:
        cve_id (str): The CVE ID which this link will be associated with
        parsed_link (ParseResult): A named tuple representing the git link
    Returns:
        The converted link
    """
    query = urllib.parse.parse_qs(parsed_link.query)

    repo_user, repo_name = known_repositories[parsed_link.netloc]

    commit = query["h"][0]

    return flask.url_for(
        "main.info_page",
        cve_id=cve_id,
        repo_user=repo_user,
        repo_name=repo_name,
        commit=commit,
    )
