"""Собирает свежие MTProto-прокси из канала @mtpproxytg и обновляет proxies.txt, proxies.json и таблицу в README.md

Запуск: python update.py  (GitHub Actions делает это каждый час)
"""
import html, json, re, socket, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

CHANNEL = "https://t.me/s/mtpproxytg"
PAGES = 3          # сколько страниц канала просмотреть (по ~20 постов)
LIMIT = 30         # сколько живых прокси показывать
TIMEOUT = 4


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")


def collect():
    found, url = [], CHANNEL
    for _ in range(PAGES):
        page = fetch(url)
        for m in re.finditer(r'href="(?:tg|https)://(?:t\.me/)?proxy\?([^"]+)"', page):
            q = urllib.parse.parse_qs(html.unescape(m.group(1)))
            try:
                found.append((q["server"][0], int(q["port"][0]), q["secret"][0]))
            except (KeyError, ValueError):
                pass
        before = re.search(r'data-before="(\d+)"', page)
        if not before:
            break
        url = f"{CHANNEL}?before={before.group(1)}"
    seen, out = set(), []
    for p in reversed(found):  # новые первыми
        if p[:2] not in seen:
            seen.add(p[:2]); out.append(p)
    return out


def alive(p):
    try:
        with socket.create_connection(p[:2], timeout=TIMEOUT):
            return True
    except OSError:
        return False


def link(p):
    return "https://t.me/proxy?" + urllib.parse.urlencode({"server": p[0], "port": p[1], "secret": p[2]})


def main():
    proxies = collect()
    with ThreadPoolExecutor(16) as ex:
        ok = [p for p, a in zip(proxies, ex.map(alive, proxies)) if a][:LIMIT]
    now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    with open("proxies.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(link(p) for p in ok) + "\n")
    with open("proxies.json", "w", encoding="utf-8") as f:
        json.dump({"updated": now, "proxies": [{"server": s, "port": pt, "secret": sc, "link": link((s, pt, sc))} for s, pt, sc in ok]}, f, ensure_ascii=False, indent=1)
    rows = ["| # | Сервер | Порт | Подключить |", "|---|---|---|---|"]
    rows += [f"| {i} | `{s}` | {pt} | [Подключить]({link((s, pt, sc))}) |" for i, (s, pt, sc) in enumerate(ok, 1)]
    table = f"Обновлено: **{now}** · живых прокси: **{len(ok)}**\n\n" + "\n".join(rows)
    readme = open("README.md", encoding="utf-8").read()
    readme = re.sub(r"(<!-- PROXIES:START -->).*?(<!-- PROXIES:END -->)", lambda m: f"{m.group(1)}\n{table}\n{m.group(2)}", readme, flags=re.S)
    open("README.md", "w", encoding="utf-8").write(readme)
    print(f"найдено {len(proxies)}, живых {len(ok)}")


if __name__ == "__main__":
    main()
