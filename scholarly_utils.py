import csv
import time
from scholarly import scholarly
import random
from requests.exceptions import RequestException

# 配置常量
max_retries = 3  # 最大重试次数
base_delay = 2  # 基础等待时间（秒）
rate_limit_delay = (1, 3)  # 请求间隔随机范围（秒）
keywords = {"supporting information", "supplementary", "comment"}


def safe_scholarly_request(func, *args, **kwargs):
    """带异常处理和指数退避的重试包装函数"""
    for attempt in range(max_retries):
        try:
            result = func(*args, **kwargs)
            time.sleep(random.uniform(*rate_limit_delay))  # 随机间隔
            return result
        except RequestException as e:
            print(f"Attempt {attempt+1} failed: {str(e)}")
            if attempt == max_retries - 1:
                raise
            sleep_time = base_delay * (2**attempt)  # 指数退避
            print(f"Waiting {sleep_time} seconds before retry...")
            time.sleep(sleep_time)
    return None  # 理论上不会执行到这里


def get_author_publications(author_name):
    """获取作者出版物并返回CSV文件名"""
    print(f"\n开始处理作者: {author_name}")

    try:
        search_query = safe_scholarly_request(scholarly.search_author, author_name)
        author = safe_scholarly_request(next, search_query)
        safe_scholarly_request(scholarly.fill, author)
    except Exception as e:
        print(f"作者查找失败: {str(e)}")
        return None

    # 过滤和处理出版物
    filtered_pubs = []
    seen_titles = set()

    # 进度报告配置
    progress_interval = 10  # 每处理10篇报告一次进度
    total_articles = len(author["publications"])
    success_count = 0  # 成功获取数据的文章数

    print(f"\n开始处理 {total_articles} 篇文章...")
    print("=" * 40)

    for index, pub in enumerate(author["publications"], start=1):
        try:
            # 带异常处理的文章信息获取
            filled_pub = safe_scholarly_request(scholarly.fill, pub)
            success_count += 1  # 成功获取计数
            # 提取关键信息
            title = filled_pub["bib"].get("title", "")
            pub_year = filled_pub["bib"].get("pub_year")

            # 过滤条件判断
            if (
                not pub_year
                or any(kw in title.lower() for kw in keywords)
                or title in seen_titles
            ):
                continue

            seen_titles.add(title)
            filtered_pubs.append(filled_pub)
        except:
            continue

        # 进度报告（每10篇或最后1篇）
        if index % progress_interval == 0 or index == total_articles:
            progress_percent = (index / total_articles) * 100
            print(
                f"[进度] 已检索 {index}/{total_articles} 篇 | "
                f"成功获取 {success_count} 篇 | "
                f"保留 {len(filtered_pubs)} 篇 | "
                f"完成 {progress_percent:.1f}%"
            )

    # 生成CSV文件
    csv_filename = f"{author_name.replace(' ', '_')}_publications_original.csv"
    headers = [
        "Title",
        "Publication Year",
        "Authors",
        "Journal",
        "Citations",
        "Impact Factor",
        "Author Keywords",
        "Keywords Plus",
        "Institution",
        "Country",
        "DOI",
        "Abstract",
    ]

    with open(csv_filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for idx, pub in enumerate(filtered_pubs, 1):
            writer.writerow(
                [
                    pub["bib"].get("title"),
                    pub["bib"].get("pub_year"),
                    pub["bib"].get("author"),
                    pub["bib"].get("journal"),
                    pub.get("num_citations"),
                    "",  # 占位给WOS数据
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )

    print(f"已生成初始CSV文件: {csv_filename}")
    print("=" * 40)
    print(f"处理完成报告：")
    print(f"• 共检索文章：{total_articles} 篇")
    print(f"• 成功获取数据：{success_count} 篇")
    print(f"• 最终保留文章：{len(filtered_pubs)} 篇")
    return csv_filename
