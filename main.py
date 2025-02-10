""" 函数集文件一定要选对 """

import pandas as pd
import datetime
import os
import random
import time
import logging
from WOSArticleScraper import WOSArticleScraper
from scholarly_utils import get_author_publications

# 配置
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"  # 抑制 TensorFlow 日志
MAX_RETRIES = 2  # 最大重试次数
BASE_DELAY = 1  # 基础等待时间（秒）
RATE_LIMIT_DELAY = (1, 3)  # 请求间隔随机范围（秒）
BATCH_CONFIG = [  # 批次配置（阈值从大到小排列）
    {"threshold": 100, "delay": 60},
    {"threshold": 50, "delay": 10},
    {"threshold": 5, "delay": 5},
]
SAVE_ON_FAILURE = True  # 失败时立即保存

AUTHOR_NAME = "Franco Nori"  # 作者名称配置
LAST_NAME = AUTHOR_NAME.split()[-1]  # 使用全局配置
# LAST_NAME = "Cheng-Wei"  # （中文作者需手动设置）
TARGET_COLUMNS = [  # 目标列配置
    "Impact Factor",
    "Author Keywords",
    "Keywords Plus",
    "Institution",
    "Country",
    "DOI",
    "Abstract",
]

# 日志配置
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def clean_abstract(text):
    """统一清理摘要换行符"""
    if pd.isna(text):
        return ""
    return str(text).replace("\n", " ").replace("\r", "").strip()


def get_author_publications_csv():
    """获取作者出版物信息并保存到CSV文件"""
    csv_file = get_author_publications(AUTHOR_NAME)
    if not csv_file:
        logging.error("无法获取作者出版物信息")
        return None
    return csv_file


def find_start_index(df, target_columns):
    """查找需要继续处理的起始索引"""
    for col in target_columns:
        if col in df.columns:
            mask = df[col].isna() | (df[col] == "")
            if mask.any():
                return mask.idxmax()
    return 0


def scrape_article_details(scraper, title):
    """爬取文章详细信息"""
    global LAST_NAME  # 使用全局配置
    for attempt in range(MAX_RETRIES + 1):
        try:
            if scraper.search_article(title):
                details = scraper.get_article_details(LAST_NAME, original_title=title)
                if not details:
                    logging.warning(f"标题「{title}」匹配失败，放弃此条")
                return details
            else:
                logging.warning(f"第 {attempt+1} 次搜索失败")
                time.sleep(BASE_DELAY * (2**attempt))
        except Exception as e:
            logging.error(f"错误: {str(e)}")
            time.sleep(BASE_DELAY * (2**attempt))
    return {}  # 默认返回空字典


def initialize_columns(df, target_columns):
    """初始化目标列的正确数据类型"""
    dtype_mapping = {
        "Impact Factor": "float64",
        "Author Keywords": "object",
        "Keywords Plus": "object",
        "Institution": "object",
        "Country": "object",
        "DOI": "object",
        "Abstract": "object",
    }

    for col in target_columns:
        if col not in df.columns:
            if dtype_mapping.get(col) == "float64":
                df[col] = pd.NA
            else:
                df[col] = ""
        df[col] = df[col].astype(dtype_mapping[col])
    return df


def convert_details(details, target_columns):
    """添加异常处理和更严格的数据转换"""
    converted = {}
    for col in target_columns:
        value = details.get(col, "")
        try:
            if col == "Impact Factor":
                converted[col] = pd.to_numeric(value, errors="coerce")
            elif col == "Abstract":
                converted[col] = str(value).strip()
            else:
                converted[col] = str(value) if value not in [None, ""] else ""
        except Exception as e:
            logging.warning(f"转换 {col} 时发生错误: {str(e)}")
            converted[col] = ""
    return converted


def save_progress(df, csv_path):
    """安全保存进度"""
    temp_file = csv_path + ".tmp"
    df.to_csv(temp_file, index=False)
    os.replace(temp_file, csv_path)
    logging.info(f"进度已保存至 {csv_path}")


def process_publications(df, scraper, target_columns, output_csv):
    """处理出版物信息(含断点续传)"""
    failed_indices = []
    start_index = find_start_index(df, target_columns)
    logging.info(f"检测到断点，从第 {start_index+1} 篇开始继续处理")

    processed_count = 0  # 新增处理计数器

    for index, row in df.iloc[start_index:].iterrows():
        title = row["Title"]
        logging.info(f"正在处理第 {index+1}/{len(df)} 篇: {title}")

        # 跳过已处理完成的记录
        if all(pd.notna(df.at[index, col]) for col in target_columns):
            logging.info(f"跳过已处理文章: {title}")
            continue

        # 添加随机延迟
        search_delay = random.uniform(*RATE_LIMIT_DELAY)
        logging.info(f"添加搜索延迟: {search_delay:.2f} 秒")
        time.sleep(search_delay)

        details = scrape_article_details(scraper, title)
        if not details:
            logging.warning("最终搜索失败，填充空值")
            failed_indices.append(index)
            details = {col: "" for col in target_columns}
        else:
            # 转换 details 中的每一项
            details = convert_details(details, target_columns)

        # 更新数据
        for col in target_columns:
            df.at[index, col] = details.get(col, "")

        # 保存进度（每处理5篇或遇到失败时保存）
        if (index - start_index + 1) % 5 == 0 or not details:
            save_progress(df, output_csv)
            if failed_indices:
                logging.warning(f"当前失败记录数: {len(failed_indices)}")

        # 动态延迟逻辑
        processed_count += 1
        for config in BATCH_CONFIG:
            if processed_count % config["threshold"] == 0:
                delay = config["delay"]
                logging.info(f"已完成 {processed_count} 篇，添加批次延迟: {delay} 秒")
                time.sleep(delay)
                break  # 应用最大的满足条件的延迟

    df["Abstract"] = df["Abstract"].apply(clean_abstract)

    return df, failed_indices


def save_results(df, failed_indices, clean_csv):
    """保存结果到CSV文件"""
    # 统一清理摘要
    df["Abstract"] = df["Abstract"].apply(clean_abstract)

    # 创建清洗文件（删除失败记录、国家为None，并重置序列号）
    clean_df = df.drop(index=failed_indices)
    clean_df = clean_df[clean_df["Country"] != "None"]
    clean_df = clean_df.reset_index(drop=True)
    clean_df["Sequence Number"] = range(1, len(clean_df) + 1)

    # 新增abandon文件
    abandon_csv = clean_csv.replace("clean", "abandon")
    abandon_df = df[df.index.isin(failed_indices) | (df["Country"] == "None")]
    abandon_df.to_csv(abandon_csv, index=False)

    clean_df.to_csv(clean_csv, index=False)
    logging.info(f"清洗文件已保存: {clean_csv}")
    logging.info(f"舍弃记录已保存: {abandon_csv}")


def main_run_all():
    start_time = time.time()  # 开始时间戳
    logging.info("程序启动")
    # 获取当前时间并格式化输出
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Program started at: {current_time}")

    try:
        # 第一步：通过Scholarly获取基础信息
        """通过全局变量AUTHOR_NAME获取数据"""
        original_csv = get_author_publications_csv()
        if not original_csv:
            return

        # 第二步：读取CSV（只读），添加序列号列 ，初始化列
        df = pd.read_csv(original_csv)
        if "Sequence Number" not in df.columns:
            df.insert(0, "Sequence Number", range(1, len(df) + 1))
        df = initialize_columns(df, TARGET_COLUMNS)

        # 创建新文件路径
        all_csv = f"{AUTHOR_NAME.replace(' ', '_')}_publications_all.csv"
        clean_csv = f"{AUTHOR_NAME.replace(' ', '_')}_publications_clean.csv"
        abandon_csv = f"{AUTHOR_NAME.replace(' ', '_')}_publications_abandon.csv"

        # 断点检测
        start_index = find_start_index(df, TARGET_COLUMNS)
        if start_index == 0:
            logging.info("无断点，从第一篇开始处理")
        else:
            logging.info(f"共有 {len(df)} 篇待处理，从第 {start_index+1} 篇开始")

        # 初始化爬虫
        scraper = WOSArticleScraper()
        scraper.init_driver()

        # 第三步：处理数据并保存到新文件
        try:
            df, failed_indices = process_publications(
                df, scraper, TARGET_COLUMNS, all_csv
            )
            save_progress(df, all_csv)  # 最终保存
            save_results(df, failed_indices, clean_csv)
            # 打开文件
            os.startfile(all_csv)
            os.startfile(clean_csv)
            os.startfile(abandon_csv)
        except Exception as e:
            logging.error(f"致命错误: {str(e)}")
            save_progress(df, all_csv)  # 异常时紧急保存
            raise
        finally:
            scraper.driver.delete_all_cookies()
            time.sleep(1)
            scraper.close()

    finally:  # 外层finally块  # 计算运行时间
        end_time = time.time()
        total_seconds = end_time - start_time
        hours, rem = divmod(total_seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        time_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        logging.info(f"总运行时间: {time_str}")
        print(f"总运行时间: {time_str}")


def main_scholarly_only():
    start_time = time.time()  # 开始时间戳
    logging.info("程序启动")
    # 获取当前时间并格式化输出
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Program started at: {current_time}")

    try:
        # 第一步：通过Scholarly获取基础信息
        """通过全局变量AUTHOR_NAME获取数据"""
        original_csv = get_author_publications_csv()
        if not original_csv:
            return

    finally:  # 外层finally块  # 计算运行时间
        end_time = time.time()
        total_seconds = end_time - start_time
        hours, rem = divmod(total_seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        time_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        logging.info(f"总运行时间: {time_str}")
        print(f"总运行时间: {time_str}")


def main_start_by_csv():
    start_time = time.time()  # 开始时间戳
    logging.info("程序启动")
    # 获取当前时间并格式化输出
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Program started at: {current_time}")

    try:
        # 第一步：直接使用现有CSV文件
        original_csv = f"{AUTHOR_NAME.replace(' ', '_')}_publications_original.csv"  # 动态生成文件名

        # 第二步：读取CSV（只读），添加序列号列 ，初始化列
        df = pd.read_csv(original_csv)
        if "Sequence Number" not in df.columns:
            df.insert(0, "Sequence Number", range(1, len(df) + 1))
        df = initialize_columns(df, TARGET_COLUMNS)

        # 创建新文件路径
        all_csv = f"{AUTHOR_NAME.replace(' ', '_')}_publications_all.csv"
        clean_csv = f"{AUTHOR_NAME.replace(' ', '_')}_publications_clean.csv"
        abandon_csv = f"{AUTHOR_NAME.replace(' ', '_')}_publications_abandon.csv"

        # 断点检测
        start_index = find_start_index(df, TARGET_COLUMNS)
        if start_index == 0:
            logging.info("无断点，从第一篇开始处理")
        else:
            logging.info(f"共有 {len(df)} 篇待处理，从第 {start_index+1} 篇开始")

        # 初始化爬虫
        scraper = WOSArticleScraper()
        scraper.init_driver()

        # 第三步：处理数据并保存到新文件
        try:
            df, failed_indices = process_publications(
                df, scraper, TARGET_COLUMNS, all_csv
            )
            save_progress(df, all_csv)  # 最终保存
            save_results(df, failed_indices, clean_csv)
            # 打开文件
            os.startfile(all_csv)
            os.startfile(clean_csv)
            os.startfile(abandon_csv)
        except Exception as e:
            logging.error(f"致命错误: {str(e)}")
            save_progress(df, all_csv)  # 异常时紧急保存
            raise
        finally:
            scraper.driver.delete_all_cookies()
            time.sleep(1)
            scraper.close()

    finally:  # 外层finally块  # 计算运行时间
        end_time = time.time()
        total_seconds = end_time - start_time
        hours, rem = divmod(total_seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        time_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        logging.info(f"总运行时间: {time_str}")
        print(f"总运行时间: {time_str}")


if __name__ == "__main__":
    # 从scholarly到WOS全部走一遍
    # main_run_all()

    # 只用scholarly，输出original的CSV文件
    # main_scholarly_only()

    # 输入CSV，用WOS收集详细信息。注意输入的是all（断点续传）还是original（从零开始）
    # main_start_by_csv()

    pass
