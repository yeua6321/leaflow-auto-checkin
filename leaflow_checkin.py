#!/usr/bin/env python3
"""
Leaflow 多账号自动签到脚本
变量名：LEAFLOW_ACCOUNTS
变量值：邮箱1:密码1,邮箱2:密码2,邮箱3:密码3
"""

import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import requests
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LeaflowAutoCheckin:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        
        if not self.email or not self.password:
            raise ValueError("邮箱和密码不能为空")
        
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """设置Chrome驱动选项"""
        chrome_options = Options()
        
        # 禁用自动化标志和兼容性选项
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 基础沙箱和安全选项
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        # 使用 Chromium 而不是 Google Chrome
        chromium_paths = [
            '/snap/bin/chromium',
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
        ]
        
        # 查找系统中可用的 Chromium
        chromium_binary = None
        for path in chromium_paths:
            if os.path.exists(path):
                chromium_binary = path
                logger.info(f"找到 Chromium 二进制文件: {path}")
                break
        
        if chromium_binary:
            chrome_options.binary_location = chromium_binary
        
        # GitHub Actions环境配置
        if os.getenv('GITHUB_ACTIONS'):
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--headless=new')  # 新版 headless 模式
            chrome_options.add_argument('--window-size=1024,768')
        else:
            # 本地非 CI 环境的配置
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-prompt-on-repost')
        
        # 通用优化选项
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-breakpad')
        chrome_options.add_argument('--disable-client-side-phishing-detection')
        chrome_options.add_argument('--disable-component-extensions-with-background-pages')
        chrome_options.add_argument('--disable-database')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-sync')
        chrome_options.add_argument('--metrics-recording-only')
        chrome_options.add_argument('--mute-audio')
        
        # 性能优化
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-preconnect')
        
        # 页面加载策略
        chrome_options.page_load_strategy = 'eager'
        
        # 尝试使用 webdriver-manager 初始化；如果失败，尝试直接创建驱动
        try:
            logger.info("初始化 ChromeDriver...")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("使用 webdriver-manager 初始化 ChromeDriver 成功")
            
        except Exception as e:
            logger.warning(f"webdriver-manager 初始化失败: {e}")
            logger.info("尝试使用系统的 ChromeDriver 或直接调用浏览器...")
            
            try:
                # 备用方案 1: 尝试直接创建驱动（系统中可能已有 chromedriver）
                self.driver = webdriver.Chrome(options=chrome_options)
                logger.info("使用系统 ChromeDriver 初始化成功")
                
            except Exception as fallback_error:
                error_msg = f"所有 ChromeDriver 初始化方式都失败: {str(fallback_error)}"
                logger.error(error_msg)
                logger.error("诊断信息：")
                logger.error("1. 确保系统已安装 Chrome 或 Chromium 浏览器:")
                logger.error("   Ubuntu/Debian: sudo apt-get install chromium-browser")
                logger.error("   或: sudo apt-get install chromium")
                logger.error("2. 定位到我的位置检查安装 -> Linux驅動:确保系统有足够的内存和磁盘空间")
                logger.error("3. 检查是否有权限访问 /dev/shm")
                logger.error("4. 对于 GitHub Actions，确保容器支持 Chrome 运行")
                raise Exception(error_msg)
        
        try:
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            logger.warning(f"无法设置导航属性: {e}")
        
        # 设置超时时间
        self.driver.set_page_load_timeout(120)
        self.driver.implicitly_wait(10)
        self.driver.set_script_timeout(60)
        
        # 设置窗口大小
        try:
            self.driver.set_window_size(1024, 768)
        except Exception as e:
            logger.warning(f"无法设置窗口大小: {e}")
        
    def close_popup(self):
        """关闭初始弹窗"""
        try:
            logger.info("尝试关闭初始弹窗...")
            time.sleep(5)  # 等待弹窗加载
            
            # 尝试关闭弹窗
            try:
                actions = ActionChains(self.driver)
                actions.move_by_offset(10, 10).click().perform()
                logger.info("已成功关闭弹窗")
                time.sleep(3)
                return True
            except:
                pass
            return False
            
        except Exception as e:
            logger.warning(f"关闭弹窗时出错: {e}")
            return False
    
    def wait_for_element_clickable(self, by, value, timeout=10):
        """等待元素可点击"""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
    
    def wait_for_element_present(self, by, value, timeout=10):
        """等待元素出现"""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    
    def open_in_new_tab(self, url):
        """在新标签页中打开URL"""
        try:
            logger.info(f"在新标签页中打开: {url}")
            # 使用JavaScript在新标签页中打开链接
            self.driver.execute_script(f"window.open('{url}', '_blank');")
            # 切换到新打开的标签页
            self.driver.switch_to.window(self.driver.window_handles[-1])
            logger.info("已切换到新标签页")
            return True
        except Exception as e:
            logger.error(f"在新标签页中打开链接失败: {e}")
            return False
    
    def click_element_in_new_tab(self, element):
        """点击元素并在新标签页中打开（适用于链接元素）"""
        try:
            # 获取元素的href属性（如果是链接）
            href = element.get_attribute('href')
            if href:
                return self.open_in_new_tab(href)
            else:
                logger.warning("元素没有href属性，尝试使用Ctrl+Click")
                # 对于没有href的元素，使用Ctrl+Click
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.key_down(Keys.CONTROL).click(element).key_up(Keys.CONTROL).perform()
                # 切换到新标签页
                self.driver.switch_to.window(self.driver.window_handles[-1])
                return True
        except Exception as e:
            logger.error(f"在新标签页中点击元素失败: {e}")
            return False
    
    def switch_to_tab(self, tab_index):
        """切换到指定索引的标签页"""
        try:
            self.driver.switch_to.window(self.driver.window_handles[tab_index])
            logger.info(f"已切换到标签页 {tab_index}")
            return True
        except Exception as e:
            logger.error(f"切换标签页失败: {e}")
            return False
    
    def close_current_tab(self):
        """关闭当前标签页并切换回第一个标签页"""
        try:
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            logger.info("已关闭当前标签页并切换回主标签页")
            return True
        except Exception as e:
            logger.error(f"关闭标签页失败: {e}")
            return False
    
    def login(self):
        """执行登录流程"""
        logger.info(f"开始登录流程")
        
        # 访问登录页面，使用超时保护
        try:
            self.driver.set_page_load_timeout(120)  # 设置页面加载超时
            self.driver.get("https://leaflow.net/login")
            logger.info("已访问登录页面")
        except TimeoutException:
            logger.warning("登录页面加载超时，但继续尝试...")
            time.sleep(10)  # 等待页面可能的部分加载
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                logger.warning("登录页面加载超时，尝试继续...")
                time.sleep(10)
            else:
                logger.error(f"访问登录页面失败: {e}")
                raise Exception(f"无法访问登录页面: {e}")
        
        time.sleep(7)
        
        # 关闭弹窗
        self.close_popup()
        
        # 输入邮箱
        try:
            logger.info("查找邮箱输入框...")
            
            # 等待页面稳定
            time.sleep(5)
            
            # 尝试多种选择器找到邮箱输入框
            email_selectors = [
                "input[type='text']",
                "input[type='email']", 
                "input[placeholder*='邮箱']",
                "input[placeholder*='邮件']",
                "input[placeholder*='email']",
                "input[name='email']",
                "input[name='username']"
            ]
            
            email_input = None
            for selector in email_selectors:
                try:
                    email_input = self.wait_for_element_clickable(By.CSS_SELECTOR, selector, 5)
                    logger.info(f"找到邮箱输入框")
                    break
                except:
                    continue
            
            if not email_input:
                raise Exception("找不到邮箱输入框")
            
            # 清除并输入邮箱
            email_input.clear()
            email_input.send_keys(self.email)
            logger.info("邮箱输入完成")
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"输入邮箱时出错: {e}")
            # 尝试使用JavaScript直接设置值
            try:
                self.driver.execute_script(f"document.querySelector('input[type=\"text\"], input[type=\"email\"]').value = '{self.email}';")
                logger.info("通过JavaScript设置邮箱")
                time.sleep(2)
            except:
                raise Exception(f"无法输入邮箱: {e}")
        
        # 等待密码输入框出现并输入密码
        try:
            logger.info("查找密码输入框...")
            
            # 等待密码框出现
            password_input = self.wait_for_element_clickable(
                By.CSS_SELECTOR, "input[type='password']", 10
            )
            
            password_input.clear()
            password_input.send_keys(self.password)
            logger.info("密码输入完成")
            time.sleep(1)
            
        except TimeoutException:
            raise Exception("找不到密码输入框")
        
        # 点击登录按钮
        try:
            logger.info("查找登录按钮...")
            login_btn_selectors = [
                "//button[contains(text(), '登录')]",
                "//button[contains(text(), 'Login')]",
                "//button[@type='submit']",
                "//input[@type='submit']",
                "button[type='submit']"
            ]
            
            login_btn = None
            for selector in login_btn_selectors:
                try:
                    if selector.startswith("//"):
                        login_btn = self.wait_for_element_clickable(By.XPATH, selector, 5)
                    else:
                        login_btn = self.wait_for_element_clickable(By.CSS_SELECTOR, selector, 5)
                    logger.info(f"找到登录按钮")
                    break
                except:
                    continue
            
            if not login_btn:
                raise Exception("找不到登录按钮")
            
            login_btn.click()
            logger.info("已点击登录按钮")
            
        except Exception as e:
            raise Exception(f"点击登录按钮失败: {e}")
        
        # 等待登录完成
        try:
            WebDriverWait(self.driver, 30).until(
                lambda driver: "dashboard" in driver.current_url or "workspaces" in driver.current_url or "login" not in driver.current_url
            )
            
            # 检查当前URL确认登录成功
            current_url = self.driver.current_url
            if "dashboard" in current_url or "workspaces" in current_url or "login" not in current_url:
                logger.info(f"登录成功，当前URL: {current_url}")
                return True
            else:
                raise Exception("登录后未跳转到正确页面")
                
        except TimeoutException:
            # 检查是否登录失败
            try:
                error_selectors = [".error", ".alert-danger", "[class*='error']", "[class*='danger']"]
                for selector in error_selectors:
                    try:
                        error_msg = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if error_msg.is_displayed():
                            raise Exception(f"登录失败: {error_msg.text}")
                    except:
                        continue
                raise Exception("登录超时，无法确认登录状态")
            except Exception as e:
                raise e
    
    def get_balance(self):
        """获取当前账号的总余额"""
        try:
            logger.info("获取账号余额...")
            
            # 跳转到仪表板页面
            self.driver.get("https://leaflow.net/dashboard")
            time.sleep(5)
            
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 尝试多种选择器查找余额元素
            balance_selectors = [
                "//*[contains(text(), '¥') or contains(text(), '￥') or contains(text(), '元')]",
                "//*[contains(@class, 'balance')]",
                "//*[contains(@class, 'money')]",
                "//*[contains(@class, 'amount')]",
                "//button[contains(@class, 'dollar')]",
                "//span[contains(@class, 'font-medium')]"
            ]
            
            for selector in balance_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text.strip()
                        # 查找包含数字和货币符号的文本
                        if any(char.isdigit() for char in text) and ('¥' in text or '￥' in text or '元' in text):
                            # 提取数字部分
                            import re
                            numbers = re.findall(r'\d+\.?\d*', text)
                            if numbers:
                                balance = numbers[0]
                                logger.info(f"找到余额: {balance}元")
                                return f"{balance}元"
                except:
                    continue
            
            logger.warning("未找到余额信息")
            return "未知"
            
        except Exception as e:
            logger.warning(f"获取余额时出错: {e}")
            return "未知"
    
    def wait_for_checkin_page_loaded(self, max_retries=5, wait_time=15):
        """等待签到页面完全加载，支持重试"""
        for attempt in range(max_retries):
            logger.info(f"等待签到页面加载，尝试 {attempt + 1}/{max_retries}，等待 {wait_time} 秒...")
            time.sleep(wait_time)
            
            try:
                # 检查页面是否完全加载
                current_url = self.driver.current_url
                page_title = self.driver.title
                logger.info(f"当前URL: {current_url}, 页面标题: {page_title}")
                
                # 检查502错误
                if "502" in page_title or "Bad Gateway" in page_title:
                    logger.warning("检测到502错误，服务器可能正在处理请求，继续等待...")
                    # 如果是在auth_callback页面，等待重定向完成
                    if "auth_callback" in current_url:
                        logger.info("检测到认证回调页面，等待服务器处理认证并重定向...")
                        # 等待URL变化或页面加载（增加等待时间，因为认证处理可能需要更长时间）
                        max_wait = 60  # 最多等待60秒
                        waited = 0
                        while waited < max_wait:
                            time.sleep(5)
                            waited += 5
                            try:
                                current_url = self.driver.current_url
                                page_title = self.driver.title
                                # 如果URL不再是auth_callback或不再是502错误，说明重定向成功
                                if "auth_callback" not in current_url:
                                    logger.info(f"认证回调完成，已重定向到: {current_url}")
                                    break
                                if "502" not in page_title and "Bad Gateway" not in page_title:
                                    logger.info(f"502错误已解决，页面标题: {page_title}")
                                    break
                                logger.info(f"仍在等待认证处理... ({waited}/{max_wait}秒)")
                            except:
                                pass
                        
                        # 刷新页面状态
                        current_url = self.driver.current_url
                        page_title = self.driver.title
                        logger.info(f"当前URL: {current_url}, 页面标题: {page_title}")
                    else:
                        # 如果不是回调页面，尝试刷新
                        logger.info("尝试刷新页面...")
                        self.driver.refresh()
                        time.sleep(5)
                        current_url = self.driver.current_url
                        page_title = self.driver.title
                    
                    # 如果仍然是502错误，继续下一次循环
                    if "502" in page_title or "Bad Gateway" in page_title:
                        logger.warning(f"第 {attempt + 1} 次尝试仍然遇到502错误，继续等待...")
                        continue
                
                # 检查是否需要登录（如果跳转到登录页面）
                if "login" in current_url.lower():
                    logger.warning("检测到需要登录，可能登录状态已失效")
                    return False
                
                # 等待页面DOM完全加载
                try:
                    WebDriverWait(self.driver, 10).until(
                        lambda driver: driver.execute_script("return document.readyState") == "complete"
                    )
                except TimeoutException:
                    logger.warning("页面DOM加载超时，但继续尝试查找元素...")
                
                # 检查页面是否包含签到相关元素 - 扩展更多选择器
                checkin_indicators = [
                    "button.checkin-btn",  # 优先使用这个选择器
                    "//button[contains(text(), '立即签到')]",
                    "//button[contains(text(), '签到')]",
                    "//button[contains(text(), '已签到')]",
                    "//button[contains(@class, 'checkin')]",
                    "//button[contains(@class, 'sign')]",
                    "//*[contains(text(), '每日签到')]",
                    "//*[contains(text(), '签到')]",
                    "button[type='button']",  # 通用按钮
                    "//button",  # 任何按钮
                    "//div[contains(@class, 'checkin')]",  # 签到容器
                    "//div[contains(text(), '签到')]"  # 包含签到文本的div
                ]
                
                found_elements = []
                for indicator in checkin_indicators:
                    try:
                        if indicator.startswith("//"):
                            elements = self.driver.find_elements(By.XPATH, indicator)
                        else:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                        
                        for element in elements:
                            if element.is_displayed():
                                text = element.text.strip()
                                # 检查元素文本是否包含签到相关关键词
                                if any(keyword in text for keyword in ['签到', 'checkin', 'sign']):
                                    found_elements.append(f"{indicator}: {text}")
                                    logger.info(f"找到签到相关元素: {indicator}, 文本: {text}")
                    except Exception as e:
                        continue
                
                if found_elements:
                    logger.info(f"成功找到 {len(found_elements)} 个签到相关元素")
                    return True
                
                # 如果没找到，尝试获取页面文本进行调试
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if "签到" in page_text or "checkin" in page_text.lower():
                        logger.info("页面包含签到相关文本，但未找到可点击元素")
                        # 即使没找到按钮，也返回True，让后续方法尝试查找
                        return True
                except:
                    pass
                
                logger.warning(f"第 {attempt + 1} 次尝试未找到签到按钮，继续等待...")
                
            except Exception as e:
                logger.warning(f"第 {attempt + 1} 次检查签到页面时出错: {e}")
        
        # 最后一次尝试：获取页面源码用于调试
        try:
            page_source = self.driver.page_source
            if "签到" in page_source or "checkin" in page_source.lower():
                logger.warning("页面源码包含签到相关文本，但元素可能未正确加载")
                return True
        except:
            pass
        
        return False
    
    def find_and_click_checkin_button(self):
        """查找并点击签到按钮 - 处理已签到状态"""
        logger.info("查找签到按钮...")
        
        try:
            # 先等待页面可能的重载
            time.sleep(8)
            
            # 扩展选择器列表，包含更多可能的按钮定位方式
            checkin_selectors = [
                "button.checkin-btn",  # 最优先
                "//button[contains(text(), '立即签到')]",
                "//button[contains(text(), '签到')]",
                "//button[contains(@class, 'checkin')]",
                "//button[contains(@class, 'sign')]",
                "button[type='submit']",
                "button[name='checkin']",
                "//button[contains(@id, 'checkin')]",
                "//button[contains(@id, 'sign')]",
                "//a[contains(text(), '签到')]",  # 可能是链接
                "//div[contains(@class, 'checkin')]//button",  # 签到容器内的按钮
                "//*[contains(text(), '立即签到')]",  # 任何包含"立即签到"的元素
            ]
            
            # 先尝试查找所有可能的按钮
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            logger.info(f"页面上找到 {len(all_buttons)} 个按钮元素")
            
            for selector in checkin_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for checkin_btn in elements:
                        if not checkin_btn.is_displayed():
                            continue
                        
                        # 检查按钮文本，如果包含"已签到"则说明今天已经签到过了
                        btn_text = checkin_btn.text.strip()
                        logger.info(f"找到按钮，文本: {btn_text}")
                        
                        if "已签到" in btn_text:
                            logger.info("今日已经签到过了！")
                            return "already_checked_in"
                        
                        # 检查按钮是否包含签到相关关键词
                        if any(keyword in btn_text.lower() for keyword in ['签到', 'checkin', 'sign']):
                            # 检查按钮是否可用
                            if checkin_btn.is_enabled():
                                logger.info(f"找到并点击签到按钮: {btn_text}")
                                # 尝试滚动到按钮位置
                                try:
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", checkin_btn)
                                    time.sleep(1)
                                except:
                                    pass
                                
                                # 尝试点击
                                try:
                                    checkin_btn.click()
                                except:
                                    # 如果普通点击失败，尝试JavaScript点击
                                    self.driver.execute_script("arguments[0].click();", checkin_btn)
                                
                                return True
                            else:
                                logger.info("签到按钮不可用，可能已经签到过了")
                                return "already_checked_in"
                        
                except Exception as e:
                    logger.debug(f"选择器 {selector} 未找到按钮: {e}")
                    continue
            
            # 如果所有选择器都失败，尝试查找所有可见按钮
            logger.warning("使用标准选择器未找到，尝试查找所有可见按钮...")
            for btn in all_buttons:
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        btn_text = btn.text.strip()
                        if any(keyword in btn_text for keyword in ['签到', 'checkin', 'sign', '立即']):
                            logger.info(f"找到可能的签到按钮: {btn_text}")
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                            time.sleep(1)
                            btn.click()
                            return True
                except:
                    continue
            
            logger.error("找不到签到按钮")
            return False
                    
        except Exception as e:
            logger.error(f"查找签到按钮时出错: {e}")
            return False
    
    def checkin(self):
        """执行签到流程"""
        logger.info("跳转到签到页面...")
        
        # 跳转到签到页面，使用超时保护
        try:
            # 临时增加页面加载超时时间
            self.driver.set_page_load_timeout(180)  # 临时设置为180秒
            
            try:
                self.driver.get("https://checkin.leaflow.net")
                logger.info("已跳转到签到页面，等待页面加载...")
            except TimeoutException:
                logger.warning("页面加载超时，但继续尝试...")
                # 即使超时，也尝试继续，因为页面可能已经部分加载
                # 等待一下让页面有机会加载
                time.sleep(10)
            except Exception as e:
                error_msg = str(e)
                if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                    logger.warning("页面加载超时，尝试使用JavaScript导航...")
                    # 尝试使用JavaScript导航作为备选方案
                    try:
                        self.driver.execute_script("window.location.href = 'https://checkin.leaflow.net';")
                        time.sleep(10)
                    except Exception as js_error:
                        logger.warning(f"JavaScript导航也遇到问题: {js_error}，继续尝试...")
                else:
                    logger.error(f"访问签到页面时出错: {e}")
                    # 尝试使用JavaScript导航作为备选方案
                    try:
                        logger.info("尝试使用JavaScript导航...")
                        self.driver.execute_script("window.location.href = 'https://checkin.leaflow.net';")
                        time.sleep(5)
                    except Exception as js_error:
                        logger.error(f"JavaScript导航也失败: {js_error}")
                        raise Exception(f"无法访问签到页面: {e}")
            
            # 恢复原始超时设置
            self.driver.set_page_load_timeout(120)
            time.sleep(5)  # 初始等待
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                logger.warning("页面加载超时，尝试继续处理...")
                # 不抛出异常，继续尝试，因为页面可能已经部分加载
                time.sleep(10)
            else:
                logger.error(f"跳转到签到页面失败: {e}")
                raise Exception(f"无法访问签到页面: {e}")
        
        # 检查是否需要重新登录
        current_url = self.driver.current_url
        page_title = self.driver.title
        
        # 检查502错误
        if "502" in page_title or "Bad Gateway" in page_title:
            logger.warning("初始访问遇到502错误，等待服务器响应...")
            time.sleep(10)  # 额外等待
            current_url = self.driver.current_url
            page_title = self.driver.title
        
        if "login" in current_url.lower():
            logger.warning("检测到需要登录，尝试重新登录...")
            if not self.login():
                raise Exception("重新登录失败，无法继续签到")
            # 重新跳转到签到页面
            self.driver.get("https://checkin.leaflow.net")
            time.sleep(5)
        
        # 等待签到页面加载（最多重试5次，每次等待15秒）
        if not self.wait_for_checkin_page_loaded(max_retries=5, wait_time=15):
            # 获取当前页面信息用于调试
            try:
                current_url = self.driver.current_url
                page_title = self.driver.title
                page_text = self.driver.find_element(By.TAG_NAME, "body").text[:500]  # 前500字符
                logger.error(f"页面URL: {current_url}")
                logger.error(f"页面标题: {page_title}")
                logger.error(f"页面内容预览: {page_text}")
                
                # 如果仍然是502错误，尝试重新访问
                if "502" in page_title or "Bad Gateway" in page_title:
                    logger.warning("检测到持续的502错误，尝试重新访问签到页面...")
                    self.driver.get("https://checkin.leaflow.net")
                    time.sleep(10)
                    # 再次尝试等待页面加载
                    if self.wait_for_checkin_page_loaded(max_retries=3, wait_time=20):
                        logger.info("重新访问后成功加载页面")
                    else:
                        raise Exception("签到页面持续返回502错误，服务器可能暂时不可用")
            except Exception as e:
                if "502" not in str(e) and "Bad Gateway" not in str(e):
                    raise Exception(f"签到页面加载失败: {str(e)}")
                else:
                    raise
        
        # 查找并点击立即签到按钮
        checkin_result = self.find_and_click_checkin_button()
        
        if checkin_result == "already_checked_in":
            return "今日已签到"
        elif checkin_result is True:
            logger.info("已点击立即签到按钮")
            time.sleep(5)  # 等待签到结果
            
            # 获取签到结果
            result_message = self.get_checkin_result()
            return result_message
        else:
            raise Exception("找不到立即签到按钮或按钮不可点击")
    
    def get_checkin_result(self):
        """获取签到结果消息"""
        try:
            # 给页面一些时间显示结果
            time.sleep(3)
            
            # 尝试查找各种可能的成功消息元素
            success_selectors = [
                ".alert-success",
                ".success",
                ".message",
                "[class*='success']",
                "[class*='message']",
                ".modal-content",  # 弹窗内容
                ".ant-message",    # Ant Design 消息
                ".el-message",     # Element UI 消息
                ".toast",          # Toast消息
                ".notification"    # 通知
            ]
            
            for selector in success_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        text = element.text.strip()
                        if text:
                            return text
                except:
                    continue
            
            # 如果没有找到特定元素，检查页面文本
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            important_keywords = ["成功", "签到", "获得", "恭喜", "谢谢", "感谢", "完成", "已签到", "连续签到"]
            
            for keyword in important_keywords:
                if keyword in page_text:
                    # 提取包含关键词的行
                    lines = page_text.split('\n')
                    for line in lines:
                        if keyword in line and len(line.strip()) < 100:  # 避免提取过长的文本
                            return line.strip()
            
            # 检查签到按钮状态变化
            try:
                checkin_btn = self.driver.find_element(By.CSS_SELECTOR, "button.checkin-btn")
                if not checkin_btn.is_enabled() or "已签到" in checkin_btn.text or "disabled" in checkin_btn.get_attribute("class"):
                    return "今日已签到完成"
            except:
                pass
            
            return "签到完成，但未找到具体结果消息"
            
        except Exception as e:
            return f"获取签到结果时出错: {str(e)}"
    
    def run(self):
        """单个账号执行流程"""
        try:
            logger.info(f"开始处理账号")
            
            # 登录
            if self.login():
                # 签到
                result = self.checkin()
                
                # 获取余额
                balance = self.get_balance()
                
                logger.info(f"签到结果: {result}, 余额: {balance}")
                return True, result, balance
            else:
                raise Exception("登录失败")
                
        except Exception as e:
            error_msg = f"自动签到失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, "未知"
        
        finally:
            if self.driver:
                self.driver.quit()

class MultiAccountManager:
    """多账号管理器 - 简化配置版本"""
    
    def __init__(self):
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.accounts = self.load_accounts()
    
    def load_accounts(self):
        """从环境变量加载多账号信息，支持冒号分隔多账号和单账号"""
        accounts = []
        
        logger.info("开始加载账号配置...")
        
        # 方法1: 冒号分隔多账号格式
        accounts_str = os.getenv('LEAFLOW_ACCOUNTS', '').strip()
        if accounts_str:
            try:
                logger.info("尝试解析冒号分隔多账号配置")
                account_pairs = [pair.strip() for pair in accounts_str.split(',')]
                
                logger.info(f"找到 {len(account_pairs)} 个账号")
                
                for i, pair in enumerate(account_pairs):
                    if ':' in pair:
                        email, password = pair.split(':', 1)
                        email = email.strip()
                        password = password.strip()
                        
                        if email and password:
                            accounts.append({
                                'email': email,
                                'password': password
                            })
                            logger.info(f"成功添加第 {i+1} 个账号")
                        else:
                            logger.warning(f"账号对格式错误")
                    else:
                        logger.warning(f"账号对缺少冒号分隔符")
                
                if accounts:
                    logger.info(f"从冒号分隔格式成功加载了 {len(accounts)} 个账号")
                    return accounts
                else:
                    logger.warning("冒号分隔配置中没有找到有效的账号信息")
            except Exception as e:
                logger.error(f"解析冒号分隔账号配置失败: {e}")
        
        # 方法2: 单账号格式
        single_email = os.getenv('LEAFLOW_EMAIL', '').strip()
        single_password = os.getenv('LEAFLOW_PASSWORD', '').strip()
        
        if single_email and single_password:
            accounts.append({
                'email': single_email,
                'password': single_password
            })
            logger.info("加载了单个账号配置")
            return accounts
        
        # 如果所有方法都失败
        logger.error("未找到有效的账号配置")
        logger.error("请检查以下环境变量设置:")
        logger.error("1. LEAFLOW_ACCOUNTS: 冒号分隔多账号 (email1:pass1,email2:pass2)")
        logger.error("2. LEAFLOW_EMAIL 和 LEAFLOW_PASSWORD: 单账号")
        
        raise ValueError("未找到有效的账号配置")
    
    def send_notification(self, results):
        """发送汇总通知到Telegram - 按照指定模板格式"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.info("Telegram配置未设置，跳过通知")
            return
        
        try:
            # 构建通知消息
            success_count = sum(1 for _, success, _, _ in results if success)
            total_count = len(results)
            current_date = datetime.now().strftime("%Y/%m/%d")
            
            message = f"🎁 Leaflow自动签到通知\n"
            message += f"📊 成功: {success_count}/{total_count}\n"
            message += f"📅 签到时间：{current_date}\n\n"
            
            for email, success, result, balance in results:
                # 隐藏邮箱部分字符以保护隐私
                masked_email = email[:3] + "***" + email[email.find("@"):]
                
                if success:
                    status = "✅"
                    message += f"账号：{masked_email}\n"
                    message += f"{status}  {result}！\n"
                    message += f"💰  当前总余额：{balance}。\n\n"
                else:
                    status = "❌"
                    message += f"账号：{masked_email}\n"
                    message += f"{status}  {result}\n\n"
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("Telegram汇总通知发送成功")
            else:
                logger.error(f"Telegram通知发送失败: {response.text}")
                
        except Exception as e:
            logger.error(f"发送Telegram通知时出错: {e}")
    
    def run_all(self):
        """运行所有账号的签到流程"""
        logger.info(f"开始执行 {len(self.accounts)} 个账号的签到任务")
        
        results = []
        
        for i, account in enumerate(self.accounts, 1):
            logger.info(f"处理第 {i}/{len(self.accounts)} 个账号")
            
            try:
                auto_checkin = LeaflowAutoCheckin(account['email'], account['password'])
                success, result, balance = auto_checkin.run()
                results.append((account['email'], success, result, balance))
                
                # 在账号之间添加间隔，避免请求过于频繁
                if i < len(self.accounts):
                    wait_time = 5
                    logger.info(f"等待{wait_time}秒后处理下一个账号...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                error_msg = f"处理账号时发生异常: {str(e)}"
                logger.error(error_msg)
                results.append((account['email'], False, error_msg, "未知"))
        
        # 发送汇总通知
        self.send_notification(results)
        
        # 返回总体结果
        success_count = sum(1 for _, success, _, _ in results if success)
        return success_count == len(self.accounts), results

def main():
    """主函数"""
    try:
        manager = MultiAccountManager()
        overall_success, detailed_results = manager.run_all()
        
        if overall_success:
            logger.info("✅ 所有账号签到成功")
            exit(0)
        else:
            success_count = sum(1 for _, success, _, _ in detailed_results if success)
            logger.warning(f"⚠️ 部分账号签到失败: {success_count}/{len(detailed_results)} 成功")
            # 即使有失败，也不退出错误状态，因为可能部分成功
            exit(0)
            
    except Exception as e:
        logger.error(f"❌ 脚本执行出错: {e}")
        exit(1)

if __name__ == "__main__":
    main()
