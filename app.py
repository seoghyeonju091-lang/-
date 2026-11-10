import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timedelta, timezone

import extra_streamlit_components as stx
import streamlit as st
from openai import OpenAI

DATA_FILE = Path(__file__).parent / "guestbook.json"
RETENTION = timedelta(days=3)
COOKIE_NAME = "guestbook_owner_id"
LOCK = threading.Lock()


def now_utc():
    return datetime.now(timezone.utc)


def parse_date(value):
    try:
        dt = datetime.fromisoformat(value)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def read_entries():
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open(encoding="utf-8") as f:
            value = json.load(f)
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def write_entries(entries):
    fd, tmp = tempfile.mkstemp(dir=str(DATA_FILE.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, DATA_FILE)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def remove_expired(entries):
    cutoff = now_utc() - RETENTION
    return [e for e in entries if (d := parse_date(e.get("created_at"))) and d > cutoff]


def owner_for_browser(cookie_manager):
    owner = cookie_manager.get(COOKIE_NAME)
    if isinstance(owner, str) and len(owner) == 32:
        return owner
    owner = uuid.uuid4().hex
    cookie_manager.set(COOKIE_NAME, owner, expires_at=datetime.now() + timedelta(days=365))
    return owner


def moderate(name, message):
    key = st.secrets.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("Streamlit Cloud → Settings → Secrets에 OPENAI_API_KEY를 설정해 주세요.")
    client = OpenAI(api_key=key)
    response = client.moderations.create(
        model="omni-moderation-latest",
        input=f"Nickname: {name}\nGuestbook message: {message}",
    )
    return response.results[0]


def load_and_clean():
    with LOCK:
        entries = read_entries()
        cleaned = remove_expired(entries)
        if len(cleaned) != len(entries):
            write_entries(cleaned)
        return sorted(cleaned, key=lambda e: e.get("created_at", ""), reverse=True)


def add_entry(name, message, owner):
    with LOCK:
        entries = remove_expired(read_entries())
        entries.append({
            "id": uuid.uuid4().hex,
            "name": name,
            "message": message,
            "owner_id": owner,
            "created_at": now_utc().isoformat(),
        })
        write_entries(entries)


def delete_own_entry(entry_id, owner):
    with LOCK:
        entries = remove_expired(read_entries())
        kept = [e for e in entries if not (e.get("id") == entry_id and e.get("owner_id") == owner)]
        changed = len(kept) != len(entries)
        if changed:
            write_entries(kept)
        return changed


st.set_page_config(page_title="온라인 방명록", page_icon="📝", layout="centered")
cookies = stx.CookieManager(key="guestbook_cookie_manager")
owner_id = owner_for_browser(cookies)

st.title("📝 온라인 방명록")
st.caption("모두가 함께 보는 방명록입니다. 글은 작성 후 3일이 지나면 정리됩니다.")

with st.form("guestbook_form", clear_on_submit=True):
    name = st.text_input("닉네임", max_chars=30)
    message = st.text_area("방명록 메시지", max_chars=500, height=130)
    submit = st.form_submit_button("AI 검열 후 등록", type="primary", use_container_width=True)

if submit:
    name, message = name.strip(), message.strip()
    if not name or not message:
        st.warning("닉네임과 메시지를 모두 입력해 주세요.")
    else:
        try:
            with st.spinner("AI가 글을 검열하고 있습니다..."):
                result = moderate(name, message)
            if result.flagged:
                st.error("부적절할 수 있는 표현이 감지되어 등록하지 않았습니다. 표현을 바꿔 주세요.")
            else:
                add_entry(name, message, owner_id)
                st.success("AI 검열을 통과해 글이 등록되었습니다.")
                st.rerun()
        except Exception as exc:
            st.error(f"검열 또는 등록에 실패했습니다. 글은 공개되지 않았습니다. ({exc})")

st.divider()
st.subheader("방명록")
entries = load_and_clean()
if not entries:
    st.info("아직 등록된 글이 없습니다.")
else:
    st.caption(f"공개된 글 {len(entries)}개")
    for entry in entries:
        created = parse_date(entry.get("created_at"))
        date_text = created.astimezone().strftime("%Y-%m-%d %H:%M") if created else "시간 정보 없음"
        with st.container(border=True):
            st.markdown(f"**{entry.get('name', '익명')}**")
            st.caption(date_text)
            st.write(entry.get("message", ""))
            if entry.get("owner_id") == owner_id:
                if st.button("내 글 삭제", key=f"delete_{entry.get('id')}"):
                    if delete_own_entry(entry.get("id"), owner_id):
                        st.success("글을 삭제했습니다.")
                        st.rerun()
                    else:
                        st.warning("삭제할 글을 찾지 못했습니다.")

st.caption("브라우저 쿠키를 삭제하거나 다른 기기를 사용하면 본인 글의 삭제 버튼이 보이지 않을 수 있습니다. 개인정보는 남기지 마세요.")
