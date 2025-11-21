from beautifulsoup_utils import *


# ------------ Company page ------------
def scrape_company(session: requests.Session, company_url: Optional[str]) -> Dict:
    if not company_url:
        return {
            "company_name_full": None,
            "company_website": None,
            "company_size": None,
            "company_industry": None,
            "company_address": None,
            "company_description": None,
        }
    soup = get_soup(session, company_url)
    smart_sleep()

    # name
    company_name = None
    for css in ["h1.company-name", "h1.title", "div.company-header h1", "div.company-info h1",
                "meta[property='og:title']", "meta[property='og:site_name']", "title"]:
        el = soup.select_one(css)
        if el:
            company_name = el.get("content") if el.name == "meta" else text(el)
            if company_name:
                company_name = re.sub(r"\s*\|\s*TopCV.*$", "", company_name, flags=re.I)
                break

    website = size = industry = address = None
    containers = [
        "div.company-overview", "div.company-detail", "div.company-profile",
        "section#company", "section.company-info", "div.box-intro-company",
        "div.company-info-container"
    ]
    container = None
    for css in containers:
        c = soup.select_one(css)
        if c:
            container = c
            break
    if container is None:
        container = soup

    rows = container.select("li, .row, .item, .info-item, .company-info-item, .dl, .d-flex")
    for row in rows:
        row_text = text(row) or ""
        label = None
        value = None
        strong = row.find(["strong", "b"])
        if strong:
            label = text(strong)
            value = row_text
            if label:
                value = re.sub(re.escape(label), "", value, flags=re.I).strip(" :-–—")
        else:
            m = re.match(r"^([^:：]+)[:：]\s*(.+)$", row_text)
            if m:
                label, value = m.group(1).strip(), m.group(2).strip()

        if not label or not value:
            continue

        ln = re.sub(r"\s+", " ", label.lower())
        if "website" in ln or "trang web" in ln:
            website = value
        elif "quy mô" in ln or "size" in ln or "nhân sự" in ln:
            size = value
        elif "lĩnh vực" in ln or "industry" in ln or "ngành" in ln:
            industry = value
        elif "địa chỉ" in ln or "address" in ln:
            address = value

    description = None
    for css in [
        "div.company-description", "div#company-description", "div.box-intro-company",
        "div.company-introduction", "div.description", "section.company-description",
        "div#readmore-company", "div#readmore-content"
    ]:
        el = soup.select_one(css)
        if el:
            description = text(el)
            if description:
                break

    return {
        "company_name_full": company_name,
        "company_website": website,
        "company_size": size,
        "company_industry": industry,
        "company_address": address,
        "company_description": description,
    }