"""
Servicio de gestión de emails con SendGrid
Incluye: Verificación de email, restablecimiento de contraseña, notificaciones
"""

import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configuración de SendGrid
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "profego.soporte@gmail.com")
FROM_NAME = os.getenv("FROM_NAME", "ProfeGo")

# URL base de la aplicación (cambiar en producción)
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Almacenamiento temporal de tokens (en producción, usar Redis o base de datos)
verification_tokens = {}  # {token: {email, expires, type}}


class EmailService:
    """Servicio para gestionar envío de emails"""
    
    def __init__(self):
        if not SENDGRID_API_KEY:
            logger.warning("⚠️ SENDGRID_API_KEY no configurada")
            self.client = None
        else:
            self.client = SendGridAPIClient(SENDGRID_API_KEY)
            logger.info("✅ SendGrid cliente inicializado")
    
    def _send_email(self, to_email: str, subject: str, html_content: str) -> Dict:
        """
        Método privado para enviar emails
        
        Args:
            to_email: Email del destinatario
            subject: Asunto del email
            html_content: Contenido HTML del email
        
        Returns:
            Dict con resultado del envío
        """
        if not self.client:
            logger.error("❌ Cliente SendGrid no inicializado")
            return {
                'success': False,
                'error': 'SendGrid no está configurado'
            }
        
        try:
            message = Mail(
                from_email=(FROM_EMAIL, FROM_NAME),
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            
            logger.info(f"✅ Email enviado a {to_email}: {subject}")
            logger.info(f"Status Code: {response.status_code}")
            
            return {
                'success': True,
                'status_code': response.status_code,
                'message': f'Email enviado exitosamente a {to_email}'
            }
            
        except Exception as e:
            logger.error(f"❌ Error enviando email: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_token(self, email: str, token_type: str, expires_minutes: int = 60) -> str:
        """
        Genera un token único para verificación o reset
        
        Args:
            email: Email del usuario
            token_type: Tipo de token ('verification' o 'reset_password')
            expires_minutes: Minutos de validez del token
        
        Returns:
            Token generado
        """
        token = secrets.token_urlsafe(32)
        
        verification_tokens[token] = {
            'email': email,
            'type': token_type,
            'expires': datetime.now() + timedelta(minutes=expires_minutes),
            'created_at': datetime.now().isoformat()
        }
        
        logger.info(f"🔐 Token {token_type} generado para {email}")
        return token
    
    def verify_token(self, token: str, expected_type: str) -> Optional[str]:
        """
        Verifica si un token es válido
        
        Args:
            token: Token a verificar
            expected_type: Tipo esperado del token
        
        Returns:
            Email del usuario si el token es válido, None si no lo es
        """
        token_data = verification_tokens.get(token)
        
        if not token_data:
            logger.warning(f"⚠️ Token no encontrado: {token[:10]}...")
            return None
        
        if token_data['type'] != expected_type:
            logger.warning(f"⚠️ Token tipo incorrecto. Esperado: {expected_type}, Recibido: {token_data['type']}")
            return None
        
        if datetime.now() > token_data['expires']:
            logger.warning(f"⚠️ Token expirado para {token_data['email']}")
            del verification_tokens[token]
            return None
        
        logger.info(f"✅ Token válido para {token_data['email']}")
        return token_data['email']
    
    def invalidate_token(self, token: str) -> bool:
        """
        Invalida un token después de usarlo
        
        Args:
            token: Token a invalidar
        
        Returns:
            True si se invalidó correctamente
        """
        if token in verification_tokens:
            email = verification_tokens[token]['email']
            del verification_tokens[token]
            logger.info(f"🗑️ Token invalidado para {email}")
            return True
        return False
    
    # ========================================================================
    # 1️⃣ VERIFICACIÓN DE EMAIL
    # ========================================================================
    
    def send_verification_email(self, email: str) -> Dict:
        """
        Envía email de verificación al usuario
        
        Args:
            email: Email del usuario registrado
        
        Returns:
            Dict con resultado del envío
        """
        logger.info(f"📧 Enviando email de verificación a {email}")
        
        # Generar token de verificación (válido por 24 horas)
        token = self.generate_token(email, 'verification', expires_minutes=1440)
        
        # Construir URL de verificación
        verification_url = f"{BASE_URL}/api/auth/verify-email?token={token}"
        
        # Plantilla HTML del email
        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verifica tu correo - ProfeGo</title>
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #4CAF50 0%, #6f826a 100%); padding: 40px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 32px;">📚 ProfeGo</h1>
                            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">Tu biblioteca digital de educación</p>
                        </td>
                    </tr>
                    
                    <!-- Body -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 24px;">¡Bienvenido/a a ProfeGo! 🎉</h2>
                            
                            <p style="color: #666666; line-height: 1.6; margin: 0 0 20px 0; font-size: 16px;">
                                Gracias por registrarte en ProfeGo. Para completar tu registro y comenzar a usar nuestra plataforma, 
                                necesitamos que verifiques tu dirección de correo electrónico.
                            </p>
                            
                            <p style="color: #666666; line-height: 1.6; margin: 0 0 30px 0; font-size: 16px;">
                                Haz clic en el siguiente botón para verificar tu cuenta:
                            </p>
                            
                            <!-- CTA Button -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding: 20px 0;">
                                        <a href="{verification_url}" 
                                           style="background: linear-gradient(135deg, #4CAF50 0%, #6f826a 100%); 
                                                  color: #ffffff; 
                                                  text-decoration: none; 
                                                  padding: 15px 40px; 
                                                  border-radius: 6px; 
                                                  font-weight: bold; 
                                                  font-size: 16px;
                                                  display: inline-block;">
                                            ✉️ Verificar mi correo
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="color: #999999; line-height: 1.6; margin: 30px 0 0 0; font-size: 14px;">
                                Si no puedes hacer clic en el botón, copia y pega el siguiente enlace en tu navegador:
                            </p>
                            <p style="color: #4CAF50; line-height: 1.6; margin: 10px 0; font-size: 14px; word-break: break-all;">
                                {verification_url}
                            </p>
                            
                            <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 30px 0;">
                                <p style="color: #856404; margin: 0; font-size: 14px;">
                                    ⏰ <strong>Importante:</strong> Este enlace es válido por 24 horas.
                                </p>
                            </div>
                            
                            <p style="color: #999999; line-height: 1.6; margin: 20px 0 0 0; font-size: 14px;">
                                Si no creaste una cuenta en ProfeGo, puedes ignorar este mensaje de forma segura.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 30px; text-align: center; border-top: 1px solid #e0e0e0;">
                            <p style="color: #999999; margin: 0 0 10px 0; font-size: 14px;">
                                © 2025 ProfeGo - La biblioteca de los profesores
                            </p>
                            <p style="color: #999999; margin: 0; font-size: 12px;">
                                Guadalajara, Jalisco, México
                            </p>
                            <p style="color: #4CAF50; margin: 10px 0 0 0; font-size: 12px;">
                                profego.soporte@gmail.com
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        return self._send_email(
            to_email=email,
            subject="✉️ Verifica tu correo electrónico - ProfeGo",
            html_content=html_content
        )
    
    # ========================================================================
    # 2️⃣ RESTABLECIMIENTO DE CONTRASEÑA
    # ========================================================================
    
    def send_password_reset_email(self, email: str) -> Dict:
        """
        Envía email para restablecer contraseña
        
        Args:
            email: Email del usuario
        
        Returns:
            Dict con resultado del envío
        """
        logger.info(f"🔑 Enviando email de restablecimiento de contraseña a {email}")
        
        # Generar token de reset (válido por 1 hora)
        token = self.generate_token(email, 'reset_password', expires_minutes=60)
        
        # Construir URL de reset
        reset_url = f"{BASE_URL}/reset-password.html?token={token}"
        
        # Plantilla HTML del email
        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Restablecer contraseña - ProfeGo</title>
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #4CAF50 0%, #6f826a 100%); padding: 40px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 32px;">🔐 ProfeGo</h1>
                            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">Restablecimiento de contraseña</p>
                        </td>
                    </tr>
                    
                    <!-- Body -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 24px;">Solicitud de restablecimiento de contraseña</h2>
                            
                            <p style="color: #666666; line-height: 1.6; margin: 0 0 20px 0; font-size: 16px;">
                                Hola,
                            </p>
                            
                            <p style="color: #666666; line-height: 1.6; margin: 0 0 20px 0; font-size: 16px;">
                                Recibimos una solicitud para restablecer la contraseña de tu cuenta de ProfeGo asociada a este correo electrónico.
                            </p>
                            
                            <p style="color: #666666; line-height: 1.6; margin: 0 0 30px 0; font-size: 16px;">
                                Si solicitaste este cambio, haz clic en el siguiente botón para crear una nueva contraseña:
                            </p>
                            
                            <!-- CTA Button -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding: 20px 0;">
                                        <a href="{reset_url}" 
                                           style="background: linear-gradient(135deg, #4CAF50 0%, #6f826a 100%); 
                                                  color: #ffffff; 
                                                  text-decoration: none; 
                                                  padding: 15px 40px; 
                                                  border-radius: 6px; 
                                                  font-weight: bold; 
                                                  font-size: 16px;
                                                  display: inline-block;">
                                            🔑 Restablecer contraseña
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="color: #999999; line-height: 1.6; margin: 30px 0 0 0; font-size: 14px;">
                                Si no puedes hacer clic en el botón, copia y pega el siguiente enlace en tu navegador:
                            </p>
                            <p style="color: #4CAF50; line-height: 1.6; margin: 10px 0; font-size: 14px; word-break: break-all;">
                                {reset_url}
                            </p>
                            
                            <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 30px 0;">
                                <p style="color: #856404; margin: 0; font-size: 14px;">
                                    ⏰ <strong>Importante:</strong> Este enlace es válido por 1 hora solamente.
                                </p>
                            </div>
                            
                            <div style="background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 30px 0;">
                                <p style="color: #721c24; margin: 0 0 10px 0; font-size: 14px; font-weight: bold;">
                                    🔒 Seguridad
                                </p>
                                <p style="color: #721c24; margin: 0; font-size: 14px;">
                                    Si NO solicitaste este cambio, ignora este correo. Tu contraseña actual permanecerá segura. 
                                    Te recomendamos revisar la actividad reciente de tu cuenta.
                                </p>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 30px; text-align: center; border-top: 1px solid #e0e0e0;">
                            <p style="color: #999999; margin: 0 0 10px 0; font-size: 14px;">
                                © 2025 ProfeGo - La biblioteca de los profesores
                            </p>
                            <p style="color: #999999; margin: 0; font-size: 12px;">
                                Guadalajara, Jalisco, México
                            </p>
                            <p style="color: #4CAF50; margin: 10px 0 0 0; font-size: 12px;">
                                profego.soporte@gmail.com
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        return self._send_email(
            to_email=email,
            subject="🔑 Restablece tu contraseña - ProfeGo",
            html_content=html_content
        )
    
    # ========================================================================
    # 3️⃣ NOTIFICACIÓN DE INICIO DE SESIÓN
    # ========================================================================
    
    def send_login_notification(
        self,
        email: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        location: Optional[str] = None
    ) -> Dict:
        """
        Envía notificación de inicio de sesión en nuevo dispositivo
        
        Args:
            email: Email del usuario
            device_info: Información del dispositivo/navegador
            ip_address: Dirección IP del usuario
            location: Ubicación aproximada (opcional)
        
        Returns:
            Dict con resultado del envío
        """
        logger.info(f"🔔 Enviando notificación de inicio de sesión a {email}")
        
        # Timestamp del login
        login_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Información del dispositivo
        device_display = device_info or "Dispositivo desconocido"
        ip_display = ip_address or "IP desconocida"
        location_display = location or "Ubicación desconocida"
        
        # Plantilla HTML del email
        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nuevo inicio de sesión - ProfeGo</title>
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #4CAF50 0%, #6f826a 100%); padding: 40px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 32px;">🔔 ProfeGo</h1>
                            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">Alerta de seguridad</p>
                        </td>
                    </tr>
                    
                    <!-- Body -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 24px;">Nuevo inicio de sesión detectado</h2>
                            
                            <p style="color: #666666; line-height: 1.6; margin: 0 0 20px 0; font-size: 16px;">
                                Hola,
                            </p>
                            
                            <p style="color: #666666; line-height: 1.6; margin: 0 0 30px 0; font-size: 16px;">
                                Hemos detectado un nuevo inicio de sesión en tu cuenta de ProfeGo. Si fuiste tú, puedes ignorar este mensaje.
                            </p>
                            
                            <!-- Login Details Box -->
                            <div style="background-color: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin: 30px 0;">
                                <h3 style="color: #4CAF50; margin: 0 0 15px 0; font-size: 18px;">📊 Detalles del inicio de sesión</h3>
                                
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="padding: 8px 0; color: #999999; font-size: 14px; width: 140px;">
                                            <strong>⏰ Fecha y hora:</strong>
                                        </td>
                                        <td style="padding: 8px 0; color: #333333; font-size: 14px;">
                                            {login_time}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #999999; font-size: 14px;">
                                            <strong>💻 Dispositivo:</strong>
                                        </td>
                                        <td style="padding: 8px 0; color: #333333; font-size: 14px;">
                                            {device_display}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #999999; font-size: 14px;">
                                            <strong>🌐 Dirección IP:</strong>
                                        </td>
                                        <td style="padding: 8px 0; color: #333333; font-size: 14px;">
                                            {ip_display}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #999999; font-size: 14px;">
                                            <strong>📍 Ubicación:</strong>
                                        </td>
                                        <td style="padding: 8px 0; color: #333333; font-size: 14px;">
                                            {location_display}
                                        </td>
                                    </tr>
                                </table>
                            </div>
                            
                            <div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 30px 0;">
                                <p style="color: #155724; margin: 0; font-size: 14px;">
                                    ✅ <strong>¿Fuiste tú?</strong> No necesitas hacer nada. Tu cuenta está segura.
                                </p>
                            </div>
                            
                            <div style="background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 30px 0;">
                                <p style="color: #721c24; margin: 0 0 10px 0; font-size: 14px; font-weight: bold;">
                                    ⚠️ ¿No fuiste tú?
                                </p>
                                <p style="color: #721c24; margin: 0; font-size: 14px;">
                                    Si no reconoces esta actividad, te recomendamos cambiar tu contraseña inmediatamente y revisar la seguridad de tu cuenta.
                                </p>
                            </div>
                            
                            <!-- CTA Button -->
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center" style="padding: 20px 0;">
                                        <a href="{BASE_URL}/login.html" 
                                           style="background: linear-gradient(135deg, #4CAF50 0%, #6f826a 100%); 
                                                  color: #ffffff; 
                                                  text-decoration: none; 
                                                  padding: 15px 40px; 
                                                  border-radius: 6px; 
                                                  font-weight: bold; 
                                                  font-size: 16px;
                                                  display: inline-block;">
                                            🔒 Ir a mi cuenta
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="color: #999999; line-height: 1.6; margin: 30px 0 0 0; font-size: 14px; text-align: center;">
                                Este es un correo automático de seguridad. Por favor no respondas a este mensaje.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 30px; text-align: center; border-top: 1px solid #e0e0e0;">
                            <p style="color: #999999; margin: 0 0 10px 0; font-size: 14px;">
                                © 2025 ProfeGo - La biblioteca de los profesores
                            </p>
                            <p style="color: #999999; margin: 0; font-size: 12px;">
                                Guadalajara, Jalisco, México
                            </p>
                            <p style="color: #4CAF50; margin: 10px 0 0 0; font-size: 12px;">
                                profego.soporte@gmail.com
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        return self._send_email(
            to_email=email,
            subject="🔔 Nuevo inicio de sesión en tu cuenta - ProfeGo",
            html_content=html_content
        )


# Instancia global del servicio
email_service = EmailService()


# Funciones de conveniencia
def send_verification_email(email: str) -> Dict:
    """Envía email de verificación"""
    return email_service.send_verification_email(email)


def send_password_reset_email(email: str) -> Dict:
    """Envía email para restablecer contraseña"""
    return email_service.send_password_reset_email(email)


def send_login_notification(
    email: str,
    device_info: Optional[str] = None,
    ip_address: Optional[str] = None,
    location: Optional[str] = None
) -> Dict:
    """Envía notificación de inicio de sesión"""
    return email_service.send_login_notification(
        email, device_info, ip_address, location
    )


def verify_token(token: str, token_type: str) -> Optional[str]:
    """Verifica un token"""
    return email_service.verify_token(token, token_type)


def invalidate_token(token: str) -> bool:
    """Invalida un token"""
    return email_service.invalidate_token(token)
