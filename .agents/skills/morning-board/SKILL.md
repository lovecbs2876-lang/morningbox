---
name: morning-board
description: 아침 화면 만들기. 연합뉴스 RSS에서 뉴스 3건, open-meteo에서 오늘 예보를 가져와 news.md·weather.md·weather_alert.md로 저장하고, Design.md 기준대로 dashboard.html 한 장을 만들어 화면에 띄운다. 사용자가 /morning-board 라고 하면 사용한다.
---

# morning board

`/morning-board` 가 불리면 아래 순서를 그대로 따른다. 물어보지 말고 끝까지 진행하고, 마지막에 결과만 알린다.

## 바꿀 수 있는 값 (사용자가 따로 말하지 않으면 이 값)

| 항목 | 값 |
|---|---|
| 관심 낱말 | 추석 |
| 지역 | 화성시 동탄신도시 청계동 (북위 37.19, 동경 127.11) |
| 비 올 확률 기준 | 60% 이상 |
| 최저 기온 기준 | 18℃ 이하 |
| 뉴스 RSS | https://www.yna.co.kr/rss/news.xml |

사용자가 인자로 다른 낱말·지역·기준을 주면 그 값을 쓴다. 지역을 바꾸면 좌표도 바꾼다. open-meteo 지오코딩에는 한국의 동 단위가 거의 없으니, 안 나오면 대략적인 좌표를 직접 넣고 그 사실을 알린다.

## 지킬 것

- 만드는 파일은 전부 이 폴더(morningbox) 안에만 둔다. 밖의 폴더는 건드리지 않는다.
- 열쇠(토큰·키)가 필요한 단계가 있으면 이 폴더의 `.env`를 읽어서 쓴다. 열쇠 값은 화면·파일·답변 어디에도 적지 않는다. (아래 순서에는 열쇠가 필요한 단계가 없다. 사용자가 텔레그램 등으로 보내 달라고 할 때만 `.env`를 쓴다.)
- 한글 파일은 BOM 없는 UTF-8로 저장한다. PowerShell 5.1에서는 `[IO.File]::WriteAllText(경로, 내용, (New-Object System.Text.UTF8Encoding($false)))` 를 쓰고, `Set-Content`는 쓰지 않는다.
- PowerShell 스크립트에 한글이 들어가면 파일로 저장하지 말고 명령에 직접 넣어 실행한다.

## 순서

### 1. 날씨 → weather.md, weather_alert.md

open-meteo 예보를 받는다. 주소 예:
`https://api.open-meteo.com/v1/forecast?latitude=37.19&longitude=127.11&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Asia%2FSeoul&forecast_days=1`

`weather.md` 형식:

```
# {지역} 오늘 예보 ({YYYY-MM-DD})

- 최고기온: {값}℃
- 최저기온: {값}℃
- 비 올 확률: {값}%

출처: open-meteo.com (좌표 {위도}, {경도} 기준)
```

`weather_alert.md` 는 한 줄만 쓴다. 비 올 확률이 기준 이상이거나 최저 기온이 기준 이하면 `⚠ 기준 넘음`, 아니면 `기준 미달`.

### 2. 뉴스 → news.md

RSS를 받는다. 제목은 CDATA라서 `$_.title.InnerText` 로 읽는다. 응답은 `RawContentStream`을 UTF-8로 풀어서 XML로 읽는다.

- 제목에 관심 낱말이 든 기사를 피드 순서(최신순)대로 3건 고른다. 3건이 안 되면 가장 최근 기사로 채운다.
- 피드는 자주 갱신돼서 이전 기사가 금방 밀려난다. 링크가 필요하니 저장된 news.md를 다시 쓰지 말고, 매번 새로 받아서 쓴다.
- 요약은 RSS `description`에서 맨 앞 `(지역=연합뉴스) 기자이름 = ` 부분을 빼고 쓴다. 문장이 `...`로 잘려 있으면 그대로 둔다.

`news.md` 형식:

```
# 뉴스 3건 (관심 낱말: {낱말})

- [추석] [{제목}]({링크}) (MM-dd HH:mm)
  요약: {요약}
- [최근] ... (낱말이 없어서 채운 기사는 [최근])

출처: 연합뉴스 RSS ({조회 시각})
```

### 3. Design.md → dashboard.html

먼저 `Design.md`를 읽는다. 없으면 여기서 멈추고 「Design.md가 없어서 화면을 못 만들었어요」라고 알린다.

`dashboard.html` 은 `weather.md`, `weather_alert.md`, `news.md` 를 읽어서 채운 한 장짜리 화면이다. 값을 코드에 박지 말고 세 파일에서 읽는다. 색·레이아웃·글자는 Design.md 값을 그대로 쓴다. Design.md가 바뀌었으면 바뀐 값을 따른다. Design.md 값이 화면과 어긋나면 화면을 Design.md에 맞춘다.

구성은 위에서 아래로 두 구역이다.

1. **날씨 상자**: 제목(지역·오늘 예보), 날짜, 최고 기온을 큰 강조색 카드에 크게, 최저 기온·비 올 확률, 그리고 `weather_alert.md` 한 줄. 「⚠ 기준 넘음」이면 강조색 띠로 표시하고, 「기준 미달」이면 강조색 없이 카드색 바탕에 글자색으로 표시한다.
2. **뉴스 3건**: 카드 3개를 세로로. 제목은 링크(새 탭, `rel="noopener"`, 밑줄), 한 줄 요약은 보조 글자색, 그 아래에 시각·출처.

화면 규칙:

- `<meta name="viewport" content="width=device-width, initial-scale=1">` 를 넣고 휴대폰에서 옆으로 넘치지 않게 한다.
- 강조색 위의 흰 글자는 Design.md가 허용한 크기(28px 이상)에만 쓴다.
- 글자 크기는 Design.md의 네 단계만 쓴다.
- 문자열은 HTML로 이스케이프한다(`[System.Net.WebUtility]::HtmlEncode`).
- 외부 글꼴·스크립트·이미지를 불러오지 않는다. CSS는 파일 안에 넣는다.

### 4. 화면 띄우고 확인

1. 내장 브라우저로 `dashboard.html`을 연다. `file:///` 주소에 폴더의 전체 경로를 쓴다.
2. 스크린샷으로 화면을 확인한다.
3. 자바스크립트로 확인한다: 쓰인 글자 크기가 Design.md 네 단계뿐인지, `scrollWidth`가 `innerWidth`를 넘지 않는지.
4. 휴대폰 폭(375px)으로 줄여서 다시 확인하고, 끝나면 반드시 `desktop`으로 되돌린다.
5. 어긋난 곳이 있으면 고치고 다시 확인한다.

### 5. 홈페이지에 올리기

4단계 확인이 끝난 뒤에 한다. 이 폴더에서 실행한다.

1. `dashboard.html` 을 `index.html` 로 복사한다(덮어쓴다).
2. `git add -A` → `git commit -m "갱신"` → `git push`. 바뀐 것이 없으면 그냥 넘어간다.
3. `.gitignore` 가 `.env`·그림 파일을 막고 있으니 `git add -A` 로도 열쇠는 올라가지 않는다. 그래도 커밋 전 `git status` 에 `.env` 가 보이면 멈추고 알린다.
4. push 가 실패하면(로그인 만료 등) 이유를 한 줄로 알리고, 화면 만들기는 끝난 것으로 보고한다.

### 6. 알릴 것

짧게 다음만 알린다.

- 날씨 한 줄(최고·최저·비 확률)과 「기준 넘음/미달」
- 고른 뉴스 3건의 제목
- 지오코딩이 안 돼서 좌표를 직접 넣었다면 그 사실
- 낱말이 든 기사가 3건이 안 돼서 최근 기사로 채웠다면 그 사실
- 만든 파일 이름: `weather.md`, `weather_alert.md`, `news.md`, `dashboard.html`, `index.html`
- 홈페이지에 올렸는지(올렸으면 주소 https://lovecbs2876-lang.github.io/morningbox/ , 바뀐 게 없거나 실패했으면 그 사실). 홈페이지에 반영되기까지 1~2분 걸린다.
