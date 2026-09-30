"""send_kakao.py — 카카오톡 "나에게 보내기" 메시지 전송

최초 1회 설정
-------------
1. https://developers.kakao.com 에서 앱을 만들고 REST API 키를 발급받는다.
2. 앱 설정 > 카카오 로그인 > Redirect URI 에 REDIRECT_URI(기본값 https://localhost:5000)를
   등록하고, 카카오 로그인을 켠다.
3. 카카오 로그인 > 동의항목에서 "카카오톡 메시지 전송"을 신청해 켠다.
4. 이 폴더의 .env 에 아래 줄을 추가한다 (키 값은 화면에 적지 않는다):
       KAKAO_REST_API_KEY=발급받은_REST_API_키
5. 아래 주소의 <REST_API_KEY> 자리에 그 키를 넣어 브라우저로 연다.
       https://kauth.kakao.com/oauth/authorize?client_id=<REST_API_KEY>&redirect_uri=https://localhost:5000&response_type=code
   로그인 후 리디렉션된 주소(https://localhost:5000/?code=...)에서 code= 뒤의 값을 복사한다.
6. 다음처럼 최초 1회만 실행해 토큰을 발급받는다:
       python send_kakao.py --code <복사한 인가 코드>
   성공하면 kakao_token.json 이 만들어진다. 이 코드는 1회용이라 이후엔 쓰지 않는다.

평소 사용
---------
    python send_kakao.py "보낼 메시지"
인자 없이 실행하면 테스트 메시지를 보낸다. 액세스 토큰이 만료돼 있으면 리프레시 토큰으로
자동 갱신한 뒤 다시 보낸다.

열쇠 취급
---------
REST API 키는 .env 에서만 읽고, kakao_token.json 에 저장된 토큰과 함께 어디에도 옮겨
적지 않는다. 두 파일 모두 .gitignore 에 들어 있어 깃에 올라가지 않는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import requests

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
TOKEN_FILE = BASE_DIR / "kakao_token.json"

TOKEN_URL = "https://kauth.kakao.com/oauth/token"
SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
DEFAULT_REDIRECT_URI = "https://localhost:5000"
REQUEST_TIMEOUT = 10


def load_env(path: Path) -> dict:
    """.env 파일을 KEY=VALUE 사전으로 읽는다. 외부 패키지 없이 최소한만 처리한다."""
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


ENV = load_env(ENV_FILE)
REST_API_KEY = ENV.get("KAKAO_REST_API_KEY", "")
REDIRECT_URI = ENV.get("KAKAO_REDIRECT_URI", DEFAULT_REDIRECT_URI)


def require_api_key() -> None:
    if not REST_API_KEY:
        sys.exit(
            "KAKAO_REST_API_KEY 가 .env 에 없어요. developers.kakao.com 에서 REST API 키를 "
            "받아 .env 에 KAKAO_REST_API_KEY=값 형태로 적어 주세요."
        )


def save_tokens(tokens: dict) -> None:
    TOKEN_FILE.write_text(json.dumps(tokens, ensure_ascii=False, indent=2), encoding="utf-8")


def load_tokens() -> Optional[dict]:
    if not TOKEN_FILE.exists():
        return None
    return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))


def get_initial_tokens(auth_code: str) -> dict:
    """최초 인가 코드로 토큰을 발급받아 파일에 저장한다. (최초 1회만 사용)"""
    require_api_key()
    data = {
        "grant_type": "authorization_code",
        "client_id": REST_API_KEY,
        "redirect_uri": REDIRECT_URI,
        "code": auth_code,
    }
    res = requests.post(TOKEN_URL, data=data, timeout=REQUEST_TIMEOUT)
    tokens = res.json()
    if "access_token" not in tokens:
        sys.exit(f"토큰 발급 실패: {tokens}")
    save_tokens(tokens)
    print(f"토큰을 발급받아 {TOKEN_FILE.name} 에 저장했어요.")
    return tokens


def refresh_access_token(tokens: dict) -> Optional[str]:
    """리프레시 토큰으로 만료된 액세스 토큰을 갱신한다."""
    require_api_key()
    data = {
        "grant_type": "refresh_token",
        "client_id": REST_API_KEY,
        "refresh_token": tokens.get("refresh_token", ""),
    }
    res = requests.post(TOKEN_URL, data=data, timeout=REQUEST_TIMEOUT)
    new_tokens = res.json()

    if "access_token" not in new_tokens:
        return None

    tokens["access_token"] = new_tokens["access_token"]
    if "refresh_token" in new_tokens:
        tokens["refresh_token"] = new_tokens["refresh_token"]
    save_tokens(tokens)
    return tokens["access_token"]


def send_message_to_me(text: str) -> bool:
    """나와의 채팅방으로 텍스트를 보낸다. 성공하면 True."""
    tokens = load_tokens()
    if tokens is None:
        sys.exit(
            f"{TOKEN_FILE.name} 이 없어요. 먼저 `python send_kakao.py --code <인가 코드>` 로 "
            "최초 토큰을 받아 주세요."
        )

    payload = {
        "template_object": json.dumps(
            {
                "object_type": "text",
                "text": text,
                "link": {
                    "web_url": "https://developers.kakao.com",
                    "mobile_web_url": "https://developers.kakao.com",
                },
                "button_title": "확인",
            },
            ensure_ascii=False,
        )
    }

    def _post(access_token: str) -> requests.Response:
        headers = {"Authorization": f"Bearer {access_token}"}
        return requests.post(SEND_URL, headers=headers, data=payload, timeout=REQUEST_TIMEOUT)

    res = _post(tokens.get("access_token", ""))
    body = res.json()

    if res.status_code == 401 or body.get("code") == -401:
        new_token = refresh_access_token(tokens)
        if new_token is None:
            sys.exit(
                "토큰 갱신도 실패했어요. `python send_kakao.py --code <인가 코드>` 로 다시 "
                "동의를 받아야 해요."
            )
        res = _post(new_token)
        body = res.json()

    if body.get("result_code") == 0:
        print("카카오톡 전송 완료!")
        return True

    print("전송 실패:", body)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="카카오톡 나에게 보내기")
    parser.add_argument("message", nargs="*", help="보낼 메시지")
    parser.add_argument("--code", help="최초 1회, 인가 코드로 토큰을 발급받는다")
    args = parser.parse_args()

    if args.code:
        get_initial_tokens(args.code)
        return

    text = " ".join(args.message) if args.message else "클로드 코드에서 보낸 테스트 메시지입니다."
    send_message_to_me(text)


if __name__ == "__main__":
    main()
