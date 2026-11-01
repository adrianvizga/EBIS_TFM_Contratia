
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from core.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> bool:
    try:
        if not settings.smtp_user or not settings.smtp_password:
            logger.warning("SMTP not configured. Email would be sent to: %s", to_email)
            logger.info("Subject: %s", subject)
            logger.info("To configure SMTP, set SMTP_USER and SMTP_PASSWORD in .env")
            return False
        
        message = MIMEMultipart("alternative")
        message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from}>"
        message["To"] = to_email
        message["Subject"] = subject
        
        if text_content:
            text_part = MIMEText(text_content, "plain")
            message.attach(text_part)
        
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        async with aiosmtplib.SMTP(
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            use_tls=False,
            start_tls=True
        ) as smtp:
            await smtp.login(settings.smtp_user, settings.smtp_password)
            await smtp.send_message(message)
        
        logger.info("Email sent successfully to %s", to_email)
        return True
        
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, str(e))
        return False


async def send_password_reset_email(
    to_email: str,
    first_name: str,
    reset_token: str
) -> bool:
    reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"
    logger.info("Enviando email de reset a %s", to_email)
    
    html_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 600px;
            margin: 40px auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }
        .content {
            padding: 40px 30px;
        }
        .greeting {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #1a202c;
        }
        .message {
            font-size: 16px;
            color: #4a5568;
            margin-bottom: 30px;
        }
        .button-container {
            text-align: center;
            margin: 35px 0;
        }
        .reset-button {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            padding: 14px 40px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 16px;
            transition: transform 0.2s;
        }
        .reset-button:hover {
            transform: translateY(-2px);
        }
        .alternative {
            margin-top: 30px;
            padding: 20px;
            background-color: #f7fafc;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }
        .alternative p {
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #4a5568;
        }
        .link {
            word-break: break-all;
            color: #667eea;
            text-decoration: none;
            font-size: 13px;
        }
        .footer {
            padding: 30px;
            text-align: center;
            color: #718096;
            font-size: 14px;
            background-color: #f7fafc;
            border-top: 1px solid #e2e8f0;
        }
        .warning {
            margin-top: 30px;
            padding: 15px;
            background-color: #fff5f5;
            border-left: 4px solid #fc8181;
            border-radius: 4px;
        }
        .warning p {
            margin: 0;
            font-size: 14px;
            color: #742a2a;
        }
        .expiry {
            text-align: center;
            margin-top: 25px;
            color: #718096;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 ContratIA</h1>
        </div>
        
        <div class="content">
            <p class="greeting">Hola {{ first_name }},</p>
            
            <p class="message">
                Hemos recibido una solicitud para restablecer la contraseña de tu cuenta en ContratIA.
                Si no realizaste esta solicitud, puedes ignorar este correo de forma segura.
            </p>
            
            <p class="message">
                Para restablecer tu contraseña, haz clic en el siguiente botón:
            </p>
            
            <div class="button-container">
                <a href="{{ reset_link }}" class="reset-button">Restablecer Contraseña</a>
            </div>
            
            <p class="expiry">
                ⏱️ Este enlace expirará en 1 hora por motivos de seguridad.
            </p>
            
            <div class="alternative">
                <p><strong>¿El botón no funciona?</strong></p>
                <p>Copia y pega el siguiente enlace en tu navegador:</p>
                <a href="{{ reset_link }}" class="link">{{ reset_link }}</a>
            </div>
            
            <div class="warning">
                <p><strong>⚠️ Importante:</strong> Si no solicitaste restablecer tu contraseña, 
                ignora este correo o contacta con soporte si tienes preocupaciones sobre la seguridad de tu cuenta.</p>
            </div>
        </div>
        
        <div class="footer">
            <p>Este es un correo automático, por favor no respondas.</p>
            <p>© 2024 ContratIA - Sistema de Gestión de Contratos con IA</p>
        </div>
    </div>
</body>
</html>
    """)
    
    text_template = Template("""
Hola {{ first_name }},

Hemos recibido una solicitud para restablecer la contraseña de tu cuenta en ContratIA.

Para restablecer tu contraseña, visita el siguiente enlace:
{{ reset_link }}

Este enlace expirará en 1 hora por motivos de seguridad.

Si no solicitaste restablecer tu contraseña, puedes ignorar este correo de forma segura.

---
ContratIA - Sistema de Gestión de Contratos con IA
Este es un correo automático, por favor no respondas.
    """)
    
    subject = "🔐 Restablece tu contraseña de ContratIA"
    html_content = html_template.render(first_name=first_name, reset_link=reset_link)
    text_content = text_template.render(first_name=first_name, reset_link=reset_link)
    
    return await send_email(to_email, subject, html_content, text_content)


async def send_welcome_email(to_email: str, first_name: str) -> bool:
    logger.info("Enviando email de bienvenida a %s", to_email)
    html_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 600px;
            margin: 40px auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }
        .content {
            padding: 40px 30px;
        }
        .footer {
            padding: 30px;
            text-align: center;
            color: #718096;
            font-size: 14px;
            background-color: #f7fafc;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>¡Bienvenido a ContratIA! 🎉</h1>
        </div>
        <div class="content">
            <p>Hola {{ first_name }},</p>
            <p>Gracias por registrarte en ContratIA. Estamos emocionados de tenerte con nosotros.</p>
            <p>Con ContratIA puedes:</p>
            <ul>
                <li>📝 Generar contratos personalizados con IA</li>
                <li>🔍 Analizar contratos existentes</li>
                <li>⚖️ Obtener asesoramiento jurídico automatizado</li>
            </ul>
        </div>
        <div class="footer">
            <p>© 2024 ContratIA</p>
        </div>
    </div>
</body>
</html>
    """)
    
    subject = "¡Bienvenido a ContratIA! 🎉"
    html_content = html_template.render(first_name=first_name)
    
    return await send_email(to_email, subject, html_content)
