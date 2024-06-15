import requests
import json
import re
from datetime import datetime

# 从文件中读取JSON数据
with open('docs/paper_list.json', 'r') as f:
    data = json.load(f)

# 筛选条件
selected_classification = "Classification"
start_date = "2024-02-01"
end_date = "2024-02-28"

# 将日期字符串转换为日期对象
start_date = datetime.strptime(start_date, "%Y-%m-%d")
end_date = datetime.strptime(end_date, "%Y-%m-%d")

# 遍历json
for key, value in data[selected_classification].items():
    # 使用正则表达式提取日期和论文名称
    date_str, title = re.findall(r'\*\*(.+?)\*\*', value)[:2]

    # 将日期字符串转换为日期对象
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")

    # 检查日期是否在筛选范围内
    if start_date <= date_obj <= end_date:
        # 构造pdf下载链接
        url = f'http://arxiv.org/pdf/{key}.pdf'

        # 发送GET请求
        response = requests.get(url)

        # 检查响应状态码
        if response.status_code == 200:
            # 使用论文名称作为文件名，并替换不允许的字符
            filename = f'{title.replace(" ", "_").replace(":", "").replace("?", "")}.pdf'

            # 打开一个pdf文件，写入获取的内容
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f'Successfully downloaded {filename}')
        else:
            print(f'Failed to download {title}.pdf')