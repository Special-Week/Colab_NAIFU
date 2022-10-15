# 使用Google Colab搭建NAIFU后端
搭建成功一次大概能用三小时左右
Google每天都可以白嫖
链接: https://colab.research.google.com/drive/1_Ma71L6uGbtt6UQyA3FjqW2lcZ5Bjck-
科学上网是必备的
搭建后端步骤:
    1.登录你的Google账号
    2.依次运行笔记中的0 1 2步, 第三第四步选一个即可(大概十分钟)
    3.注意控制台会给你一个url
        Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):
        下面的就是你的url, 这是你的前端
    4.url出来后需要等待一些时间让他完全部署好, 用自己的浏览器测试这个前端有没有用

插件使用说明:
    1.bot刚开始启动url为空的, 所以要用第一步需要set_novelai_url
    2.假设刚刚搭建的前端你的url为 "https://myanmaar-flush-alfred-aan.trycloudflare.com", 
    3.给bot发送set_novelai_urlhttps://myanmaar-flush-alfred-aan.trycloudflare.com/(注意最后面的斜杠是必须的, 响应器用的是on_command, 如果设置了command_start,记得加上你的前缀)
    4.prompt生图的命令示例: ai绘图 loli,white hair,white legwear                                 (具体看源码)
    5.prompt生图需要设置图像大小的命令示例: ai绘图 loli,white hair,white legwear size:114x514     (具体看源码)
    6.以图生图的命令示例: img2img a girl in suit 孙笑川.jpg        (具体看源码)
    7.negative prompt已经在源码内填写了, 内容为"lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet"

        
注意:
    1.后端搭建好的前面十几分钟bot经常post不到后端, 以我用了两三天的经验, 十几分钟后就开始很稳定了
    2.colab这两天每天给我的GPU只有三,四小时左右, 你可以考虑多注册几个google账号, 这个每天会刷新的
    3.浏览器不要关掉, 关掉后过几分钟Google会close掉你的后端
    4.目前没设置任何r18限制, 因为感觉很难设置, 关键词不仅只有nsfw这一个, 自然语言也可以prompt出r18, 需要限制的请自己想
    5.嫌麻烦的可以找菩萨用他们的后端, 或者氪25美刀去官网, nonebot2商店有相关插件
    6.源码注释以补, 有问题可以看看(有问题自己想)