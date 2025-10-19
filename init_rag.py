"""
Script de inicialización del sistema RAG
Ejecutar una vez para configurar la biblioteca general
"""

import sys
import logging
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def create_directories():
    """Crea las carpetas necesarias"""
    directories = [
        './rag_data/cuentos',
        './rag_data/canciones',
        './rag_data/vector_db'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Directorio creado: {directory}")

def main():
    """Función principal"""
    print("=" * 60)
    print("INICIALIZACION DEL SISTEMA RAG - ProfeGo")
    print("=" * 60)
    
    # Crear directorios
    logger.info("Creando estructura de directorios...")
    create_directories()
    
    # Inicializar sistema RAG
    logger.info("Inicializando sistema RAG...")
    
    try:
        from rag_system import RAGSystem
        rag_system = RAGSystem()
        logger.info("Sistema RAG inicializado correctamente")
    except Exception as e:
        logger.error(f"ERROR al inicializar RAGSystem: {type(e).__name__}")
        logger.error(f"Detalle: {str(e)}")
        import traceback
        logger.error(f"Traceback completo:\n{traceback.format_exc()}")
        return
    
    # Verificar si hay archivos en las carpetas
    cuentos_path = Path('./rag_data/cuentos')
    canciones_path = Path('./rag_data/canciones')
    
    cuentos_count = len(list(cuentos_path.glob('**/*.*')))
    canciones_count = len(list(canciones_path.glob('**/*.*')))
    
    print(f"\nESTADISTICAS ACTUALES:")
    print(f"   Cuentos encontrados: {cuentos_count}")
    print(f"   Canciones encontradas: {canciones_count}")
    
    if cuentos_count == 0 and canciones_count == 0:
        print("\nNo se encontraron archivos en la biblioteca general")
        print("Agrega archivos .pdf, .docx o .txt en:")
        print(f"   - {cuentos_path.absolute()}")
        print(f"   - {canciones_path.absolute()}")
        print("\nDespues ejecuta este script nuevamente para indexarlos")
        return
    
    # Indexar biblioteca
    print("\nIndexando biblioteca general...")
    print("Este proceso puede tardar varios minutos...")
    
    try:
        success = rag_system.initialize_general_library()
        
        if success:
            stats = rag_system.get_stats()
            print("\nINICIALIZACION COMPLETADA")
            print(f"Documentos indexados: {stats['total_documents']}")
            print("=" * 60)
        else:
            print("\nError durante la inicializacion")
            print("Revisa los logs para mas detalles")
    except Exception as e:
        logger.error(f"ERROR durante initialize_general_library: {type(e).__name__}")
        logger.error(f"Detalle: {str(e)}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()