import base64
import random
from re import I
from httpx import AsyncClient
from nonebot.permission import SUPERUSER
from nonebot import on_regex, on_command


# 这里是响应器
novelai = on_regex(
    r"^(ai绘图|ai约稿|ai画图)\s?(.*)?",
    flags=I,
    priority=10,
    block=True
)
img2img = on_command(
    "以图画图", aliases={"以图生图", "imgtoimg", "img2img"}, priority=5, block=True)
naifu_url = on_command("set_naifu", priority=10,
                       block=True, permission=SUPERUSER)
reverse_isRunning = on_command(
    "重置ai绘图", priority=10, block=True, permission=SUPERUSER)


# 转发消息用的函数
def to_json(msg, name: str, uin: str):
    return {
        'type': 'node',
        'data': {
            'name': name,
            'uin': uin,
            'content': msg
        }
    }


# 请求图片, 参数: url(后端的url), key(prompt), size(图像大小)
async def down_pic(url, key, size):
    data = {
        "prompt": "masterpiece, best quality" + str(key),
        "width": size[0],
        "height": size[1],
        "scale": 12,
        "sampler": "k_euler_ancestral",
        "steps": 28,
        "seed": random.randint(0, 2**32),
        "n_samples": 1,
        "ucPreset": 0,
        "uc": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet"
    }
    header = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.42',

    }
    async with AsyncClient() as client:
        re = await client.post(url=url, timeout=120, json=data, headers=header)
        if re.status_code != 200:
            return "fail"
        re = re.text
        index = re.find('data:')
        img_data = base64.b64decode(re[index+5:])
    return img_data


# 以图生图的请求图片函数, 参数: url(后端的url), key(prompt), size(图像大小), img(发出请求图片的base64编码)
# 这里可以复用代码的, 但是我懒得改了
async def down_img2img(url, key, size, img):
    data = {
        "prompt": "masterpiece, best quality," + str(key),
        "width": size[0],
        "height": size[1],
        "scale": 12,
        "sampler": "k_euler_ancestral",
        "steps": 28,
        "seed": random.randint(0, 2**32),
        "n_samples": 1,
        "strength": 0.7,
        "noise": 0.2,
        "ucPreset": 0,
        "image": img,
        "uc": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet"
    }
    header = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.42',

    }
    async with AsyncClient() as client:
        re = await client.post(url=url, timeout=120, json=data, headers=header)
        if re.status_code != 200:
            return "fail"
        re = re.text
        index = re.find('data:')
        img_data = base64.b64decode(re[index+5:])
    return img_data


# 记录最后一次发出的时间
lastTime: str = ''
# 是否正在执行
isRunning: bool = False
# 后端的url, 至于为什么要用dict, 我当初忘记了, 我也懒得改了
novelai_url = {'url': ''}
