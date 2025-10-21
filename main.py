from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import pyrebase
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Optional, Dict
import json
from datetime import datetime
import tempfile
import io
import time
import uuid
import logging
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from rag_system import get_rag_system, initialize_rag_system
from typing import List, Dict, Optional
import json
from pathlib import Path
"""
Endpoints para visualizar métricas RAG y demostrar su funcionamiento
"""
from fastapi import APIRouter, Depends, HTTPException
from rag_system.metrics import get_metrics_instance
import json
from pathlib import Path

# Importar el módulo OCR
from PruebaOcr import process_file_to_txt, check_supported_file, get_text_only

# Importar el módulo de Google Cloud Storage mejorado
from gcs_storage import GCSStorageManagerV2

# Importar el servicio de Gemini AI
from gemini_service import generar_plan_estudio

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

app = FastAPI(title="ProfeGo API", version="2.0.0")
rag_system = None
# Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configurar CORS para desarrollo y producción
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
allowed_origins = []

if RENDER_EXTERNAL_URL:
    # En producción (Render)
    allowed_origins = [
        RENDER_EXTERNAL_URL,
        f"https://{RENDER_EXTERNAL_URL.replace('https://', '')}",
    ]
else:
    # En desarrollo local - CORS PERMISIVO
    allowed_origins = ["*"]  # Permitir todos los orígenes en desarrollo

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de archivos
MAX_FILE_SIZE = 80 * 1024 * 1024  # 80MB
ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', 
    '.png', '.xlsx', '.xls', '.csv', '.json', '.xml'
}

# Obtener directorio base del script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# ========== IMPORTANTE: SERVIR ARCHIVOS ESTÁTICOS CORRECTAMENTE ==========
# Verificar que el directorio frontend existe
if not os.path.exists(FRONTEND_DIR):
    print(f"⚠️ ADVERTENCIA: No se encontró el directorio frontend en {FRONTEND_DIR}")
else:
    print(f"✅ Frontend encontrado en: {FRONTEND_DIR}")
    
    # Montar archivos estáticos ANTES de definir las rutas
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")
    print(f"✅ Archivos estáticos montados en /frontend")

# Firebase Config (Solo Auth)
firebaseConfig = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL", "")
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

# Google Cloud Storage Manager V2 con nueva estructura
gcs_storage = GCSStorageManagerV2(
    bucket_name=os.getenv("GCS_BUCKET_NAME", "bucket-profe-go")
)

# ---------------- Modelos Pydantic ----------------
class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    email: str
    token: str
    message: str

class FileInfo(BaseModel):
    name: str
    type: str
    size: str
    category: str
    date: str
    download_url: Optional[str] = None

class ProcessingResult(BaseModel):
    success: bool
    files_uploaded: int
    files_processed: int
    message: str
    errors: List[str] = []

class PaginatedFiles(BaseModel):
    files: List[FileInfo]
    total: int
    page: int
    pages: int
    per_page: int

class PlanGenerationRequest(BaseModel):
    plan_filename: str
    diagnostico_filename: Optional[str] = None

class PlanResponse(BaseModel):
    success: bool
    plan_id: Optional[str] = None
    plan_data: Optional[Dict] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None

# ---------------- Utilidades ----------------
class ProfeGoUtils:
    @staticmethod
    def validar_email(email: str) -> bool:
        """Validar formato de email"""
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validar_password(password: str) -> bool:
        """Validar que la contraseña tenga al menos 6 caracteres"""
        return len(password) >= 6
    
    @staticmethod
    def obtener_tipo_archivo(filename: str) -> str:
        """Determinar el tipo de archivo basado en su extensión"""
        ext = os.path.splitext(filename)[1].lower()
        
        tipos = {
            '.pdf': "PDF",
            '.jpg': "Imagen", '.jpeg': "Imagen", '.png': "Imagen",
            '.doc': "Word", '.docx': "Word",
            '.xls': "Excel", '.xlsx': "Excel",
            '.txt': "Texto",
            '.csv': "CSV",
            '.json': "JSON",
            '.xml': "XML"
        }
        
        return tipos.get(ext, "Archivo")
    
    @staticmethod
    def validar_extension(filename: str) -> bool:
        """Validar si la extensión del archivo está permitida"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in ALLOWED_EXTENSIONS

# ---------------- Dependency para autenticación ----------------
async def get_current_user(authorization: str = Header(None)):
    """Verificar token de Firebase y extraer usuario"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        user_info = auth.get_account_info(token)
        email = user_info['users'][0]['email']
        return {"email": email, "token": token}
    except Exception as e:
        logger.error(f"Error verificando token: {e}")
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

# ============================================================================
# RUTAS DE AUTENTICACIÓN
# ============================================================================

@app.post("/api/auth/login", response_model=UserResponse)
@limiter.limit("10/minute")
async def login(request: Request, user_data: UserLogin):
    """Iniciar sesión con rate limiting"""
    logger.info(f"📧 Intento de login: {user_data.email}")
    
    if not ProfeGoUtils.validar_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email inválido")
    
    if not ProfeGoUtils.validar_password(user_data.password):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    
    try:
        user = auth.sign_in_with_email_and_password(user_data.email, user_data.password)
        
        # Inicializar estructura en GCS
        gcs_storage.inicializar_usuario(user_data.email)
        
        logger.info(f"✅ Login exitoso: {user_data.email}")
        
        return UserResponse(
            email=user_data.email,
            token=user.get("idToken"),
            message=f"Bienvenido/a {user_data.email}"
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error en login: {error_msg}")
        
        if "EMAIL_NOT_FOUND" in error_msg:
            raise HTTPException(status_code=400, detail="Usuario no encontrado")
        elif "INVALID_PASSWORD" in error_msg or "INVALID_LOGIN_CREDENTIALS" in error_msg:
            raise HTTPException(status_code=400, detail="Credenciales incorrectas")
        elif "TOO_MANY_ATTEMPTS" in error_msg:
            raise HTTPException(status_code=429, detail="Demasiados intentos. Intenta más tarde")
        else:
            raise HTTPException(status_code=400, detail="Error de autenticación")

@app.on_event("startup")
async def startup_event():
    """
    Inicializa el sistema RAG al arrancar la aplicación
    VERSIÓN MEJORADA CON LOGS
    """
    global rag_system, rag_analyzer
    
    logger.info("🚀 Inicializando sistema RAG...")
    
    try:
        # Crear directorios manualmente
        from pathlib import Path
        
        dirs_to_create = [
            './rag_data/cuentos',
            './rag_data/canciones',
            './rag_data/vector_db'
        ]
        
        for dir_path in dirs_to_create:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ Directorios RAG creados/verificados")
        
        # Verificar que hay archivos en la biblioteca
        cuentos_count = len(list(Path('./rag_data/cuentos').glob('**/*.txt')))
        canciones_count = len(list(Path('./rag_data/canciones').glob('**/*.txt')))
        
        logger.info(f"📚 Biblioteca: {cuentos_count} cuentos, {canciones_count} canciones")
        
        if cuentos_count == 0 and canciones_count == 0:
            logger.warning("⚠️ Biblioteca RAG vacía - No se encontraron archivos .txt")
            logger.warning("💡 Agrega archivos .txt en ./rag_data/cuentos y ./rag_data/canciones")
            logger.warning("💡 Luego ejecuta: python init_rag.py")
        
        # Inicializar sistema RAG
        rag_system = initialize_rag_system()
        
        if rag_system is None:
            logger.warning("⚠️ Sistema RAG no pudo inicializarse")
            return
        
        # Inicializar analizador RAG
        rag_analyzer = RAGAnalyzer(rag_system)
        logger.info("✅ RAG Analyzer inicializado")
        
        # Verificar stats
        stats = rag_system.get_stats()
        
        if stats['total_documents'] == 0:
            logger.warning("⚠️ Vector store vacío - ejecuta 'python init_rag.py'")
        else:
            logger.info(f"✅ Vector store listo: {stats['total_documents']} documentos indexados")
        
    except Exception as e:
        logger.error(f"❌ Error inicializando RAG: {e}", exc_info=True)
        logger.warning("⚠️ La aplicación continuará sin RAG")
        rag_system = None
        rag_analyzer = None

@app.post("/api/auth/register")
@limiter.limit("3/minute")
async def register(request: Request, user_data: UserLogin):
    """Registrar nuevo usuario con rate limiting"""
    logger.info(f"📝 Intento de registro: {user_data.email}")
    
    if not ProfeGoUtils.validar_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email inválido")
    
    if not ProfeGoUtils.validar_password(user_data.password):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    
    try:
        auth.create_user_with_email_and_password(user_data.email, user_data.password)
        gcs_storage.inicializar_usuario(user_data.email)
        
        logger.info(f"✅ Registro exitoso: {user_data.email}")
        
        return {"message": "Usuario registrado correctamente. Ya puedes iniciar sesión."}
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error en registro: {error_msg}")
        
        if "EMAIL_EXISTS" in error_msg:
            raise HTTPException(status_code=400, detail="Este email ya está registrado")
        else:
            raise HTTPException(status_code=400, detail="Error en el registro")

# ============================================================================
# RUTAS DE ARCHIVOS
# ============================================================================

@app.post("/api/files/upload", response_model=ProcessingResult)
@limiter.limit("10/minute")
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Subir y procesar archivos con validaciones"""
    user_email = current_user["email"]
    
    archivos_subidos = []
    archivos_procesados = []
    errores_procesamiento = []
    
    for file in files:
        try:
            # Validar extensión
            if not ProfeGoUtils.validar_extension(file.filename):
                errores_procesamiento.append(
                    f"{file.filename}: Tipo de archivo no permitido"
                )
                continue
            
            # Leer contenido del archivo
            content = await file.read()
            
            # Validar tamaño
            if len(content) > MAX_FILE_SIZE:
                errores_procesamiento.append(
                    f"{file.filename}: Archivo muy grande (máx: 80MB)"
                )
                continue
            
            # Crear archivo temporal para procesamiento
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            try:
                # Subir archivo original a GCS
                resultado_subida = gcs_storage.subir_archivo_desde_bytes(
                    contenido=content,
                    email=user_email,
                    nombre_archivo=file.filename,
                    es_procesado=False
                )
                
                if resultado_subida['success']:
                    archivos_subidos.append(file.filename)
                    
                    # Verificar si es procesable
                    verificacion = check_supported_file(tmp_file_path)
                    
                    if verificacion['supported']:
                        # Procesar archivo
                        nombre_base = Path(file.filename).stem
                        resultado_conversion = process_file_to_txt(tmp_file_path)
                        
                        if resultado_conversion['success']:
                            # Leer el archivo procesado
                            with open(resultado_conversion['output_file'], 'rb') as f:
                                contenido_procesado = f.read()
                            
                            # Subir archivo procesado a GCS
                            resultado_txt = gcs_storage.subir_archivo_desde_bytes(
                                contenido=contenido_procesado,
                                email=user_email,
                                nombre_archivo=f"{nombre_base}_procesado.txt",
                                es_procesado=True
                            )
                            
                            if resultado_txt['success']:
                                archivos_procesados.append({
                                    'original': file.filename,
                                    'txt': f"{nombre_base}_procesado.txt"
                                })
                            
                            # Limpiar archivo procesado temporal
                            if os.path.exists(resultado_conversion['output_file']):
                                os.remove(resultado_conversion['output_file'])
                else:
                    errores_procesamiento.append(
                        f"{file.filename}: Error subiendo a GCS"
                    )
                    
            finally:
                # Limpiar archivo temporal
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
                    
        except Exception as ex:
            errores_procesamiento.append(f"{file.filename}: {str(ex)}")
    
    message = f"Archivos subidos: {len(archivos_subidos)}"
    if archivos_procesados:
        message += f", Procesados: {len(archivos_procesados)}"
    
    return ProcessingResult(
        success=len(archivos_subidos) > 0,
        files_uploaded=len(archivos_subidos),
        files_processed=len(archivos_procesados),
        message=message,
        errors=errores_procesamiento
    )

@app.get("/api/files/list")
async def list_files(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Listar archivos sin paginación estricta para desarrollo"""
    user_email = current_user["email"]
    files_info = []
    
    try:
        # Obtener todos los archivos
        archivos_originales = gcs_storage.listar_archivos(user_email, "uploads")
        archivos_procesados = gcs_storage.listar_archivos(user_email, "processed")
        
        # Combinar y formatear
        for archivo in archivos_originales:
            files_info.append({
                "name": archivo['name'],
                "type": ProfeGoUtils.obtener_tipo_archivo(archivo['name']),
                "size": f"{archivo['size_mb']} MB",
                "category": "original",
                "date": archivo['date']
            })
        
        # Filtrar archivos procesados (excluir planes JSON)
        for archivo in archivos_procesados:
            # Excluir archivos que son planes generados
            if not archivo['name'].startswith('plan_') or not archivo['name'].endswith('.json'):
                files_info.append({
                    "name": archivo['name'],
                    "type": "TXT Procesado",
                    "size": f"{archivo['size_mb']} MB",
                    "category": "procesado",
                    "date": archivo['date']
                })
        
        return files_info
        
    except Exception as e:
        logger.error(f"❌ Error listando archivos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listando archivos: {str(e)}")

@app.get("/api/files/download/{category}/{filename}")
async def download_file(
    category: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Descargar archivo directamente desde GCS"""
    user_email = current_user["email"]
    
    try:
        es_procesado = category == "procesado"
        
        # Obtener el archivo desde GCS
        contenido = gcs_storage.obtener_archivo_bytes(
            email=user_email,
            nombre_archivo=filename,
            es_procesado=es_procesado
        )
        
        if contenido is None:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        # Determinar el tipo MIME
        content_type = "application/octet-stream"
        ext = Path(filename).suffix.lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        content_type = mime_types.get(ext, content_type)
        
        # Retornar el archivo como stream
        return StreamingResponse(
            io.BytesIO(contenido),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Error descargando archivo: {str(ex)}")

@app.get("/api/files/preview/{category}/{filename}")
async def preview_file(
    category: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Vista previa de archivo - devuelve contenido según tipo"""
    user_email = current_user["email"]
    
    try:
        es_procesado = category == "procesado"
        
        # Obtener el archivo desde GCS
        contenido = gcs_storage.obtener_archivo_bytes(
            email=user_email,
            nombre_archivo=filename,
            es_procesado=es_procesado
        )
        
        if contenido is None:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        # Detectar tipo de archivo
        ext = Path(filename).suffix.lower()
        
        # Para PDFs e imágenes, devolver el archivo directamente
        if ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            mime_types = {
                '.pdf': 'application/pdf',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp'
            }
            
            return StreamingResponse(
                io.BytesIO(contenido),
                media_type=mime_types.get(ext, 'application/octet-stream'),
                headers={"Content-Disposition": f"inline; filename={filename}"}
            )
        
        # Para archivos TXT, devolver el contenido como JSON
        elif ext == '.txt':
            try:
                texto = contenido.decode('utf-8')
            except UnicodeDecodeError:
                texto = contenido.decode('latin-1', errors='ignore')
            
            return JSONResponse(content={
                "type": "text",
                "content": texto,
                "filename": filename
            })
        
        else:
            raise HTTPException(
                status_code=400, 
                detail="Tipo de archivo no soportado para vista previa"
            )
            
    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"Error en preview: {str(ex)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(ex)}")

@app.delete("/api/files/delete/{category}/{filename}")
@limiter.limit("20/minute")
async def delete_file(
    request: Request,
    category: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Eliminar archivo de GCS"""
    user_email = current_user["email"]
    
    try:
        es_procesado = category == "procesado"
        
        resultado = gcs_storage.eliminar_archivo(
            email=user_email,
            nombre_archivo=filename,
            es_procesado=es_procesado
        )
        
        if not resultado['success']:
            raise HTTPException(status_code=404, detail=resultado.get('error', 'Archivo no encontrado'))
        
        return {"message": f"Archivo '{filename}' eliminado correctamente"}
        
    except HTTPException:
        raise
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Error eliminando archivo: {str(ex)}")

@app.get("/api/user/storage-info")
async def get_storage_info(current_user: dict = Depends(get_current_user)):
    """Obtener información de almacenamiento del usuario"""
    user_email = current_user["email"]
    
    try:
        info = gcs_storage.obtener_info_almacenamiento(user_email)
        return info
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Error obteniendo información: {str(ex)}")

def generar_documento_word(plan_data: Dict) -> io.BytesIO:
    """
    Genera un documento Word profesional a partir de los datos del plan
    """
    doc = Document()
    
    # Configurar estilos del documento
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(12)
    p_format = style.paragraph_format
    p_format.line_spacing = 1.5
    # ========== PORTADA ==========
    portada = doc.add_heading(plan_data.get('nombre_plan', 'Plan Educativo'), 0)
    portada.alignment = WD_ALIGN_PARAGRAPH.CENTER
    portada.runs[0].font.color.rgb = RGBColor(0, 102, 204)
    
    # Información general
    info_general = doc.add_paragraph()
    info_general.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    if plan_data.get('grado'):
        run = info_general.add_run(f"Grado: {plan_data['grado']}\n")
        run.bold = True
        run.font.size = Pt(12)
    
    if plan_data.get('edad_aprox'):
        run = info_general.add_run(f"Edad aproximada: {plan_data['edad_aprox']}\n")
        run.font.size = Pt(12)
    
    if plan_data.get('duracion_total'):
        run = info_general.add_run(f"Duración total: {plan_data['duracion_total']}\n")
        run.font.size = Pt(12)

    if plan_data.get('fecha_generacion'):
        fecha = datetime.fromisoformat(plan_data['fecha_generacion']).strftime('%d/%m/%Y %H:%M')
        run = info_general.add_run(f"Generado: {fecha}\n")
        run.font.size = Pt(12)
        run.italic = True
    
    doc.add_paragraph()  # Espacio
    
    # Campo formativo y ejes
    if plan_data.get('campo_formativo_principal'):
        p = doc.add_paragraph()
        p.add_run('Campo Formativo Principal: ').bold = True
        p.add_run(plan_data['campo_formativo_principal'])
    
    if plan_data.get('ejes_articuladores_generales'):
        p = doc.add_paragraph()
        p.add_run('Ejes Articuladores: ').bold = True
        p.add_run(', '.join(plan_data['ejes_articuladores_generales']))
    
    doc.add_page_break()
    
    # ========== MÓDULOS ==========
    doc.add_heading('📚 Módulos del Plan', 1)
    
    modulos = plan_data.get('modulos', [])
    
    for idx, modulo in enumerate(modulos, 1):
        # Encabezado del módulo
        modulo_heading = doc.add_heading(f"Módulo {modulo.get('numero', idx)}: {modulo.get('nombre', '')}", 2)
        modulo_heading.runs[0].font.color.rgb = RGBColor(0, 102, 204)
        
        # Información del módulo
        if modulo.get('campo_formativo'):
            p = doc.add_paragraph()
            p.add_run('📘 Campo Formativo: ').bold = True
            p.add_run(modulo['campo_formativo'])
        
        if modulo.get('ejes_articuladores'):
            p = doc.add_paragraph()
            p.add_run('🔗 Ejes Articuladores: ').bold = True
            p.add_run(', '.join(modulo['ejes_articuladores']))
        
        if modulo.get('aprendizaje_esperado'):
            p = doc.add_paragraph()
            p.add_run('🎯 Aprendizaje Esperado: ').bold = True
            p.add_run(modulo['aprendizaje_esperado'])
        
        if modulo.get('tiempo_estimado'):
            p = doc.add_paragraph()
            p.add_run('⏱️ Tiempo Estimado: ').bold = True
            p.add_run(modulo['tiempo_estimado'])
        
        doc.add_paragraph()  # Espacio
        
        # Actividad de inicio
        if modulo.get('actividad_inicio'):
            doc.add_heading('🎬 Actividad de Inicio', 3)
            inicio = modulo['actividad_inicio']
            
            p = doc.add_paragraph()
            p.add_run('Nombre: ').bold = True
            p.add_run(inicio.get('nombre', ''))
            
            p = doc.add_paragraph()
            p.add_run('Descripción: ').bold = True
            p.add_run(inicio.get('descripcion', ''))
            
            if inicio.get('duracion'):
                p = doc.add_paragraph()
                p.add_run('Duración: ').bold = True
                p.add_run(inicio['duracion'])
            
            if inicio.get('materiales'):
                p = doc.add_paragraph()
                p.add_run('Materiales: ').bold = True
                materiales = inicio['materiales'] if isinstance(inicio['materiales'], list) else [inicio['materiales']]
                p.add_run(', '.join(materiales))
            
            if inicio.get('organizacion'):
                p = doc.add_paragraph()
                p.add_run('Organización: ').bold = True
                p.add_run(inicio['organizacion'])
        
        # Actividades de desarrollo
        if modulo.get('actividades_desarrollo'):
            doc.add_heading('🚀 Actividades de Desarrollo', 3)
            
            for act_idx, actividad in enumerate(modulo['actividades_desarrollo'], 1):
                doc.add_heading(f"Actividad {act_idx}: {actividad.get('nombre', '')}", 4)
                
                if actividad.get('tipo'):
                    p = doc.add_paragraph()
                    p.add_run('Tipo: ').bold = True
                    p.add_run(actividad['tipo'])
                
                if actividad.get('descripcion'):
                    p = doc.add_paragraph()
                    p.add_run('Descripción: ').bold = True
                    p.add_run(actividad['descripcion'])
                
                if actividad.get('duracion'):
                    p = doc.add_paragraph()
                    p.add_run('Duración: ').bold = True
                    p.add_run(actividad['duracion'])
                
                if actividad.get('organizacion'):
                    p = doc.add_paragraph()
                    p.add_run('Organización: ').bold = True
                    p.add_run(actividad['organizacion'])
                
                if actividad.get('materiales'):
                    p = doc.add_paragraph()
                    p.add_run('Materiales: ').bold = True
                    materiales = actividad['materiales'] if isinstance(actividad['materiales'], list) else [actividad['materiales']]
                    p.add_run(', '.join(materiales))
                
                if actividad.get('aspectos_a_observar'):
                    p = doc.add_paragraph()
                    p.add_run('Aspectos a observar: ').bold = True
                    p.add_run(actividad['aspectos_a_observar'])
                
                doc.add_paragraph()  # Espacio entre actividades
        
        # Actividad de cierre
        if modulo.get('actividad_cierre'):
            doc.add_heading('🎬 Actividad de Cierre', 3)
            cierre = modulo['actividad_cierre']
            
            p = doc.add_paragraph()
            p.add_run('Nombre: ').bold = True
            p.add_run(cierre.get('nombre', ''))
            
            p = doc.add_paragraph()
            p.add_run('Descripción: ').bold = True
            p.add_run(cierre.get('descripcion', ''))
            
            if cierre.get('duracion'):
                p = doc.add_paragraph()
                p.add_run('Duración: ').bold = True
                p.add_run(cierre['duracion'])
            
            if cierre.get('preguntas_guia'):
                p = doc.add_paragraph()
                p.add_run('Preguntas guía:').bold = True
                for pregunta in cierre['preguntas_guia']:
                    doc.add_paragraph(f"• {pregunta}", style='List Bullet')
        
        # Información adicional del módulo
        if modulo.get('consejos_maestra'):
            doc.add_heading('💡 Consejos para la Maestra', 3)
            doc.add_paragraph(modulo['consejos_maestra'])
        
        if modulo.get('variaciones'):
            doc.add_heading('🔄 Variaciones', 3)
            doc.add_paragraph(modulo['variaciones'])
        
        if modulo.get('vinculo_familia'):
            doc.add_heading('🏠 Vínculo con la Familia', 3)
            doc.add_paragraph(modulo['vinculo_familia'])
        
        if modulo.get('evaluacion'):
            doc.add_heading('📋 Evaluación', 3)
            doc.add_paragraph(modulo['evaluacion'])
        
        # Separador entre módulos
        if idx < len(modulos):
            doc.add_page_break()
    
    # ========== RECURSOS EDUCATIVOS ==========
    if plan_data.get('recursos_educativos'):
        doc.add_page_break()
        doc.add_heading('📚 Recursos Educativos', 1)
        recursos = plan_data['recursos_educativos']
        
        if recursos.get('materiales_generales'):
            doc.add_heading('🛠️ Materiales Generales', 2)
            for material in recursos['materiales_generales']:
                doc.add_paragraph(f"• {material}", style='List Bullet')
        
        if recursos.get('cuentos_recomendados'):
            doc.add_heading('📖 Cuentos Recomendados', 2)
            for cuento in recursos['cuentos_recomendados']:
                p = doc.add_paragraph()
                p.add_run(f"• {cuento.get('titulo', '')}: ").bold = True
                
                detalles = []
                if cuento.get('autor'):
                    detalles.append(f"Autor: {cuento['autor']}")
                if cuento.get('tipo'):
                    detalles.append(f"Tipo: {cuento['tipo']}")
                if cuento.get('acceso'):
                    detalles.append(f"Acceso: {cuento['acceso']}")
                if cuento.get('disponibilidad'):
                    detalles.append(f"Disponibilidad: {cuento['disponibilidad']}")
                
                p.add_run(' | '.join(detalles))
                
                if cuento.get('descripcion_breve'):
                    doc.add_paragraph(f"  {cuento['descripcion_breve']}", style='List Bullet 2')
        
        if recursos.get('canciones_recomendadas'):
            doc.add_heading('🎵 Canciones Recomendadas', 2)
            for cancion in recursos['canciones_recomendadas']:
                p = doc.add_paragraph()
                p.add_run(f"• {cancion.get('titulo', '')}: ").bold = True
                
                detalles = []
                if cancion.get('tipo'):
                    detalles.append(f"Tipo: {cancion['tipo']}")
                if cancion.get('acceso'):
                    detalles.append(f"Acceso: {cancion['acceso']}")
                if cancion.get('disponibilidad'):
                    detalles.append(f"Disponibilidad: {cancion['disponibilidad']}")
                
                p.add_run(' | '.join(detalles))
                
                if cancion.get('uso_sugerido'):
                    doc.add_paragraph(f"  Uso sugerido: {cancion['uso_sugerido']}", style='List Bullet 2')
    
    # ========== RECOMENDACIONES DE AMBIENTE ==========
    if plan_data.get('recomendaciones_ambiente'):
        doc.add_heading('🏫 Recomendaciones para el Ambiente', 2)
        doc.add_paragraph(plan_data['recomendaciones_ambiente'])
    
    # ========== VINCULACIÓN CURRICULAR ==========
    if plan_data.get('vinculacion_curricular'):
        doc.add_heading('🔗 Vinculación Curricular', 2)
        vinculacion = plan_data['vinculacion_curricular']
        
        if vinculacion.get('campo_formativo_principal'):
            p = doc.add_paragraph()
            p.add_run('Campo Formativo Principal: ').bold = True
            p.add_run(vinculacion['campo_formativo_principal'])
        
        if vinculacion.get('campos_secundarios'):
            p = doc.add_paragraph()
            p.add_run('Campos Secundarios: ').bold = True
            p.add_run(', '.join(vinculacion['campos_secundarios']))
        
        if vinculacion.get('ejes_transversales'):
            p = doc.add_paragraph()
            p.add_run('Ejes Transversales: ').bold = True
            p.add_run(', '.join(vinculacion['ejes_transversales']))
        
        if vinculacion.get('aprendizajes_clave'):
            doc.add_heading('Aprendizajes Clave:', 3)
            for aprendizaje in vinculacion['aprendizajes_clave']:
                doc.add_paragraph(f"• {aprendizaje}", style='List Bullet')
    
    # Guardar en memoria
    docx_bytes = io.BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    
    return docx_bytes

# ============================================================================
# RUTAS PARA GENERACIÓN DE PLANES CON IA
# ============================================================================

@app.post("/api/plans/generate", response_model=PlanResponse)
@limiter.limit("5/hour")
async def generate_plan_with_rag(
    request: Request,
    plan_file: UploadFile = File(..., description="Archivo del plan de estudios"),
    diagnostico_file: Optional[UploadFile] = File(None, description="Archivo de diagnóstico (opcional)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Genera un plan de estudio personalizado usando Gemini AI + RAG
    VERSIÓN CORREGIDA - USA CORRECTAMENTE LOS DOCUMENTOS RAG
    """
    user_email = current_user["email"]
    start_time = time.time()
    
    logger.info(f"🎓 Generando plan con RAG para usuario: {user_email}")
    
    try:
        # ========== VALIDACIÓN DE ARCHIVOS ==========
        
        if not ProfeGoUtils.validar_extension(plan_file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no permitido para plan: {plan_file.filename}"
            )
        
        plan_content = await plan_file.read()
        if len(plan_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="El archivo del plan excede el límite de 80MB"
            )
        
        diagnostico_content = None
        diagnostico_filename = None
        
        if diagnostico_file and diagnostico_file.filename:
            if not ProfeGoUtils.validar_extension(diagnostico_file.filename):
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de archivo no permitido para diagnóstico: {diagnostico_file.filename}"
                )
            
            diagnostico_content = await diagnostico_file.read()
            if len(diagnostico_content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail="El archivo de diagnóstico excede el límite de 80MB"
                )
            diagnostico_filename = diagnostico_file.filename
        
        logger.info(f"✅ Archivos validados")
        
        # ========== PROCESAMIENTO OCR ==========
        
        logger.info("📄 Extrayendo texto del plan de estudios...")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(plan_file.filename).suffix) as tmp_plan:
            tmp_plan.write(plan_content)
            tmp_plan_path = tmp_plan.name
        
        try:
            plan_result = get_text_only(tmp_plan_path)
            
            if not plan_result['success'] or not plan_result['text']:
                raise HTTPException(
                    status_code=400,
                    detail=f"No se pudo extraer texto del plan"
                )
            
            plan_text = plan_result['text']
            logger.info(f"✅ Texto extraído del plan: {len(plan_text)} caracteres")
            
            diagnostico_text = None
            
            if diagnostico_content:
                logger.info("📄 Extrayendo texto del diagnóstico...")
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(diagnostico_filename).suffix) as tmp_diag:
                    tmp_diag.write(diagnostico_content)
                    tmp_diag_path = tmp_diag.name
                
                try:
                    diagnostico_result = get_text_only(tmp_diag_path)
                    
                    if diagnostico_result['success'] and diagnostico_result['text']:
                        diagnostico_text = diagnostico_result['text']
                        logger.info(f"✅ Texto extraído del diagnóstico: {len(diagnostico_text)} caracteres")
                
                finally:
                    if os.path.exists(tmp_diag_path):
                        os.remove(tmp_diag_path)
            
        finally:
            if os.path.exists(tmp_plan_path):
                os.remove(tmp_plan_path)
        
        # ========== RECUPERACIÓN RAG - VERSIÓN CORREGIDA ==========
        
        retrieved_docs = {'cuentos': [], 'canciones': []}
        rag_context_text = ""  # 🔥 ESTO ES CRÍTICO
        
        if rag_system is not None:
            logger.info("🔍 Recuperando documentos de la biblioteca RAG...")
            
            try:
                # Combinar plan y diagnóstico para búsqueda
                query_text = plan_text
                if diagnostico_text:
                    query_text = f"{plan_text}\n\n{diagnostico_text}"
                
                # Generar embedding
                query_embedding = rag_system.embeddings.embed_query(query_text)
                
                # Buscar cuentos
                logger.info("📖 Buscando cuentos relevantes...")
                cuentos_results = rag_system.vector_store.query(
                    query_embedding=query_embedding,
                    n_results=5,
                    filter_metadata={'document_type': 'cuento'}
                )
                
                for doc, metadata, distance in zip(
                    cuentos_results['documents'],
                    cuentos_results['metadatas'],
                    cuentos_results['distances']
                ):
                    retrieved_docs['cuentos'].append({
                        'text': doc,
                        'metadata': metadata,
                        'similarity': 1 - distance
                    })
                
                logger.info(f"✅ {len(retrieved_docs['cuentos'])} cuentos recuperados")
                
                # Buscar canciones
                logger.info("🎵 Buscando canciones relevantes...")
                canciones_results = rag_system.vector_store.query(
                    query_embedding=query_embedding,
                    n_results=5,
                    filter_metadata={'document_type': 'cancion'}
                )
                
                for doc, metadata, distance in zip(
                    canciones_results['documents'],
                    canciones_results['metadatas'],
                    canciones_results['distances']
                ):
                    retrieved_docs['canciones'].append({
                        'text': doc,
                        'metadata': metadata,
                        'similarity': 1 - distance
                    })
                
                logger.info(f"✅ {len(retrieved_docs['canciones'])} canciones recuperadas")
                
                # 🔥 CONSTRUIR CONTEXTO RAG PARA GEMINI
                rag_context_parts = []
                
                if retrieved_docs['cuentos']:
                    rag_context_parts.append("\n\n# 📖 CUENTOS DISPONIBLES EN LA BIBLIOTECA:")
                    for idx, cuento in enumerate(retrieved_docs['cuentos'], 1):
                        filename = cuento['metadata'].get('filename', 'Desconocido')
                        similitud = cuento['similarity'] * 100
                        texto = cuento['text'][:500]  # Primeros 500 caracteres
                        
                        rag_context_parts.append(f"""
## Cuento {idx}: {filename}
**Relevancia:** {similitud:.1f}%
**Contenido:**
{texto}
""")
                
                if retrieved_docs['canciones']:
                    rag_context_parts.append("\n\n# 🎵 CANCIONES DISPONIBLES EN LA BIBLIOTECA:")
                    for idx, cancion in enumerate(retrieved_docs['canciones'], 1):
                        filename = cancion['metadata'].get('filename', 'Desconocido')
                        similitud = cancion['similarity'] * 100
                        texto = cancion['text'][:500]
                        
                        rag_context_parts.append(f"""
## Canción {idx}: {filename}
**Relevancia:** {similitud:.1f}%
**Contenido:**
{texto}
""")
                
                # Unir todo el contexto RAG
                rag_context_text = "\n".join(rag_context_parts)
                
                logger.info(f"✅ Contexto RAG construido: {len(rag_context_text)} caracteres")
                
            except Exception as e:
                logger.warning(f"⚠️ Error en RAG, continuando sin él: {e}")
                rag_context_text = ""
        
        # ========== GENERACIÓN CON GEMINI - USANDO CONTEXTO RAG ==========
        
        logger.info("🤖 Generando plan con Gemini AI + contexto RAG...")
        
        # 🔥 AGREGAR CONTEXTO RAG AL TEXTO DEL PLAN
        enriched_plan_text = plan_text
        if rag_context_text:
            enriched_plan_text = f"""
{plan_text}

---

# RECURSOS EDUCATIVOS DISPONIBLES EN LA BIBLIOTECA DIGITAL

{rag_context_text}

---

**INSTRUCCIÓN IMPORTANTE PARA LA GENERACIÓN:**
Los recursos anteriores (cuentos y canciones) están VERIFICADOS y DISPONIBLES en la biblioteca.
Al generar el plan:
1. **PRIORIZA** estos recursos en la sección "recursos_educativos"
2. Menciona sus títulos EXACTOS como aparecen arriba
3. Marca estos recursos como "RECURSO REAL" y "GRATUITO"
4. Indica que están "Disponibles en la biblioteca digital"
5. Integra estos recursos en las actividades cuando sea relevante
"""
            logger.info("✅ Plan enriquecido con contexto RAG")
        
        # Generar con Gemini
        resultado_gemini = await generar_plan_estudio(
            plan_text=enriched_plan_text,  # 🔥 Usar el texto enriquecido
            diagnostico_text=diagnostico_text
        )
        
        if not resultado_gemini['success']:
            raise HTTPException(
                status_code=500,
                detail=f"Error generando plan con IA: {resultado_gemini.get('error')}"
            )
        
        plan_data = resultado_gemini['plan']
        
        logger.info(f"✅ Plan generado: {plan_data['nombre_plan']}")
        
        # ========== AGREGAR METADATA RAG ==========
        
        plan_id = f"plan_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"
        
        plan_data['plan_id'] = plan_id
        plan_data['usuario'] = user_email
        plan_data['fecha_generacion'] = datetime.now().isoformat()
        plan_data['archivos_originales'] = {
            'plan': plan_file.filename,
            'diagnostico': diagnostico_filename
        }
        
        # 🔥 GUARDAR METADATA RAG CORRECTAMENTE
        plan_data['rag_metadata'] = {
            'recursos_recuperados': {
                'cuentos': [
                    {
                        'nombre': c['metadata'].get('filename', ''),
                        'similitud': round(c['similarity'], 3)
                    }
                    for c in retrieved_docs['cuentos']
                ],
                'canciones': [
                    {
                        'nombre': c['metadata'].get('filename', ''),
                        'similitud': round(c['similarity'], 3)
                    }
                    for c in retrieved_docs['canciones']
                ]
            },
            'total_recuperado': len(retrieved_docs['cuentos']) + len(retrieved_docs['canciones']),
            'contexto_rag_chars': len(rag_context_text),
            'rag_usado': len(rag_context_text) > 0
        }
        
        logger.info(f"📊 Metadata RAG: {plan_data['rag_metadata']['total_recuperado']} recursos")
        
        # ========== GUARDAR EN GCS ==========
        
        plan_json = json.dumps(plan_data, indent=2, ensure_ascii=False)
        plan_json_bytes = plan_json.encode('utf-8')
        
        resultado_guardado = gcs_storage.subir_archivo_desde_bytes(
            contenido=plan_json_bytes,
            email=user_email,
            nombre_archivo=f"{plan_id}.json",
            es_procesado=True
        )
        
        if resultado_guardado['success']:
            logger.info(f"✅ Plan guardado en GCS con metadata RAG")
        
        # Subir archivos originales
        gcs_storage.subir_archivo_desde_bytes(
            contenido=plan_content,
            email=user_email,
            nombre_archivo=plan_file.filename,
            es_procesado=False
        )
        
        if diagnostico_content:
            gcs_storage.subir_archivo_desde_bytes(
                contenido=diagnostico_content,
                email=user_email,
                nombre_archivo=diagnostico_filename,
                es_procesado=False
            )
        
        # ========== RETORNAR RESULTADO ==========
        
        processing_time = time.time() - start_time
        logger.info(f"⏱️ Tiempo total: {processing_time:.2f}s")
        logger.info(f"🎉 Plan generado exitosamente con RAG")
        
        return PlanResponse(
            success=True,
            plan_id=plan_id,
            plan_data=plan_data,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generando plan: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado: {str(e)}"
        )


@app.get("/api/plans/list")
async def list_plans(
    current_user: dict = Depends(get_current_user)
):
    """
    Lista todos los planes generados del usuario
    """
    user_email = current_user["email"]
    
    try:
        # Obtener archivos JSON de la carpeta processed
        archivos_procesados = gcs_storage.listar_archivos(user_email, "processed")
        
        planes = []
        
        for archivo in archivos_procesados:
            # Solo archivos JSON que empiezan con "plan_"
            if archivo['name'].startswith('plan_') and archivo['name'].endswith('.json'):
                # Obtener el contenido del plan
                contenido = gcs_storage.obtener_archivo_bytes(
                    email=user_email,
                    nombre_archivo=archivo['name'],
                    es_procesado=True
                )
                
                if contenido:
                    try:
                        plan_data = json.loads(contenido.decode('utf-8'))
                        
                        # IMPORTANTE: Incluir TODOS los campos necesarios
                        planes.append({
                            'plan_id': plan_data.get('plan_id'),
                            'nombre_plan': plan_data.get('nombre_plan'),
                            'grado': plan_data.get('grado'),
                            
                            # ✅ NUEVA ESTRUCTURA (Preescolar mejorado)
                            'campo_formativo_principal': plan_data.get('campo_formativo_principal'),
                            'ejes_articuladores_generales': plan_data.get('ejes_articuladores_generales', []),
                            'edad_aprox': plan_data.get('edad_aprox'),
                            'duracion_total': plan_data.get('duracion_total'),
                            
                            # ❌ ESTRUCTURA ANTIGUA (para retrocompatibilidad)
                            'materia': plan_data.get('materia'),
                            
                            # Campos comunes
                            'num_modulos': plan_data.get('num_modulos', len(plan_data.get('modulos', []))),
                            'fecha_generacion': plan_data.get('fecha_generacion'),
                            'tiene_diagnostico': plan_data.get('tiene_diagnostico', False),
                            'archivos_originales': plan_data.get('archivos_originales', {}),
                            'generado_con': plan_data.get('generado_con'),
                            'modelo': plan_data.get('modelo')
                        })
                    except json.JSONDecodeError:
                        logger.warning(f"⚠️ No se pudo parsear el plan: {archivo['name']}")
        
        # Ordenar por fecha (más recientes primero)
        planes.sort(key=lambda x: x.get('fecha_generacion', ''), reverse=True)
        
        return {
            'success': True,
            'planes': planes,
            'total': len(planes)
        }
        
    except Exception as e:
        logger.error(f"❌ Error listando planes: {e}")
        raise HTTPException(status_code=500, detail=f"Error listando planes: {str(e)}")

@app.get("/api/plans/{plan_id}/download")
async def download_plan_word(
    plan_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Descarga el plan como documento Word (.docx) profesional
    """
    user_email = current_user["email"]
    
    try:
        # Obtener el plan desde GCS
        filename = f"{plan_id}.json"
        
        contenido = gcs_storage.obtener_archivo_bytes(
            email=user_email,
            nombre_archivo=filename,
            es_procesado=True
        )
        
        if not contenido:
            raise HTTPException(status_code=404, detail="Plan no encontrado")
        
        plan_data = json.loads(contenido.decode('utf-8'))
        
        # Generar documento Word
        docx_bytes = generar_documento_word(plan_data)
        
        # Crear nombre de archivo seguro
        nombre_plan = plan_data.get('nombre_plan', 'Plan_Educativo')
        nombre_archivo = f"{nombre_plan.replace(' ', '_').replace('/', '_')}.docx"
        
        # Retornar archivo Word
        return StreamingResponse(
            docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename={nombre_archivo}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generando documento Word: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando documento: {str(e)}")


@app.get("/api/plans/{plan_id}")
async def get_plan_detail(
    plan_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene el detalle completo de un plan específico
    """
    user_email = current_user["email"]
    
    try:
        # Obtener el archivo JSON del plan
        filename = f"{plan_id}.json"
        
        contenido = gcs_storage.obtener_archivo_bytes(
            email=user_email,
            nombre_archivo=filename,
            es_procesado=True
        )
        
        if not contenido:
            raise HTTPException(status_code=404, detail="Plan no encontrado")
        
        plan_data = json.loads(contenido.decode('utf-8'))
        
        return {
            'success': True,
            'plan': plan_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo plan: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo plan: {str(e)}")


@app.delete("/api/plans/{plan_id}")
@limiter.limit("10/minute")
async def delete_plan(
    request: Request,
    plan_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Elimina un plan generado
    """
    user_email = current_user["email"]
    
    try:
        filename = f"{plan_id}.json"
        
        resultado = gcs_storage.eliminar_archivo(
            email=user_email,
            nombre_archivo=filename,
            es_procesado=True
        )
        
        if not resultado['success']:
            raise HTTPException(status_code=404, detail="Plan no encontrado")
        
        return {
            'success': True,
            'message': 'Plan eliminado correctamente'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error eliminando plan: {e}")
        raise HTTPException(status_code=500, detail=f"Error eliminando plan: {str(e)}")
    
    @app.get("/api/rag/metrics/latest")
    async def get_latest_rag_metrics(current_user: dict = Depends(get_current_user)):
        """
        Obtiene las métricas de la última sesión RAG del usuario
        DEMUESTRA QUE RAG ESTÁ FUNCIONANDO
        """
    try:
        user_email = current_user["email"]
        metrics_file = "./rag_data/rag_metrics.json"
        
        if not Path(metrics_file).exists():
            return {
                'success': False,
                'message': 'No hay métricas disponibles'
            }
        
        # Cargar métricas
        with open(metrics_file, 'r', encoding='utf-8') as f:
            all_metrics = json.load(f)
        
        # Filtrar por usuario y obtener la más reciente
        user_metrics = [m for m in all_metrics if m['user_email'] == user_email]
        
        if not user_metrics:
            return {
                'success': False,
                'message': f'No hay métricas para el usuario {user_email}'
            }
        
        latest = user_metrics[-1]  # La más reciente
        
        # Generar reporte visual
        metrics_instance = get_metrics_instance()
        metrics_instance.current_session = latest
        report = metrics_instance.generate_report()
        
        return {
            'success': True,
            'metrics': latest,
            'report': report,
            'summary': {
                'recursos_rag_recuperados': latest['retrieval_metrics']['total_retrieved'],
                'recursos_rag_utilizados': latest['rag_impact']['recursos_rag_utilizados'],
                'porcentaje_rag': latest['rag_impact']['porcentaje_recursos_rag'],
                'evidencias': latest['rag_impact']['evidencias_rag']
            }
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/metrics/all")
async def get_all_rag_metrics(current_user: dict = Depends(get_current_user)):
    """
    Obtiene todas las métricas RAG del usuario
    """
    try:
        user_email = current_user["email"]
        metrics_file = "./rag_data/rag_metrics.json"
        
        if not Path(metrics_file).exists():
            return {
                'success': False,
                'sessions': []
            }
        
        with open(metrics_file, 'r', encoding='utf-8') as f:
            all_metrics = json.load(f)
        
        user_metrics = [m for m in all_metrics if m['user_email'] == user_email]
        
        return {
            'success': True,
            'total_sessions': len(user_metrics),
            'sessions': user_metrics
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/demo")
async def rag_demo_comparison():
    """
    ENDPOINT DE DEMOSTRACIÓN
    Muestra la diferencia entre usar RAG vs no usar RAG
    """
    return {
        'title': 'Demostración del Sistema RAG',
        'sin_rag': {
            'descripcion': 'Generación tradicional solo con Gemini AI',
            'proceso': [
                '1. Usuario sube plan de estudios',
                '2. OCR extrae texto',
                '3. Gemini genera plan genérico',
                '4. Recursos recomendados son inventados o genéricos'
            ],
            'limitaciones': [
                '❌ No acceso a biblioteca de recursos reales',
                '❌ Recomendaciones genéricas',
                '❌ Sin personalización por contexto histórico',
                '❌ Recursos pueden no existir'
            ]
        },
        'con_rag': {
            'descripcion': 'Generación mejorada con RAG + Gemini AI',
            'proceso': [
                '1. Usuario sube plan de estudios + diagnóstico',
                '2. OCR extrae texto',
                '3. Sistema indexa documentos del usuario',
                '4. Vector store busca cuentos y canciones relevantes',
                '5. Gemini recibe contexto enriquecido con recursos reales',
                '6. Plan generado incluye recursos verificados de la biblioteca'
            ],
            'beneficios': [
                '✅ Acceso a biblioteca de 📚 cuentos + 🎵 canciones reales',
                '✅ Búsqueda semántica (encuentra recursos por significado)',
                '✅ Recursos verificados que existen en la biblioteca',
                '✅ Actividades basadas en materiales disponibles',
                '✅ Personalización según el diagnóstico del grupo',
                '✅ Métricas demostrables del impacto RAG'
            ]
        },
        'metricas_ejemplo': {
            'descripcion': 'Ejemplo de métricas RAG capturadas',
            'indexing': {
                'plan_chunks': 15,
                'diagnostico_chunks': 8,
                'embeddings_generados': 23,
                'tiempo': '2.5s'
            },
            'retrieval': {
                'cuentos_recuperados': 5,
                'canciones_recuperadas': 5,
                'similitud_promedio': '78%',
                'tiempo': '0.8s'
            },
            'impacto': {
                'recursos_rag_utilizados': 7,
                'actividades_basadas_rag': 4,
                'porcentaje_recursos_rag': '70%',
                'evidencias': [
                    "✅ Cuento 'El patito feo' mencionado en módulo 2",
                    "✅ Canción 'Los pollitos dicen' integrada en actividad de inicio",
                    "✅ Actividad basada en 'La tortuga y la liebre'"
                ]
            }
        },
        'como_verificar': {
            'paso_1': 'Genera un plan con RAG',
            'paso_2': 'Consulta GET /api/rag/metrics/latest',
            'paso_3': 'Revisa el campo "rag_impact" para ver evidencias',
            'paso_4': 'Compara "recursos_recuperados" vs "recursos_educativos" del plan',
            'paso_5': 'Verifica que los recursos del plan existen en rag_data/cuentos o rag_data/canciones'
        }
    }


@app.get("/api/rag/verification/{plan_id}")
async def verify_rag_usage_in_plan(
    plan_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    VERIFICACIÓN DETALLADA: Demuestra que un plan específico usó RAG
    
    Compara los recursos del plan vs los recursos de la biblioteca RAG
    """
    try:
        user_email = current_user["email"]
        
        # Obtener el plan
        filename = f"{plan_id}.json"
        contenido = gcs_storage.obtener_archivo_bytes(
            email=user_email,
            nombre_archivo=filename,
            es_procesado=True
        )
        
        if not contenido:
            raise HTTPException(status_code=404, detail="Plan no encontrado")
        
        plan_data = json.loads(contenido.decode('utf-8'))
        
        # Obtener métricas RAG de este plan
        rag_metadata = plan_data.get('rag_metadata', {})
        
        if not rag_metadata:
            return {
                'success': False,
                'message': 'Este plan no tiene metadata RAG (generado sin RAG)',
                'plan_name': plan_data.get('nombre_plan')
            }
        
        # Extraer recursos del plan
        recursos_plan = plan_data.get('recursos_educativos', {})
        cuentos_plan = recursos_plan.get('cuentos_recomendados', [])
        canciones_plan = recursos_plan.get('canciones_recomendadas', [])
        
        # Comparar con recursos recuperados de RAG
        recursos_rag = rag_metadata.get('recursos_recuperados', {})
        cuentos_rag = recursos_rag.get('cuentos', [])
        canciones_rag = recursos_rag.get('canciones', [])
        
        # Análisis de coincidencias
        coincidencias_cuentos = []
        for cuento_plan in cuentos_plan:
            titulo_plan = cuento_plan.get('titulo', '').lower()
            for cuento_rag in cuentos_rag:
                nombre_rag = Path(cuento_rag['nombre']).stem.lower()
                if nombre_rag in titulo_plan or titulo_plan in nombre_rag:
                    coincidencias_cuentos.append({
                        'titulo_plan': cuento_plan.get('titulo'),
                        'archivo_rag': cuento_rag['nombre'],
                        'similitud_rag': cuento_rag['similitud'],
                        'match': True
                    })
        
        coincidencias_canciones = []
        for cancion_plan in canciones_plan:
            titulo_plan = cancion_plan.get('titulo', '').lower()
            for cancion_rag in canciones_rag:
                nombre_rag = Path(cancion_rag['nombre']).stem.lower()
                if nombre_rag in titulo_plan or titulo_plan in nombre_rag:
                    coincidencias_canciones.append({
                        'titulo_plan': cancion_plan.get('titulo'),
                        'archivo_rag': cancion_rag['nombre'],
                        'similitud_rag': cancion_rag['similitud'],
                        'match': True
                    })
        
        total_coincidencias = len(coincidencias_cuentos) + len(coincidencias_canciones)
        total_recursos = len(cuentos_plan) + len(canciones_plan)
        
        porcentaje_rag = (total_coincidencias / total_recursos * 100) if total_recursos > 0 else 0
        
        return {
            'success': True,
            'plan_name': plan_data.get('nombre_plan'),
            'plan_id': plan_id,
            'verificacion': {
                'total_recursos_plan': total_recursos,
                'total_coincidencias_rag': total_coincidencias,
                'porcentaje_rag': round(porcentaje_rag, 1),
                'usa_rag': total_coincidencias > 0
            },
            'evidencias': {
                'cuentos': {
                    'total_en_plan': len(cuentos_plan),
                    'provenientes_de_rag': len(coincidencias_cuentos),
                    'coincidencias': coincidencias_cuentos
                },
                'canciones': {
                    'total_en_plan': len(canciones_plan),
                    'provenientes_de_rag': len(coincidencias_canciones),
                    'coincidencias': coincidencias_canciones
                }
            },
            'metadata_rag_completa': rag_metadata,
            'recursos_rag_recuperados': {
                'cuentos_recuperados': len(cuentos_rag),
                'canciones_recuperadas': len(canciones_rag),
                'listado_cuentos': [c['nombre'] for c in cuentos_rag],
                'listado_canciones': [c['nombre'] for c in canciones_rag]
            },
            'conclusion': f"✅ El plan utilizó RAG: {porcentaje_rag:.1f}% de los recursos provienen de la biblioteca RAG" if total_coincidencias > 0 else "❌ El plan no utilizó recursos de RAG"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verificando RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# REEMPLAZAR LA CLASE RAGAnalyzer EN main.py
# Esta versión detecta mejor el uso de recursos RAG
# ==============================================================================

class RAGAnalyzer:
    """
    Analizador avanzado de similitud semántica entre planes y recursos RAG
    VERSIÓN MEJORADA - DETECTA USO SEMÁNTICO
    """
    
    def __init__(self, rag_system):
        self.rag_system = rag_system
    
    def analyze_plan_rag_match(
        self,
        plan_data: Dict,
        retrieved_docs: Dict,
        threshold: float = 0.48  # 48% de similitud mínima
    ) -> Dict:
        """
        Analiza la similitud entre el plan generado y los recursos RAG
        VERSIÓN MEJORADA - Detecta uso semántico de recursos
        """
        analisis = {
            'similitud_general': 0.0,
            'recursos_altamente_relevantes': [],
            'recursos_por_modulo': [],
            'metricas_rag': {
                'total_recursos_rag': 0,
                'recursos_utilizados': 0,
                'porcentaje_uso_rag': 0.0,
                'similitud_promedio': 0.0
            },
            'recomendaciones_adicionales': []
        }
        
        # Extraer texto completo del plan
        plan_text = self._extract_plan_text(plan_data)
        plan_text_lower = plan_text.lower()
        
        # Combinar todos los recursos
        all_resources = []
        
        cuentos = retrieved_docs.get('cuentos', [])
        canciones = retrieved_docs.get('canciones', [])
        
        analisis['metricas_rag']['total_recursos_rag'] = len(cuentos) + len(canciones)
        
        # 🔥 ANÁLISIS MEJORADO: Buscar coincidencias semánticas
        recursos_encontrados = []
        
        for cuento in cuentos:
            filename = cuento['metadata'].get('filename', '')
            # Limpiar nombre del archivo
            clean_name = Path(filename).stem.replace('_', ' ').lower()
            similitud = cuento.get('similarity', 0)
            
            # Verificar si el recurso aparece en el plan (flexible)
            usado = False
            keywords = clean_name.split()[:3]  # Primeras 3 palabras
            
            for keyword in keywords:
                if len(keyword) > 3 and keyword in plan_text_lower:
                    usado = True
                    break
            
            # También revisar si está en la sección de recursos
            recursos_plan = plan_data.get('recursos_educativos', {})
            cuentos_recomendados = recursos_plan.get('cuentos_recomendados', [])
            
            for cuento_rec in cuentos_recomendados:
                titulo = cuento_rec.get('titulo', '').lower()
                if any(kw in titulo for kw in keywords if len(kw) > 3):
                    usado = True
                    break
            
            if usado or similitud >= 0.60:  # Baja el threshold
                recurso_info = self._format_recurso(cuento, 'cuento', similitud)
                recursos_encontrados.append(recurso_info)
                if usado:
                    analisis['metricas_rag']['recursos_utilizados'] += 1
        
        for cancion in canciones:
            filename = cancion['metadata'].get('filename', '')
            clean_name = Path(filename).stem.replace('_', ' ').lower()
            similitud = cancion.get('similarity', 0)
            
            usado = False
            keywords = clean_name.split()[:3]
            
            for keyword in keywords:
                if len(keyword) > 3 and keyword in plan_text_lower:
                    usado = True
                    break
            
            recursos_plan = plan_data.get('recursos_educativos', {})
            canciones_recomendadas = recursos_plan.get('canciones_recomendadas', [])
            
            for cancion_rec in canciones_recomendadas:
                titulo = cancion_rec.get('titulo', '').lower()
                if any(kw in titulo for kw in keywords if len(kw) > 3):
                    usado = True
                    break
            
            if usado or similitud >= 0.60:
                recurso_info = self._format_recurso(cancion, 'cancion', similitud)
                recursos_encontrados.append(recurso_info)
                if usado:
                    analisis['metricas_rag']['recursos_utilizados'] += 1
        
        # Ordenar por similitud
        recursos_encontrados.sort(key=lambda x: x['similitud_porcentaje'], reverse=True)
        analisis['recursos_altamente_relevantes'] = recursos_encontrados
        
        # 🔥 CALCULAR PORCENTAJE BASADO EN RECURSOS_EDUCATIVOS
        recursos_plan = plan_data.get('recursos_educativos', {})
        total_cuentos_plan = len(recursos_plan.get('cuentos_recomendados', []))
        total_canciones_plan = len(recursos_plan.get('canciones_recomendadas', []))
        total_recursos_plan = total_cuentos_plan + total_canciones_plan
        
        if total_recursos_plan > 0:
            # Contar cuántos recursos del plan tienen origen RAG
            recursos_rag_en_plan = 0
            
            for cuento_plan in recursos_plan.get('cuentos_recomendados', []):
                if cuento_plan.get('tipo') == 'RECURSO REAL':
                    recursos_rag_en_plan += 1
            
            for cancion_plan in recursos_plan.get('canciones_recomendadas', []):
                if cancion_plan.get('tipo') == 'RECURSO REAL':
                    recursos_rag_en_plan += 1
            
            analisis['metricas_rag']['recursos_utilizados'] = max(
                analisis['metricas_rag']['recursos_utilizados'],
                recursos_rag_en_plan
            )
            
            analisis['metricas_rag']['porcentaje_uso_rag'] = round(
                (recursos_rag_en_plan / total_recursos_plan) * 100,
                1
            )
        elif analisis['metricas_rag']['total_recursos_rag'] > 0:
            # Fallback: usar recursos utilizados vs recuperados
            analisis['metricas_rag']['porcentaje_uso_rag'] = round(
                (analisis['metricas_rag']['recursos_utilizados'] / 
                 analisis['metricas_rag']['total_recursos_rag']) * 100,
                1
            )
        
        # Calcular similitud promedio
        if recursos_encontrados:
            analisis['metricas_rag']['similitud_promedio'] = round(
                sum(r['similitud_porcentaje'] for r in recursos_encontrados) / len(recursos_encontrados),
                1
            )
        
        # Analizar por módulo
        analisis['recursos_por_modulo'] = self._analyze_modules(
            plan_data,
            retrieved_docs,
            threshold
        )
        
        logger.info(f"📊 Análisis RAG completado:")
        logger.info(f"   Total recuperado: {analisis['metricas_rag']['total_recursos_rag']}")
        logger.info(f"   Recursos utilizados: {analisis['metricas_rag']['recursos_utilizados']}")
        logger.info(f"   Porcentaje uso: {analisis['metricas_rag']['porcentaje_uso_rag']}%")
        logger.info(f"   Similitud promedio: {analisis['metricas_rag']['similitud_promedio']}%")
        
        return analisis
    
    def _extract_plan_text(self, plan_data: Dict) -> str:
        """Extrae el texto completo del plan para análisis"""
        texts = []
        
        texts.append(plan_data.get('nombre_plan', ''))
        texts.append(plan_data.get('campo_formativo_principal', ''))
        
        for modulo in plan_data.get('modulos', []):
            texts.append(modulo.get('nombre', ''))
            texts.append(modulo.get('aprendizaje_esperado', ''))
            
            if modulo.get('actividad_inicio'):
                texts.append(modulo['actividad_inicio'].get('descripcion', ''))
            
            for act in modulo.get('actividades_desarrollo', []):
                texts.append(act.get('descripcion', ''))
            
            if modulo.get('actividad_cierre'):
                texts.append(modulo['actividad_cierre'].get('descripcion', ''))
        
        # También incluir recursos educativos
        recursos = plan_data.get('recursos_educativos', {})
        
        for cuento in recursos.get('cuentos_recomendados', []):
            texts.append(cuento.get('titulo', ''))
            texts.append(cuento.get('descripcion_breve', ''))
        
        for cancion in recursos.get('canciones_recomendadas', []):
            texts.append(cancion.get('titulo', ''))
        
        return ' '.join(filter(None, texts))
    
    def _format_recurso(self, doc: Dict, tipo: str, similitud: float) -> Dict:
        """Formatea un recurso RAG para presentación"""
        metadata = doc.get('metadata', {})
        texto = doc.get('text', '')
        
        # Extraer título del nombre del archivo
        filename = metadata.get('filename', 'Recurso desconocido')
        titulo = Path(filename).stem.replace('_', ' ').title()
        
        return {
            'titulo': titulo,
            'tipo': tipo,
            'fuente': 'RECURSO REAL',
            'similitud_porcentaje': round(similitud * 100, 1),
            'similitud_nivel': self._get_similarity_level(similitud),
            'contenido_completo': texto,
            'fragmento': texto[:300] + '...' if len(texto) > 300 else texto,
            'filename': filename,
            'acceso': 'GRATUITO',
            'markdown_formato': f"""---
### 📚 {titulo}

**Tipo:** {tipo.upper()}  
**Disponibilidad:** Biblioteca Digital ProfeGo  
**Acceso:** GRATUITO  
**Similitud con el plan:** {round(similitud * 100, 1)}%

**Contenido:**

{texto[:500]}...

---
"""
        }
    
    def _get_similarity_level(self, similitud: float) -> str:
        """Clasifica el nivel de similitud"""
        if similitud >= 0.75:
            return 'MUY ALTA'
        elif similitud >= 0.60:
            return 'ALTA'
        elif similitud >= 0.48:
            return 'MEDIA'
        elif similitud >= 0.30:
            return 'MEDIA-BAJA'
        else:
            return 'BAJA'
    
    def _analyze_modules(
        self,
        plan_data: Dict,
        retrieved_docs: Dict,
        threshold: float
    ) -> List[Dict]:
        """Analiza similitud por módulo"""
        modulos_analisis = []
        
        for modulo in plan_data.get('modulos', []):
            modulo_text = f"{modulo.get('nombre', '')} {modulo.get('aprendizaje_esperado', '')}"
            modulo_text_lower = modulo_text.lower()
            
            if not modulo_text.strip():
                continue
            
            recursos_modulo = []
            
            # Buscar cuentos relacionados
            for cuento in retrieved_docs.get('cuentos', []):
                filename = cuento['metadata'].get('filename', '')
                clean_name = Path(filename).stem.replace('_', ' ')
                similitud = cuento.get('similarity', 0)
                
                # Verificar si aparece en el módulo
                keywords = clean_name.lower().split()[:3]
                if any(kw in modulo_text_lower for kw in keywords if len(kw) > 3):
                    recursos_modulo.append({
                        'titulo': clean_name.title(),
                        'tipo': 'cuento',
                        'similitud': round(similitud * 100, 1)
                    })
            
            # Buscar canciones relacionadas
            for cancion in retrieved_docs.get('canciones', []):
                filename = cancion['metadata'].get('filename', '')
                clean_name = Path(filename).stem.replace('_', ' ')
                similitud = cancion.get('similarity', 0)
                
                keywords = clean_name.lower().split()[:3]
                if any(kw in modulo_text_lower for kw in keywords if len(kw) > 3):
                    recursos_modulo.append({
                        'titulo': clean_name.title(),
                        'tipo': 'cancion',
                        'similitud': round(similitud * 100, 1)
                    })
            
            if recursos_modulo:
                modulos_analisis.append({
                    'numero': modulo.get('numero', 0),
                    'nombre': modulo.get('nombre', ''),
                    'recursos_relacionados': recursos_modulo[:5]  # Top 5
                })
        
        return modulos_analisis


# Instancia global del analizador
rag_analyzer = None


@app.on_event("startup")
async def initialize_rag_analyzer():
    """Inicializa el analizador RAG al arranque"""
    global rag_analyzer
    
    if rag_system is not None:
        rag_analyzer = RAGAnalyzer(rag_system)
        logger.info("✅ RAG Analyzer inicializado")


@app.get("/api/plans/{plan_id}/rag-analysis")
async def analyze_plan_rag(
    plan_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint MEJORADO: Análisis completo de similitud RAG
    Con mejor manejo de errores y datos faltantes
    """
    user_email = current_user["email"]
    
    try:
        logger.info(f"🔍 Iniciando análisis RAG para plan: {plan_id}")
        
        # Verificar que el analizador RAG existe
        if rag_analyzer is None or rag_system is None:
            logger.warning("Sistema RAG no disponible")
            return {
                'success': False,
                'message': 'El sistema de análisis RAG no está disponible en este momento. Asegúrate de que la biblioteca RAG esté inicializada.'
            }
        
        # Obtener el plan
        filename = f"{plan_id}.json"
        contenido = gcs_storage.obtener_archivo_bytes(
            email=user_email,
            nombre_archivo=filename,
            es_procesado=True
        )
        
        if not contenido:
            logger.warning(f"Plan no encontrado: {plan_id}")
            raise HTTPException(status_code=404, detail="Plan no encontrado")
        
        plan_data = json.loads(contenido.decode('utf-8'))
        logger.info(f"✅ Plan cargado: {plan_data.get('nombre_plan')}")
        
        # Verificar metadata RAG
        rag_metadata = plan_data.get('rag_metadata', {})
        
        if not rag_metadata or not rag_metadata.get('recursos_recuperados'):
            logger.warning(f"Plan sin metadata RAG: {plan_id}")
            return {
                'success': False,
                'message': 'Este plan no tiene metadata RAG. Fue generado antes de implementar el sistema RAG o sin recursos en la biblioteca.',
                'plan_name': plan_data.get('nombre_plan'),
                'sugerencia': 'Genera un nuevo plan para que incluya análisis RAG automáticamente.'
            }
        
        # Reconstruir retrieved_docs desde metadata
        retrieved_docs = {
            'cuentos': [],
            'canciones': []
        }
        
        logger.info("📚 Reconstruyendo documentos RAG desde metadata...")
        
        recursos_metadata = rag_metadata.get('recursos_recuperados', {})
        
        # Buscar cuentos en el filesystem
        cuentos_dir = Path('./rag_data/cuentos')
        for cuento_meta in recursos_metadata.get('cuentos', []):
            filename_cuento = cuento_meta.get('nombre', '')
            if not filename_cuento:
                continue
                
            cuento_path = cuentos_dir / filename_cuento
            
            if cuento_path.exists():
                try:
                    with open(cuento_path, 'r', encoding='utf-8') as f:
                        contenido_cuento = f.read()
                    
                    retrieved_docs['cuentos'].append({
                        'text': contenido_cuento,
                        'metadata': {
                            'filename': filename_cuento,
                            'document_type': 'cuento'
                        },
                        'similarity': cuento_meta.get('similitud', 0.75)
                    })
                    logger.info(f"✅ Cuento cargado: {filename_cuento}")
                except Exception as e:
                    logger.warning(f"⚠️ Error leyendo cuento {filename_cuento}: {e}")
            else:
                logger.warning(f"⚠️ Cuento no encontrado: {cuento_path}")
        
        # Buscar canciones en el filesystem
        canciones_dir = Path('./rag_data/canciones')
        for cancion_meta in recursos_metadata.get('canciones', []):
            filename_cancion = cancion_meta.get('nombre', '')
            if not filename_cancion:
                continue
                
            cancion_path = canciones_dir / filename_cancion
            
            if cancion_path.exists():
                try:
                    with open(cancion_path, 'r', encoding='utf-8') as f:
                        contenido_cancion = f.read()
                    
                    retrieved_docs['canciones'].append({
                        'text': contenido_cancion,
                        'metadata': {
                            'filename': filename_cancion,
                            'document_type': 'cancion'
                        },
                        'similarity': cancion_meta.get('similitud', 0.75)
                    })
                    logger.info(f"✅ Canción cargada: {filename_cancion}")
                except Exception as e:
                    logger.warning(f"⚠️ Error leyendo canción {filename_cancion}: {e}")
            else:
                logger.warning(f"⚠️ Canción no encontrada: {cancion_path}")
        
        total_recursos = len(retrieved_docs['cuentos']) + len(retrieved_docs['canciones'])
        logger.info(f"📊 Total recursos cargados: {total_recursos}")
        
        if total_recursos == 0:
            return {
                'success': False,
                'message': 'No se pudieron cargar los recursos RAG desde el filesystem. Es posible que los archivos hayan sido eliminados.',
                'plan_name': plan_data.get('nombre_plan')
            }
        
        # Realizar análisis
        logger.info("🔬 Analizando similitud semántica...")
        analisis = rag_analyzer.analyze_plan_rag_match(
            plan_data,
            retrieved_docs,
            threshold=0.65
        )
        
        logger.info(f"✅ Análisis completado: {analisis['metricas_rag']['porcentaje_uso_rag']}% uso RAG")
        
        # Generar recursos formateados
        recursos_completos = []
        for recurso in analisis['recursos_altamente_relevantes']:
            recursos_completos.append({
                **recurso,
                'markdown_formato': f"""---
### 📚 Recurso Musical o Literario Relacionado

**Título:** {recurso['titulo']}  
**Tipo:** {recurso['tipo'].upper()}  
**Fuente:** {recurso['fuente']}  
**Similitud con el plan:** {recurso['similitud_porcentaje']}% ({recurso['similitud_nivel']})  
**Acceso:** {recurso['acceso']}

**Contenido completo:**

{recurso['contenido_completo']}

---
"""
            })
        
        return {
            'success': True,
            'plan_id': plan_id,
            'plan_name': plan_data.get('nombre_plan'),
            'analisis': analisis,
            'recursos_completos': recursos_completos
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error analizando RAG: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'Error inesperado al analizar RAG: {str(e)}',
            'error_type': type(e).__name__
        }


@app.get("/api/plans/{plan_id}/rag-metrics")
async def get_plan_rag_metrics(
    plan_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint simplificado: Solo métricas RAG de un plan
    """
    user_email = current_user["email"]
    
    try:
        analysis_response = await analyze_plan_rag(plan_id, current_user)
        
        if not analysis_response['success']:
            return analysis_response
        
        analisis = analysis_response['analisis']
        
        return {
            'success': True,
            'plan_id': plan_id,
            'plan_name': analysis_response['plan_name'],
            'metricas': analisis['metricas_rag'],
            'recursos_count': len(analisis['recursos_altamente_relevantes']),
            'similitud_general': analisis['metricas_rag']['similitud_promedio']
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/api/rag/debug/status")
async def rag_debug_status():
    """
    Endpoint de debug para verificar estado del sistema RAG
    """
    cuentos_path = Path('./rag_data/cuentos')
    canciones_path = Path('./rag_data/canciones')
    
    cuentos_files = list(cuentos_path.glob('**/*.txt')) if cuentos_path.exists() else []
    canciones_files = list(canciones_path.glob('**/*.txt')) if canciones_path.exists() else []
    
    status = {
        'rag_system_initialized': rag_system is not None,
        'rag_analyzer_initialized': rag_analyzer is not None,
        'filesystem': {
            'cuentos_dir_exists': cuentos_path.exists(),
            'canciones_dir_exists': canciones_path.exists(),
            'cuentos_files': [f.name for f in cuentos_files],
            'canciones_files': [f.name for f in canciones_files],
            'total_files': len(cuentos_files) + len(canciones_files)
        }
    }
    
    if rag_system:
        stats = rag_system.get_stats()
        status['vector_store'] = stats
    
    return status

# ============================================================================
# RUTAS PARA SERVIR EL FRONTEND
# ============================================================================

@app.get("/")
async def serve_index():
    """Servir index.html (redirección a login)"""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return JSONResponse(
            content={
                "message": "ProfeGo API v2.0",
                "status": "running",
                "docs": "/docs",
                "error": "Frontend no encontrado"
            },
            status_code=404
        )

@app.get("/login.html")
async def serve_login():
    """Servir login.html"""
    login_path = os.path.join(FRONTEND_DIR, "login.html")
    
    if os.path.exists(login_path):
        return FileResponse(login_path)
    else:
        raise HTTPException(status_code=404, detail="login.html no encontrado")

@app.get("/menu.html")
async def serve_menu():
    """Servir menu.html"""
    menu_path = os.path.join(FRONTEND_DIR, "menu.html")
    
    if os.path.exists(menu_path):
        return FileResponse(menu_path)
    else:
        raise HTTPException(status_code=404, detail="menu.html no encontrado")

# ========== RUTAS PARA ARCHIVOS ESTÁTICOS ==========

@app.get("/styles.css")
async def serve_styles():
    """Servir styles.css"""
    styles_path = os.path.join(FRONTEND_DIR, "styles.css")
    
    if os.path.exists(styles_path):
        return FileResponse(styles_path, media_type="text/css")
    else:
        raise HTTPException(status_code=404, detail="styles.css no encontrado")

@app.get("/shared.js")
async def serve_shared_js():
    """Servir shared.js"""
    shared_path = os.path.join(FRONTEND_DIR, "shared.js")
    
    if os.path.exists(shared_path):
        return FileResponse(shared_path, media_type="application/javascript")
    else:
        raise HTTPException(status_code=404, detail="shared.js no encontrado")

@app.get("/login-script.js")
async def serve_login_script():
    """Servir login-script.js"""
    script_path = os.path.join(FRONTEND_DIR, "login-script.js")
    
    if os.path.exists(script_path):
        return FileResponse(script_path, media_type="application/javascript")
    else:
        raise HTTPException(status_code=404, detail="login-script.js no encontrado")

@app.get("/menu-script.js")
async def serve_menu_script():
    """Servir menu-script.js"""
    script_path = os.path.join(FRONTEND_DIR, "menu-script.js")
    
    if os.path.exists(script_path):
        return FileResponse(script_path, media_type="application/javascript")
    else:
        raise HTTPException(status_code=404, detail="menu-script.js no encontrado")

@app.get("/health")
async def health_check():
    """Verificar estado del servicio"""
    try:
        gcs_status = "connected" if gcs_storage.bucket.exists() else "disconnected"
        
        # Verificar si Gemini está configurado
        gemini_configured = bool(os.getenv("GEMINI_API_KEY"))
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "gcs_status": gcs_status,
            "bucket_name": gcs_storage.bucket_name,
            "frontend_dir": FRONTEND_DIR,
            "frontend_exists": os.path.exists(FRONTEND_DIR),
            "gemini_configured": gemini_configured,
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 ProfeGo API v2.0 - Servidor Iniciando")
    print("=" * 60)
    print(f"📁 Frontend: {FRONTEND_DIR}")
    print(f"☁️ GCS Bucket: {gcs_storage.bucket_name}")
    print(f"📦 Límite de archivo: {MAX_FILE_SIZE / (1024*1024)}MB")
    print(f"🔐 CORS Origins: {allowed_origins}")
    print(f"🤖 Gemini AI: {'✅ Configurado' if os.getenv('GEMINI_API_KEY') else '❌ No configurado'}")
    print(f"🌐 Servidor: http://127.0.0.1:8000")
    print(f"📖 Docs: http://127.0.0.1:8000/docs")
    print("=" * 60)

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")