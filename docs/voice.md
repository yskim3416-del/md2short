# Voice 설정

## 기본 Voice ID

v1 한국어 기본 voice는 다음 `voice_id`를 사용한다.

```text
v1jVu1Ky28piIPEJqRrm
```

- 코드 기준: `md2short/schema.py` `DEFAULT_VOICES["ko"]`
- 참고: https://elevenlabs.io/app/voice-library?voiceId=v1jVu1Ky28piIPEJqRrm
## 플랜 제약 (2026-10-26 확인)

- 기본 voice `v1jVu1Ky28piIPEJqRrm`("KKC RADIO")는 Voice Library의 professional 음성이다. ElevenLabs **무료 플랜에서는 API로 쓸 수 없고** `HTTP 402 paid_plan_required`로 실패한다 (Creator 이상 구독 또는 구매 크레딧 필요). 무료 플랜이 매달 주는 크레딧으로는 풀리지 않는다.
- 무료 플랜은 premade 음성을 `--voice`로 지정한다. 브리핑 톤 추천: Daniel `onwK4e9ZLuTAKqWW03F9`(남성, 방송 톤), Matilda `XrExE9yKIg1WjnnlVkGX`(여성, 정보형). premade 음성은 영어권 화자라 `eleven_multilingual_v2`로 한국어를 읽을 때 억양이 다소 외국인처럼 들릴 수 있다.
- 계정에서 쓸 수 있는 음성 목록 조회(`GET /v1/voices`)에는 API 키의 **음성 읽기** 권한이 필요하다. 파이프라인 실행 자체에는 Text to Speech · Speech to Text 접근 권한만 있으면 된다.
