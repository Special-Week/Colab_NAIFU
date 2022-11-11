import base64
import random
from typing import Union, List
try:
    import ujson as json
except ModuleNotFoundError:
    import json
from re import I
from httpx import AsyncClient
from nonebot.permission import SUPERUSER
from nonebot import on_regex, on_command
from io import BytesIO
from PIL import Image as IMG
from nonebot.adapters.onebot.v11 import MessageEvent, Message
from nonebot.typing import T_State
from nonebot.params import Arg, Depends


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
appreciate_img = on_command("图片鉴赏", aliases={"图片分析"}, priority=10, block=True)


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
        try:
            re = await client.post(url=url, timeout=120, json=data, headers=header)
        except:
            return "fail"
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
        try:
            re = await client.post(url=url, timeout=120, json=data, headers=header)
        except:
            return "fail"
        if re.status_code != 200:
            return "fail"
        re = re.text
        index = re.find('data:')
        img_data = base64.b64decode(re[index+5:])
    return img_data

# 提供给鉴赏功能的函数
async def down_appreciate(url) -> str:
    # 下载请求的图片
    async with AsyncClient() as client:
        re = await client.get(url)
        if re.status_code == 200:
            image = IMG.open(BytesIO(re.content)).convert('RGB')
        else:
            await appreciate_img.finish("图片下载失败...")
    image.save(imageData := BytesIO(), format="jpeg")
    img_b64 = base64.b64encode(imageData.getvalue()).decode()
    data = {
        'fn_index': 0,
        "data": [f"data:image/jpeg;base64,{img_b64}", 0.5],
    }
    # 发送请求
    url_push = "https://hysts-deepdanbooru.hf.space/api/predict"
    async with AsyncClient() as client:
        r = await client.post(url=url_push, json=data)
        result = r.json()["data"][0]["confidences"]
        msg = ", ".join(i["label"]
                        for i in result if not i["label"].startswith("rating:"))
    return msg

# 提供给鉴赏功能的函数
def parse_image(key: str):
    async def _key_parser(state: T_State, img: Message = Arg(key)):
        if not get_message_img(img):
            await appreciate_img.finish("格式错误，鉴赏取消...")
        state[key] = img
    return _key_parser

# 鉴赏功能handle
@appreciate_img.handle()
async def _(event: MessageEvent, state: T_State):
    if event.reply:
        state["img"] = event.reply.message
    if get_message_img(event.json()):
        state["img"] = event.message

# 工具函数, 获取消息中所有的图片的链接
def get_message_img(data: Union[str, Message]) -> List[str]:
    img_list = []
    if isinstance(data, str):
        data = json.loads(data)
        for msg in data["message"]:
            if msg["type"] == "image":
                img_list.append(msg["data"]["url"])
    else:
        for seg in data["image"]:
            img_list.append(seg.data["url"])
    return img_list

# got
@appreciate_img.got(
    "img", prompt="请发送需要处理的图片...", parameterless=[Depends(parse_image("img"))]
)
async def _(img: Message = Arg("img")):
    img_url = get_message_img(img)[0]
    msg = await down_appreciate(url=img_url)
    await appreciate_img.finish(f"得出图片的prompt为:\n{msg}", at_sender=True)

# 记录最后一次发出的时间
lastTime: str = ''
# 是否正在执行
isRunning: bool = False
# 后端的url, 至于为什么要用dict, 我当初忘记了, 我也懒得改了
novelai_url = {'url': ''}
