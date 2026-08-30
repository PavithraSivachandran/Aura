"""Aura intelligence: facts, conversation, kids-safe learning, and tools."""

from __future__ import annotations

import ast
import datetime as dt
import math
import operator
import random
import re
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests

TZ = ZoneInfo("Asia/Kolkata")
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "AuraAssistant/1.0 (local educational companion)",
        "Accept": "application/json",
    }
)

KIDS_BLOCK = re.compile(
    r"\b(sex|sexy|porn|nude|naked|xxx|suicide|kill yourself|murder|rape|"
    r"drug|cocaine|heroin|weed|marijuana|alcohol|beer|wine|whisky|vodka|"
    r"gun|pistol|rifle|bomb|terror|blood and gore|nsfw)\b",
    re.I,
)

GREET_RE = re.compile(
    r"^\s*(hi|hello|hey|yo|hola|namaste|namaskar|good\s+(morning|afternoon|evening|night)|hiya|sup)\b",
    re.I,
)
THANKS_RE = re.compile(r"\b(thanks|thank you|thx|tysm|shukriya|dhanyavaad|dhanyavad)\b", re.I)
IDENTITY_RE = re.compile(
    r"\b(who are you|what(?:'s| is) your name|what are you|who made you|what can you do)\b",
    re.I,
)
TIME_RE = re.compile(r"\b(what(?:'s| is) the time|current time|time now|what time)\b", re.I)
DATE_RE = re.compile(r"\b(what(?:'s| is) (the )?(date|day)|today(?:'s)? date|what day)\b", re.I)
WEATHER_RE = re.compile(r"\b(weather|temperature|forecast|hot outside|will it rain)\b", re.I)
DEFINE_RE = re.compile(r"^\s*(define|definition of|what does .+ mean|meaning of)\b", re.I)
MATH_RE = re.compile(
    r"(?:^(?:what(?:'s| is)|calculate|compute|solve)\s+)?([0-9\.\s\+\-\*\/\^\(\)%x×÷sqrt]+)$",
    re.I,
)
CONVERT_RE = re.compile(
    r"\b(?:convert|how many)\s+([\d\.]+)\s*([a-z°]+)\s+(?:to|in|into)\s+([a-z°]+)\b",
    re.I,
)
CURRENCY_RE = re.compile(
    r"\b([\d,.]+)\s*(usd|inr|eur|gbp|dollars?|rupees?|rs\.?|₹|\$|€|£)\s+(?:to|in|into)\s*(usd|inr|eur|gbp|dollars?|rupees?|rs\.?|₹|\$|€|£)\b",
    re.I,
)
JOKE_RE = re.compile(r"\b(joke|make me laugh|funny)\b", re.I)
RIDDLE_RE = re.compile(r"\b(riddle)\b", re.I)
STORY_RE = re.compile(r"\b(story|bedtime|once upon)\b", re.I)
QUIZ_RE = re.compile(r"\b(quiz|trivia|question|test me|play a game|let'?s play)\b", re.I)
RHYME_RE = re.compile(r"\b(rhyme|nursery|poem|sing)\b", re.I)
HELP_RE = re.compile(r"^\s*(help|commands|what can you do)\s*[?.]?\s*$", re.I)

KIDS_WHY = {
    "sky blue": "Sunlight is made of many colours. Air molecules scatter the blue part the most, so the sky looks blue. At sunset the light travels farther and we see orange and pink instead!",
    "rainbow": "Raindrops act like tiny prisms. They bend sunlight and split it into red, orange, yellow, green, blue, indigo and violet. Stand with the sun behind you after rain and you might see one!",
    "thunder": "Lightning super-heats the air. The air expands in a boom — that's thunder. Light reaches you first, so you see the flash before you hear the rumble.",
    "rain": "The sun warms water. It turns into invisible vapour, rises, cools, and becomes clouds. When drops get heavy, they fall as rain. That's the water cycle!",
    "night": "Earth is a spinning ball. When your side turns away from the sun, it's night. The other side is having daytime. We spin once every 24 hours.",
    "moon": "The Moon is Earth's friend in space. It doesn't make its own light — it reflects the sun. It looks like it changes shape because we see different lit parts as it goes around us.",
    "stars twinkle": "Starlight wiggles through layers of moving air, like looking through wavy water. That's why stars twinkle. Planets usually shine steadier.",
    "ocean salty": "Rivers carry tiny bits of mineral salt from rocks into the sea. Water evaporates but salt stays, so oceans taste salty.",
    "leaves green": "Leaves have chlorophyll, a green helper that catches sunlight to make food. That's photosynthesis — plants eating sunshine!",
    "dinosaurs extinct": "A huge space rock hit Earth about 66 million years ago. Dust blocked sunlight, plants struggled, and many dinosaurs could not survive. Birds are their living relatives!",
    "heart beat": "Your heart is a strong pump. It squeezes to send blood — full of oxygen and snacks for your cells — all around your body. That's the beat you feel.",
    "yawn": "Scientists think yawning helps cool the brain and wake us up a little. It's also contagious because humans copy each other — even reading this might make you yawn!",
}

ANIMAL_FACTS = {
    "elephant": "Elephants are the largest land animals. They use their trunks like a hand, a straw, and a trumpet. They never forget their friends!",
    "tiger": "Tigers are big striped cats. Each tiger's stripes are unique, like a fingerprint. They love to swim!",
    "lion": "Lions live in family groups called prides. Male lions have fluffy manes. The lionesses do most of the hunting.",
    "giraffe": "Giraffes are the tallest animals. Their tongues can be 45 cm long and are often dark to protect from the sun.",
    "penguin": "Penguins are birds that cannot fly but are champion swimmers. Emperor penguins huddle together to stay warm in Antarctica.",
    "dolphin": "Dolphins are clever sea mammals. They talk with clicks and whistles and love to play. They breathe air like we do.",
    "dog": "Dogs have been human friends for thousands of years. They can learn hundreds of words and love to help and play.",
    "cat": "Cats sleep a lot — sometimes 16 hours a day! They purr when they feel safe, and their whiskers help them measure spaces.",
    "owl": "Owls can turn their heads almost all the way around. Soft feathers make their flight whisper-quiet for night hunting.",
    "butterfly": "Butterflies start as tiny eggs, become caterpillars, rest in a chrysalis, then unfold as flying rainbows. That's metamorphosis!",
    "whale": "Blue whales are the biggest animals that have ever lived — even bigger than dinosaurs. Their hearts are as large as a small car.",
    "bee": "Bees dance to tell friends where flowers are. They make honey and help plants grow by carrying pollen. Thank you, bees!",
    "peacock": "Peacocks are famous in India. The colourful train is used in a sparkling courtship dance. A group of peacocks is a party!",
    "cobra": "The Indian cobra can raise its hood when it feels scared. It is a snake we admire from a safe distance. In stories it is often wise.",
    "monkey": "Monkeys are playful and curious. Many use their tails for balance. They live in troops and groom each other to show friendship.",
}

PLANETS = {
    "mercury": "Mercury is the closest planet to the sun. Days are scorching and nights are freezing. It is a little grey rock world.",
    "venus": "Venus is the hottest planet because of a thick blanket of clouds. It spins the opposite way to Earth!",
    "earth": "Earth is our home. It has air, water, and life. It is the only planet we know with living things — so far!",
    "mars": "Mars is the rusty red planet. It has the tallest volcano in the solar system, Olympus Mons, and maybe had rivers long ago.",
    "jupiter": "Jupiter is the king of planets, a giant ball of gas with a huge storm called the Great Red Spot.",
    "saturn": "Saturn wears bright icy rings. It is a gas giant so light it could float in a giant bathtub — if one existed!",
    "uranus": "Uranus rolls on its side like a ball. It is a pale icy blue and very, very cold.",
    "neptune": "Neptune is a windy deep-blue world, the farthest planet from the sun. A year there lasts 165 Earth years.",
    "pluto": "Pluto is a dwarf planet far away. It has a heart-shaped glacier and a moon named Charon.",
}

KIDS_JOKES = [
    "Why did the banana go to the doctor? Because it wasn't peeling well!",
    "What do you call a bear with no teeth? A gummy bear!",
    "Why don't scientists trust atoms? Because they make up everything!",
    "What is a cat's favourite colour? Purr-ple!",
    "Why did the student eat his homework? Because the teacher said it was a piece of cake!",
    "How do you make a tissue dance? Put a little boogie in it!",
    "What do you call cheese that isn't yours? Nacho cheese!",
    "Why was the maths book sad? It had too many problems.",
    "What did the ocean say to the beach? Nothing, it just waved.",
    "Why did the bicycle fall over? Because it was two-tired!",
    "What do you call a sleeping bull? A bulldozer!",
    "Why can't your nose be 12 inches long? Because then it would be a foot!",
]

RIDDLES = [
    {"q": "I have hands but no arms, and a face but no eyes. What am I?", "a": "clock", "hint": "I help you know when it's lunchtime."},
    {"q": "I am full of keys but I cannot open a door. What am I?", "a": "piano", "hint": "I make music."},
    {"q": "The more you take, the more you leave behind. What am I?", "a": "footsteps", "hint": "Think about walking."},
    {"q": "What has a neck but no head?", "a": "bottle", "hint": "You might drink water from me."},
    {"q": "What can travel around the world while staying in a corner?", "a": "stamp", "hint": "Look at an envelope."},
    {"q": "What has to be broken before you can use it?", "a": "egg", "hint": "Breakfast!"},
    {"q": "I’m tall when I’m young and short when I’m old. What am I?", "a": "candle", "hint": "I make light and melt."},
    {"q": "What has words but never speaks?", "a": "book", "hint": "You turn my pages."},
]

QUIZZES = [
    {"q": "How many legs does a spider have?", "a": ["8", "eight"]},
    {"q": "What planet do we live on?", "a": ["earth"]},
    {"q": "What colour do you get when you mix blue and yellow?", "a": ["green"]},
    {"q": "How many days are in a week?", "a": ["7", "seven"]},
    {"q": "Which animal is called the King of the Jungle?", "a": ["lion"]},
    {"q": "What do bees make?", "a": ["honey"]},
    {"q": "How many continents are there?", "a": ["7", "seven"]},
    {"q": "What is the capital of India?", "a": ["new delhi", "delhi"]},
    {"q": "Which is the largest land animal?", "a": ["elephant"]},
    {"q": "What gas do we breathe in to live?", "a": ["oxygen"]},
    {"q": "How many colours are in a rainbow?", "a": ["7", "seven"]},
    {"q": "What do caterpillars turn into?", "a": ["butterfly", "butterflies", "moth"]},
]

RHYMES = [
    "Twinkle, twinkle, little star,\nHow I wonder what you are.\nUp above the world so high,\nLike a diamond in the sky.",
    "Rain, rain, go away,\nCome again another day.\nLittle children want to play,\nRain, rain, go away.",
    "The wheels on the bus go round and round,\nRound and round, round and round.\nThe wheels on the bus go round and round,\nAll through the town!",
    "Row, row, row your boat,\nGently down the stream.\nMerrily, merrily, merrily, merrily,\nLife is but a dream.",
]

SIMPLE_WORDS = {
    "approximately": "about",
    "subsequently": "later",
    "therefore": "so",
    "however": "but",
    "utilize": "use",
    "commonly": "often",
    "significant": "big",
    "inhabitants": "people who live there",
    "established": "started",
    "renowned": "famous",
    "located": "found",
    "constructed": "built",
    "primarily": "mainly",
}


def pack(text: str, meta: dict | None = None, suggestions: list[str] | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {"text": text.strip(), "meta": meta or {}}
    if suggestions:
        data["meta"]["suggestions"] = suggestions
    return data


def generate(
    message: str,
    history: list[dict[str, Any]] | None = None,
    kids_mode: bool = False,
    user_name: str = "",
    location: str = "Jaipur",
) -> dict[str, Any]:
    history = history or []
    text = (message or "").strip()
    name = (user_name or "").strip() or ("friend" if kids_mode else "there")
    if not text:
        return pack("I didn't catch that. Type a question or tap the mic.")

    if kids_mode:
        blocked = _kids_block_message(text, name)
        if blocked:
            return blocked
        quiz = _pending_quiz(history)
        if quiz:
            return _grade_quiz(text, quiz, name)
        riddle = _pending_riddle(history)
        if riddle:
            return _grade_riddle(text, riddle, name)

    low = text.lower().strip()

    if HELP_RE.search(low) or low in {"menu", "options"}:
        return _help(kids_mode, name)
    if GREET_RE.search(low) or low in {"hi", "hello", "hey", "namaste"}:
        return _greet(kids_mode, name)
    if THANKS_RE.search(low):
        return pack(
            f"You're welcome, {name}! "
            + ("Want another story or a quiz?" if kids_mode else "What should we tackle next?"),
            suggestions=["Tell me a story", "Quiz time"] if kids_mode else ["Weather", "Today's date"],
        )
    if IDENTITY_RE.search(low):
        return _identity(kids_mode, name)
    if TIME_RE.search(low):
        return _time(kids_mode)
    if DATE_RE.search(low):
        return _date(kids_mode)
    if WEATHER_RE.search(low):
        city = _extract_city(text, location)
        return _weather(city, kids_mode)
    if CURRENCY_RE.search(low):
        return _currency(text, kids_mode)
    if CONVERT_RE.search(low):
        return _convert(text, kids_mode)

    math_hit = _try_math(text)
    if math_hit:
        return pack(math_hit)

    if DEFINE_RE.search(low) or low.startswith("what is a ") or low.startswith("what is an "):
        defined = _define(text, kids_mode)
        if defined:
            return defined

    if kids_mode:
        kid = _kids_intents(text, name)
        if kid:
            return kid

    if JOKE_RE.search(low):
        return pack(random.choice(KIDS_JOKES) if kids_mode else _adult_joke())

    lookup = _knowledge(text, kids_mode, name)
    if lookup:
        return lookup

    more = _tell_more(text, history, kids_mode)
    if more:
        return more

    creative = _maybe_creative(text, kids_mode, name)
    if creative:
        return creative

    return _fallback(text, kids_mode, name)


def _help(kids: bool, name: str) -> dict[str, Any]:
    if kids:
        return pack(
            f"Hi {name}! I am Spark's friend Aura. We can:\n\n"
            "• Read a story\n• Tell animal & space facts\n• Play a quiz or riddle\n"
            "• Share a joke or rhyme\n• Explain why the sky is blue\n• Check the weather\n\n"
            "Tap a button below or just talk to me!",
            suggestions=["Tell me a story", "Animal facts", "Quiz time", "Why is the sky blue?"],
        )
    return pack(
        "I'm **Aura**, your workspace companion. I can help with:\n\n"
        "• Facts on people, places, science, history (live knowledge)\n"
        "• Weather and local time (IST)\n"
        "• Maths, unit and currency conversion\n"
        "• Definitions\n"
        "• Voice notes and talk mode\n"
        "• A separate **Kids Mode** with stories, quizzes and a parent lock\n\n"
        "Ask naturally — for example, *Who is the Prime Minister of India?* or *Weather in Jaipur*.",
        suggestions=["Weather in Jaipur", "Define serendipity", "Convert 10 km to miles"],
    )


def _greet(kids: bool, name: str) -> dict[str, Any]:
    now = dt.datetime.now(TZ)
    hour = now.hour
    if hour < 12:
        part = "Good morning"
    elif hour < 17:
        part = "Good afternoon"
    else:
        part = "Good evening"
    if kids:
        return pack(
            f"{part}, {name}! Spark and I are ready to play and learn. What sounds fun?",
            suggestions=["Tell me a story", "A silly joke", "Quiz time", "Space facts"],
        )
    return pack(
        f"{part}, {name}. Aura is ready — ask a question, send a voice note, or start talk mode.",
        suggestions=["Weather in Jaipur", "What can you do?", "Today's date"],
    )


def _identity(kids: bool, name: str) -> dict[str, Any]:
    if kids:
        return pack(
            f"I'm **Aura**, and my star friend is **Spark**. We help kids like you, {name}, "
            "learn things, hear stories, and play kind games. Grown-ups use Aura for work too. "
            "I don't have a body — I live in this app — but I have lots of curiosity!",
            suggestions=["Tell me a story", "What do elephants eat?"],
        )
    return pack(
        "I'm **Aura**, a professional AI assistant built into this workspace. "
        "I answer questions, keep chats in a local database, and speak with voice notes "
        "inspired by WhatsApp, ChatGPT, and Claude. I look up live facts (Wikipedia, weather, markets) "
        "and I have a **Kids Mode** with Spark, a parent PIN, and gentler language.\n\n"
        "I don't pretend to be human, and I keep your conversations on this device.",
        suggestions=["Open kids mode tips", "Weather in Jaipur"],
    )


def _time(kids: bool) -> dict[str, Any]:
    now = dt.datetime.now(TZ)
    pretty = now.strftime("%I:%M %p").lstrip("0")
    if kids:
        return pack(f"The clock says **{pretty}** in India. That's {now.strftime('%H')} hours and {now.strftime('%M')} minutes.")
    return pack(f"It's **{pretty} IST** ({now.strftime('%H:%M')}) on {now.strftime('%A, %d %B %Y')}.")


def _date(kids: bool) -> dict[str, Any]:
    now = dt.datetime.now(TZ)
    if kids:
        return pack(f"Today is **{now.strftime('%A')}**, {now.strftime('%d %B %Y')}. Have a wonderful {now.strftime('%A')}!")
    return pack(f"Today is **{now.strftime('%A, %d %B %Y')}** (India Standard Time).")


def _extract_city(text: str, default: str) -> str:
    m = re.search(r"\b(?:in|for|at)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)", text)
    if m:
        return m.group(1)
    m2 = re.search(r"\b(?:in|for|at)\s+([a-zA-Z]{3,})$", text.strip())
    if m2:
        return m2.group(1).title()
    return default


def _weather(city: str, kids: bool) -> dict[str, Any]:
    try:
        r = SESSION.get(f"https://wttr.in/{quote(city)}?format=j1", timeout=7)
        r.raise_for_status()
        data = r.json()
        cur = data["current_condition"][0]
        area = data.get("nearest_area", [{}])[0]
        place = area.get("areaName", [{}])[0].get("value", city)
        region = area.get("region", [{}])[0].get("value", "")
        temp = cur.get("temp_C")
        feels = cur.get("FeelsLikeC")
        desc = cur.get("weatherDesc", [{}])[0].get("value", "")
        hum = cur.get("humidity")
        wind = cur.get("windspeedKmph")
        forecast = data.get("weather", [{}])[0]
        max_t = forecast.get("maxtempC")
        min_t = forecast.get("mintempC")
        where = f"{place}" + (f", {region}" if region else "")
        if kids:
            return pack(
                f"Outside in **{where}** it feels like **{feels}°C** and looks **{desc.lower()}**. "
                f"The thermometer says {temp}°C. Don't forget water if it's hot, and a jacket if it's cool!",
                suggestions=["Why does it rain?", "Tell me a story"],
            )
        return pack(
            f"**Weather · {where}**\n\n"
            f"{desc}, **{temp}°C** (feels like {feels}°C). Humidity {hum}%, wind {wind} km/h.\n"
            f"Today's range: {min_t}–{max_t}°C.",
            suggestions=[f"Forecast for {place}", "Time now"],
        )
    except Exception:
        return pack(f"I couldn't reach the weather service for {city}. Try again in a moment.")


def _try_math(text: str) -> str | None:
    raw = text.strip().lower()
    raw = raw.replace("what is", "").replace("what's", "").replace("calculate", "")
    raw = raw.replace("compute", "").replace("solve", "").replace("equals", "")
    raw = raw.replace("x", "*").replace("×", "*").replace("÷", "/").replace("^", "**")
    raw = raw.replace("%", "/100")
    raw = re.sub(r"[^0-9\.\+\-\*\/\(\)\s\*]", "", raw)
    raw = raw.strip()
    if not raw or not re.search(r"\d", raw):
        return None
    if not re.search(r"[\+\-\*\/]", raw) and "**" not in raw:
        return None
    try:
        tree = ast.parse(raw, mode="eval")
        if not _safe_math(tree):
            return None
        value = eval(compile(tree, "<math>", "eval"), {"__builtins__": {}}, {})
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        elif isinstance(value, float):
            value = round(value, 8)
        return f"**{text.strip()}**\n\n= `{value}`"
    except Exception:
        return None


def _safe_math(node: ast.AST) -> bool:
    allowed = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.Pow,
        ast.USub,
        ast.UAdd,
        ast.Load,
        ast.Tuple,
    )
    for child in ast.walk(node):
        if not isinstance(child, allowed):
            return False
        if isinstance(child, ast.Constant) and not isinstance(child.value, (int, float)):
            return False
    return True


UNIT = {
    "km": ("m", 1000),
    "kilometer": ("m", 1000),
    "kilometers": ("m", 1000),
    "m": ("m", 1),
    "meter": ("m", 1),
    "meters": ("m", 1),
    "cm": ("m", 0.01),
    "mm": ("m", 0.001),
    "mile": ("m", 1609.344),
    "miles": ("m", 1609.344),
    "mi": ("m", 1609.344),
    "ft": ("m", 0.3048),
    "foot": ("m", 0.3048),
    "feet": ("m", 0.3048),
    "inch": ("m", 0.0254),
    "inches": ("m", 0.0254),
    "in": ("m", 0.0254),
    "kg": ("g", 1000),
    "kilogram": ("g", 1000),
    "g": ("g", 1),
    "gram": ("g", 1),
    "lb": ("g", 453.592),
    "pound": ("g", 453.592),
    "pounds": ("g", 453.592),
    "oz": ("g", 28.3495),
    "c": ("c", 1),
    "f": ("c", "temp"),
    "celsius": ("c", 1),
    "fahrenheit": ("c", "temp"),
    "l": ("l", 1),
    "liter": ("l", 1),
    "litre": ("l", 1),
    "ml": ("l", 0.001),
    "gallon": ("l", 3.78541),
    "gallons": ("l", 3.78541),
}


def _convert(text: str, kids: bool) -> dict[str, Any]:
    m = CONVERT_RE.search(text)
    if not m:
        return pack("Try: convert 10 km to miles")
    amount, src, dst = float(m.group(1)), m.group(2).lower().strip("s"), m.group(3).lower().strip("s")
    src_k = m.group(2).lower()
    dst_k = m.group(3).lower()
    if src_k not in UNIT:
        src_k = src
    if dst_k not in UNIT:
        dst_k = dst
    if src_k not in UNIT or dst_k not in UNIT:
        return pack("I can convert km, miles, kg, pounds, Celsius/Fahrenheit, litres and gallons.")
    s_dim, s_f = UNIT[src_k]
    d_dim, d_f = UNIT[dst_k]
    if src_k in {"c", "celsius"} and dst_k in {"f", "fahrenheit"}:
        val = amount * 9 / 5 + 32
    elif src_k in {"f", "fahrenheit"} and dst_k in {"c", "celsius"}:
        val = (amount - 32) * 5 / 9
    else:
        if s_dim != d_dim or s_f == "temp" or d_f == "temp":
            return pack("Those units don't match. Try km→miles or °C→°F.")
        metres = amount * float(s_f)
        val = metres / float(d_f)
    pretty = round(val, 4)
    if kids:
        return pack(f"**{amount} {m.group(2)}** is about **{pretty} {m.group(3)}**. Nice converting!")
    return pack(f"**{amount} {m.group(2)}** = **{pretty} {m.group(3)}**")


CUR_MAP = {
    "usd": "USD",
    "dollar": "USD",
    "dollars": "USD",
    "$": "USD",
    "inr": "INR",
    "rupee": "INR",
    "rupees": "INR",
    "rs": "INR",
    "rs.": "INR",
    "₹": "INR",
    "eur": "EUR",
    "€": "EUR",
    "gbp": "GBP",
    "£": "GBP",
}


def _currency(text: str, kids: bool) -> dict[str, Any]:
    m = CURRENCY_RE.search(text.lower())
    if not m:
        return pack("Try: 25 USD to INR")
    amount = float(m.group(1).replace(",", ""))
    src = CUR_MAP.get(m.group(2).replace("₹", "₹"))
    # group 2 might be rs.
    g2 = m.group(2).lower().strip()
    g3 = m.group(3).lower().strip()
    src = CUR_MAP.get(g2, CUR_MAP.get(g2.rstrip("s")))
    dst = CUR_MAP.get(g3, CUR_MAP.get(g3.rstrip("s")))
    if not src or not dst:
        return pack("I can convert USD, INR, EUR and GBP.")
    try:
        r = SESSION.get(f"https://api.frankfurter.app/latest?amount={amount}&from={src}&to={dst}", timeout=6)
        r.raise_for_status()
        val = r.json()["rates"][dst]
        if kids:
            return pack(f"**{amount} {src}** is about **{val:.2f} {dst}**.")
        return pack(f"**{amount:,.2f} {src}** = **{val:,.2f} {dst}** (European Central Bank reference rate).")
    except Exception:
        return pack("Currency service is busy. Try again shortly.")


def _define(text: str, kids: bool) -> dict[str, Any] | None:
    word = text.lower()
    word = re.sub(r"^(define|definition of|meaning of|what does|what is a|what is an|what is)\s+", "", word)
    word = re.sub(r"\s+mean\??$", "", word)
    word = re.sub(r"[^a-z\- ]", "", word).strip()
    if not word or len(word.split()) > 4:
        return None
    try:
        r = SESSION.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(word)}", timeout=6)
        if r.status_code != 200:
            return None
        data = r.json()[0]
        term = data.get("word", word)
        phonetic = data.get("phonetic") or ""
        meanings = data.get("meanings") or []
        bits = [f"**{term}**" + (f" · {phonetic}" if phonetic else "")]
        for meaning in meanings[:2]:
            part = meaning.get("partOfSpeech", "")
            defs = meaning.get("definitions") or []
            if not defs:
                continue
            d0 = defs[0].get("definition", "")
            ex = defs[0].get("example")
            if kids:
                bits.append(f"It is a {part}. {d0}")
            else:
                bits.append(f"*{part}* — {d0}")
            if ex:
                bits.append(f"Example: _{ex}_")
        return pack("\n\n".join(bits))
    except Exception:
        return None


def _kids_intents(text: str, name: str) -> dict[str, Any] | None:
    low = text.lower()

    if STORY_RE.search(low):
        topic = re.sub(r".*?(?:story about|story of|story)\s*", "", low).strip(" ?.!")
        if topic in {"story", "a story", "me a story", "please", ""}:
            topic = random.choice(["a brave little peacock", "a rocket to the moon", "a kind elephant"])
        return pack(_make_story(name, topic), suggestions=["Another story", "A riddle", "Quiz time"])

    if RHYME_RE.search(low):
        return pack("Here is a rhyme we can say together:\n\n" + random.choice(RHYMES), suggestions=["Another rhyme", "A story"])

    if RIDDLE_RE.search(low):
        item = random.choice(RIDDLES)
        return pack(
            f"Riddle time, {name}!\n\n**{item['q']}**\n\nTake a guess — or ask for a hint.",
            meta={"riddle_answer": item["a"], "riddle_hint": item["hint"]},
            suggestions=["Hint please", "Tell me a joke"],
        )

    if QUIZ_RE.search(low):
        item = random.choice(QUIZZES)
        return pack(
            f"Quiz time, {name}! 🌟\n\n**{item['q']}**",
            meta={"quiz_answers": item["a"]},
            suggestions=["Another quiz", "A riddle"],
        )

    if JOKE_RE.search(low):
        return pack(random.choice(KIDS_JOKES) + "\n\nWant another one?", suggestions=["Another joke", "A riddle"])

    for key, ans in KIDS_WHY.items():
        if key in low or low.replace("why is the ", "").replace("why are ", "").replace("why do ", "").startswith(key):
            return pack(ans, suggestions=["Another why", "Space facts"])
    if low.startswith("why "):
        wiki = _knowledge(text, True, name)
        if wiki:
            return wiki

    for animal, fact in ANIMAL_FACTS.items():
        if animal in low:
            return pack(fact, suggestions=["Another animal", "Tell me a story"])
    if "animal" in low:
        animal, fact = random.choice(list(ANIMAL_FACTS.items()))
        return pack(f"Let's meet the **{animal}**!\n\n{fact}", suggestions=["Another animal", "Quiz time"])

    for planet, fact in PLANETS.items():
        if planet in low:
            return pack(fact, suggestions=["Mars", "Jupiter", "Earth"])
    if any(w in low for w in ("space", "planet", "solar system", "galaxy", "astronaut")):
        return pack(
            "Our solar system has eight planets dancing around the sun. "
            "Earth is the one with oceans and people. Saturn has rings. Jupiter is the giant. "
            "Want a fact about a planet?",
            suggestions=["Mars", "Saturn", "The Moon"],
        )

    if "dinosaur" in low:
        return pack(
            KIDS_WHY["dinosaurs extinct"] + " T-Rex had tiny arms and huge teeth. Triceratops had three horns. "
            "Some dinosaurs had feathers!",
            suggestions=["Tell me a dinosaur story", "Quiz time"],
        )

    if any(w in low for w in ("i love you", "you're my friend", "best friend")):
        return pack(f"That's so kind, {name}. Spark and I care about you too. You are brave and curious!")

    if any(w in low for w in ("i'm sad", "im sad", "i am sad", "nobody likes", "i'm scared", "im scared")):
        return pack(
            f"I'm here with you, {name}. It's okay to feel sad or scared — feelings come and go like weather. "
            "You can take a slow breath with me: in for 3, out for 3. "
            "A hug from someone you trust helps too. Want a gentle story?",
            suggestions=["A gentle story", "A kind joke"],
        )

    return None


def _make_story(name: str, topic: str) -> str:
    topic = topic[:40] if topic else "a little star"
    openings = [
        f"Once upon a time, in a sunny courtyard in Jaipur, a child named {name} met {topic}.",
        f"On a sparkling evening, {name} looked up and imagined {topic}.",
        f"Long ago, and also right now in our imaginations, {name} and {topic} became friends.",
    ]
    middles = [
        "They found a problem: a lost kite stuck in a mango tree. Instead of grabbing, they asked for help, made a plan, and used kindness as their superpower.",
        "A small storm rolled in. They waited together, shared snacks, and sang until the clouds turned pink again.",
        "They discovered a secret garden where every flower had a wish. They wished for courage, then practised it with tiny brave steps.",
    ]
    endings = [
        f"When the stars came out, {topic} whispered, 'You were the hero all along, {name}.' And {name} slept with a smile.",
        f"They promised to meet again tomorrow. The end — until you say 'another story'!",
        f"And that is how {name} learned that curious hearts can change a whole day. Goodnight, explorer.",
    ]
    return f"{random.choice(openings)}\n\n{random.choice(middles)}\n\n{random.choice(endings)}"


def _pending_quiz(history: list[dict[str, Any]]) -> list[str] | None:
    for item in reversed(history):
        if item.get("role") == "assistant":
            answers = (item.get("meta") or {}).get("quiz_answers")
            return answers
        if item.get("role") == "user":
            break
    return None


def _pending_riddle(history: list[dict[str, Any]]) -> dict[str, str] | None:
    for item in reversed(history):
        if item.get("role") == "assistant":
            meta = item.get("meta") or {}
            if meta.get("riddle_answer"):
                return {"a": meta["riddle_answer"], "hint": meta.get("riddle_hint", "")}
        if item.get("role") == "user":
            break
    return None


def _grade_quiz(text: str, answers: list[str], name: str) -> dict[str, Any]:
    guess = text.lower().strip(" !.?,")
    ok = any(guess == a or a in guess or guess in a for a in answers)
    next_q = random.choice(QUIZZES)
    if ok:
        body = f"Yes, {name}! **{answers[0]}** is right. You're shining.\n\nNext: **{next_q['q']}**"
    else:
        body = f"Nice try! The answer was **{answers[0]}**. You'll get the next one.\n\nNext: **{next_q['q']}**"
    return pack(body, meta={"quiz_answers": next_q["a"]}, suggestions=["Stop quiz", "A joke"])


def _grade_riddle(text: str, riddle: dict[str, str], name: str) -> dict[str, Any]:
    guess = text.lower().strip(" !.?,")
    if "hint" in guess:
        return pack(
            f"Hint: {riddle['hint']}",
            meta={"riddle_answer": riddle["a"], "riddle_hint": riddle["hint"]},
        )
    if riddle["a"] in guess or guess in riddle["a"]:
        return pack(f"You got it, {name}! It was **{riddle['a']}**. Another riddle, a story, or a quiz?", suggestions=["Another riddle", "Story", "Quiz"])
    return pack(
        f"Not quite — keep thinking! Hint: {riddle['hint']}",
        meta={"riddle_answer": riddle["a"], "riddle_hint": riddle["hint"]},
        suggestions=["Tell me the answer"],
    )


def _kids_block_message(text: str, name: str) -> dict[str, Any] | None:
    if KIDS_BLOCK.search(text):
        return pack(
            f"{name}, that's a grown-up topic. Let's pick something kind and curious instead — "
            "a story, animals, space, or a quiz!",
            suggestions=["Tell me a story", "Animal facts", "Space facts", "Quiz time"],
        )
    return None


def _simplify(text: str) -> str:
    out = text
    for a, b in SIMPLE_WORDS.items():
        out = re.sub(rf"\b{a}\b", b, out, flags=re.I)
    sentences = re.split(r"(?<=[.!?])\s+", out)
    return " ".join(sentences[:3])


def _knowledge(text: str, kids: bool, name: str) -> dict[str, Any] | None:
    query = _search_query(text)
    if not query or len(query) < 2:
        return None
    ddg = _duckduckgo(query)
    wiki = _wikipedia(query)
    pieces = []
    title = None
    if ddg.get("answer"):
        pieces.append(ddg["answer"])
    if wiki.get("extract"):
        pieces.append(wiki["extract"])
        title = wiki.get("title") or title
    elif ddg.get("abstract"):
        pieces.append(ddg["abstract"])
        title = ddg.get("heading") or title
    if not pieces:
        return None
    def _trim(block: str, n: int = 4) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", block.strip())
        return " ".join(sentences[:n]).strip()

    body = _trim(pieces[0])
    extra = _trim(pieces[1], 2) if len(pieces) > 1 and pieces[1] not in pieces[0] else ""
    if kids:
        body = _simplify(body)
        extra = _simplify(extra) if extra else ""
        text_out = f"{body}"
        if extra and extra not in body:
            text_out += " " + extra
        text_out += f"\n\nWant to keep exploring, {name}?"
        return pack(
            text_out,
            meta={"topic": title or query},
            suggestions=["Tell me more", "A quiz", "A story"],
        )
    heading = f"**{title}**\n\n" if title else ""
    text_out = heading + body
    if extra and extra not in body:
        text_out += "\n\n" + extra
    source = wiki.get("url") or ddg.get("url")
    if source:
        text_out += f"\n\n_Source: {source}_"
    return pack(text_out, meta={"topic": title or query}, suggestions=["Tell me more"])


def _search_query(text: str) -> str:
    q = text.strip()
    q = re.sub(r"[?!.]+$", "", q)
    q = re.sub(
        r"^\s*(please |can you |could you |tell me |explain |who is |who was |what is |what are |what was |what's |whats |where is |when is |how does |how do |how did |why is |why are |why do )",
        "",
        q,
        flags=re.I,
    )
    q = re.sub(r"^\s*(a |an |the )", "", q, flags=re.I)
    return q.strip()[:80]


def _duckduckgo(query: str) -> dict[str, str]:
    try:
        r = SESSION.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=6,
        )
        r.raise_for_status()
        data = r.json()
        abstract = (data.get("AbstractText") or "").strip()
        heading = data.get("Heading") or ""
        answer = (data.get("Answer") or "").strip()
        url = data.get("AbstractURL") or ""
        if not abstract and data.get("RelatedTopics"):
            rel = data["RelatedTopics"][0]
            if isinstance(rel, dict):
                abstract = (rel.get("Text") or "")[:400]
        return {"abstract": abstract, "heading": heading, "answer": answer, "url": url}
    except Exception:
        return {}


def _wikipedia(query: str) -> dict[str, str]:
    try:
        s = SESSION.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": 5,
                "utf8": 1,
                "format": "json",
            },
            timeout=6,
        )
        s.raise_for_status()
        hits = s.json().get("query", {}).get("search") or []
        title = None
        for hit in hits:
            t = hit.get("title") or ""
            low = t.lower()
            if low.startswith("list of") or low.endswith("(disambiguation)"):
                continue
            title = t
            break
        if not title:
            return {}
        r = SESSION.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}",
            timeout=6,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("type") == "disambiguation":
            return {}
        extract = (data.get("extract") or "").strip()
        incumbent = _wiki_incumbent(title)
        if incumbent and incumbent.lower() not in extract.lower():
            person = _wikipedia_summary(incumbent)
            if person.get("extract"):
                extract = f"The current officeholder is **{incumbent}**. " + person["extract"]
                return {
                    "title": incumbent,
                    "extract": extract,
                    "url": person.get("url") or "",
                }
        return {
            "title": data.get("title") or title,
            "extract": extract,
            "url": data.get("content_urls", {}).get("desktop", {}).get("page") or "",
        }
    except Exception:
        return {}


def _wikipedia_summary(title: str) -> dict[str, str]:
    try:
        r = SESSION.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}",
            timeout=6,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "title": data.get("title") or title,
            "extract": (data.get("extract") or "").strip(),
            "url": data.get("content_urls", {}).get("desktop", {}).get("page") or "",
        }
    except Exception:
        return {}


def _wiki_incumbent(title: str) -> str | None:
    try:
        r = SESSION.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "rvsection": 0,
                "titles": title,
                "format": "json",
            },
            timeout=6,
        )
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
        content = ""
        for page in pages.values():
            revs = page.get("revisions") or []
            if revs:
                content = revs[0].get("slots", {}).get("main", {}).get("*") or revs[0].get("*") or ""
        m = re.search(r"\|\s*incumbent\s*=\s*\[\[([^\]|]+)", content, re.I)
        if m:
            return m.group(1).strip()
    except Exception:
        return None
    return None


def _tell_more(text: str, history: list[dict[str, Any]], kids: bool) -> dict[str, Any] | None:
    if not re.search(r"\b(tell me more|more about that|continue|go on|and then)\b", text, re.I):
        return None
    topic = None
    for item in reversed(history):
        topic = (item.get("meta") or {}).get("topic")
        if topic:
            break
    if not topic:
        return None
    return _knowledge(f"what is {topic}", kids, "friend")


def _maybe_creative(text: str, kids: bool, name: str) -> dict[str, Any] | None:
    if not re.search(r"\b(write|compose|draft|poem|email|lyrics|brainstorm|give me ideas)\b", text, re.I):
        return None
    if kids:
        return pack(
            _make_story(name, "a magical paintbrush"),
            suggestions=["Another story"],
        )
    low = text.lower()
    if "email" in low or "mail" in low:
        return pack(
            "Here's a clean email draft you can tailor:\n\n"
            "**Subject:** Following up\n\n"
            "Hi [Name],\n\nI hope you're well. I'm writing regarding [topic]. "
            "Please let me know a convenient time to discuss, or if you need anything from my side.\n\n"
            "Thank you,\n[Your name]\n\nTell me the recipient and goal and I'll rewrite it more tightly."
        )
    if "poem" in low:
        return pack(
            "A short poem:\n\n"
            "The city cools, the neon thins,\n"
            "A quieter courage under the din.\n"
            "Ask again with a subject — I'll write one just for that."
        )
    if "idea" in low or "brainstorm" in low:
        return pack(
            "Three starting points:\n\n1. Define the outcome in one sentence.\n"
            "2. List constraints (time, money, people).\n"
            "3. Sketch the smallest version you could finish this week.\n\nShare the topic for a sharper list."
        )
    return None


def _adult_joke() -> str:
    return random.choice(
        [
            "I told my database a joke about entropy. It wasn't ordered enough to laugh.",
            "There are 10 kinds of people: those who understand binary and those who don't.",
            "Why do programmers prefer dark mode? Because light attracts bugs.",
            "I would tell you a UDP joke, but you might not get it.",
        ]
    )


def _fallback(text: str, kids: bool, name: str) -> dict[str, Any]:
    wiki = _knowledge(text, kids, name)
    if wiki:
        return wiki
    if kids:
        return pack(
            f"Hmm, I'm not sure yet, {name}. We can try a story, an animal fact, space, a quiz, or asking 'why is the sky blue?'",
            suggestions=["Tell me a story", "Animal facts", "Quiz time", "Weather"],
        )
    return pack(
        "I don't have a confident answer for that yet. I'm strongest on **facts, weather, maths, conversions, and definitions**. "
        "Try naming a person, place, or idea — for example *What is the Taj Mahal?* or *10 km to miles*.",
        suggestions=["Weather in Jaipur", "Who is the Prime Minister of India?", "Define entropy"],
    )
