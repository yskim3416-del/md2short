"""호랑이 PNG cue planner (visual_mode=emoticon).

자막 segment(=caption_plan 결과) 하나당 cue 1개. segment 텍스트에서 가장 구체적인(긴) keyword match를
고르고, 없으면 감성 fallback category → neutral 순환 순으로 결정론적으로 선택한다.
"""

from __future__ import annotations

from pathlib import Path

import re

from md2short.caption_plan import ends_sentence
from md2short.data_extract import sentence_tone

EMOTICON_DIR = "emoticon"

# 파일명 → 매칭 keyword. 파일명(NN_키워드_설명.png)의 두 단어는 자동으로 포함된다.
EMOTICON_KEYWORDS: dict[str, list[str]] = {
    "01_정독중_리포트.png": ["보고서", "리포트", "자료", "풀이됩니다", "해석됩니다", "보고 있습니다", "신호로"],
    "02_머리아파_혼란.png": ["혼란", "골치", "복잡"],
    "03_굿굿_칭찬.png": ["호재", "긍정적", "좋은 성과", "좋은"],
    "04_나도울고싶어_하락.png": ["하락", "약세", "내렸", "떨어"],
    "05_분석중_차트.png": ["분석", "차트", "지표", "데이터"],
    "06_움직임없음_관망.png": ["보합", "관망", "소폭", "횡보"],
    "07_승인완료_도장.png": ["승인", "확정", "공식", "합류", "체결"],
    "08_전량매도_급락.png": ["급락", "투매", "매도세"],
    "09_가즈아_상승.png": ["상승", "올랐", "강세", "오름"],
    "10_살까말까_고민.png": ["고민", "선택", "갈등"],
    "11_물타기가즈아_하락매수.png": ["저가매수", "물타기", "하락매수"],
    "12_리포트작성_공부.png": ["공부", "연구", "작성"],
    "13_이게뭔말이야_당황.png": ["당황", "예상밖", "의외"],
    "14_상폐_장례식.png": ["상장폐지", "상폐", "파산"],
    "15_존버중_버티기.png": ["버티", "존버", "장기 보유"],
    "16_손절_컷.png": ["손절", "정리"],
    "17_익절각_매도.png": ["차익실현", "익절", "매도"],
    "18_테마주탑승_로켓.png": ["테마주", "급등주", "로켓"],
    "19_FOMO_추격매수.png": ["추격매수", "포모", "FOMO"],
    "20_깜짝성장_실적호조.png": ["호실적", "실적호조", "깜짝", "어닝 서프라이즈"],
    "21_소비심리추락_불안.png": ["소비심리", "불안", "우려"],
    "22_유가비상_원유급등.png": ["원유", "유가 급등"],
    "23_총파업_초읽기.png": ["파업", "초읽기"],
    "24_연준혼돈_금리불확실.png": ["연준", "금리 불확실"],
    "25_애플깜짝성장_실적호조.png": ["애플", "호실적"],
    "26_반도체급등_로켓상승.png": ["반도체 급등", "샌디스크", "급등", "로켓"],
    "27_AI계약_승인.png": ["AI 계약", "AI 네트워크", "AI 시장", "국방부", "AI"],
    "28_폭락_패닉하락.png": ["폭락", "패닉"],
    "29_유가하락_오일약세.png": ["유가 하락", "유가하락"],
    "30_랠리_상승파티.png": ["랠리", "연속 상승", "상승 마감"],
    "31_매파_금리압박.png": ["매파", "금리 인상"],
    "32_매파동결_국채금리급등.png": ["국채", "국채금리"],
    "33_유가급등_이란봉쇄.png": ["이란"],
    "34_내부분열_의견갈등.png": ["분열", "의견 차이"],
    "35_돈태운다_현금소각.png": ["현금 소각", "손실", "적자"],
    "36_클라우드상승_성장.png": ["클라우드", "성장"],
    "37_검색강세_트렌드상승.png": ["검색", "트렌드", "구글"],
    "38_혼조세_증시갈림길.png": ["혼조", "엇갈", "갈림길"],
    "39_목표미달_AI수익성우려.png": ["목표 미달", "수익성", "부진"],
    "40_실적대기_발표긴장.png": ["실적 발표", "대기", "앞두고"],
    "41_반도체매도_주가하락.png": ["반도체 약세", "반도체 하락"],
    "42_유가111달러_호르무즈위기.png": ["호르무즈", "유가"],
    "43_UAE탈퇴_OPEC불확실.png": ["OPEC", "오펙", "탈퇴"],
    "44_평화협상_중동긴장완화.png": ["평화", "중동", "협상"],
    "45_금리동결_FED기준금리.png": ["금리 동결", "기준금리", "금리"],
    "46_사상최고치_지수신고가.png": ["사상 최고", "최고치", "신고가"],  # "최장"(기간)은 "최고치"(수준)와 다른 개념
    "47_협상교착_호르무즈긴장.png": ["교착", "긴장"],
    "48_특사취소_전화협상.png": ["특사", "전화"],
    "49_반도체18연속상승_강세마감.png": ["강세 마감", "연속 상승"],
    # 특정 종목명·수치가 그려진 이미지 — 일반어로 매칭하면 다른 종목 기사에 잘못 붙는다
    "50_포테크놀로지폭락_47퍼센트하락.png": ["포 테크놀로지", "포테크놀로지"],
    "51_퀄컴오픈AI협력설_AI협업.png": ["협력", "협업", "퀄컴", "오픈AI"],
    "52_글로벌금리결정대기_중앙은행회의.png": ["중앙은행", "통화정책"],
    "53_60일만료_전쟁권한법시한.png": ["시한", "만료"],
    "54_다크이글배치_극초음속미사일.png": ["미사일", "배치"],
    "55_6500톤수령_군수물자지원.png": ["군수", "지원"],
    "56_아이언빔배치_UAE군사협력.png": ["군사", "방산"],
    "57_여행금지_UAE긴급조치.png": ["여행 금지", "긴급"],
    "58_봉쇄지속_유가급등.png": ["봉쇄"],
    "59_연쇄타격_물가환율압박.png": ["물가", "환율", "인플레이션"],
    "60_카운트제외_휴전기간논리.png": ["휴전"],
}

FALLBACK_CATEGORIES: list[tuple[tuple[str, ...], str]] = [
    (("급락", "폭락", "추락", "하락", "떨어", "내렸", "감소", "약세"), "04_나도울고싶어_하락.png"),
    (("상승", "올랐", "증가", "강세", "개선", "좋은"), "09_가즈아_상승.png"),
    (("발표", "기록", "밝혔", "전망", "신호"), "05_분석중_차트.png"),
]
NEUTRAL_ROTATION = ["01_정독중_리포트.png", "05_분석중_차트.png", "12_리포트작성_공부.png", "06_움직임없음_관망.png"]
# 1% 미만·"소폭" 변동에 "가즈아"·울상 같은 과장 이미지가 붙지 않도록 완만한 이미지로 대체
MILD_UP = "03_굿굿_칭찬.png"
MILD_DOWN = "06_움직임없음_관망.png"
CLOSING_CHOICES = ["07_승인완료_도장.png", "12_리포트작성_공부.png"]
# 거의 같은 그림 — 한 영상에서 하나만 쓴 것으로 취급
SIMILAR_FAMILIES = [{"20_깜짝성장_실적호조.png", "25_애플깜짝성장_실적호조.png"}]
_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def _keywords_for(filename: str) -> list[str]:
    stem_parts = Path(filename).stem.split("_")[1:]
    return list(dict.fromkeys(EMOTICON_KEYWORDS.get(filename, []) + stem_parts))


def _norm(text: str) -> str:
    return text.replace(" ", "").lower()


def best_match(text: str, exclude: str | set[str] | None = None) -> tuple[str, str] | None:
    """(filename, 대표 keyword). 점수 = 매칭된 keyword 길이 합, 동점이면 파일 순서."""
    flat = _norm(text)
    skip = {exclude} if isinstance(exclude, str) else (exclude or set())
    best: tuple[int, str, str] | None = None
    for filename in EMOTICON_KEYWORDS:
        if filename in skip:
            continue
        hits = [kw for kw in _keywords_for(filename) if len(_norm(kw)) >= 2 and _norm(kw) in flat]
        if not hits:
            continue
        score = sum(len(_norm(kw)) for kw in hits)
        if best is None or score > best[0]:
            best = (score, filename, max(hits, key=lambda k: len(_norm(k))))
    return (best[1], best[2]) if best else None


def mild_move(text: str) -> str | None:
    """작은 변동 문장이면 완만한 이미지 파일명. 1% 이상 수치가 하나라도 있으면 None."""
    tone = sentence_tone(text)
    if tone == "neutral":
        return None
    pcts = [float(x) for x in _PCT.findall(text)]
    if ("소폭" in text and not pcts) or (pcts and max(pcts) < 1.0):
        return MILD_UP if tone == "up" else MILD_DOWN
    return None


def choose_emoticon(text: str, index: int, exclude: str | set[str] | None = None) -> tuple[str, str]:
    """keyword → 감성 fallback → neutral 순환. exclude를 모두 피할 수 없으면 neutral 순환 그대로 반환."""
    skip = {exclude} if isinstance(exclude, str) else (exclude or set())
    hit = best_match(text, exclude=skip)
    if hit:
        return hit
    for triggers, filename in FALLBACK_CATEGORIES:
        if filename not in skip and any(t in text for t in triggers):
            return filename, ""
    for k in range(len(NEUTRAL_ROTATION)):
        filename = NEUTRAL_ROTATION[(index + k) % len(NEUTRAL_ROTATION)]
        if filename not in skip:
            return filename, ""
    return NEUTRAL_ROTATION[index % len(NEUTRAL_ROTATION)], ""


def _with_family(files: set[str]) -> set[str]:
    out = set(files)
    for fam in SIMILAR_FAMILIES:
        if fam & files:
            out |= fam
    return out


def _sentence_spans(segments: list[dict], hints: list[str] | None) -> list[tuple[dict, str]]:
    """자막 segment를 문장 단위 visual span으로 묶는다 (pause로 쪼개진 문장 조각을 다시 합침).

    스토리보드 hint가 바뀌는 곳(컷 경계)에서는 문장 중간이어도 끊는다.
    """
    spans: list[tuple[dict, str]] = []
    cur: dict | None = None
    cur_hint = ""
    for i, seg in enumerate(segments):
        hint = (hints[i] if hints and i < len(hints) else "") or ""
        if cur is not None and hint != cur_hint:
            spans.append((cur, cur_hint))
            cur = None
        if cur is None:
            cur, cur_hint = {"startMs": seg["startMs"], "text": seg["text"]}, hint
        else:
            cur["text"] += " " + seg["text"]
        if ends_sentence(seg["text"]):
            spans.append((cur, cur_hint))
            cur = None
    if cur is not None:
        spans.append((cur, cur_hint))
    return spans


def _merge_closing(spans: list[tuple[dict, str]], closing_text: str) -> list[tuple[dict, str]]:
    """CTA("질문? 댓글 요청.")가 여러 문장이면 끝쪽 span들을 하나로 합쳐 이미지 1장으로 보여 준다."""
    if not closing_text:
        return spans
    k = len(spans)
    while k > 0 and not spans[k - 1][1] and _norm(spans[k - 1][0]["text"]) in _norm(closing_text):
        k -= 1
    if len(spans) - k < 2:
        return spans
    merged = {"startMs": spans[k][0]["startMs"], "text": " ".join(sp["text"] for sp, _ in spans[k:])}
    return spans[:k] + [(merged, "")]


def plan_cues(
    segments: list[dict],
    audio_duration_ms: int,
    hints: list[str] | None = None,
    start_ms: int | None = None,
    closing_text: str = "",
) -> list[dict]:
    """문장 span마다 cue 1개. 표시 구간은 다음 span 시작(또는 오디오 끝)까지.

    hints[i]가 있으면(스토리보드 `화면 연출`) segment 텍스트보다 먼저 매칭한다 (직전과 같을 때만 교체).
    그 외에는 한 영상에서 이미 쓴 이미지(비슷한 그림 family 포함)를 피한다:
    closing_text와 같은 마지막 문장(CTA)은 CLOSING_CHOICES, 작은 변동(소폭, 1% 미만)은 완만한 이미지,
    그 외 keyword → 감성 fallback → neutral 순환. 피할 후보가 없으면 직전과만 다르게 재사용한다.
    start_ms: 첫 cue를 이 시점부터 보여 준다 (오프닝 구간도 첫 문장 이미지로 채움).
    """
    spans = _merge_closing(_sentence_spans(segments, hints), closing_text)
    cues: list[dict] = []
    prev_file: str | None = None
    used: set[str] = set()
    for i, (span, hint) in enumerate(spans):
        text = span["text"]
        hit = best_match(hint) if hint else None
        blocked = _with_family(used)
        is_closing = bool(closing_text) and i == len(spans) - 1 and (
            _norm(text) in _norm(closing_text) or _norm(closing_text) in _norm(text))
        closing = next((f for f in CLOSING_CHOICES if f not in blocked), None) if is_closing else None
        mild = mild_move(text)
        if hit:
            filename, keyword = hit
        elif closing:
            filename, keyword = closing, ""
        elif mild and mild not in blocked:
            filename, keyword = mild, ""
        else:
            filename, keyword = choose_emoticon(text, i, exclude=blocked)
        if filename == prev_file:
            filename, keyword = choose_emoticon(hint or text, i + 1, exclude=_with_family(used | {prev_file}))
            if filename == prev_file:
                filename, keyword = choose_emoticon(hint or text, i + 1, exclude=prev_file)
        end = spans[i + 1][0]["startMs"] if i + 1 < len(spans) else audio_duration_ms
        begin = start_ms if (i == 0 and start_ms is not None) else span["startMs"]
        cues.append({
            "startMs": begin,
            "durationMs": max(1, end - begin),
            "emoticonFileName": f"{EMOTICON_DIR}/{filename}",
            "keyword": keyword,
            "assetKind": "emoticon",
            "visualMode": "emoticon",
        })
        prev_file = filename
        used.add(filename)
    return cues


COMPANY_LOGO_DURATION_MS = 2000


def plan_company_logo_cues(words: list, company_dir: Path, skip_before_ms: int = 0) -> list[dict]:
    """`company/<이름>.png`가 있으면 그 이름이 처음 언급되는 단어 시점에 로고 cue. 파일 없으면 빈 목록."""
    if not company_dir.is_dir():
        return []
    logos = {p.stem: p.name for p in sorted(company_dir.glob("*.png"))}
    cues: list[dict] = []
    for name, filename in logos.items():
        for w in words:
            if w.start >= skip_before_ms and name.lower() in w.text.lower():
                cues.append({"startMs": w.start, "durationMs": COMPANY_LOGO_DURATION_MS, "logoFileName": f"company/{filename}", "name": name})
                break
    return sorted(cues, key=lambda c: c["startMs"])


def highlight_keywords(segments: list[dict]) -> list[str]:
    """segment마다 표시 텍스트에 실제 존재하는 keyword 1개 (Captions 강조용)."""
    out: list[str] = []
    for seg in segments:
        hit = best_match(seg["text"])
        if hit and hit[1] in seg["text"] and hit[1] not in out:
            out.append(hit[1])
    return out


def keyword_tones(keywords: list[str]) -> dict[str, str]:
    """강조 keyword별 색상 톤 (상승=빨강, 하락=파랑, 그 외 노랑). neutral은 생략."""
    return {kw: tone for kw in keywords if (tone := sentence_tone(kw)) != "neutral"}
