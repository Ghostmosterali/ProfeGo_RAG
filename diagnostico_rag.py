"""
Script de diagnóstico completo del sistema RAG
"""

import sys
from pathlib import Path
import json

# Agregar path
sys.path.insert(0, str(Path(__file__).parent))

print("="*80)
print("🔍 DIAGNÓSTICO COMPLETO DEL SISTEMA RAG")
print("="*80)

# ============================================================================
# 1. VERIFICAR ARCHIVOS EN LA BIBLIOTECA
# ============================================================================

print("\n📚 PASO 1: Verificando archivos en la biblioteca...")

cuentos_dir = Path('./rag_data/cuentos')
canciones_dir = Path('./rag_data/canciones')

print(f"\n📂 Directorio cuentos: {cuentos_dir.absolute()}")
print(f"   ¿Existe? {cuentos_dir.exists()}")

if cuentos_dir.exists():
    cuentos = list(cuentos_dir.glob('**/*.txt'))
    print(f"   Archivos .txt encontrados: {len(cuentos)}")
    for cuento in cuentos:
        print(f"      - {cuento.name} ({cuento.stat().st_size} bytes)")
else:
    print("   ❌ Directorio no existe")

print(f"\n📂 Directorio canciones: {canciones_dir.absolute()}")
print(f"   ¿Existe? {canciones_dir.exists()}")

if canciones_dir.exists():
    canciones = list(canciones_dir.glob('**/*.txt'))
    print(f"   Archivos .txt encontrados: {len(canciones)}")
    for cancion in canciones:
        print(f"      - {cancion.name} ({cancion.stat().st_size} bytes)")
else:
    print("   ❌ Directorio no existe")

# ============================================================================
# 2. VERIFICAR VECTOR STORE
# ============================================================================

print("\n🗄️ PASO 2: Verificando Vector Store (ChromaDB)...")

vector_db_path = Path('./rag_data/vector_db')
print(f"   Ruta: {vector_db_path.absolute()}")
print(f"   ¿Existe? {vector_db_path.exists()}")

if vector_db_path.exists():
    db_files = list(vector_db_path.glob('**/*'))
    print(f"   Archivos en vector_db: {len(db_files)}")

try:
    from rag_system import RAGSystem
    
    rag = RAGSystem()
    stats = rag.get_stats()
    
    print(f"\n   ✅ RAG System inicializado correctamente")
    print(f"   📊 Documentos indexados: {stats['total_documents']}")
    print(f"   📦 Colección: {stats['collection_name']}")
    
    if stats['total_documents'] == 0:
        print("\n   ⚠️ WARNING: Vector store está VACÍO")
        print("   💡 Necesitas ejecutar: python init_rag.py")
    
except Exception as e:
    print(f"\n   ❌ ERROR inicializando RAG System: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 3. PROBAR BÚSQUEDA RAG
# ============================================================================

print("\n🔍 PASO 3: Probando búsqueda en RAG...")

try:
    from rag_system import RAGSystem
    
    rag = RAGSystem()
    
    # Query de prueba
    query_test = "canciones sobre saludos y buenos días"
    print(f"\n   Query de prueba: '{query_test}'")
    
    # Generar embedding
    query_embedding = rag.embeddings.embed_query(query_test)
    print(f"   ✅ Embedding generado: {len(query_embedding)} dimensiones")
    
    # Buscar canciones
    results = rag.vector_store.query(
        query_embedding=query_embedding,
        n_results=5,
        filter_metadata={'document_type': 'cancion'}
    )
    
    print(f"\n   📋 Resultados encontrados: {len(results['documents'])}")
    
    if len(results['documents']) > 0:
        print("\n   🎵 Canciones recuperadas:")
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'],
            results['metadatas'],
            results['distances']
        ), 1):
            similitud = (1 - distance) * 100
            print(f"\n      {i}. {metadata.get('filename', 'Sin nombre')}")
            print(f"         Similitud: {similitud:.1f}%")
            print(f"         Preview: {doc[:100]}...")
    else:
        print("\n   ⚠️ No se encontraron resultados")
        print("   💡 Esto indica que el vector store está vacío o no tiene canciones indexadas")
    
except Exception as e:
    print(f"\n   ❌ ERROR en búsqueda: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 4. VERIFICAR ÚLTIMO PLAN GENERADO
# ============================================================================

print("\n📄 PASO 4: Verificando último plan generado...")

try:
    # Buscar el plan más reciente en GCS local (si existe)
    from gcs_storage import GCSStorageManagerV2
    
    # Nota: Esta parte requiere credenciales GCS
    print("   ℹ️ Para verificar planes en GCS, usa la interfaz web o revisa los logs del backend")
    
except Exception as e:
    print(f"   ⚠️ No se puede verificar GCS localmente: {e}")

# ============================================================================
# 5. VERIFICAR GENERACIÓN CON GEMINI
# ============================================================================

print("\n🤖 PASO 5: Verificando integración con Gemini...")

try:
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if gemini_key:
        print(f"   ✅ GEMINI_API_KEY configurada")
        print(f"   Key (primeros 10 chars): {gemini_key[:10]}...")
    else:
        print(f"   ❌ GEMINI_API_KEY NO configurada")
        print(f"   💡 Revisa tu archivo .env")
    
    # Verificar que gemini_service.py existe
    gemini_service_path = Path('./gemini_service.py')
    print(f"\n   gemini_service.py existe: {gemini_service_path.exists()}")
    
    if gemini_service_path.exists():
        from gemini_service import plan_generator
        print(f"   ✅ plan_generator importado correctamente")
        print(f"   Modelo configurado: {plan_generator.model._model_name}")
    
except Exception as e:
    print(f"   ❌ ERROR verificando Gemini: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# RESUMEN Y RECOMENDACIONES
# ============================================================================

print("\n" + "="*80)
print("📊 RESUMEN DEL DIAGNÓSTICO")
print("="*80)

# Contar archivos
total_cuentos = len(list(cuentos_dir.glob('**/*.txt'))) if cuentos_dir.exists() else 0
total_canciones = len(list(canciones_dir.glob('**/*.txt'))) if canciones_dir.exists() else 0

print(f"\n✅ Archivos en biblioteca:")
print(f"   📖 Cuentos: {total_cuentos}")
print(f"   🎵 Canciones: {total_canciones}")

if total_cuentos + total_canciones == 0:
    print("\n❌ PROBLEMA DETECTADO: No hay archivos .txt en la biblioteca")
    print("   SOLUCIÓN:")
    print("   1. Agrega archivos .txt en ./rag_data/cuentos/")
    print("   2. Agrega archivos .txt en ./rag_data/canciones/")
    print("   3. Ejecuta: python init_rag.py")

try:
    from rag_system import RAGSystem
    rag = RAGSystem()
    stats = rag.get_stats()
    
    print(f"\n✅ Vector Store:")
    print(f"   📊 Documentos indexados: {stats['total_documents']}")
    
    if stats['total_documents'] == 0 and (total_cuentos + total_canciones) > 0:
        print("\n❌ PROBLEMA DETECTADO: Hay archivos pero el vector store está vacío")
        print("   SOLUCIÓN:")
        print("   Ejecuta: python init_rag.py")
    
    if stats['total_documents'] > 0:
        print("\n✅ RAG está correctamente configurado en el backend")
        print("\n⚠️ PROBLEMA PROBABLE: El frontend NO está usando RAG al generar planes")
        print("   POSIBLES CAUSAS:")
        print("   1. El endpoint /api/plans/generate NO está llamando al RAG")
        print("   2. Los documentos RAG NO se están pasando a Gemini")
        print("   3. El prompt de Gemini NO está usando el contexto RAG")
        
except Exception as e:
    print(f"\n❌ Error obteniendo stats: {e}")

print("\n" + "="*80)
print("🔍 Para más detalles, revisa los logs arriba")
print("="*80)