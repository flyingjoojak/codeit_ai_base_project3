import streamlit as st
import requests

from config import API_URL, TONE_OPTIONS, ACK_ENDPOINT
from api import poll_job, post_generate
from state import init_state
from utils.text import normalize_keywords
from utils.image import b64_to_bytes,convert_image_bytes, add_image_overlay




init_state()

def render_result(container, result:dict):
    with container:
        st.subheader("결과")

        if not result:
            st.caption("생성 결과가 여기에 표시됩니다.")
            return
        
        copy_data = result.get("copy_data",{})
        if isinstance(copy_data, dict) and copy_data:
            brand = copy_data.get("brand_name","")
            headline = copy_data.get("product_headline", "")
            cta = copy_data.get("cta_text","")

            if brand:
                st.markdown(f"**브랜드명**: {brand}")
            if headline:
                st.markdown(f"**헤드라인**: {headline}")
            if cta:
                st.markdown(f"**CTA**: {cta}")
        else:
            st.caption("카피 데이터가 없습니다.")

        img_b64 = result.get("final_image")
        if not img_b64:
            st.warning("result.final_image(base64)가 없습니다.")
            return

        src_bytes = b64_to_bytes(img_b64)
        final_bytes = st.session_state.get("edited_bytes", src_bytes)

        st.image(final_bytes, use_container_width=True)

        out_fmt = st.selectbox("다운로드 형식", ["png", "jpg","jpeg"], index=0, key="output_format")
        out_bytes, mime = convert_image_bytes(final_bytes, out_fmt)

        st.download_button(
            f"{out_fmt.upper()} 다운로드",
            data = out_bytes,
            file_name=f"ad_widget.{out_fmt}",
            mime = mime,
            use_container_width=True
        )
def render_editor(col, result:dict):
        with col:
            st.subheader("이미지 편집(선택)")

            if not result:
                st.caption("결과가 생성되면 편집할 수 있어요.")
                return
            img_b64 = result.get("final_image")
            if not img_b64:
                st.caption("편집할 이미지가 없습니다.")
                return
            src_bytes = b64_to_bytes(img_b64)

            overlay_file = st.file_uploader(
                "추가 이미지 업로드(로고/스티커)",
                type=["png","jpg","jpeg"],
                key="overlay_uploader"
            )

            scale = st.slider("크기", 0.10, 0.60, 0.25, 0.01, key="overlay_scale")
            x_ratio = st.slider("가로위치", 0.0, 1.0, 1.0, 0.01, key="overlay_x")
            y_ratio = st.slider("세로위치", 0.0, 1.0, 0.0, 0.01, key="overlay_y")
            opacity = st.slider("투명도", 0.0, 1.0, 1.0, 0.05, key="overlay_opacity")

            btn_apply, btn_reset = st.columns(2)

            with btn_apply:
                if st.button("적용", use_container_width=True):
                    if overlay_file is None:
                        st.warning("추가 이미지를 업로드해주세요.")
                    else:
                        overlay_bytes = overlay_file.getvalue()
                        edited = add_image_overlay(
                            base_bytes=src_bytes,
                            overlay_bytes=overlay_bytes,
                            scale = scale,
                            x_ratio=x_ratio,
                            y_ratio=y_ratio,
                            opacity=opacity
                        )
                        st.session_state["edited_bytes"] = edited
                        st.success("적용 완료.")
                        st.rerun()
            with btn_reset:
                if st.button("되돌리기", use_container_width=True):
                    st.session_state.pop("edited_bytes", None)
                    st.success("원본으로 되돌렸습니다.")
                    st.rerun()


st.set_page_config(
    layout="centered",
    page_title="광고 위젯 생성",
    page_icon="📣",
)
st.title("광고 위젯 생성")
st.caption("Ad Widget Generator")

with st.sidebar:
    st.header("선택 설정")
    tone = st.selectbox("분위기", TONE_OPTIONS, index=TONE_OPTIONS.index(st.session_state["tone"]), key="tone")

    layout_label = st.selectbox("레이아웃", ["세로형","가로형"], index=0, key="layout_label")
    layout_map = {"세로형": "vertical", "가로형": "horizontal"}
    st.session_state["layout"] = layout_map[layout_label]




st.subheader("필수 입력")
st.info("제품 이미지/제품명을 입력해주세요. (사이즈/분위기는 왼쪽 사이드에서 설정할 수 있습니다.")

uploaded= st.file_uploader("상품 이미지", type=["png","jpg","jpeg"],key="image_uploader")

if uploaded is not None:
    st.session_state["image_bytes"] = uploaded.getvalue()
    st.session_state["image_name"] = uploaded.name
    st.session_state["image_type"] = uploaded.type

if st.session_state.get("image_bytes"):
    st.success(f"이미지 업로드됨:{st.session_state.get('image_name')}")
else:
    st.warning("아직 이미지가 업로드되지 않았습니다.")

st.text_input("상품명", key="product_name")
st.text_input("핵심 키워드(쉼표로 구분)", placeholder="예:행사,1+1,선물추천",key="keywords_raw")

generate_clicked = st.button("위젯 생성", use_container_width=True)

progress_holder = st.empty()
status_holder = st.empty()

progress_bar = progress_holder.progress(0)


if generate_clicked:
    if not st.session_state.get("image_bytes"):
        status_holder.warning("상품 이미지를 업로드해주세요.")
    elif not st.session_state["product_name"].strip():
        status_holder.warning("상품명을 입력해주세요.")
    elif not st.session_state["keywords_raw"].strip():
        status_holder.warning("키워드를 입력해주세요.")
    else:
        st.session_state.pop("edited_bytes", None)
        progress_bar.progress(0)
        status_holder.info("요청 준비 중")

        try:
            keywords_str = normalize_keywords(st.session_state["keywords_raw"])
            tone_value = st.session_state["tone"]
            layout_value = st.session_state["layout"]

            status_holder.info("생성 요청 중")
            payload = post_generate(
                image_name=st.session_state["image_name"],
                image_bytes=st.session_state["image_bytes"],
                image_type=st.session_state["image_type"],
                product_name=st.session_state["product_name"].strip(),
                keywords_str=keywords_str,
                tone_ko=tone_value,
                layout = layout_value
            )

            task_id = payload.get("task_id")
            if task_id:
                st.session_state["last_task_id"] = task_id

            if not task_id:
                status_holder.error("요청 접수에 실패했어요. 잠시 후 다시 시도해주세요.")
            else:
                final_payload = poll_job(task_id, progress_bar=progress_bar, status_holder=status_holder)
                st.session_state["result"] = final_payload.get("result", {})

                try:
                    ack_url = f"{API_URL}{ACK_ENDPOINT}".format(task_id=task_id)
                    ack_res = requests.post(ack_url, timeout=10)
                    ack_res.raise_for_status()
                    ack_json = ack_res.json()
                    if not ack_json.get("ok", False):
                        status_holder.warning(f"서버 정리(ACK) 실패: {ack_json.get('error','unknown')}")
                except Exception:
                    status_holder.warning("서버 정리(ACK) 요청이 실패했어요.")


        except requests.HTTPError as e:
            status_holder.error(f"HTTP 오류: {e.response.status_code}")
            st.write(e.response.text)
        except Exception as e:
            status_holder.error(f"생성에 실패했어요. 잠시 후 다시 시도해주세요.")
            with st.expander("접수번호(담당자에게 전달)"):
                st.code(st.session_state.get("last_task_id","없음"))

st.divider()
result_col, edit_col = st.columns([1.4,1.0], gap="large")

render_result(result_col, st.session_state.get("result"))
render_editor(edit_col, st.session_state.get("result"))













