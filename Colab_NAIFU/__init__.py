import time
import asyncio
from .utils import *
from nonebot.adapters.onebot.v11 import Bot, PrivateMessageEvent, GroupMessageEvent, MessageSegment
from nonebot.params import CommandArg
size_list = [64, 128, 192, 256, 320, 384, 448, 512,
             576, 640, 704, 768, 832, 896, 960, 1024]


# 换后端的url, 因为你的google colab每次启动的url不一样
@naifu_url.handle()
async def _(msg: Message = CommandArg()):
    url = msg.extract_plain_text()
    novelai_url.update({"url": url + "generate-stream"})
    await naifu_url.finish("设置成功, 当前url为: " + novelai_url["url"])


# 根据prompt生图的响应器
@novelai.handle()
async def _(bot: Bot, event: MessageEvent, state: T_State):
    global isRunning, lastTime
    if isRunning:
        await novelai.finish(f"当前有任务正在进行, 上次运行时:  {lastTime}")
    isRunning = True
    lastTime = time.strftime("%H:%M:%S", time.localtime())
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
        if len(size) != 2:
            size = [512, 768]
    except:
        size = [512, 768]
    size = [int(size[0]), int(size[1])]

    # 如果size不在列表里面, 就用最接近的
    if size[0] not in size_list:
        size[0] = size_list[min(range(len(size_list)),
                                key=lambda i: abs(size_list[i] - size[0]))]
    if size[1] not in size_list:
        size[1] = size_list[min(range(len(size_list)),
                                key=lambda i: abs(size_list[i] - size[1]))]

    # prompt不能为空
    if key == "" or key.isspace():
        isRunning = False
        await novelai.finish('键入prompt: [ai绘图|ai约稿|ai画图] + 关键词 + size:intxint')
    await novelai.send("ai绘制中，请稍等")

    # 请求后端
    try:
        img_data = await down_pic(novelai_url["url"], key, size)
    except:
        img_data = "fail"
    if img_data == "fail":
        isRunning = False
        await novelai.finish("后端请求失败")

    # 构造消息
    messages = f'prompt:{key}'+MessageSegment.image(img_data)
    # 私聊直接发
    if isinstance(event, PrivateMessageEvent):
        message_id = await novelai.send(messages)
    # 群聊转发
    elif isinstance(event, GroupMessageEvent):
        msg = to_json(messages, "ai-setu-bot", bot.self_id)
        message_id = await bot.call_api('send_group_forward_msg', group_id=event.group_id, messages=msg)
    isRunning = False
    # sleep100s
    await asyncio.sleep(100)
    # 撤回消息
    del_id = message_id['message_id']
    await bot.delete_msg(message_id=del_id)


# 以图生图的handle
@img2img.handle()
async def _(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
    global isRunning, lastTime
    if isRunning:
        await img2img.finish(f"当前有任务正在进行, 上次运行时:  {lastTime}")
    isRunning = True
    lastTime = time.strftime("%H:%M:%S", time.localtime())
    # 获取命令参数
    prompt = msg.extract_plain_text()
    # 尝试那到图片url, 其实有更好的方法, 但是我没写过, 懒得研究了
    try:
        img_url = str(msg)[str(msg).find('url=')+4:str(msg).find(']')]
    except:
        img_url = ""

    # 如果没有图片, 提示
    if prompt == "" or prompt.isspace():
        isRunning = False
        await img2img.finish("需要输入prompt")
    if img_url == "" or img_url.isspace():
        isRunning = False
        await img2img.finish("需要输入图片")
    try:
        # 下载请求的图片
        async with AsyncClient() as client:
            re = await client.get(img_url)
            if re.status_code == 200:
                image = IMG.open(BytesIO(re.content))
            else:
                isRunning = False
                await img2img.finish("图片下载失败...")
    except:
        isRunning = False
        await img2img.finish("图片下载失败...")
    # git不支持
    is_gif = getattr(image, "is_animated", False)
    if is_gif:
        isRunning = False
        await img2img.finish("不支持gif图片")

    # 获取图片的size
    size = list(image.size)
    # 如果size不在列表里面, 就用最接近的
    if size[0] not in size_list:
        size[0] = size_list[min(range(len(size_list)),
                                key=lambda i: abs(size_list[i] - size[0]))]
    if size[1] not in size_list:
        size[1] = size_list[min(range(len(size_list)),
                                key=lambda i: abs(size_list[i] - size[1]))]

    # 所以这里强制拉伸一下
    image = image.resize((size[0], size[1]), IMG.ANTIALIAS)
    # 转成byte
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    # 转成base64字符串, 准备用来请求后端
    b64_encode = base64.b64encode(img_byte_arr).decode()

    await img2img.send("ai绘制中，请稍等")
    # 请求后端
    try:
        print("size: ", size)
        print("prompt: ", prompt)
        img_data = await down_img2img(novelai_url["url"], prompt, size, b64_encode)
    except:
        img_data = "fail"
    if img_data == "fail":
        isRunning = False
        await novelai.finish("后端请求失败")
    # 构造消息
    messages = f'img2img\nprompt:{prompt}'+MessageSegment.image(img_data)
    if isinstance(event, PrivateMessageEvent):
        await novelai.send(messages)
    elif isinstance(event, GroupMessageEvent):
        msg = to_json(messages, "ai-setu-bot", bot.self_id)
        await bot.call_api('send_group_forward_msg', group_id=event.group_id, messages=msg)
    isRunning = False


@reverse_isRunning.handle()
async def _():
    global isRunning
    if isRunning:
        isRunning = False
        await reverse_isRunning.finish("isRunning已重置为了False")
    else:
        await reverse_isRunning.finish("isRunning已经是False了")
