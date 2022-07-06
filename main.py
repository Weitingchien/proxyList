import os
import time
import random
import pymysql
import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fake_useragent import UserAgent
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

# DB(MySQL) configuration
dbConfig = {
    "host": os.getenv("HOST"),
    "port": int(os.getenv("PORT")),
    "user": os.getenv("USER"),
    "password": os.getenv("DBPWD"),
    "db": os.getenv("DB"),
    "charset": "utf8"
}


validIps = []

userAgent = UserAgent()


async def sslProxies():
    headers = {
        "user-agent": userAgent.random
    }
    print(headers["user-agent"])
    time.sleep(random.uniform(5, 10))
    ips = []
    if(len(validIps)):
        validIps.clear()
    r = requests.get("https://www.sslproxies.org/", headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    allTr = soup.find(
        "table", class_="table-striped").find("tbody").find_all("tr")
    for index, tr in enumerate(allTr):
        if index <= 45:
            allTd = tr.find_all("td")
            ip = allTd[0].text
            port = allTd[1].text
            code = allTd[2].text
            country = allTd[3].text
            anonymity = allTd[4].text
            https = "https" if allTd[6].text == "yes" else "http"
            lastChecked = allTd[7].text
            proxyInfo = {
                "proxy": f"{https}://{ip}:{port}",
                "ip": ip,
                "ipAndPort": f"{ip}:{port}",
                "port": port,
                "code": code,
                "country": country,
                "anonymity": anonymity,
                "https": https,
                "lastChecked": lastChecked
            }
            ips.append(f"http://{proxyInfo['ipAndPort']}")
    print(f"尚未驗證的IP清單: {ips} 數量: {len(ips)}")

    timeout = aiohttp.ClientTimeout(total=4)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [asyncio.create_task(
            proxyCheckAvailable(ip, session))for ip in ips]
        results = await asyncio.gather(*tasks)
        for i in results:
            print(i)
        try:
            # Create connection object
            db = pymysql.connect(**dbConfig)
            # Create cursor object
            cursor = db.cursor()
            sqlIps = "SELECT COUNT(ip) FROM ips"
            cursor.execute(sqlIps)
            total = cursor.fetchall()
            print(f"total:{total}")
            if total[0][0] >= 10:
                print("筆數超過10筆準備刪除ips內所有資料")
                cursor.execute("TRUNCATE TABLE ips")
            sql = "REPLACE INTO ips (id, ip) VALUES(%s, %s)"
            for ip in range(len(validIps)):
                cursor.execute(sql, (ip, validIps[ip]))
            db.commit()
        except Exception as e:
            db.rollback()
            print(e)
            print("IP already exists")

        db.close()


async def proxyCheckAvailable(proxy, session):
    try:
        async with session.get("https://ip.seeip.org/jsonip?", proxy=proxy) as response:
            if response.status == 200:
                print(f"狀態碼{response.status}")
                text = await response.text()
                validIps.append(proxy)
                return response.status
            return response.status
    except:
        return "invalid"

"""
def getProxyIP():
    fetchIps = []
    try:
        db = pymysql.connect(**dbConfig)
        cursor = db.cursor()
        sql = "SELECT ip FROM ips"
        cursor.execute(sql)
        results = cursor.fetchall()
        print(results)
        for row in results:
            fetchIps.append(row)
        print(len(fetchIps))
        print(fetchIps)
    except:
        print("Can't fetch data")
    db.close()
    for ip in range(len(fetchIps)):
        print(fetchIps[ip][0])
    
"""


if __name__ == "__main__":
    #startTime = time.time()

    #loop = asyncio.get_event_loop()
    # loop.run_until_complete(sslProxies())

    scheduler = AsyncIOScheduler(timezone="Asia/Taipei")
    scheduler.add_job(sslProxies, "interval",
                      seconds=random.uniform(15, 20))
    scheduler.start()
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass


"""
# test connection
db = pymysql.connect(**dbConfig)

cursor = db.cursor()

sql = 'SELECT VERSION()'

cursor.execute(sql)

data = cursor.fetchone()

print(data)

db.close()
"""
