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
    # 全局变量
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
    if size[0] > 1024 or size[1] > 1024:
        # 等比例缩放, 把最大的边缩放到1024
        if size[0] > size[1]:
            size[1] = int(size[1] * 1024 / size[0])
            size[0] = 1024
        else:
            size[0] = int(size[0] * 1024 / size[1])
            size[1] = 1024

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


# 重写以图生图的handle
@img2img.handle()
async def _(event: MessageEvent, state: T_State):
    if event.reply:
        state["img"] = event.reply.message
    if get_message_img(event.json()):
        state["img"] = event.message
    state["prompt"] = event.get_plaintext()

def parse_img2img(key: str):
    async def _key_parser(state: T_State, img: Message = Arg(key)):
        if not get_message_img(img):
            await img2img.finish("格式错误，操作取消...")
        state[key] = img
    return _key_parser

@img2img.got(
    "img", prompt="请发送需要处理的图片...", parameterless=[Depends(parse_img2img("img"))]
)
async def _(bot: Bot, event: MessageEvent, img: Message = Arg("img"), prompt: str = Arg("prompt")):
    img_url = get_message_img(img)[0]   # 获取图片链接
    global isRunning, lastTime          # 全局变量
    if isRunning:
        await img2img.finish(f"当前有任务正在进行, 上次运行时:  {lastTime}")
    isRunning = True                    # 标记任务开始
    lastTime = time.strftime("%H:%M:%S", time.localtime())      # 记录时间
    prompt1 = prompt.strip()                                    # 可能会拿到的prompt
    prompt2 = event.get_message().extract_plain_text().strip()  # 可能会拿到的prompt
    # prompt1和prompt2都删掉the_matcher里面的内容
    for i in ["以图生图", "imgtoimg", "img2img", "以图画图"]:  # 因为拿到的message会包含命令头, 所以这里要删掉
        prompt1 = prompt1.replace(i, "")
        prompt2 = prompt2.replace(i, "")
    # 如果prompt1和prompt2都为空或者都是空格
    if (prompt1 == "" or prompt1.isspace()) and (prompt2 == "" or prompt2.isspace()):
        isRunning = False
        await img2img.finish('该功能需要提供prompt')
    # prompt是prompt1或者prompt2, 不为空的一个
    if prompt1 == "" or prompt1.isspace():
        prompt = prompt2
    else:
        prompt = prompt1
    
    # 图片url以及prompt全部到手, 开始处理

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
    if size[0] > 1024 or size[1] > 1024:
        # 等比例缩放, 把最大的边缩放到1024
        if size[0] > size[1]:
            size[1] = int(size[1] * 1024 / size[0])
            size[0] = 1024
        else:
            size[0] = int(size[0] * 1024 / size[1])
            size[1] = 1024
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
