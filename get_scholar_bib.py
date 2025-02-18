# coding=utf-8

import requests
import time
import os
import csv
import re
import urllib.parse
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from lxml import etree
import os
# 用于存储paper标题列表
paper_list = []

# 从CSV读取paper标题信息
with open("paper_list.txt") as fp:
    r = fp.readlines()
    for row in r:
        paper_list.append(row)  # 假设每行只有一个标题
print(paper_list)


def log(fp, text):
    """日志记录函数"""
    fp.write(text + "\n")
    fp.flush()
    print(text)

def get(browser, url):
    """打开页面并处理验证码"""
    browser.get(url)
    while "you're not a robot" in browser.page_source:
        browser.get(url)
        time.sleep(20)

def fetch_bibtex(title, browser):
    """根据论文标题从Google Scholar获取BibTeX"""
    gs_url = f"https://scholar.google.com/scholar?hl=en&q={urllib.parse.quote(title)}"
    get(browser, gs_url)
    
    # 等待页面加载完毕并找到第一个文章的“引用”按钮
    # EC. 方法可选择css样式筛选或者html标签筛选，通过检查前端元素源代码修改
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a.gs_or_cit.gs_or_btn.gs_nph')))

    # 使用XPath选择“引用”按钮并点击
    citation_button = browser.find_element(By.CSS_SELECTOR, 'a.gs_or_cit.gs_or_btn.gs_nph')
    citation_button.click()
    # input("Press Enter to continue...")
    # 等待弹出窗口出现并找到“BibTeX”链接
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.gs_citi")))

    # 找到BibTeX链接并点击
    bibtex_button = browser.find_element(By.CSS_SELECTOR, 'a[href*="scholar.bib"]')

    bibtex_button.click()
    # input("Press Enter to continue...")
    # 等待BibTeX内容加载
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "pre")))

    # 获取BibTeX内容
    # 找到包含BibTeX内容的 <pre> 标签并获取其文本
    bibtex_content = browser.find_element(By.CSS_SELECTOR, "pre").text
    
    return bibtex_content

def _fetch_bibtex(title, browser):
    """根据论文标题从Google Scholar获取BibTeX"""
    gs_url = f"https://scholar.google.com/scholar?hl=en&q={urllib.parse.quote(title)}"
    get(browser, gs_url)
    root_sel = etree.HTML(browser.page_source, parser=etree.HTMLParser(encoding="utf-8"))
    print(root_sel)
    # 查找BibTeX链接
    bibtex_url = None
    for bib_link in root_sel.xpath("//div[@class='gs_or_ggsm']//a[@href]"):
        href = bib_link.get('href')
        if 'bibtex' in href:
            bibtex_url = href
            break

    if bibtex_url:
        # 请求BibTeX内容
        bibtex_page = requests.get(bibtex_url)
        return bibtex_page.text
    else:
        return None

def extract_citation_key(bibtex):
    """从BibTeX信息中提取引用标识符（如abusitta2024survey）"""
    match = re.search(r"@(article|inproceedings|){([^,]+),", bibtex) # 或是incollection。。。
    if match:
        return match.group(2)
    return None

def main():
    # 设置Selenium浏览器
    browser = webdriver.Edge()
    browser.set_window_position(0, 0)
    browser.set_window_size(1600, 900)

    # 打开一个Google Scholar页面进行验证，先随机搜索一个词，在30s内完成人机验证
    get(browser, "https://scholar.google.com/")
    time.sleep(30)

    # 存储BibTeX数据
    with open("papers.bib", "a", encoding="utf-8") as bib_file, \
         open("citations.txt", "a", encoding="utf-8") as citation_file, \
            open("log.txt", "a", encoding="utf-8") as log_file:
        # 遍历每篇论文
        for title in paper_list:
            # print(bib_file, f"Processing: {title}")
            # log(log_file, f"Processing: {title}")
            # time.sleep(20)
            try:
                bibtex = fetch_bibtex(title, browser)
                if bibtex:
                    # log(log_file, f"BibTeX for {title}:\n{bibtex}")
                    bib_file.write(f"{bibtex}\n")

                    # 提取引用标识符并保存为 \cite{key}
                    citation_key = extract_citation_key(bibtex)
                    if citation_key:
                        citation_text = f"\\cite{{{citation_key}}}"
                        citation_file.write(f"{citation_text}\n")
                        # log(log_file, f"Added citation: {citation_text}")
                    else:
                        log(log_file, f"No citation key found for {title}")
                else:
                    log(log_file, f"No BibTeX found for {title}")
                # 每处理完一篇文章后更新记录
                
                time.sleep(2)  # 适当的休眠时间来避免被封锁

            except Exception as e:
                # log(bib_file, f"Error fetching BibTeX for {title}: {e}")
                log(log_file, f"Error fetching BibTeX for {title}: {e}")
                continue
            bib_file.flush()
            citation_file.flush()
            log_file.flush()

    browser.quit()

if __name__ == "__main__":
    main()
