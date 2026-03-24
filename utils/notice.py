import asyncio
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup

async def get_notice_v1(url, method="GET"):
    headers = {
        "accept": "*/*",
        "accept-language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "origin": "https://www.ykvs.ntpc.edu.tw",
        "priority": "u=1, i",
        "referer": "https://www.ykvs.ntpc.edu.tw/",
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
    }

    async with AsyncSession(impersonate="chrome") as session:
        if method == "GET":
            response = await session.get(url, headers=headers)
        else:
            response = await session.post(url, headers=headers)

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for row in soup.select("tbody tr"):
        tds = row.find_all("td")
        if len(tds) < 5:
            continue
        a_tag = tds[1].find("a")
        results.append(
            {
                "link": a_tag["href"] if a_tag else None,
                "title": (
                    a_tag.get_text(strip=True) if a_tag else tds[1].get_text(strip=True)
                ),
                "publisher": tds[2].get_text(strip=True),
                "date": tds[3].get_text(strip=True),
                "views": tds[4].get_text(strip=True),
            }
        )
    return results


async def main():
    result = await get_notice_v1(
        "https://www.ykvs.ntpc.edu.tw/app/index.php?Action=mobileloadmod&Type=mobile_rcg_mstr&Nbr=23",
        method="POST",
    )
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
