import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.utils.db import Database
from src.utils.logger import get_logger
from src.model.schema import ApprovedReport

logger = get_logger(__name__)


async def _get_agent_email(p_trademark_reg_no: str) -> str | None:
    """
    보호 상표 번호로 담당 변리사 이메일을 조회
    """
    pool = await Database.get_pool()
    
    query = """
        SELECT c.agent_email
          FROM tbl_protection_trademark a,
               tbl_customer_info b,
               tbl_patent_attorney c
         WHERE a.p_trademark_reg_no = $1
           AND a.p_trademark_user_no = b.customer_no
           AND c.agent_id = b.agent_id
    """
    
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, p_trademark_reg_no)
            
        if not row:
            logger.warning(f"[이메일] 담당 변리사 이메일을 찾을 수 없음 (등록번호: {p_trademark_reg_no})")
            return None
            
        return row["agent_email"]
        
    except Exception as e:
        logger.error(f"[이메일] DB 조회 오류: {e}")
        return None


def _build_email_body(approved_reports: list[ApprovedReport], p_trademark_name: str) -> str:
    """보호 상표 1건에 대한 승인된 보고서 N건을 하나의 메일 본문으로 구성"""
    try:
        reports_html = ""
        for idx, report in enumerate(approved_reports, 1):
            formatted_content = report.report_content.replace("\n", "<br>")
            reports_html += f"""
            <div style="margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; border-radius: 5px;">
                <h3>#{idx}. 침해 의심 상표: {report.c_trademark_name}</h3>
                <p>위험도: <strong>{report.risk_level}</strong> | 종합 점수: <strong>{report.total_score}</strong></p>
                <hr/>
                <div style="background-color: #f9f9f9; padding: 10px; font-family: monospace;">
                    {formatted_content}
                </div>
            </div>
            """
        
        return f"""
        <html>
        <body>
            <h2>[TIP] 상표권 침해 분석 보고서</h2>
            <p>안녕하세요.</p>
            <p>보호 상표 <strong>[{p_trademark_name}]</strong>에 대한 
            침해 의심 상표 <strong>{len(approved_reports)}건</strong>의 분석이 완료되었습니다.</p>
            <hr/>
            {reports_html}
            <p>본 메일은 발신 전용입니다.</p>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"[이메일] 본문 생성 중 오류: {e}")
        return "<p>본문 생성 실패</p>"


async def send_report_mail(
    approved_reports: list[ApprovedReport],
    p_trademark_reg_no: str,
    p_trademark_name: str,
) -> bool:
    """
    보호 상표 1건에 대한 승인된 보고서 N건을 담당 변리사에게 메일로 일괄 발송
    """
    try:
        if not approved_reports:
            logger.info("[이메일] 발송할 보고서가 없어 중단")
            return False
            
        agent_email = await _get_agent_email(p_trademark_reg_no)
        
        if not agent_email:
            logger.warning(f"[이메일] 수신자 이메일 없음. 발송 취소. ({p_trademark_name})")
            return False

        # 2. 메일 구성
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port_env = os.getenv("SMTP_PORT", "587")
        smtp_port = int(smtp_port_env) if smtp_port_env.isdigit() else 587
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        
        if not all([smtp_server, smtp_user, smtp_password]):
            logger.error("[이메일] SMTP 환경변수 설정 누락 (.env 확인 필요)")
            return False
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[TIP] 상표권 침해 분석 보고서 - {p_trademark_name} ({len(approved_reports)}건)"
        msg["From"] = smtp_user
        msg["To"] = agent_email
        
        body = _build_email_body(approved_reports, p_trademark_name)
        msg.attach(MIMEText(body, "html"))
        
        # 3. 메일 발송
        logger.info(f"[이메일] SMTP 서버 연결 시도: {smtp_server}:{smtp_port}")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, agent_email, msg.as_string())
            
        logger.info(f"[이메일] 발송 성공: {agent_email} (건수: {len(approved_reports)})")
        return True
        
    except Exception as e:
        logger.error(f"[이메일] 발송 실패: {e}", exc_info=True)
        return False
