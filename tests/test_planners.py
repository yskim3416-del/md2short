from datetime import date

from conftest import ROOT, words_from_text

from md2short import caption_plan, data_extract, emoticon_map, opening, storyboard
from md2short.numeric_display import align_display_words
from md2short.schema import CaptionWord
from md2short.script import fallback_extract
from md2short.tts_text import prepare_tts_text, read_native, read_number, read_sino, to_spoken

SAMPLE = (ROOT / "sample.md").read_text(encoding="utf-8")


# --- tts_text ---------------------------------------------------------------

def test_number_readings():
    assert read_sino(7230) == "칠천이백삼십"
    assert read_sino(10000) == "만"
    assert read_sino(1950) == "천구백오십"
    assert read_sino(120000000) == "일억이천만"
    assert read_number("0.94") == "영점구사"
    assert read_number("7,230") == "칠천이백삼십"
    assert read_native(3) == "세" and read_native(20) == "스무" and read_native(100) is None


def test_to_spoken_and_display_unchanged():
    display = "S&P 500 종가 7,230 기록, 나스닥은 0.94% 상승. 3개 종목, AI 시장."
    spoken = to_spoken(display)
    assert "에스앤피 오백" in spoken and "칠천이백삼십" in spoken
    assert "영점구사 퍼센트" in spoken and "세 개" in spoken and "에이아이" in spoken
    assert display == "S&P 500 종가 7,230 기록, 나스닥은 0.94% 상승. 3개 종목, AI 시장."
    assert to_spoken("2개월 동안 5개국") == "이개월 동안 오개국"
    assert to_spoken("첫째 1번째, 3시간") == "첫째 첫 번째, 세 시간"
    assert to_spoken("1950년 이후, 2024년") == "천구백오십 년 이후, 이천이십사 년"
    tts = prepare_tts_text("핵심은 ‘5주 연속 상승’이라는 점입니다.\n다음 줄…끝")
    assert "‘" not in tts and "\n" not in tts and "오주" in tts and "…" not in tts


# --- numeric_display --------------------------------------------------------

def test_numeric_display_restores_original_tokens_without_retiming():
    script = "S&P 500 종가 7,230 기록했습니다. 나스닥은 0.94% 상승했습니다."
    scribe = [
        CaptionWord(text="에센피", start=0, end=300),
        CaptionWord(text="오백", start=310, end=600),
        CaptionWord(text="종가", start=610, end=900),
        CaptionWord(text="칠천", start=910, end=1200),
        CaptionWord(text="이백삼십", start=1210, end=1600),
        CaptionWord(text="기록했습니다", start=1610, end=2200),
        CaptionWord(text="나스닥은", start=2900, end=3300),
        CaptionWord(text="영점구사퍼센트", start=3310, end=4000),
        CaptionWord(text="상승했습니다.", start=4010, end=4600),
    ]
    out, src = align_display_words(script, scribe)
    assert [w.text for w in out] == ["S&P", "500", "종가", "7,230", "기록했습니다.", "나스닥은", "0.94%", "상승했습니다."]
    merged = out[3]
    assert (merged.start, merged.end) == (910, 1600)  # Scribe timing 유지, 두 단어 병합
    assert out[0].start == 0 and out[-1].end == 4600
    assert src == [0, 1, 2, 3, 4, 5, 6, 7]


def test_numeric_display_keeps_unrelated_scribe_words():
    out, src = align_display_words("상승했습니다.", [CaptionWord(text="완전히", start=0, end=100), CaptionWord(text="상승했습니다", start=110, end=500)])
    assert [w.text for w in out] == ["완전히", "상승했습니다."]
    assert src == [None, 0]


# --- caption_plan -----------------------------------------------------------

def test_caption_segments_rules():
    words = words_from_text("오늘 증시가 올랐습니다. 다만 거래량은")
    words.append(CaptionWord(text="적었습니다", start=words[-1].end + 700, end=words[-1].end + 1000))
    words.append(CaptionWord(text="끝", start=words[-1].end + 50, end=words[-1].end + 200))
    segs = caption_plan.build_caption_segments(words, chunk_size=14)
    # 2단어 뒤 700ms 쉼은 끊지 않는다 (주어만 남는 조각 방지)
    assert [(s["wordStart"], s["wordEnd"]) for s in segs] == [(0, 3), (3, 7)]
    assert segs[0]["text"] == "오늘 증시가 올랐습니다."
    assert segs[0]["startMs"] == words[0].start and segs[0]["endMs"] == words[2].end
    long = words_from_text("지난 금요일 미국 증시가 강하게")
    long.append(CaptionWord(text="마감했습니다.", start=long[-1].end + 700, end=long[-1].end + 1000))
    segs = caption_plan.build_caption_segments(long, chunk_size=14)
    assert [(s["wordStart"], s["wordEnd"]) for s in segs] == [(0, 5), (5, 6)]


def test_caption_segments_balanced_split_of_long_sentence():
    text = "업계에서는 어린이 이용 제한 기능 도입이 사용자 감소로 이어진 것으로 보고 있습니다. 끝."
    segs = caption_plan.build_caption_segments(words_from_text(text), chunk_size=14)
    lens = [len(s["text"]) for s in segs[:-1]]
    assert len(lens) == 2 and all(n <= caption_plan.MAX_SEGMENT_CHARS for n in lens)
    assert abs(lens[0] - lens[1]) <= 8  # 짧은 꼬리 조각 없음
    assert segs[-1]["text"] == "끝."


def test_caption_segments_chunk_cap_and_opening_skip():
    words = words_from_text("하나 둘 셋 넷 다섯 여섯 일곱")
    segs = caption_plan.build_caption_segments(words, chunk_size=3, skip_before_ms=800)
    assert [(s["wordStart"], s["wordEnd"]) for s in segs] == [(2, 5), (5, 7)]
    forced = caption_plan.build_caption_segments(words, chunk_size=14, forced_breaks={1})
    assert [(s["wordStart"], s["wordEnd"]) for s in forced] == [(0, 2), (2, 7)]


# --- emoticon_map -----------------------------------------------------------

def test_emoticon_dictionary_covers_all_assets():
    files = {p.name for p in (ROOT / "emoticon").glob("*.png")}
    assert len(files) == 60
    assert set(emoticon_map.EMOTICON_KEYWORDS) == files
    for _, f in emoticon_map.FALLBACK_CATEGORIES:
        assert f in files
    assert set(emoticon_map.NEUTRAL_ROTATION) <= files


def test_emoticon_cues_deterministic_and_exist():
    words = words_from_text(fallback_extract(SAMPLE)["hook"] + " " + fallback_extract(SAMPLE)["body"])
    segs = caption_plan.build_caption_segments(words)
    cues1 = emoticon_map.plan_cues(segs, words[-1].end + 300)
    cues2 = emoticon_map.plan_cues(segs, words[-1].end + 300)
    assert cues1 == cues2 and len(cues1) <= len(segs)  # 긴 문장은 자막 여러 조각, 이미지는 문장당 1장
    for c in cues1:
        assert (ROOT / c["emoticonFileName"]).exists()
    by_start = {c["startMs"]: c["emoticonFileName"] for c in cues1}
    by_text = {s["text"]: by_start[s["startMs"]] for s in segs if s["startMs"] in by_start}
    assert by_text["로블록스, 18% 급락했습니다."].endswith("08_전량매도_급락.png")
    assert by_text["애플, 호실적으로 3.2% 상승했습니다."].endswith("25_애플깜짝성장_실적호조.png")
    # 연속 구간은 빈틈없이 이어진다
    for a, b in zip(cues1, cues1[1:]):
        assert a["startMs"] + a["durationMs"] == b["startMs"]


def test_cues_follow_sentences_on_real_scribe_timing():
    """실제 sample.md 실행(Daniel voice)의 words.json — pause로 쪼개진 문장 조각이 중립 이미지를 받던 회귀."""
    import json

    words = [CaptionWord(**w) for w in json.loads((ROOT / "tests/fixtures/sample_words_real.json").read_text(encoding="utf-8"))["words"]]
    segs = caption_plan.build_caption_segments(words, 14, skip_before_ms=2540)
    cues = emoticon_map.plan_cues(segs, 76254)
    assert len(cues) < len(segs)  # 문장 단위로 묶임
    for a, b in zip(cues, cues[1:]):
        assert a["emoticonFileName"] != b["emoticonFileName"]
        assert a["startMs"] + a["durationMs"] == b["startMs"]
    t_7230 = next(w.start for w in words if w.text == "7,230")
    at = [c for c in cues if c["startMs"] <= t_7230][-1]
    assert not at["emoticonFileName"].endswith("06_움직임없음_관망.png")
    # 다른 종목명이 그려진 이미지가 로블록스 문장에 붙던 회귀
    assert not any("포테크놀로지" in c["emoticonFileName"] for c in cues)


def test_index_lookahead_stops_at_sentence_end_on_real_words():
    """'다우는 소폭 하락했습니다. 4월 기준으로는…' 에서 '다우 4' 카드가 생기던 회귀 (실제 Scribe 타이밍)."""
    import json

    words = [CaptionWord(**w) for w in json.loads((ROOT / "tests/fixtures/sample_words_real.json").read_text(encoding="utf-8"))["words"]]
    cards = data_extract.plan_number_cards(words, skip_before_ms=2540)
    assert all(c["text"] != "4" for c in cards)
    assert not any(c["label"] == "다우" for c in cards)
    assert ("7,230", "S&P 500") in [(c["text"], c["label"]) for c in cards]
    synthetic = words_from_text("다우는 하락했습니다. 4월 기준 코스피 5주 연속 상승", step_ms=1500)
    assert data_extract.plan_number_cards(synthetic) == []


def test_card_label_uses_sentence_subject_and_merged_index():
    """'애플은 호실적으로 3.2%' 라벨이 '호실적'이 되던 회귀, 'S&P 500은'이 한 단어로 합쳐져 카드가 빠지던 회귀."""
    words = words_from_text("애플은 호실적으로 3.2% 상승했습니다. 반면 로블록스는 18% 급락했습니다.", step_ms=1500)
    cards = data_extract.plan_number_cards(words)
    assert [(c["label"], c["text"], c["tone"]) for c in cards] == [("애플", "3.2%", "up"), ("로블록스", "18%", "down")]
    again = words_from_text("로블록스는 18% 급락했습니다. 로블록스는 18% 급락, 어떻게 보시나요?", step_ms=1500)
    assert len(data_extract.plan_number_cards(again)) == 1
    merged = [CaptionWord(text="S&P 500은", start=0, end=600), CaptionWord(text="7,230에", start=700, end=1200),
              CaptionWord(text="마감했습니다.", start=1300, end=1900)]
    assert [(c["label"], c["text"]) for c in data_extract.plan_number_cards(merged)] == [("S&P 500", "7,230")]


def test_mild_moves_closing_and_dedupe_fallback():
    segs = [
        {"startMs": 0, "endMs": 900, "text": "나스닥은 0.94% 상승했습니다."},
        {"startMs": 1000, "endMs": 1900, "text": "다우는 소폭 하락했습니다."},
        {"startMs": 2000, "endMs": 2900, "text": "오라클이 AI 네트워크에 합류했습니다."},
        {"startMs": 3000, "endMs": 3900, "text": "정부의 AI 시장이 본격 매출 사이클에 진입한 신호로 풀이됩니다."},
        {"startMs": 4000, "endMs": 4400, "text": "로블록스 급락, 여러분은 어떻게 보시나요?"},
        {"startMs": 4500, "endMs": 4900, "text": "댓글로 알려 주세요."},
    ]
    cues = emoticon_map.plan_cues(segs, 5000, start_ms=0, closing_text="로블록스 급락, 여러분은 어떻게 보시나요? 댓글로 알려 주세요.")
    files = [c["emoticonFileName"].split("/")[-1] for c in cues]
    assert files[0] == "03_굿굿_칭찬.png"  # 1% 미만 상승 → 과장 없는 이미지
    assert files[1] == "06_움직임없음_관망.png"  # 소폭 하락
    assert files[2] == "27_AI계약_승인.png"
    assert files[3] == "01_정독중_리포트.png"  # 해석 문장 → 리포트 정독 (직전 AI 이미지·애플 '깜짝 성장' 재사용 아님)
    assert files[-1] == emoticon_map.CLOSING_CHOICES[0]
    assert len(cues) == len(segs) - 1  # 두 문장짜리 CTA는 이미지 1장
    assert len(set(files)) == len(files)  # 한 영상 안에서 같은 이미지 반복 없음
    assert cues[0]["startMs"] == 0
    assert emoticon_map.keyword_tones(["급락", "연속 상승", "AI 시장"]) == {"급락": "down", "연속 상승": "up"}


def test_no_image_reuse_and_similar_family():
    segs = [
        {"startMs": 0, "endMs": 900, "text": "나스닥은 0.94% 상승했습니다."},
        {"startMs": 1000, "endMs": 1900, "text": "두 번째로 좋은 성과입니다."},
        {"startMs": 2000, "endMs": 2900, "text": "애플은 호실적으로 3.2% 상승했습니다."},
        {"startMs": 3000, "endMs": 3900, "text": "메타도 깜짝 실적호조를 보였습니다."},
    ]
    files = [c["emoticonFileName"].split("/")[-1] for c in emoticon_map.plan_cues(segs, 4000)]
    assert files.count("03_굿굿_칭찬.png") == 1  # '좋은 성과'가 굿굿을 다시 쓰지 않음
    assert files[2] == "25_애플깜짝성장_실적호조.png"
    assert "20_깜짝성장_실적호조.png" not in files  # 애플 깜짝성장과 거의 같은 그림은 같은 영상에서 피함


def test_card_label_particles():
    assert data_extract.strip_particle("로블록스가") == "로블록스"
    assert data_extract.strip_particle("호실적으로") == "호실적"
    assert data_extract.strip_particle("나스닥은") == "나스닥"
    assert data_extract.strip_particle("다우") == "다우"


def test_storyboard_hint_wins():
    segs = [{"startMs": 0, "endMs": 500, "text": "오늘 소식입니다."}]
    cues = emoticon_map.plan_cues(segs, 600, hints=["호랑이가 로켓을 타고 급등"])
    assert cues[0]["emoticonFileName"].endswith("26_반도체급등_로켓상승.png")


def test_company_logo_cues(tmp_path):
    assert emoticon_map.plan_company_logo_cues(words_from_text("애플 상승"), tmp_path / "none") == []
    (tmp_path / "애플.png").write_bytes(b"png")
    cues = emoticon_map.plan_company_logo_cues(words_from_text("오늘 애플, 상승"), tmp_path)
    assert cues == [{"startMs": 400, "durationMs": 2000, "logoFileName": "company/애플.png", "name": "애플"}]


# --- data_extract -----------------------------------------------------------

def test_number_cards_from_sample():
    words = words_from_text(fallback_extract(SAMPLE)["hook"] + " " + fallback_extract(SAMPLE)["body"], step_ms=600)
    cards = data_extract.plan_number_cards(words)
    texts = [c["text"] for c in cards]
    assert texts[0] == "7,230" and cards[0]["label"] == "S&P 500"
    # 0.94%는 7,230 직후(<2.5s)라 cooldown으로 빠진다
    assert "3.2%" in texts and "18%" in texts and "0.94%" not in texts
    assert "500" not in texts
    assert len(cards) <= data_extract.MAX_CARDS
    for a, b in zip(cards, cards[1:]):
        assert b["startMs"] - a["startMs"] >= data_extract.COOLDOWN_MS
    assert all(c["durationMs"] == 1800 for c in cards)


def test_number_cards_patterns_and_limits():
    words = words_from_text("코스피 2,650 포인트 마감, 매출 3조 원 기록, 120 포인트 하락, 순이익 5억 달러", step_ms=1500)
    texts = [c["text"] for c in data_extract.plan_number_cards(words)]
    assert texts == ["2,650 포인트", "3조 원", "120 포인트", "5억 달러"]
    many = words_from_text(" ".join(f"{i}%" for i in range(1, 30)), step_ms=3000)
    assert len(data_extract.plan_number_cards(many)) == 6


# --- storyboard / opening / script fallback ---------------------------------

STORYBOARD = """# 데일리
### 1컷
- 자막: 미국 증시가 올랐습니다
- 화면 연출: 호랑이가 로켓을 탄다
- 이미지 프롬프트: tiger on a rocket
### 2컷
**자막**: 로블록스는 18% 급락했습니다.
**화면 연출**: 패닉
"""


def test_storyboard_parse():
    assert storyboard.is_storyboard(STORYBOARD) and not storyboard.is_storyboard(SAMPLE)
    cuts = storyboard.parse_storyboard(STORYBOARD)
    assert [c.caption for c in cuts] == ["미국 증시가 올랐습니다.", "로블록스는 18% 급락했습니다."]
    assert cuts[0].direction == "호랑이가 로켓을 탄다" and cuts[0].image_prompt == "tiger on a rocket"
    narration = storyboard.narration(cuts)
    assert "화면" not in narration and "tiger" not in narration and "패닉" not in narration


def test_opening():
    d = date(2026, 10, 26)
    assert opening.spoken_opening(d) == "10월 26일 데이브리핑입니다."
    assert opening.opening_visual_text(d) == "26년 10월 26일\n데이브리핑"
    words = words_from_text("10월 26일 데이브리핑입니다. 증시가")
    assert opening.opening_duration_ms(words) == words[2].end
    assert opening.opening_duration_ms(words_from_text("증시가 올랐습니다")) == 0


def test_fallback_extract_preserves_all_sentences():
    s = fallback_extract(SAMPLE)
    assert s["hook"] == "지난 금요일 미국 증시, 강하게 상승 마감했습니다."
    full = s["hook"] + "\n" + s["body"]
    for line in [ln.strip() for ln in SAMPLE.splitlines() if ln.strip()]:
        assert line.rstrip(".") in full
