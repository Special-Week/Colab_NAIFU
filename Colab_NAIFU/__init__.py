import asyncio
from .utils import *
from io import BytesIO
from loguru import logger
from PIL import Image as IMG
from nonebot.typing import T_State
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Bot, PrivateMessageEvent,GroupMessageEvent, MessageSegment,MessageEvent,Message



# 换后端的url, 因为你的google colab每次启动的url不一样
@novelai_seturl.handle()
async def _(msg: Message = CommandArg()):
    url = msg.extract_plain_text()
    novelai_url.update({"url":url + "generate-stream"})
    await novelai_seturl.finish("设置成功, 当前url为: " + novelai_url["url"])


# 根据prompt生图的响应器
@novelai.handle()
async def _(bot:Bot,event: MessageEvent,state: T_State):

    global lastTime,cdTime      # 两个全局变量, 控制cd时间
    url = novelai_url["url"]    # 这个是请求的url(后端url)
    # 60s只能触发一次
    cd = event.time - lastTime
    if cd < cdTime:
        await novelai.finish(f"请求占用中，CD{cdTime - cd}s(公共CD)")
    else:
        lastTime = event.time


    # 获取参数
    args = list(state["_matched_groups"])
    key = args[1]
    size = ''
    # 正则表达式不熟连, 别骂
    if "size" in key:
        # 如果字符串里面有size这个参数, 把冒号的内容提出来
        index = key.find('size')
        size = key[index + 5:]
        key = key[:index]
    if size == "":
        size = "512x768"
    try:
        size = size.split("x")
        if len(size)!=2:
            size = [512,768]
    except:
        size = [512,768]
    size = [int(size[0]), int(size[1])]

    # size不能太大, 后端承受的住吗?
    if size[0] > 1024 or size[1] > 1024:
        lastTime -= cdTime
        await novelai.finish('图片尺寸异常,请重新输入(200--1024)')
    if size[0] < 200 or size[1] < 200:
        lastTime -= cdTime
        await novelai.finish('图片尺寸异常,请重新输入(200--1024)')
    # prompt不能为空
    if key == "" or key.isspace():
        lastTime -= cdTime
        await novelai.finish('键入prompt: [ai绘图|ai约稿|ai画图] + 关键词 + size:intxint')


    await novelai.send("ai绘制中，请稍等") 

    # 请求后端
    try:
        img_data = await down_pic(url,key,size)
    except:
        img_data = "fail"
    if img_data == "fail":
        lastTime -= cdTime
        await novelai.finish("后端请求失败")

    # 构造消息
    messages = f'prompt:{key}'+MessageSegment.image(img_data)
    # 私聊老样子, 直接发
    if isinstance(event, PrivateMessageEvent):
        message_id=await novelai.send(messages)
    # 群聊要转发
    elif isinstance(event, GroupMessageEvent):
        msg = to_json(messages, "ai-setu-bot", bot.self_id)
        message_id=await bot.call_api('send_group_forward_msg', group_id=event.group_id, messages=msg) 
    # sleep100s
    await asyncio.sleep(100)
    # 撤回消息
    del_id = message_id['message_id']
    await bot.delete_msg(message_id =del_id)



# 以图生图的handle
@img2img.handle()
async def _(bot:Bot,event: MessageEvent,msg: Message = CommandArg()):
    # 全局变量, cd用
    global lastTime,cdTime
    # 60s只能触发一次
    cd = event.time - lastTime
    if cd < cdTime:
        await novelai.finish(f"请求占用中，CD{cdTime - cd}s(公共CD)")
    else:
        lastTime = event.time
    # 获取命令参数
    prompt = msg.extract_plain_text()
    # 尝试那到图片url, 其实有更好的方法, 但是我没写过, 懒得研究了
    try:
        img_url = str(msg)[str(msg).find('url=')+4:str(msg).find(']')]
    except:
        img_url = ""

    # 如果没有图片, 提示
    if prompt == "" or prompt.isspace():
        lastTime -= cdTime
        await img2img.finish("需要输入prompt")
    if img_url == "" or img_url.isspace():
        lastTime -= cdTime
        await img2img.finish("需要输入图片")
    try:
        # 下载请求的图片
        async with AsyncClient() as client:
            re = await client.get(img_url)
            if re.status_code == 200:
                image = IMG.open(BytesIO(re.content))
            else:
                lastTime -= cdTime
                await img2img.finish("图片下载失败...")
    except:
        lastTime -= cdTime
        await img2img.finish("图片下载失败...")
    # git不支持
    is_gif = getattr(image, "is_animated", False)
    if is_gif:
        lastTime -= cdTime
        await img2img.finish("不支持gif图片")

    # 传给后端的图片分辨率不是512x768的话, 不知道为什么后端会报错张量维度相关的错误
    # 所以这里强制拉伸一下
    image = image.resize((512,768),IMG.ANTIALIAS)
    # 转成byte
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    # 转成base64字符串, 准备用来请求后端
    b64_encode = base64.b64encode(img_byte_arr).decode()

    await img2img.send("ai绘制中，请稍等")
    # 请求后端
    try:
        img_data = await down_img2img(novelai_url["url"],prompt,image.size,b64_encode)
    except:
        img_data = "fail"
    if img_data == "fail":
        lastTime -= cdTime
        await novelai.finish("后端请求失败")
    # 构造消息
    messages = f'img2img\nprompt:{prompt}'+MessageSegment.image(img_data)
    if isinstance(event, PrivateMessageEvent):
        await novelai.send(messages)
    elif isinstance(event, GroupMessageEvent):
        msg = to_json(messages, "ai-setu-bot", bot.self_id)
        await bot.call_api('send_group_forward_msg', group_id=event.group_id, messages=msg) 
    
    # 这里我就不设定撤回了

