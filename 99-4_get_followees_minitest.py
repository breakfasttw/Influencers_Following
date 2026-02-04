import instaloader
from dotenv import load_dotenv
import os

ACC= os.getenv("ACCOUNT2")
PWD = os.getenv("PWD2")

# 建立實例並登入
L = instaloader.Instaloader()
L.login(ACC, PWD) # 必須登入才能獲取追蹤列表

# 指定目標帳號 (追蹤人數務必小於50)
profile = instaloader.Profile.from_username(L.context, "tsaigray2018")

# 獲取追蹤列表 (followees)
print(f"{profile.username} 追蹤了以下帳號：")
for followee in profile.get_followees():
    print(followee.username)
