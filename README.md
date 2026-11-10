# 온라인 임시 방명록

GitHub + Streamlit Community Cloud로 배포하는 공용 임시 방명록 예제입니다.

## 기능
- 모든 방문자가 같은 방명록 목록을 봅니다.
- OpenAI Moderation API로 닉네임과 메시지를 검사합니다.
- 검열 API에 연결할 수 없으면 글을 등록하지 않는 fail-closed 방식입니다.
- 글은 작성 시각 기준 3일이 지나면 다음 앱 접근/실행 때 정리됩니다.
- 데이터베이스 없이 `guestbook.json` 파일을 사용합니다.

## 실행 준비

1. Python 환경에서 설치:
   ```bash
   pip install -r requirements.txt
   ```
2. `.streamlit/secrets.toml.example`을 복사해 `.streamlit/secrets.toml`로 이름을 바꿉니다.
3. 파일 안의 `OPENAI_API_KEY` 값을 본인의 API 키로 바꿉니다.
4. 실행:
   ```bash
   streamlit run app.py
   ```

## Streamlit Community Cloud 배포

1. 이 프로젝트를 GitHub 저장소에 업로드합니다.
2. Streamlit Community Cloud에서 저장소와 `app.py`를 선택해 앱을 배포합니다.
3. 앱의 Settings → Secrets에 다음 내용을 입력합니다.
   ```toml
   OPENAI_API_KEY = "실제_API_키"
   ```
4. 저장 후 앱을 재시작합니다.

## 중요한 한계

- Streamlit Community Cloud의 로컬 파일 시스템은 영구 저장소가 아닙니다. 앱 재시작, 재배포, 인스턴스 교체 등으로 `guestbook.json`이 사라질 수 있습니다.
- 따라서 이 프로젝트는 글이 사라져도 괜찮은 이벤트성/시험용 방명록에 적합합니다.
- 3일 만료는 정확히 만료 시각에 백그라운드에서 실행되는 방식이 아닙니다. 앱에 접속하거나 실행 흐름이 돌아갈 때 만료 글을 정리합니다.
- 앱이 여러 실행 인스턴스로 확장되면 각 인스턴스의 로컬 파일이 서로 다를 수 있습니다. 데이터베이스 없이 모든 사용자에게 항상 동일한 데이터를 보장할 수는 없습니다.
- 코드에는 같은 프로세스 안의 동시 파일 쓰기를 줄이기 위한 잠금과 원자적 파일 교체가 포함되어 있지만, 여러 인스턴스 간 동기화는 제공하지 않습니다.
- 공개 방명록이므로 개인정보를 입력하지 않도록 안내하고, 악성 이용이나 과도한 요청에 대비한 추가 제한이 필요할 수 있습니다.
- AI 검열은 완벽하지 않습니다. 문맥에 따른 오탐/누락이 있을 수 있습니다.
- OpenAI API 사용에는 별도 API 요금이 발생할 수 있습니다.

## 보안
- 실제 API 키를 GitHub에 올리지 마세요.
- `.streamlit/secrets.toml`과 `guestbook.json`은 `.gitignore`에 포함되어 있습니다.
