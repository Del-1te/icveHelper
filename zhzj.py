import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
import urllib.parse
import requests
from datetime import date
import re
from tqdm import tqdm
import sys
import os

baseurl = 'https://zjy2.icve.com.cn/prod-api/spoc/'

session = requests.session()

au = ''

year = str(date.today().year)
flag = 0
filename = 'token'

def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Authorization': au
    }

def is_token():
    global au
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            au = f.read().strip()
            print("本地已存在Token")
    else:
        print("本地未找到Token")
        au = input("请输入Token(获取Token方法详见图片):").strip()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(au)


def get_classList():
    global flag
    url = baseurl + f"courseInfoStudent/myCourseList?pageNum=1&pageSize=1000&isCriteria=1"
    res = session.get(url, headers=get_headers())
    data = res.json()

    while data['code'] != 200:
        print('Token已失效,请重新获取')
        if os.path.exists(filename):
            os.remove(filename)
        is_token()
        res = session.get(url, headers=get_headers())
        data = res.json()

    courseName = []
    datalist = data["rows"]
    for data in datalist:
        time = data["termCode"][:4]
        if time != year:
            break
        courseName.append(data["courseName"])

    if flag == 0:
        print("本学期的课程有:\n")
        for i, v in enumerate(courseName):
            print(f"{i + 1}. {v}")
        flag = 1

    res_id = input("\n请输入需要提交课程的id(输入q退出):")
    if res_id.lower() == 'q':
        print("已退出程序")
        sys.exit()

    courseId = datalist[int(res_id) - 1]["courseId"]
    courseInfoId = datalist[int(res_id) - 1]["courseInfoId"]
    classId = datalist[int(res_id) - 1]["classId"]
    print("正在获取课程内容........")
    return courseId, courseInfoId, classId


def is_file(name):
    return re.search(r"\.([a-zA-Z0-9]{2,5})$", name) is not None


def get_project(courseId, courseInfoId, classId, parent_id=0, level=1):
    url = baseurl + f"courseDesign/study/record?courseId={courseId}&courseInfoId={courseInfoId}&parentId={parent_id}&level={level}&classId={classId}"
    res = session.get(url, headers=get_headers())
    data = res.json()
    if not data:
        return []

    collected_ids = []

    for item in data:
        item_id = item.get("id")
        name = item.get("name", "")

        if is_file(name):
            collected_ids.append(item_id)
        else:
            sub_ids = get_project(courseId, courseInfoId, classId, parent_id=item_id, level=level + 1)
            if not sub_ids:
                collected_ids.append(item_id)
            else:
                collected_ids.extend(sub_ids)

    return collected_ids


def get_param(t, data_str):
    md5_hash = hashlib.md5(t.encode()).hexdigest()
    r = md5_hash[:16]
    # JSON 转字符串，再转字节
    data_bytes = data_str.encode('utf-8')

    # 密钥转字节
    key = r.encode('utf-8')

    # 使用 ECB 模式 + PKCS7 填充
    cipher = AES.new(key, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(data_bytes, AES.block_size))

    # 转 Base64 字符串
    i = base64.b64encode(encrypted).decode('utf-8')

    encoded = urllib.parse.quote(i)
    if encoded.endswith('%3D%3D'):
        encoded = encoded[:-6] + '=='

    return encoded


def send_progress():
    courseId, courseInfoId, classId = get_classList()
    collected_ids = get_project(courseId, courseInfoId, classId)
    print("获取完成正在提交进度")

    if collected_ids:
        for id in tqdm(collected_ids, ncols=100, smoothing=0.1, desc="🔥 提交进度中..."):
            url = baseurl + "studyRecord/update"
            data_str = f'{{"courseInfoId":"{courseInfoId}","classId":"{classId}","studyTime":5,"sourceId":"{id}","totalNum":999,"actualNum":999,"lastNum":1}}'
            param = get_param(au, data_str)
            date = {
                "param": param
            }
            session.post(url, headers=get_headers(), json=date)

    else:
        print("暂无内容")


if __name__ == '__main__':
    is_token()
    while 1:
        send_progress()