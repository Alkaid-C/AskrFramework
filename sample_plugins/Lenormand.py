"""
调用Claude API，进行每日雷诺曼牌阵占卜
"""


import datetime
import random
import anthropic
API_KEY="****" #在此处输入你的真实API Key

MANIFEST = {
    "MESSAGE_GROUP": "Lenormand"
}

def Lenormand(simpleEvent, rawEvent):
    date_str = datetime.datetime.now(userZone).strftime("%Y年%m月%d日")
    nickname=rawEvent.get("sender").get("nickname")
    cards=three_card(simpleEvent["user_id"])
    if simpleEvent["text_message"]=="/今日牌阵（解读）":
        AI_response=AI_divination(f"{nickname}抽到的今日（{date_str}）牌阵：{cards}\n请解读今日牌阵。")
        return AI_response
    elif simpleEvent["text_message"]=="/今日牌阵":
        return f"贵安。{nickname}的今日（{date_str}）牌阵为：\n {cards}。"


def AI_divination(message: str) -> str:
    #调用AI进行解读
    system_prompt = """你是一个专业的雷诺曼占卜 AI，专注于每日三牌阵（Three-Card Spread）的解读。你不扮演通灵者，也不声称能预知命运，而是通过符号学、心理启示和雷诺曼卡牌的传统象征意义，提供启发性的分析与建议。
你的工作方式如下：

每次占卜都包含三张卡牌。

你需要解释每张牌的基本含义，以及它在牌阵中的位置所扮演的角色（例如：过去、现在、未来，或情境、行动、结果）。

分析卡牌之间的联系与组合意义，而非孤立解读。

在可能的情况下，提出温和而务实的生活建议，但不要使用绝对化语句（例如“你一定会成功”），而应使用启发式语气（如“这可能暗示…”、“你可以考虑…”）。

解读应控制在不超过 300 字，语言清晰、富有象征性和启发性。

你必须遵守以下限制：

 - 不涉及健康诊断、法律决策或金融投资建议。
 - 不鼓励迷信，也不应暗示用户“命运已定”。
 
示例输入格式：

用户将输入三张牌，例如：骑士、棺材 / Coffin、Heart

你应回应：骑士象征消息或新动态，出现在首位，可能表示你最近收到或即将收到重要信息。棺材在中间位置，暗示当前正处于一个结束或转换期，可能与旧关系、计划或情绪有关。心位于结尾，带来积极能量，暗示未来将有情感上的恢复、连接或喜悦。整体来看，这是一个“从变动中走向内心和感情恢复”的过程。你可以留意那些在动荡后给予你安慰的人与事。

你始终以理解象征、启发内心、照见日常为使命。
"""
    
    client = anthropic.Anthropic(api_key=API_KEY)
    
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        temperature=1,
        top_p=0.9,
        system=system_prompt,
        messages=[{"role": "user", "content": message}]
    )
    
    return response.content[0].text
 
def three_card(userId):
    #抽牌函数
    
    current_date = datetime.datetime.now()
    date_salt = current_date.year * 10000 + current_date.month * 100 + current_date.day
    card_seed=hash(userId+date_salt) #以日期和QQ号作为随机数种子，确保每日的牌阵不变
    
    random.seed(seed)
    
    # 定义雷诺曼牌组（36张牌）
    lenormand_deck=["骑士(Rider)","三叶草(Clover)","船(Ship)","房子(House)","树(Tree)","云(Clouds)","蛇(Snake)","棺材(Coffin)","花束(Bouquet)","镰刀(Scythe)","鞭子(Whip)","鸟(Birds)","孩子(Child)","狐狸(Fox)","熊(Bear)","星星(Star)","鹳(Stork)","狗(Dog)","塔(Tower)","花园(Garden)","山(Mountain)","十字路口(Crossroads)","老鼠(Mice)","心(Heart)","戒指(Ring)","书(Book)","信(Letter)","男人(Man)","女人(Woman)","百合(Lily)","太阳(Sun)","月亮(Moon)","钥匙(Key)","鱼(Fish)","锚(Anchor)","十字架(Cross)"]

#洗牌
    random.shuffle(lenormand_deck)

#抽取三张牌
    cards_drawn=lenormand_deck[:3]

#返回结果作为字符串
    result_string=f"{cards_drawn[0]}、{cards_drawn[1]}、{cards_drawn[2]}"
    return result_string

