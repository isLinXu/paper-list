import os
import json
import re
import requests
import logging
from datetime import datetime
from tqdm import tqdm


class ArxivPaperDownloader:
    def __init__(self, json_file, start_date, end_date):
        with open(json_file, 'r') as f:
            self.data = json.load(f)
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")

        # 设置日志记录器
        logging.basicConfig(filename='paper_downloader.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.getLogger().addHandler(logging.StreamHandler())

    def download_papers(self, selected_topic):
        if selected_topic not in self.data:
            logging.error(f"{selected_topic} not found in the JSON data.")
            return

        # 创建目录
        os.makedirs(selected_topic, exist_ok=True)

        # 遍历json
        for key, value in tqdm(self.data[selected_topic].items(), desc=f"Downloading {selected_topic} papers"):
            # 使用正则表达式提取日期和论文名称
            date_str, title = re.findall(r'\*\*(.+?)\*\*', value)[:2]

            # 将日期字符串转换为日期对象
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")

            # 检查日期是否在筛选范围内
            if self.start_date <= date_obj <= self.end_date:
                # 构造pdf下载链接
                url = f'http://arxiv.org/pdf/{key}.pdf'

                # 发送GET请求
                response = requests.get(url)

                # 检查响应状态码
                if response.status_code == 200:
                    # 使用论文名称作为文件名，并替换不允许的字符
                    filename = f'{title.replace(" ", "_").replace(":", "").replace("?", "")}.pdf'

                    # 在选定的分类目录中保存文件
                    filepath = os.path.join(selected_topic, filename)

                    # 打开一个pdf文件，写入获取的内容
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    logging.info(f'Successfully downloaded {filepath}')
                else:
                    logging.error(f'Failed to download {title}.pdf')


if __name__ == "__main__":
    # 初始化下载器
    downloader = ArxivPaperDownloader('docs/paper_list.json', '2024-02-01', '2024-06-13')

    # 下载指定分类的论文
    downloader.download_papers('Classification')
    downloader.download_papers('Object Detection')
    downloader.download_papers('Semantic Segmentation')
    downloader.download_papers('Object Tracking')
    downloader.download_papers('Action Recognition')
    downloader.download_papers('Pose Estimation')
    downloader.download_papers('Image Generation')
    downloader.download_papers('LLM')
    downloader.download_papers('Scene Understanding')
    downloader.download_papers('Depth Estimation')
    downloader.download_papers('Audio Processing')
    downloader.download_papers('Multimodal')
    downloader.download_papers('Reinforcement Learning')
    downloader.download_papers('Graph Neural Networks')

