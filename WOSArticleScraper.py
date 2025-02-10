from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
import time
from difflib import SequenceMatcher


class WOSArticleScraper:
    def __init__(self):
        self.driver = None
        self.title = None
        self.keywords = []
        self.keywordsplus = []
        self.doi = None
        self.author_address = None
        self.impact_factor = None
        self.abstract = None

    def init_driver(self):
        """初始化浏览器驱动"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 无头模式
        chrome_options.add_argument("--disable-gpu")  # 禁用 GPU 硬件加速
        chrome_options.add_argument("--no-sandbox")  # 禁用沙盒模式
        chrome_options.add_argument("--disable-dev-shm-usage")  # 禁 /dev/shm 的使用
        chrome_options.add_argument("--ignore-certificate-errors")  # 忽略 SSL 证书错误

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)  # 设置页面加载的超时时间
        self.driver.set_script_timeout(30)  # 设置异步脚本执行的超时时间

    def search_article(self, title):
        """搜索文章并进入详情页"""
        try:
            self.driver.get("https://webofscience.clarivate.cn/wos/alldb/basic-search")
            """alldb：跨多个数据库的综合检索。  woscc：仅限 Web of Science 核心合集的检索。"""
            wait = WebDriverWait(self.driver, 10)  # 定义统一的等待对象

            # 处理 Cookie 弹窗（使用 JS 点击）
            self.handle_cookie_consent()

            # 显式等待 Cookie 弹窗容器消失（关键！）
            try:
                wait.until(
                    EC.invisibility_of_element_located(
                        (By.ID, "onetrust-group-container")
                    )
                )
                print("已确认 Cookie 弹窗完全关闭。")
            except TimeoutException:
                print("警告：Cookie 弹窗容器未及时关闭。")

            # ---------- 清理搜索框 ----------
            try:
                # 定位搜索输入框
                search_input = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "input[id='search-option']")
                    )
                )
                # 如果输入框已有内容，尝试点击清除按钮
                if search_input.get_attribute("value"):
                    # 定位清除按钮（通过 mat-icon 属性）
                    clear_button = wait.until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, 'mat-icon[data-mat-icon-name="close"]')
                        )
                    )
                    # 使用 JavaScript 点击避免前端拦截
                    self.driver.execute_script("arguments[0].click();", clear_button)
                    print("已清除历史搜索词")
                    time.sleep(0.5)  # 等待清除动画完成
            except Exception as e:
                print(f"清理搜索框时出现异常（尝试强制清空）: {e}")
                search_input.clear()  # 强制清空作为备用方案

            # 输入搜索标题
            # 重新定位输入框确保元素可用
            search_input = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "input[id='search-option']")
                )
            )
            # 使用动作链模拟更真实的输入
            ActionChains(self.driver).move_to_element(search_input).click().send_keys(
                title
            ).perform()

            # 点击搜索
            search_button = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'button[data-ta="run-search"]')
                )
            )
            search_button.click()

            # 检查搜索结果
            result_count = self.get_result_count()
            print(f"搜索结果数量: {result_count}")
            if result_count == 0:
                return False
            elif result_count == 1:
                self.enter_article_page()
                return True
            else:
                self.handle_multiple_results()
                return True

        except TimeoutException:
            print("搜索超时")
            return False
        except Exception as e:
            print(f"搜索流程异常: {e}")
            return False

    def handle_cookie_consent(self):
        """处理 cookie 同意弹窗（增强稳定性）"""
        try:
            wait = WebDriverWait(self.driver, 15)
            # 确保弹窗可见且可点击
            accept_button = wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "button#onetrust-accept-btn-handler")
                )
            )
            # 使用 JavaScript 点击绕过前端拦截
            self.driver.execute_script("arguments[0].click();", accept_button)
            print("已通过 JS 点击接受 cookie 同意。")
        except TimeoutException:
            print("未找到 cookie 同意弹窗，继续执行。")
        except Exception as e:
            print(f"处理 cookie 弹窗失败（最终尝试点击）: {e}")
            # 最终尝试强制点击（仅用于调试）
            try:
                accept_button.click()
            except:
                pass

    def get_result_count(self):
        """获取搜索结果数量"""
        try:
            count_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.brand-blue"))
            )
            return int(count_element.text)
        except Exception as e:
            print(f"获取结果数量失败: {e}")
            return 0

    def enter_article_page(self):
        """进入文章详情页"""
        try:
            try:
                # 等待并定位关闭按钮
                close_button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button#pendo-close-guide-30f847dd")
                    )
                )
                close_button.click()  # 点击关闭按钮
            except TimeoutException:
                print("未找到关闭按钮，继续执行。")
            except Exception as e:
                print(f"关闭弹窗失败: {e}")
            # 使用更稳定的 CSS 选择器定位标题元素
            title_element = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'a[data-ta="summary-record-title-link"]')
                )
            )
            # 确保元素可见并滚动到视图中心
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", title_element
            )
            # 使用 JavaScript 点击绕过前端拦截
            self.driver.execute_script("arguments[0].click();", title_element)
            print("成功进入文章详情页")
            return True
        except Exception as e:
            print(f"进入详情页失败: {e}")
            return False

    def scroll_and_click(self, element):
        """滚动并点击元素（直接点击，无需额外等待）"""
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element
        )
        element.click()
        print("成功进入文章详情页")

    def handle_multiple_results(self):
        """处理多个搜索结果"""
        try:
            try:
                # 等待并定位关闭按钮
                close_button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button#pendo-close-guide-30f847dd")
                    )
                )
                close_button.click()  # 点击关闭按钮
            except TimeoutException:
                print("未找到关闭按钮，继续执行。")
            except Exception as e:
                print(f"关闭弹窗失败: {e}")

            # 显式等待搜索结果列表加载完成
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'a[data-ta="summary-record-title-link"]')
                )
            )

            # 获取所有标题链接（增强定位稳定性）
            title_links = self.driver.find_elements(
                By.CSS_SELECTOR, 'a[data-ta="summary-record-title-link"]'
            )

            # 过滤无效标题
            valid_links = [
                link
                for link in title_links
                if "arXiv" not in link.text
                and "Comment" not in link.text
                and "Information" not in link.text  # 排除Supporting Information
                and "Supplementary" not in link.text  # 排除Supplementary Materials
            ]

            if len(valid_links) == 1:
                self.scroll_and_click(valid_links[0])
                return True
            elif len(valid_links) >= 2:
                self.scroll_and_click(valid_links[0])
                return True
            else:
                print("没有有效的搜索结果可供处理。")
                return False

        except Exception as e:
            print(f"处理多结果时发生错误: {e}")
            return False

    def get_article_details(self, last_name, original_title=None):
        """获取文章详细信息（含标题比对）"""
        try:
            # 关闭可能的研究助手弹窗
            try:
                close_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button#pendo-close-guide-d9649cea")
                    )
                )
                close_button.click()
            except TimeoutException:
                pass

            # 获取标题
            scraped_title = self.get_title() or ""
            # 标题模糊匹配
            if original_title and not self._is_title_match(
                original_title, scraped_title
            ):
                print(
                    f"标题匹配失败：输入「{original_title}」≠ 爬取「{scraped_title}」"
                )
                return {}  # 返回空字典

            # 若匹配成功，继续获取其他信息
            self.get_keywords()
            self.get_keywordsplus()
            self.doi = self.get_doi() or "未获取 DOI"
            self.author_address = self.get_author_address(last_name) or {
                "institution": "未获取",
                "country": "未获取",
            }
            self.abstract = self.get_abstract() or "未获取摘要"
            self.impact_factor = self.get_impact_factor()

            return self.format_details()
        except Exception as e:
            print(f"获取详情失败: {e}")
            return None

    def _is_title_match(self, original_title, scraped_title, threshold=0.8):
        """标题相似度匹配（阈值可调）"""
        original = original_title.lower().strip()
        scraped = scraped_title.lower().strip()
        return SequenceMatcher(None, original, scraped).ratio() >= threshold

    def get_title(self):
        """获取文章标题"""
        try:
            title_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "h2.title"))
            )
            return title_element.text
        except Exception as e:
            print(f"获取标题失败: {e}")
            return None

    def get_keywords(self):
        """获取作者关键词"""
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "h3#FRkeywordsTa-authorKeywordsLabel")
                )
            )
            keyword_elements = self.driver.find_elements(
                By.XPATH, "//*[contains(@id, 'FRkeywordsTa-authorKeywordLink')]"
            )

            self.keywords = [
                k.text.strip() for k in keyword_elements if k.text.strip()
            ] or ["None"]
        except Exception as e:
            print(f"获取关键词失败: {e}")
            self.keywords = ["None"]

    def get_keywordsplus(self):
        """获取Keywords Plus"""
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "h3#FRkeywordsTa-keyWordsPlusLabel")
                )
            )
            keywordplus_elements = self.driver.find_elements(
                By.XPATH, "//*[contains(@id, 'FRkeywordsTa-keyWordsPlusLink')]"
            )
            self.keywordsplus = [
                kw.text.strip().capitalize() for kw in keywordplus_elements
            ] or ["None"]
        except Exception as e:
            print(f"获取更宽泛的关键词失败: {e}")
            self.keywordsplus = ["None"]

    def get_doi(self):
        """获取DOI"""
        try:
            doi_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "span[data-ta='FullRTa-DOI']")
                )
            )
            return doi_element.text
        except Exception as e:
            print(f"获取DOI失败: {e}")
            return None

    def get_author_address(self, last_name):
        """获取作者地址信息"""
        try:
            # 展开更多作者信息
            try:
                more_author_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//span[contains(text(), "More")]')
                    )
                )
                more_author_button.click()
            except TimeoutException:
                pass

            # 展开更多地址信息
            try:
                more_address_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "#FRACTa-authorAddressView")
                    )
                )
                more_address_button.click()
            except TimeoutException:
                pass

            # 获取作者列表
            author_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.cdx-grid-data"))
            )
            author_elements = author_container.find_elements(
                By.CSS_SELECTOR, 'span.value.ng-star-inserted[id^="author-"]'
            )

            # 匹配姓氏并提取地址
            for author_element in author_elements:
                if last_name in author_element.text:
                    text_parts = author_element.text.strip().split()
                    address_num = self._extract_address_number(text_parts)
                    address_element = self.driver.find_element(
                        By.ID, f"address_{address_num}"
                    )
                    # print(f"地址序号:{address_num}")
                    return self._parse_address(address_element.text)
            return {"institution": "None", "country": "None"}
        except Exception as e:
            print(f"获取地址失败: {e}")
            return {"institution": "None", "country": "None"}

    def _extract_address_number(self, text_parts):
        """从作者信息中提取地址编号（优先提取第一个地址编号）"""
        # 删除末尾分号
        if text_parts and text_parts[-1].endswith(";"):
            text_parts = text_parts[:-1]
        # 从前往后遍历，寻找第一个包含中括号的项
        for part in text_parts:
            if "[" in part and "]" in part:
                return part.strip("[]")
        # 默认返回第一个地址
        return "1"

    def _parse_address(self, address_text):
        """辅助函数：解析地址文本"""
        address_parts = address_text.split(",")
        institution = (
            address_parts[0].strip().split(maxsplit=1)[-1].replace("\n", "")
            if address_parts
            else "None"
        )
        country = address_parts[-1].strip() if len(address_parts) >= 2 else "None"
        return {"institution": institution, "country": country}

    def get_impact_factor(self):
        """获取期刊影响因子"""
        try:
            impact_factor_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[@class='font-size-26']"))
            )
            return impact_factor_element.text.strip()
        except Exception as e:
            print(f"获取影响因子失败: {e}")
            return None

    def get_abstract(self):
        """获取摘要"""
        try:
            abstract_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[data-ta='FullRTa-abstract-basic']")
                )
            )
            return abstract_element.text
        except Exception as e:
            print(f"获取摘要失败: {e}")
            return None

    def format_details(self):
        """格式化输出"""
        return {
            "Title": self.title,
            "Impact Factor": self.impact_factor,
            "Author Keywords": ", ".join(self.keywords),
            "Keywords Plus": ", ".join(self.keywordsplus),
            "Institution": self.author_address.get("institution"),
            "Country": self.author_address.get("country"),
            "DOI": self.doi,
            "Abstract": self.abstract,
        }

    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
