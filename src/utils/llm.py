from langchain_core.messages import SystemMessage, HumanMessage
from src.container import Container
from src.utils.logger import get_logger
from langchain_openai import AzureChatOpenAI
import base64
import mimetypes

logger = get_logger(__name__)

def generate_text(model : AzureChatOpenAI, system_prompt: str, user_prompt: str, detail_prompt: str, image_byte_array=None):
    try:
        if image_byte_array:
            image_url = get_image_url_from_bytea(image_byte_array)
            
            logger.info(f"[LLM] 이미지 URL: {image_url[:100]}")
            
            human_message = HumanMessage(content=[
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": image_url, "detail": detail_prompt}},
            ])
            logger.debug("[LLM] 이미지 입력 포함 호출")
        else:
            human_message = HumanMessage(content=[
                {"type": "text", "text": user_prompt},
            ])            
            
        if model:
            # 로깅을 위해 프롬프트 일부 출력 (너무 길면 잘림)
            log_prompt = user_prompt[:100].replace('\n', ' ')
            logger.info(f"[LLM] 생성 요청: {log_prompt}...")
            
            response = model.invoke([
                SystemMessage(content=system_prompt),
                human_message
            ])
            #raw = response.choices[0].message.content.strip()
            raw = response.content.strip()
            clean_text = raw[:100].replace('\n', ' ')
            logger.info(f"[LLM] 생성 응답: {clean_text}...")
            
            return raw
    except Exception as e:
        logger.error(f"[LLM] 텍스트 생성 중 오류: {e}", exc_info=True)
        return ""
    return ""


def get_image_url_from_bytea(image_data):
    # 주석 앞에 r을 붙여 Raw String으로 선언합니다.
    r"""
    SAM 결과물(Hex String \x...)을 포함하여 다양한 이미지를 
    LLM용 Data URL(Base64)로 변환합니다.
    """
    if not image_data:
        return ""

    image_bytes = b""

    # 1. 데이터 타입 정규화
    try:
        if isinstance(image_data, bytes):
            image_bytes = image_data
        elif isinstance(image_data, memoryview):
            image_bytes = image_data.tobytes()
        elif isinstance(image_data, str):
            # 문자열 비교 시에도 r을 붙여 \x를 안전하게 처리합니다.
            if image_data.startswith(r'\x'):
                # 헥사 문자열을 바이트로 변환
                image_bytes = bytes.fromhex(image_data[2:])
            else:
                try:
                    image_bytes = base64.b64decode(image_data)
                except Exception:
                    image_bytes = image_data.encode('latin-1', errors='ignore')
    except Exception as e:
        logger.error(f"변환 오류: {e}")
        return ""

    if not image_bytes:
        return ""

    # 2. MIME Type 감지
    mime_type = "image/jpeg" # 기본값

    if image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        mime_type = "image/png"
    elif image_bytes.startswith(b'\xff\xd8'):
        mime_type = "image/jpeg"
    elif image_bytes.startswith(b'RIFF') and len(image_bytes) > 12 and image_bytes[8:12] == b'WEBP':
        mime_type = "image/webp"
    elif image_bytes.startswith(b'GIF8'):
        mime_type = "image/gif"
    else:
        # SAM 결과물은 대부분 PNG이므로 fallback을 png로 설정
        mime_type = "image/png"

    # 3. 최종 Base64 인코딩
    base64_str = base64.b64encode(image_bytes).decode('utf-8')
    
    return f"data:{mime_type};base64,{base64_str}"