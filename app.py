import json
import os
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import contextmanager

import streamlit as st
from openai import OpenAI

APP_DIR = Path(__file__).parent
DATA_FILE = APP_DIR / "guestbook.json"
RETENTION = timedelta(days=3)
MAX_NAME_LENGTH = 30
MAX_MESSAGE_LENGTH = 500

# Protects simultaneous writes within the app process.
_FILE_LOCK = threading.Lock()


def utc_now():
    return datetime.now(timezone.utc)


def parse_timestamp(value):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def read_entries():
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        # Do not overwrite a file that could not be read safely.
        return []


def write_entries(entries):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix="guestbook_", suffix=".tmp", dir=str(DATA_FILE.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_name, DATA_FILE)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def prune_expired(entries):
    cutoff = utc_now() - RETENTION
    kept = []
    for entry in entries:
        created = parse_timestamp(entry.get("created_at"))
        if created is not None and created > cutoff:
            kept.append(entry)
    return kept


def get_entries_and_cleanup():
    with _FILE_LOCK:
        entries = read_entries()
        kept = prune_expired(entries)
        if len(kept) != len(entries):
            write_entries(kept)
        return sorted(kept, key=lambda x: x.get("created_at", ""), reverse=True)


def moderate_text(name, message):
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "관리자가 OpenAI API 키를 설정하지 않았습니다. 잠시 후 다시 이용해 주세요."
        )

    client = OpenAI(api_key=api_key)
    result = client.moderations.create(
        model="omni-moderation-latest",
        input=f"Nickname: {name}\nGuestbook message: {message}",
    )
    return result.results[0]


def save_entry(name, message):
    with _FILE_LOCK:
        entries = read_entries()
        entries = prune_expired(entries)
        entries.append({
            "name": name,
            "message": message,
            "created_at": utc_now().isoformat(),
        })
        write_entries(entries)


st.set_page_config(
    page_title="온라인 방명록",
    page_icon="📝",
    layout="centered",
)

st.title("📝 온라인 방명록")
st.caption("따뜻한 인사를 남겨 주세요. 등록된 글은 3일 후 자동으로 정리됩니다.")

with st.form("guestbook_form", clear_on_submit=True):
    name = st.text_input("닉네임", max_chars=MAX_NAME_LENGTH, placeholder="닉네임")
    message = st.text_area(
        "방명록 메시지",
        max_chars=MAX_MESSAGE_LENGTH,
        height=130,
        placeholder="방명록에 남길 말을 작성해 주세요.",
    )
    submitted = st.form_submit_button("검열 후 등록", type="primary", use_container_width=True)

if submitted:
    clean_name = name.strip()
    clean_message = message.strip()

    if not clean_name or not clean_message:
        st.warning("닉네임과 메시지를 모두 입력해 주세요.")
    elif len(clean_name) > MAX_NAME_LENGTH or len(clean_message) > MAX_MESSAGE_LENGTH:
        st.warning("입력 글자 수 제한을 확인해 주세요.")
    else:
        try:
            with st.spinner("AI가 메시지를 확인하고 있습니다..."):
                moderation = moderate_text(clean_name, clean_message)

            if moderation.flagged:
                st.error("부적절할 수 있는 표현이 감지되어 글을 등록하지 않았습니다. 표현을 바꿔 다시 작성해 주세요.")
            else:
                save_entry(clean_name, clean_message)
                st.success("방명록이 등록되었습니다!")
                st.rerun()
        except Exception as exc:
            # Fail closed: if moderation cannot run, do not publish the message.
            st.error(f"검열 또는 등록 과정에서 문제가 발생했습니다: {exc}")

st.divider()
st.subheader("방명록")

entries = get_entries_and_cleanup()

if not entries:
    st.info("아직 등록된 방명록이 없습니다. 첫 번째 인사를 남겨 보세요!")
else:
    st.caption(f"현재 공개된 글 {len(entries)}개 · 작성 후 3일이 지나면 자동 삭제")
    for entry in entries:
        created = parse_timestamp(entry.get("created_at"))
        if created:
            local_created = created.astimezone()
            date_label = local_created.strftime("%Y-%m-%d %H:%M")
        else:
            date_label = "작성 시간 정보 없음"

        with st.container(border=True):
            st.markdown(f"**{entry.get('name', '익명')}**")
            st.caption(date_label)
            st.write(entry.get("message", ""))

st.caption("안내: 공개 방명록이므로 개인 연락처, 주소 등 민감한 개인정보는 남기지 마세요.")
