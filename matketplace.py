import os
import platform
import re
import time
from datetime import datetime
import config as config
import pymysql
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

CHROMEDRIVER_PATH = os.path.join(
    os.path.dirname(__file__),
    f"../chromedriver/{platform.system().lower()}/chromedriver"
)


class DBHandler:
    DB_CONN = None

    def __init__(self):

        self.DB_HOST = config.DB_CONFIG["host"]
        self.DB_USER = config.DB_CONFIG["user"]
        self.DB_PW = config.DB_CONFIG["pw"]
        self.DB_NAME = config.DB_CONFIG["name"]

    def openConnection(self):

        self.DB_CONN = pymysql.connect(self.DB_HOST, self.DB_USER, self.DB_PW, self.DB_NAME, autocommit=True)

    def closeConnection(self):
        self.DB_CONN.close()

    def executeSQL(self, sql, args=None):
        self.openConnection()
        with self.DB_CONN.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, args)
            queryResult = cursor
        self.closeConnection()
        return queryResult

    def check_if_postingid_exists(self, postingid):
        sql = f"SELECT COUNT(*) FROM cars  WHERE posting_id='{postingid}'"
        res = self.executeSQL(sql).fetchone()['COUNT(*)']
        if res == 0:
            return False
        else:
            return True

    def insert_new_car(self, data):
        sql = f"""INSERT INTO cars(created_at, source, offer_timestamp, type, price,
                    make, vin, car_condition, paint_color, image, size, odometer, year, ad_title,
                    posting_id, transmission, model, fuel, drive, url, cylinders) VALUES(
                    '{datetime.now()}','{"FB Marketplace"}','{None}',
                    '{None}','{data["price"]}','{data["make"]}',
                    '{data["vin"]}','{data["car_condition"]}','{data["paint_color"]}',
                    '{data["image"]}','{None}', '{data["odometer"]}',
                    '{data["year"]}','{data["ad_title"]}', '{data["posting_id"]}',
                    '{data["transmission"]}', '{data["model"]}','{data["fuel"]}',
                    '{data["drive"]}','{data["url"]}','{data["cylinders"]}');"""

        if not self.check_if_postingid_exists(data["posting_id"]):
            self.executeSQL(sql)
            print(data["posting_id"] + " inserted!")
        else:
            print(data["posting_id"] + ' already in db')
        return

    def get_all_data(self):
        sql = "SELECT * FROM cars"
        return self.executeSQL(sql).fetchall()


class Item:
    driver = None

    def __init__(self):
        options = webdriver.ChromeOptions()
        # print("Connecting existing Chrome for debugging...")
        # options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        print("Turning off images to save bandwidth")
        options.add_argument("--blink-settings=imagesEnabled=false")
        print("Making chrome headless")
        options.add_argument("--headless")
        options.add_argument("--window-size=1920x1080")
        print("Launching Chrome...")
        self.driver = webdriver.Chrome(options=options)
        # driver.maximize_window()

    def getItem(self, url):
        self.driver.get("view-source:" + url)
        content = BeautifulSoup(self.driver.page_source, 'lxml').text
        dictionary = {
            "price": self.get('price', content),
            "make": self.get('vehicle_make_display_name', content),
            "vin": self.get('vehicle_identification_number', content),
            "car_condition": self.get('condition', content),
            "paint_color": self.get('vehicle_exterior_color', content),
            "image": self.get('image', content).replace('\\', ''),
            "odometer": self.get("vehicle_odometer_data", content),
            "year": self.get('marketplace_listing_title', content)[:4],
            "ad_title": self.get('marketplace_listing_title', content),
            "posting_id": self.get("post_id", content),
            "transmission": self.get("TRANSMISSION", content),
            "model": self.get('vehicle_model_display_name', content),
            "fuel": self.get('vehicle_fuel_type', content),
            "drive": self.get("DRIVETRAIN", content),
            "url": self.driver.current_url,
            "cylinders": self.get("Cyl", content) if self.isInt(self.get("Cyl", content)) else None
        }
        print(dictionary)
        handler = DBHandler()
        handler.insert_new_car(data=dictionary)

    def isInt(self, value):
        try:
            int(value)
            return True
        except:
            return False

    def get(self, attrib, content):
        if attrib == "post_id":
            result = re.search(attrib + '":"(.*?)"},', content)
            if result is not None:
                return result.group(0)[11:-3]
        elif attrib == "vehicle_odometer_data":
            result = re.search(attrib + '":{"unit":"MILES","value":(.*?)},"', content)
            if result is not None:
                return result.group(0)[47:-3]
        elif attrib == "TRANSMISSION":
            result = re.search('"CONVENIENCE","feature_type(.*)' + attrib, content)
            if result is not None:
                return result.group(0).split('{')[1].split('","')[0].split('":"')[1]
        elif attrib == "Cyl":
            if content.__contains__("-Cyl"):
                return content[content.find("-Cyl") - 1:content.find("-Cyl")]
        elif attrib == "DRIVETRAIN":
            if content.__contains__("DRIVETRAIN"):
                return content[content.find("DRIVETRAIN") - 30:content.find("DRIVETRAIN")].split(":")[1].split(",")[
                    0].replace('"', '')
        else:
            result = re.search(attrib + '":"(.*?)","', content)
            if result is not None:
                return result.group(0)[len(attrib) + 3:-3]
        return None


class Marketplace:
    def __init__(self):
        options = webdriver.ChromeOptions()
        print("Connecting existing Chrome for debugging...")
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        print("Turning off images to save bandwidth")
        options.add_argument("--blink-settings=imagesEnabled=false")
        # print("Making chrome headless")
        # options.add_argument("--headless")
        # options.add_argument("--window-size=1920x1080")
        print("Launching Chrome...")
        driver = webdriver.Chrome(options=options)
        url = "https://www.facebook.com/marketplace/seattle/cars"
        print("Opening marketplace URL: " + url)
        driver.get(url)
        print("Setting filters: Seattle, WA - within 100 mi")
        try:
            driver.find_element_by_xpath()
        except:
            pass
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "seo_filters"))).find_element_by_css_selector('div').click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[text()='Radius']"))).find_element_by_xpath('..').click()
        for item in WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[role='menuitemradio']"))):
            if item.text == "100 miles":
                item.click()
                break
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//span[text()='Apply']"))).find_element_by_xpath('..').click()
        print("Filters done, now working on item listings...")
        element = driver.find_element_by_xpath(
            "//div[@id='seo_pivots']/following-sibling::div/following-sibling::div/following-sibling::div"). \
            find_element_by_css_selector(
            "div")
        hrefs = [x.get_attribute('href') for x in element.find_elements_by_css_selector('a')]
        print(hrefs)
        item = Item()
        for href in hrefs:
            item.getItem(href)


m = Marketplace()
