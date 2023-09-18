from Server import DBMongo
import random
from Config.settings import background_js, privateProxy, manifest_json
import copy,zipfile
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time
import ddddocr
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import re
import traceback
import random

import os
working_directory = os.getcwd()
if not os.path.exists(working_directory + "/tmp"):
    os.mkdir(working_directory + "/tmp")

def start_chrome(PROXY = None):
    options = webdriver.ChromeOptions()
    if PROXY:
        db = DBMongo(database="products_2306")
        collection = "proxy"
        proxies = db.getAll(collection, filter={'region':"Hong Kong"}, column={})
        candidateProxy = random.choice(proxies)['_id']

        authentication = copy.deepcopy(background_js)
        authentication = authentication % (
            candidateProxy.split(":")[0],
            candidateProxy.split(":")[1],
            privateProxy['username'],
            privateProxy['password']
        )
        
        pluginfile = 'dump/proxy_auth_plugin.zip'
        with zipfile.ZipFile(pluginfile, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", authentication)
        options.add_extension(pluginfile)

    driver = webdriver.Chrome('/usr/local/bin/chromedriver', options=options)
    # driver = webdriver.Edge(executable_path="C:/Users/zhili/AmazonSpider/msedgedriver.exe")
    driver.get("https://www.amazon.com")
    driver.maximize_window()
    # driver = decaptcha(driver)
    time.sleep(5)
    return driver

def decaptcha(driver):
    ocr = ddddocr.DdddOcr()
    while True:
        captcha = None
        try:
            captcha = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//form[@action='/errors/validateCaptcha']//div[@class='a-row a-text-center']/img")))
        except Exception as e:
            break
            pass
        else:
            if captcha is not None:
                url = captcha.get_attribute('src')
                response = requests.get(url)
                filename = 'amz_captcha.png'
                with open(f"./fig/{filename}", 'wb') as f:
                    f.write(response.content)

                with open(f"./fig/{filename}", 'rb') as f:
                    img_bytes = f.read()
                res = ocr.classification(img_bytes).upper()
                if len(res) != 6:
                    driver.refresh()
                    time.sleep(10)
                    continue
                captcha_input_box = driver.find_element(By.XPATH, "//input[@id='captchacharacters']")
                for p in str(res):
                    captcha_input_box.send_keys(p)
                    time.sleep(0.5) 
                sumbit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                sumbit_button.click()
            else:
                break
        time.sleep(10)
    return driver

def spider(driver, kind, node):
    cur_path = kind
    cur_node = node
    # find and click the menu button 'all'
    all_button = driver.find_element_by_id("nav-hamburger-menu")
    all_button.click()
    time.sleep(2)
    # find the menu and click 'see all' button, then get to the expected kind of products
    menu = driver.find_element_by_id("hmenu-content")
    if kind in pre_kinds:
        li_group = menu.find_elements_by_xpath("*[@class='hmenu hmenu-visible']/li")
        for li in li_group[6:10]:
            if li.text == kind:
                li.click()
                break
    else:        
        compress_button = menu.find_element_by_xpath(".//*[@class='hmenu-item hmenu-compressed-btn']")
        compress_button.click()
        time.sleep(2)
        li_group = driver.find_elements_by_xpath("//*[@class='hmenu-compress-section']/li")
        for li in li_group[1:]:
            if li.text == kind:
                li.click()
                break
            
    time.sleep(2)
    # traverse all child kinds of the expected kind
    original_window = driver.current_window_handle
    a_group = driver.find_elements_by_xpath("//*[@class='hmenu hmenu-visible hmenu-translateX']/li/a[@class='hmenu-item']")
    random.shuffle(a_group)
    for a in a_group:
        # get sub_kind of the expected kind and print its class_path
        child_kind = a.text
        tmp_node = re.search(r"%3A([0-9]+?)&ref",a.get_attribute("href"))
        print(cur_path, child_kind, a.get_attribute("href"))
        child_node = "n/" + tmp_node.group(1)
        if not child_kind:
            continue
        original_path = cur_path
        original_node = cur_node
        print(f"turn to {child_kind} / {child_node}...")
        cur_path += f"/{child_kind}"
        cur_node += f"/{child_node}"
        print(f"current path: {cur_path} / {cur_node}")
        # if cur_path not in finished_paths:
        if not db.getAll(f"PROGRESS-{collection}-{period}", filter = {'_id':cur_path,"page":"FINISHED"}):
        # jump to the sub_kind webpage
            # a = li.find_element_by_tag_name("a")
            link = a.get_attribute("href")
            driver.execute_script(f'window.open("{link}", "_blank");')

            # switch the target window of the driver and traverse all the sub_kinds
            driver.switch_to.window(driver.window_handles[-1])
            time.sleep(2)
            traverse_sub_kinds(driver, cur_path, cur_node)
            print(f"\nall sub-kinds of the {cur_path}/{cur_node} have been traversed\n")
            driver.close()
            # update_progress(cur_path, "FINISHED")
        # switch back and reset the class_path
        cur_path = original_path
        cur_node = original_node
        driver.switch_to.window(driver.window_handles[0]) ## original_window
if __name__ == '__main__':
    pre_kinds = {"Electronics", "Computers", "Smart Home", "Arts & Crafts"}
    db = DBMongo(database="control_db")
    collection = "asins_by_class"
    node_collection = "nodes"
    driver = start_chrome(PROXY = True)
    f = None
    # change the parameter as the expected kind
    period = "2308"
    categories = ["Home and Kitchen", "Automotive","Beauty and personal care","Pet supplies", "Sports and Outdoors", "Tools & Home Improvement", "Toys and Games", "Video Games"]
    # ["Luggage", "Industrial and Scientific", "Health and Household", "Baby", "Men's Fashion", "Women's Fashion", "Girls' Fashion", "Boys' Fashion", ]
    # ["Electronics", "Computers", "Smart Home", "Arts & Crafts"]
    categories_nodes = [
        ("Home and Kitchen", "1055398"),
        ("Automotive", "15684181"), 
        ("Baby", "165796011"),
        ("Beauty and personal care", "3760911"), 
        ("Health and Household", "3760901"),
        ("Industrial and Scientific", "16310091"), 
        ("Pet supplies", "2619533011"), 
        ("Sports and Outdoors", "3375251"),  
        ("Tools & Home Improvement", "228013"), 
        ("Toys and Games", "165793011"), 
        ("Video Games", "468642")
                        ]
    random.shuffle(categories_nodes)
    for category, node in categories_nodes:
        print(f"current category: {category}/{node}")
        # if db.getAll(f"PROGRESS-{collection}-{period}", filter={"_id":category,'page':"FINISHED"}, column={}):
        #     print(f"{category}: FINISHED")
        #     continue
        try:
            spider(driver, category, node)
        except Exception as e:
            print("RESTART!!")
            traceback.print_exc()
            print(e)
            time.sleep(5)
            try:
                driver.close()
            except:
                pass 
            driver = start_chrome()
        else:
            print(category, "FINISHED")
            # update_progress(category, "FINISHED")    