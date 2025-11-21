from beautifulsoup_utils import *



# ------------ Job detail page ------------
def pick_info_value(soup: BeautifulSoup, title: str) -> Optional[str]:
    for sec in soup.select(".job-detail__info--section"):
        t = text(sec.select_one(".job-detail__info--section-content-title")) or ""
        if t.lower() == title.lower():
            v = sec.select_one(".job-detail__info--section-content-value")
            return text(v) if v else text(sec)
    return None

def extract_deadline(soup: BeautifulSoup) -> Optional[str]:
    for el in soup.select(".job-detail__info--deadline, .job-detail__information-detail--actions-label"):
        t = text(el)
        if t and "Hạn nộp" in t:
            m = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", t)
            return m.group(1) if m else t
    return None

def extract_tags(soup: BeautifulSoup):
    return [text(a) for a in soup.select(".job-tags a.item") if text(a)]

def extract_desc_blocks(soup: BeautifulSoup):
    data = {}
    for item in soup.select(".job-description .job-description__item"):
        h3 = text(item.select_one("h3")) or ""
        content = item.select_one(".job-description__item--content")
        if content:
            data[h3] = text(content)
    return data

def extract_working_addresses(soup: BeautifulSoup):
    out = []
    for item in soup.select(".job-description__item h3"):
        if "Địa điểm làm việc" in (text(item) or ""):
            wrap = item.find_parent(class_="job-description__item")
            if wrap:
                for d in wrap.select(".job-description__item--content div, .job-description__item--content li"):
                    val = text(d)
                    if val:
                        out.append(val)
    return out

def extract_working_times(soup: BeautifulSoup):
    out = []
    for item in soup.select(".job-description__item h3"):
        if "Thời gian làm việc" in (text(item) or ""):
            wrap = item.find_parent(class_="job-description__item")
            if wrap:
                for d in wrap.select(".job-description__item--content div, .job-description__item--content li"):
                    val = text(d)
                    if val:
                        out.append(val)
    return out

def extract_company_link_from_job(soup: BeautifulSoup) -> Optional[str]:
    cand = soup.select_one("a.company[href]") or soup.select_one("a[href*='/cong-ty/']")
    return urljoin(BASE, cand["href"]) if cand and cand.has_attr("href") else None

def scrape_job_detail(session: requests.Session, job_url: str) -> Dict:
    soup = get_soup(session, job_url)
    smart_sleep()  # nghỉ nhẹ giữa các trang

    title = text(soup.select_one(".job-detail__info--title, h1"))
    salary = pick_info_value(soup, "Mức lương")
    location = pick_info_value(soup, "Địa điểm")
    experience = pick_info_value(soup, "Kinh nghiệm")
    deadline = extract_deadline(soup)
    tags = extract_tags(soup)
    desc_blocks = extract_desc_blocks(soup)
    addrs = extract_working_addresses(soup)
    times = extract_working_times(soup)
    company_url_detail = extract_company_link_from_job(soup)

    return {
        "detail_title": title,
        "detail_salary": salary,
        "detail_location": location,
        "detail_experience": experience,
        "deadline": deadline,
        "tags": "; ".join(tags) if tags else None,
        "desc_mota": desc_blocks.get("Mô tả công việc"),
        "desc_yeucau": desc_blocks.get("Yêu cầu ứng viên"),
        "desc_quyenloi": desc_blocks.get("Quyền lợi"),
        "working_addresses": "; ".join(addrs) if addrs else None,
        "working_times": "; ".join(times) if times else None,
        "company_url_from_job": company_url_detail,
    }