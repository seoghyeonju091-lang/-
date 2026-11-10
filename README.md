# 온라인 임시 방명록 v2

## 기능
- 모든 방문자가 공용 방명록을 봅니다.
- OpenAI Moderation API(`omni-moderation-latest`)로 닉네임과 메시지를 검사합니다.
- 검열 API 오류 시 게시하지 않습니다.
- 글은 작성 시각부터 3일이 지난 뒤 앱 접근/실행 시 정리됩니다.
- 브라우저 쿠키의 임의 ID로 작성자를 구분해 같은 브라우저에서 작성한 글에 삭제 버튼을 표시합니다.
- 별도 데이터베이스 없이 JSON 파일을 사용합니다.

## 실행
1. `pip install -r requirements.txt`
2. `.streamlit/secrets.toml.example`을 `.streamlit/secrets.toml`로 복사하고 실제 API 키 입력
3. `streamlit run app.py`

## Streamlit Cloud 배포
1. 파일을 GitHub 저장소에 업로드
2. Streamlit Community Cloud에서 저장소와 `app.py`를 선택해 배포
3. 앱 Settings → Secrets에 `OPENAI_API_KEY = "실제_API_키"` 입력
4. 저장 후 앱 재시작

## 중요한 한계
- 브라우저 쿠키를 삭제하거나 다른 기기를 사용하면 본인 글의 삭제 버튼이 보이지 않을 수 있습니다.
- 쿠키 기반 식별은 편의 기능이지 강력한 인증이 아닙니다. 쿠키를 복사/조작할 수 있는 사용자는 식별값을 흉내 낼 수 있습니다.
- Streamlit Cloud 로컬 파일은 영구 저장소가 아니므로 재시작/재배포/인스턴스 교체 시 데이터가 사라질 수 있습니다.
- 여러 앱 인스턴스 간 파일 동기화가 되지 않으므로 공용 데이터가 항상 일치한다고 보장할 수 없습니다.
- 파일 잠금은 같은 프로세스 안의 동시 쓰기만 완화합니다.
- 3일 자동 정리는 만료 시각에 백그라운드 실행되는 것이 아니라 앱 실행/접속 시 수행됩니다.
- AI 검열은 완벽하지 않으며 오탐/누락이 있을 수 있습니다. API 사용료가 발생할 수 있습니다.

## 보안
실제 API 키를 GitHub에 올리지 마세요. `.streamlit/secrets.toml`과 `guestbook.json`은 `.gitignore`에 포함되어 있습니다.
